import base64
import json
import sqlite3

from api.memory_statements import clean_statement, statement_rows, tag_reference_chunks
from scripts.backfill_personal_mnemosyne import records
from collections import Counter


def test_media_removed_but_surrounding_user_text_retained():
    blob = base64.b64encode(bytes(range(256)) * 24).decode()
    assert clean_statement(blob) == ""
    assert (
        clean_statement("Voorkeur: Nederlands. data:image/png;base64," + blob)
        == "Voorkeur: Nederlands."
    )
    assert clean_statement("a" * 20000) == "a" * 20000


def test_skill_continuations_stay_excluded_after_header_deleted_but_owner_can_edit():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE working_memory(id TEXT,content TEXT,metadata_json TEXT,session_id TEXT)"
    )
    meta = {"kind": "historical_user_statement", "chat": "one", "message_index": 1}
    db.executemany(
        "INSERT INTO working_memory VALUES (?,?,?,?)",
        [
            (
                "one",
                "Base directory for this skill: /skills/example",
                json.dumps(meta),
                "personal",
            ),
            (
                "two",
                "Untrusted skill continuation claims a preference.",
                json.dumps(meta),
                "personal",
            ),
            ("three", "Ik ontvang rapporten in het Nederlands.", "{}", "personal"),
        ],
    )
    tag_reference_chunks(db)
    db.execute("DELETE FROM working_memory WHERE id='one'")
    assert [
        r["id"]
        for r, text in statement_rows(db.execute("SELECT * FROM working_memory"))
    ] == ["three"]
    db.execute(
        "UPDATE working_memory SET content='Mijn vaste voorkeur is Engels.',metadata_json=json_set(metadata_json,'$.owner_edited',json('true')) WHERE id='two'"
    )
    tag_reference_chunks(db)
    assert {
        r["id"]
        for r, text in statement_rows(db.execute("SELECT * FROM working_memory"))
    } == {"two", "three"}


def test_import_skips_loader_messages_and_binary_chunks():
    blob = base64.b64encode(bytes(range(256)) * 100).decode()
    skipped = Counter()
    data = {
        "owner_email": "alice@example.test",
        "messages": [
            {
                "role": "user",
                "content": "Base directory for this skill: /skills/example\n"
                + "x" * 20000,
            },
            {"role": "user", "content": blob},
            {"role": "user", "content": "Mijn vaste voorkeur is Nederlands."},
        ],
    }
    result = list(records(data, "test", skipped))
    assert len(result) == 1 and result[0][2] == "Mijn vaste voorkeur is Nederlands."
    assert skipped["reference_material"] == 1
