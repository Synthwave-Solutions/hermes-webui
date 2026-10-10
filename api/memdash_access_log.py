"""Who viewed my memories: the Memory explorer access log.

Plan addendum 6.6.8 (decision 10). ``STATE_DIR/memory_access_log.sqlite3``
(mode 0600) holds one row per administrator request on a store that is not
the requester's own personal store, appended before any data is returned, and
hash chained so a deleted or edited row is detected. It never holds memory
content or search text: the item a row names is stored as a hash.

It is the system of record for admin views (addendum 2.4): the person sees
their rows under Memory, Who viewed my memories; A6's export merges
``rows_for_subject()``; A9 appends rows for shared items through
``append()``; A13's notice card and A7's first-use card record
acknowledgements through ``ack_notice()``.

Chain: ``row_hash = sha256(prev_hash || canonical(row))`` over every column
except ``viewer_display``, the presentation name, which a leaver's
pseudonymisation rewrites (the viewer stays anchored by ``viewer_hash``). A
retention purge deletes old rows and writes a checkpoint with the hash of the
last purged row, so the remaining chain still verifies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

FILE_NAME = "memory_access_log.sqlite3"
GENESIS = "0" * 64
ROLES = ("platform_admin", "org_admin")
ACTIONS = ("open", "view", "item", "search", "edit", "forget", "meta")
REASON_CODES = ("none", "support", "safety", "quality", "asked", "other")
REASON_TEXT_MAX = 200
SESSION_GAP = timedelta(minutes=15)
DEFAULT_RETENTION_DAYS = 730
_HASH_RE = re.compile(r"^[0-9a-f]{24}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS access_log (
  id INTEGER PRIMARY KEY, at TEXT NOT NULL,
  viewer_hash TEXT NOT NULL, viewer_display TEXT NOT NULL,
  viewer_role TEXT NOT NULL CHECK (viewer_role IN ('platform_admin','org_admin')),
  subject_hash TEXT NOT NULL,
  store_ref TEXT NOT NULL, store_kind TEXT NOT NULL, org_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('open','view','item','search','edit','forget','meta')),
  reason_code TEXT NOT NULL DEFAULT 'none', reason_text TEXT NOT NULL DEFAULT '',
  item_id_hash TEXT NOT NULL DEFAULT '', outcome TEXT NOT NULL,
  prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS access_log_subject ON access_log (subject_hash, id);
CREATE INDEX IF NOT EXISTS access_log_store ON access_log (store_ref, id);
CREATE INDEX IF NOT EXISTS access_log_viewer ON access_log (viewer_hash, store_ref, id);
CREATE TABLE IF NOT EXISTS seen (subject_hash TEXT PRIMARY KEY, seen_until_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS notice_ack (email_hash TEXT PRIMARY KEY, version TEXT NOT NULL, acked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS checkpoints (
  id INTEGER PRIMARY KEY, at TEXT NOT NULL, purged_through_id INTEGER NOT NULL,
  last_purged_hash TEXT NOT NULL, rows_purged INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# Columns covered by the chain, in canonical order (viewer_display excluded).
_CHAIN_COLUMNS = (
    "id", "at", "viewer_hash", "viewer_role", "subject_hash", "store_ref", "store_kind",
    "org_id", "action", "reason_code", "reason_text", "item_id_hash", "outcome",
)
_ROW_COLUMNS = (
    "id", "at", "viewer_hash", "viewer_display", "viewer_role", "subject_hash", "store_ref",
    "store_kind", "org_id", "action", "reason_code", "reason_text", "item_id_hash", "outcome",
    "prev_hash", "row_hash",
)

_LOCK = threading.RLock()
_PATH_OVERRIDE: Path | None = None
_LAST_PURGE_CHECK: dict[str, datetime] = {}


class AccessLogError(RuntimeError):
    """The access log cannot be written or read; callers answer 503."""


def email_hash(email: str) -> str:
    """The governance audit's hash: sha256 of the lowercased email, 24 hex."""
    raw = str(email or "").strip().lower()
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def item_hash(item_id) -> str:
    raw = str(item_id or "").strip()
    if not raw:
        return ""
    return hashlib.sha256(("memdash-item|" + raw).encode("utf-8")).hexdigest()[:24]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def set_path(path: str | os.PathLike | None) -> None:
    """Point the log at another file (tests)."""
    global _PATH_OVERRIDE
    _PATH_OVERRIDE = Path(path) if path else None


