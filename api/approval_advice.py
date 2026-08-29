"""What an admin needs to decide on an access request, in plain language.

``api/capability_risk.py`` already answers *what a grant would do*, from a fixed
catalogue. That is reliable but impersonal: it cannot say why THIS person asked
for THIS thing right now, and it never takes a position.

This module adds the two things an approver actually wants:

* the ask behind the request, in the requester's own words, and
* a recommendation with a reason: grant it, grant something narrower, or don't.

A model writes it, given only the request and the catalogue explanation. When
the model is unavailable, slow, or returns something unusable, a rules-based
recommendation takes its place and says so, so the screen never sits empty and
an approver is never left guessing whether advice is missing or simply absent.

The advice is guidance for a human, never an actor: nothing here approves,
writes policy, or changes a request. The admin still decides.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time

logger = logging.getLogger(__name__)

# One advice per request, kept for an hour. The approvals screen polls, and
# re-asking a model on every poll would cost money for an answer that cannot
# have changed: the request is immutable once filed.
_CACHE_TTL_SECONDS = 3600
_CACHE_MAX_ENTRIES = 256
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()

# Recommendations are a closed set so the UI can style them and so a model
# cannot invent a fourth verdict that nothing knows how to render.
GRANT = "grant"
NARROWER = "grant_narrower"
DECLINE = "decline"
UNSURE = "needs_more_information"
_RECOMMENDATIONS = (GRANT, NARROWER, DECLINE, UNSURE)

_ADVICE_TIMEOUT_SECONDS = 20.0
_ADVICE_MAX_TOKENS = 700

_SYSTEM_PROMPT = """You advise an administrator who is deciding on one access request on an internal AI workstation. You never decide; you explain and recommend.

You are given: who asked, what they asked for, what the platform's own risk catalogue says the grant would do, and the user's own message that triggered the request.

Answer ONLY with a JSON object, no prose around it, with exactly these keys:
{
 "why": "1-2 sentences on what the person was most likely trying to do, grounded in their own message. If their message is missing or unclear, say so plainly instead of guessing.",
 "risk": "1-2 sentences on the realistic worst case if this is granted to this person. Concrete, not generic.",
 "recommendation": one of "grant", "grant_narrower", "decline", "needs_more_information",
 "recommendation_reason": "1-2 sentences justifying the recommendation.",
 "narrower_alternative": "If the recommendation is grant_narrower, the narrower thing to give instead. Otherwise an empty string."
}

