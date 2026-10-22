import threading
import time


def test_runtime_warm_single_flight_and_completion(monkeypatch):
    from api import prewarm
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def warm():
        entered.set(); release.wait(2); finished.set()
    monkeypatch.setattr(prewarm, '_warm_chat_runtime', warm)
    monkeypatch.setattr(prewarm, '_chat_warm_state', 'cold')
    monkeypatch.setattr(prewarm, '_chat_warm_retry_at', 0)
    monkeypatch.setattr(prewarm, '_prewarm_enabled', lambda: True)
    try:
        assert prewarm.start_chat_prewarm() == 'warming'
        assert entered.wait(1)
        for _ in range(10): assert prewarm.start_chat_prewarm() == 'warming'
        release.set(); assert finished.wait(1)
        deadline=time.monotonic()+1
        while prewarm._chat_warm_state != 'ready' and time.monotonic()<deadline: time.sleep(.001)
        assert prewarm.start_chat_prewarm() == 'ready'
    finally: release.set()


def test_disabled_prewarm_does_not_start(monkeypatch):
    from api import prewarm
    monkeypatch.setattr(prewarm, '_prewarm_enabled', lambda: False)
    assert prewarm.start_chat_prewarm() == 'disabled'
