"""The effective-access preview must retain restrictions without granting tools."""
import pytest

from api.governance.loader import parse_governance_policy
from api.governance.models import GovernanceSubject
from api.governance.resolver import resolve_effective_access


@pytest.mark.parametrize("mode", ["blacklist", "whitelist"])
@pytest.mark.parametrize("deny_selector", [False, True])
def test_cli_review_restrictions_survive_managed_access_without_granting_commands(mode, deny_selector):
    user = {
        "roles": ["member"], "access_mode": mode, "access_level": "elevated",
        "grants": {"cli": {"approval_commands": ["touch"]}},
    }
    if deny_selector:
        user["deny"] = {"cli": {"approval_commands": ["touch"]}}
    policy = parse_governance_policy({
        "mode": "enforce", "users": {"qa@example.test": user},
        "roles": {"member": {"grants": {"cli": {
            "commands": ["printf"], "approval_commands": ["git"],
        }}}},
    })
    access = resolve_effective_access(policy, GovernanceSubject(email="qa@example.test"))
    assert access.grants.cli_approval_commands == frozenset({"git", "touch"})
    assert "touch" not in access.grants.cli_commands
    assert access.grants.cli_commands == (frozenset({"printf"}) if mode == "blacklist" else frozenset())
