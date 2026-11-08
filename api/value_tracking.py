"""What a scheduled task or a bot saves: the work before against the work now.

Every job may carry a ``value`` block and every bot responsibility may carry
minutes before and now. This module validates those, keeps a ledger of what
actually ran, and computes the numbers the Organisation and Management
screens show.

Model
-----
    before   minutes of manual work per run (or per occurrence of a duty)
    now      minutes a person still spends per run (review, follow-up)
             + AI cost of the run (tokens x price, see pricing)
    saved    before - now, only for runs that completed

Three labels travel with every number and are never mixed silently:
``ai_estimate`` (a model guessed), ``confirmed`` (the owner said so) and
``measured`` (counted from runs). Failed runs cost money and save nothing.

Ledger
------
The engine keeps a short execution history per cron store
(``<home>/cron/executions.db``, pruned to about 1000 rows). ``collect()``
copies finished executions from every store into ``STATE_DIR/value/
value.db`` before they are pruned, with the job's value, team and bot as
they were at that moment, and the tokens of the run's session from the
store's ``state.db``. Bot chats are collected the same way from each
profile's ``state.db``. ``collect()`` is idempotent and cheap; the read
endpoints call it at most every few minutes.

Pricing
-------
Model routes here mostly run through OmniRoute combos and a subscription
bridge, so the engine records ``cost_status: unknown``. When a provider did
report a cost we use it (``cost_source: provider``). Otherwise the cost is
tokens times the price an administrator set per model in Management
(``cost_source: price_table``), shown as "API equivalent". Without a price
the cost is unknown and the screen says so instead of showing zero.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

VALUE_SOURCES = ("owner", "ai_estimate", "playbook", "workshop")
VALUE_CONFIDENCE = ("estimated", "confirmed")
# A frequent job (every few minutes) replaces work per day, not per run: then
# the saving counts once per day (or week) with at least one completed run.
VALUE_PER = ("run", "day", "week")
MINUTES_MAX = 6000
USD_TO_EUR = float(os.environ.get("SP_VALUE_USD_TO_EUR", "0.92"))
COLLECT_MIN_INTERVAL = int(os.environ.get("SP_VALUE_COLLECT_INTERVAL", "180"))
CHAT_SOURCES = ("webui", "api_server", "telegram", "slack", "teams", "gchat")
_COLLECT_LOCK = threading.Lock()
_last_collect = 0.0


# ── Validation ───────────────────────────────────────────────────────────────

def _minutes(value: Any, name: str) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number of minutes")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number of minutes")
    if number < 0 or number > MINUTES_MAX:
        raise ValueError(f"{name} must be between 0 and {MINUTES_MAX} minutes")
    return int(round(number))


def _text(value: Any, limit: int, name: str) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    text = " ".join(value.split())
    if len(text) > limit:
        raise ValueError(f"{name} is at most {limit} characters")
    return text


def validate_value(raw: Any) -> dict:
    """The normalized ``value`` block of a job. Raises ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("Value must be an object")
    allowed = {"task", "before_minutes", "review_minutes", "per", "source", "confidence", "rationale",
               "unknown", "unknown_reason", "team", "confirmed_by", "confirmed_at", "set_by", "set_at"}
    if set(raw) - allowed:
        raise ValueError("Unknown value field: " + ", ".join(sorted(set(raw) - allowed)))
    out: dict[str, Any] = {}
    if raw.get("unknown"):
        reason = _text(raw.get("unknown_reason"), 200, "Reason")
        if not reason:
            raise ValueError("Say why the value is unknown")
        out.update({"unknown": True, "unknown_reason": reason})
    else:
        out["before_minutes"] = _minutes(raw.get("before_minutes"), "Minutes before")
        out["review_minutes"] = _minutes(raw.get("review_minutes"), "Minutes now")
        if out["before_minutes"] <= 0:
            raise ValueError("Fill in how many minutes this took by hand, or mark the value as unknown")
    per = str(raw.get("per") or "run")
    if per not in VALUE_PER:
        raise ValueError("Per must be run, day or week")
    if not out.get("unknown"):
        out["per"] = per
    out["task"] = _text(raw.get("task"), 120, "Task")
    out["rationale"] = _text(raw.get("rationale"), 400, "Rationale")
    source = str(raw.get("source") or "owner")
    if source not in VALUE_SOURCES:
        raise ValueError("Unknown value source")
    out["source"] = source
    confidence = str(raw.get("confidence") or ("confirmed" if source == "owner" else "estimated"))
    if confidence not in VALUE_CONFIDENCE:
        raise ValueError("Unknown confidence")
    out["confidence"] = confidence
    team = str(raw.get("team") or "").strip()
    if team:
        from api import org_structure

        if team not in org_structure.team_keys():
            raise ValueError("Unknown team")
        out["team"] = team
    for key in ("confirmed_by", "confirmed_at", "set_by", "set_at"):
        if raw.get(key):
            out[key] = _text(raw.get(key), 120, key)
    return out


