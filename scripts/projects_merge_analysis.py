#!/usr/bin/env python3
"""READ-ONLY analysis for merging Projects and Spaces into one "Project".

Reads (never writes) the live WebUI state:
  * <state>/projects.json                       projects (personal + team)
  * <state>/workspaces.json                     spaces of the default profile
  * <hermes>/profiles/*/webui_state/workspaces.json  spaces of other profiles
  * <state>/sessions/_index.json                chats: owner, profile, workspace, project
  * <hermes>/dashboard-governance.yaml          people and admin roles

and reports, per person, what they can see now versus after the proposed
migration, plus a conflict list. Output goes to --out (Markdown + JSON).

Visibility rules mirrored from the code (summarised, see report):
  * projects: admins see all; personal projects their owner; team projects
    (collaboration) the owner and members (api/project_collaboration.member).
  * spaces: admins see all; entries without owner/members are shared with
    every signed-in person; otherwise owner + members
    (api/routes._workspace_visible_to).

It imports nothing from the WebUI package, so it cannot trigger a migration.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import time
from pathlib import Path

ADMIN_ROLES = {"owner", "admin"}


def _read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _read_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}


def _norm(email) -> str:
    return str(email or "").strip().lower()


def _emails(entry) -> set:
    out = {_norm(entry.get("owner_email"))}
    out |= {_norm(m) for m in entry.get("members") or []}
    return {e for e in out if e}


def _inside(path: str, root: str) -> bool:
    try:
        p = os.path.realpath(os.path.expanduser(path))
        r = os.path.realpath(os.path.expanduser(root))
    except (OSError, ValueError):
        return False
    return p == r or p.startswith(r.rstrip("/") + "/")


def load(state: Path, hermes: Path):
    projects = _read_json(state / "projects.json", [])
    spaces = []  # (profile, entry)
    for entry in _read_json(state / "workspaces.json", []) or []:
        if isinstance(entry, dict) and entry.get("path"):
            spaces.append(("default", entry))
    for reg in sorted((hermes / "profiles").glob("*/webui_state/workspaces.json")):
        profile = reg.parent.parent.name
        for entry in _read_json(reg, []) or []:
            if isinstance(entry, dict) and entry.get("path"):
                spaces.append((profile, entry))
    index = _read_json(state / "sessions" / "_index.json", [])
    sessions = index if isinstance(index, list) else list((index or {}).values())
    policy = _read_yaml(hermes / "dashboard-governance.yaml")
    return projects, spaces, sessions, policy


def analyse(projects, spaces, sessions, policy):
    users = (policy or {}).get("users") or {}
    admins = {_norm(e) for e in (policy or {}).get("bootstrap_admins") or []}
    admins |= {_norm(e) for e, u in users.items() if ADMIN_ROLES & set((u or {}).get("roles") or [])}
    people = {_norm(e) for e in users} | admins
    live_projects = [p for p in projects if isinstance(p, dict) and not p.get("deleted")]
    for p in live_projects:
        people |= _emails(p)
    for _, s in spaces:
        people |= _emails(s)
    people.discard("")

    def project_visible(p, who):
        if who in admins:
            return True
        if who == _norm(p.get("owner_email")):
            return True
        return bool(p.get("collaboration")) and who in {_norm(m) for m in p.get("members") or []}

    def space_visible(s, who):
        if who in admins:
            return True
        em = _emails(s)
        return not em or who in em

    # Which projects use which space (through their chats' working folder).
    sessions_by_space = collections.defaultdict(list)
    orphans = []
    team_folders = {p.get("workspace"): p for p in live_projects if p.get("collaboration") and p.get("workspace")}
    for row in sessions:
        if not isinstance(row, dict) or row.get("archived"):
            continue
        ws = row.get("workspace") or ""
        profile = row.get("profile") or "default"
        if not ws:
            continue
        if any(_inside(ws, f) for f in team_folders):
            continue
        candidates = [(prof, s) for prof, s in spaces if prof == profile and _inside(ws, s["path"])]
        if not candidates:
            orphans.append({"session_id": row.get("session_id"), "profile": profile, "workspace": ws,
                            "owner": _norm(row.get("owner_email")), "title": (row.get("title") or "")[:80]})
            continue
        prof, best = max(candidates, key=lambda c: len(c[1]["path"]))
        sessions_by_space[(prof, best["path"])].append(row)

    # Conflicts.
    names = collections.defaultdict(set)
    for prof, s in spaces:
        names[str(s.get("name") or "").strip().lower()].add(prof)
    duplicate_space_names = sorted([{"name": n, "profiles": sorted(p)} for n, p in names.items() if n and len(p) > 1],
                                   key=lambda x: x["name"])
    pnames = collections.Counter(str(p.get("name") or "").strip().lower() for p in live_projects)
    snames = {str(s.get("name") or "").strip().lower() for _, s in spaces}
    duplicate_project_names = sorted(n for n, c in pnames.items() if n and c > 1)
    name_clashes_project_space = sorted(n for n in pnames if n and n in snames)
    unowned_spaces = [{"profile": prof, "name": s.get("name"), "path": s.get("path")}
                      for prof, s in spaces if not _emails(s)]
    missing_dirs = [{"profile": prof, "name": s.get("name"), "path": s.get("path")}
                    for prof, s in spaces if not os.path.isdir(os.path.expanduser(s["path"]))]
    multi_project_spaces = []
    link_candidates = []
    for (prof, path), rows in sessions_by_space.items():
        pids = collections.Counter(r.get("project_id") for r in rows if r.get("project_id"))
        if len(pids) > 1:
            multi_project_spaces.append({"profile": prof, "path": path, "projects": dict(pids)})
        if pids:
            link_candidates.append({"profile": prof, "path": path, "projects": dict(pids), "chats": len(rows)})

    # Per person: now vs after.
    #   Option A (proposed default): every space without a project becomes its
    #   own project with exactly the same owner/members; unowned spaces become a
    #   project shared with everyone (as today). Folder access is unchanged.
    #   Option B (link): a space is attached to the project(s) whose chats use
    #   it; project members then also reach that folder.
    proj_by_id = {p.get("project_id"): p for p in live_projects}
    per_person = {}
    gains_b = collections.defaultdict(list)
    for who in sorted(people):
        p_now = sorted(p.get("name") or p.get("project_id") for p in live_projects if project_visible(p, who))
        s_now = sorted(f"{prof}:{s.get('name')}" for prof, s in spaces if space_visible(s, who))
        space_projects_after = sorted(f"{prof}:{s.get('name')}" for prof, s in spaces if space_visible(s, who))
        per_person[who] = {
            "admin": who in admins,
            "projects_now": len(p_now), "spaces_now": len(s_now),
            "projects_after_option_a": len(p_now) + len(space_projects_after),
            "folders_now": len(s_now), "folders_after_option_a": len(space_projects_after),
            "gains_option_a": [], "losses_option_a": [],
        }
    for cand in link_candidates:
        prof, path = cand["profile"], cand["path"]
        space = next(s for p_, s in spaces if p_ == prof and s["path"] == path)
        for pid in cand["projects"]:
            project = proj_by_id.get(pid)
            if not project:
                continue
            for who in sorted(people):
                if project_visible(project, who) and not space_visible(space, who):
                    gains_b[who].append(f"folder {prof}:{space.get('name')} via project {project.get('name')}")
    for who, items in gains_b.items():
        if who in per_person:
            per_person[who]["gains_option_b"] = sorted(set(items))

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "people": len(people), "admins": sorted(admins),
        "projects": len(live_projects),
        "team_projects": sum(1 for p in live_projects if p.get("collaboration")),
        "personal_projects": sum(1 for p in live_projects if not p.get("collaboration")),
        "spaces": len(spaces), "profiles_with_spaces": len({p for p, _ in spaces}),
        "sessions_indexed": len(sessions),
        "sessions_with_workspace_in_space": sum(len(v) for v in sessions_by_space.values()),
        "orphaned_session_workdirs": len(orphans),
        "unowned_spaces": len(unowned_spaces), "missing_space_dirs": len(missing_dirs),
        "duplicate_space_names_across_profiles": len(duplicate_space_names),
        "duplicate_project_names": len(duplicate_project_names),
        "project_space_name_clashes": len(name_clashes_project_space),
        "spaces_used_by_multiple_projects": len(multi_project_spaces),
        "people_gaining_access_option_a": 0, "people_losing_access_option_a": 0,
        "people_gaining_access_option_b": sum(1 for v in gains_b.values() if v),
    }
    return {
        "summary": summary, "per_person": per_person,
        "conflicts": {
            "duplicate_space_names_across_profiles": duplicate_space_names,
            "duplicate_project_names": duplicate_project_names,
            "project_space_name_clashes": name_clashes_project_space,
            "unowned_spaces": unowned_spaces, "missing_space_dirs": missing_dirs,
            "spaces_used_by_multiple_projects": multi_project_spaces,
            "orphaned_session_workdirs": orphans,
        },
        "link_candidates": link_candidates,
    }


def to_markdown(result) -> str:
    s, c = result["summary"], result["conflicts"]
    lines = [f"# Projecten en Ruimtes samenvoegen: analyse ({s['generated_at']})", "",
             "Alleen gelezen, niets aangepast. Bronnen: projects.json, alle workspaces.json, sessions/_index.json, dashboard-governance.yaml.", "",
             "## Samenvatting", ""]
    for k, v in s.items():
        if k != "generated_at":
            lines.append(f"* {k}: {v if not isinstance(v, list) else ', '.join(v)}")
    lines += ["", "## Per persoon (nu en na optie A)", "",
              "Optie A: elke ruimte zonder project wordt een eigen project met precies dezelfde eigenaar en leden; "
              "ruimtes zonder eigenaar worden een project dat iedereen ziet (zoals nu). Mappentoegang blijft gelijk.", "",
              "| Persoon | Beheerder | Projecten nu | Ruimtes nu | Projecten na A | Mappen nu | Mappen na A | Erbij (optie B) |",
              "|---|---|---|---|---|---|---|---|"]
    for who, p in result["per_person"].items():
        lines.append(f"| {who} | {'ja' if p['admin'] else 'nee'} | {p['projects_now']} | {p['spaces_now']} | "
                     f"{p['projects_after_option_a']} | {p['folders_now']} | {p['folders_after_option_a']} | "
                     f"{len(p.get('gains_option_b', []))} |")
    lines += ["", "## Conflicten", ""]
    lines.append(f"### Ruimtenamen die in meerdere profielen voorkomen ({len(c['duplicate_space_names_across_profiles'])})")
    lines += [f"* {d['name']}: {', '.join(d['profiles'])}" for d in c["duplicate_space_names_across_profiles"][:60]] or ["* geen"]
    lines.append(f"\n### Dubbele projectnamen ({len(c['duplicate_project_names'])})")
    lines += [f"* {n}" for n in c["duplicate_project_names"]] or ["* geen"]
    lines.append(f"\n### Naam van project en ruimte gelijk ({len(c['project_space_name_clashes'])})")
    lines += [f"* {n}" for n in c["project_space_name_clashes"]] or ["* geen"]
    lines.append(f"\n### Ruimtes zonder eigenaar, nu zichtbaar voor iedereen ({len(c['unowned_spaces'])})")
    lines += [f"* {d['profile']}: {d['name']} ({d['path']})" for d in c["unowned_spaces"][:80]] or ["* geen"]
    lines.append(f"\n### Ruimtes waarvan de map niet (meer) bestaat ({len(c['missing_space_dirs'])})")
    lines += [f"* {d['profile']}: {d['name']} ({d['path']})" for d in c["missing_space_dirs"][:80]] or ["* geen"]
    lines.append(f"\n### Ruimtes die door gesprekken van meerdere projecten worden gebruikt ({len(c['spaces_used_by_multiple_projects'])})")
    lines += [f"* {d['profile']}: {d['path']} -> {d['projects']}" for d in c["spaces_used_by_multiple_projects"]] or ["* geen"]
    lines.append(f"\n### Gesprekken met een werkmap buiten elke ruimte ({len(c['orphaned_session_workdirs'])})")
    by_dir = collections.Counter((o["profile"], o["workspace"]) for o in c["orphaned_session_workdirs"])
    lines += [f"* {prof}: {ws} ({n} gesprekken)" for (prof, ws), n in by_dir.most_common(60)] or ["* geen"]
    lines += ["", "## Wie krijgt er toegang bij (optie B: ruimte koppelen aan het project dat haar gebruikt)", ""]
    any_gain = False
    for who, p in result["per_person"].items():
        g = p.get("gains_option_b") or []
        if g:
            any_gain = True
            lines.append(f"* {who}: {len(g)}")
            lines += [f"  * {x}" for x in g[:20]]
    if not any_gain:
        lines.append("* niemand")
    lines += ["", "Bij optie A krijgt niemand er toegang bij en verliest niemand toegang (per constructie)."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=os.path.expanduser("~/.hermes/webui"))
    ap.add_argument("--hermes", default=os.path.expanduser("~/.hermes"))
    ap.add_argument("--out", default=".analysis")
    args = ap.parse_args()
    projects, spaces, sessions, policy = load(Path(args.state), Path(args.hermes))
    result = analyse(projects, spaces, sessions, policy)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d")
    (out / f"projects-merge-{stamp}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / f"projects-merge-{stamp}.md").write_text(to_markdown(result), encoding="utf-8")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
