"""Studio reads successful deliveries from the viewer's own permitted bot chats."""
import json
from types import SimpleNamespace

import pytest

from api import cron_bots, cron_webui_delivery as delivery, personal_findings as feed, routes


ME = "owner@example.test"


def report(day, text, status="ok", job="daily", profile="sales"):
    run_at = f"2026-10-{day:02}T12:00:00Z"
    job_data = {"id": job, "name": "Daily", "last_run_at": run_at}
    return {"role": "assistant", "content": delivery.build_update_text(job_data, body=text, run_ok=True, run_error=None),
            "cron_delivery": {"job_id": job, "profile": profile, "run_at": run_at, "status": status}}


@pytest.fixture
def registry(monkeypatch, tmp_path):
    from api import config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(feed, "request_owner_email", lambda _: ME.upper())
    monkeypatch.setattr(routes, "_chat_profile_target_allowed", lambda _, p: p != "revoked")
    monkeypatch.setattr(routes, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(feed, "load_settings", lambda: {"api_redact_enabled": True})
    monkeypatch.setattr(cron_bots, "bot_label", lambda p: p.title())
    monkeypatch.setattr(feed, "j", lambda _, payload, extra_headers: (200, payload, extra_headers))
    monkeypatch.setattr(feed, "bad", lambda _, reason, status: (status, reason, {}))
    sessions = {}
    monkeypatch.setattr(feed, "get_session", lambda sid, metadata_only: sessions[sid])
    monkeypatch.setattr(feed, "get_session_for_scan", lambda sid: sessions[sid])

    def add(profile, job="daily", owner=ME, listed=ME, **kwargs):
        sid = "chat-" + profile
        session = SimpleNamespace(session_id=sid, owner_email=owner, archived=False, project_shared=False,
                                  profile=profile, cron_job={"job_id":job, "profile":profile, "kind":"scout"},
                                  messages=[report(1, profile, job=job, profile=profile)])
        for field, value in kwargs.items():
            setattr(session, field, value)
        sessions[sid] = session
        data = cron_bots._load_chats()
        data["chats"][cron_bots._chat_key(job, profile)] = {"session_id":sid, "owner_email":listed}
        cron_bots._save_chats(data)
        return session
    return add


def test_exact_deliveries_sorted_across_bots(registry):
    first = registry("sales")
    first.messages = [report(day, f"Report {day}") for day in range(1, 16)]
    first.messages += [
        report(15, "Corrected\nSCOUT-LEDGER: internal\nSCOUT-WEB: raw"),
        report(16, None), report(17, "[SILENT]"), report(18, "error", "error"),
        report(19, "wrong profile", profile="other"), report(20, "wrong job", job="another"),
        {"role":"user", "content":"a follow-up"}, dict(report(21, "quoted"), role="user"),
        dict(report(22, "notice"), content="delivery troubleshooting"),
    ]
    registry("research", messages=[report(16, "Research result", profile="research")])
    status, payload, headers = feed.handle(None)
    rows = payload["findings"]
    assert status == 200 and headers["Cache-Control"] == "private, no-store"
    assert len(rows) == 12
    assert [r["body"] for r in rows[:3]] == ["Research result", "Corrected", "Report 14"]
    assert rows[-1]["body"] == "Report 5"
    assert rows[0]["bot"] == "Research" and rows[0]["session_id"] == "chat-research"
    assert all(set(r) == {"session_id", "run_at", "at", "body", "profile", "bot"} for r in rows)


def test_only_owned_current_readable_chats(registry, monkeypatch):
    registry("sales")
    registry("other-person", owner="someone@example.test")
    registry("other-entry", listed="someone@example.test")
    registry("revoked")
    registry("archived", archived=True)
    registry("stale", cron_job={"kind":"scout","job_id":"other","profile":"stale"})
    registry("ordinary", cron_job={"job_id":"daily","profile":"ordinary"})
    registry("removed-project", project_shared=True, project_id="missing")
    monkeypatch.setattr("api.models.load_projects", lambda _migrate: [])
    assert [r["profile"] for r in feed.handle(None)[1]["findings"]] == ["sales"]
    monkeypatch.setattr(routes, "_is_isolated_profile_mode", lambda: True)
    monkeypatch.setattr(routes, "_session_visible_to_active_profile", lambda profile, _: profile == "other-person")
    assert feed.handle(None)[1]["findings"] == []
    monkeypatch.setattr(feed, "request_owner_email", lambda _: None)
    assert feed.handle(None)[1]["findings"] == []


def test_rechecks_owner_on_full_chat(registry, monkeypatch):
    session = registry("sales")
    monkeypatch.setattr(feed, "get_session_for_scan", lambda _: SimpleNamespace(**{**vars(session), "owner_email":"changed@example.test"}))
    assert feed.handle(None)[1]["findings"] == []


def test_unavailable_registry_is_distinct_from_no_deliveries(registry):
    assert feed.handle(None)[1]["findings"] == []
    for data in ["{", json.dumps({"chats": []})]:
        cron_bots._chats_path().write_text(data)
        assert feed.handle(None)[0] == 503


def test_transcript_redaction_applies_to_dashboard(registry):
    synthetic_key = "sk-ant-api03-" + "A" * 40
    registry("sales", messages=[report(4, f"Sample token={synthetic_key}")])
    body = feed.handle(None)[1]["findings"][0]["body"]
    assert "Sample" in body and synthetic_key not in body
