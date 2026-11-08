# Interactive answers

A reply can contain a small live app: calculators, what-if models, charts,
comparisons, timelines, maps or 3D. The agent writes a fenced block with the
info string `interactive-ui`; the chat shows it as a card with the app inside.

## What the user sees

- **While the reply streams** the card builds up live: styles and markup appear
  as they arrive, the raw source stays hidden and a thin progress line runs
  under the title with the word "Wordt gemaakt".
- **When the reply is complete** the scripts run and the status disappears. The
  frame grows or shrinks to fit its content; heights are remembered per tab so
  the chat does not jump when scrolling back.
- **Header:** the title, full screen (a real overlay above the chat, Escape or
  Sluiten closes it, focus stays inside) and one menu: Downloaden, Opnieuw
  starten and, under "Voor ontwikkelaars", Code bekijken and Code kopiëren.
- **Errors** show one plain sentence with "Laat repareren"; the technical
  details are folded away under "Details". Skipped external sources only show
  in the details. The rest of the chat is unaffected.
- **Follow-ups:** a button inside the app can offer a question with the chosen
  values (`synthwave.sendPrompt`). It appears in the card and is only sent when
  the user presses Versturen; a draft already in the message box is never
  overwritten.
- **Settings are kept:** values the user set in inputs and sliders come back
  when the chat re-renders the message list (per tab).
- Frames load only when they come near the screen, so long chats stay fast.

## Isolation

The app runs in `static/interactive-ui/frame.html`, served by
`api/interactive_ui.py` with its own Content-Security-Policy:

- `sandbox allow-scripts allow-forms allow-popups`, never `allow-same-origin`:
  an opaque origin with no access to the WebUI cookie, storage, DOM or API;
- scripts, styles and `fetch` only inline or from `cdn.jsdelivr.net`,
  `unpkg.com`, `cdnjs.cloudflare.com` and `esm.sh`; images from any `https:`
  source (map tiles). This keeps the app away from the user's data; it does not
  stop the app itself from loading a remote image, so treat what it shows as
  model output;
- `form-action 'none'`, no top navigation, no cookies set, `Cache-Control:
  no-store`.

The host never puts the source into its own DOM as HTML: it is shown with
`textContent` and sent to the frame with `postMessage`. Messages from frames are
only accepted from the window of a known iframe with an opaque origin; the
frame only accepts messages from its parent's origin and renders nothing when
opened on its own. Nothing a widget sends acts for the user by itself: prompts
need the host's Send button, copying needs a recent click.

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
  Chromium: live build, settled run, calm header and menu, full screen on top of
  the chat, download, a lone frame that ignores posted content, confirmed
  follow-ups that keep the user's draft, kept settings after a re-render,
  automatic prompts never sent, theme sync, isolation, plain errors with repair,
  reload, narrow layout.

The approach follows CopilotKit's Open Generative UI and Open Intelligent UI
(MIT); no code from those projects is included.
