"""B6 gap suite: reference assertions not yet mirrored by the other builders.

Covers two areas from the reference dashboard_governance tests:

1. OIDC claims -> staged session identity (reference
   test_dashboard_auth_session_claims.py): complete_authorization_code_flow
   must stage a bounded identity dict (lowercased email, string-coerced
   groups with a roles fallback, claims_subset limited to a fixed key set,
   never tokens or protocol claims) that the following create_session()
   consumes into an identity-aware session entry.

2. Background process usage cap (reference
   test_background_process_cap_counts_background_terminal): terminal calls
   with background=True count against the background_processes counter.

All state is isolated: api.auth globals are rebound to tmp_path and the
usage state file lives under HERMES_HOME=tmp_path. No network: every
auth_oidc collaborator that would touch the IdP is monkeypatched.
"""
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.auth as auth  # noqa: E402
import api.auth_oidc as auth_oidc  # noqa: E402
from api.governance.models import EffectiveAccess, GovernanceSubject, GrantSet  # noqa: E402
from api.governance.usage import check_usage_caps, record_tool_usage  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────────

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


_CFG = {
    'issuer': 'https://idp.example.test',
    'client_id': 'client-abc',
    'scopes': ['openid', 'email', 'profile'],
    'allow_claim': None,
    'allow_values': [],
}

_DISCOVERY = {
    'issuer': 'https://idp.example.test',
    'token_endpoint': 'https://idp.example.test/token',
    'jwks_uri': 'https://idp.example.test/jwks',
}


def _run_flow(monkeypatch, claims: dict) -> dict:
    """Drive complete_authorization_code_flow with every IdP hop stubbed."""
    monkeypatch.setattr(auth_oidc, '_require_oidc_config', lambda: dict(_CFG))
    monkeypatch.setattr(auth_oidc, '_consume_pending_flow', lambda state: {
        'created_at': time.time(),
        'nonce': 'test-nonce',
        'code_verifier': 'test-verifier',
        'next_path': '/',
    })
    monkeypatch.setattr(auth_oidc, '_get_discovery_document', lambda issuer: dict(_DISCOVERY))
    monkeypatch.setattr(auth_oidc, '_resolve_redirect_uri', lambda cfg, base: 'https://app.example.test/api/auth/oidc/callback')
    monkeypatch.setattr(auth_oidc, '_post_form_json', lambda url, form: {'id_token': 'stub-id-token'})
    monkeypatch.setattr(auth_oidc, '_validate_id_token', lambda *a, **kw: dict(claims))
    monkeypatch.setattr(auth_oidc, '_enforce_allowlist', lambda *a, **kw: None)
    return auth_oidc.complete_authorization_code_flow('https://app.example.test', 'state', 'code')


_FULL_CLAIMS = {
    'sub': 'user-123',
    'email': 'Freelancer@Example.TEST',
    'name': 'Free Lancer',
    'preferred_username': 'freelancer',
    'groups': ['sw-freelancers', 'sw-viewers'],
    # Protocol/extra claims that must never reach the session store
    'iss': 'https://idp.example.test',
    'aud': 'client-abc',
    'nonce': 'test-nonce',
    'exp': 9999999999,
    'iat': 1,
    'at_hash': 'xyz',
    'department': 'engineering',
}


# ── OIDC claims -> staged identity ──────────────────────────────────────────

def test_oidc_flow_stages_bounded_identity(isolated_auth, monkeypatch):
    result = _run_flow(monkeypatch, _FULL_CLAIMS)
    assert result['next_path'] == '/'
    assert result['subject'] == 'user-123'

    staged = auth._pop_pending_identity()
    assert staged is not None
    # Email is lowercased for stable policy lookups
    assert staged['email'] == 'freelancer@example.test'
    assert staged['groups'] == ['sw-freelancers', 'sw-viewers']
    assert staged['method'] == 'oidc'
    # claims_subset stays bounded: only the fixed allowlist of keys
    assert set(staged['claims_subset']) <= {'sub', 'email', 'name', 'preferred_username'}
    assert staged['claims_subset']['sub'] == 'user-123'
    # Protocol claims, extras, and anything token-shaped never reach the store
    flat = repr(staged)
    for forbidden in ('iss', 'aud', 'nonce', 'at_hash', 'department', 'stub-id-token'):
        assert forbidden not in staged['claims_subset']
    assert 'id_token' not in flat and 'access_token' not in flat


def test_string_groups_claim_is_wrapped_to_list(isolated_auth, monkeypatch):
    claims = dict(_FULL_CLAIMS, groups='sw-viewers')
    _run_flow(monkeypatch, claims)
    staged = auth._pop_pending_identity()
    assert staged['groups'] == ['sw-viewers']


def test_roles_claim_is_fallback_when_groups_absent(isolated_auth, monkeypatch):
    claims = {k: v for k, v in _FULL_CLAIMS.items() if k != 'groups'}
    claims['roles'] = ['operator']
    _run_flow(monkeypatch, claims)
    staged = auth._pop_pending_identity()
    assert staged['groups'] == ['operator']


def test_no_group_claims_yields_email_only_identity(isolated_auth, monkeypatch):
    claims = {k: v for k, v in _FULL_CLAIMS.items() if k not in ('groups', 'roles')}
    _run_flow(monkeypatch, claims)
    staged = auth._pop_pending_identity()
    assert staged['email'] == 'freelancer@example.test'
    assert staged['groups'] == []


def test_non_string_group_values_are_coerced_to_str(isolated_auth, monkeypatch):
    claims = dict(_FULL_CLAIMS, groups=[123, 'sw-viewers'])
    _run_flow(monkeypatch, claims)
    staged = auth._pop_pending_identity()
    assert staged['groups'] == ['123', 'sw-viewers']


def test_oidc_flow_end_to_end_into_session(isolated_auth, monkeypatch):
    """The staged identity is consumed by the login route's create_session()."""
    _run_flow(monkeypatch, _FULL_CLAIMS)
    cookie = auth.create_session()  # same zero-argument call routes.py makes
    identity = auth.get_session_identity(cookie)
    assert identity is not None
    assert identity['email'] == 'freelancer@example.test'
    assert identity['groups'] == ['sw-freelancers', 'sw-viewers']
    assert identity['method'] == 'oidc'
    # Staged identity is consumed exactly once: a second session falls back
    # to the local identity mapping, not the previous OIDC login
    second = auth.get_session_identity(auth.create_session())
    assert second['method'] == 'local'


# ── Background process usage cap ────────────────────────────────────────────

def _usage_ctx(caps: dict) -> SimpleNamespace:
    access = EffectiveAccess(
        subject=GovernanceSubject(email='operator@example.test'),
        mode='enforce',
        grants=GrantSet(usage_caps=caps),
    )
    return SimpleNamespace(subject=access.subject, access=access)


def test_background_process_cap_counts_background_terminal(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    ctx = _usage_ctx({'daily_background_processes': 1})

    assert check_usage_caps(ctx, 'terminal', {'background': True}).allowed is True
    record_tool_usage(ctx, 'terminal', {'background': True})

    decision = check_usage_caps(ctx, 'terminal', {'background': True})
    assert decision.allowed is False
    assert decision.reason == 'daily_background_processes_exceeded'


def test_foreground_terminal_does_not_count_against_background_cap(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    ctx = _usage_ctx({'daily_background_processes': 1})

    record_tool_usage(ctx, 'terminal', {'background': True})
    # Foreground terminal calls skip the background counter entirely
    assert check_usage_caps(ctx, 'terminal', {}).allowed is True
    assert check_usage_caps(ctx, 'terminal').allowed is True
