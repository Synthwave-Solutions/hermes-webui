"""Use Case Studio: discover, design, playbook, build (8 Nov 2026).

The thinking of SynthDrive's QuickScan and Deep Dive, as a SynthPulse
screen: a person describes their work, the model proposes goals, pain points
and opportunities (impact and effort), the person picks one and describes
the process as it is, the model proposes the process as it should be with a
building block per step, and that becomes a Playbook of components (skills,
scheduled tasks with their value, human steps, connections).

Building happens in the browser through the existing routes, under the
person's own rights and governance (``/api/skills/save``,
``/api/crons/create`` paused and with its value and team, ``/api/kanban/
tasks``). This module stores use cases and runs the three model steps.

Storage: ``STATE_DIR/studio/<id>.json``, one document per use case with its
owner. A person sees their own use cases; organisation admins see all,
department admins those of teams in their departments.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs

from api import org_structure
from api.helpers import j

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ID_RE = re.compile(r"^uc_[a-f0-9]{12}$")
PHASES = ("discover", "design", "playbook", "build", "measure")
BLOCKS = ("task", "skill", "bot", "human", "connection", "custom")
COMPONENT_TYPES = ("task", "skill", "human", "connection")
MAX_TEXT = 6000


def _dir() -> Path:
    from api.config import STATE_DIR

    path = Path(STATE_DIR) / "studio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(uc_id: str) -> Path:
    if not _ID_RE.match(str(uc_id or "")):
        raise KeyError("Use case not found")
    return _dir() / f"{uc_id}.json"


def _load(uc_id: str) -> dict:
    try:
        return json.loads(_path(uc_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise KeyError("Use case not found")


def _save(doc: dict) -> dict:
    doc["updated_at"] = time.time()
    path = _path(doc["id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return doc


def _visible(view: org_structure.ViewScope, doc: dict) -> bool:
    if view.scope == org_structure.SCOPE_ALL or doc.get("owner") == view.email:
        return True
    team = doc.get("team") or ""
    return bool(team) and view.scope == org_structure.SCOPE_DEPARTMENTS and view.edits_team(team)


def _editable(view, doc) -> bool:
    return doc.get("owner") == view.email or view.scope == org_structure.SCOPE_ALL


def list_for(view) -> list[dict]:
    rows = []
    for path in sorted(_dir().glob("uc_*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if _visible(view, doc):
            rows.append({k: doc.get(k) for k in ("id", "title", "owner", "team", "phase", "updated_at", "created_at")}
                        | {"components": len(((doc.get("playbook") or {}).get("components") or [])),
                           "built": sum(1 for b in doc.get("build_log") or [] if b.get("status") == "ok")})
    return sorted(rows, key=lambda r: -(r.get("updated_at") or 0))


# ── Validation of what the browser stores ────────────────────────────────────

def _txt(value, limit=400) -> str:
    return " ".join(str(value or "").split())[:limit]


def _int(value, lo=0, hi=6000) -> int:
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return lo


def clean_goals(items) -> list:
    return [{"name": _txt(g.get("name"), 120), "kpi": _txt(g.get("kpi"), 160), "chosen": bool(g.get("chosen", True))}
            for g in (items or [])[:8] if isinstance(g, dict) and _txt(g.get("name"))]


def clean_opportunities(items) -> list:
    out = []
    for i, o in enumerate((items or [])[:20]):
        if not isinstance(o, dict) or not _txt(o.get("title")):
            continue
        block = o.get("building_block") if o.get("building_block") in BLOCKS else "task"
        out.append({"id": _txt(o.get("id"), 20) or f"o{i + 1}", "title": _txt(o.get("title"), 140),
                    "why": _txt(o.get("why"), 300), "pain": _txt(o.get("pain"), 200),
                    "impact": _int(o.get("impact"), 1, 5), "effort": _int(o.get("effort"), 1, 5),
                    "building_block": block})
    return out


def clean_process(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}

    def steps(items, to_be=False):
        out = []
        for s in (items or [])[:20]:
            if not isinstance(s, dict) or not _txt(s.get("step")):
                continue
            row = {"step": _txt(s.get("step"), 160), "actor": _txt(s.get("actor"), 40) or "mens",
                   "minutes": _int(s.get("minutes"), 0, 6000)}
            if to_be:
                row["building_block"] = s.get("building_block") if s.get("building_block") in BLOCKS else "human"
                row["note"] = _txt(s.get("note"), 240)
                row["reuse"] = [_txt(r, 120) for r in (s.get("reuse") or [])[:3]]
            out.append(row)
        return out

    metrics = [{"name": _txt(m.get("name"), 80), "baseline": _txt(m.get("baseline"), 40), "target": _txt(m.get("target"), 40)}
               for m in (raw.get("metrics") or [])[:3] if isinstance(m, dict) and _txt(m.get("name"))]
    return {"as_is": steps(raw.get("as_is")), "to_be": steps(raw.get("to_be"), True), "metrics": metrics,
            "description": str(raw.get("description") or "")[:MAX_TEXT]}


_SLUG = re.compile(r"[^a-z0-9]+")


def clean_components(items) -> list:
    out = []
    seen = set()
    for c in (items or [])[:12]:
        if not isinstance(c, dict) or c.get("type") not in COMPONENT_TYPES:
            continue
        key = _SLUG.sub("-", str(c.get("key") or c.get("name") or "").lower()).strip("-")[:48] or f"c{len(out) + 1}"
        if key in seen:
            key = f"{key}-{len(out) + 1}"
        seen.add(key)
        row = {"key": key, "type": c["type"], "name": _txt(c.get("name"), 100), "include": c.get("include", True) is not False,
               "reuse": _txt(c.get("reuse"), 120)}
        if c["type"] == "task":
            per = c.get("per") if c.get("per") in ("run", "day", "week") else "run"
            row.update({"schedule": _txt(c.get("schedule"), 60) or "0 8 * * 1",
                        "prompt": str(c.get("prompt") or "")[:4000], "bot": _txt(c.get("bot"), 64),
                        "before_minutes": _int(c.get("before_minutes"), 0, 6000),
                        "review_minutes": _int(c.get("review_minutes"), 0, 6000), "per": per})
        elif c["type"] == "skill":
            row.update({"description": _txt(c.get("description"), 300), "content": str(c.get("content") or "")[:12000]})
        elif c["type"] == "human":
            row.update({"who": _txt(c.get("who"), 120), "what": _txt(c.get("what"), 300)})
        elif c["type"] == "connection":
            row.update({"provider": _txt(c.get("provider"), 60), "why": _txt(c.get("why"), 200)})
        out.append(row)
    return out


def update(view, body: dict) -> dict:
    uc_id = str(body.get("id") or "")
    with _LOCK:
        if not uc_id:
            doc = {"id": "uc_" + secrets.token_hex(6), "owner": view.email, "created_at": time.time(),
                   "title": "", "team": "", "phase": "discover", "notes": [], "goals": [], "opportunities": [],
                   "selected": "", "process": {}, "playbook": {"version": 0, "components": []}, "build_log": []}
        else:
            doc = _load(uc_id)
            if not _editable(view, doc):
                raise PermissionError("Only the owner can change this use case")
        if "title" in body:
            doc["title"] = _txt(body.get("title"), 120)
        if "team" in body:
            team = str(body.get("team") or "")
            if team and team not in org_structure.team_keys():
                raise ValueError("Unknown team")
            doc["team"] = team
        if "phase" in body and body.get("phase") in PHASES:
            doc["phase"] = body["phase"]
        if "notes" in body:
            doc["notes"] = [{"role": n.get("role") if n.get("role") in ("user", "agent") else "user",
                             "text": str(n.get("text") or "")[:MAX_TEXT], "at": n.get("at") or time.time()}
                            for n in (body.get("notes") or [])[-40:] if isinstance(n, dict)]
        if "goals" in body:
            doc["goals"] = clean_goals(body.get("goals"))
        if "opportunities" in body:
            doc["opportunities"] = clean_opportunities(body.get("opportunities"))
        if "selected" in body:
            doc["selected"] = _txt(body.get("selected"), 20)
        if "process" in body:
            doc["process"] = clean_process(body.get("process"))
        if "components" in body:
            pb = doc.get("playbook") or {"version": 0}
            doc["playbook"] = {"version": int(pb.get("version") or 0) + 1, "components": clean_components(body.get("components")),
                               "saved_at": time.time(), "saved_by": view.email}
        if "build_log" in body:
            doc["build_log"] = [{"key": _txt(b.get("key"), 48), "type": _txt(b.get("type"), 20),
                                 "status": b.get("status") if b.get("status") in ("ok", "failed", "skipped") else "failed",
                                 "ref": _txt(b.get("ref"), 200), "error": _txt(b.get("error"), 300), "at": b.get("at") or time.time()}
                                for b in (body.get("build_log") or [])[:40] if isinstance(b, dict)]
        return _save(doc)


# ── Model steps ──────────────────────────────────────────────────────────────

DISCOVER = """Je bent de AI-consultant van SynthPulse. Iemand beschrijft zijn werk. Zoek waar AI echt helpt.
Geef 2 tot 4 doelen (met een meetbare KPI), en 3 tot 6 kansen. Een kans is concreet werk dat een agent kan
overnemen of ondersteunen. Per kans: impact 1-5, moeite 1-5, het knelpunt dat het oplost, waarom, en de
bouwsteen: task (geplande taak), skill (werkwijze/kennis), bot (vaste AI-collega), human (blijft mens),
connection (koppeling met een systeem), custom (maatwerksoftware). Antwoord in het Nederlands, alleen JSON:
{"title": "korte titel", "goals": [{"name": "...", "kpi": "..."}],
 "opportunities": [{"id": "o1", "title": "...", "pain": "...", "why": "...", "impact": 4, "effort": 2, "building_block": "task"}]}"""

DESIGN = """Je ontwerpt een werkproces opnieuw met AI. Gegeven de gekozen kans en de beschrijving van het huidige
proces: maak het proces zoals het nu is (as_is: stap, actor mens/systeem, minuten per keer) en zoals het wordt
(to_be: stap, actor agent/mens/systeem, building_block task/skill/bot/human/connection/custom, korte note).
Houd menselijke beslissingen bij de mens. Geef 1 tot 3 metrics met nulmeting en doel. Nederlands, alleen JSON:
{"as_is": [{"step": "...", "actor": "mens", "minutes": 20}], "to_be": [{"step": "...", "actor": "agent",
 "building_block": "task", "note": "..."}], "metrics": [{"name": "...", "baseline": "...", "target": "..."}]}"""

PLAYBOOK = """Maak van het nieuwe proces een uitvoerbaar Playbook voor SynthPulse. Componenten:
- task: een geplande taak. Velden: name, schedule (cron, Europe/Amsterdam, binnen kantoortijden),
  prompt (zelfstandige opdracht voor de agent, Nederlands, verstuurt NOOIT iets naar anderen maar maakt concepten
  en levert in dit gesprek af), before_minutes en review_minutes (handwerk eerst en controle nu), per (run/day/week).