def job_value(job: dict) -> dict | None:
    value = (job or {}).get("value")
    if not isinstance(value, dict):
        return None
    try:
        return validate_value(value)
    except ValueError:
        return None


# ── Writing a job's value and team ───────────────────────────────────────────

def set_job_value(job_id: str, store_profile: str, value: dict | None, actor: str) -> dict:
    """Store (or clear with None) the value block on a job, in its own store.

    Same locking as ``cron_bots.assign_job``: the record stays where it is
    and the run itself does not change. Returns the saved job.
    """
    from api import cron_bots
    from api.profiles import cron_profile_context_for_home

    store = cron_bots.normalize_profile(store_profile)
    home = cron_bots.home_for_profile(store)
    clean = None
    if value is not None:
        clean = validate_value(value)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        clean["set_by"] = actor
        clean["set_at"] = now
        if clean.get("confidence") == "confirmed":
            clean["confirmed_by"] = actor
            clean["confirmed_at"] = now
    with cron_profile_context_for_home(home):
        import cron.jobs as cj

        with cron_bots._locked(cj):
            jobs = cj.load_jobs()
            match = next((j for j in jobs if str(j.get("id") or "") == str(job_id)), None)
            if match is None:
                raise KeyError("Job not found")
            if clean is None:
                match.pop("value", None)
            else:
                previous = match.get("value") if isinstance(match.get("value"), dict) else {}
                if "team" not in clean and previous.get("team"):
                    clean["team"] = previous["team"]
                match["value"] = clean
            cron_bots._save(cj, jobs)
            return dict(match)


def confirm_job_value(job_id: str, store_profile: str, answer: str, actor: str) -> dict:
    """Owner answers an estimate: yes / less / more / unknown."""
    from api import cron_bots

    job, _owner = cron_bots.find_job(job_id, store_profile)
    if job is None:
        raise KeyError("Job not found")
    current = job_value(job) or {}
    if answer not in ("yes", "less", "more"):
        raise ValueError("Answer yes, less or more")
    if not current or current.get("unknown"):
        raise ValueError("There is no estimate to confirm")
    before = current.get("before_minutes", 0)
    if answer == "less":
        before = max(1, int(round(before * 0.7)))
    elif answer == "more":
        before = int(round(before * 1.3)) + 1
    current.update({"before_minutes": before, "confidence": "confirmed"})
    return set_job_value(job_id, store_profile, current, actor)


# ── Ledger ───────────────────────────────────────────────────────────────────

