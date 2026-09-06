def test_model_warm_starts_while_sidebar_blocked(monkeypatch):
    from api import prewarm
    from threading import Event
    blocked=Event(); model_started=Event(); sidebar_started=Event()
    def sidebar():sidebar_started.set();blocked.wait(2)
    monkeypatch.setattr(prewarm,"_run",sidebar)
    monkeypatch.setattr(prewarm,"_warm_model_catalog",model_started.set)
    monkeypatch.setattr(prewarm,"_prewarm_enabled",lambda:True)
    try:
        assert prewarm.start_prewarm_thread()
        assert sidebar_started.wait(1) and model_started.wait(1)
    finally:blocked.set()
