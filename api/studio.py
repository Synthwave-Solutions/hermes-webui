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
COMPONENT_TYPES = ("bot", "task", "skill", "human", "connection")
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
            rows.append({k: doc.get(k) for k in ("id", "title", "owner", "team", "phase", "updated_at", "created_at", "voice_session")}
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
    return [{"name": _txt(g.get("name"), 120), "kpi": _txt(g.get("kpi"), 160), "baseline": _txt(g.get("baseline"), 100),
             "target": _txt(g.get("target"), 100), "chosen": bool(g.get("chosen", True))}
            for g in (items or [])[:5] if isinstance(g, dict) and _txt(g.get("name"))]


def _clean_solution(s, opp_id, j, legacy=None) -> dict:
    s = s if isinstance(s, dict) else {}
    legacy = legacy or {}
    block = s.get("building_block") if s.get("building_block") in BLOCKS else (
        legacy.get("building_block") if legacy.get("building_block") in BLOCKS else "task")
    return {"id": _txt(s.get("id"), 24) or f"{opp_id}s{j + 1}",
            "title": _txt(s.get("title") or legacy.get("title"), 140),
            "building_block": block,
            "impact": _int(s.get("impact", legacy.get("impact", 3)), 1, 5),
            "effort": _int(s.get("effort", legacy.get("effort", 3)), 1, 5),
            "how": _txt(s.get("how") or legacy.get("why"), 300), "test": _txt(s.get("test"), 240)}


def clean_opportunities(items) -> list:
    """Opportunities (problem space) with solutions underneath (solution
    space). An old opportunity without solutions becomes one solution."""
    out = []
    for i, o in enumerate((items or [])[:12]):
        if not isinstance(o, dict) or not _txt(o.get("title")):
            continue
        opp_id = _txt(o.get("id"), 20) or f"o{i + 1}"
        raw = [s for s in (o.get("solutions") or []) if isinstance(s, dict) and _txt(s.get("title"))][:4]
        solutions = [_clean_solution(s, opp_id, j) for j, s in enumerate(raw)] or [_clean_solution({}, opp_id, 0, o)]
        seen = set()
        for j, s in enumerate(solutions):
            if s["id"] in seen or not s["id"].startswith(opp_id):
                s["id"] = f"{opp_id}s{j + 1}"
            seen.add(s["id"])
        out.append({"id": opp_id, "title": _txt(o.get("title"), 140), "goal": _txt(o.get("goal"), 120),
                    "pain": _txt(o.get("pain") or o.get("title"), 200), "cause": _txt(o.get("cause"), 200),
                    "solutions": solutions})
    return out


def selection(doc) -> tuple[dict | None, dict | None]:
    """(opportunity, solution) for ``doc.selected``: a solution id, or an
    opportunity id (its first solution)."""
    sel = str(doc.get("selected") or "")
    for o in doc.get("opportunities") or []:
        for s in o.get("solutions") or []:
            if s.get("id") == sel:
                return o, s
        if o.get("id") == sel:
            return o, (o.get("solutions") or [None])[0]
    return None, None


DATA_LEVELS = ("public", "internal", "confidential", "personal")
PER_WEEK = {"day": 5, "week": 1, "month": 12 / 52}


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
                row["replaces"] = sorted({_int(n, 1, 20) for n in (s.get("replaces") or [])[:10]
                                          if str(n).strip().lstrip("-").isdigit() and int(n) > 0})
            else:
                tools = s.get("tools") if isinstance(s.get("tools"), list) else []
                row["tools"] = [t for t in (_txt(t, 40) for t in tools[:5]) if t]
                row["pain"] = _txt(s.get("pain"), 200)
                row["decision"] = bool(s.get("decision"))
            out.append(row)
        return out

    metrics = [{"name": _txt(m.get("name"), 80), "baseline": _txt(m.get("baseline"), 100), "target": _txt(m.get("target"), 100)}
               for m in (raw.get("metrics") or [])[:3] if isinstance(m, dict) and _txt(m.get("name"))]
    freq = raw.get("frequency") if isinstance(raw.get("frequency"), dict) else {}
    frequency = {"count": _int(freq.get("count"), 0, 10000),
                 "per": freq.get("per") if freq.get("per") in PER_WEEK else "week"}
    data = raw.get("data_sensitivity") if raw.get("data_sensitivity") in DATA_LEVELS else ""
    as_is, to_be = steps(raw.get("as_is")), steps(raw.get("to_be"), True)
    return {"as_is": as_is, "to_be": to_be, "metrics": metrics, "frequency": frequency,
            "data_sensitivity": data, "data_note": _txt(raw.get("data_note"), 240) if data else "",
            "questions": [q for q in (_txt(q, 200) for q in (raw.get("questions") or [])[:3]) if q],
            "baseline": baseline(as_is, to_be, frequency),
            "description": str(raw.get("description") or "")[:MAX_TEXT]}


def baseline(as_is, to_be, frequency) -> dict:
    """Minutes per run before and after, and hours per week when the frequency is known."""
    before = sum(s.get("minutes") or 0 for s in as_is)
    after = sum(s.get("minutes") or 0 for s in to_be)
    runs = (frequency.get("count") or 0) * PER_WEEK.get(frequency.get("per") or "week", 1)
    out = {"minutes_before": before, "minutes_after": after, "runs_per_week": round(runs, 2)}
    if runs and before:
        out["hours_week_before"] = round(before * runs / 60, 1)
        out["hours_week_after"] = round(after * runs / 60, 1)
    return out


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
                        "prompt": str(c.get("prompt") or "")[:4000], "bot": _txt(c.get("bot"), 64).lower(),
                        "before_minutes": _int(c.get("before_minutes"), 0, 6000),
                        "review_minutes": _int(c.get("review_minutes"), 0, 6000), "per": per})
        elif c["type"] == "bot":
            row.update({"description": _txt(c.get("description"), 300),
                        "instructions": str(c.get("instructions") or "")[:4000]})
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
        if "voice_session" in body:
            sid = str(body.get("voice_session") or "")
            if sid and not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", sid):
                raise ValueError("Invalid session")
            doc["voice_session"] = sid
        if "ui_view" in body and body.get("ui_view") in ("matrix", "tree"):
            doc["ui_view"] = body["ui_view"]
        if "selected" in body:
            doc["selected"] = _txt(body.get("selected"), 24)
            if doc["selected"] and selection(doc) == (None, None):
                raise ValueError("Unknown opportunity or solution")
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

