# Daily work navigation

SynPulse members have seven primary destinations: Chats, Bots, Projects,
Scheduled tasks, Skills library, Connections and My approvals. A destination
is omitted when its feature permission is absent. Settings remains a utility
for personal preferences and request history.

Navigation is derived from the caller's effective access returned by
`/api/governance/me`. Wildcard, `governance:write` or `governance:admin` grants
select the complete administrator navigation. Explicit owner/admin roles and
bootstrap administrators follow the same administrative identity as ownership.
Read-only governance access and wildcard route allowlists do not select the
administrator interface. Policy mode alone never promotes a signed-in member;
auth-disabled local single-user mode keeps the complete interface. Backend
feature permission checks remain independent.

This intentionally replaces permission-only navigation: ordinary members no
longer see every technical panel for which they happen to hold read access.
If effective access cannot be read, navigation falls back to the member surface;
backend calls remain independently authorized. Optional diagnostics and gateway
health checks do not run for callers missing their respective grants.

My approvals reads only `/api/governance/approvals/mine`, whose backend scopes
requests to the authenticated caller. Its primary view contains pending
requests; history remains available under Settings. It never fetches the
administrator approval queue.

Bot cards support keyboard activation. The detail view presents identity and
configuration links first, with technical bindings under a disclosure. Editing
identity requires the effective `profiles:admin` grant; the backend retains its
own grant and bot-scope checks. Narrow screens stack the editor fields and keep
configuration buttons touch-sized.

Frontend labels use SynPulse. Engine import names, URLs, storage keys, locale
registration hooks and the existing synthpulse skin value remain compatible.

Validation: `./scripts/test.sh tests/test_synpulse_role_navigation.py
tests/test_governance_nav_visibility.py tests/test_synpulse_own_approvals_ui.py`.
Browser checks should use distinct signed-in member and administrator accounts,
at desktop and mobile widths. Verify that a member cannot see another person's
approval requests, and that refreshing retains the correct navigation.

## Conversation controls

Members start with the bot, files, workspace and conversation members in reach.
Model, reasoning, mode, toolsets and provider quota controls are disclosed through
Settings > Appearance > Show advanced chat controls. This preference is stored
per signed-in email in the browser and does not change backend permissions or
the selected model. Administrators retain all composer controls.

The CLI/WebUI source filter remains an administrative control. Members use the
WebUI conversation list, with the same server-side ownership filtering. A stale
CLI-only preference from another account is reset when member navigation loads.
Navigation labels are always visible for members, so the redundant Show labels
toggle is hidden.

Bot lists and pickers request /api/profiles?fast=1: cold skill counts are omitted while the server computes them in its bounded background worker. Pending counts are never rendered as zero; reopening the list refreshes counts without polling.

Personal memory is an eighth daily-use area after My approvals. It requires
chat:use, matching the private memory API. It does not require or grant access
to shared memory administration, logs or governance. Existing admin navigation
remains unchanged.
