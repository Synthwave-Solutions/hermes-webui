# Personal clarification preferences

Settings → Preferences → Clarification style lets a signed-in user choose
**Balanced** or **Fewer questions**. The latter asks the assistant to use sensible
defaults for reversible details and ask when missing information prevents correct
work. A conversation can inherit the user's default or have a separate choice.
“Use my default” removes that conversation's override. Without an open conversation,
only the user default is editable.

These controls affect clarification style. They do not accept governance requests,
grant permissions, expand whitelist/blacklist rules, or replace a required approval.
Only fixed server-authored prompt text is emitted; the settings cannot inject a
free-form system prompt. Preferences apply when the next text turn's prompt is
built and when a new realtime voice call is created. They do not rewrite an
existing call's instructions or promise model compliance.

## Scope and persistence

`GET/POST /api/interaction/preferences` require `chat:use`. The server selects the
authenticated actor; request bodies cannot name another user. A supplied session
requires current membership, including when reading the prompt overlay. An admin
does not become another conversation owner's identity. Shared-chat participants
keep independent preferences; changes to one user's style do not affect peers.

The store is separate from profile configuration, personal memory, governance and
chat history. Each actor has a hashed directory under personal context; no legacy
chat ownership is reassigned. A versioned JSON document holds the user default,
conversation overrides and one revision. A save compares that revision under a
bounded cross-process lock, rechecks membership, and atomically replaces the file.
Stale revisions receive409 and require reload. Malformed or unavailable storage is
preserved and produces a bounded error; prompt assembly continues without the
optional overlay. Symlinks and nonregular store/lock files are rejected.

This implementation requires safe POSIX file operations for persistence. When
`fcntl` or `O_NOFOLLOW` is unavailable, it explicitly refuses unsafe operations;
it does not emulate CAS with an unlocked write. Windows preference persistence
is not supported by this change. Core chat guidance remains available.

The frontend binds loaded/saved values to a conversation ID and request generation.
A late response cannot enable controls for a newly selected conversation. A save
error may follow a successful server commit, so the UI requires reading saved
preferences before another write. These settings do not change an in-progress
conversation or stream's ownership/profile.

## Verification

Run the isolated behavior and prompt checks through the repository test runner:

```sh
./scripts/test.sh -q tests/test_interaction_preferences.py tests/test_webui_interaction_context.py
```

The rendered fixture extracts the actual form from `static/index.html`, serves
the production `static/interaction_preferences.js`, and uses the real preference
store in a fresh temporary directory. Its Alice/Bob selector supplies explicitly
synthetic identities. It does not replace a signed-in production account test or
test governance authentication, session revocation, or model/provider behavior;
the backend tests cover membership and actor isolation separately.

Start the fixture from the repository with the existing supported test environment:

```sh
.venv/bin/python tests/interaction_preferences_fixture.py 8936
```

Then, in CI or an authorized browser-testing environment with existing Playwright:

```sh
INTERACTION_QA_ORIGIN=http://127.0.0.1:8936 node tests/interaction_preferences_browser.cjs
```

`PLAYWRIGHT_MODULE` may point to the existing installation. The script verifies
the fixture page before making changes, accepts loopback origins only, launches
an isolated browser context, and closes its pages afterward. Stop the fixture
server when finished. It never accesses production state or providers.

At desktop1360px and mobile390px the script covers persistence after reload,
Alice/Bob isolation, per-conversation inheritance and reset, no-conversation
editing, a stale save after navigation, delayed GET/POST responses, offline
failure, a committed write whose response is lost, and actual revision conflicts
between two tabs. The lost-response case lets the fixture server commit via
`route.fetch()` before aborting the browser response; it is distinct from the
fixture's immediate offline selector. In sessions requiring CUA, execute the
actual interactions with CUA and report them separately from this CI script.
