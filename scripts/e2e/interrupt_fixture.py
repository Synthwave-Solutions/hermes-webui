"""Explicitly armed scheduling barriers for real startup cancellation QA.

No HTTP, engine result, or provider result is replaced. Private control files
pause initialization and the actual cancel response at the cache boundary.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
import threading
import time


def setup(qa: Path) -> None:
    from api import config, streaming
    from run_agent import AIAgent

    control = qa / "interrupt-control.json"
    records = qa / "interrupt-evidence.jsonl"
    controllers = {}
    lock = threading.Lock()

    def record(session_id, phase, **details):
        with lock, records.open("a") as handle:
            handle.write(json.dumps({"session_id": session_id, "phase": phase, **details}) + "\n")

    def armed(session_id, mode):
        if not control.exists():
            return None
        spec = json.loads(control.read_text())
        if spec != {"session_id": session_id, "mode": mode}:
            return None
        with lock:
            if session_id in controllers:
                return None
            item = {"resume": threading.Event(), "early_cancel": threading.Event(), "mode": mode}
            controllers[session_id] = item
        record(session_id, "initialization_held", mode=mode)
        return item

    def wait(event, label):
        if not event.wait(15):
            raise RuntimeError("QA interrupt barrier timed out: " + label)

    original_debug = streaming.logger.debug

    def debug(message, *args, **kwargs):
        # This log occurs after a fresh agent is published in the cache and
        # before it is registered for this stream. Interleaving Stop here is
        # valid application scheduling; retaining its HTTP response makes it
        # deterministic without replacing the handler.
        if message == '[webui] Created new agent for session %s' and args:
            item = armed(args[0], "cancel_initialization")
            if item:
                wait(item["resume"], "initialization")
        return original_debug(message, *args, **kwargs)

    streaming.logger.debug = debug
    original_refresh = streaming._refresh_cached_agent_runtime

    @functools.wraps(original_refresh)
    def refresh(agent, kwargs):
        result = original_refresh(agent, kwargs)
        item = armed(agent.session_id, "cancel_reuse") if result else None
        if item:
            deadline = time.monotonic() + 15
            release = qa / ("interrupt-release-" + agent.session_id)
            while not release.exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError("QA interrupt barrier timed out: reuse")
                time.sleep(.01)
            with config.ACTIVE_RUNS_LOCK:
                streams = [key for key, value in config.ACTIVE_RUNS.items()
                           if value.get('session_id') == agent.session_id]
            record(agent.session_id, 'reuse_released',
                   cancel_flag_present=any(key in config.CANCEL_FLAGS for key in streams))
        return result

    streaming._refresh_cached_agent_runtime = refresh
    original_interrupt = AIAgent.interrupt

    @functools.wraps(original_interrupt)
    def interrupt(agent, message=None, *args, **kwargs):
        result = original_interrupt(agent, message, *args, **kwargs)
        item = controllers.get(agent.session_id)
        if item:
            record(agent.session_id, "interrupt", reason=message)
            if (message == "Cancelled by user" and item['mode'] == 'cancel_initialization'
                    and not item["resume"].is_set()):
                item["resume"].set()
                wait(item["early_cancel"], "cancel response")
            elif message == "Cancelled before start":
                item["early_cancel"].set()
            elif message == 'Cancelled by user' and item['mode'] == 'cancelled_worker_response':
                # Simulate an already-long-running request without extending
                # test timeouts. Only advisory start timestamps change; the
                # actual worker, held provider reply and interrupt stay real.
                with config.ACTIVE_RUNS_LOCK:
                    for value in config.ACTIVE_RUNS.values():
                        if value.get('session_id') == agent.session_id:
                            value['started_at'] = time.time() - 181
                record(agent.session_id, 'cancelled_worker_aged', interrupted=agent._interrupt_requested)
        return result

    AIAgent.interrupt = interrupt
    original_run = AIAgent.run_conversation

    @functools.wraps(original_run)
    def run(agent, *args, **kwargs):
        if agent.session_id in controllers:
            record(agent.session_id, "conversation_entered",
                   interrupted=bool(agent._interrupt_requested))
        return original_run(agent, *args, **kwargs)

    AIAgent.run_conversation = run

    original_model = AIAgent._interruptible_streaming_api_call

    @functools.wraps(original_model)
    def model(agent, *args, **kwargs):
        result = original_model(agent, *args, **kwargs)
        item = armed(agent.session_id, 'cancelled_worker_response')
        if item:
            item['agent'] = agent
            item['response_held'] = True
            record(agent.session_id, 'provider_response_held')
            release = qa / ('interrupt-release-' + agent.session_id)
            deadline = time.monotonic() + 15
            while not release.exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError('QA interrupt barrier timed out: provider response')
                time.sleep(.01)
            record(agent.session_id, 'provider_response_released', interrupted=agent._interrupt_requested)
            item['response_held'] = False
        return result

    AIAgent._interruptible_streaming_api_call = model
    original_clear = AIAgent.clear_interrupt

    @functools.wraps(original_clear)
    def clear(agent, *args, **kwargs):
        item = controllers.get(agent.session_id)
        if item and item.get('response_held') and item.get('agent') is agent:
            record(agent.session_id, 'interrupt_reset_while_response_held')
        return original_clear(agent, *args, **kwargs)

    AIAgent.clear_interrupt = clear
