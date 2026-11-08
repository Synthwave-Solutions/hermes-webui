"""Use-case backlog, the agent that works an idea out, and Playbooks (8 Nov 2026).

Backlog
    Every opportunity worth keeping, from any Studio use case or added by
    hand, in one ranked list for the organisation: status (idea, chosen, in
    design, built, live, parked), team, impact, effort, owner and the use case
    it came from. Order is a manual rank (drag and drop in the UI).

Agent works it out ("Laat de agent het maken")
    A backlog idea becomes a Studio use case with the opportunity chosen; a
    background thread runs the design and build-plan steps with the model and
    leaves the use case at the dry run. Building stays a person's click.

Playbooks
    The organisation's library of how a process is done now with the Super
    Agent: steps with text, screenshots and screen recordings, linked to the
    bots, tasks and skills involved and the team that works this way. Visible
    to the organisation (default), the team, or only the author. A draft can
    be written by the model from a built use case.

Media are stored under ``STATE_DIR/studio/media/<playbook>/`` and served
only to people who may see that playbook.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs

from api import org_structure, studio
from api.helpers import j

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
STATUSES = ("idea", "chosen", "design", "built", "live", "parked")
VISIBILITY = ("org", "team", "private")
MEDIA_MAX = 14 * 1024 * 1024
MEDIA_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif",
               "video/webm": ".webm", "video/mp4": ".mp4", "audio/webm": ".weba", "audio/mpeg": ".mp3"}
_ID = re.compile(r"^(bl|pb)_[a-f0-9]{12}$")
_FILE = re.compile(r"^[a-f0-9]{16}\.(png|jpg|webp|gif|webm|mp4|weba|mp3)$")
_AUTOPILOT: dict[str, dict] = {}


def _dir() -> Path:
    return studio._dir()


def _read(name: str, default):
    try:
        return json.loads((_dir() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(name: str, data) -> None:
    path = _dir() / name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _txt(v, n=300) -> str:
    return studio._txt(v, n)


def _sees_team(view, team: str) -> bool:
    if view.scope == org_structure.SCOPE_ALL:
        return True
    return bool(team) and view.sees_team(team)


# ── Backlog ──────────────────────────────────────────────────────────────────

def backlog_items() -> list[dict]:
    data = _read("backlog.json", {"items": []})
    return [i for i in data.get("items") or [] if isinstance(i, dict)]


def _visible_item(view, item) -> bool:
    return item.get("owner") == view.email or _sees_team(view, item.get("team") or "") or (
        view.scope != org_structure.SCOPE_NONE and not item.get("team"))


def backlog_for(view) -> list[dict]:
    rows = [dict(i, editable=_editable_item(view, i), autopilot=_AUTOPILOT.get(i["id"]))
            for i in backlog_items() if _visible_item(view, i)]
    return sorted(rows, key=lambda r: (STATUSES.index(r.get("status", "idea")) if r.get("status") in STATUSES else 9,
                                       r.get("rank", 1e9)))


def _editable_item(view, item) -> bool:
    if item.get("owner") == view.email or view.scope == org_structure.SCOPE_ALL:
        return True
    return bool(item.get("team")) and (view.edits_team(item["team"]) or item["team"] in view.lead_teams)


def save_item(view, body: dict) -> dict:
    with _LOCK:
        data = _read("backlog.json", {"items": []})
        items = [i for i in data.get("items") or [] if isinstance(i, dict)]
        item_id = str(body.get("id") or "")
        if item_id:
            item = next((i for i in items if i.get("id") == item_id), None)
            if item is None:
                raise KeyError("Idea not found")
            if not _editable_item(view, item):
                raise PermissionError("Only the owner, the team lead or an admin can change this idea")
        else:
            item = {"id": "bl_" + secrets.token_hex(6), "owner": view.email, "created_at": time.time(),
                    "status": "idea", "rank": (max([i.get("rank", 0) for i in items] or [0]) + 1)}
            items.append(item)
        if "title" in body or not item_id:
            title = _txt(body.get("title"), 140)
            if not title:
                raise ValueError("An idea needs a title")
            item["title"] = title
        for key, limit in (("pain", 200), ("why", 300), ("goal", 120)):
            if key in body:
                item[key] = _txt(body.get(key), limit)
        for key in ("impact", "effort"):
            if key in body:
                item[key] = studio._int(body.get(key), 1, 5)
        if "building_block" in body:
            item["building_block"] = body["building_block"] if body.get("building_block") in studio.BLOCKS else "task"
        if "status" in body:
            if body["status"] not in STATUSES:
                raise ValueError("Unknown status")
            item["status"] = body["status"]
        if "team" in body:
            team = str(body.get("team") or "")
            if team and team not in org_structure.team_keys():
                raise ValueError("Unknown team")
            item["team"] = team
        for key in ("use_case", "source_use_case"):
            if key in body:
                item[key] = _txt(body.get(key), 20)
        item.setdefault("impact", 3)
        item.setdefault("effort", 3)
        item.setdefault("building_block", "task")
        item["updated_at"] = time.time()
        if body.get("delete"):
            items.remove(item)
        data["items"] = items
        _write("backlog.json", data)
        return item


def reorder(view, ids: list[str]) -> None:
    with _LOCK:
        data = _read("backlog.json", {"items": []})
        items = {i["id"]: i for i in data.get("items") or [] if isinstance(i, dict)}
        rank = 1
        for item_id in ids:
            item = items.get(item_id)
            if item is None or not _editable_item(view, item):
                continue
            item["rank"] = rank
            rank += 1
        data["items"] = list(items.values())
        _write("backlog.json", data)


# ── The agent works an idea out ──────────────────────────────────────────────

def _autopilot_run(view, item: dict, uc_id: str) -> None:
    state = _AUTOPILOT[item["id"]]
    try:
        state.update(step="design", message="Proces ontwerpen")
        process = (f"Dit idee komt uit de backlog. Knelpunt: {item.get('pain') or '-'}. "
                   f"Waarom: {item.get('why') or '-'}. Doel: {item.get('goal') or '-'}. "
                   "Ontwerp het meest gangbare huidige proces hiervoor en hoe het met de Super Agent wordt.")
        studio.run_step(view, {"id": uc_id, "step": "design", "input": process})
        state.update(step="playbook", message="Bouwplan maken")
        studio.run_step(view, {"id": uc_id, "step": "playbook", "input": ""})
        studio.update(view, {"id": uc_id, "phase": "build"})
        save_item(view, {"id": item["id"], "status": "design", "use_case": uc_id})
        state.update(step="done", message="Klaar voor jouw controle", done=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("autopilot failed for %s", item.get("id"), exc_info=True)
        state.update(step="failed", message=str(exc)[:200], done=True, failed=True)


def autopilot(view, item_id: str) -> dict:
    item = next((i for i in backlog_items() if i.get("id") == item_id), None)
    if item is None or not _visible_item(view, item):
        raise KeyError("Idea not found")
    running = _AUTOPILOT.get(item_id)
    if running and not running.get("done"):
        return running
    doc = studio.update(view, {"title": item["title"], "team": item.get("team") or "", "notes": [
        {"role": "user", "text": f"Uit de backlog: {item['title']}. {item.get('pain') or ''}"}]})
    opp = {"id": "o1", "title": item.get("pain") or item["title"], "pain": item.get("pain", ""), "goal": item.get("goal", ""),
           "solutions": [{"id": "o1s1", "title": item["title"], "how": item.get("why", ""), "impact": item.get("impact", 3),
                          "effort": item.get("effort", 3), "building_block": item.get("building_block", "task")}]}
    studio.update(view, {"id": doc["id"], "opportunities": [opp], "selected": "o1s1", "phase": "design",
                         "goals": [{"name": item.get("goal") or item["title"], "kpi": ""}]})
    save_item(view, {"id": item_id, "status": "chosen", "use_case": doc["id"]})
    _AUTOPILOT[item_id] = {"use_case": doc["id"], "step": "start", "message": "Gestart", "done": False, "started": time.time()}
    threading.Thread(target=_autopilot_run, args=(view, item, doc["id"]), daemon=True, name="studio-autopilot").start()
    return _AUTOPILOT[item_id]


# ── Playbooks ────────────────────────────────────────────────────────────────

def _pb_path(pb_id: str) -> Path:
    if not _ID.match(str(pb_id or "")) or not str(pb_id).startswith("pb_"):
        raise KeyError("Playbook not found")
    folder = _dir() / "playbooks"
    folder.mkdir(exist_ok=True)
    return folder / f"{pb_id}.json"


def _pb_load(pb_id: str) -> dict:
    try:
        return json.loads(_pb_path(pb_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise KeyError("Playbook not found")


def _pb_visible(view, pb: dict) -> bool:
    if pb.get("owner") == view.email or view.scope == org_structure.SCOPE_ALL:
        return True
    if pb.get("status") != "published":
        return False
    vis = pb.get("visibility", "org")
    if vis == "org":
        return True
    return vis == "team" and _sees_team(view, pb.get("team") or "")


def _pb_editable(view, pb: dict) -> bool:
    return pb.get("owner") == view.email or view.scope == org_structure.SCOPE_ALL or (
        bool(pb.get("team")) and view.edits_team(pb["team"]))


def playbooks_for(view) -> list[dict]:
    folder = _dir() / "playbooks"
    out = []
    for path in sorted(folder.glob("pb_*.json")) if folder.is_dir() else []:
        try:
            pb = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if _pb_visible(view, pb):
            media = sum(len(s.get("media") or []) for s in pb.get("steps") or [])
            cover = next((m for s in pb.get("steps") or [] for m in s.get("media") or [] if m.get("kind") == "image"), None)
            out.append({k: pb.get(k) for k in ("id", "title", "summary", "team", "category", "owner", "status", "visibility", "updated_at", "trigger")}
                       | {"steps": len(pb.get("steps") or []), "media": media, "cover": cover and cover.get("file"),
                          "links": pb.get("links") or {}, "stats": run_stats(pb)})
    return sorted(out, key=lambda r: -(r.get("updated_at") or 0))


def save_playbook(view, body: dict) -> dict:
    pb_id = str(body.get("id") or "")
    with _LOCK:
        if pb_id:
            pb = _pb_load(pb_id)
            if not _pb_editable(view, pb):
                raise PermissionError("Only the author, the team's admin or an organisation admin can change this playbook")
        else:
            pb = {"id": "pb_" + secrets.token_hex(6), "owner": view.email, "created_at": time.time(), "status": "draft",
                  "visibility": "org", "steps": [], "links": {}}
        if "title" in body or not pb_id:
            pb["title"] = _txt(body.get("title"), 120) or pb.get("title") or "Nieuw playbook"
        for key, limit in (("summary", 600), ("trigger", 200), ("category", 60)):
            if key in body:
                pb[key] = _txt(body.get(key), limit)
        if "team" in body:
            team = str(body.get("team") or "")
            if team and team not in org_structure.team_keys():
                raise ValueError("Unknown team")
            pb["team"] = team
        if "visibility" in body:
            if body["visibility"] not in VISIBILITY:
                raise ValueError("Unknown visibility")
            pb["visibility"] = body["visibility"]
        if "status" in body:
            if body["status"] not in ("draft", "published"):
                raise ValueError("Unknown status")
            pb["status"] = body["status"]
        if "use_case" in body:
            pb["use_case"] = _txt(body.get("use_case"), 20)
        if "links" in body and isinstance(body["links"], dict):
            pb["links"] = {k: [_txt(v, 120) for v in (body["links"].get(k) or [])[:20]] for k in ("bots", "tasks", "skills")}
        if "steps" in body:
            known = {m["file"] for s in pb.get("steps") or [] for m in s.get("media") or []}
            steps = []
            for s in (body.get("steps") or [])[:40]:
                if not isinstance(s, dict):
                    continue
                media = [{"file": m["file"], "kind": m.get("kind") if m.get("kind") in ("image", "video", "audio") else "image",
                          "caption": _txt(m.get("caption"), 160)}
                         for m in (s.get("media") or [])[:12] if isinstance(m, dict) and _FILE.match(str(m.get("file")))
                         and (m.get("file") in known or (_dir() / "media" / pb["id"] / str(m.get("file"))).is_file())]
                steps.append({"title": _txt(s.get("title"), 140), "text": str(s.get("text") or "")[:6000],
                              "actor": _txt(s.get("actor"), 40), "prompt": str(s.get("prompt") or "")[:2000], "media": media})
            pb["steps"] = steps
        pb["updated_at"] = time.time()
        pb["updated_by"] = view.email
        _pb_path(pb["id"]).write_text(json.dumps(pb, ensure_ascii=False, indent=1), encoding="utf-8")
        return pb


PLAYBOOK_DOC = """Schrijf een Playbook voor collega's: hoe dit proces NU wordt uitgevoerd met de Super Agent van
SynthPulse. Concreet en kort, in de jij-vorm, Nederlands. Per stap: een titel, wie het doet (jij, de Super Agent,
een bot of een geplande taak), wat je precies doet, en waar je de Super Agent iets vraagt de letterlijke prompt in "prompt".
Begin met wanneer je dit gebruikt. Alleen JSON:
{"title": "...", "summary": "...", "trigger": "wanneer gebruik je dit",
 "steps": [{"title": "...", "actor": "jij", "text": "...", "prompt": "..."}]}"""


def draft_from_use_case(view, uc_id: str) -> dict:
    doc = studio._load(uc_id)
    if not studio._visible(view, doc):
        raise KeyError("Use case not found")
    comps = (doc.get("playbook") or {}).get("components") or []
    built = [b for b in doc.get("build_log") or [] if b.get("status") == "ok"]
    process = doc.get("process") or {}
    context = (f"Use case: {doc.get('title')}\nNieuw proces:\n" + "\n".join(f"- {s.get('step')} ({s.get('actor')})" for s in process.get("to_be") or [])
               + "\nOnderdelen:\n" + "\n".join(f"- {c.get('type')}: {c.get('name')} {c.get('schedule') or ''}" for c in comps)
               + "\nGebouwd:\n" + "\n".join(f"- {b.get('ref')}" for b in built))
    answer = studio._ask_json(PLAYBOOK_DOC, context)
    links = {"bots": [b["ref"].replace("bot ", "") for b in built if b.get("type") == "bot"],
             "tasks": [b["ref"].split(" → ")[0] for b in built if b.get("type") == "task"],
             "skills": [b["ref"].replace("skill ", "") for b in built if b.get("type") == "skill"]}
    return save_playbook(view, {"title": answer.get("title") or doc.get("title"), "summary": answer.get("summary"),
                                "trigger": answer.get("trigger"), "team": doc.get("team") or "", "use_case": uc_id,
                                "steps": [{"title": s.get("title"), "actor": s.get("actor"), "text": s.get("text"), "prompt": s.get("prompt"), "media": []}
                                          for s in answer.get("steps") or [] if isinstance(s, dict)], "links": links})


def record_run(view, body: dict) -> dict:
    """Someone followed the playbook: minutes it took, steps done, a note.
    Feeds "what does it cost now" next to the value of the tasks involved."""
    with _LOCK:
        pb = _pb_load(str(body.get("id") or ""))
        if not _pb_visible(view, pb):
            raise KeyError("Playbook not found")
        steps = len(pb.get("steps") or [])
        done = [int(i) for i in (body.get("done") or []) if str(i).isdigit() and int(i) < steps][:steps]
        run = {"by": view.email, "at": time.time(), "minutes": studio._int(body.get("minutes"), 0, 6000),
               "done": sorted(set(done)), "complete": len(set(done)) == steps and steps > 0,
               "note": _txt(body.get("note"), 400)}
        pb["runs"] = ((pb.get("runs") or []) + [run])[-200:]
        _pb_path(pb["id"]).write_text(json.dumps(pb, ensure_ascii=False, indent=1), encoding="utf-8")
        return run


def run_stats(pb: dict) -> dict:
    runs = pb.get("runs") or []
    complete = [r for r in runs if r.get("complete")]
    mins = [r["minutes"] for r in complete if r.get("minutes")]
    return {"runs": len(runs), "complete": len(complete), "avg_minutes": round(sum(mins) / len(mins)) if mins else None,
            "last_at": runs[-1]["at"] if runs else None}


def save_media(view, body: dict) -> dict:
    pb = _pb_load(str(body.get("playbook") or ""))
    if not _pb_editable(view, pb):
        raise PermissionError("Only people who may edit this playbook can add media")
    mime = str(body.get("type") or "").split(";")[0].strip().lower()
    ext = MEDIA_TYPES.get(mime)
    if not ext:
        raise ValueError("Use an image (png, jpg, webp, gif), a video (webm, mp4) or audio (webm, mp3)")
    try:
        raw = base64.b64decode(str(body.get("data") or ""), validate=True)
    except ValueError:
        raise ValueError("Invalid file data")
    if not raw or len(raw) > MEDIA_MAX:
        raise ValueError("A file can be at most 14 MB")
    folder = _dir() / "media" / pb["id"]
    folder.mkdir(parents=True, exist_ok=True)
    name = secrets.token_hex(8) + ext
    (folder / name).write_bytes(raw)
    kind = "video" if mime.startswith("video/") else "audio" if mime.startswith("audio/") else "image"
    return {"file": name, "kind": kind, "size": len(raw)}


def serve_media(handler, view, pb_id: str, name: str) -> None:
    pb = _pb_load(pb_id)
    if not _pb_visible(view, pb) or not _FILE.match(name or ""):
        raise KeyError("Not found")
    path = _dir() / "media" / pb["id"] / name
    if not path.is_file():
        raise KeyError("Not found")
    data = path.read_bytes()
    ctype = mimetypes.guess_type(name)[0] or ("video/webm" if name.endswith(".webm") else "audio/webm" if name.endswith(".weba") else "application/octet-stream")
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=3600")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(data)



# ── Shared prompts: per team, department or the whole organisation ──────────
# Personal prompts stay where they are (/api/prompts, per profile). These are
# the ones people share, with a category, the way SynthDrive's prompt bank did.

PROMPT_SCOPES = ("team", "department", "org")


def _member_departments(view) -> set:
    return {k.split("/", 1)[0] for k in (view.member_teams | view.lead_teams)} | set(view.departments)


def _prompt_visible(view, p: dict) -> bool:
    if view.scope == org_structure.SCOPE_ALL or p.get("owner") == view.email:
        return True
    scope = p.get("scope")
    if scope == "org":
        return True
    if scope == "team":
        return _sees_team(view, p.get("team") or "")
    if scope == "department":
        return (p.get("department") or "") in _member_departments(view)
    return False


def _prompt_editable(view, p: dict) -> bool:
    if view.scope == org_structure.SCOPE_ALL or p.get("owner") == view.email:
        return True
    if p.get("scope") == "team" and p.get("team"):
        return view.edits_team(p["team"]) or p["team"] in view.lead_teams
    if p.get("scope") == "department":
        return (p.get("department") or "") in view.departments
    return False


def prompts_for(view) -> dict:
    rows = [dict(p, editable=_prompt_editable(view, p)) for p in _read("prompts.json", {"prompts": []}).get("prompts") or []
            if isinstance(p, dict) and _prompt_visible(view, p)]
    data = org_structure.load()
    depts = org_structure.departments(data)
    teams = [{"key": k, "name": (t or {}).get("name") or k, "department": (t or {}).get("department") or k.split("/", 1)[0]}
             for k, t in sorted((data.get("teams") or {}).items()) if isinstance(t, dict)]
    mine = view.member_teams | view.lead_teams
    return {"prompts": sorted(rows, key=lambda r: (-(r.get("uses") or 0), str(r.get("label") or "").lower())),
            "teams": teams, "departments": [{"key": k, "name": (d or {}).get("name") or k} for k, d in sorted(depts.items())],
            "my_teams": sorted(mine), "my_departments": sorted(_member_departments(view)),
            "is_admin": view.scope == org_structure.SCOPE_ALL,
            "categories": sorted({r.get("category") for r in rows if r.get("category")})}


def save_prompt(view, body: dict) -> dict:
    op = body.get("op") or "save"
    with _LOCK:
        data = _read("prompts.json", {"prompts": []})
        rows = [p for p in data.get("prompts") or [] if isinstance(p, dict)]
        pid = str(body.get("id") or "")
        row = next((p for p in rows if p.get("id") == pid), None) if pid else None
        if pid and row is None:
            raise KeyError("Prompt not found")
        if op == "use":
            if row is None or not _prompt_visible(view, row):
                raise KeyError("Prompt not found")
            row["uses"] = int(row.get("uses") or 0) + 1
            _write("prompts.json", {"prompts": rows})
            return {"ok": True, "uses": row["uses"]}
        if op == "delete":
            if row is None or not _prompt_editable(view, row):
                raise PermissionError("Only the author or an admin of that team can remove this prompt")
            rows.remove(row)
            _write("prompts.json", {"prompts": rows})
            return {"ok": True}
        if row is not None and not _prompt_editable(view, row):
            raise PermissionError("Only the author or an admin of that team can change this prompt")
        text = str(body.get("text") if "text" in body else (row or {}).get("text") or "").strip()
        if not text:
            raise ValueError("A prompt needs text")
        if len(text) > 8000:
            raise ValueError("Prompt too long (max 8000 characters)")
        scope = body.get("scope") or (row or {}).get("scope") or "team"
        if scope not in PROMPT_SCOPES:
            raise ValueError("Share with a team, a department or the organisation")
        team = str(body.get("team") if "team" in body else (row or {}).get("team") or "")
        dept = str(body.get("department") if "department" in body else (row or {}).get("department") or "")
        structure = org_structure.load()
        if scope == "team":
            if team not in (structure.get("teams") or {}):
                raise ValueError("Choose a team")
            if view.scope != org_structure.SCOPE_ALL and not _sees_team(view, team):
                raise PermissionError("You can only share with your own team")
            dept = ""
        elif scope == "department":
            if dept not in org_structure.departments(structure):
                raise ValueError("Choose a department")
            if view.scope != org_structure.SCOPE_ALL and dept not in _member_departments(view):
                raise PermissionError("You can only share with your own department")
            team = ""
        else:
            team = dept = ""
        if row is None:
            if len(rows) >= 2000:
                raise ValueError("Too many shared prompts")
            row = {"id": "pr_" + secrets.token_hex(6), "owner": view.email, "created_at": time.time(), "uses": 0}
            rows.append(row)
        row.update({"label": _txt(body.get("label") if "label" in body else row.get("label"), 120) or text[:60],
                    "text": text, "category": _txt(body.get("category") if "category" in body else row.get("category"), 60),
                    "scope": scope, "team": team, "department": dept, "updated_at": time.time(),
                    "source": _txt(body.get("source") if "source" in body else row.get("source"), 80)})
        _write("prompts.json", {"prompts": rows})
        return dict(row, editable=True)


# ── Organisation profile: context for every QuickScan ───────────────────────

PROFILE_FIELDS = {"name": 120, "website": 200, "sector": 120, "size": 80, "description": 900, "customers": 400, "policy": 900}
PROFILE_LISTS = {"goals": (8, 200), "systems": (40, 60), "products": (12, 120), "rules": (16, 200), "departments_note": (12, 120)}


def load_profile() -> dict:
    return _read("org_profile.json", {})


def clean_profile(raw: dict) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    out = {k: _txt(raw.get(k), n) for k, n in PROFILE_FIELDS.items()}
    for k, (count, n) in PROFILE_LISTS.items():
        items = raw.get(k) if isinstance(raw.get(k), list) else re.split(r"[,\n]", str(raw.get(k) or ""))
        out[k] = [x for x in (_txt(i, n) for i in items[:count * 2]) if x][:count]
    if out["website"] and not re.match(r"^https?://", out["website"]):
        out["website"] = "https://" + out["website"]
    return out


def save_profile(view, body: dict) -> dict:
    if view.scope != org_structure.SCOPE_ALL:
        raise PermissionError("Only organisation admins change the organisation profile")
    with _LOCK:
        current = load_profile()
        profile = dict(current, **clean_profile(dict({k: current.get(k) for k in (*PROFILE_FIELDS, *PROFILE_LISTS)}, **body)))
        profile.update(updated_at=time.time(), updated_by=view.email)
        _write("org_profile.json", profile)
    return profile


def context_text(limit: int = 1400) -> str:
    """The organisation profile as a short context block for Studio prompts."""
    p = load_profile()
    if not any(p.get(k) for k in (*PROFILE_FIELDS, *PROFILE_LISTS)):
        return ""
    parts = []
    head = ", ".join(x for x in (p.get("sector"), p.get("size")) if x)
    if p.get("name"):
        parts.append(p["name"] + (f" ({head})" if head else ""))
    elif head:
        parts.append(head)
    if p.get("description"):
        parts.append(p["description"])
    if p.get("products"):
        parts.append("Producten en diensten: " + "; ".join(p["products"]))
    if p.get("customers"):
        parts.append("Klanten: " + p["customers"])
    if p.get("goals"):
        parts.append("Doelen: " + "; ".join(p["goals"]))
    if p.get("systems"):
        parts.append("Systemen in gebruik: " + ", ".join(p["systems"]))
    if p.get("rules"):
        parts.append("Regels voor AI: " + "; ".join(p["rules"]))
    if p.get("policy"):
        parts.append("Beleid voor AI en data: " + p["policy"])
    return "\n".join(parts)[:limit]


_RESEARCH = """Je onderzoekt een organisatie voor een AI QuickScan. Je krijgt tekst van hun website.
Haal eruit wat er staat, en verzin niets: laat een veld leeg als het niet op de site staat.
Nederlands, kort en zakelijk. Alleen JSON:
{"name": "...", "sector": "...", "size": "...", "description": "twee of drie zinnen wat ze doen",
 "products": ["..."], "customers": "voor wie", "systems": ["software of platforms die op de site genoemd worden"],
 "goals": ["ambities of speerpunten die de site noemt"], "summary": "een zin wat je gevonden hebt"}"""


def _public_host(host: str) -> bool:
    import ipaddress
    import socket

    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return bool(infos)


def fetch_public_page(url: str, limit: int = 400_000) -> tuple[str, str]:
    """GET a public web page (no private addresses, at most three redirects). Returns (final url, text)."""
    import html as _html
    import urllib.error
    import urllib.parse
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(4):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or not _public_host(parts.hostname):
            raise ValueError("Only public web addresses can be researched")
        req = urllib.request.Request(url, headers={"User-Agent": "SynthPulse-Studio/1.0 (organisation profile)",
                                                   "Accept": "text/html,application/xhtml+xml"})
        try:
            resp = opener.open(req, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            raise ValueError(f"The website answered {e.code}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ValueError("The website could not be reached") from e
        with resp:
            raw = resp.read(limit)
            charset = resp.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        # What a page says about itself, also when its body is built by JavaScript.
        meta = []
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
        if title:
            meta.append("Titel: " + title.group(1).strip())
        for m in re.finditer(r'(?is)<meta\s+[^>]*>', text):
            tag = m.group(0)
            name = re.search(r'(?i)(?:name|property)=["\']([^"\']+)["\']', tag)
            content = re.search(r'(?i)content=["\']([^"\']*)["\']', tag)
            if name and content and name.group(1).lower() in ("description", "og:title", "og:description", "og:site_name", "keywords", "twitter:description"):
                meta.append(f"{name.group(1)}: {content.group(1).strip()}")
        for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', text):
            meta.append("Gestructureerde gegevens: " + re.sub(r"\s+", " ", m.group(1))[:2500])
        text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", text)
        links = re.findall(r'(?i)href=["\']([^"\']+)["\']', text)
        body = _html.unescape(re.sub(r"<[^>]+>", " ", text))
        body = re.sub(r"\s+", " ", body).strip()
        head = _html.unescape("\n".join(dict.fromkeys(meta)))
        return url, (head + "\n\n" if head else "") + body + "\n\nLINKS: " + " ".join(links[:200])
    raise ValueError("Too many redirects")


def research_profile(view, url: str) -> dict:
    """Read the organisation's website and propose profile fields. Nothing is saved."""
    import urllib.parse

    if view.scope != org_structure.SCOPE_ALL:
        raise PermissionError("Only organisation admins research the organisation profile")
    url = str(url or "").strip()
    if url and not re.match(r"^https?://", url):
        url = "https://" + url
    if not url:
        raise ValueError("Fill in the website first")
    final, text = fetch_public_page(url)
    pages, sources = [text.split("\n\nLINKS: ", 1)[0][:9000]], [final]
    links = text.split("\n\nLINKS: ", 1)[1].split() if "\n\nLINKS: " in text else []
    host = urllib.parse.urlsplit(final).hostname
    for href in links:
        if len(sources) >= 3:
            break
        full = urllib.parse.urljoin(final, href)
        if urllib.parse.urlsplit(full).hostname == host and re.search(r"(?i)over|about|wie-|team|organisatie|company|diensten|services", full) and full not in sources:
            try:
                got, page = fetch_public_page(full)
                pages.append(page.split("\n\nLINKS: ", 1)[0][:5000])
                sources.append(got)
            except ValueError:
                continue
    answer = studio._ask_json(_RESEARCH, "\n\n---\n\n".join(pages)[:16000])
    proposal = clean_profile(dict(answer, website=final))
    return {"proposal": proposal, "summary": _txt(answer.get("summary"), 300), "sources": sources}


