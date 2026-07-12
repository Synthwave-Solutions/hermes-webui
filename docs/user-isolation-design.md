# Per-user data isolation and skill approvals (design)

Date: 2026-07-12. Branch: feat/user-isolation. Builds on the merged governance RBAC layer (api/governance/).

## Requirement (from Michael)

Every logged-in user gets their own account experience: own chats, own projects and project labels. Non-admins must never see another user's chats (specifically: Steve and Hrishi must not see Michael's chats). Every user may add their own skills; skills added by a non-admin also surface to the admin. The admin can, from the admin account, approve/allow skills, MCPs, CLIs and so on per user.

## Decisions (locked)

1. **Ownership field**: `owner_email` (lowercased string or None) on chat sessions and on projects. Stamped at creation time from the authenticated identity (`api.governance.enforce._request_identity(handler)` -> `email`). Password login carries identity too (`HERMES_WEBUI_PASSWORD_IDENTITY`, default michael@synthwave.solutions), so password sessions are owned by Michael.
2. **Visibility rule** (always on, independent of governance `mode`):
   - Admins (see 4) see ALL sessions and projects.
   - Non-admin sees only rows where `owner_email == identity.email`.
   - Legacy rows without `owner_email` (all of Michael's existing chats, cron/CLI-imported sessions with no interactive creator) are **admin-only**. This is the core protection: Steve/Hrishi can never see pre-existing chats.
   - No identity on the request (auth disabled / internal): behave as admin (auth-disabled deployments keep working unchanged).
3. **Escape hatch**: env `HERMES_WEBUI_USER_ISOLATION=0` disables the ownership filter entirely (default ON). No lockout risk either way: password identity default resolves to Michael who is a bootstrap admin.
4. **Admin determination**: helper `identity_is_admin(identity)` in `api/governance/enforce.py` (or resolver): True when the resolved EffectiveAccess has bootstrap-admin grant source, or role owner/admin wildcard routes, or `governance:write` permission. Works in `report_only` and even `off` mode (resolver is mode-independent). Michael, Yaser, Odis resolve admin per the live policy.
5. **Enforcement points** (data layer, mirrors the existing profile guard, does NOT replace it, both apply):
   - `/api/sessions` list build: filter rows by ownership scope; cache key must include the ownership scope (e.g. `admin` vs the email) so users never get each other's cached lists.
   - `_session_visible_to_active_profile` / `_session_id_visible_to_request_profile` / `_guard_request_session_visibility`: extend with an ownership check using the request identity (404 on foreign sessions, same as profile mismatch).
   - Single-session reads (`/api/session`, stream, export, events): already funnel through the guards above; verify each and add explicit checks where the guard is bypassed (SSE streams that push session rows must filter per connection identity).
   - `/api/projects` list + create/rename/delete: stamp owner on create, filter list, 404 foreign mutations for non-admins.
   - Session creation points stamp owner: `/api/chat/start`, `/api/session/import`, `/api/session/import_cli`.
6. **Skills ownership**: sidecar registry `STATE_DIR/skill_ownership.json` mapping skill key (`category/name` or `name`) -> `{owner_email, added_at, status}` with status `pending` or `approved`.
   - Skill created via `/api/skills/save` by a non-admin: written to disk as today, registered with `status: pending`, immediately visible and usable to its owner.
   - Skill list (`/api/skills`): admin sees everything (pending items flagged `added_by`); non-admin sees global skills (no registry entry, existing behaviour incl. per-profile disabled filter) + their own skills; other users' pending skills are hidden.
   - Admin approval: approve -> status `approved` (skill becomes global, visible to everyone); reject -> skill dir deleted + registry entry removed. Non-admins cannot edit/delete skills they do not own (admins can do anything).
7. **Admin approval surface** (extends the existing governance admin UI):
   - `GET /api/governance/approvals`: pending skill additions (admin-gated, same `_require_governance_admin`).
   - `POST /api/governance/approvals/decide` `{kind: "skill", key, decision: approve|reject}` (admin-gated, audited via the existing audit trail).
   - Per-user allow-lists for skills/MCP/CLI already exist in the policy (`users.<email>.grants.skills|mcp|cli`) and are editable via `/api/governance/users/update`; the UI gets a grants editor on the Users tab (textareas/simple lists for skills view/load/manage, mcp servers, cli commands) so Michael can allow MCPs/CLIs/skills per user without editing YAML.
   - New "Approvals" tab in `static/governance.js` listing pending skills with Approve/Reject buttons; badge count on the tab.
8. **Frontend**: sessions/projects/skills lists are already fetched from the filtered APIs, so isolation is server-side; UI additions are limited to the Approvals tab, an `added by <email>` badge on user-added skills (admin view), and pending-state badge for the owner.
9. **Out of scope now**: per-user MCP/CLI runtime enforcement (that is governance enforce-mode work, already built); per-user model keys; quota UI.

## Constraints

- Plain stdlib Python, match surrounding style of routes.py/models.py.
- No em or en dashes anywhere (code comments, UI strings, docs).
- Commits as `Michael Ramirez <michael@synthwave.solutions>` only, no co-author trailers.
- Never touch the live tree `/home/synthwavehq/hermes-webui`; work only in this worktree.
- Backward compatible session JSON (unknown field tolerated by old readers; new field optional).
