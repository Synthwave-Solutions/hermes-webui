"""Governance audit tests: secret redaction, hashed subjects, newest-first
reads and thread-safe appends. Isolated via HERMES_HOME=tmp_path.
"""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance.audit import append_audit_event, read_audit_events  # noqa: E402


def test_audit_log_redacts_secret_like_values(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    append_audit_event(
        "deny",
        subject_email="User@Example.test",
        path="/api/settings",
        method="GET",
        reason="permission_not_allowed",
        extra={
            "api_key": "sk-secret-value",
            "nested": {"Authorization": "Bearer abc123"},
            "note": "header was Bearer xyz789 today",
        },
    )

    audit_file = tmp_path / "dashboard-governance-audit.jsonl"
    raw = audit_file.read_text(encoding="utf-8")
    assert "sk-secret-value" not in raw
    assert "Bearer abc123" not in raw
    assert "xyz789" not in raw
    row = json.loads(raw)
    assert row["event"] == "deny"
    assert row["path"] == "/api/settings"
    assert row["extra"]["api_key"] == "[REDACTED]"
    assert row["extra"]["nested"]["Authorization"] == "[REDACTED]"
    assert row["extra"]["note"] == "header was Bearer [REDACTED] today"


def test_identities_are_hashed_never_raw(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    append_audit_event(
        "would_deny",
        subject_email="Person@Example.test",
        subject_user_id="sub-12345",
        path="/api/session",
        method="POST",
        reason="route_not_allowed",
        mode="report_only",
        report_only=True,
    )

    raw = (tmp_path / "dashboard-governance-audit.jsonl").read_text(encoding="utf-8")
    assert "person@example.test" not in raw.lower()
    assert "sub-12345" not in raw
    row = json.loads(raw)
    assert len(row["subject_email_hash"]) == 24
    assert len(row["subject_user_id_hash"]) == 24
    assert row["report_only"] is True
    assert row["mode"] == "report_only"


def test_read_audit_events_returns_newest_first_and_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    append_audit_event("deny", path="/api/one")
    append_audit_event("policy_change", path="/api/two")
    append_audit_event("would_deny", path="/api/three")

    events = read_audit_events(limit=2)

    assert [event["event"] for event in events] == ["would_deny", "policy_change"]
    assert [event["path"] for event in events] == ["/api/three", "/api/two"]


def test_read_skips_malformed_lines_and_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    assert read_audit_events() == []

    append_audit_event("deny", path="/api/ok")
    audit_file = tmp_path / "dashboard-governance-audit.jsonl"
    with audit_file.open("a", encoding="utf-8") as fh:
        fh.write("{not json}\n")

    events = read_audit_events(limit=10)
    assert [event["path"] for event in events] == ["/api/ok"]


def test_concurrent_appends_produce_valid_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    def _worker(idx):
        for n in range(20):
            append_audit_event("deny", path=f"/api/thread/{idx}/{n}", reason="x" * 200)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = (tmp_path / "dashboard-governance-audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 160
    for line in lines:
        row = json.loads(line)  # raises on interleaved partial writes
        assert row["event"] == "deny"
