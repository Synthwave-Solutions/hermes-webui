# Interactive answers

A reply can contain a small live app: calculators, what-if models, charts,
comparisons, timelines, maps or 3D. The agent writes a fenced block with the
info string `interactive-ui`; the chat shows it as a card with the app inside.

## What the user sees

- **While the reply streams** the card builds up live: styles and markup appear
  as they arrive, the raw source stays hidden, a progress line runs under the
  header and the status shows the size so far.
- **When the reply is complete** the scripts run and the card says
  "Interactief". The frame grows or shrinks to fit its content.
- **Header actions:** source (with copy), reload, download as a standalone HTML
  file, open in a new tab, full screen (Escape closes it, also from inside the
  app).
- **Errors** (a script error, a blocked source) show a red bar under the app with
  a button that asks the agent to repair it; the rest of the chat is unaffected.
- **Follow-ups:** a button inside the app can send a prompt with the chosen
  values (`synthwave.sendPrompt`). This only works right after a click or key
  press inside that app; automatic prompts are refused.
- Frames load only when they come near the screen, so long chats stay fast.

## Isolation

The app runs in `static/interactive-ui/frame.html`, served by
`api/interactive_ui.py` with its own Content-Security-Policy:

- `sandbox allow-scripts allow-forms allow-popups`, never `allow-same-origin`:
  an opaque origin with no access to the WebUI cookie, storage, DOM or API, also
  when opened in its own tab;
- scripts, styles and network only inline or from `cdn.jsdelivr.net`,
  `unpkg.com`, `cdnjs.cloudflare.com` and `esm.sh`; images from any `https:`
  source (map tiles);
- `form-action 'none'`, no top navigation, no cookies set, `Cache-Control:
  no-store`.

The host never puts the source into its own DOM as HTML: it is shown with
`textContent` and sent to the frame with `postMessage`. Messages from frames are
only accepted from the window of a known iframe.

## Agent side

`api/interactive_ui.prompt_block` adds the contract to the WebUI runtime
instructions on every browser and Gateway turn (not voice). Switch:
`webui_interactive_ui` in the config, `HERMES_WEBUI_INTERACTIVE_UI=0|1`
overrides; default on. The `interactive-ui` skill in the shared skill library
holds templates (calculator, scenario chart, weighted comparison, Gantt, KPI
dashboard, map) and the quality bar.

## Tests

- `tests/test_interactive_ui.py`: frame headers and CSP, prompt placement and
  switch, renderer seams, parser (Node, `tests/interactive_ui_parse.cjs`).
- `tests/browser_interactive_ui.py`: real server and engine with a fake model in
  Chromium: live build, settled run, actions, follow-up, refusal of automatic
  prompts, theme sync, isolation, error and repair, reload, narrow layout.

The approach follows CopilotKit's Open Generative UI and Open Intelligent UI
(MIT); no code from those projects is included.