# ── Personal intake: who you are, your tasks and how the agent should work with you ──
# The full intake stays here for Studio; a short entry goes into the person's
# user notes (personal USER.md, the "user profile" the agent reads in every
# conversation). Only that one entry is replaced; the person's own notes stay.

INTAKE_MARK = "Intake (Studio):"
USER_NOTE_LIMIT = 1375          # the agent's user_char_limit
INTAKE_NOTE_MAX = 700
SENIORITY = ("junior", "medior", "senior", "lead", "management")
WORK_TYPES = ("office", "hybrid", "remote", "field")
CADENCES = ("daily", "weekly", "monthly", "adhoc")
TASK_KINDS = ("automate", "assist", "human")
LANGS, TONES, LENGTHS, FORMATS = ("nl", "en"), ("informal", "formal"), ("short", "detailed"), ("bullets", "prose")
AI_LEVELS = ("beginner", "regular", "advanced")


def _person_file(email: str) -> str:
    import hashlib
    return "people/" + hashlib.sha256(str(email or "").lower().encode()).hexdigest()[:32] + ".json"


def load_person(email: str) -> dict:
    (_dir() / "people").mkdir(parents=True, exist_ok=True)
    return _read(_person_file(email), {})


def clean_person(raw: dict) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    role = raw.get("role") if isinstance(raw.get("role"), dict) else {}
    lst = lambda v, n, m: [x for x in (_txt(i, m) for i in (v if isinstance(v, list) else re.split(r"[,\n]", str(v or "")))[: n * 2]) if x][:n]
    out_role = {"title": _txt(role.get("title"), 100), "team": _txt(role.get("team"), 90), "speciality": _txt(role.get("speciality"), 100),
                "seniority": role.get("seniority") if role.get("seniority") in SENIORITY else "",
                "work_type": role.get("work_type") if role.get("work_type") in WORK_TYPES else "",
                "focus": lst(role.get("focus"), 6, 80), "responsibilities": lst(role.get("responsibilities"), 8, 120)}
    tasks = []
    for t in (raw.get("tasks") or [])[:20]:
        if not isinstance(t, dict) or not _txt(t.get("name")):
            continue
        tasks.append({"name": _txt(t.get("name"), 120), "cadence": t.get("cadence") if t.get("cadence") in CADENCES else "weekly",
                      "minutes": studio._int(t.get("minutes"), 0, 2400), "tools": lst(t.get("tools"), 6, 40),
                      "kind": t.get("kind") if t.get("kind") in TASK_KINDS else ""})
    prefs = raw.get("prefs") if isinstance(raw.get("prefs"), dict) else {}
    out_prefs = {"language": prefs.get("language") if prefs.get("language") in LANGS else "",
                 "tone": prefs.get("tone") if prefs.get("tone") in TONES else "",
                 "length": prefs.get("length") if prefs.get("length") in LENGTHS else "",
                 "format": prefs.get("format") if prefs.get("format") in FORMATS else "",
                 "hours": _txt(prefs.get("hours"), 80), "never": _txt(prefs.get("never"), 300), "notes": _txt(prefs.get("notes"), 300)}
    lit = raw.get("literacy") if isinstance(raw.get("literacy"), dict) else {}
    out_lit = {"self": lit.get("self") if lit.get("self") in AI_LEVELS else "", "score": studio._int(lit.get("score"), 0, 3),
               "answered": bool(lit.get("answered"))}
    return {"role": out_role, "tasks": tasks, "tools": lst(raw.get("tools"), 30, 40), "prefs": out_prefs, "literacy": out_lit}


