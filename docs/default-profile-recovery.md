# Default profile recovery

The browser profile switch uses the fast profile catalogue, so the normal fast
path does not synchronously scan every bot's skills before setting the profile
cookie. The switch response filters the returned catalogue with the same current
actor checks used by `GET /api/profiles`. An allowed switch therefore does not
disclose another person's private or revoked bot metadata.

The earlier one-way default-profile denial was already corrected in
`571c11f9cc184657b49abf93ad9bedf633a437fe`: a scoped user can return to the ambient,
unmanaged default profile. Managed bot ACLs still apply before that fallback.
This change does not alter those ACLs, hidden-profile preferences, runtime
capabilities, session ownership, or access to legacy unowned conversations.

## Reproduction and checks

`tests/test_default_profile_recovery.py` injects a synthetic governed developer,
their managed bot, another person's private bot, and four in-memory chats. It
drives the real profile list/switch handlers and sidebar filtering. It verifies:

- Returning to default restores only that developer's morning conversation;
  switching back restores their own bot conversation.
- Another person's and unowned conversations stay hidden; originals are unchanged.
- The switch response omits inaccessible bot metadata and respects a revoked ACL.
- A failing full skill catalogue scan does not block the fast switch path.

Before the change the historical roundtrip passed, while the new response-scope
and full-scan-dependency regressions failed. These are distinct findings, not a
claim that the historical default denial was newly fixed.

For the rendered picker and switch orchestration, serve the repository only on
loopback and open `tests/fixtures/default-profile-recovery.html`. The fixture
uses actual `renderProfileDropdown`, `closeProfileDropdown`, and
`switchToProfile` source functions with explicitly synthetic API, session-list,
and session-creation adapters. Its durable script is
`tests/default_profile_recovery_browser.cjs`; set `PROFILE_QA_ORIGIN` to the
loopback server and use the existing Playwright installation. Run at desktop
and mobile widths: open own chat, choose Slow switch, pick SynthPulse, check
disabled chip/loading list, complete the switch, open Morning conversation,
try Denied switch, check restored list/chip, and switch successfully back.

This fixture does not prove live account access, provider execution, or recovery
of unowned historical sessions. A signed-in affected-account production journey
remains a separate verification step; do not reassign private history to make
the test pass.
