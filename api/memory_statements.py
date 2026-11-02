"""Separate human statements from imported reference scaffolding and encoded media."""

import json
import re

# These are complete, generated skill-loader messages, not task-keyword rules.
SKILL_PREFIX = "Base directory for this skill:"
BLOB = re.compile(r"(?:data:[\w.+/-]+;base64,)?([A-Za-z0-9+/]{512,}={0,2})")


def clean_statement(content):
    value = str(content or "")
    if value.lstrip().startswith(SKILL_PREFIX):
        return ""

    def remove_blob(match):
        token = match.group(1)
        # Preserve legitimate long repeated text; encoded binary spans have a
        # broad alphabet and no word boundaries. Keep surrounding human text.
        if len(set(token)) >= 24 and (
            "+" in token or "/" in token or any(c.isdigit() for c in token)
        ):
            return ""
        return match.group(0)

    return BLOB.sub(remove_blob, value).strip()


def _origin(row):
    meta = json.loads(row["metadata_json"] or "{}")
    if (
        meta.get("kind") == "historical_user_statement"
        and not meta.get("owner_edited")
        and "message_index" in meta
        and meta.get("chat")
    ):
        return (meta["chat"], meta["message_index"])
    return None


def _reference_groups(rows):
    return {
        _origin(r)
        for r in rows
        if r["content"].lstrip().startswith(SKILL_PREFIX)
        or json.loads(r["metadata_json"] or "{}").get("reference_type")
        == "skill_loader"
    } - {None}


def tag_reference_chunks(db):
    """Retain provenance even if the first chunk of a reference is later deleted."""
    rows = db.execute(
        "SELECT id,content,metadata_json FROM working_memory WHERE session_id='personal' AND json_extract(metadata_json,'$.kind')='historical_user_statement'"
    ).fetchall()
    groups = _reference_groups(rows)
    for row in rows:
        if _origin(row) in groups:
            meta = json.loads(row["metadata_json"] or "{}")
            if meta.get("reference_type") != "skill_loader":
                meta["reference_type"] = "skill_loader"
                db.execute(
                    "UPDATE working_memory SET metadata_json=? WHERE id=?",
                    (json.dumps(meta), row["id"]),
                )
    db.commit()


def statement_rows(rows):
    """Exclude reference imports; an explicit owner edit can make one a statement."""
    rows = list(rows)
    reference_messages = _reference_groups(rows)
    for row in rows:
        meta = json.loads(row["metadata_json"] or "{}")
        if _origin(row) in reference_messages or (
            meta.get("reference_type") == "skill_loader"
            and not meta.get("owner_edited")
        ):
            continue
        content = clean_statement(row["content"])
        if content:
            yield row, content