_NL = {"seniority": {"junior": "junior", "medior": "medior", "senior": "senior", "lead": "teamlead", "management": "management"},
       "work_type": {"office": "op kantoor", "hybrid": "hybride", "remote": "op afstand", "field": "op locatie"},
       "cadence": {"daily": "dagelijks", "weekly": "wekelijks", "monthly": "maandelijks", "adhoc": "af en toe"},
       "language": {"nl": "Nederlands", "en": "Engels"}, "tone": {"informal": "informeel (je)", "formal": "formeel (u)"},
       "length": {"short": "kort en bondig", "detailed": "uitgebreid"}, "format": {"bullets": "opsommingen", "prose": "lopende tekst"},
       "ai": {"beginner": "beginner met AI", "regular": "gebruikt AI regelmatig", "advanced": "ervaren met AI"}}


def person_note(intake: dict, team_name: str = "") -> str:
    """One short user-notes entry the agent reads in every conversation."""
    r, p, t = intake.get("role") or {}, intake.get("prefs") or {}, intake.get("tasks") or []
    bits = []
    role = ", ".join(x for x in (r.get("title"), team_name, _NL["seniority"].get(r.get("seniority"), ""), r.get("speciality")) if x)
    if role:
        bits.append("Rol: " + role + ("; werkt " + _NL["work_type"][r["work_type"]] if r.get("work_type") else "") + ".")
    if r.get("focus"):
        bits.append("Focus: " + "; ".join(r["focus"][:4]) + ".")
    if t:
        bits.append("Terugkerend werk: " + "; ".join(f"{x['name']} ({_NL['cadence'][x['cadence']]})" for x in t[:5]) + ".")
    if intake.get("tools"):
        bits.append("Systemen: " + ", ".join(intake["tools"][:10]) + ".")
    pref = [x for x in (_NL["language"].get(p.get("language"), ""), _NL["tone"].get(p.get("tone"), ""),
                        _NL["length"].get(p.get("length"), ""), _NL["format"].get(p.get("format"), "")) if x]
    if pref:
        bits.append("Voorkeur in antwoorden: " + ", ".join(pref) + ".")
    if p.get("hours"):
        bits.append("Werktijden: " + p["hours"] + ".")
    if p.get("never"):
        bits.append("Nooit: " + p["never"] + ".")
    if p.get("notes"):
        bits.append(p["notes"] + ".")
    lvl = (intake.get("literacy") or {}).get("self")
    if lvl:
        bits.append("AI-ervaring: " + _NL["ai"][lvl] + ".")
    text = INTAKE_MARK + " " + " ".join(bits)
    text = re.sub(r"\.\.+", ".", text)
    return text[:INTAKE_NOTE_MAX].rstrip()