DISCOVER = """Je bent de AI-consultant van SynthPulse en maakt een opportunity solution tree (QuickScan).
Iemand vertelt over zijn werk. Bouw drie lagen, strikt gescheiden:

1. GEWENST DOEL (1 tot 3): de uitkomst die het team wil bereiken, in hun eigen taal. Meetbaar: een KPI met
   nulmeting en doelwaarde. Gebruik alleen getallen die de persoon noemt; anders "nulmeting nog bepalen"
   of "doelwaarde nog bepalen". De naam van het doel geeft de richting ("offertes sneller de deur uit"),
   zonder een getal of termijn die de persoon niet zelf noemde. Nulmeting en doelwaarde zijn kort: een getal
   met eenheid ("3 dagen", "15 per week"), geen zin.
   Een doel is nooit een oplossing ("minder openstaande facturen", niet "een bot die aanmaant").
2. KANSEN (2 tot 5): behoeften, knelpunten of wensen die het doel in de weg staan, geformuleerd vanuit de
   medewerker of klant ("ik verlies elke maandag twee uur aan nabellen"). Nog GEEN oplossing. Elke kans hoort
   bij precies één doel (veld goal = naam van dat doel) en heeft een korte oorzaak.
3. OPLOSSINGEN (1 tot 3 per kans): concreet wat de Super Agent, een bot of een geplande taak doet.
   - building_block: task (geplande taak), skill (werkwijze), bot (vaste AI-collega), connection (koppeling),
     human (blijft mens), custom (maatwerksoftware).
   - impact 1-5: bijdrage aan de KPI van het doel. effort 1-5: bouwen plus verandering voor het team.
   - how: in een zin hoe het werkt. test: het kleinste experiment om het te bewijzen (bijv. "een week lang
     concepten laten maken en vergelijken").
Verzin geen feiten. Ontbreekt informatie die de keuze verandert, zet dan 1 tot 3 korte vragen in "questions".
Antwoord in het Nederlands, alleen JSON:
{"title": "korte titel", "goals": [{"name": "...", "kpi": "...", "baseline": "...", "target": "..."}],
 "opportunities": [{"id": "o1", "goal": "<name van het doel>", "title": "...", "cause": "...",
   "solutions": [{"id": "o1s1", "title": "...", "building_block": "task", "impact": 4, "effort": 2,
                  "how": "...", "test": "..."}]}],
 "questions": ["..."]}"""

