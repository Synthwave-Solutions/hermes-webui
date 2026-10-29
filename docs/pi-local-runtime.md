# Local Pi memory explorer and customer preferences

`HERMES_WEBUI_MEMDASH=1` with `HERMES_WEBUI_MEMDASH_BACKEND=local_personal`
enables the existing Memory Explorer for the authenticated person's local
private/conversation databases. It works on customer installations and does
not include legacy, HQ, other-user or shared service-token banks. A configured
remote hub URL is rejected in this mode.

The adapter reuses current authorization and the read-only SQLite child.
Explorer mutations remain unavailable. A separate Mnemosyne maintenance job
performs consolidation against the same personal database; resulting episodic
summaries and consolidation records are visible through the existing views.
Nanosecond database/WAL revisions invalidate cached views immediately after a
consolidation, including writes within the same second.

`SP_WEBUI_LOGIN_SUBTITLE` overrides the login subtitle. The value is HTML escaped;
blank/unset preserves the selected language's default text.

`SP_MSP_REQUEST_ONLY_APPS=1` makes app availability changes a request to the MSP:
app cards offer an explicit request, direct toggles are hidden and the server
rejects `/api/msp/app-state`. The existing signed request endpoint is used.
MSP pairing and actual disabled/enabled entitlements remain server-owned; this
option does not simulate a connection, automatically submit requests or alter
billing. Existing behavior is unchanged when unset.

Existing appearance settings can hide `files`, `logs`, `todos` and realtime voice
without patching the frontend: `hidden_tabs` and `hide_composer_voice_mode`.
Bot Screens already appears in the right workspace panel when its API returns
an authorized bot. These customer preferences and SSO configuration are not
forced by this change.

Focused tests cover personal isolation, read-only behavior, immediate refresh,
MSP request versus toggle behavior, and escaped/localized login subtitles. When
mnemosyne-memory 3.15.1 is installed, a disposable-bank test runs real fallback
consolidation and reads its resulting episodic summary through the Explorer API.
That proof deliberately disables LLM/embeddings and does not claim that a
production scheduler or semantic embedding model has been configured.
