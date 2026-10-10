"""AG-UI 1.0 projection of WebUI runs (program plan 5.1, package W5).

The WebUI streams its own SSE vocabulary (``token``, ``tool``, ``done`` and so
on) and journals every frame in ``_run_journal/<session_id>/<stream_id>.jsonl``
(api/run_journal.py). This module maps that vocabulary onto AG-UI 1.0 events
without an AG-UI runtime dependency:

* ``Projector(ctx).feed(event_name, data)`` turns one native frame into zero or
  more AG-UI events and keeps the run, message, reasoning, tool call, step and
  subagent bookkeeping that the protocol's ordering rules need;
* ``project_journal(rows)`` projects one recorded run;
* ``encode_sse(events)`` frames events for the AG-UI HTTP and SSE binding;
* ``handle_replay(handler, parsed)`` serves ``GET /api/agui/runs/<stream_id>``
  for a finished run, to the owner of the run's conversation or a current
  participant only.

The mapping, the payload contracts of the ``turn_bot`` and ``step`` frames
(emitted by later packages) and every deviation from the plan table are in
docs/rfcs/agui-projection-v1.md. Emitted events never carry ``null``: an
optional field without a value is omitted.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0"
CUSTOM_PREFIX = "synthpulse."
ROUTE_PREFIX = "/api/agui/runs/"

# A finished run's journal can hold the whole redacted conversation in its
# ``done`` row, so the cap is generous. Configurable, never hardcoded (plan 0.4
# rule 12).
REPLAY_MAX_BYTES_ENV = "HERMES_WEBUI_AGUI_REPLAY_MAX_BYTES"
DEFAULT_REPLAY_MAX_BYTES = 32 * 1024 * 1024

# Native frames that become ``CUSTOM synthpulse.<name>`` with their payload.
PASSTHROUGH_CUSTOM_EVENTS = frozenset({
    "warning",
    "title",
    "title_status",
    "state_saved",
    "pending_steer_leftover",
})

_SUBAGENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SUBAGENT_STATUSES = frozenset({"queued", "running", "completed", "failed", "cancelled"})
_CANCEL_ERROR_TYPES = frozenset({"cancelled", "canceled"})
_TOOL_LIMIT_STATE = "tool_limit_reached"
_STEP_NAME_MAX = 128
_ERROR_MESSAGE_MAX = 2000
_MAX_DEPTH = 16
_MAX_SAFE_INTEGER = 9007199254740991

# Usage fields copied into the run state under ``/usage``. Everything else in a
# native usage or metering payload stays out: the metering frame also carries
# server-wide numbers (active streams, global throughput) that describe other
# people's runs, and routing details that are not this run's state.
_USAGE_FIELDS = (
    ("input_tokens", "inputTokens"),
    ("output_tokens", "outputTokens"),
    ("cache_read_tokens", "cacheReadTokens"),
    ("cache_write_tokens", "cacheWriteTokens"),
    ("context_length", "contextLength"),
    ("threshold_tokens", "thresholdTokens"),
    ("last_prompt_tokens", "lastPromptTokens"),
    ("post_compression_context_tokens_estimate", "postCompressionContextTokensEstimate"),
    ("estimated_cost", "estimatedCost"),
    ("cache_hit_percent", "cacheHitPercent"),
    ("turn_cache_hit_percent", "turnCacheHitPercent"),
    ("duration_seconds", "durationSeconds"),
    ("tps", "tps"),
    ("ttft_ms", "ttftMs"),
)
_APPROVAL_FIELDS = (
    ("approval_id", "approvalId"),
    ("command", "command"),
    ("description", "description"),
    ("pattern_key", "patternKey"),
    ("pattern_keys", "patternKeys"),
    ("pending_count", "pendingCount"),
)
_CLARIFY_FIELDS = (
    ("clarify_id", "clarifyId"),
    ("question", "question"),
    ("description", "description"),
    ("timeout_seconds", "timeoutSeconds"),
)

_DROP = object()


# ── JSON hygiene ─────────────────────────────────────────────────────────────

def _clean(value: Any, *, depth: int = 0, drop_private: bool = True) -> Any:
    """Return ``value`` as plain JSON without ``null`` or non-finite numbers.

    ``None`` values are removed from objects and arrays, keys starting with an
    underscore (the WebUI's private bookkeeping, for example approval mirror
    tokens) are dropped, and nesting deeper than ``_MAX_DEPTH`` is cut. Returns
    the ``_DROP`` sentinel when nothing is left of the value itself.
    """
    if value is None or depth > _MAX_DEPTH:
        return _DROP
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else _DROP
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            key = str(key)
            if drop_private and key.startswith("_"):
                continue
            cleaned = _clean(item, depth=depth + 1, drop_private=drop_private)
            if cleaned is not _DROP:
                out[key] = cleaned
        return out
    if isinstance(value, (list, tuple)):
        items = (_clean(item, depth=depth + 1, drop_private=drop_private) for item in value)
        return [item for item in items if item is not _DROP]
    return str(value)


def _clean_or(value: Any, default: Any) -> Any:
    cleaned = _clean(value)
    return default if cleaned is _DROP else cleaned


def _json_text(value: Any) -> str:
    """Compact, key-sorted JSON text (the argument text of a tool call)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _nonempty_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _timestamp_ms(value: Any) -> int | None:
    """Journal ``created_at`` (seconds since the epoch) as AG-UI milliseconds."""
    number = _finite_number(value)
    if number is None or number < 0:
        return None
    millis = int(round(number * 1000))
    return millis if millis <= _MAX_SAFE_INTEGER else None