DESIGN = """Je bent de AI-consultant van SynthPulse en doet de Deep Dive op een gekozen oplossing.
Je krijgt het doel, de kans, de gekozen oplossing en wat de persoon vertelt over het huidige proces.

1. NULMETING: hoe vaak loopt dit proces (frequency: count plus per day/week/month). Gebruik alleen wat de persoon
   noemt; weet je het niet, zet count op 0 en stel er een vraag over.
2. ZOALS HET NU GAAT (as_is, 3 tot 10 stappen, in volgorde): per stap step (werkwoord vooraan), actor (mens of
   systeem), minutes per keer (schatting mag, wees realistisch), tools (systemen of bestanden die erbij gebruikt
   worden, zoals Excel, Outlook, Exact), pain (het knelpunt in die stap, leeg als er geen is) en decision (true als
   er in die stap een menselijke beslissing valt).
3. ZOALS HET WORDT (to_be): per stap step, actor (agent, mens of systeem), building_block (task, skill, bot,
   human, connection, custom), minutes (handwerk dat per keer overblijft, ook controle), replaces (nummers van de
   as_is-stappen die deze stap vervangt) en een korte note. Beslissingen blijven bij de mens: een stap met
   decision in as_is komt terug als stap voor een mens (human). De agent maakt concepten en verstuurt nooit zelf.
4. DATA: data_sensitivity is public, internal, confidential of personal (persoonsgegevens) met data_note (waarom,
   een zin). Bij personal: noem in de note welke gegevens het zijn.
5. METRICS (1 tot 3): sluit aan op de KPI van het doel; baseline en target kort, een getal met eenheid
   ("50 min", "3 dagen") of "nog bepalen", geen zin. Een target alleen als de persoon het noemde of als het
   volgt uit de minuten van to_be; anders "nog bepalen".
6. QUESTIONS (0 tot 3): wat je nog moet weten om het ontwerp te kunnen bouwen.

Nederlands, eenvoudige woorden. Alleen JSON:
{"frequency": {"count": 15, "per": "week"},
 "as_is": [{"step": "...", "actor": "mens", "minutes": 20, "tools": ["Word"], "pain": "...", "decision": false}],
 "to_be": [{"step": "...", "actor": "agent", "building_block": "task", "minutes": 5, "replaces": [1, 2], "note": "..."}],
 "data_sensitivity": "internal", "data_note": "...",
 "metrics": [{"name": "...", "baseline": "...", "target": "..."}], "questions": ["..."]}"""