def log_path() -> Path:
    if _PATH_OVERRIDE is not None:
        return _PATH_OVERRIDE
    from api.config import STATE_DIR

    return Path(STATE_DIR) / FILE_NAME


def _connect() -> sqlite3.Connection:
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass  # created earlier, or by another thread a moment ago
        os.chmod(path, 0o600)
        con = sqlite3.connect(str(path), timeout=5, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        con.executescript(_SCHEMA)
        for suffix in ("-wal", "-shm"):
            side = Path(str(path) + suffix)
            if side.exists():
                os.chmod(side, 0o600)
        return con
    except (OSError, sqlite3.Error) as exc:
        raise AccessLogError("the access log is not available") from exc


def _canonical(row: dict) -> bytes:
    return json.dumps([row[c] for c in _CHAIN_COLUMNS], ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _row_hash(prev_hash: str, row: dict) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + b"|" + _canonical(row)).hexdigest()


def clean_reason(code, text) -> tuple[str, str]:
    """A known reason code, and free text only with ``other`` (max 200)."""
    code = str(code or "none").strip().lower()
    if code not in REASON_CODES:
        code = "none"
    if code != "other":
        return code, ""
    value = _CONTROL_RE.sub(" ", str(text or "")).strip()
    value = re.sub(r"\s+", " ", value)[:REASON_TEXT_MAX]
    return code, value


@dataclass(frozen=True)
class Entry:
    viewer_email: str
    viewer_display: str
    viewer_role: str
    subject_email: str
    store_ref: str
    store_kind: str
    org_id: str
    action: str
    reason_code: str = "none"
    reason_text: str = ""
    item_id: str = ""
    outcome: str = "allowed"


def _last_hash(con: sqlite3.Connection) -> str:
    row = con.execute("SELECT row_hash FROM access_log ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        return row["row_hash"]
    checkpoint = con.execute("SELECT last_purged_hash FROM checkpoints ORDER BY id DESC LIMIT 1").fetchone()
    return checkpoint["last_purged_hash"] if checkpoint else GENESIS


def append(entry: Entry, *, subject_hash: str | None = None, now: datetime | None = None) -> int:
    """Append one row; raises ``AccessLogError`` when it cannot be written.

    ``subject_hash`` may be passed directly (A9 appends rows about an item's
    author); otherwise it is the hash of ``entry.subject_email`` ('' for a
    store that is not one person's).
    """
    if entry.viewer_role not in ROLES:
        raise AccessLogError("unknown viewer role")
    if entry.action not in ACTIONS:
        raise AccessLogError("unknown action")
    code, text = clean_reason(entry.reason_code, entry.reason_text)
    subject = email_hash(entry.subject_email) if subject_hash is None else str(subject_hash)
    if subject and not _HASH_RE.match(subject):
        raise AccessLogError("invalid subject hash")
    viewer = email_hash(entry.viewer_email)
    if not viewer:
        raise AccessLogError("no viewer")
    display = _CONTROL_RE.sub(" ", str(entry.viewer_display or "")).strip()[:120] or "Administrator"
    at = _iso(now or _utc_now())
    with _LOCK:
        con = _connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            prev = _last_hash(con)
            next_id = (con.execute("SELECT COALESCE(MAX(id), 0) FROM access_log").fetchone()[0] or 0) + 1
            checkpoint = con.execute("SELECT COALESCE(MAX(purged_through_id), 0) FROM checkpoints").fetchone()[0] or 0
            next_id = max(next_id, checkpoint + 1)
            row = {
                "id": next_id, "at": at, "viewer_hash": viewer, "viewer_display": display,
                "viewer_role": entry.viewer_role, "subject_hash": subject,
                "store_ref": str(entry.store_ref)[:80], "store_kind": str(entry.store_kind)[:20],
                "org_id": str(entry.org_id or "")[:60], "action": entry.action,
                "reason_code": code, "reason_text": text, "item_id_hash": item_hash(entry.item_id),
                "outcome": str(entry.outcome or "allowed")[:20], "prev_hash": prev,
            }
            row["row_hash"] = _row_hash(prev, row)
            con.execute(
                "INSERT INTO access_log (" + ",".join(_ROW_COLUMNS) + ") VALUES (" + ",".join("?" * len(_ROW_COLUMNS)) + ")",
                [row[c] for c in _ROW_COLUMNS],
            )
            con.execute("COMMIT")
            return next_id
        except sqlite3.Error as exc:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise AccessLogError("the access log could not be written") from exc
        finally:
            con.close()


def last_row_for(viewer_email: str, store_ref: str) -> dict | None:
    """The newest row of one viewer on one store (store sessions)."""
    if not _exists():
        return None
    with _LOCK:
        con = _connect()
        try:
            row = con.execute(
                "SELECT * FROM access_log WHERE viewer_hash=? AND store_ref=? ORDER BY id DESC LIMIT 1",
                (email_hash(viewer_email), str(store_ref)),
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be read") from exc
        finally:
            con.close()


def is_new_session(viewer_email: str, store_ref: str, *, now: datetime | None = None) -> bool:
    last = last_row_for(viewer_email, store_ref)
    if not last:
        return True
    try:
        return (now or _utc_now()) - _parse(last["at"]) > SESSION_GAP
    except ValueError:
        return True


def _public(row) -> dict:
    return {
        "id": row["id"], "at": row["at"], "viewer": row["viewer_display"], "role": row["viewer_role"],
        "store_kind": row["store_kind"], "action": row["action"], "reason_code": row["reason_code"],
        "reason_text": row["reason_text"], "outcome": row["outcome"],
    }


def _exists() -> bool:
    """Readers never create the log: no file means no rows."""
    try:
        return log_path().is_file()
    except OSError:
        return False


def _query(sql: str, params: tuple) -> list[dict]:
    if not _exists():
        return []
    with _LOCK:
        con = _connect()
        try:
            return [dict(r) for r in con.execute(sql, params).fetchall()]
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be read") from exc
        finally:
            con.close()


def rows_for_subject(email) -> list:
    """The access log rows about one person (A6's export, addendum 7.3).

    Content free: who viewed or changed the person's memories, when, with
    which role and reason. Never a row about anyone else. Returns ``[]`` when
    the log cannot be read, so an export never fails on it.
    """
    subject = email_hash(email)
    if not subject:
        return []
    try:
        rows = _query("SELECT * FROM access_log WHERE subject_hash=? ORDER BY id", (subject,))
    except AccessLogError:
        logger.warning("memdash access log unreadable for an export")
        return []
    return [_public(r) for r in rows]


def rows_for_store(store_ref: str, limit: int = 500) -> list[dict]:
    rows = _query("SELECT * FROM access_log WHERE store_ref=? ORDER BY id DESC LIMIT ?", (str(store_ref), int(limit)))
    return [_public(r) for r in rows]


def rows_all(limit: int = 500) -> list[dict]:
    rows = _query("SELECT * FROM access_log ORDER BY id DESC LIMIT ?", (int(limit),))
    out = []
    for r in rows:
        item = _public(r)
        item["store"] = r["store_ref"]
        item["mixed_or_shared"] = r["subject_hash"] == ""
        out.append(item)
    return out


def raw_rows_for_subject_hash(subject: str) -> list[dict]:
    return _query("SELECT * FROM access_log WHERE subject_hash=? ORDER BY id", (subject,))


def group_sessions(rows: list[dict]) -> list[dict]:
    """Group a subject's rows into viewing sessions.

    One session is one viewer's consecutive rows with gaps of at most 15
    minutes, across all the subject's stores. Newest session first.
    """
    by_viewer: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda r: r["id"]):
        by_viewer.setdefault(row["viewer_hash"], []).append(row)
    sessions: list[dict] = []
    for viewer_rows in by_viewer.values():
        current: dict | None = None
        last_at: datetime | None = None
        for row in viewer_rows:
            at = _parse(row["at"])
            if current is None or last_at is None or at - last_at > SESSION_GAP:
                current = {
                    "viewer": row["viewer_display"], "role": row["viewer_role"], "start": row["at"],
                    "end": row["at"], "views": 0, "items": 0, "searches": 0, "changed": 0,
                    "forgot": 0, "reason_code": "none", "reason_text": "", "first_id": row["id"],
                    "last_id": row["id"], "store_kinds": [],
                }
                sessions.append(current)
            current["end"] = row["at"]
            current["last_id"] = row["id"]
            current["viewer"] = row["viewer_display"]
            action = row["action"]
            if action in ("open", "view"):
                current["views"] += 1
            elif action == "item":
                current["items"] += 1
            elif action == "search":
                current["searches"] += 1
            elif action in ("edit", "meta"):
                current["changed"] += 1
            elif action == "forget":
                current["forgot"] += 1
            if row["reason_code"] and row["reason_code"] != "none":
                current["reason_code"] = row["reason_code"]
                current["reason_text"] = row["reason_text"]
            if row["store_kind"] not in current["store_kinds"]:
                current["store_kinds"].append(row["store_kind"])
            last_at = at
    sessions.sort(key=lambda s: (s["end"], s["last_id"]), reverse=True)
    return sessions


def subject_view(email: str) -> dict:
    """The data of Who viewed my memories for one person."""
    subject = email_hash(email)
    rows = raw_rows_for_subject_hash(subject) if subject else []
    seen_until = seen_until_id(email)
    sessions = group_sessions(rows)
    for session in sessions:
        session["new"] = session["last_id"] > seen_until
    unseen = sum(1 for r in rows if r["id"] > seen_until)
    last_id = max((r["id"] for r in rows), default=0)
    return {"sessions": sessions, "unseen": unseen, "last_id": last_id}


def seen_until_id(email: str) -> int:
    subject = email_hash(email)
    if not subject:
        return 0
    rows = _query("SELECT seen_until_id FROM seen WHERE subject_hash=?", (subject,))
    return int(rows[0]["seen_until_id"]) if rows else 0


def unseen_count(email: str) -> int:
    subject = email_hash(email)
    if not subject:
        return 0
    until = seen_until_id(email)
    rows = _query("SELECT COUNT(*) AS n FROM access_log WHERE subject_hash=? AND id>?", (subject, until))
    return int(rows[0]["n"]) if rows else 0


def mark_seen(email: str, until_id: int) -> int:
    subject = email_hash(email)
    if not subject:
        raise AccessLogError("no subject")
    with _LOCK:
        con = _connect()
        try:
            top = con.execute("SELECT COALESCE(MAX(id), 0) FROM access_log WHERE subject_hash=?", (subject,)).fetchone()[0] or 0
            value = max(0, min(int(until_id), int(top)))
            current = con.execute("SELECT seen_until_id FROM seen WHERE subject_hash=?", (subject,)).fetchone()
            if current and int(current["seen_until_id"]) >= value:
                return int(current["seen_until_id"])
            con.execute(
                "INSERT INTO seen (subject_hash, seen_until_id) VALUES (?, ?) "
                "ON CONFLICT(subject_hash) DO UPDATE SET seen_until_id=excluded.seen_until_id",
                (subject, value),
            )
            return value
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be written") from exc
        finally:
            con.close()


def ack_notice(email, version) -> None:
    """Record that a person acknowledged the memory notice (A13 and A7)."""
    subject = email_hash(email)
    version = str(version or "").strip()
    if not subject or not re.match(r"^[a-z0-9][a-z0-9._-]{0,39}$", version):
        raise AccessLogError("invalid acknowledgement")
    with _LOCK:
        con = _connect()
        try:
            con.execute(
                "INSERT INTO notice_ack (email_hash, version, acked_at) VALUES (?, ?, ?) "
                "ON CONFLICT(email_hash) DO UPDATE SET version=excluded.version, acked_at=excluded.acked_at",
                (subject, version, _iso(_utc_now())),
            )
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be written") from exc
        finally:
            con.close()


def notice_acked(email, version) -> bool:
    subject = email_hash(email)
    if not subject:
        return False
    rows = _query("SELECT version FROM notice_ack WHERE email_hash=?", (subject,))
    return bool(rows) and rows[0]["version"] == str(version)


def verify_chain() -> tuple[bool, str]:
    """Check every remaining row against the chain and the last checkpoint."""
    if not _exists():
        return True, "ok"
    with _LOCK:
        con = _connect()
        try:
            checkpoint = con.execute("SELECT * FROM checkpoints ORDER BY id DESC LIMIT 1").fetchone()
            prev = checkpoint["last_purged_hash"] if checkpoint else GENESIS
            expected_id = (checkpoint["purged_through_id"] + 1) if checkpoint else None
            for row in con.execute("SELECT * FROM access_log ORDER BY id"):
                data = dict(row)
                if expected_id is not None and data["id"] != expected_id:
                    return False, f"row {expected_id} is missing"
                if data["prev_hash"] != prev:
                    return False, f"row {data['id']} does not follow the previous row"
                if _row_hash(prev, data) != data["row_hash"]:
                    return False, f"row {data['id']} was changed"
                prev = data["row_hash"]
                expected_id = data["id"] + 1
            return True, "ok"
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be read") from exc
        finally:
            con.close()


def purge(retention_days: int = DEFAULT_RETENTION_DAYS, *, now: datetime | None = None) -> int:
    """Delete rows older than the retention and write a checkpoint."""
    days = max(1, int(retention_days))
    cutoff = _iso((now or _utc_now()) - timedelta(days=days))
    with _LOCK:
        con = _connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            last = con.execute(
                "SELECT id, row_hash FROM access_log WHERE at < ? ORDER BY id DESC LIMIT 1", (cutoff,)
            ).fetchone()
            if not last:
                con.execute("COMMIT")
                return 0
            count = con.execute("SELECT COUNT(*) FROM access_log WHERE id <= ?", (last["id"],)).fetchone()[0]
            con.execute("DELETE FROM access_log WHERE id <= ?", (last["id"],))
            con.execute(
                "INSERT INTO checkpoints (at, purged_through_id, last_purged_hash, rows_purged) VALUES (?, ?, ?, ?)",
                (_iso(now or _utc_now()), last["id"], last["row_hash"], count),
            )
            con.execute("COMMIT")
            return int(count)
        except sqlite3.Error as exc:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise AccessLogError("the access log could not be purged") from exc
        finally:
            con.close()


def purge_if_due(retention_days: int, *, now: datetime | None = None) -> None:
    """Run ``purge`` at most once a day per log file; never raises."""
    key = str(log_path())
    current = now or _utc_now()
    last = _LAST_PURGE_CHECK.get(key)
    if last and current - last < timedelta(days=1):
        return
    _LAST_PURGE_CHECK[key] = current
    try:
        purge(retention_days, now=now)
    except AccessLogError:
        logger.warning("memdash access log purge failed")


def pseudonymise_viewer(email: str, label: str = "Former administrator") -> int:
    """A leaver's name is replaced in the rows they wrote; rows are kept."""
    viewer = email_hash(email)
    if not viewer:
        return 0
    value = _CONTROL_RE.sub(" ", str(label or "")).strip()[:120] or "Former administrator"
    with _LOCK:
        con = _connect()
        try:
            cur = con.execute("UPDATE access_log SET viewer_display=? WHERE viewer_hash=?", (value, viewer))
            return int(cur.rowcount or 0)
        except sqlite3.Error as exc:
            raise AccessLogError("the access log could not be written") from exc
        finally:
            con.close()
