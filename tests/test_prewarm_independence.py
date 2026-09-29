def test_model_warm_starts_while_sidebar_blocked(monkeypatch):
    from api import prewarm
    from threading import Event
    blocked=Event(); model_started=Event(); sidebar_started=Event()
    def sidebar():sidebar_started.set();blocked.wait(2)
    monkeypatch.setattr(prewarm,"_run",sidebar)
    monkeypatch.setattr(prewarm,"_warm_model_catalog",model_started.set)
    monkeypatch.setattr(prewarm,"_warm_profile_rows",lambda:None)
    monkeypatch.setattr(prewarm,"_warm_cli_sessions",lambda:None)
    monkeypatch.setattr(prewarm,"_prewarm_enabled",lambda:True)
    try:
        assert prewarm.start_prewarm_thread()
        assert sidebar_started.wait(1) and model_started.wait(1)
    finally:blocked.set()


def test_cli_session_warm_uses_request_path_arguments(monkeypatch):
    from api import config, models, prewarm
    calls = []
    monkeypatch.setattr(config, "load_settings", lambda: {
        "show_cli_sessions": True,
        "show_claude_code_sessions": False,
        "agent_session_source_filter": "cli",
    })
    monkeypatch.setattr(models, "get_cli_sessions", lambda **kw: calls.append(kw) or [{"session_id": "a"}])
    prewarm._warm_cli_sessions()
    assert calls == [{"source_filter": "cli", "all_profiles": False, "include_claude_code": False}]


def test_cli_session_warm_skipped_when_setting_off(monkeypatch):
    from api import config, models, prewarm
    monkeypatch.setattr(config, "load_settings", lambda: {"show_cli_sessions": False})
    monkeypatch.setattr(models, "get_cli_sessions", lambda **kw: (_ for _ in ()).throw(AssertionError("must not scan")))
    prewarm._warm_cli_sessions()


def test_start_prewarm_thread_starts_cli_warm(monkeypatch):
    from threading import Event
    from api import prewarm
    started = Event()
    monkeypatch.setattr(prewarm, "_run", lambda: None)
    monkeypatch.setattr(prewarm, "_warm_model_catalog", lambda: None)
    monkeypatch.setattr(prewarm, "_warm_profile_rows", lambda: None)
    monkeypatch.setattr(prewarm, "_warm_cli_sessions", started.set)
    monkeypatch.setattr(prewarm, "_prewarm_enabled", lambda: True)
    assert prewarm.start_prewarm_thread()
    assert started.wait(1)