def _pointer(*parts: str) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _pick(payload: dict, fields) -> dict:
    """Copy the listed native keys under their AG-UI names, cleaned."""
    out = {}
    for native, name in fields:
        cleaned = _clean(payload.get(native))
        if cleaned is not _DROP and cleaned != "":
            out[name] = cleaned
    return out


def _text_of(content: Any) -> str:
    """Flatten native message content (a string or a list of parts) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        return _json_text(_clean_or(content, {}))
    return str(content)


def _usage_state(usage: Any) -> dict:
    if not isinstance(usage, dict):
        return {}
    out = {}
    for native, name in _USAGE_FIELDS:
        number = _finite_number(usage.get(native))
        if number is not None:
            out[name] = number
    status = _nonempty_str(usage.get("cost_status"))
    if status:
        out["costStatus"] = status
    return out


def _default_redact_messages(messages: list) -> list:
    """Redact credentials the way the session GET response does."""
    from api.helpers import redact_session_data

    redacted = redact_session_data({"messages": messages}).get("messages")
    return redacted if isinstance(redacted, list) else []


# ── Projector ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProjectionContext:
    """Identity of the run being projected.

    ``thread_id`` is the WebUI session id and ``run_id`` the stream id.
    ``redact_messages`` redacts the conversation before ``MESSAGES_SNAPSHOT``;
    by default the WebUI's credential redaction is used.
    """

    thread_id: str
    run_id: str
    redact_messages: Callable[[list], list] | None = None


class Projector:
    """Stateful projection of one run's native frames onto AG-UI 1.0 events.

    ``feed`` accepts the native frames in stream order. ``seq`` (the journal
    sequence number) keeps synthetic tool call ids identical between a live
    projection and a replay; ``timestamp`` (the journal ``created_at`` in
    seconds) becomes each event's ``timestamp`` in milliseconds. Without them
    the projection is still valid, only less precise.
    """

    def __init__(self, ctx: ProjectionContext):
        if not isinstance(ctx, ProjectionContext):
            raise TypeError("ctx must be a ProjectionContext")
        if not _nonempty_str(ctx.thread_id) or not _nonempty_str(ctx.run_id):
            raise ValueError("thread_id and run_id are required")
        self._ctx = ctx
        self._run = ctx.run_id
        # new, open, finishing (done received, waiting for stream_end),
        # finished (RUN_FINISHED sent) or errored (RUN_ERROR sent).
        self._phase = "new"
        self._pending_outcome: dict | None = None
        self._late_error_allowed = False
        self._fed = 0
        self._text: str | None = None
        self._text_count = 0
        self._segment_message: str | None = None
        self._reasoning: tuple[str, str] | None = None
        self._reasoning_count = 0
        self._tools: dict[str, dict] = {}
        self._tool_order: list[str] = []
        self._subagents: dict[str, str] = {}
        self._steps: list[str] = []
        self._state: dict | None = None
        self._bot: str | None = None
        self._prompt_count = 0

    @property
    def closed(self) -> bool:
        """Whether the run has ended with RUN_FINISHED or RUN_ERROR."""
        return self._phase in ("finished", "errored")

    # ── public entry points ──

    def feed(self, event_name: str, data: Any = None, *, seq: int | None = None,
             timestamp: float | None = None) -> list[dict]:
        """Project one native frame. Returns the AG-UI events it produces."""
        self._fed += 1
        name = event_name if isinstance(event_name, str) else ""
        payload = data if isinstance(data, dict) else {}
        ts = _timestamp_ms(timestamp)
        key = seq if isinstance(seq, int) and not isinstance(seq, bool) and seq > 0 else self._fed
        out: list[dict] = []
        if self.closed:
            self._after_close(name, payload, ts, out)
            return out
        if self._phase == "new":
            self._phase = "open"
            out.append(self._event("RUN_STARTED", ts, threadId=self._ctx.thread_id,
                                   runId=self._run, protocolVersion=PROTOCOL_VERSION))
        handler = _HANDLERS.get(name)
        if handler is not None:
            handler(self, payload, ts, key, out)
        elif name in PASSTHROUGH_CUSTOM_EVENTS:
            self._custom(name, _clean_or(payload, {}), ts, out)
        return out

    def finish(self, *, timestamp: float | None = None) -> list[dict]:
        """End of input. Sends a RUN_FINISHED that was waiting for ``stream_end``.

        A run without a terminal frame stays open: the projection never invents
        how a run ended (the replay route adds the journal's own interruption
        frame for a run whose worker is gone).
        """
        out: list[dict] = []
        if self._phase == "finishing":
            self._emit_finish(_timestamp_ms(timestamp), out)
        return out

    # ── event construction ──

    def _event(self, event_type: str, ts: int | None, **fields) -> dict:
        event = {"type": event_type}
        for key, value in fields.items():
            if value is None:
                continue
            event[key] = value
        if ts is not None:
            event["timestamp"] = ts
        return event

    def _custom(self, name: str, value: Any, ts, out) -> None:
        out.append(self._event("CUSTOM", ts, name=CUSTOM_PREFIX + name, value=value))

    def _activity(self, message_id: str, activity_type: str, content: dict, ts, out) -> None:
        out.append(self._event("ACTIVITY_SNAPSHOT", ts, messageId=message_id,
                               activityType=activity_type, content=content))

    # ── open and close helpers ──

    def _open_text(self, ts, out) -> str:
        if self._text is None:
            self._text_count += 1
            self._text = f"{self._run}:text:{self._text_count}"
            self._segment_message = self._text
            out.append(self._event("TEXT_MESSAGE_START", ts, messageId=self._text,
                                   role="assistant", name=self._bot))
        return self._text

    def _close_text(self, ts, out) -> None:
        if self._text is not None:
            out.append(self._event("TEXT_MESSAGE_END", ts, messageId=self._text))
            self._text = None

    def _close_reasoning(self, ts, out) -> None:
        if self._reasoning is not None:
            span, message = self._reasoning
            out.append(self._event("REASONING_MESSAGE_END", ts, messageId=message))
            out.append(self._event("REASONING_END", ts, messageId=span))
            self._reasoning = None

    def _close_steps(self, ts, out) -> None:
        for name in list(self._steps):
            out.append(self._event("STEP_FINISHED", ts, stepName=name))
        self._steps = []

    def _close_subagents(self, ts, out, *, code: str, message: str) -> None:
        for sid, state in self._subagents.items():
            if state == "active":
                out.append(self._event("SUBAGENT_ERROR", ts, subagentRunId=sid, message=message, code=code))
                self._subagents[sid] = "closed"

    def _close_all(self, ts, out, *, cancelled: bool) -> None:
        self._close_reasoning(ts, out)
        self._close_text(ts, out)
        self._close_steps(ts, out)
        if cancelled:
            self._close_subagents(ts, out, code="cancelled", message="The delegated task was cancelled.")
        else:
            self._close_subagents(ts, out, code="unfinished",
                                  message="The delegated task ended without a final status.")

    def _run_finished(self, outcome: str, ts, out) -> None:
        out.append(self._event("RUN_FINISHED", ts, threadId=self._ctx.thread_id,
                               runId=self._run, outcome={"type": outcome}))
        self._phase = "finished"
        self._late_error_allowed = True

    def _emit_finish(self, ts, out) -> None:
        outcome = (self._pending_outcome or {}).get("type") or "success"
        self._close_all(ts, out, cancelled=outcome == "cancelled")
        self._pending_outcome = None
        self._run_finished(outcome, ts, out)

    def _run_error(self, payload: dict, ts, out) -> None:
        message = _nonempty_str(payload.get("message")) or "The run failed."
        code = _nonempty_str(payload.get("type"))
        out.append(self._event("RUN_ERROR", ts, message=message[:_ERROR_MESSAGE_MAX],
                               code=code.strip().lower() if code else None))
        self._phase = "errored"
        self._late_error_allowed = False

    def _after_close(self, name, payload, ts, out) -> None:
        # A run that finished may still report a failure that surfaced later;
        # after RUN_ERROR nothing may follow (AG-UI lifecycle rules).
        if name not in ("apperror", "error") or not self._late_error_allowed:
            return
        if str(payload.get("type") or "").strip().lower() in _CANCEL_ERROR_TYPES:
            return
        self._run_error(payload, ts, out)

    def _update_state(self, top: str, values: dict, ts, out) -> None:
        if not values:
            return
        new_state = copy.deepcopy(self._state) if self._state is not None else {}
        section = dict(new_state.get(top) or {})
        section.update(values)
        new_state[top] = section
        if self._state is None:
            out.append(self._event("STATE_SNAPSHOT", ts, snapshot=new_state))
            self._state = new_state
            return
        old_section = self._state.get(top)
        ops = []
        if old_section is None:
            ops.append({"op": "add", "path": _pointer(top), "value": section})
        else:
            for field, value in section.items():
                if field not in old_section:
                    ops.append({"op": "add", "path": _pointer(top, field), "value": value})
                elif old_section[field] != value:
                    ops.append({"op": "replace", "path": _pointer(top, field), "value": value})
        self._state = new_state
        if ops:
            out.append(self._event("STATE_DELTA", ts, delta=ops))

    def _synthetic_tool_id(self, key: int) -> str:
        tid = f"t{key}"
        suffix = 1
        while tid in self._tools:
            suffix += 1
            tid = f"t{key}.{suffix}"
        return tid

    def _start_tool(self, tid: str, name: str, args: Any, ts, out, *, synthetic: bool,
                    started: bool = True) -> dict:
        out.append(self._event("TOOL_CALL_START", ts, toolCallId=tid, toolCallName=name,
                               parentMessageId=self._segment_message))
        out.append(self._event("TOOL_CALL_ARGS", ts, toolCallId=tid, delta=_json_text(_clean_or(args, {}))))
        out.append(self._event("TOOL_CALL_END", ts, toolCallId=tid))
        # ``ts`` is the call's start only when a start frame was seen; a call
        # opened late for an orphaned result has no start time to measure from.
        record = {"name": name, "ts": ts if started else None, "answered": False, "synthetic": synthetic}
        self._tools[tid] = record
        self._tool_order.append(tid)
        return record

    # ── native frame handlers ──

    def _on_token(self, payload, ts, key, out) -> None:
        text = payload.get("text")
        text = text if isinstance(text, str) else ("" if text is None else str(text))
        if not text:
            return
        self._close_reasoning(ts, out)
        message = self._open_text(ts, out)
        out.append(self._event("TEXT_MESSAGE_CONTENT", ts, messageId=message, delta=text))

    def _on_interim_assistant(self, payload, ts, key, out) -> None:
        text = payload.get("text")
        visible = str(text).strip() if text is not None else ""
        if not visible:
            return
        # An interim message ends an assistant segment. When its text already
        # streamed as tokens, only the open message closes.
        self._close_reasoning(ts, out)
        self._close_text(ts, out)
        if payload.get("already_streamed"):
            return
        message = self._open_text(ts, out)
        out.append(self._event("TEXT_MESSAGE_CONTENT", ts, messageId=message, delta=visible))
        self._close_text(ts, out)

    def _on_reasoning(self, payload, ts, key, out) -> None:
        # The native frame carries the new reasoning text since the previous
        # frame (it is coalesced and appended by the browser), not the
        # cumulative text, so it is passed on as the delta unchanged.
        text = payload.get("text")
        text = text if isinstance(text, str) else ("" if text is None else str(text))
        if not text:
            return
        if self._reasoning is None:
            self._reasoning_count += 1
            span = f"{self._run}:reasoning:{self._reasoning_count}"
            message = f"{span}:message"
            out.append(self._event("REASONING_START", ts, messageId=span))
            out.append(self._event("REASONING_MESSAGE_START", ts, messageId=message, role="reasoning"))
            self._reasoning = (span, message)
        out.append(self._event("REASONING_MESSAGE_CONTENT", ts, messageId=self._reasoning[1], delta=text))

    def _on_tool(self, payload, ts, key, out) -> None:
        self._close_reasoning(ts, out)
        self._close_text(ts, out)
        tid = _nonempty_str(payload.get("tid"))
        if tid is not None and tid in self._tools:
            return
        synthetic = tid is None
        if synthetic:
            tid = self._synthetic_tool_id(key)
        name = _nonempty_str(payload.get("name")) or "tool"
        self._start_tool(tid, name, payload.get("args"), ts, out, synthetic=synthetic)

    def _match_tool(self, name: str | None) -> str | None:
        """The native legacy rule: the latest unanswered call with that name."""
        for want_synthetic in (True, False):
            for tid in reversed(self._tool_order):
                record = self._tools[tid]
                if record["answered"] or record["synthetic"] != want_synthetic:
                    continue
                if name is None or record["name"] == name:
                    return tid
        return None

    def _on_tool_complete(self, payload, ts, key, out) -> None:
        self._close_reasoning(ts, out)
        self._close_text(ts, out)
        name = _nonempty_str(payload.get("name"))
        tid = _nonempty_str(payload.get("tid"))
        if tid is None:
            tid = self._match_tool(name)
        record = self._tools.get(tid) if tid is not None else None
        if record is None:
            # A result for a call that never started in this run: open the call
            # first, so the result always answers a call the consumer knows.
            if tid is None:
                tid = self._synthetic_tool_id(key)
            record = self._start_tool(tid, name or "tool", payload.get("args"), ts, out,
                                      synthetic=_nonempty_str(payload.get("tid")) is None, started=False)
        if record["answered"]:
            return
        record["answered"] = True
        preview = payload.get("preview")
        if isinstance(preview, str):
            content = preview
        elif preview is None:
            content = ""
        else:
            content = _json_text(_clean_or(preview, {}))
        out.append(self._event("TOOL_CALL_RESULT", ts, messageId=f"{self._run}:tool-result:{tid}",
                               toolCallId=tid, content=content, role="tool"))
        timing = {"toolCallId": tid}
        duration = _finite_number(payload.get("duration"))
        if duration is not None and duration >= 0:
            timing["durationMs"] = int(round(duration * 1000))
        elif ts is not None and record["ts"] is not None and ts >= record["ts"]:
            timing["durationMs"] = ts - record["ts"]
        timing["isError"] = bool(payload.get("is_error"))
        self._custom("tool_timing", timing, ts, out)
        # Results go back to the model, whose next message is a new segment.
        self._segment_message = None

    def _on_subagent(self, payload, ts, key, out) -> None:
        sid = payload.get("id")
        status = payload.get("status")
        if not isinstance(sid, str) or not _SUBAGENT_ID_RE.match(sid) or status not in _SUBAGENT_STATUSES:
            return
        state = self._subagents.get(sid)
        if state == "closed":
            # AG-UI forbids reusing an invocation id within a run.
            return
        summary = _nonempty_str(payload.get("summary"))
        parent = payload.get("parent_id")
        parent = parent if isinstance(parent, str) and parent in self._subagents and parent != sid else None
        if state is None:
            out.append(self._event("SUBAGENT_STARTED", ts, subagentRunId=sid, name="subagent",
                                   description=summary, parentSubagentRunId=parent))
            self._subagents[sid] = "active"
        content = {"id": sid, "status": status}
        if summary:
            content["summary"] = summary
        for native, field in (("task_index", "taskIndex"), ("task_count", "taskCount"),
                              ("tool_count", "toolCount"), ("duration_seconds", "durationSeconds")):
            number = _finite_number(payload.get(native))
            if number is not None:
                content[field] = number
        if parent:
            content["parentId"] = parent
        self._activity(f"{self._run}:subagent:{sid}", "subagent", content, ts, out)
        if status == "completed":
            out.append(self._event("SUBAGENT_FINISHED", ts, subagentRunId=sid))
        elif status == "failed":
            out.append(self._event("SUBAGENT_ERROR", ts, subagentRunId=sid,
                                   message="The delegated task failed.", code="failed"))
        elif status == "cancelled":
            out.append(self._event("SUBAGENT_ERROR", ts, subagentRunId=sid,
                                   message="The delegated task was cancelled.", code="cancelled"))
        if status in ("completed", "failed", "cancelled"):
            self._subagents[sid] = "closed"

    def _on_todo_state(self, payload, ts, key, out) -> None:
        todos = payload.get("todos")
        if not isinstance(todos, list):
            return
        content = {"todos": _clean_or(todos, [])}
        summary = _clean(payload.get("summary"))
        if isinstance(summary, dict):
            content["summary"] = summary
        self._activity(f"{self._run}:plan", "plan", content, ts, out)

    def _goal_content(self, payload, state) -> dict:
        content = {}
        if state:
            content["state"] = state
        message = _nonempty_str(payload.get("message"))
        if message:
            content["message"] = message
        message_key = _nonempty_str(payload.get("message_key"))
        if message_key:
            content["messageKey"] = message_key
        args = _clean(payload.get("message_args"))
        if isinstance(args, list) and args:
            content["messageArgs"] = args
        return content

    def _on_goal(self, payload, ts, key, out) -> None:
        content = self._goal_content(payload, _nonempty_str(payload.get("state")))
        if content:
            self._activity(f"{self._run}:goal", "goal", content, ts, out)

    def _on_goal_continue(self, payload, ts, key, out) -> None:
        content = self._goal_content(payload, "continuing")
        prompt = _nonempty_str(payload.get("continuation_prompt"))
        if prompt:
            content["continuationPrompt"] = prompt
        self._activity(f"{self._run}:goal", "goal", content, ts, out)

    def _on_context_status(self, payload, ts, key, out) -> None:
        prefill = payload.get("prefill")
        if not isinstance(prefill, dict):
            return
        values = {}
        for native, field in (("status", "prefillStatus"), ("source", "prefillSource")):
            text = _nonempty_str(prefill.get(native))
            if text:
                values[field] = text
        count = _finite_number(prefill.get("message_count"))
        if count is not None:
            values["prefillMessageCount"] = count
        if prefill.get("compacted") is True:
            values["prefillCompacted"] = True
        self._update_state("context", values, ts, out)

    def _on_metering(self, payload, ts, key, out) -> None:
        values = _usage_state(payload.get("usage"))
        ttft = _finite_number(payload.get("ttft_ms"))
        if ttft is not None:
            values["ttftMs"] = ttft
        self._update_state("usage", values, ts, out)

    def _open_step(self, name: str, ts, out) -> None:
        if name not in self._steps:
            self._steps.append(name)
            out.append(self._event("STEP_STARTED", ts, stepName=name))

    def _finish_step(self, name: str, ts, out) -> None:
        # A finish without a start still marks the step, as a started and
        # finished pair, because AG-UI forbids finishing a step never opened.
        self._open_step(name, ts, out)
        self._steps.remove(name)
        out.append(self._event("STEP_FINISHED", ts, stepName=name))

    def _on_compressing(self, payload, ts, key, out) -> None:
        self._open_step("compress", ts, out)

    def _on_compressed(self, payload, ts, key, out) -> None:
        self._finish_step("compress", ts, out)
        self._update_state("usage", _usage_state(payload.get("usage")), ts, out)

    def _on_step(self, payload, ts, key, out) -> None:
        name = _nonempty_str(payload.get("name"))
        status = payload.get("status")
        if name is None or len(name) > _STEP_NAME_MAX:
            return
        if status == "started":
            self._open_step(name, ts, out)
        elif status == "finished":
            self._finish_step(name, ts, out)

    def _on_approval(self, payload, ts, key, out) -> None:
        value = _pick(payload, _APPROVAL_FIELDS)
        self._custom("approval", value, ts, out)
        self._prompt_count += 1
        approval_id = value.get("approvalId")
        ident = approval_id if isinstance(approval_id, str) else str(self._prompt_count)
        content = {"kind": "approval", "status": "pending"}
        for field in ("approvalId", "description"):
            if field in value:
                content[field] = value[field]
        self._activity(f"{self._run}:approval:{ident}", "approval", content, ts, out)

    def _on_clarify(self, payload, ts, key, out) -> None:
        value = _pick(payload, _CLARIFY_FIELDS)
        choices = payload.get("choices_offered")
        if not isinstance(choices, list):
            choices = payload.get("choices")
        if isinstance(choices, list):
            choices = [str(choice) for choice in choices if choice is not None]
            if choices:
                value["choices"] = choices
        self._custom("clarify", value, ts, out)
        self._prompt_count += 1
        clarify_id = value.get("clarifyId")
        ident = clarify_id if isinstance(clarify_id, str) else str(self._prompt_count)
        content = {"kind": "clarify", "status": "pending"}
        for field in ("clarifyId", "question"):
            if field in value:
                content[field] = value[field]
        self._activity(f"{self._run}:clarify:{ident}", "approval", content, ts, out)

    def _on_turn_bot(self, payload, ts, key, out) -> None:
        bot = _nonempty_str(payload.get("bot")) or _nonempty_str(payload.get("bot_profile"))
        if bot is None:
            return
        value = {"bot": bot}
        reason = _nonempty_str(payload.get("reason"))
        if reason:
            value["reason"] = reason
        self._bot = bot
        self._custom("turn_bot", value, ts, out)

    def _snapshot_messages(self, messages: list) -> list[dict] | None:
        redact = self._ctx.redact_messages or _default_redact_messages
        try:
            redacted = redact(copy.deepcopy([m for m in messages if isinstance(m, dict)]))
        except Exception:
            # Never send the conversation unredacted: without redaction the
            # snapshot is left out and the streamed events stand on their own.
            logger.warning("AG-UI messages snapshot skipped: redaction failed", exc_info=True)
            return None
        out = []
        for index, message in enumerate(redacted if isinstance(redacted, list) else []):
            converted = _snapshot_message(self._ctx.thread_id, index, message)
            if converted is not None:
                out.append(converted)
        return out

    def _on_done(self, payload, ts, key, out) -> None:
        if self._phase == "finishing":
            return
        self._close_reasoning(ts, out)
        self._close_text(ts, out)
        self._update_state("usage", _usage_state(payload.get("usage")), ts, out)
        session = payload.get("session")
        messages = session.get("messages") if isinstance(session, dict) else None
        if isinstance(messages, list):
            snapshot = self._snapshot_messages(messages)
            if snapshot is not None:
                out.append(self._event("MESSAGES_SNAPSHOT", ts, messages=snapshot))
        outcome = "success"
        if payload.get("terminal_state") == _TOOL_LIMIT_STATE:
            outcome = "cancelled"
            self._terminal_state_custom(payload, ts, out)
        # RUN_FINISHED waits for stream_end: the native stream still sends
        # usage and other frames after done, and AG-UI allows nothing after
        # RUN_FINISHED except a late RUN_ERROR.
        self._pending_outcome = {"type": outcome}
        self._phase = "finishing"

    def _terminal_state_custom(self, payload, ts, out) -> None:
        value = {"state": _TOOL_LIMIT_STATE}
        reason = _nonempty_str(payload.get("terminal_reason"))
        if reason:
            value["reason"] = reason
        self._custom("terminal_state", value, ts, out)

    def _on_stream_end(self, payload, ts, key, out) -> None:
        # A stream that ends without done, cancel or error completed in the
        # native journal's terms, so it finishes as a success.
        self._emit_finish(ts, out)

    def _on_cancel(self, payload, ts, key, out) -> None:
        self._close_all(ts, out, cancelled=True)
        self._pending_outcome = None
        self._run_finished("cancelled", ts, out)

    def _on_error(self, payload, ts, key, out) -> None:
        error_type = str(payload.get("type") or "").strip().lower()
        if error_type in _CANCEL_ERROR_TYPES:
            self._on_cancel(payload, ts, key, out)
            return
        if error_type == _TOOL_LIMIT_STATE or payload.get("terminal_state") == _TOOL_LIMIT_STATE:
            # A limit the producer enforces stops the run without failing it:
            # AG-UI names that ending the cancelled outcome.
            self._terminal_state_custom(payload, ts, out)
            self._close_all(ts, out, cancelled=True)
            self._pending_outcome = None
            self._run_finished("cancelled", ts, out)
            return
        # RUN_ERROR ends everything still open; no closing events are needed.
        self._run_error(payload, ts, out)


_HANDLERS: dict[str, Callable] = {
    "token": Projector._on_token,
    "interim_assistant": Projector._on_interim_assistant,
    "reasoning": Projector._on_reasoning,
    "tool": Projector._on_tool,
    "tool_complete": Projector._on_tool_complete,
    "subagent": Projector._on_subagent,
    "todo_state": Projector._on_todo_state,
    "goal": Projector._on_goal,
    "goal_continue": Projector._on_goal_continue,
    "context_status": Projector._on_context_status,
    "metering": Projector._on_metering,
    "compressing": Projector._on_compressing,
    "compressed": Projector._on_compressed,
    "step": Projector._on_step,
    "approval": Projector._on_approval,
    "clarify": Projector._on_clarify,
    "turn_bot": Projector._on_turn_bot,
    "done": Projector._on_done,
    "stream_end": Projector._on_stream_end,
    "cancel": Projector._on_cancel,
    "apperror": Projector._on_error,
    "error": Projector._on_error,
}


def _snapshot_message(thread_id: str, index: int, message: Any) -> dict | None:
    """One native transcript message as an AG-UI message, or None to skip it."""
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    message_id = f"{thread_id}:message:{index}"
    if role == "user":
        return {"id": message_id, "role": "user", "content": _text_of(message.get("content"))}
    if role in ("system", "developer"):
        return {"id": message_id, "role": role, "content": _text_of(message.get("content"))}
    if role == "assistant":
        out: dict = {"id": message_id, "role": "assistant"}
        bot = _nonempty_str(message.get("bot_profile"))
        if bot:
            out["name"] = bot
        text = _text_of(message.get("content"))
        if text:
            out["content"] = text
        calls = []
        for call in message.get("tool_calls") or []:
            converted = _snapshot_tool_call(call)
            if converted is not None:
                calls.append(converted)
        if calls:
            out["toolCalls"] = calls
        return out
    if role == "tool":
        call_id = _nonempty_str(message.get("tool_call_id"))
        if call_id is None:
            # AG-UI requires the call a tool message answers.
            return None
        return {"id": message_id, "role": "tool", "content": _text_of(message.get("content")),
                "toolCallId": call_id}
    return None


def _snapshot_tool_call(call: Any) -> dict | None:
    if not isinstance(call, dict):
        return None
    call_id = _nonempty_str(call.get("id"))
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    name = _nonempty_str(function.get("name"))
    if call_id is None or name is None:
        return None
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        arguments = _json_text(_clean_or(arguments, {}))
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def _row_event_name(row: dict) -> str:
    name = row.get("event")
    if not isinstance(name, str) or not name:
        name = row.get("type")
    return name if isinstance(name, str) else ""


def project_journal(rows: Iterable[dict], *, ctx: ProjectionContext | None = None) -> list[dict]:
    """Project the journal rows of one run (api/run_journal.py format).

    The context defaults to the session and run ids of the first row. Rows are
    fed in the order given, which for a journal file is sequence order.
    """
    rows = [row for row in rows if isinstance(row, dict)]
    if ctx is None:
        if not rows:
            return []
        ctx = ProjectionContext(thread_id=str(rows[0].get("session_id") or ""),
                                run_id=str(rows[0].get("run_id") or ""))
    projector = Projector(ctx)
    events: list[dict] = []
    last_ts = None
    for row in rows:
        seq = row.get("seq")
        last_ts = row.get("created_at")
        events.extend(projector.feed(_row_event_name(row), row.get("payload"),
                                     seq=seq if isinstance(seq, int) else None, timestamp=last_ts))
    events.extend(projector.finish(timestamp=last_ts))
    return events


def encode_sse(events: Iterable[dict]) -> bytes:
    """Frame events for the AG-UI HTTP and SSE binding: one ``data:`` per event."""
    chunks = []
    for event in events:
        text = json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        chunks.append(b"data: " + text.encode("utf-8") + b"\n\n")
    return b"".join(chunks)


# ── Replay route ─────────────────────────────────────────────────────────────

def replay_max_bytes() -> int:
    raw = str(os.environ.get(REPLAY_MAX_BYTES_ENV, "") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_REPLAY_MAX_BYTES
    return value if value > 0 else DEFAULT_REPLAY_MAX_BYTES


def _stream_id_from_path(path: Any) -> str | None:
    if not isinstance(path, str) or not path.startswith(ROUTE_PREFIX):
        return None
    stream_id = path[len(ROUTE_PREFIX):]
    from api import run_journal
    from api.models import is_safe_session_id

    try:
        run_journal._validate_id(stream_id, "run_id")
    except ValueError:
        return None
    if stream_id in (".", "..") or not is_safe_session_id(stream_id):
        return None
    return stream_id


def _locate_run(stream_id: str):
    """Return ``(session_id, path)`` of the run's journal, or None.

    Exactly one journal file must carry the stream id; a missing, ambiguous or
    symlinked one is refused rather than guessed.
    """
    from api import run_journal
    from api.models import is_safe_session_id

    root = run_journal._default_session_dir() / run_journal.RUN_JOURNAL_DIR_NAME
    try:
        matches = [p for p in root.glob(f"*/{stream_id}.jsonl")]
    except OSError:
        return None
    if len(matches) != 1:
        return None
    path = matches[0]
    session_id = path.parent.name
    try:
        run_journal._validate_id(session_id, "session_id")
    except ValueError:
        return None
    if session_id in (".", "..") or not is_safe_session_id(session_id):
        return None
    try:
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
            return None
        if path.resolve().parent.parent != root.resolve():
            return None
    except OSError:
        return None
    return session_id, path


def _load_owner_session(session_id: str):
    from api import models

    try:
        session = models.get_session(session_id, metadata_only=True)
    except Exception:
        return None
    if session is None or str(getattr(session, "session_id", "") or "") != session_id:
        return None
    return session


def _may_replay(session, email: str) -> bool:
    """Only the conversation's owner or a current participant may replay.

    An unowned conversation (legacy, cron or CLI rows) has no owner to resolve,
    so it is refused. Administrators get no wider access here.
    """
    owner = str(getattr(session, "owner_email", "") or "").strip().lower()
    if not owner or not email:
        return False
    if email == owner:
        return True
    from api.group_chat import participants_of

    return email in participants_of(session)


def _run_is_live(stream_id: str) -> bool:
    from api import config

    with config.ACTIVE_RUNS_LOCK:
        if stream_id in config.ACTIVE_RUNS:
            return True
    with config.STREAMS_LOCK:
        return stream_id in config.STREAMS


def _rows_consistent(rows: list, session_id: str, stream_id: str) -> bool:
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            return False
        if row.get("session_id") != session_id or row.get("run_id") != stream_id:
            return False
        if row.get("seq") != index:
            return False
    return True


def handle_replay(handler, parsed) -> bool:
    """Serve ``GET /api/agui/runs/<stream_id>`` as AG-UI events over SSE.

    Every refusal before authorization (an unknown, foreign or unresolvable
    stream, no identity) returns False, so the caller answers the same generic
    404 whether or not the stream exists. Only after the caller is known to be
    the owner or a current participant does the route say why it cannot
    replay: 409 while the run is still in progress, 413 above the size cap,
    422 for a damaged journal.
    """
    stream_id = _stream_id_from_path(getattr(parsed, "path", None))
    if stream_id is None:
        return False
    from api.ownership import request_owner_email

    try:
        email = str(request_owner_email(handler) or "").strip().lower()
    except Exception:
        email = ""
    if not email:
        return False
    located = _locate_run(stream_id)
    if located is None:
        return False
    session_id, path = located
    session = _load_owner_session(session_id)
    if session is None or not _may_replay(session, email):
        return False

    from api import run_journal
    from api.helpers import bad, t

    if _run_is_live(stream_id):
        bad(handler, "This run is still in progress. Try again when it has finished.", 409)
        return True
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size > replay_max_bytes():
        bad(handler, "This run is too large to replay.", 413)
        return True
    journal = run_journal.read_run_events(session_id, stream_id)
    rows = journal.get("events") or []
    if journal.get("malformed") or not _rows_consistent(rows, session_id, stream_id):
        bad(handler, "This run's record is damaged and cannot be replayed.", 422)
        return True
    if not rows:
        return False
    if run_journal.select_authoritative_terminal_event(rows) is None:
        # The worker is gone and never wrote a terminal frame: close the run
        # the way the native replay does, with its interruption frame.
        stale = run_journal.stale_interrupted_event(session_id, stream_id)
        if stale:
            rows = rows + [stale]
    events = project_journal(rows, ctx=ProjectionContext(thread_id=session_id, run_id=stream_id))
    # A finished run is sent whole, with a length: the shared plain-body
    # helper adds no-store, the security headers and any pending auth cookie.
    t(handler, encode_sse(events), 200, content_type="text/event-stream; charset=utf-8",
      extra_headers={"X-Accel-Buffering": "no"})
    return True
