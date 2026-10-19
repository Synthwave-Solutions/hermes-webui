#!/usr/bin/env python3
"""Projects + Spaces merge: plan, apply, verify and roll back (step 4).

Every space (an entry in a workspaces.json registry) becomes a project of
kind "space" with exactly the same visibility:
  * same profile, same owner, same members (lower-cased);
  * a space without owner and members (visible to everyone today) becomes a
    project with ``shared_with_all: true``;
  * the space folder is the project's only folder (role "linked").
Spaces that already are a team project's own folder are skipped. Nothing is
deleted: workspaces.json files are only backed up (they stay the source of
truth for folder access), chats keep their project_id and working folder.

Commands (all take --state and --hermes; nothing is written without --apply):

  plan      print the decisions, write nothing
  apply     back up projects.json and every workspaces.json, add the projects,
            write a per-item log and the merge marker; idempotent
  verify    per-person access comparison (before = spaces, after = space
            projects): must show zero gain and zero loss; exit 1 otherwise
  rollback  remove the projects this migration added (by migration id) and
            the marker; --restore-files puts the backed-up files back instead

The visibility rules are mirrored from api/projects_hub.space_project_visible
and api/routes._workspace_visible_to; tests/test_projects_merge_migration.py
checks the mirror against the app functions.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ADMIN_ROLES = {"owner", "admin"}
MARKER = "projects_merge_state.json"
CATEGORY = "Werkmappen"
KIND = "space"


# ── reading ───────────────────────────────────────────────────────────────

def _read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def _norm(v) -> str:
    return str(v or "").strip().lower()


def _real(path) -> str:
    return os.path.realpath(os.path.expanduser(str(path)))


def registries(state: Path, hermes: Path) -> list[tuple[str, Path]]:
    out = [("default", state / "workspaces.json")]
    for reg in sorted((hermes / "profiles").glob("*/webui_state/workspaces.json")):
        out.append((reg.parent.parent.name, reg))
    return out


def load_spaces(state: Path, hermes: Path) -> list[tuple[str, dict]]:
    spaces = []
    for profile, reg in registries(state, hermes):
        for entry in _read_json(reg, []) or []:
            if isinstance(entry, dict) and str(entry.get("path") or "").strip():
                spaces.append((profile, entry))
    return spaces


def load_people(hermes: Path, projects, spaces):
    try:
        import yaml  # type: ignore
        with (hermes / "dashboard-governance.yaml").open("r", encoding="utf-8") as fh:
            policy = yaml.safe_load(fh) or {}
    except (ImportError, FileNotFoundError):
        policy = {}
    users = policy.get("users") or {}
    admins = {_norm(e) for e in policy.get("bootstrap_admins") or []}
    admins |= {_norm(e) for e, u in users.items() if ADMIN_ROLES & set((u or {}).get("roles") or [])}
    people = {_norm(e) for e in users} | admins
    for p in projects:
        if isinstance(p, dict):
            people.add(_norm(p.get("owner_email")))
            people |= {_norm(m) for m in p.get("members") or []}
    for _, s in spaces:
        people.add(_norm(s.get("owner_email")))
        people |= {_norm(m) for m in s.get("members") or []}
    people.discard("")
    return sorted(people), admins


# ── visibility (mirrors the app) ──────────────────────────────────────────

def space_visible(entry: dict, scope: str) -> bool:
    if scope == "all":
        return True
    emails = {_norm(entry.get("owner_email"))} | {_norm(m) for m in entry.get("members") or []}
    emails.discard("")
    return not emails or scope in emails


def space_project_visible(project: dict, scope: str) -> bool:
    if scope == "all":
        return True
    emails = {_norm(project.get("owner_email"))} | {_norm(m) for m in project.get("members") or []}
    emails.discard("")
    if not emails:
        return bool(project.get("shared_with_all"))
    return bool(scope) and scope in emails


def legacy_project_visible(project: dict, scope: str) -> bool:
    if scope == "all":
        return True
    owner = _norm(project.get("owner_email"))
    return bool(owner) and (owner == scope or scope in (project.get("members") or []))


# ── plan ──────────────────────────────────────────────────────────────────

def migration_id(profile: str, path: str) -> str:
    return "sp" + hashlib.sha1(f"{profile}\0{_real(path)}".encode()).hexdigest()[:10]


def plan(projects: list, spaces: list) -> tuple[list, list]:
    """Return (new_project_rows, decisions). Pure; no I/O except realpath/isdir."""
    live = [p for p in projects if isinstance(p, dict) and not p.get("deleted")]
    existing_ids = {p.get("project_id") for p in projects if isinstance(p, dict)}
    team_folders = {_real(p["workspace"]) for p in live if p.get("collaboration") and p.get("workspace")}
    name_profiles = collections.defaultdict(set)
    for prof, s in spaces:
        name_profiles[_norm(s.get("name"))].add(prof)
    project_names = collections.defaultdict(set)
    for p in live:
        project_names[_norm(p.get("name"))].add(p.get("profile") or "default")
    rows, decisions, taken = [], [], collections.defaultdict(set)
    for prof, s in spaces:
        path = str(s["path"]).strip()
        pid = migration_id(prof, path)
        base = str(s.get("name") or Path(path).name or "Map").strip()[:100]
        d = {"profile": prof, "space": base, "path": path, "project_id": pid}
        if _real(path) in team_folders:
            decisions.append({**d, "decision": "skip", "reason": "already the folder of a team project"})
            continue
        if pid in existing_ids:
            decisions.append({**d, "decision": "skip", "reason": "already migrated (idempotent)"})
            continue
        name, reasons = base, []
        if len(name_profiles[_norm(base)]) > 1 and prof != "default":
            name = f"{base} ({prof})"
            reasons.append(f"name also used in profiles {sorted(name_profiles[_norm(base)])}: suffixed with profile")
        if _norm(name) in {_norm(n) for n in taken[prof]} or prof in project_names.get(_norm(name), set()):
            name = f"{name} (map)"
            reasons.append("name already used by a project in this profile: suffixed with (map)")
        taken[prof].add(name)
        owner = _norm(s.get("owner_email"))
        members = sorted({_norm(m) for m in s.get("members") or []} - {"", owner})
        shared = not owner and not members
        if shared:
            reasons.append("space had no owner or members (visible to everyone): project shared with everyone")
        if not os.path.isdir(_real(path)):
            reasons.append("folder does not exist on disk: project kept so nothing disappears; fix or remove by hand")
        row = {
            "project_id": pid, "name": name, "kind": KIND, "category": CATEGORY, "color": "#64748b",
            "profile": prof, "owner_email": owner or None, "members": members,
            "folders": [{"path": path, "name": base, "role": "linked"}],
            "source_space": {"profile": prof, "path": path, "name": base},
            "created_at": time.time(),
        }
        if shared:
            row["shared_with_all"] = True
        rows.append(row)
        decisions.append({**d, "name": name, "decision": "create", "owner": owner or None,
                          "members": members, "shared_with_all": shared, "reasons": reasons})
    return rows, decisions


# ── verify ────────────────────────────────────────────────────────────────

def access_diff(projects: list, spaces: list, people: list, admins: set) -> dict:
    """Per person: spaces visible before vs space projects visible after.

    Keys are (profile, real folder). Folder access itself is unchanged by
    construction (workspaces.json files are not modified; see verify_files).
    """
    space_projects = [p for p in projects if isinstance(p, dict) and p.get("kind") == KIND and not p.get("deleted")]
    team_folders = {_real(p["workspace"]) for p in projects
                    if isinstance(p, dict) and p.get("collaboration") and p.get("workspace") and not p.get("deleted")}
    result = {}
    for who in people:
        scope = "all" if who in admins else who
        before = {(prof, _real(s["path"])) for prof, s in spaces
                  if space_visible(s, scope) and _real(s["path"]) not in team_folders}
        after = {(p.get("profile") or "default", _real(p["source_space"]["path"])) for p in space_projects
                 if space_project_visible(p, scope)}
        gain, loss = sorted(after - before), sorted(before - after)
        result[who] = {"before": len(before), "after": len(after),
                       "gain": [f"{a}:{b}" for a, b in gain], "loss": [f"{a}:{b}" for a, b in loss]}
    return result


# ── apply / rollback ──────────────────────────────────────────────────────

def _atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".projects-merge-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def backup(state: Path, hermes: Path, stamp: str) -> Path:
    base = state / "migration-backups" / f"projects-merge-{stamp}"
    dest, n = base, 1
    while True:
        try:
            dest.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            n += 1
            dest = base.with_name(f"{base.name}-{n}")
    manifest = []
    for name, src in [("projects.json", state / "projects.json")] + [
            (f"workspaces/{prof}.json", reg) for prof, reg in registries(state, hermes)]:
        if src.is_file():
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            manifest.append({"source": str(src), "backup": str(target), "sha256": _sha(src)})
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest


def apply(state: Path, hermes: Path) -> dict:
    projects = _read_json(state / "projects.json", [])
    spaces = load_spaces(state, hermes)
    rows, decisions = plan(projects, spaces)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = backup(state, hermes, stamp)
    run_id = dest.name
    for r in rows:
        r["migration_id"] = run_id
    if rows:
        _atomic_write(state / "projects.json", list(projects) + rows)
    with (dest / "migration-log.jsonl").open("w", encoding="utf-8") as fh:
        for d in decisions:
            fh.write(json.dumps({**d, "migration_id": run_id}, ensure_ascii=False) + "\n")
    marker = _read_json(state / MARKER, {}) or {}
    runs = list(marker.get("runs") or []) + [{"migration_id": run_id, "backup": str(dest), "created": len(rows),
                                             "at": time.strftime("%Y-%m-%d %H:%M:%S")}]
    _atomic_write(state / MARKER, {"version": 1, "runs": runs})
    return {"migration_id": run_id, "backup": str(dest), "created": len(rows),
            "skipped": sum(1 for d in decisions if d["decision"] == "skip")}


def rollback(state: Path, hermes: Path, backup_dir: Path | None, restore_files: bool) -> dict:
    marker = _read_json(state / MARKER, {}) or {}
    if restore_files:
        if not backup_dir:
            raise SystemExit("--backup is required with --restore-files")
        manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest:
            shutil.copy2(item["backup"], item["source"])
        (state / MARKER).unlink(missing_ok=True)
        return {"restored_files": len(manifest)}
    ids = {r.get("migration_id") for r in marker.get("runs") or []}
    if backup_dir:
        ids = {backup_dir.name}
    projects = _read_json(state / "projects.json", [])
    kept = [p for p in projects if not (isinstance(p, dict) and p.get("kind") == KIND and p.get("migration_id") in ids)]
    removed = len(projects) - len(kept)
    _atomic_write(state / "projects.json", kept)
    remaining = [r for r in marker.get("runs") or [] if r.get("migration_id") not in ids]
    if remaining:
        _atomic_write(state / MARKER, {"version": 1, "runs": remaining})
    else:
        (state / MARKER).unlink(missing_ok=True)
    return {"removed_projects": removed, "migration_ids": sorted(i for i in ids if i)}


def verify(state: Path, hermes: Path, backup_dir: Path | None = None) -> tuple[bool, dict]:
    projects = _read_json(state / "projects.json", [])
    spaces = load_spaces(state, hermes)
    people, admins = load_people(hermes, projects, spaces)
    diff = access_diff(projects, spaces, people, admins)
    ok = all(not v["gain"] and not v["loss"] for v in diff.values())
    files = {}
    if backup_dir and (backup_dir / "manifest.json").is_file():
        for item in json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8")):
            if item["source"].endswith("workspaces.json"):
                same = _sha(Path(item["source"])) == item["sha256"]
                files[item["source"]] = "unchanged" if same else "CHANGED"
                ok = ok and same
        base = json.loads(Path(backup_dir / "projects.json").read_text(encoding="utf-8")) \
            if (backup_dir / "projects.json").is_file() else []
        now_non_space = [p for p in projects if not (isinstance(p, dict) and p.get("kind") == KIND)]
        files["projects.json (non-space rows)"] = "unchanged" if now_non_space == base else "CHANGED"
        ok = ok and now_non_space == base
    return ok, {"ok": ok, "people": diff, "files": files,
                "space_projects": sum(1 for p in projects if isinstance(p, dict) and p.get("kind") == KIND)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["plan", "apply", "verify", "rollback"])
    ap.add_argument("--state", default=os.path.expanduser("~/.hermes/webui"))
    ap.add_argument("--hermes", default=os.path.expanduser("~/.hermes"))
    ap.add_argument("--apply", action="store_true", help="required for apply and rollback")
    ap.add_argument("--backup", help="backup dir (verify: compare files; rollback: which run)")
    ap.add_argument("--restore-files", action="store_true")
    ap.add_argument("--out", help="write the result JSON here")
    args = ap.parse_args()
    state, hermes = Path(args.state), Path(args.hermes)
    backup_dir = Path(args.backup) if args.backup else None
    if args.command == "plan":
        rows, decisions = plan(_read_json(state / "projects.json", []), load_spaces(state, hermes))
        result = {"create": len(rows), "decisions": decisions}
        code = 0
    elif args.command == "apply":
        if not args.apply:
            print("refusing: add --apply to write", file=sys.stderr)
            return 2
        result = apply(state, hermes)
        code = 0
    elif args.command == "verify":
        ok, result = verify(state, hermes, backup_dir)
        code = 0 if ok else 1
    else:
        if not args.apply:
            print("refusing: add --apply to write", file=sys.stderr)
            return 2
        result = rollback(state, hermes, backup_dir, args.restore_files)
        code = 0
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("decisions", "people")}
    if args.command == "verify":
        summary["people_with_gain"] = [k for k, v in result["people"].items() if v["gain"]]
        summary["people_with_loss"] = [k for k, v in result["people"].items() if v["loss"]]
    if args.command == "plan":
        summary["decision_counts"] = dict(collections.Counter(d["decision"] for d in result["decisions"]))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
