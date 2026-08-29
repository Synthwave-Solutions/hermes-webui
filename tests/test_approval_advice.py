"""Advice on an access request: honest about its source, safe when the model fails."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import approval_advice  # noqa: E402


PENDING = {
    "kind": "grant",
    "key": "stephen@synthwave.solutions|skill|gws-gmail",
    "label": "Skill: gws-gmail",
    "owner_email": "stephen@synthwave.solutions",
    "status": "pending",
    "payload": {
        "email": "stephen@synthwave.solutions",
        "gkind": "skill",
        "value": "gws-gmail",
        "trigger": "check whether the client replied to yesterday's mail",
        "count": 3,
    },
}

EXPLANATION = {
    "capability": "Lets this person use one skill.",
    "data": "Whatever the skill's own steps reach when it runs.",
    "risks": ["reads_mail"],
    "alternatives": ["a read-only mail skill"],
    "scope_text": "This one person only.",
}


@pytest.fixture(autouse=True)
def clean_cache():
    approval_advice.clear_cache()
    yield
    approval_advice.clear_cache()


@pytest.fixture
def no_model(monkeypatch):
    monkeypatch.setattr(approval_advice, "_ask_model", lambda entry, explanation: None)


class TestFallsBackHonestly:
    def test_advice_is_returned_even_without_a_model(self, no_model):
        advice = approval_advice.advise(PENDING, EXPLANATION)
        assert advice["recommendation"] in approval_advice._RECOMMENDATIONS
        assert advice["recommendation_reason"]

    def test_the_source_says_it_came_from_the_rules(self, no_model):
        assert approval_advice.advise(PENDING, EXPLANATION)["source"] == "rules"

    def test_the_note_explains_why_there_is_no_model_advice(self, no_model):
        assert "did not answer" in approval_advice.advise(PENDING, EXPLANATION)["note"]

    def test_a_narrower_option_is_recommended_when_one_exists(self, no_model):
        assert approval_advice.advise(PENDING, EXPLANATION)["recommendation"] == approval_advice.NARROWER

    def test_a_request_without_the_users_ask_asks_them_first(self, no_model):
        entry = {**PENDING, "payload": {**PENDING["payload"], "trigger": ""}}
        assert approval_advice.advise(entry, EXPLANATION)["recommendation"] == approval_advice.UNSURE

    def test_turning_the_model_off_is_stated_in_the_note(self, monkeypatch):
        monkeypatch.setenv("HERMES_WEBUI_APPROVAL_ADVICE", "off")
        advice = approval_advice.advise(PENDING, EXPLANATION)
        assert advice["source"] == "rules"
        assert "advisory model is off" in advice["note"]

    def test_the_model_is_not_called_when_it_is_off(self, monkeypatch):
        monkeypatch.setenv("HERMES_WEBUI_APPROVAL_ADVICE", "off")
        called = []
        monkeypatch.setattr(approval_advice, "_ask_model", lambda *a: called.append(1))
        approval_advice.advise(PENDING, EXPLANATION)
        assert not called


class TestModelAdvice:
    def _reply(self, monkeypatch, text):
        monkeypatch.setattr(
            approval_advice,
            "_ask_model",
            lambda entry, explanation: approval_advice._parse_model_reply(text),
        )

    GOOD = (
        '{"why":"They wanted to see a client reply.",'
        '"risk":"Could read any mail in that mailbox.",'
        '"recommendation":"grant_narrower",'
        '"recommendation_reason":"A read-only skill covers the ask.",'
        '"narrower_alternative":"a read-only mail skill"}'
    )

    def test_a_good_reply_is_used(self, monkeypatch):
        self._reply(monkeypatch, self.GOOD)
        advice = approval_advice.advise(PENDING, EXPLANATION)
        assert advice["source"] == "model"
        assert advice["recommendation"] == "grant_narrower"
        assert advice["why"].startswith("They wanted")

    def test_a_fenced_reply_is_still_read(self, monkeypatch):
        self._reply(monkeypatch, "```json\n" + self.GOOD + "\n```")
        assert approval_advice.advise(PENDING, EXPLANATION)["source"] == "model"

    def test_an_invented_verdict_is_refused(self):
        assert approval_advice._parse_model_reply(
            '{"why":"x","risk":"y","recommendation":"maybe","recommendation_reason":"z"}'
        ) is None

    def test_prose_instead_of_json_is_refused(self):
        assert approval_advice._parse_model_reply("I think you should grant this.") is None

    def test_an_empty_reply_is_refused(self):
        assert approval_advice._parse_model_reply("") is None

    def test_a_json_array_is_refused(self):
        assert approval_advice._parse_model_reply('[{"recommendation":"grant"}]') is None

    def test_long_model_text_is_truncated(self, monkeypatch):
        long_reply = (
            '{"why":"' + ("x" * 5000) + '","risk":"y","recommendation":"grant",'
            '"recommendation_reason":"z","narrower_alternative":""}'
        )
        self._reply(monkeypatch, long_reply)
        assert len(approval_advice.advise(PENDING, EXPLANATION)["why"]) <= 600


class TestCache:
    def test_a_second_read_does_not_ask_again(self, monkeypatch):
        calls = []

        def once(entry, explanation):
            calls.append(1)
            return approval_advice._parse_model_reply(TestModelAdvice.GOOD)

        monkeypatch.setattr(approval_advice, "_ask_model", once)
        approval_advice.advise(PENDING, EXPLANATION)
        approval_advice.advise(PENDING, EXPLANATION)
        assert len(calls) == 1

    def test_a_different_request_is_asked_separately(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            approval_advice,
            "_ask_model",
            lambda e, x: (calls.append(1), approval_advice._parse_model_reply(TestModelAdvice.GOOD))[1],
        )
        approval_advice.advise(PENDING, EXPLANATION)
        approval_advice.advise({**PENDING, "key": "other|skill|thing"}, EXPLANATION)
        assert len(calls) == 2


class TestNeverBreaksTheQueue:
    def test_a_non_dict_entry_returns_nothing(self):
        assert approval_advice.advise("not a request") == {}

    def test_a_raising_model_falls_back_instead_of_propagating(self, monkeypatch):
        def boom(entry, explanation):
            raise RuntimeError("gateway down")

        monkeypatch.setattr(approval_advice, "_ask_model", boom)
        # _ask_model swallows its own errors in production; assert the outer
        # guard too, so a future refactor cannot turn this into a 500.
        advice = approval_advice.advise(PENDING, EXPLANATION)
        assert advice == {} or advice["source"] == "rules"

    def test_the_requesters_own_ask_is_carried_through(self, no_model):
        advice = approval_advice.advise(PENDING, EXPLANATION)
        assert advice["requester_ask"] == PENDING["payload"]["trigger"]

    def test_a_missing_explanation_still_yields_advice(self, no_model):
        assert approval_advice.advise(PENDING)["recommendation"]
