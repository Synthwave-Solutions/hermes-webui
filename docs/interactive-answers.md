# Interactive answers

A reply can contain a small live app: calculators, what-if models,
simulations or 3D. The agent writes a fenced block with the info string
`interactive-ui`; the chat shows it as a card with the app inside. Tables,
charts, maps, headline figures and plans are data blocks instead (see
below): the agent only writes JSON and the chat draws it.

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

## Data blocks: tables, charts, maps, KPIs and timelines

For data the agent does not write code. It writes a fenced block that holds
only JSON (```` ```table ````, ```` ```chart ````, ```` ```map ````,
```` ```kpi ```` (also `kpis`, `kpi-row`), ```` ```timeline ````, or the Dutch
```` ```tabel ````, ```` ```grafiek ````, ```` ```kaart ````, ```` ```tijdlijn ````,
```` ```planning ````) or plain CSV (```` ```csv ````). A ```` ```chart ```` that holds JavaScript stays a code
block: only a body that starts with `{` is data.

- **Checking:** `static/interactive-ui/kit-core.js` (`SWKit.build`) reads the
  JSON leniently (comments and trailing commas are fine), fixes what it can
  (rows padded or cut to the column count, Dutch and English numbers, a
  Dutch place written as lng/lat) and lists those fixes under Details. Only
  when nothing can be drawn does the card show "Deze tabel/grafiek/kaart kon
  niet worden gemaakt" with "Laat repareren"; the repair prompt names the
  problem ("Rij 3 heeft 4 waarden, verwacht 5. Stuur het volledige
  chart-blok opnieuw.").
- **Drawing:** the cleaned spec goes as a structured clone to
  `static/interactive-ui/kit.html`, a second frame served by
  `api/interactive_ui.py`. It holds its own renderers
  (`static/interactive-ui/kits.js`) plus vendored Chart.js 4.4.7 and Leaflet
  1.9.4, all inline. Its CSP is `sandbox allow-scripts` (no popups, no forms),
  `script-src` with one sha256 per inline script (no `unsafe-inline`, no
  `unsafe-eval`, no CDN), `connect-src 'none'` and images only from the tile
  host and `upload.wikimedia.org`. The frame accepts only the `kit`, `theme`
  and `measure` messages and builds every element with `textContent`.
- **Table:** sortable headers (oplopend, aflopend, origineel), "Zoek in
  tabel" from 10 rows, the first 50 rows with "Toon alle {n} rijen", sticky
  header and first column, Dutch number format, an optional "Totaal" row and
  the source under the table. Sort and search are kept per tab.
- **Chart:** bar, hbar, stacked, line, area, pie and donut in the chart
  palette, with `highlight` (the rest muted) and a dashed `target` line.
  "Grafiek | Tabel" switches to the numbers (kept per tab); if the chart
  cannot draw, the table shows with "Grafiek kon niet laden, hier zijn de
  cijfers."
- **Map:** numbered pins that drop in once and, for a route, a line that
  draws itself (at most 2.5 s, never looping, still under reduced motion), a
  linked list ("Locatie 2 van 5: Rijksmuseum"), "Niet op de kaart gevonden"
  for places without a position, "Open in Google Maps", "Kopieer adressen"
  and, for a route, "Opnieuw afspelen". When tiles do not load the list stays
  with "De kaart laadt nu niet. De lijst klopt wel."
- **KPI:** one to eight tiles side by side (two on a phone): the label, one
  big number in the block's language (millions written short, "1,3 mln."),
  a pill with the change ("+12,5%", "+0,4 pp" for a percentage, "€ -800"
  with `deltaFormat: "number"`) that is green or red by `good` (`up` by
  default, `down` for costs and churn) and also carries an arrow, the sign
  and a spoken "gunstig" or "ongunstig", an optional note and a thin bar
  toward `target` ("92% van doel € 20.000"). The export has Label, Waarde,
  Verandering and Doel.
- **Timeline:** a Gantt with a label column (owner and status under the
  label) and one track per item. `start` and `end` are dates (YYYY-MM-DD, or
  a month YYYY-MM) or unit numbers (`unit`: day, week or month; week 1 starts
  on the block's `start`); `end` is included. Bars are green for done,
  accent for doing, red for risk and grey for todo; milestones are diamonds;
  a red line marks `today` (a unit number or a date; a plan with dates and no
  `today` uses the browser's date, and the line only shows inside the
  range). Clicking a bar, or its label, or pressing Enter on it (arrow keys
  move between bars) writes its period, owner, status and note in a status
  line; the choice is kept per tab. Under 480 px the chart becomes a stacked
  list: label, period, then a slim full-width bar with today marked. The
  export has Onderdeel, Start, Einde, Eigenaar, Status, Mijlpaal and
  Notitie.
- **Menu:** "Download als CSV" (`;`, decimal comma, UTF-8 BOM, as sorted and
  filtered), "Kopieer als tabel" (for Excel or Sheets), "Downloaden" (a
  standalone page) and, for developers, "Gegevens bekijken". There is no
  sandbox note: none of the model's code runs.

### Map positions and photos

`POST /api/map/resolve` (`api/map_resolve.py`, signed in plus CSRF) looks up
the places of a finished map block once; the chat keeps the answer per tab
(`static/interactive_ui_map.js`) and retries places marked `later` once after
3 s. Order: coordinates in the block, the cache (`STATE_DIR/map_cache.sqlite`,
180 days for hits, 1 day for misses), PDOK Locatieserver for Dutch
addresses, Nominatim (one request per 1.05 s for the whole server, an
identifying User-Agent, at most 8 new lookups per map and about 500 a day),
then the coordinates of the Wikipedia article in `wiki`. With `photos: true`
a landmark can get its Wikipedia photo, only when Wikimedia Commons lists a
CC or public-domain license and a creator; the credit shows as "Foto:
{maker}, {licentie}". Per user: 20 calls a minute and 300 places an hour.
Logs hold counts, never addresses.

Settings: `webui_map_geocoder` (`pdok,nominatim` by default; `off` sends
nothing outside, only coordinates in the block are shown; an unknown value
counts as `off`), `webui_map_contact` (added to the User-Agent and sent to
Nominatim as `email`) and `webui_map_tiles` (a tile URL template or
`{url, attribution, maxZoom}`; the frame's image policy follows its host).
`HERMES_WEBUI_MAP_GEOCODER`, `HERMES_WEBUI_MAP_CONTACT` and
`HERMES_WEBUI_MAP_TILES` override them. OpenStreetMap tiles and Nominatim
are best effort under their usage policies; a tenant with heavy use should
point `webui_map_tiles` at its own tile server.

## Agent side

`api/interactive_ui.prompt_block` adds the contract to the WebUI runtime
instructions on every browser and Gateway turn (not voice): first the data
blocks (`PROMPT_DATA`: which fence for which content, the short shapes, JSON
numbers, real addresses only, no invented travel times or opening hours, one
data block per reply), then interactive-ui for calculators, what-if models
and simulations. Switch:
`webui_interactive_ui` in the config, `HERMES_WEBUI_INTERACTIVE_UI=0|1`
overrides; default on. The `interactive-ui` skill in the shared skill library
holds templates (calculator, scenario chart, weighted comparison, Gantt, KPI
dashboard, map) and the quality bar.

## Tests

- `tests/test_interactive_ui.py`: frame headers and CSP, prompt placement and
  switch, renderer seams, parser (Node, `tests/interactive_ui_parse.cjs`).
- `tests/test_interactive_kits.py` with `tests/interactive_kits.cjs`: the kit
  helpers in Node (valid, fixable and fatal fixtures per kind, CSV quoting,
  Dutch numbers, exports, the lat/lng swap, KPI deltas and the timeline axis,
  the fence seam) and the renderer's DOM rules.
- `tests/test_map_resolve.py`: the endpoint with a mocked network
  (User-Agent, spacing across threads, no redirects, PDOK parsing, cache
  times, limits, the Commons license gate, geocoder off, no addresses in logs).
- `tests/browser_interactive_ui.py`: real server and engine with a fake model in
  Chromium: live build, settled run, calm header and menu, full screen on top of
  the chat, download, a lone frame that ignores posted content, confirmed
  follow-ups that keep the user's draft, kept settings after a re-render,
  automatic prompts never sent, theme sync, isolation, plain errors with repair,
  reload, narrow layout; then data blocks (table, csv, chart, map with stubbed
  tiles and the geocoder off, kpi tiles with delta colours, a timeline with
  status colours, the today line, click and keyboard details and the
  stacked list at 390 px) with screenshots at desktop and 390 px, dark and
  light.

The approach follows CopilotKit's Open Generative UI and Open Intelligent UI
(MIT); no code from those projects is included.