PLAYBOOK = """Maak van het nieuwe proces een uitvoerbaar Playbook voor SynthPulse. Componenten:
- bot: alleen als het team een vaste AI-collega voor dit werk nodig heeft. Velden: name (bijv. "Debiteuren Bot"),
  description, instructions (de rol in de jij-vorm, wat hij wel en niet doet, verstuurt nooit zelf iets).
  Een task die door deze bot gedaan wordt, krijgt bot: <de name van de bot>.
- task: een geplande taak. Velden: name, schedule (cron, Europe/Amsterdam, binnen kantoortijden),
  prompt (zelfstandige opdracht voor de agent, Nederlands, verstuurt NOOIT iets naar anderen maar maakt concepten
  en levert in dit gesprek af), before_minutes en review_minutes (handwerk eerst en controle nu), per (run/day/week).
- skill: een werkwijze als Markdown. Velden: name (kort), description, content (SKILL-tekst met stappen).
- human: een stap die bij een mens blijft. Velden: name, who, what.
- connection: een benodigde koppeling. Velden: name, provider, why.
Gebruik de nulmeting voor before_minutes en review_minutes. Bij persoonsgegevens of vertrouwelijke data: de prompt
en de instructies zeggen dat de gegevens binnen SynthPulse blijven en alleen in concepten voor een mens staan.
Maximaal 7 componenten, alleen wat nodig is. Alleen JSON: {"components": [{"type": "task", "name": "...", ...}]}"""


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


_WORD = re.compile(r"[a-zà-ÿ0-9]{4,}")


_FILLER = {"agent", "maak", "maakt", "maken", "voor", "naar", "door", "wordt", "worden", "elke", "alle", "deze",
           "super", "skill", "taak", "with", "from", "that", "this", "synthwave", "synthpulse", "hermes"}


def _stems(text: str) -> set:
    """Lower-case words of four letters or more, with a plain Dutch or English plural cut off."""
    out = set()
    for w in _WORD.findall(str(text or "").lower()):
        if w in _FILLER:
            continue
        for suffix in ("en", "s"):
            if len(w) > 5 and w.endswith(suffix):
                w = w[: -len(suffix)]
                break
        out.add(w)
    return out


def _reuse_score(words: set, name: str) -> float:
    """How well an existing name fits: two shared words, or most of a short name.

    One shared word in a long name ("klant huisstijl document" for a quote
    about house style) is a coincidence, not something to reuse.
    """
    own = _stems(name)
    shared = len(words & own)
    if not shared:
        return 0
    coverage = shared / len(own)
    if shared >= 2 or coverage >= 0.5:
        return shared + coverage
    return 0


