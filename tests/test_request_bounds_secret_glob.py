"""An administrator decides secret-file exceptions from the queue (14-09-2026).

Two access requests from a blacklist-mode account (one exact path, once as
`~/...` and once absolute) answered "forbidden" on Approve while the button
was offered: grant_within_bounds refused every secret_glob for a managed
account. The exception lands on one person's files.allow_globs for one path,
so it is decided like any other grant; only an explicit per-person deny on
that path stays out of reach.
"""
from copy import deepcopy

from api.governance.loader import parse_governance_policy
from api.governance.request_bounds import grant_within_bounds

ME = "vansh@example.test"
PATH = "/home/synthwavehq/.config/synthwave/clients/makro/metro-state.json"
BASE = {
    "mode": "enforce",
    "roles": {"member": {"grants": {
        "permissions": ["chat:use", "files:read", "terminal:use"],
        "routes": ["*"], "profiles": ["vansh"],
        "tools": {"builtins": ["*"]},
        "files": {"denied_globs": ["**/.hermes/**", "**/.config/**"], "read_roots": ["/home/synthwavehq"]},
    }}},
    "users": {ME: {"roles": ["member"], "access_mode": "blacklist", "access_level": "elevated"}},
}


def policy(**entry):
    raw = deepcopy(BASE)
    raw["users"][ME].update(entry)
    return parse_governance_policy(raw)


def payload(value=PATH):
    return {"email": ME, "gkind": "secret_glob", "value": value}


def test_a_blacklist_account_secret_exception_is_approvable():
    assert grant_within_bounds(policy(), payload())


def test_the_tilde_spelling_of_the_same_file_is_approvable():
    assert grant_within_bounds(policy(), payload("~/.config/synthwave/clients/makro/metro-state.json"))


def test_an_explicit_per_person_deny_on_that_path_stays_closed():
    assert not grant_within_bounds(policy(deny={"files": {"denied_globs": ["**/makro/**"]}}), payload())
    assert not grant_within_bounds(
        policy(deny={"files": {"denied_globs": ["**/makro/**"]}}),
        payload("~/.config/synthwave/clients/makro/metro-state.json"),
    )


def test_a_deny_elsewhere_does_not_block_this_file():
    assert grant_within_bounds(policy(deny={"files": {"denied_globs": ["**/bunq*"]}}), payload())


def test_a_whitelist_account_is_decided_the_same_way():
    assert grant_within_bounds(policy(access_mode="whitelist"), payload())


def test_an_unmanaged_account_is_unchanged():
    assert grant_within_bounds(policy(access_mode="", access_level=""), payload())
