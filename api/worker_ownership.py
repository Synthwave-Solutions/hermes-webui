"""Actual in-process worker lifetime, independent of advisory run timestamps."""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Callable


@dataclass(eq=False)
class WorkerToken:
    session_id: str
    stream_id: str
    thread_id: int = field(default_factory=threading.get_ident)
    finished: bool = False
    actions: int = 0
    on_retired: Callable[[], None] | None = None


_LOCK = threading.Lock()
_OWNERS: dict[str, WorkerToken] = {}


def claim(session_id: str, stream_id: str, *, on_retired: Callable[[], None] | None = None) -> WorkerToken:
    with _LOCK:
        if session_id in _OWNERS:
            raise RuntimeError('Previous session worker is still finishing')
        token = WorkerToken(session_id, stream_id, on_retired=on_retired)
        _OWNERS[session_id] = token
        return token


def _retire(token: WorkerToken) -> Callable[[], None] | None:
    if token.finished and not token.actions and _OWNERS.get(token.session_id) is token:
        del _OWNERS[token.session_id]
        return token.on_retired
    return None


def release(token: WorkerToken | None) -> None:
    if token is None:
        return
    notify = None
    with _LOCK:
        if _OWNERS.get(token.session_id) is token:
            token.finished = True
            notify = _retire(token)
    if notify:
        notify()


def live_stream(session_id: str) -> str | None:
    with _LOCK:
        token = _OWNERS.get(session_id)
        return token.stream_id if token else None


def owned_by_other_thread(session_id: str) -> bool:
    with _LOCK:
        token = _OWNERS.get(session_id)
        return bool(token and (token.finished or token.thread_id != threading.get_ident()))


def live_sessions() -> set[str]:
    with _LOCK:
        return set(_OWNERS)


def run_if_live(session_id: str, stream_id: str, callback: Callable[[], None]) -> bool:
    """Lease a matching worker while signalling it, without callback lock nesting.

    Its finally can finish during the callback; successor admission remains
    fenced until both have settled. No new cancellation can lease a finished
    worker, nor can an old callback borrow its successor's cached agent.
    """
    with _LOCK:
        token = _OWNERS.get(session_id)
        if token is None or token.stream_id != stream_id or token.finished:
            return False
        token.actions += 1
    try:
        callback()
        return True
    finally:
        with _LOCK:
            token.actions -= 1
            notify = _retire(token)
        if notify:
            notify()