Rules:
- Write for a busy reader: short, concrete, no hedging, no filler, no bullet points.
- Never invent facts about the person, their role, or their past requests. Only use what you were given.
- Recommend "decline" only when the risk is real and specific, not because a capability sounds broad.
- Recommend "needs_more_information" when the person's own message does not explain the ask.
- Never use em dashes or en dashes.
"""


def _clean(value) -> str:
    return str(value or "").strip()


def _cache_get(key: str):
    now = time.time()
    with _CACHE_LOCK:
        found = _CACHE.get(key)
        if not found:
            return None
        stored_at, value = found
        if now - stored_at > _CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        return value


def _cache_put(key: str, value: dict) -> None:
    with _CACHE_LOCK:
        if len(_CACHE) >= _CACHE_MAX_ENTRIES:
            oldest = min(_CACHE, key=lambda k: _CACHE[k][0], default=None)
            if oldest is not None:
                _CACHE.pop(oldest, None)
        _CACHE[key] = (time.time(), value)


def clear_cache() -> None:
    """Forget every cached advice. Used by tests and after a policy change."""
    with _CACHE_LOCK:
        _CACHE.clear()


def advice_enabled() -> bool:
    """Whether a model may be asked. Off switches the module to rules only."""
    raw = os.getenv("HERMES_WEBUI_APPROVAL_ADVICE", "").strip().lower()
    if raw in {"0", "off", "false", "no"}:
        return False
    return True


def _cache_key(entry: dict) -> str:
    return "|".join((
        _clean(entry.get("kind")),
        _clean(entry.get("key")),
        _clean(entry.get("owner_email")),
        _clean((entry.get("payload") or {}).get("trigger"))[:120],
    ))


def _requester_ask(entry: dict) -> str:
    """The user's own message behind the request, or an empty string.

    Stored by the engine on the request itself; already redacted and truncated
    there, so it is quoted here rather than re-processed. Two redactors drift.
    """
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    for field in ("trigger", "user_ask", "reason_text"):
        found = _clean(payload.get(field))
        if found:
            return found[:1200]
    return ""


def _rules_advice(entry: dict, explanation: dict, note: str) -> dict:
    """A recommendation from what the platform already knows, no model.

    Deliberately cautious and deliberately explicit about being rule-based: an
    approver should be able to tell advice from a model apart from a default.
    """
    explanation = explanation if isinstance(explanation, dict) else {}
    risks = [r for r in (explanation.get("risks") or []) if _clean(r)]
    alternatives = [a for a in (explanation.get("alternatives") or []) if _clean(a)]
    ask = _requester_ask(entry)

    if not ask:
        recommendation = UNSURE
        reason = (
            "The request carries no message from the person who triggered it, so "
            "there is nothing to check the ask against. Ask them what they were doing."
        )
    elif alternatives:
        recommendation = NARROWER
        reason = (
            "The catalogue lists a narrower capability that covers this kind of ask, "
            "so the smaller grant is the safer first answer."
        )
    elif risks:
        recommendation = GRANT
        reason = (
            "Nothing in the catalogue marks this as unusually wide for one person, "
            "and it is written on their own entry only, so it stays revocable."
        )
    else:
        recommendation = UNSURE
        reason = "The catalogue has no entry for this capability, so it needs a human read."

    return {
        "why": ask and f"Their own message was: {ask[:400]}" or "",
        "risk": risks[0] if risks else _clean(explanation.get("data")),
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "narrower_alternative": alternatives[0] if alternatives else "",
        "source": "rules",
        "note": note,
    }


def _prompt_payload(entry: dict, explanation: dict) -> str:
    explanation = explanation if isinstance(explanation, dict) else {}
    return json.dumps(
        {
            "requested_by": _clean(entry.get("owner_email")),
            "request_kind": _clean(entry.get("kind")),
            "requested_capability": _clean(entry.get("label") or entry.get("name")),
            "their_own_message": _requester_ask(entry) or None,
            "catalogue_says_it_allows": _clean(explanation.get("capability")),
            "catalogue_says_it_reaches": _clean(explanation.get("data")),
            "catalogue_risks": list(explanation.get("risks") or [])[:6],
            "catalogue_narrower_options": list(explanation.get("alternatives") or [])[:4],
            "scope": _clean(explanation.get("scope_text")),
            "how_often_they_hit_this": (entry.get("payload") or {}).get("count"),
        },
        ensure_ascii=False,
    )[:6000]


def _parse_model_reply(text: str) -> dict | None:
    """Read the model's JSON, tolerating a code fence around it."""
    raw = _clean(text)
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return None
        raw = raw[start:end + 1]
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    recommendation = _clean(parsed.get("recommendation")).lower().replace(" ", "_")
    if recommendation not in _RECOMMENDATIONS:
        return None
    # A verdict with no reasoning is worse than no advice: it reads as a
    # considered opinion while saying nothing an approver can weigh. This also
    # catches an object plucked out of a JSON array by the brace scan above.
    if not _clean(parsed.get("recommendation_reason")) or not _clean(parsed.get("why")):
        return None
    return {
        "why": _clean(parsed.get("why"))[:600],
        "risk": _clean(parsed.get("risk"))[:600],
        "recommendation": recommendation,
        "recommendation_reason": _clean(parsed.get("recommendation_reason"))[:600],
        "narrower_alternative": _clean(parsed.get("narrower_alternative"))[:300],
        "source": "model",
        "note": "",
    }


def _ask_model(entry: dict, explanation: dict) -> dict | None:
    try:
        from agent.auxiliary_client import call_llm
    except Exception:
        logger.debug("approval advice: auxiliary client unavailable", exc_info=True)
        return None
    try:
        response = call_llm(
            task="approval_advice",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _prompt_payload(entry, explanation)},
            ],
            temperature=0.2,
            max_tokens=_ADVICE_MAX_TOKENS,
            timeout=_ADVICE_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.debug("approval advice: model call failed", exc_info=True)
        return None
    try:
        choices = getattr(response, "choices", None) or (response or {}).get("choices")
        first = choices[0]
        message = getattr(first, "message", None) or first.get("message")
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
    except Exception:
        logger.debug("approval advice: unexpected model response shape", exc_info=True)
        return None
    return _parse_model_reply(content)


def advise(entry, explanation=None) -> dict:
    """Return the advice block for one approvals row. Never raises.

    Always returns a usable block: from the model when it answers, from the
    rules otherwise, and the ``source`` field says which, so nobody mistakes a
    default for a considered opinion.
    """
    try:
        if not isinstance(entry, dict):
            return {}
        explanation = explanation if isinstance(explanation, dict) else {}
        key = _cache_key(entry)
        cached = _cache_get(key)
        if cached is not None:
            return cached
        result = None
        if advice_enabled():
            result = _ask_model(entry, explanation)
        if result is None:
            note = (
                "Written from the platform's own risk catalogue: the advisory model "
                "did not answer."
                if advice_enabled()
                else "Written from the platform's own risk catalogue: advisory model is off."
            )
            result = _rules_advice(entry, explanation, note)
        result["requester_ask"] = _requester_ask(entry)
        _cache_put(key, result)
        return result
    except Exception:  # pragma: no cover: the queue must render regardless
        logger.debug("approval advice failed", exc_info=True)
        return {}
