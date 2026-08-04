"""Identity-aware session store tests (governance port, builder B2).

The session store values are either a plain float expiry (legacy anonymous
sessions, kept forever for rollback safety) or an identity dict
{"exp": float, "email": str, "groups": [str], "claims_subset": dict,
"method": str}. These tests cover both formats end to end: load, verify,
prune, CSRF derivation, thread-local identity staging, and the
get_session_identity accessor.

All state is isolated to a per-test tmp_path; the real STATE_DIR session
file and signing keys are never touched.
"""
import hashlib
import hmac
import json
import time

import pytest

import api.auth as auth


@pytest.fixture
def isolated_auth(tmp_path, monkeypatch):
    """Bind api.auth's STATE_DIR-derived globals to a fresh tmp dir."""
    monkeypatch.setattr(auth, 'STATE_DIR', tmp_path)
    monkeypatch.setattr(auth, '_SESSIONS_FILE', tmp_path / '.sessions.json')
    monkeypatch.setattr(auth, '_LOGIN_ATTEMPTS_FILE', tmp_path / '.login_attempts.json')
    monkeypatch.setattr(auth, '_PBKDF2_KEY_CACHE', None)
    monkeypatch.setattr(auth, '_SIGNING_KEY_CACHE', None)
    saved = dict(auth._sessions)
    auth._sessions.clear()
    auth._PENDING_IDENTITY.value = None
    try:
        yield auth
    finally:
        auth._sessions.clear()
        auth._sessions.update(saved)
        auth._PENDING_IDENTITY.value = None


def _cookie_for(token: str) -> str:
    sig = hmac.new(auth._signing_key(), token.encode(), hashlib.sha256).hexdigest()
    return f"{token}.{sig}"


def _insert(token: str, entry) -> None:
    with auth._SESSIONS_LOCK:
        auth._sessions[token] = entry


# ── Legacy float entries keep working unchanged ─────────────────────────────

def test_legacy_float_entry_verifies(isolated_auth):
    token = 'a' * 64
    _insert(token, time.time() + 3600)
    cookie = _cookie_for(token)
    assert auth.verify_session(cookie) is True
    # Anonymous sessions carry no identity
    assert auth.get_session_identity(cookie) is None
    # The entry stays a float (no in-place migration)
    assert isinstance(auth._sessions[token], float)


def test_legacy_float_entry_expiry_and_prune(isolated_auth):
    live, dead = 'b' * 64, 'c' * 64
    _insert(live, time.time() + 3600)
    _insert(dead, time.time() - 10)
    auth._prune_expired_sessions()
    assert live in auth._sessions
    assert dead not in auth._sessions
    assert auth.verify_session(_cookie_for(dead)) is False


def test_dict_entry_expiry_and_prune(isolated_auth):
    live, dead = 'd' * 64, 'e' * 64
    _insert(live, {'exp': time.time() + 3600, 'email': 'x@y.z',
                   'groups': [], 'claims_subset': {}, 'method': 'local'})
    _insert(dead, {'exp': time.time() - 10, 'email': 'x@y.z',
                   'groups': [], 'claims_subset': {}, 'method': 'local'})
    auth._prune_expired_sessions()
    assert live in auth._sessions
    assert dead not in auth._sessions
    assert auth.verify_session(_cookie_for(live)) is True
    assert auth.get_session_identity(_cookie_for(dead)) is None


def test_malformed_entry_treated_as_expired(isolated_auth):
    # A dict without a numeric exp resolves to 0.0 and gets pruned
    assert auth._session_expiry({'email': 'x@y.z'}) == 0.0
    assert auth._session_expiry('garbage') == 0.0
    assert auth._session_expiry({'exp': 'soon'}) == 0.0


# ── Session file round-trip, mixed formats ──────────────────────────────────

def test_mixed_format_sessions_file_survives_load(isolated_auth, tmp_path):
    now = time.time()
    (tmp_path / '.sessions.json').write_text(json.dumps({
        'float_valid': now + 3600,
        'float_expired': now - 10,
        'dict_valid': {'exp': now + 3600, 'email': 'user@example.com',
                       'groups': ['g1'], 'claims_subset': {}, 'method': 'oidc'},
        'dict_expired': {'exp': now - 10, 'email': 'old@example.com',
                         'groups': [], 'claims_subset': {}, 'method': 'oidc'},
        'garbage_value': 'not-a-session',
        42: now + 3600,  # json coerces to "42" string key; still a float entry
    }), encoding='utf-8')
    loaded = auth._load_sessions()
    assert 'float_valid' in loaded
    assert 'dict_valid' in loaded
    assert loaded['dict_valid']['email'] == 'user@example.com'
    assert 'float_expired' not in loaded
    assert 'dict_expired' not in loaded
    assert 'garbage_value' not in loaded


