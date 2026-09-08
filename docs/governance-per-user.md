# Per-user access and action approval

Governance → Users has independent access level, access mode and action approval
controls. Changes require `governance:write`; browser controls do not replace
server authorization. User edits retain the policy's optimistic `If-Match`
revision check and audit trail.

Activate the global policy's `mode: enforce` to apply these restrictions and
action reviews. `off` permits work without enforcement; `report_only` records
policy decisions without blocking. Saving per-user controls does not silently
change this global operating mode. Upgrade the WebUI and engine together before
activation, and retain an authenticated bootstrap recovery owner.

```yaml
users:
  person@example.test:
    roles: [team-member]
    access_level: user
    access_mode: whitelist
    approval:
      mode: automatic
      prompt: >-
        Allow public research and reading assigned project documents.
        Deny sharing private project content externally.
        Ask for manual review when the destination or purpose is unclear.
    grants:
      permissions: [chat:use, profiles:read]
      routes: [/api/chat*, /api/profiles*, /api/profile*]
      profiles: [assigned-profile]
      tools:
        builtins: [web_search]
    deny:
      tools:
        builtins: [execute_code]
```

The assigned role/group grants define available resources, including profiles,
workspaces, files, models, tools and command scopes. With an explicitly selected
whitelist or blacklist mode, a direct user grant cannot widen that envelope.

| Control | Behavior |
|---|---|
| User | Uses assigned work capabilities; cannot gain governance administration, terminal/arbitrary code execution, settings/provider writes or administrative permissions. |
| Elevated | Uses assigned additional operational capabilities, including an explicitly granted terminal. Governance administration stays excluded. |
| Admin | Provides the administrative capability envelope. It remains subject to the selected access mode and explicit denies. |
| Whitelist | Starts without work capabilities. Direct user grants permit only explicitly selected capabilities within the role/resource envelope. |
| Blacklist | Inherits the assigned role/resource envelope except explicit per-user denies. |
| Manual approval | Each eligible tool invocation requires a one-action human approval. Existing gateway/CLI approval interfaces carry the request. |
| Automatic approval | A configured auxiliary model applies this user's admin-authored prompt to the exact eligible tool invocation. It can accept, deny, or refer to a human. |

An explicit deny wins over wildcard allowances and all role/group grants. Tool,
MCP tool/server, route, profile, model, skill, file and command checks retain the
deny separately from the displayed effective allowlist. Roles never grant access
to unassigned profiles/workspaces implicitly. Self identity and own request
status remain reachable for an empty managed whitelist; work APIs stay denied.

Bootstrap owners are the existing recovery exception: they bypass ordinary
policy. The user editor identifies them and disables per-user controls so the
screen does not suggest they are restricted. An assignable Admin is distinct
from a bootstrap owner.

## Approval is for actions, not new privileges

The AI never edits the policy, adds whitelist capabilities, removes blacklists,
installs shared resources, publishes skills, or approves another user's work.
An action must pass current profile, bot/project, tool, argument and usage checks
before review. Review happens on the final invocation after middleware argument
changes, before the handler executes. After any wait, the current policy and
resource access are rechecked. A changed policy invalidates the old decision.

Automatic decisions use the configured `approval_advice` auxiliary-model route,
a 20-second provider timeout and a strict JSON decision/reason/confidence
contract. Missing providers, malformed responses, confidence below 0.9,
ambiguity, oversized arguments, and arbitrary-code actions go to manual review.
The request is bounded and redacted; request text is untrusted data, separate
from the administrator's prompt. There is no model tool access and no decision
cache. The prompt must be nonempty for automatic mode and at most 8,000
characters. Manual approval permits only the current action, regardless of
global YOLO, session or permanent allowlists. No connected review interface
means the action is blocked.

Both automatic and human outcomes emit `action_approval` audit records with the
subject hash, tool, session/request, unique operation, policy revision, source,
decision and reason. A failed required audit write cannot authorize execution.
Normal downstream command safety guards still apply to an approved action.
Managed users with an explicit file-root, file-pattern or environment-variable
deny cannot run host terminal or arbitrary-code tools, including the direct
terminal API. Repository-wide Git APIs are also blocked: diff, status, history
and Git operations can expose or modify files beyond a selected file grant.
Programs can derive paths internally, so command text review
cannot enforce those resource restrictions. A separately isolated execution
environment is required to combine restricted resources with arbitrary programs.
An elevated user without such denies may be granted trusted host execution;
that remains host privilege. AI and manual review never override this boundary.

The existing Governance → Approvals capability-request queue is separate.
Administrators can use it to explicitly grant missing access; the AI action
reviewer cannot turn a missing whitelist capability into permission.

## Compatibility and paired upgrade

Existing users with omitted access controls and approval settings keep their
previous behavior. Creating a new user explicitly defaults to User, Whitelist
and Manual. Saving an unrelated field on a legacy user does not silently opt
them into a new mode.
Changing only the access level preserves the existing role/group/direct grant
union, subject to the selected level's ceiling. An omitted approval setting
preserves existing approval behavior even when another access control changes.
Explicit manual approval applies independently, including when access mode and
level are left unchanged. Session-wide approval and skip-all requests cannot
bypass managed action reviews; the server enforces their one-action scope.

WebUI and Hermes Agent must be upgraded together. New runtime context payloads
carry deny, role ceiling, access mode and approval configuration. The WebUI
refuses a governed turn if the engine cannot round-trip the new controls.
The runtime evaluates current policy even when a generated profile's resources
have not yet synchronized; a profile copy is not an authorization decision.
In-process delegated agents inherit the live bot/project access checker and
policy source through the existing context propagation. Their manual actions
use the parent's connected review interface; unattended subagent autoapproval
does not satisfy manual governance. External-process payloads retain resource
ceilings but cannot carry live ACL callbacks. Bot/project actions in such a
process remain blocked until that host supplies an authoritative checker.

## API additions

User create/update and full-policy validation accept `access_level`,
`access_mode`, and `approval: {mode, prompt}`. Unknown values and malformed
prompts return validation errors. `/api/governance/users` additionally returns
`bootstrap_admins` separately from persisted entries. `/api/governance/me` and
preview include the selected controls; preview provides full policy-shaped
`grants`, `deny`, and `role_ceiling`. Own identity responses omit the review
prompt. The admin policy endpoints retain the prompt for editing.

Tests: `tests/test_governance_per_user_modes.py` in WebUI and
`tests/test_governance_per_user_actions.py` in Hermes Agent. They cover the
actual gateway queue, serialization, policy races, model parser/fallback,
concrete deny under wildcard, and final dispatch side effects. Browser evidence
and real-provider checks are separate from deterministic automated tests.