def save_person(view, identity, body: dict) -> dict:
    """Store the personal intake and write its short entry into the person's user notes."""
    from api import personal_context

    intake = clean_person(body)
    team_key = intake["role"]["team"]
    teams = org_structure.load().get("teams") or {}
    team_name = (teams.get(team_key) or {}).get("name") or ""
    note = person_note(intake, team_name)
    current = personal_context.read_file(personal_context.paths(identity)["user"])
    entries = [e for e in current.split("\n§\n") if e.strip()] if current.strip() else []
    entries = [e for e in entries if not e.strip().startswith(INTAKE_MARK)]
    own = sum(len(e) for e in entries) + max(0, len(entries)) * 3
    if own + len(note) > USER_NOTE_LIMIT:
        note = note[: max(160, USER_NOTE_LIMIT - own - 3)].rstrip()
    entries.append(note)
    personal_context.write(identity, "user", "\n§\n".join(entries))
    intake.update(updated_at=time.time(), email=view.email, note=note)
    with _LOCK:
        (_dir() / "people").mkdir(parents=True, exist_ok=True)
        _write(_person_file(view.email), intake)
    used = sum(len(e) for e in entries) + max(0, len(entries) - 1) * 3
    return dict(intake, notes_used=used, notes_limit=USER_NOTE_LIMIT)