def test_dict_entry_roundtrips_through_save_and_load(isolated_auth):
    identity = {'email': 'roundtrip@example.com', 'groups': ['sw-engineering'],
                'claims_subset': {'sub': 'abc'}, 'method': 'oidc'}
    cookie = auth.create_session(identity)
    token = cookie.rsplit('.', 1)[0]
    loaded = auth._load_sessions()
    assert token in loaded
    entry = loaded[token]
    assert entry['email'] == 'roundtrip@example.com'
    assert entry['groups'] == ['sw-engineering']
    assert entry['claims_subset'] == {'sub': 'abc'}
    assert entry['method'] == 'oidc'
    assert entry['exp'] > time.time()


# ── create_session identity resolution ──────────────────────────────────────

def test_create_session_defaults_to_local_identity(isolated_auth):
    cookie = auth.create_session()
    ident = auth.get_session_identity(cookie)
    assert ident == {'email': 'michael@synthwave.solutions', 'groups': [],
                     'claims_subset': {}, 'method': 'local'}


def test_password_identity_env_override_lowercased(isolated_auth, monkeypatch):
    monkeypatch.setenv('HERMES_WEBUI_PASSWORD_IDENTITY', '  Team@Synthwave.Solutions ')
    cookie = auth.create_session()
    ident = auth.get_session_identity(cookie)
    assert ident['email'] == 'team@synthwave.solutions'
    assert ident['method'] == 'local'


def test_explicit_identity_wins_over_staged(isolated_auth):
    auth.stage_session_identity({'email': 'staged@example.com', 'groups': [],
                                 'claims_subset': {}, 'method': 'oidc'})
    cookie = auth.create_session({'email': 'explicit@example.com', 'groups': [],
                                  'claims_subset': {}, 'method': 'oidc'})
    assert auth.get_session_identity(cookie)['email'] == 'explicit@example.com'


def test_staged_identity_consumed_exactly_once(isolated_auth):
    staged = {'email': 'sso@example.com', 'groups': ['sw-admins'],
              'claims_subset': {'sub': 's-1', 'name': 'SSO User'}, 'method': 'oidc'}
    auth.stage_session_identity(staged)
    first = auth.create_session()
    second = auth.create_session()
    ident1 = auth.get_session_identity(first)
    assert ident1['email'] == 'sso@example.com'
    assert ident1['groups'] == ['sw-admins']
    assert ident1['method'] == 'oidc'
    # The staged identity is gone; the second session falls back to local
    ident2 = auth.get_session_identity(second)
    assert ident2['method'] == 'local'
    assert ident2['email'] == 'michael@synthwave.solutions'


def test_identity_exp_key_cannot_override_session_expiry(isolated_auth):
    cookie = auth.create_session({'email': 'x@y.z', 'groups': [],
                                  'claims_subset': {}, 'method': 'local',
                                  'exp': 1.0})
    assert auth.verify_session(cookie) is True
    token = cookie.rsplit('.', 1)[0]
    assert auth._sessions[token]['exp'] > time.time()
    # exp never leaks into the identity view
    assert 'exp' not in auth.get_session_identity(cookie)


# ── get_session_identity edge cases ──────────────────────────────────────────

def test_get_session_identity_invalid_cookie(isolated_auth):
    assert auth.get_session_identity('') is None
    assert auth.get_session_identity('no-dot-here') is None
    assert auth.get_session_identity('f' * 64 + '.' + '0' * 64) is None
    # Valid token, wrong signature
    cookie = auth.create_session()
    token = cookie.rsplit('.', 1)[0]
    assert auth.get_session_identity(token + '.' + '0' * 64) is None


def test_get_session_identity_expired_dict_entry(isolated_auth):
    token = '9' * 64
    _insert(token, {'exp': time.time() - 5, 'email': 'x@y.z',
                    'groups': [], 'claims_subset': {}, 'method': 'oidc'})
    assert auth.get_session_identity(_cookie_for(token)) is None
    assert token not in auth._sessions  # lazily pruned


# ── Cookie mechanics unchanged for both entry formats ────────────────────────

def test_csrf_derivation_unchanged_for_both_formats(isolated_auth):
    float_token = '1' * 64
    _insert(float_token, time.time() + 3600)
    float_cookie = _cookie_for(float_token)
    dict_cookie = auth.create_session()

    for cookie in (float_cookie, dict_cookie):
        assert auth.verify_session(cookie) is True
        token = cookie.rsplit('.', 1)[0]
        expected = hmac.new(auth._signing_key(), f"csrf:{token}".encode(),
                            hashlib.sha256).hexdigest()
        assert auth.csrf_token_for_session(cookie) == expected
        assert auth.verify_csrf_token(cookie, expected) is True
        assert auth.verify_csrf_token(cookie, 'nope') is False


def test_invalidate_session_works_for_dict_entries(isolated_auth):
    cookie = auth.create_session()
    assert auth.verify_session(cookie) is True
    auth.invalidate_session(cookie)
    assert auth.verify_session(cookie) is False
    assert auth.get_session_identity(cookie) is None
