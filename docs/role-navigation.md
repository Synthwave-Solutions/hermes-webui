# Daily work navigation

SynPulse members have seven primary destinations: Chats, Bots, Projects,
Scheduled tasks, Skills library, Connections and My approvals. A destination
is omitted when its feature permission is absent. Settings remains a utility
for personal preferences and request history.

Navigation is derived from the caller's effective permissions returned by
`/api/governance/me`. Wildcard, `governance:write` or `governance:admin` grants
select the complete administrator navigation. A role called admin without an
administrative grant does not. Read-only governance access does not select
the administrator interface. Local ungoverned and report-only deployments keep
the complete interface. Backend authorization is unchanged.

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