def _reuse_candidates(text: str, limit: int = 3) -> list[str]:
    """Existing tasks and skills whose names fit ``text`` well."""
    words = _stems(text)
    if not words:
        return []
    scored = []
    try:
        from api import value_tracking

        for _profile, job in value_tracking.iter_store_jobs():
            name = str(job.get("name") or "")
            score = _reuse_score(words, name)
            if score:
                scored.append((score, "Taak: " + name))
    except Exception:
        pass
    try:
        from api.profiles import get_hermes_home_for_profile

        skills_root = Path(get_hermes_home_for_profile("default")) / "skills"
        for skill in skills_root.glob("*/*/SKILL.md"):
            score = _reuse_score(words, skill.parent.name.replace("-", " "))
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
        opps = clean_opportunities(answer.get("opportunities"))
        n_sol = sum(len(o["solutions"]) for o in opps)
        questions = [_txt(q, 200) for q in (answer.get("questions") or []) if _txt(q, 200)][:3]
        text = f"{len(opps)} kansen met {n_sol} oplossingen. Kies een oplossing in de matrix of de boom."
        if questions:
            text += "\nOm het scherper te maken:\n" + "\n".join("• " + q for q in questions)
        update(view, {"id": doc["id"], "goals": answer.get("goals"), "opportunities": opps, "selected": "",
                      "title": doc.get("title") or answer.get("title") or "",
                      "notes": notes + [{"role": "agent", "text": text, "at": time.time()}]})
    elif step == "design":
        opp, sol = selection(doc)
        if not opp or not sol:
            raise ValueError("Choose a solution first")
        goal = next((g for g in doc.get("goals") or [] if g.get("name") == opp.get("goal")), {})
        answer = _ask_json(DESIGN, f"Doel: {goal.get('name') or opp.get('goal') or '-'} (KPI: {goal.get('kpi') or '-'})\n"
                                   f"Kans: {opp['title']} (oorzaak: {opp.get('cause') or '-'})\n"
                                   f"Gekozen oplossing: {sol['title']} [{sol['building_block']}]. Hoe: {sol.get('how') or '-'}\n"
                                   f"Eerder verteld (ook gebruiken voor de nulmeting):\n{history or '-'}\n"
                                   f"Huidig proces volgens de persoon:\n{text or history}")
        for s in answer.get("to_be") or []:
            if isinstance(s, dict) and s.get("building_block") in ("task", "skill", "bot"):
                s["reuse"] = _reuse_candidates(s.get("step", "") + " " + sol["title"])
        answer["description"] = text
        process = clean_process(answer)
        b = process["baseline"]
        msg = "Proces zoals het nu gaat en zoals het wordt staan klaar."
        if b.get("hours_week_before") is not None:
            nl = lambda v: f"{v:g}".replace(".", ",")
            msg += f" Nu {nl(b['hours_week_before'])} uur per week, straks {nl(b['hours_week_after'])} uur."
        if process["questions"]:
            msg += "\nNog nodig voor het bouwen:\n" + "\n".join("• " + q for q in process["questions"])
        else:
            msg += " Pas aan en ga door naar het bouwplan."
        update(view, {"id": doc["id"], "process": process, "phase": "design", "notes": notes + [
            {"role": "agent", "text": msg, "at": time.time()}]})
    elif step == "playbook":
        process = doc.get("process") or {}
        opp, sol = selection(doc)
        opp, sol = opp or {}, sol or {}
        to_be = "\n".join(f"- [{s.get('building_block')}] {s.get('step')} ({s.get('actor')}) {s.get('note') or ''}"
                          for s in process.get("to_be") or [])
        b = process.get("baseline") or {}
        freq = process.get("frequency") or {}
        data = process.get("data_sensitivity") or "onbekend"
        answer = _ask_json(PLAYBOOK, f"Kans: {opp.get('title')}\nOplossing: {sol.get('title')} (test: {sol.get('test') or '-'})\n"
                                     f"Team: {team_name or 'onbekend'}\nNieuw proces:\n{to_be}\n"
                                     f"Nulmeting: {b.get('minutes_before') or '?'} minuten handwerk per keer, straks "
                                     f"{b.get('minutes_after') or '?'}; {freq.get('count') or '?'} keer per {freq.get('per') or 'week'}\n"
                                     f"Gevoeligheid van de data: {data} ({process.get('data_note') or '-'})\n"
                                     f"Extra wensen: {text or 'geen'}")
        components = answer.get("components") or []
        for c in components:
            if isinstance(c, dict) and c.get("type") in ("task", "skill"):
                c["reuse"] = (_reuse_candidates(str(c.get("name") or "")) or [""])[0]
        update(view, {"id": doc["id"], "components": components, "phase": "playbook", "notes": notes + [
            {"role": "agent", "text": f"Bouwplan met {len(components)} onderdelen. Controleer en kies Droogrun.", "at": time.time()}]})
    else:
        raise ValueError("Unknown step")
    return _load(doc["id"])


# ── HTTP ─────────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    path = parsed.path
    if path in ("/api/studio/backlog", "/api/studio/playbooks", "/api/studio/playbook", "/api/studio/media"):
        from api import studio_library
        return studio_library.handle_get(handler, parsed)
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
    if path in ("/api/studio/backlog", "/api/studio/backlog/order", "/api/studio/autopilot", "/api/studio/playbook",
                "/api/studio/playbook/delete", "/api/studio/playbook/draft", "/api/studio/playbook/run", "/api/studio/media"):
        from api import studio_library
        return studio_library.handle_post(handler, parsed, body)
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


def for_voice_session(email: str, session_id: str) -> dict | None:
    """The caller's own use case whose live conversation is ``session_id``."""
    if not email or not session_id:
        return None
    for path in _dir().glob("uc_*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if doc.get("voice_session") == session_id and doc.get("owner") == email:
            return doc
    return None