def _db_path() -> Path:
    from api.config import STATE_DIR

    path = Path(STATE_DIR) / "value"
    path.mkdir(parents=True, exist_ok=True)
    return path / "value.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  exec_id TEXT PRIMARY KEY,
  store TEXT NOT NULL,
  job_id TEXT NOT NULL,
  job_name TEXT,
  bot TEXT,
  team TEXT,
  owner_email TEXT,
  status TEXT NOT NULL,
  started_at REAL,
  finished_at REAL,
  duration_s REAL,
  session_id TEXT,
  model TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  tokens_cache INTEGER DEFAULT 0,
  provider_cost_usd REAL,
  before_minutes INTEGER,
  review_minutes INTEGER,
  value_source TEXT,
  value_confidence TEXT,
  collected_at REAL
);
CREATE INDEX IF NOT EXISTS idx_runs_finished ON runs(finished_at);
CREATE INDEX IF NOT EXISTS idx_runs_job ON runs(job_id);
CREATE TABLE IF NOT EXISTS chats (
  session_key TEXT PRIMARY KEY,
  bot TEXT NOT NULL,
  session_id TEXT NOT NULL,
  user_hash TEXT,
  user_email TEXT,
  team TEXT,
  source TEXT,
  started_at REAL,
  last_at REAL,
  message_count INTEGER,
  model TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  tokens_cache INTEGER DEFAULT 0,
  provider_cost_usd REAL,
  title TEXT,
  duty TEXT,
  label_state TEXT DEFAULT 'none',
  saved_minutes INTEGER DEFAULT 0,
  collected_at REAL
);
CREATE INDEX IF NOT EXISTS idx_chats_started ON chats(started_at);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _readonly(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None


def _ts(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return None


def _meta_get(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _meta_set(conn, key: str, value: str) -> None:
    conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, value))


def _user_hash(email: str) -> str:
    return hashlib.sha256(("sp-value|" + (email or "").lower()).encode()).hexdigest()[:16] if email else ""


def _session_for_run(state: sqlite3.Connection | None, job_name: str, started: float | None,
                     finished: float | None) -> sqlite3.Row | None:
    """The cron session of one run: same job name in the title, inside the run."""
    if state is None or not job_name or started is None:
        return None
    lo = started - 180
    hi = (finished or started) + 120
    try:
        return state.execute(
            "SELECT id, model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, "
            "estimated_cost_usd, actual_cost_usd, cost_status FROM sessions "
            "WHERE source='cron' AND started_at BETWEEN ? AND ? AND (title=? OR title LIKE ?) "
            "ORDER BY ABS(started_at-?) LIMIT 1",
            (lo, hi, job_name, job_name + " ·%", started)).fetchone()
    except sqlite3.Error:
        return None


def _provider_cost(row) -> float | None:
    if row is None:
        return None
    for key in ("actual_cost_usd", "estimated_cost_usd"):
        try:
            value = row[key]
        except (IndexError, KeyError):
            value = None
        if value not in (None, 0, 0.0) and (row["cost_status"] or "") not in ("unknown", ""):
            return float(value)
    return None


def _job_team(job: dict, structure: dict) -> str:
    from api import org_structure

    value = job.get("value") if isinstance(job.get("value"), dict) else {}
    if value.get("team"):
        return value["team"]
    owner = org_structure.norm_email(job.get("owner_email") or (job.get("origin") or {}).get("user_id"))
    return org_structure.team_of(owner, structure) if owner else ""


def collect(force: bool = False) -> dict:
    """Copy finished runs and bot chats into the ledger. Idempotent."""
    global _last_collect
    if not force and time.time() - _last_collect < COLLECT_MIN_INTERVAL:
        return {"skipped": True}
    if not _COLLECT_LOCK.acquire(blocking=False):
        return {"skipped": True, "busy": True}
    try:
        from api import cron_bots, org_structure

        structure = org_structure.load()
        stats = {"runs": 0, "chats": 0, "stores": 0}
        conn = _connect()
        now = time.time()
        try:
            for profile, home in cron_bots.store_homes():
                stats["stores"] += 1
                home = Path(home)
                jobs = {str(j.get("id")): j for j in cron_bots.read_store_jobs(home) if isinstance(j, dict)}
                state = _readonly(home / "state.db")
                execs = _readonly(home / "cron" / "executions.db")
                try:
                    if execs is not None:
                        mark_key = f"exec_mark:{profile}"
                        mark = _meta_get(conn, mark_key, "")
                        rows = execs.execute(
                            "SELECT id, job_id, status, claimed_at, started_at, finished_at FROM executions "
                            "WHERE status IN ('completed','failed') AND finished_at IS NOT NULL AND claimed_at >= ? "
                            "ORDER BY claimed_at", (mark,)).fetchall()
                        newest = mark
                        for row in rows:
                            newest = max(newest, row["claimed_at"] or "")
                            exec_key = f"{profile}:{row['id']}"
                            if conn.execute("SELECT 1 FROM runs WHERE exec_id=?", (exec_key,)).fetchone():
                                continue
                            job = jobs.get(str(row["job_id"])) or {}
                            name = str(job.get("name") or "")
                            started, finished = _ts(row["started_at"]), _ts(row["finished_at"])
                            session = _session_for_run(state, name, started, finished)
                            value = job_value(job) or {}
                            conn.execute(
                                "INSERT OR IGNORE INTO runs(exec_id,store,job_id,job_name,bot,team,owner_email,status,"
                                "started_at,finished_at,duration_s,session_id,model,tokens_in,tokens_out,tokens_cache,"
                                "provider_cost_usd,before_minutes,review_minutes,value_source,value_confidence,collected_at)"
                                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (exec_key, profile, str(row["job_id"]), name,
                                 cron_bots.job_bot(job, profile) if job else profile,
                                 _job_team(job, structure) if job else "",
                                 org_structure.norm_email(job.get("owner_email")),
                                 "ok" if row["status"] == "completed" else "failed",
                                 started, finished, (finished - started) if started and finished else None,
                                 session["id"] if session else None,
                                 session["model"] if session else None,
                                 int(session["input_tokens"] or 0) if session else 0,
                                 int(session["output_tokens"] or 0) if session else 0,
                                 int((session["cache_read_tokens"] or 0) + (session["cache_write_tokens"] or 0)) if session else 0,
                                 _provider_cost(session),
                                 None if value.get("unknown") else value.get("before_minutes"),
                                 None if value.get("unknown") else value.get("review_minutes"),
                                 value.get("source"), value.get("confidence"), now))
                            stats["runs"] += 1
                        if newest != mark:
                            _meta_set(conn, mark_key, newest)
                    if state is not None:
                        stats["chats"] += _collect_chats(conn, state, profile, structure, now)
                finally:
                    for handle in (state, execs):
                        if handle is not None:
                            handle.close()
            _meta_set(conn, "last_collect", str(now))
            conn.commit()
        finally:
            conn.close()
        _last_collect = time.time()
        return stats
    finally:
        _COLLECT_LOCK.release()


def _collect_chats(conn, state, profile: str, structure: dict, now: float) -> int:
    from api import org_structure

    mark_key = f"chat_mark:{profile}"
    mark = float(_meta_get(conn, mark_key, "0") or 0)
    since = max(mark - 6 * 3600, now - 120 * 86400)
    placeholders = ",".join("?" * len(CHAT_SOURCES))
    try:
        rows = state.execute(
            f"SELECT id, source, user_id, model, started_at, last_activity_at, ended_at, message_count, "
            f"input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, estimated_cost_usd, "
            f"actual_cost_usd, cost_status, title FROM sessions WHERE source IN ({placeholders}) "
            f"AND COALESCE(last_activity_at, ended_at, started_at) >= ? AND COALESCE(message_count,0) > 0",
            (*CHAT_SOURCES, since)).fetchall()
    except sqlite3.Error:
        return 0
    count = 0
    newest = mark
    for row in rows:
        last = float(row["last_activity_at"] or row["ended_at"] or row["started_at"] or 0)
        newest = max(newest, last)
        email = org_structure.norm_email(row["user_id"])
        key = f"{profile}:{row['id']}"
        existing = conn.execute("SELECT label_state, duty, saved_minutes FROM chats WHERE session_key=?", (key,)).fetchone()
        conn.execute(
            "INSERT INTO chats(session_key,bot,session_id,user_hash,user_email,team,source,started_at,last_at,"
            "message_count,model,tokens_in,tokens_out,tokens_cache,provider_cost_usd,title,collected_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(session_key) DO UPDATE SET "
            "last_at=excluded.last_at, message_count=excluded.message_count, model=excluded.model, "
            "tokens_in=excluded.tokens_in, tokens_out=excluded.tokens_out, tokens_cache=excluded.tokens_cache, "
            "provider_cost_usd=excluded.provider_cost_usd, title=excluded.title, collected_at=excluded.collected_at",
            (key, profile, row["id"], _user_hash(email), email,
             org_structure.team_of(email, structure) if email else "", row["source"],
             row["started_at"], last, row["message_count"], row["model"],
             int(row["input_tokens"] or 0), int(row["output_tokens"] or 0),
             int((row["cache_read_tokens"] or 0) + (row["cache_write_tokens"] or 0)),
             _provider_cost(row), (row["title"] or "")[:200], now))
        if existing is None:
            count += 1
    if newest > mark:
        _meta_set(conn, mark_key, str(newest))
    return count


def label_chat(session_key: str, duty: str, actor_email: str, saved_minutes: int | None = None) -> dict:
    """The person who had the chat says which duty it covered (or none)."""
    from api import org_structure

    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM chats WHERE session_key=?", (session_key,)).fetchone()
        if row is None:
            raise KeyError("Chat not found")
        if (row["user_email"] or "") != org_structure.norm_email(actor_email):
            raise PermissionError("Only the person who had this chat can label it")
        duty = _text(duty, 80, "Duty")
        minutes = 0
        if duty:
            minutes = _minutes(saved_minutes, "Minutes saved") if saved_minutes is not None else _duty_saving(row["bot"], duty)
        conn.execute("UPDATE chats SET duty=?, label_state=?, saved_minutes=? WHERE session_key=?",
                     (duty or None, "confirmed" if duty else "removed", minutes, session_key))
        conn.commit()
        return dict(conn.execute("SELECT * FROM chats WHERE session_key=?", (session_key,)).fetchone())
    finally:
        conn.close()


# ── Bots: duties with minutes ────────────────────────────────────────────────

def bot_duties(bot: str) -> list[dict]:
    try:
        from api.bot_metadata import read_profile

        return list(((read_profile(bot) or {}).get("bot") or {}).get("responsibilities") or [])
    except Exception:
        return []


def _duty_saving(bot: str, duty_title: str) -> int:
    for duty in bot_duties(bot):
        if duty.get("title") == duty_title:
            return max(0, int(duty.get("minutes_before") or 0) - int(duty.get("minutes_now") or 0))
    return 0


def bot_estimate_per_week(bot: str) -> dict:
    """Sum over duties of (before - now) x times per week. Estimate only."""
    minutes = 0
    covered = 0
    duties = bot_duties(bot)
    for duty in duties:
        before = int(duty.get("minutes_before") or 0)
        if before <= 0:
            continue
        covered += 1
        per_week = float(duty.get("times_per_week") or 0)
        minutes += max(0, before - int(duty.get("minutes_now") or 0)) * per_week
    return {"minutes_per_week": int(round(minutes)), "duties": len(duties), "duties_with_value": covered,
            "confirmed": all(d.get("value_confidence") == "confirmed" for d in duties if d.get("minutes_before"))
            and covered > 0}


# ── Pricing ──────────────────────────────────────────────────────────────────

def _pricing_path() -> Path:
    return _db_path().parent / "pricing.json"


def load_pricing() -> dict:
    """``{"models": {model: {"in": eur/M, "out": eur/M, "cache": eur/M}}, "updated_at", "updated_by"}``"""
    try:
        data = json.loads(_pricing_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("models"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"models": {}, "updated_at": None, "updated_by": None}


def save_pricing(models: dict, actor: str) -> dict:
    if not isinstance(models, dict) or len(models) > 100:
        raise ValueError("Invalid price table")
    clean = {}
    for model, row in models.items():
        name = _text(model, 120, "Model")
        if not name or not isinstance(row, dict):
            raise ValueError("Invalid price row")
        entry = {}
        for key in ("in", "out", "cache"):
            value = row.get(key, 0)
            try:
                number = float(value or 0)
            except (TypeError, ValueError):
                raise ValueError(f"Price {key} of {name} must be a number")
            if number < 0 or number > 10000:
                raise ValueError(f"Price {key} of {name} out of range")
            entry[key] = round(number, 4)
        clean[name] = entry
    data = {"models": clean, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "updated_by": actor}
    tmp = _pricing_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, _pricing_path())
    return data


def ai_cost_eur(model: str | None, tokens_in: int, tokens_out: int, tokens_cache: int,
                provider_cost_usd: float | None, pricing: dict) -> tuple[float | None, str]:
    """``(eur, source)`` with source provider | price_table | unknown | none."""
    if provider_cost_usd:
        return round(provider_cost_usd * USD_TO_EUR, 4), "provider"
    if not (tokens_in or tokens_out or tokens_cache):
        return 0.0, "none"
    price = (pricing.get("models") or {}).get(model or "") or (pricing.get("models") or {}).get("*")
    if not price:
        return None, "unknown"
    eur = (tokens_in * price.get("in", 0) + tokens_out * price.get("out", 0) + tokens_cache * price.get("cache", 0)) / 1_000_000
    return round(eur, 4), "price_table"


# ── Queries ──────────────────────────────────────────────────────────────────

def runs_between(start: float, end: float) -> list[dict]:
    conn = _connect()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM runs WHERE finished_at >= ? AND finished_at < ?", (start, end))]
    finally:
        conn.close()


def chats_between(start: float, end: float) -> list[dict]:
    conn = _connect()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM chats WHERE last_at >= ? AND last_at < ?", (start, end))]
    finally:
        conn.close()


def ledger_since() -> float | None:
    """When the earliest run in the ledger finished: measuring starts there."""
    conn = _connect()
    try:
        row = conn.execute("SELECT MIN(finished_at) AS m FROM runs").fetchone()
        return float(row["m"]) if row and row["m"] else None
    finally:
        conn.close()


def last_collect_at() -> float | None:
    conn = _connect()
    try:
        value = _meta_get(conn, "last_collect", "")
        return float(value) if value else None
    finally:
        conn.close()


def run_money(run: dict, rate: float | None, pricing: dict) -> dict:
    """Per-run figures: saved minutes, AI cost, net EUR (None when unknown)."""
    ok = run.get("status") == "ok"
    before = run.get("before_minutes")
    review = run.get("review_minutes") or 0
    has_value = before is not None
    saved = max(0, before - review) if (ok and has_value) else 0
    cost, cost_source = ai_cost_eur(run.get("model"), run.get("tokens_in") or 0, run.get("tokens_out") or 0,
                                    run.get("tokens_cache") or 0, run.get("provider_cost_usd"), pricing)
    net = None
    if rate is not None and has_value:
        net = round(saved / 60 * rate - (cost or 0), 2)
    return {"saved_minutes": saved, "has_value": has_value, "ai_cost_eur": cost, "cost_source": cost_source,
            "net_eur": net, "review_minutes": review if ok else 0}


def iter_store_jobs() -> Iterable[tuple[str, dict]]:
    from api import cron_bots

    for profile, home in cron_bots.store_homes():
        for job in cron_bots.read_store_jobs(home):
            if isinstance(job, dict):
                yield profile, job


# ── Labelling bot chats ──────────────────────────────────────────────────────
# A finished chat with a bot that has responsibilities with minutes gets one
# label: which responsibility it covered, or none. A cheap model decides from
# the chat title and the first user message. The label counts as an estimate
# (``label_state: auto``) until the person confirms or corrects it.
LABEL_BATCH = int(os.environ.get("SP_VALUE_LABEL_BATCH", "20"))
LABEL_MODEL = os.environ.get("SP_VALUE_LABEL_MODEL", "synthwave-auto")
LABEL_IDLE_SECONDS = 1800


def _omniroute_key() -> str:
    key = os.environ.get("OMNIROUTE_API_KEY", "")
    if key:
        return key
    try:
        from api.profiles import get_hermes_home_for_profile

        env = Path(get_hermes_home_for_profile("default")) / ".env"
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("OMNIROUTE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _ask_label(duties: list[dict], title: str, first: str) -> str | None:
    """The duty title the chat covered, "" for none, None when unsure/failed."""
    import urllib.request

    names = [d["title"] for d in duties]
    system = ("Je krijgt een gesprek met een AI-bot en de lijst verantwoordelijkheden van die bot. "
              "Kies de ene verantwoordelijkheid die dit gesprek afhandelde, of 'geen'. "
              "Antwoord alleen met de exacte titel uit de lijst, of met: geen.")
    user = "Verantwoordelijkheden:\n" + "\n".join("- " + n for n in names) + f"\n\nTitel: {title}\nEerste vraag: {first[:800]}"
    body = json.dumps({"model": LABEL_MODEL, "temperature": 0, "max_tokens": 40, "stream": False,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    headers = {"Content-Type": "application/json"}
    key = _omniroute_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=60) as resp:
            raw = resp.read().decode()
    except Exception:
        return None
    text = ""
    raw = raw.strip()
    try:
        if raw.startswith("{"):
            text = json.loads(raw)["choices"][0]["message"]["content"] or ""
        else:
            for line in raw.splitlines():
                if line.startswith("data:") and line[5:].strip() not in ("", "[DONE]"):
                    chunk = json.loads(line[5:].strip())
                    for choice in chunk.get("choices") or []:
                        text += (choice.get("delta") or {}).get("content") or ""
    except ValueError:
        return None
    text = text.strip().strip(".").strip('"').strip()
    if text.lower() in ("geen", "none", ""):
        return ""
    for name in names:
        if text.lower() == name.lower():
            return name
    return None


def label_chats(limit: int = LABEL_BATCH) -> int:
    """Label up to ``limit`` finished, unlabelled chats of bots whose duties
    carry minutes. Returns how many were labelled."""
    from api import cron_bots

    duties_by_bot = {}
    conn = _connect()
    done = 0
    try:
        rows = conn.execute(
            "SELECT session_key, bot, session_id, title FROM chats WHERE label_state='none' AND last_at < ? "
            "ORDER BY last_at DESC LIMIT ?", (time.time() - LABEL_IDLE_SECONDS, limit * 5)).fetchall()
        homes = dict(cron_bots.store_homes())
        for row in rows:
            if done >= limit:
                break
            bot = row["bot"]
            if bot not in duties_by_bot:
                duties_by_bot[bot] = [d for d in bot_duties(bot) if int(d.get("minutes_before") or 0) > 0]
            duties = duties_by_bot[bot]
            if not duties:
                conn.execute("UPDATE chats SET label_state='skipped' WHERE session_key=?", (row["session_key"],))
                continue
            first = ""
            state = _readonly(Path(homes.get(bot, "")) / "state.db") if homes.get(bot) else None
            if state is not None:
                try:
                    hit = state.execute("SELECT content FROM messages WHERE session_id=? AND role='user' "
                                        "ORDER BY timestamp, id LIMIT 1", (row["session_id"],)).fetchone()
                    first = str(hit["content"] or "") if hit else ""
                except sqlite3.Error:
                    first = ""
                finally:
                    state.close()
            label = _ask_label(duties, row["title"] or "", first)
            if label is None:
                continue
            minutes = 0
            if label:
                duty = next(d for d in duties if d["title"] == label)
                minutes = max(0, int(duty.get("minutes_before") or 0) - int(duty.get("minutes_now") or 0))
            conn.execute("UPDATE chats SET duty=?, label_state=?, saved_minutes=? WHERE session_key=?",
                         (label or None, "auto" if label else "auto_none", minutes, row["session_key"]))
            done += 1
        conn.commit()
    finally:
        conn.close()
    return done


# ── Background collector ─────────────────────────────────────────────────────
# The engine prunes each store's execution history to about 1000 rows, which
# in a busy store is half a day. Collect on a timer so no run is lost when
# nobody opens Management for a while.
_COLLECTOR_THREAD = None
_COLLECTOR_STOP = threading.Event()
COLLECTOR_INTERVAL = int(os.environ.get("SP_VALUE_COLLECTOR_INTERVAL", "600"))


def _collector_loop() -> None:
    _COLLECTOR_STOP.wait(30)
    while not _COLLECTOR_STOP.is_set():
        try:
            collect(force=True)
        except Exception:
            logger.warning("value collector run failed", exc_info=True)
        if os.environ.get("SP_VALUE_LABELER", "1") != "0":
            try:
                label_chats()
            except Exception:
                logger.warning("value chat labelling failed", exc_info=True)
        _COLLECTOR_STOP.wait(max(60, COLLECTOR_INTERVAL))


def start_collector_thread() -> bool:
    """Start the collector daemon (idempotent). Off with SP_VALUE_COLLECTOR=0."""
    global _COLLECTOR_THREAD
    if os.environ.get("SP_VALUE_COLLECTOR", "1") == "0":
        return False
    if _COLLECTOR_THREAD is not None and _COLLECTOR_THREAD.is_alive():
        return False
    _COLLECTOR_STOP.clear()
    _COLLECTOR_THREAD = threading.Thread(target=_collector_loop, daemon=True, name="value-collector")
    _COLLECTOR_THREAD.start()
    return True


def stop_collector_thread(timeout: float = 2.0) -> None:
    global _COLLECTOR_THREAD
    thread, _COLLECTOR_THREAD = _COLLECTOR_THREAD, None
    _COLLECTOR_STOP.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=timeout)
