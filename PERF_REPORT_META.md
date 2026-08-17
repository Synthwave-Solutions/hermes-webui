# PERF_REPORT_META: slimming the metadata-only GET /api/session payload

Branch: `perf/metadata-payload`. Scope: `GET /api/session?session_id=<sid>&messages=0` (the metadata-only variant used for fast session switching, boot checks, and pollers).

## 1. Where the bytes actually come from

The metadata response is `Session.compact()` (api/models.py:1397) plus a handler overlay (api/routes.py, `/api/session` GET). Per-field JSON size of the simulated metadata response, computed from live sidecars under `/home/synthwavehq/.hermes/webui/sessions/` (read-only):

| session (sidecar size, msgs) | metadata response raw | gzip | dominant field |
|---|---|---|---|
| 731b45358f9c (2.3MB, 714) | 1,866 B | 871 B | none (all small) |
| a55a0f91eb41 (8.2MB, 1392) | 2,497 B | 1,204 B | compression_anchor_summary 720 B |
| 00134f26d7f0 (8.1MB, 1762) | 195,522 B | 40,811 B | compression_anchor_summary 193,743 B |

Per-field maxima across ALL sidecars (compact()-emitted fields only): `compression_anchor_summary` 193,711 B; `composer_draft` 3,239 B; everything else under 300 B. So persisted metadata alone never explains a ~4MB raw / ~458KB gzip response.

The multi-MB case is runtime-only: when the session has an ACTIVE stream, the handler adds `runtime_journal_snapshot`, built by `_run_journal_live_snapshot()` (api/routes.py:3222). That function replays the entire run-journal jsonl (`sessions/_run_journal/<sid>/<rid>.jsonl`, observed 7 to 8 MB per long turn) and serializes the full in-flight assistant text, reasoning, tool calls, and anchor activity rows (heavy duplication of the same text). That is both the ~4MB/458KB payload and most of the 900 to 1300 ms: journal replay plus serialization on every metadata poll of a streaming session.