def person_context_text(email: str) -> str:
    p = load_person(email)
    return p.get("note", "").replace(INTAKE_MARK, "").strip() if p else ""


_TASKS = """Je helpt iemand zijn terugkerende werk in kaart te brengen. Je krijgt een beschrijving van een werkweek.
Haal de concrete, terugkerende taken eruit (hooguit 10). Verzin niets: alleen wat genoemd wordt.
Per taak: name (kort, werkwoord vooraan), cadence (daily, weekly, monthly of adhoc), minutes (per keer, alleen als
het genoemd wordt of duidelijk volgt, anders 0), tools (systemen die bij die taak genoemd worden).
Alleen JSON: {"tasks": [{"name": "...", "cadence": "weekly", "minutes": 30, "tools": ["Excel"]}]}"""


def extract_tasks(text: str) -> list:
    text = str(text or "").strip()
    if len(text) < 10:
        raise ValueError("Describe your week first")
    answer = studio._ask_json(_TASKS, text[:6000])
    return clean_person({"tasks": answer.get("tasks") or []})["tasks"]

# ── HTTP ─────────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    view = org_structure.request_scope(handler)
    qs = parse_qs(parsed.query or "")
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        if parsed.path == "/api/studio/backlog":
            j(handler, {"items": backlog_for(view)})
        elif parsed.path == "/api/studio/playbooks":
            j(handler, {"playbooks": playbooks_for(view)})
        elif parsed.path == "/api/studio/prompts":
            j(handler, prompts_for(view))
        elif parsed.path == "/api/studio/profile" and (qs.get("who") or [""])[0] == "me":
            from api import personal_context
            from api.governance.enforce import _request_identity
            notes = personal_context.read_file(personal_context.paths(_request_identity(handler))["user"])
            data = org_structure.load()
            mine = sorted(view.member_teams | view.lead_teams)
            j(handler, dict(load_person(view.email), email=view.email, my_teams=mine,
                            teams=[{"key": k, "name": (t or {}).get("name") or k} for k, t in sorted((data.get("teams") or {}).items()) if isinstance(t, dict)],
                            org_systems=load_profile().get("systems") or [],
                            notes_used=len(notes), notes_limit=USER_NOTE_LIMIT))
        elif parsed.path == "/api/studio/profile":
            j(handler, dict(load_profile(), editable=view.scope == org_structure.SCOPE_ALL, context=context_text()))
        elif parsed.path == "/api/studio/playbook":
            pb = _pb_load((qs.get("id") or [""])[0])
            if not _pb_visible(view, pb):
                raise KeyError("Playbook not found")
            out = dict(pb, editable=_pb_editable(view, pb), stats=run_stats(pb))
            # Runs of other people stay private; the stats are enough.
            out["runs"] = [r for r in pb.get("runs") or [] if r.get("by") == view.email][-20:]
            j(handler, out)
        else:
            serve_media(handler, view, (qs.get("pb") or [""])[0], (qs.get("f") or [""])[0])
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    return True


