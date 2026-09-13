# Shared project lifecycle

Projects retain their existing IDs and projects.json ownership. Authenticated creation through both the Projects hub and existing sidebar endpoint creates one shared-project record, with explicit human members, assigned stable bot profile IDs, revision, and a dedicated server-owned workspace. Owners and administrators resolved by the shared ownership.identity_is_admin contract manage membership. Joining a project never grants a global bot/tool permission.

The owner can adopt a legacy personal project using the hub's membership controls. Its old conversations remain private: only new project group conversations receive the persisted project_shared marker. New group chats are created through /api/projects/chat, select from assigned bots that their authenticated sender may already use, and keep the project association. Moving a shared chat out of its project or changing a separate per-chat roster is refused.

For every project conversation, session detail/status/start and list responses consult current project membership. Worker entry checks membership and the selected bot again. Project file calls hold the project membership lock through the operation, require files:read/write, use a server-owned dirfd and O_NOFOLLOW, reject traversal/hidden files and symlinks, cap files at 5 MB, and refuse accidental overwrite. Archiving keeps a tombstone and retains files; it revokes access without a destructive recursive filesystem deletion.

The agent receives only an in-memory project workspace and authorization callback, never a permanent grant or serialized credential. Each contained file-tool invocation rechecks the current original human, project roster, bot profile grant and files capability. The engine retains ordinary tool/profile/denied-glob checks; project authorization only supplies the specific workspace root. Private paths, symlink escapes and terminal/MCP tools receive no additional permission. Older engines lacking the callback fields refuse project execution rather than silently broadening access.

Tests exercise actual GET/POST dispatch using separate authenticated identities and isolated state. They cover owner/member/outsider, immediate revocation and deleted-project tombstones, revision conflicts, scoped file uploads/downloads, path attacks, absent capabilities, both create entrypoints and private legacy adoption. A separate integration test binds the real engine context and checks read/write policy inside, private paths outside, symlinks, and post-bind membership revocation. No real colleague is added or messaged by this verification.

Authenticated SSO group claims travel with the original actor into the worker and invocation callback. Connected SSE consumers recheck access before live events and each journal replay event. All project read-modify-write paths, including legacy routes, cron and webhook creation, share one transaction lock so stale writes cannot restore removed members. New empty groups persist owner and both rosters before returning their creation response.

## Reliable creation and existing conversations

SynthPulse's sidebar project shortcut and the Projects team panel now use the
same shared-conversation creation flow. The flow refreshes the selected project,
checks its available bot choices, shows progress, and uses `/api/projects/chat`.
The personal `/api/session/new` endpoint keeps rejecting shared projects.

A per-tab request reference survives a refresh or a lost response. The server
maps that reference together with the current actor and project to a reserved
session ID; the session is saved atomically before success. A retry rechecks
current membership and bot permissions and returns the same session without
rewriting its messages. Concurrent project creates and session deletes use the
same project transaction lock, then the session cache lock. Explicit IDs are
checked again at cache registration, so they cannot overwrite another record.
Deleted or changed creation scopes return a specific conflict code. Only that
confirmed outcome allows the UI to start a new intent after explaining that the
next click creates a separate conversation; uncertain outcomes keep their key.

Choosing a shared project in an existing conversation's project picker offers
**Create a separate project conversation**. The confirmation explains its audience
and that the existing transcript, attachments and access remain unchanged. No
messages, attachment links, credentials or hidden context are copied. Bulk moves
to a shared project open that project with the same explanation. This is an
actionable alternative; a private organisational association with a shared project
is still not implemented. Shared conversations still cannot be moved out of their
project. These server guards have not been relaxed.

Local validation uses `tests/test_project_conversation_creation.py` for real
request dispatch and `tests/project_conversation_logic.cjs` for navigation,
duplicate calls and retry state. The rendered fixture and durable script are
`tests/fixtures/project-conversation.html` and
`tests/project_conversation_browser.cjs`. Serve this repository on a loopback-only
port and set `PROJECT_QA_ORIGIN` to that origin when running the browser script.
The fixture executes production frontend functions with synthetic API responses;
it proves rendered controls, not production membership, provider execution or
successful live delivery. Keep those live checks separate.

### Project actions while team lists load

The Projects team panel renders **New group conversation** as soon as the
project detail is available. Loading people, bot profiles or project files no
longer delays that action. The button still calls the existing creation flow,
which refreshes project membership and bot availability before sending the
authenticated create request. Loading the lists does not replace a busy button
or reset its duplicate-click protection.

Saving members and bots requires complete people and profile responses. Failed
or malformed lists show an error inside the team section without enabling an
incomplete update or removing the conversation action. A file-list failure does
not prevent editing a fully loaded team. Each metadata load owns a generation
and a specific DOM host; a new load or replacement host invalidates older
success and error responses, including returning to the same project.

`tests/test_project_team_readiness.py` runs the complete `static/projects.js`
inside Chromium through `tests/project_team_readiness_browser.cjs`. The 28
scenario executions cover pending, failed and malformed lists, clicks through
the real conversation action, metadata arriving during creation, A-to-B-to-A
navigation and a same-host revision reload at desktop and narrow widths. All
network requests are intercepted; project APIs and session navigation use
synthetic fixtures. This proves the rendered action and request contract, not
production membership, live provider execution or the full application layout.

Run `./scripts/test.sh tests/test_project_team_readiness.py -q` with Python
Playwright and Chromium installed; the wrapper discovers its existing Node
driver package. `PLAYWRIGHT_MODULE` and `CHROMIUM_PATH` can point to an existing
local installation instead; `PROJECT_QA_SCREENSHOT_DIR` captures before/after
fixture views without using the user's browser. Existing project dispatch,
creation, hub and shortcut tests remain separate neighboring checks.