Second latency class: `Session.load_metadata_only()` reads a bounded JSON prefix (before the top-level `"messages"` key). The cap was 64KB. Sidecars with a big `compression_anchor_summary` (194KB) or `anchor_activity_scenes` (up to 708KB; this branch has no #5854 scene split, scenes serialize before messages) overflowed the cap, silently falling back to a FULL parse of the multi-MB sidecar on EVERY metadata request (metadata loads are deliberately not cached). Measured on this VPS: ~3.0 s per request for a55a0f91eb41. The prefix reader was additionally O(n^2) (full char-by-char rescan after every 4KB chunk).

## 2. What changed

### api/routes.py (GET /api/session handler)
- New `include=` query param (comma-separated), parsed next to `messages`/`resolve_model`:
  - `journal_snapshot`: metadata-only requests get `runtime_journal_snapshot` again.
  - `full`: full pre-slimming metadata shape (escape hatch for any external consumer).
  - No-op for `messages=1` (full loads keep everything, unchanged).
- Metadata-only responses now omit, unless `include=full`:
  - `runtime_journal_snapshot` (also skips the journal replay compute, only built when requested);
  - `compression_anchor_summary`, `compression_anchor_details`, `context_engine_state` (popped just before redaction; mirrors the existing `_sidebar_session_response_item` allowlist for /api/sessions).
- `runtime_journal` (small status dict) stays in all variants.

### static/sessions.js
- `loadSession()` phase-1 fetch now sends `&include=journal_snapshot`: it is the only metadata-only consumer that reads `S.session.runtime_journal_snapshot` (mid-stream switch recovery), so live-stream reattach keeps working unchanged.
- `_ensureMessagesLoaded()` (phase 2, `messages=1`) now copies `compression_anchor_summary` from the full response onto `S.session`, since the metadata fetch no longer carries it. The compression banner needs rendered messages anyway, so there is no visible regression window.

### api/models.py (`_read_metadata_json_prefix`)
- Prefix cap 64KB -> 1MB (covers observed 194KB summaries and 708KB scene blocks, so those sessions stay on the cheap prefix path instead of re-parsing 8MB per poll).
- Reader made near-linear: 64KB chunks, running byte counter, and a C-speed `'"messages"' in buf` pre-filter before the char-by-char scanner (a raw `"messages"` substring cannot occur inside a JSON string value because interior quotes are escaped, so the scanner still decides authoritatively).

### tests/test_issue5854_anchor_scene_split.py
- Two size constants bumped ("Z" * 80000 -> "Z" * 1100000) so the prefix-overflow test still exercises the overflow path under the new 1MB cap. Test intent unchanged. This file is largely red pre-existing on this branch (the #5854 scene split is not implemented here); the failure set is byte-identical before and after this diff.

## 3. Why this is safe, per consumer of messages=0

| consumer | fields it reads | impact |
|---|---|---|
| static/boot.js:114 `_savedSessionSidebarOnlyState` | archived, active_stream_id, pending_user_message | untouched |
| static/sessions.js:122 `_validateCachedSessionScene` | revision/updated_at/last_message_at, message_count | untouched |
| static/sessions.js:~300 `_restoreRememberedNewChatDraftSession` | active_stream_id, pending_user_message, has_pending_user_message, worktree_path, composer_draft, message_count | untouched (composer_draft kept) |
| static/sessions.js:~1926 `loadSession` phase 1 | whole object into S.session; runtime_journal_snapshot + pending_attachments when streaming; continuation_session_id | now requests `include=journal_snapshot`; summary re-hydrated in phase 2 |
| static/sessions.js:~3050 `_resolveSessionModelForDisplaySoon` | model, model_provider, context_length, threshold_tokens, last_prompt_tokens | untouched |
| static/sessions.js:~5975 external-refresh poller | message_count, last_message_at, updated_at | untouched |

`compression_anchor_details` and `context_engine_state` have zero consumers anywhere in static/. No internal repo callers (mcp_server.py, scripts/, api/) call GET /api/session over HTTP. Frontend reads of `S.session.compression_anchor_summary` (ui.js render fingerprint + compression banner) are fed by the phase-2 hydration. Unknown external consumers can pass `include=full` to get the old shape.

## 4. Measured results (isolated trial server from this worktree, port 8791, copies of live sidecars)

| session | before raw / gzip | after raw / gzip | before t | after t |
|---|---|---|---|---|
| 00134f26d7f0 | 195,867 B / 44,000 B | 2,050 B / 880 B | 0.35 to 0.59 s | 0.11 to 0.25 s |
| a55a0f91eb41 | 2,801 B / 1,259 B | 2,006 B / 830 B | ~3.0 s | ~0.35 s |
| 731b45358f9c | 2,172 B / 925 B | 2,015 B / 855 B | 0.24 s | 0.14 s |
| streaming session (live only) | ~4MB raw / ~458KB gzip incl. runtime_journal_snapshot | ~2KB unless `include=journal_snapshot` | 0.9 to 1.3 s | snapshot compute skipped entirely |

The streaming-session row is the reported production case: it cannot be reproduced on the trial server (no active runs there), but the snapshot is the only payload component that can reach multi-MB, and it is now opt-in. The session-switch path still requests it, so mid-stream switch recovery keeps the previous behavior and cost; the boot check, scene validation, draft restore, poller, and model resolver no longer pay it.

## 5. Live verification

```bash
# Slim metadata (expect roughly 1 to 3 KB raw, under 1 KB gzip, even for big sessions):
curl -s -o /dev/null -w "raw=%{size_download}B t=%{time_total}s\n" \
  "http://127.0.0.1:8787/api/session?session_id=731b45358f9c&messages=0&resolve_model=0"
curl -s -H "Accept-Encoding: gzip" -o /dev/null -w "gz=%{size_download}B\n" \
  "http://127.0.0.1:8787/api/session?session_id=731b45358f9c&messages=0&resolve_model=0"

# Old shape still available:
curl -s "http://127.0.0.1:8787/api/session?session_id=<sid>&messages=0&include=full" | wc -c

# For an actively streaming session, the switch path (with include=journal_snapshot)
# still carries the live snapshot; the plain metadata call must not:
curl -s "http://127.0.0.1:8787/api/session?session_id=<sid>&messages=0" \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['session']; print('snapshot present:', 'runtime_journal_snapshot' in d)"
```

Expected: `snapshot present: False` on the plain call; `messages=1` responses unchanged (still carry `compression_anchor_summary`, messages, tool_calls, todo_state, snapshot when streaming).

## 6. Verification performed

- `python3 -c "import ast; ast.parse(...)"` clean for api/routes.py, api/models.py, the test file; `node --check static/sessions.js` clean.
- Trial server end-to-end checks: stripped keys absent on messages=0; present with include=full and with messages=1; include=journal_snapshot does not re-add the summary; message_count/counters correct (1762 for 00134f26d7f0).
- Targeted pytest (12 files, 144 tests): 129 passed, 15 failed; the failure set is byte-identical with the diff stashed (all pre-existing: the unimplemented #5854 scene split, four run-journal tests, one SynthPulse service-worker branding test). Zero new failures.
- Offline parity check: `Session.load_metadata_only().compact()` vs full-load compact() differs only in `user_message_count` and `last_message_at` fallback, both pre-existing metadata-stub semantics untouched by this diff.

Out of scope, noted for follow-up: `_run_journal_live_snapshot` itself still serializes the full in-flight text several times over (messages + anchor rows + assistant turn); bounding that would also shrink the one remaining heavy call (session switch onto an actively streaming chat).
