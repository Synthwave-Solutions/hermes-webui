import importlib.util
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def collector(monkeypatch):
    root = Path(__file__).resolve().parents[1] / "scripts" / "scout"
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location("scout_feedback", root / "scout_collect.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output(home, name, content, timestamp):
    path = home / "cron" / "output" / "scout-job" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.utime(path, (timestamp, timestamp))


def test_failed_preflight_can_retry_then_success_debounces(collector, monkeypatch, tmp_path, capsys):
    ctx = {"home": tmp_path, "profile": "radar", "self_job": "scout-job",
           "ledger": tmp_path / "seen.db"}
    monkeypatch.setattr(collector, "resolve_context", lambda: ctx)
    monkeypatch.setattr(collector, "load_meta", lambda _: {"title": "Radar", "scout": {"enabled": True}})
    monkeypatch.setattr(collector, "collect_calendar", lambda *a: ("", []))
    monkeypatch.setattr(collector, "collect_email", lambda *a: ("", []))
    for name in ("collect_jobs", "collect_kanban", "collect_screen"):
        monkeypatch.setattr(collector, name, lambda *a: [])
    monkeypatch.setattr(collector, "collect_memory", lambda *a: "")

    monkeypatch.setattr(collector.time, "time", lambda: 10000)
    assert collector.run() == 0
    assert "Proactieve ronde" in capsys.readouterr().out
    output(tmp_path, "blocked.md", "# Cron Job: Scout\n**Status:** BLOCKED (configuration)\n", 10001)

    monkeypatch.setattr(collector.time, "time", lambda: 10010)
    assert collector.run() == 0
    assert "Proactieve ronde" in capsys.readouterr().out
    output(tmp_path, "answer.md", "# Cron Job: Scout\n## Response\n\nMeeting preparation ready.", 10011)

    monkeypatch.setattr(collector.time, "time", lambda: 10020)
    assert collector.run() == 0
    assert json.loads(capsys.readouterr().out) == {"wakeAgent": False}
    with collector.scout_ledger.Ledger(ctx["ledger"]) as ledger:
        assert ledger.get_meta("last_preparation") == "Meeting preparation ready."
        assert float(ledger.get_meta("last_proactive_sweep")) == 10011


@pytest.mark.parametrize("answer", ["Useful preparation", "[SILENT]"])
def test_completed_agent_run_acknowledges_only_pending_cooldowns(collector, tmp_path, answer):
    with collector.scout_ledger.Ledger(tmp_path / "seen.db") as ledger:
        ledger.set_meta("last_notes_wake", "5000")
        ledger.set_meta("pending_run", json.dumps({"at": 10000, "hashes": [],
            "cooldowns": ["last_proactive_sweep", "last_topic_sweep", "not_a_cooldown"]}))
        output(tmp_path, "answer.md", "# Cron Job: Scout\n## Response\n\n" + answer, 10001)
        collector.apply_feedback({"home": tmp_path, "self_job": "scout-job"}, ledger, 10010)
        assert ledger.get_meta("last_proactive_sweep") == "10001.0"
        assert ledger.get_meta("last_topic_sweep") == "10001.0"
        assert ledger.get_meta("last_notes_wake") == "5000"
        assert ledger.get_meta("not_a_cooldown") is None
        assert ledger.get_meta("pending_run") is None


@pytest.mark.parametrize("content", [None, "# Cron Job: Scout (FAILED)\n",
    "# Cron Job: Scout\nScript gate returned `wakeAgent=false` — agent skipped.\n"])
def test_uncompleted_legacy_attempt_does_not_consume_cooldown(collector, tmp_path, content):
    with collector.scout_ledger.Ledger(tmp_path / "seen.db") as ledger:
        ledger.set_meta("last_proactive_sweep", "10000")
        ledger.set_meta("last_topic_sweep", "10000")
        ledger.set_meta("last_notes_wake", "5000")
        ledger.set_meta("pending_run", json.dumps({"at": 10000, "hashes": []}))
        if content:
            output(tmp_path, "attempt.md", content, 10001)
        notes = collector.apply_feedback({"home": tmp_path, "self_job": "scout-job"}, ledger, 10010)
        assert collector.proactive_due(ledger, 10010)
        assert ledger.get_meta("last_topic_sweep") is None
        assert ledger.get_meta("last_notes_wake") == "5000"
        assert notes


def test_script_gate_is_not_an_agent_response(collector):
    assert collector.classify_run_doc(
        "# Cron Job: Scout\nScript gate returned `wakeAgent=false` — agent skipped.\n"
    ) == ("gate", "")


def test_failed_attempts_do_not_exhaust_item_display_budget(collector, tmp_path):
    with collector.scout_ledger.Ledger(tmp_path / "seen.db") as ledger:
        h = collector.scout_ledger.item_hash("chat", "own-chat", "Prepare meeting")
        for attempt in range(4):
            at = 10000 + attempt * 10
            ledger.record_shown(h, "chat", "Prepare meeting", "own-chat", "An open task", at, now=at)
            ledger.set_meta("pending_run", json.dumps({"at": at, "hashes": [h]}))
            output(tmp_path, f"failed-{attempt}.md", "# Cron Job: Scout (FAILED)\n", at + 1)
            ctx = {"home": tmp_path, "self_job": "scout-job"}
            collector.apply_feedback(ctx, ledger, at + 2)
            collector.apply_feedback(ctx, ledger, at + 3)
            assert ledger.auto_ignore(now=at + 3) == 0
            assert ledger.unclassified()[0]["hash"] == h
            assert ledger.unclassified()[0]["shown_count"] == 0

        ledger.record_shown(h, "chat", "Prepare meeting", "own-chat", "An open task", 20000, now=20000)
        ledger.release_shown([h], 10000)
        assert ledger.unclassified()[0]["shown_count"] == 1


def test_successful_silent_run_still_classifies_pending_items(collector, tmp_path):
    with collector.scout_ledger.Ledger(tmp_path / "seen.db") as ledger:
        h = collector.scout_ledger.item_hash("chat", "own-chat", "Prepare meeting")
        ledger.record_shown(h, "chat", "Prepare meeting", "own-chat", "An open task", 10000, now=10000)
        ledger.set_meta("pending_run", json.dumps({"at": 10000, "hashes": [h]}))
        output(tmp_path, "silent.md", "# Cron Job: Scout\n## Response\n\n[SILENT]", 10001)
        collector.apply_feedback({"home": tmp_path, "self_job": "scout-job"}, ledger, 10010)
        assert ledger.known(h) == "ignored"
        assert ledger.unclassified() == []
