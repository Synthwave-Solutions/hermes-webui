"""14-09-2026 (Michael): approval: {mode: automatic, prompt} decides a person's
ACCESS REQUESTS in the queue; it never reviews tool calls. Uncertain verdicts
and out-of-bounds approvals leave the row to an administrator."""
import threading
import time

import pytest
import yaml

from api import approvals, config, grant_auto_review
from api.governance import loader

ME = "vansh@example.test"


def _raw(approval=True, deny_bunq=True):
    user = {"roles": ["member"], "access_mode": "blacklist", "access_level": "elevated",
            "grants": {"cli": {"commands": ["*"]}}}
    if approval:
        user["approval"] = {"mode": "automatic", "prompt": "Approve ordinary technical work; deny bank and Productive."}
    if deny_bunq:
        user["deny"] = {"cli": {"commands": ["bunq"]}}
    return {"mode": "enforce", "bootstrap_admins": ["michael@example.test"],
            "roles": {"member": {"grants": {"permissions": ["chat:use", "terminal:use"], "routes": ["*"], "profiles": ["vansh"],
                                            "tools": {"builtins": ["*"]}, "cli": {"commands": ["*"]}}}},
            "users": {ME: user}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    monkeypatch.setenv("HERMES_WEBUI_DISABLE_PROFILE_SYNC", "1")
    (tmp_path / "webui").mkdir()
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    monkeypatch.setattr("api.grant_requests.notify_requester_of_decision", lambda *a, **k: True)
    loader._clear_policy_cache()

    def write(raw):
        (tmp_path / "dashboard-governance.yaml").write_text(yaml.safe_dump(raw))
        loader._clear_policy_cache()

    def request(value="jq", gkind="cli"):
        key = f"{ME}|{gkind}|{value}"
        approvals.request(approvals.KIND_GRANT, key, ME, label=f"CLI: {value}",
                          payload={"email": ME, "gkind": gkind, "value": value, "reason": "cli_command_not_allowed",
                                   "tool": "terminal", "detail": value, "trigger": "parse the json export", "count": 1})
        return approvals.get(approvals.KIND_GRANT, key)

    write(_raw())
    return type("Env", (), {"tmp": tmp_path, "write": write, "request": request})


def _verdict(monkeypatch, decision, confidence=1.0):
    calls = []
    monkeypatch.setattr(grant_auto_review, "_ask_model",
                        lambda access, request: calls.append((access.subject.email, request)) or
                        {"decision": decision, "reason": f"model says {decision}", "confidence": confidence})
    return calls


def _policy_cli(tmp):
    raw = yaml.safe_load((tmp / "dashboard-governance.yaml").read_text())
    return raw["users"][ME].get("grants", {}).get("cli", {}).get("commands", [])


def test_an_approved_request_is_granted_without_a_person(env, monkeypatch):
    calls = _verdict(monkeypatch, "approve")
    entry = env.request("jq")
    review = grant_auto_review.auto_review_entry(entry)
    assert review["decision"] == "approve" and review["decided"] is True
    assert calls and calls[0][1]["asked_for"] == "parse the json export"
    assert approvals.get(approvals.KIND_GRANT, entry["key"])["status"] == "approved"
    assert "jq" in _policy_cli(env.tmp)


def test_a_denied_request_is_rejected_with_the_reason(env, monkeypatch):
    _verdict(monkeypatch, "deny")
    entry = env.request("trading212")
    review = grant_auto_review.auto_review_entry(entry)
    assert review["decision"] == "deny" and review["decided"] is True
    row = approvals.get(approvals.KIND_GRANT, entry["key"])
    assert row["status"] == "rejected" and "trading212" not in _policy_cli(env.tmp)


def test_an_uncertain_verdict_leaves_the_row_to_an_administrator(env, monkeypatch):
    _verdict(monkeypatch, "approve", confidence=0.4)
    entry = env.request("jq")
    review = grant_auto_review.auto_review_entry(entry)
    assert review["decision"] == "manual" and review["decided"] is False
    row = approvals.get(approvals.KIND_GRANT, entry["key"])
    assert row["status"] == "pending" and row["payload"]["auto_review"]["decision"] == "manual"


def test_without_an_approval_section_nothing_happens(env, monkeypatch):
    env.write(_raw(approval=False))
    calls = _verdict(monkeypatch, "approve")
    entry = env.request("jq")
    assert grant_auto_review.auto_review_entry(entry) is None
    assert not calls and approvals.get(approvals.KIND_GRANT, entry["key"])["status"] == "pending"


def test_an_explicit_deny_is_never_overridden_by_the_reviewer(env, monkeypatch):
    _verdict(monkeypatch, "approve")
    entry = env.request("bunq")
    review = grant_auto_review.auto_review_entry(entry)
    assert review["decision"] == "manual" and review["decided"] is False and "not applied" in review["reason"]
    assert approvals.get(approvals.KIND_GRANT, entry["key"])["status"] == "pending"
    assert "bunq" not in _policy_cli(env.tmp)


def test_schedule_pings_administrators_only_when_the_row_stays(env, monkeypatch):
    pinged = []
    done = threading.Event()
    def on_manual(entry):
        pinged.append(entry["key"]); done.set()
    _verdict(monkeypatch, "approve")
    entry = env.request("jq")
    grant_auto_review.schedule(entry, on_manual=on_manual)
    deadline = time.time() + 5
    while time.time() < deadline and approvals.get(approvals.KIND_GRANT, entry["key"])["status"] == "pending":
        time.sleep(0.05)
    assert approvals.get(approvals.KIND_GRANT, entry["key"])["status"] == "approved" and not pinged
    _verdict(monkeypatch, "manual")
    entry2 = env.request("yq")
    grant_auto_review.schedule(entry2, on_manual=on_manual)
    assert done.wait(5) and pinged == [entry2["key"]]
