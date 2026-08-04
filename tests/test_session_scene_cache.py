from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSIONS_JS = (ROOT / "static" / "sessions.js").read_text(encoding="utf-8")


def _block(start: str, end: str) -> str:
    begin = SESSIONS_JS.index(start)
    finish = SESSIONS_JS.index(end, begin)
    return SESSIONS_JS[begin:finish]


def test_scene_cache_is_bounded_and_lru_evicted():
    assert "const _SESSION_SCENE_CACHE_MAX_ENTRIES = 15;" in SESSIONS_JS
    assert "const _SESSION_SCENE_CACHE_MAX_BYTES = 32 * 1024 * 1024;" in SESSIONS_JS
    cache_put = _block("function _putSessionSceneCache", "function _captureActiveSessionScene")
    assert "_sessionSceneCache.delete(sid);" in cache_put
    assert "_sessionSceneCache.set(sid, scene);" in cache_put
    assert "_sessionSceneCache.keys().next().value" in cache_put
    assert "_sessionSceneCacheBytes > _SESSION_SCENE_CACHE_MAX_BYTES" in cache_put


def test_scene_cache_captures_metadata_tail_cursor_and_scroll():
    capture = _block("function _captureActiveSessionScene", "function _restoreSessionScene")
    assert "metadata:" in capture
    assert "messages:" in capture
    assert "messagesTruncated:" in capture
    assert "oldestIdx:" in capture
    assert "scrollTop:" in capture
    assert "updated_at" in capture


def test_warm_switch_restores_before_lightweight_async_validation():
    load = _block("async function loadSession(sid)", "// ── Handoff hint logic")
    assert "const cachedScene = !forceReload ? _getSessionSceneCache(sid) : null;" in load
    assert "data = {session:_restoreSessionScene(cachedScene)};" in load
    assert "void _validateCachedSessionScene(sid, cachedScene);" in load
    assert load.index("data = {session:_restoreSessionScene(cachedScene)};") < load.index("void _validateCachedSessionScene(sid, cachedScene);")


def test_cold_switch_uses_one_metadata_plus_messages_request():
    load = _block("async function loadSession(sid)", "// ── Handoff hint logic")
    assert "messages=0&resolve_model=0" not in load
    assert "messages=1&resolve_model=0&msg_limit=${_INITIAL_MSG_LIMIT}" in load
    assert "_applyLoadedSessionMessages(data.session, sid);" in load


def test_draft_switch_waits_only_when_payload_changed():
    save_now = _block("function _saveComposerDraftNow", "// Restore composer draft")
    assert "_composerDraftPayloadSignature" in save_now
    assert "return Promise.resolve(false);" in save_now
    load = _block("async function loadSession(sid)", "const _keepStaleUntilLoaded")
    assert "const draftSave = _saveComposerDraftNow" in load
    assert "if (draftSave) await draftSave;" in load


def test_sessions_changed_invalidates_target_scene():
    sse = _block("_sessionEventsSSE.addEventListener('sessions_changed'", "_sessionEventsSSE.onerror")
    assert "_invalidateSessionSceneCache(payload.session_id);" in sse
