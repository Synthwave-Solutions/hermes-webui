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