def handle_post(handler, parsed, body) -> bool:
    view = org_structure.request_scope(handler)
    body = body if isinstance(body, dict) else {}
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        path = parsed.path
        if path == "/api/studio/backlog":
            j(handler, save_item(view, body))
        elif path == "/api/studio/backlog/order":
            reorder(view, [str(i) for i in (body.get("ids") or [])][:500])
            j(handler, {"ok": True})
        elif path == "/api/studio/autopilot":
            j(handler, autopilot(view, str(body.get("id") or "")))
        elif path == "/api/studio/playbook":
            j(handler, dict(save_playbook(view, body), editable=True))
        elif path == "/api/studio/prompts":
            j(handler, save_prompt(view, body))
        elif path == "/api/studio/profile":
            if body.get("op") == "research":
                j(handler, research_profile(view, body.get("url") or ""))
            elif body.get("op") == "me":
                from api.governance.enforce import _request_identity
                j(handler, save_person(view, _request_identity(handler), body))
            elif body.get("op") == "me_extract":
                j(handler, {"tasks": extract_tasks(body.get("text") or "")})
            else:
                j(handler, dict(save_profile(view, body), editable=True))
        elif path == "/api/studio/playbook/run":
            j(handler, record_run(view, body))
        elif path == "/api/studio/playbook/draft":
            j(handler, dict(draft_from_use_case(view, str(body.get("use_case") or "")), editable=True))
        elif path == "/api/studio/playbook/delete":
            pb = _pb_load(str(body.get("id") or ""))
            if not _pb_editable(view, pb):
                raise PermissionError("Only the author or an admin can delete this playbook")
            _pb_path(pb["id"]).unlink()
            j(handler, {"ok": True})
        else:
            j(handler, save_media(view, body))
    except PermissionError as e:
        j(handler, {"error": str(e)}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except RuntimeError as e:
        j(handler, {"error": str(e)}, status=502)
    except Exception:
        logger.exception("POST %s failed", parsed.path)
        j(handler, {"error": "internal_error"}, status=500)
    return True