- skill: een werkwijze als Markdown. Velden: name (kort), description, content (SKILL-tekst met stappen).
- human: een stap die bij een mens blijft. Velden: name, who, what.
- connection: een benodigde koppeling. Velden: name, provider, why.
Maximaal 6 componenten, alleen wat nodig is. Alleen JSON: {"components": [{"type": "task", "name": "...", ...}]}"""


def _ask_json(system: str, user: str) -> dict:
    """One structured model call through OmniRoute; raises RuntimeError."""
    import urllib.request

    from api.value_tracking import _omniroute_key

    url = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions")
    model = os.environ.get("SP_STUDIO_MODEL", "synthwave-auto")
    body = json.dumps({"model": model, "temperature": 0.2, "max_tokens": 3000, "stream": False,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    headers = {"Content-Type": "application/json"}
    key = _omniroute_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    last = "no answer"
    for _ in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=180) as resp:
                raw = resp.read().decode()
            text = ""
            raw = raw.strip()
            if raw.startswith("{"):
                text = json.loads(raw)["choices"][0]["message"]["content"] or ""
            else:
                for line in raw.splitlines():
                    if line.startswith("data:") and line[5:].strip() not in ("", "[DONE]"):
                        for choice in json.loads(line[5:].strip()).get("choices") or []:
                            text += (choice.get("delta") or {}).get("content") or ""
            start = text.find("{")
            if start >= 0:
                obj, _end = json.JSONDecoder().raw_decode(text[start:])
                if isinstance(obj, dict):
                    return obj
            last = "answer was not JSON"
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:200]
    raise RuntimeError("The model did not answer usefully (" + last + "). Your input is kept; try again.")


def _reuse_candidates(text: str, limit: int = 3) -> list[str]:
    """Existing tasks and skills whose names share words with ``text``."""
    words = {w for w in re.findall(r"[a-zà-ÿ0-9]{4,}", text.lower())}
    if not words:
        return []
    scored = []
    try:
        from api import value_tracking

        for _profile, job in value_tracking.iter_store_jobs():
            name = str(job.get("name") or "")
            score = len(words & set(re.findall(r"[a-zà-ÿ0-9]{4,}", name.lower())))
            if score:
                scored.append((score, "Taak: " + name))
    except Exception:
        pass
    try:
        from api.profiles import get_hermes_home_for_profile

        skills_root = Path(get_hermes_home_for_profile("default")) / "skills"
        for skill in skills_root.glob("*/*/SKILL.md"):
            name = skill.parent.name.replace("-", " ")
            score = len(words & set(re.findall(r"[a-zà-ÿ0-9]{4,}", name.lower())))
            if score:
                scored.append((score, "Skill: " + skill.parent.name))
    except Exception:
        pass
    scored.sort(key=lambda s: -s[0])
    out = []
    for _s, label in scored:
        if label not in out:
            out.append(label)
        if len(out) >= limit:
            break
    return out


def run_step(view, body: dict) -> dict:
    doc = _load(str(body.get("id") or ""))
    if not _editable(view, doc):
        raise PermissionError("Only the owner can change this use case")
    step = body.get("step")
    text = str(body.get("input") or "").strip()[:MAX_TEXT]
    team_name = ""
    if doc.get("team"):
        team_name = ((org_structure.load().get("teams") or {}).get(doc["team"]) or {}).get("name") or doc["team"]
    notes = list(doc.get("notes") or [])
    if text:
        notes.append({"role": "user", "text": text, "at": time.time()})
    history = "\n".join(f"- {n['text']}" for n in notes if n.get("role") == "user")[-MAX_TEXT:]
    if step == "discover":
        answer = _ask_json(DISCOVER, f"Team: {team_name or 'onbekend'}\nWat de persoon vertelt:\n{history}")
        update(view, {"id": doc["id"], "goals": answer.get("goals"), "opportunities": answer.get("opportunities"),
                      "title": doc.get("title") or answer.get("title") or "", "notes": notes + [
                          {"role": "agent", "text": f"{len(answer.get('opportunities') or [])} kansen gevonden. Kies er één in de matrix.",
                           "at": time.time()}]})
    elif step == "design":
        opp = next((o for o in doc.get("opportunities") or [] if o.get("id") == doc.get("selected")), None)
        if not opp:
            raise ValueError("Choose an opportunity first")
        answer = _ask_json(DESIGN, f"Kans: {opp['title']}\nKnelpunt: {opp.get('pain')}\nWaarom: {opp.get('why')}\n"
                                   f"Huidig proces volgens de persoon:\n{text or history}")
        for s in answer.get("to_be") or []:
            if isinstance(s, dict) and s.get("building_block") in ("task", "skill", "bot"):
                s["reuse"] = _reuse_candidates(s.get("step", "") + " " + opp["title"])
        answer["description"] = text
        update(view, {"id": doc["id"], "process": answer, "phase": "design", "notes": notes + [
            {"role": "agent", "text": "Proces as-is en to-be staan klaar. Pas aan en ga door naar het Playbook.", "at": time.time()}]})
    elif step == "playbook":
        process = doc.get("process") or {}
        opp = next((o for o in doc.get("opportunities") or [] if o.get("id") == doc.get("selected")), {})
        to_be = "\n".join(f"- [{s.get('building_block')}] {s.get('step')} ({s.get('actor')}) {s.get('note') or ''}"
                          for s in process.get("to_be") or [])
        answer = _ask_json(PLAYBOOK, f"Kans: {opp.get('title')}\nTeam: {team_name or 'onbekend'}\nNieuw proces:\n{to_be}\n"
                                     f"Extra wensen: {text or 'geen'}")
        components = answer.get("components") or []
        for c in components:
            if isinstance(c, dict) and c.get("type") in ("task", "skill"):
                c["reuse"] = (_reuse_candidates(str(c.get("name") or "")) or [""])[0]
        update(view, {"id": doc["id"], "components": components, "phase": "playbook", "notes": notes + [
            {"role": "agent", "text": f"Playbook met {len(components)} onderdelen. Controleer en kies Droogrun.", "at": time.time()}]})
    else:
        raise ValueError("Unknown step")
    return _load(doc["id"])


# ── HTTP ─────────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    path = parsed.path
    if path not in ("/api/studio/usecases", "/api/studio/usecase"):
        return False
    view = org_structure.request_scope(handler)
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        if path == "/api/studio/usecases":
            j(handler, {"usecases": list_for(view), "viewer": view.to_dict(),
                        "teams": [{"key": k, "name": (t or {}).get("name") or k}
                                  for k, t in sorted((org_structure.load().get("teams") or {}).items())]})
            return True
        doc = _load((parse_qs(parsed.query or "").get("id") or [""])[0])
        if not _visible(view, doc):
            raise KeyError("Use case not found")
        j(handler, dict(doc, editable=_editable(view, doc)))
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    return True


def handle_post(handler, parsed, body) -> bool:
    path = parsed.path
    if path not in ("/api/studio/usecase", "/api/studio/step", "/api/studio/delete"):
        return False
    view = org_structure.request_scope(handler)
    body = body if isinstance(body, dict) else {}
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        if path == "/api/studio/usecase":
            j(handler, dict(update(view, body), editable=True))
        elif path == "/api/studio/step":
            j(handler, dict(run_step(view, body), editable=True))
        else:
            doc = _load(str(body.get("id") or ""))
            if not _editable(view, doc):
                raise PermissionError("Only the owner can delete this use case")
            _path(doc["id"]).unlink()
            j(handler, {"ok": True})
    except PermissionError as e:
        j(handler, {"error": str(e)}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except RuntimeError as e:
        j(handler, {"error": str(e)}, status=502)
    except Exception:
        logger.exception("POST %s failed", path)
        j(handler, {"error": "internal_error"}, status=500)
    return True
