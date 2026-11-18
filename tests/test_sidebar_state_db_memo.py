"""The sidebar's state.db overrides are remembered briefly per set of rows."""
import api.models as models


def test_memo_reuses_and_expires(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(models, "_read_state_db_sidebar_overrides",
                        lambda db, ids, count_session_ids=None: calls.append(set(ids)) or {"a": {"x": len(calls)}})
    monkeypatch.setattr(models, "_SIDEBAR_STATE_DB_MEMO", {})
    db = tmp_path / "state.db"
    db.write_text("1")
    clock = [1000.0]
    monkeypatch.setattr(models.time, "monotonic", lambda: clock[0])
    get = lambda ids: models._sidebar_state_db_overrides_memoized(db, set(ids), None)
    assert get("ab") == {"a": {"x": 1}} and get("ab") == {"a": {"x": 1}} and len(calls) == 1
    get("abc")
    assert len(calls) == 2
    clock[0] += 200          # unchanged database: still valid
    get("ab")
    assert len(calls) == 2
    db.write_text("22")      # changed database, past the short window: read again
    get("ab")
    assert len(calls) == 3
    clock[0] += 3            # changed again but inside the short window: reuse
    db.write_text("333")
    get("ab")
    assert len(calls) == 3
    monkeypatch.setenv("HERMES_WEBUI_STATE_DB_OVERRIDE_MEMO_SECONDS", "0")
    get("ab")
    assert len(calls) == 4
