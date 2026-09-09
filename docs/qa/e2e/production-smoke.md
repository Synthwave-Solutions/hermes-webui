# Production smoke — production execution still pending

Use `production-smoke.py` only after the paired candidate commits have been
deployed and the service restarted. It runs against the actual service, not a
synthetic provider or fixture server. Its real HTTP/API and cleanup paths have
also been exercised against fresh private candidate fixtures. The isolated
validation harness changes only Git cleanliness metadata discovery; it does
not replace authentication, handlers or results. Production has not been
accessed by this script.

## VPS API procedure

Invoke the deployed Python interpreter with explicit absolute WebUI, engine,
authorized workspace and new evidence paths, the exact expected paired commit
IDs and `--base-url http://127.0.0.1:<actual-service-port>`. Add `--execute` to
perform the bounded test. Without that flag it makes no HTTP requests.
Tracked modifications always fail the source gate. The only supported explicit
exception is `--allow-untracked-dir .playwright-mcp`, for the already-reviewed
browser artifact directory. Other untracked paths still fail. The report retains
the actual dirty status, untracked path list/count/hash and tracked-change flag;
the exception does not treat the checkout as clean or ignore changed tracked code.

The runtime `HERMES_WEBUI_PASSWORD` must already be inherited in memory. Do not
place a password, cookie, provider key or an entire environment on a command
line or in a report. The script performs one normal password login. If the
deployment requires SSO first, it fails closed; use the already-authenticated
Mac browser procedure instead of bypassing SSO or weakening configuration.

The script imports one new synthetic conversation through the authenticated
HTTP API. No model runs for that fixture. It creates an anonymous public Share,
checks the exact synthetic payload, renames the source and proves the snapshot
stays unchanged until explicit refresh, then revokes the link. It creates a
unique non-current Kanban board (`switch:false`), creates two unassigned Todo
tasks and exercises Todo → Done and Todo → Blocked without queuing a worker.
These manual transitions invoke the normal `kanban_task_completed` and
`kanban_task_blocked` lifecycle hooks. Before production execution, verify that
the deployed handlers for those events cannot send messages or launch other
work. A private board does not disable global lifecycle hooks; do not change
production hook settings just to make the smoke pass.

Cleanup verifies its exact random fixture markers before deleting its session
and hard-deleting its own board. It refuses board cleanup if someone selected
that board, inserted another task, changed fixture text, commented or started a
worker. The manual Done/Blocked history intentionally contains one closed,
zero-duration audit row with no assignee, worker, claim or heartbeat fields.
The script verifies that exact content and the Created plus Completed/Blocked
plus the explicit Todo status event, then compares the full persisted task detail (excluding only the two clock-derived age aliases) during cleanup. It never resets the global board selection. It revokes its Share before
deleting the conversation; the application's revoked snapshot tombstone remains
in the normal Share store. A cleanup failure is a failed smoke, with only the
synthetic record IDs and safe reason codes recorded for follow-up.

The JSON artifact is created with mode 0600 and contains disk commit IDs,
whether either checkout was dirty, served static response SHA256 values and
their corresponding disk hashes, HTTP status/assertion outcomes and cleanup.
It contains no raw conversation, response diagnostics, cookies, bearer Share
URL, SDP, provider call ID, password, key or CSRF token. A token hash can correlate
the synthetic Share without exposing the bearer link. A disk commit and matching
static assets do not prove which Python modules an unrestarted worker loaded;
the deployment record must separately identify the restarted process.

## Actual browser viewport checks

The VPS script labels desktop 1440×1000 and mobile 390×844 **NOT RUN — API ONLY**.
It does not invent viewport evidence. In the authenticated Mac browser, create a
separate uniquely named synthetic session and perform the Share action normally,
view its page in a separate unauthenticated browser context, inspect Copy link
and Open SynPulse at both viewport sizes, cancel revocation once and then revoke.
Capture only the synthetic page, verify both revoked page/API return 404, and
delete only that created session. Keep screenshots free of other conversation
titles or private navigation data. Record the actual browser and viewport sizes.

## Real voice provider negotiation and response

The VPS script checks only `/api/voice/realtime/capability`. It does not submit
fake SDP, mock `RTCPeerConnection`, replace media devices, or claim to test a
physical microphone on a headless server. A positive capability response alone
does not prove provider entitlement or connectivity.

After confirming the restarted service has `SYNPULSE_REALTIME_VOICE_ENABLED=1`
and the supplied `OPENAI_API_KEY` in its own environment (presence only; do not
read or emit the value), use the real authenticated HTTPS page on the Mac:

1. Open a new uniquely named synthetic chat. Click **Voice mode** normally.
   Grant the browser's microphone permission only through its normal permission
   flow. The application obtains the real device and immediately sets every
   track `enabled=false`; keep **Unmute** and **Hold to talk** untouched.
2. Verify a real `/api/voice/realtime/call` returns 200, the actual native
   `window.synPulseVoice.pc.connectionState` is `connected`, its native data
   channel is `open`, and all `window.synPulseVoice.media.getAudioTracks()` are
   disabled. Collect booleans/status codes only, never SDP, credentials or raw
   device identifiers. This tests native WebRTC/provider negotiation while
   microphone audio stays muted.
3. If a bounded real spoken-response proof is required without activating the
   microphone, send a single **input_text** conversation item on the existing
   real native data channel, then `response.create`, asking only for a short
   synthetic acknowledgement and explicitly no tools. This uses the real
   provider and normal audio playback; it is protocol-seeded input, **not proof
   of microphone speech recognition**. Verify native output-audio buffer start
   and stop events and the matching assistant caption. Record only success,
   timing and a hash of the expected synthetic text. Do not dispatch real work
   or external messages for this bounded negotiation test.
4. Click **End voice** within 30 seconds. Confirm every local track is stopped,
   peer/data channel closed and subsequent status for that call returns 404.
   Delete the synthetic conversation after ensuring no child work was started.

If microphone permission/device availability, autoplay, network or provider
entitlement prevents these checks, end the attempt and record the actual
boundary. Do not replace native APIs with fixtures or mark audio quality tested.
Real human speech input, recognition accuracy and audible quality remain
unverified until someone actually speaks and listens on that device. Do not
claim production native tool execution from a successful short voice reply.
