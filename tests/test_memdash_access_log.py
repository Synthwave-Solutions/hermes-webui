"""The Memory explorer access log (addendum 6.6.8, decision 10).

Every administrator request on a store that is not the requester's own is
written before any data leaves, content free and hash chained; the person
sees their rows under Who viewed my memories; the governance audit mirrors it.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))

import memdash_harness as H  # noqa: E402
from api import memdash_access_log as log  # noqa: E402


@pytest.fixture
def env(monkeypatch, tmp_path):
    environment = H.Env(monkeypatch, tmp_path)
    yield environment
    environment.close()


@pytest.fixture
def plain_log(tmp_path):
    log.set_path(tmp_path / "log.sqlite3")
    yield tmp_path / "log.sqlite3"
    log.set_path(None)


def _entry(**changes):
    data = dict(viewer_email=H.YASER, viewer_display="Yaser", viewer_role="platform_admin",
                subject_email=H.ADA, store_ref="b_" + "1" * 32, store_kind="personal", org_id="",
                action="view")
    data.update(changes)
    return log.Entry(**data)


def _ada_ref(env):
    return env.ref_of(lambda s: s.store_id == "hub:u-ada")


def test_the_row_is_written_before_any_data_and_a_failed_write_gives_503(env, monkeypatch):
    env.as_user(H.YASER, "Yaser")
    ref = _ada_ref(env)
    order = []
    real_append = log.append
    real_view = env.backends.InterimSqliteBackend.view

    def spy_append(*args, **kwargs):
        order.append("log")
        return real_append(*args, **kwargs)

    def spy_view(self, *args, **kwargs):
        order.append("data")
        return real_view(self, *args, **kwargs)

    monkeypatch.setattr(log, "append", spy_append)
    monkeypatch.setattr(env.backends.InterimSqliteBackend, "view", spy_view)
    assert env.view(ref, "stats").status == 200
    assert order == ["log", "data"]

    def failing(*args, **kwargs):
        raise log.AccessLogError("disk full")

    order.clear()
    monkeypatch.setattr(log, "append", failing)
    response = env.view(ref, "memories", q="option")
    assert response.status == 503
    assert "items" not in response.raw.decode()
    assert order == []


def test_no_memory_content_and_no_search_text_reach_the_log_or_the_audit(env):
    env.as_user(H.YASER, "Yaser")
    ref = _ada_ref(env)
    search = "SEARCH-CANARY-51d0"
    assert env.view(ref, "stats").status == 200
    found = env.view(ref, "search", q=H.CANARY)
    assert found.status == 200 and H.CANARY in found.raw.decode()  # the admin sees the content...
    assert env.view(ref, "memories", q=search).status == 200
    memory = env.view(ref, "memory", id="ada-e0")
    assert memory.status == 200
    blob = b""
    for path in env.state.iterdir():
        if path.name.startswith("memory_access_log.sqlite3"):
            blob += path.read_bytes()
    audit = (env.hermes_home / "dashboard-governance-audit.jsonl").read_bytes()
    for secret in (H.CANARY, search, "ada-e0", "option"):
        assert secret.encode() not in blob, secret  # ...the log never does
        assert secret.encode() not in audit, secret
    rows = log.rows_for_subject(H.ADA)
    assert [r["action"] for r in rows] == ["open", "search", "search", "item"]


def test_the_chain_verifies_and_a_deleted_or_edited_row_is_detected(plain_log):
    for action in ("open", "view", "search", "item"):
        log.append(_entry(action=action))
    assert log.verify_chain() == (True, "ok")
    con = sqlite3.connect(plain_log)
    con.execute("UPDATE access_log SET reason_code='support' WHERE id=2")
    con.commit()
    ok, why = log.verify_chain()
    assert not ok and "row 2 was changed" in why
    con.execute("UPDATE access_log SET reason_code='none' WHERE id=2")
    con.execute("DELETE FROM access_log WHERE id=3")
    con.commit()
    con.close()
    ok, why = log.verify_chain()
    assert not ok and "row 3 is missing" in why


def test_the_log_file_is_owner_only(plain_log):
    log.append(_entry())
    assert (plain_log.stat().st_mode & 0o777) == 0o600


def test_rows_group_into_sessions_with_a_fifteen_minute_gap(plain_log):
    start = datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc)
    log.append(_entry(action="open", reason_code="support"), now=start)
    log.append(_entry(action="view"), now=start + timedelta(minutes=5))
    log.append(_entry(action="search"), now=start + timedelta(minutes=10))
    log.append(_entry(action="item"), now=start + timedelta(minutes=19))
    log.append(_entry(action="open"), now=start + timedelta(minutes=40))
    log.append(_entry(action="edit", reason_code="other", reason_text="Asked\x00 to fix\n a typo"),
               now=start + timedelta(minutes=41))
    log.append(_entry(viewer_email=H.ODIS, viewer_display="Odis", action="open"), now=start + timedelta(minutes=2))
    view = log.subject_view(H.ADA)
    sessions = view["sessions"]
    assert len(sessions) == 3
    newest = sessions[0]
    assert (newest["viewer"], newest["views"], newest["changed"]) == ("Yaser", 1, 1)
    assert newest["reason_code"] == "other" and newest["reason_text"] == "Asked to fix a typo"
    first = next(s for s in sessions if s["viewer"] == "Yaser" and s["views"] == 2)
    assert (first["searches"], first["items"], first["reason_code"]) == (1, 1, "support")
    assert first["start"].startswith("2026-09-28T09:00") and first["end"].startswith("2026-09-28T09:19")
    assert any(s["viewer"] == "Odis" for s in sessions)
    assert view["unseen"] == 7


def test_the_subject_sees_only_their_rows_across_all_their_stores(env):
    env.as_user(H.YASER, "Yaser")
    hub = _ada_ref(env)
    profile = env.ref_of(lambda s: s.store_id == "profile:ada:u-ada")
    bob = env.ref_of(lambda s: s.store_id == "hub:u-bob")
    for ref in (hub, profile, bob):
        assert env.view(ref, "stats").status == 200
    env.as_user(H.ADA, "Ada Lovelace")
    mine = env.get("/api/memdash/access-log?scope=me").body
    assert mine["unseen"] == 2 and len(mine["sessions"]) == 1
    assert mine["sessions"][0]["views"] == 2 and mine["sessions"][0]["viewer"] == "Yaser"
    assert len(log.rows_for_subject(H.ADA)) == 2
    assert len(log.rows_for_subject(H.BOB)) == 1
    assert log.rows_for_subject("nobody@example.test") == []
    # Marking seen clears the count, only for the subject.
    assert env.post("/api/memdash/access-log/seen", {"until_id": mine["last_id"]}).status == 200
    assert env.get("/api/memdash/access-log?scope=me").body["unseen"] == 0
    env.as_user(H.BOB, "Bob")
    assert env.get("/api/memdash/access-log?scope=me").body["unseen"] == 1


def test_self_views_are_never_logged(env):
    env.as_user(H.ADA, "Ada Lovelace")
    for view in ("stats", "memories", "search", "graph"):
        assert env.view("me", view, q="option").status == 200
    own_profile = env.ref_of(lambda s: s.store_id == "profile:ada:u-ada")
    assert env.view(own_profile, "stats").status == 200
    assert log.rows_all() == []
    env.as_user(H.MICHAEL, "Michael")
    assert env.view("me", "stats").status == 200
    assert log.rows_all() == []


def test_a_mixed_store_view_is_logged_with_an_empty_subject_and_listed_under_all(env):
    env.as_user(H.YASER, "Yaser")
    custom = env.ref_of(lambda s: s.store_id.startswith("extra:") and s.label == "custom")
    info = env.ref_of(lambda s: s.store_id == "hub:u-info")
    assert env.view(custom, "stats").status == 200
    assert env.view(info, "stats").status == 200
    rows = log.rows_all()
    assert len(rows) == 2 and all(r["mixed_or_shared"] for r in rows)
    assert {r["store"] for r in rows} == {custom, info}
    everything = env.get("/api/memdash/access-log?scope=all")
    assert everything.status == 200 and len(everything.body["items"]) == 2
    # Nobody's Who viewed my memories lists them.
    for email in (H.ADA, H.BOB, H.MICHAEL):
        assert log.rows_for_subject(email) == []
    # scope=all is for platform admins only.
    env.as_user(H.ADA)
    assert env.get("/api/memdash/access-log?scope=all").status == 404
    audit = [r for r in env.audit_rows() if r["event"] == "memory.admin_read"]
    assert len(audit) == 2 and all(r["extra"]["mixed"] for r in audit)


def test_the_retention_purge_keeps_a_verifiable_chain(plain_log):
    old = datetime.now(timezone.utc) - timedelta(days=800)
    for i in range(3):
        log.append(_entry(action="view"), now=old + timedelta(minutes=i))
    for i in range(2):
        log.append(_entry(action="search"))
    assert log.purge(730) == 3
    assert log.verify_chain() == (True, "ok")
    assert [r["action"] for r in log.rows_for_subject(H.ADA)] == ["search", "search"]
    log.append(_entry(action="item"))
    assert log.verify_chain() == (True, "ok")
    con = sqlite3.connect(plain_log)
    checkpoint = con.execute("SELECT purged_through_id, rows_purged FROM checkpoints").fetchall()
    ids = [r[0] for r in con.execute("SELECT id FROM access_log ORDER BY id")]
    con.close()
    assert checkpoint == [(3, 3)] and ids == [4, 5, 6]
    # A purge of everything still anchors the next row.
    assert log.purge(1, now=datetime.now(timezone.utc) + timedelta(days=5)) == 3
    log.append(_entry(action="open"))
    assert log.verify_chain() == (True, "ok")


def test_the_governance_mirror_is_written_once_per_store_session(env):
    env.as_user(H.YASER, "Yaser")
    ref = _ada_ref(env)
    for view in ("stats", "memories", "graph"):
        assert env.view(ref, view, reason_code="support").status == 200
    reads = [r for r in env.audit_rows() if r["event"] == "memory.admin_read"]
    assert len(reads) == 1
    extra = reads[0]["extra"]
    assert extra["scope"] == "store:" + ref and extra["role"] == "platform_admin"
    assert extra["owner_hash"] == log.email_hash(H.ADA) and extra["reason_code"] == "support"
    assert reads[0]["subject_email_hash"] == log.email_hash(H.YASER)
    rows = log.rows_for_subject(H.ADA)
    assert [r["action"] for r in rows] == ["open", "view", "view"]
    assert all(r["reason_code"] == "support" for r in rows)


def test_a_leaver_is_pseudonymised_and_the_chain_still_verifies(plain_log):
    log.append(_entry())
    log.append(_entry(viewer_email=H.ODIS, viewer_display="Odis"))
    assert log.pseudonymise_viewer(H.YASER) == 1
    names = [r["viewer"] for r in log.rows_for_subject(H.ADA)]
    assert names == ["Former administrator", "Odis"]
    assert log.verify_chain() == (True, "ok")


def test_notice_acknowledgement_is_recorded_once_per_person(plain_log):
    assert not log.notice_acked(H.ADA, "memdash-notice-1")
    log.ack_notice(H.ADA, "memdash-notice-1")
    assert log.notice_acked(H.ADA, "memdash-notice-1")
    assert not log.notice_acked(H.ADA, "memdash-notice-2")
    assert not log.notice_acked(H.BOB, "memdash-notice-1")
    with pytest.raises(log.AccessLogError):
        log.ack_notice(H.ADA, "Bad Version!")


def test_rows_for_subject_never_raises(tmp_path):
    log.set_path(tmp_path / "missing-dir" / "sub" / "x.sqlite3")
    try:
        (tmp_path / "missing-dir").mkdir()
        (tmp_path / "missing-dir" / "sub").write_text("not a directory")
        assert log.rows_for_subject(H.ADA) == []
    finally:
        log.set_path(None)


def test_bad_rows_are_refused(plain_log):
    with pytest.raises(log.AccessLogError):
        log.append(_entry(viewer_role="member"))
    with pytest.raises(log.AccessLogError):
        log.append(_entry(action="export"))
    with pytest.raises(log.AccessLogError):
        log.append(_entry(), subject_hash="not-a-hash")
    assert log.clean_reason("other", "x" * 500)[1] == "x" * 200
    assert log.clean_reason("support", "ignored") == ("support", "")
    assert log.clean_reason("made-up", "x") == ("none", "")
