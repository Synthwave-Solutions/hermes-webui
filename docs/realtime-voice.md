# Realtime voice in SynPulse

Realtime voice is an optional speech surface for the existing chat. Enable it with
`SYNPULSE_REALTIME_VOICE_ENABLED=1` and a server-side `OPENAI_API_KEY` with Realtime
API access and billing. It is disabled by default. The browser needs HTTPS,
WebRTC and microphone permission. The button starts a connection **muted**;
Hold to talk or Unmute microphone explicitly enables audio capture.

The speech transport uses OpenAI gpt-realtime-2.1 with marin, plus
gpt-4o-mini-transcribe. This is separate API usage, not the Codex subscription.
The chat keeps its selected SynPulse engine model, including Astra through
OmniRoute. Existing Codex Responses credentials are not reused for Realtime.
Key presence does not prove model entitlement, billing, or working audio.

## Controls and behavior

- Hold to talk: pointer or Space while focused; releasing mutes.
- Unmute/Mute: explicit continuous listening; no automatic unmute.
- Interrupt speech: clears current audio without canceling ongoing agent work.
  The existing chat Stop control cancels the engine run.
- End voice: stops tracks and closes the connection. Navigation to another chat,
  hiding the page, transport failure, and a 15-minute limit also end it.
- Existing text input and written answers remain usable if speech fails.
  If a draft already exists, the transcript is appended for manual review/send.

Speech transcripts use the ordinary chat send/queue path. Tool calls, approvals,
project access, selected bots, background tasks and subagents use the original
human identity and existing durable run journal. Voice has no separate tool
execution endpoint and cannot grant permissions. The interface gives a short
submission acknowledgement; real tool-start events can trigger a throttled,
generic progress announcement. Actual details remain in the existing worklog.

This is interruptible realtime **speech transport**, with an engine turn between
transcription and answer narration. Final narration starts after the engine
answer completes, so model/tool time still affects conversational latency. It
does not stream engine reasoning or claim full-duplex autonomous orchestration.

## Security and state

The authenticated, CSRF-protected SDP exchange checks current session visibility,
including project/group access, before and after negotiation. If access is revoked
during negotiation, it attempts a server-side hangup before refusing the SDP. Governance requires
chat:use. The standard API key stays on the server; the browser receives only SDP.
There is no browser bearer token or model tool proxy. SDP size and connection
attempts are bounded. Provider error bodies are never echoed to users.

Audio flows to OpenAI over WebRTC while the microphone is enabled. This feature
does not save raw audio. Speech transcripts are ordinary persisted chat content.
The browser owns microphone tracks, peer connection and the duplicate-event set;
all are released on teardown. Engine runs remain server-owned and durable after
voice ends. The speech model receives only its audio input and answer text sent
for narration, not a copy of workspace files or the full session history.

## Verification and rollout

Run the canonical runner on tests/test_realtime_voice.py plus existing voice
and composer tests. Automated fixtures cover SDP credentials, no-tool config,
invalid inputs, rate limits, authentication/visibility, revocation during
negotiation, muted startup, duplicate transcripts, interruption, navigation and
late microphone resolution after teardown. These do not establish real provider
billing or real microphone quality. Enable production only after a user-gesture
browser test confirms provider access, sound, interruption and microphone mute.

Official protocol references:
- https://developers.openai.com/api/docs/guides/realtime-webrtc
- https://developers.openai.com/api/docs/guides/realtime-server-controls
- https://developers.openai.com/api/docs/models/gpt-realtime-2.1
- https://help.openai.com/en/articles/9039756

The unified server SDP exchange avoids issuing browser client secrets. A
server-side sideband is not used because the speech model has no application
tools; all execution belongs to the existing authenticated engine turn.
