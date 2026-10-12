# Bot Screens in SynthPulse

Open **Bots → Bot Screens**. The separate screen window uses the existing
SynthPulse session, fills the available viewport and provides Dutch/English
interactive guidance for each control. Screen access is independent of bot chat
or configuration access. A bot's screen is its computer on the server, not the
user's laptop.

From a normal chat, expand the right panel and select its **Bot Screens** tab.
The same viewer runs beside the conversation, including takeover, full screen
and the interactive guide. It initially selects the active chat bot when that
bot is allowed. Use its bot selector to change screens; changing chats does not
silently replace an open screen. Switching to Files/Artifacts or collapsing the
panel keeps the viewer and human lease intact. Reopen Bot Screens to hand back.
The screen tab is shown only to accounts with explicit screen access, including
when no chat session or workspace has been created yet.

1. Choose an allowed bot, then **Start screen**.
2. Watch without sending input. A viewer-only account cannot start or control.
3. Choose **Take over** and confirm. Only that browser tab can drive the screen.
   Other viewers lose the stream; their canvases are removed. The engine's durable
   human lease blocks computer-use and browser tools, including captures.
4. Choose **Hand back**, then ask the bot in chat to continue.
5. Reconnect from the same tab after a reload or network loss. Closing the tab or
   losing the connection retains the lease. An administrator can explicitly
   confirm **Release control** for an abandoned lease. Save work before **Stop
   screen**; stopping is refused while a human holds control.

## Administrator configuration

Install the engine's Linux desktop dependencies using its supported
`hermes computer-use screen install` operator command. Keep the engine's separate
`bot_desktop.dashboard_viewer` disabled: the WebUI supplies its own authenticated
bridge. The upstream Desktop app is not required. Existing runtime placement
(gateway host or terminal sandbox) is retained; the bridge accepts no browser-
provided path, host or socket address. Set `browser.headed: true` for a bot whose
browser actions should appear on its screen. Automatic desktop startup remains
opt-in; the UI supports explicit start. The upstream idle-stop policy is retained.

Add explicit email grants to the canonical dashboard governance policy:

```yaml
bot_screens:
  enabled: true
  profiles:
    example_bot:
      viewers: [viewer@example.test]
      controllers: [operator@example.test]
      admins: [admin@example.test]
```

Controllers also view; administrators also control and can stop/recover. Neither
bootstrap administrators nor ordinary bot access imply a screen grant. For roles
with route allowlists, add `/api/bot-screen` and `/api/bot-screen/ws`. Unknown users,
anonymous sessions, absent policy and unlisted bots are refused in every governance
mode. Disabling the policy or removing a grant also terminates an existing stream.

## Boundaries and lifecycle

- The WebUI bridges its existing authenticated HTTPS/WebSocket endpoint to the
  engine's private RFB socket (or existing sandbox relay). No TCP VNC port opens.
- Server-side RFB filtering enforces the lease; noVNC view-only mode is additional
  UX, not authorization. Privacy is automatic while any human holds control.
- Viewer identity binds the signed session, bot and tab. A tab identifier alone
  is not authority. Takeover, recovery and stop require a single-use, 60-second,
  session-bound confirmation. This confirmation is not MFA or reauthentication.
- The browser's existing CSRF check protects mutations; WebSocket handshakes
  require matching Origin and Host. Cookie validity, grants and privacy are
  checked during streams. Eight streams and 256-KiB client messages bound load.
- Screen opens/closes, control and runtime actions are recorded in the existing
  governance audit log with hashed actor identity. Frames, keys, clipboard
  contents and credentials are not recorded. Previously viewed pixels cannot be
  recalled from another device.
- The upstream lease is a tool boundary, not an OS sandbox. Processes sharing
  the host user can access that user's files and display. Use the engine's
  terminal sandbox or separate hosts for stronger tenant isolation.
- Reversing this deployment means disabling `bot_screens.enabled` and restoring
  the previous WebUI version. Stop desktops explicitly after users save work;
  do not delete profiles, browser sessions or documents.

## Verification

`./scripts/test.sh tests/test_bot_screens.py` covers authority, scoped leases,
confirmation, recovery, revocation and Origin checks. Release validation also
uses a real disposable Xvnc/Xfce desktop and Chromium: stream connection, observer
read-only access, privacy across two users, refresh while holding control, hand
back, stopping and NL/EN interactive guides at desktop/mobile widths.

The pinned noVNC 1.7.0 source under `static/vendor/novnc` is served locally without
a build step or CDN. Copyright and license files are retained there.
