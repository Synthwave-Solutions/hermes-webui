# October 2026 feature integration

This release integrates the prepared engine compatibility changes with the current
WebUI, preserving personal/company memory, bot handoffs and session polling caches.

- SVG fences and raw SVG answers render as sanitized image data, with source,
  download and full-size controls. Scripts, active SVG content and external loads
  are rejected. `HERMES_WEBUI_INLINE_SVG=1` enables the visual-answer prompt;
  rendering is available independently for stored answers.
- The title-bar help button explains the current page. Settings includes tours;
  `/tour` and `/explain` open the same accessible help. An optional first-use offer
  dismisses when the user starts typing and stays clear of the composer.
- Group turns select a mentioned, sole, last-used or explicitly configured default
  bot, in that order. Selection is checked against the sender's current grants.
  Default selection persists across reloads; reply attribution and route reasons
  remain attached to the conversation's own turn.
- Finished run journals can be replayed through `/api/agui/runs/<stream_id>`.
  Only the owner or a current participant may read the projection. Unknown and
  unauthorized identifiers have the same response.

## Memory explorer

The Memory panel retains its existing sections and adds a read-only explorer when
`HERMES_WEBUI_MEMDASH=1`. This release supports the explicitly configured HQ interim
reader: `HERMES_WEBUI_MEMDASH_BACKEND=sqlite_interim`, a policy with
`installation.kind: hq`, `HERMES_WEBUI_MEMDASH_HUB_CONFIG` pointing at a registry,
and narrowly scoped `HERMES_WEBUI_MEMDASH_BANK_ROOTS`. An active hub URL disables
this interim backend. It never writes to memory databases.

The current personal banks are selected from the authenticated person's generated
state directory, irrespective of selected bot or administrative role. A current
private bank takes priority over legacy registry entries; the latter are marked
“legacy”. Conversation banks are the person's private copies, not shared ownership.
An owner-private store is inaccessible to any other administrator.

Leave `HERMES_WEBUI_MNEMO_ADMIN_VIEW` unset for own-memory-only navigation.
Administrative views require explicitly enabling that setting and successful
access-log writes before another person's data can be read. Database editing is
unavailable in the interim reader. The dashboard runs in an opaque, network-disabled
sandbox and communicates only through a scoped message bridge.

## Verification

Use `scripts/test.sh` with an isolated home/state and the reviewed engine on
`PYTHONPATH`. Feature/security regression tests cover SVG validation, help,
group routing, replay authorization, memory ownership, read-only databases,
audit-write failures, and current Personal memory behavior.
`tests/e2e/full/release-features.spec.ts` complements existing real-engine chat and
bot delegation scenarios with desktop/mobile SVG/help, default-bot persistence,
and the Memory explorer bridge. These require the private loopback QA fixture.
