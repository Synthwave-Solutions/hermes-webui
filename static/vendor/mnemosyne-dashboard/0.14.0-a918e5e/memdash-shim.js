/*
 * Memory explorer frame shim (plan addendum 6.6.4). Loaded before app.js.
 *
 * The frame runs in an opaque origin (CSP sandbox allow-scripts) with no
 * network (connect-src 'none'), no cookie and no storage. This shim:
 *   - reads the per-load frame key and the theme from the URL fragment, then
 *     removes the fragment from the address;
 *   - gives app.js an in-memory __mdStore in place of localStorage;
 *   - removes EventSource, so live updates are off;
 *   - replaces fetch: a URL that starts with /api/ becomes a message to the
 *     parent WebUI panel, which answers it; anything else is refused;
 *   - applies theme messages from the parent: dark or light, the WebUI's
 *     appearance tokens (colours, font, font size, radii) as --sp-* custom
 *     properties that memdash-overrides.css maps onto the dashboard, and the
 *     WebUI language (Dutch or English) for the dashboard's own strings;
 *   - draws the 3D visualiser with the same tokens (wrapped palette functions).
 * It never builds HTML from strings.
 */
(function () {
  'use strict';

  var fragment = String(location.hash || '').replace(/^#/, '');
  var params = new URLSearchParams(fragment);
  var key = String(params.get('k') || '');
  var theme = params.get('theme') === 'light' ? 'light' : 'dark';
  // params.get('lang') is read by the language part below.
  if (!/^[0-9a-f]{32}$/.test(key)) key = '';
  try { history.replaceState(null, '', location.pathname + location.search); } catch (_) { /* opaque origin */ }

  // app.js pushes a history entry per tab; in a frame that would fill the
  // WebUI's back button, so every push replaces the current entry instead.
  try {
    var replace = history.replaceState.bind(history);
    history.pushState = function (state, title, url) {
      try { replace(state, title, url); } catch (_) { /* opaque origin */ }
    };
    history.replaceState = function (state, title, url) {
      try { replace(state, title, url); } catch (_) { /* opaque origin */ }
    };
  } catch (_) { /* keep the browser's own */ }

  var store = Object.create(null);
  store['mnemosyne-dashboard-theme'] = theme;
  var mdStore = Object.freeze({
    getItem: function (k) { k = String(k); return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem: function (k, v) { store[String(k)] = String(v); },
    removeItem: function (k) { delete store[String(k)]; },
    clear: function () { Object.keys(store).forEach(function (k) { delete store[k]; }); }
  });
  Object.defineProperty(window, '__mdStore', { value: mdStore, writable: false, configurable: false });
  document.documentElement.dataset.theme = theme;

  try { delete window.EventSource; } catch (_) { /* ignore */ }
  if ('EventSource' in window) {
    try { Object.defineProperty(window, 'EventSource', { value: undefined, configurable: true }); } catch (_) { /* ignore */ }
  }

  var parentWindow = window.parent && window.parent !== window ? window.parent : null;
  var targetOrigin = (typeof location.origin === 'string' && location.origin && location.origin !== 'null') ? location.origin : '*';
  var pending = new Map();
  var nextId = 1;
  var TIMEOUT_MS = 30000;
  var COLOUR_RE = /^#[0-9a-f]{3,8}$/;
  var COLOUR_VARS = { accent: '--accent', bg: '--bg', panel: '--panel', text: '--text' };
  var RGB_RE = /^rgba?\(\s*\d{1,3}(\s*,\s*|\s+)\d{1,3}(\s*,\s*|\s+)\d{1,3}(\s*[,/]\s*(0|1|0?\.\d+|\d{1,3}%))?\s*\)$/;
  var FONT_RE = /^[A-Za-z0-9 ,"'._-]{1,240}$/;
  var LENGTH_RE = /^\d{1,3}(\.\d{1,3})?px$/;
  var TOKEN_KINDS = {
    'bg': 'colour', 'surface': 'colour', 'sidebar': 'colour', 'code-bg': 'colour', 'text': 'colour',
    'muted': 'colour', 'border': 'colour', 'border2': 'colour', 'accent': 'colour',
    'accent-hover': 'colour', 'accent-text': 'colour', 'accent-bg': 'colour',
    'accent-bg-strong': 'colour', 'focus-ring': 'colour', 'input-bg': 'colour', 'hover-bg': 'colour',
    'success': 'colour', 'warning': 'colour', 'error': 'colour', 'info': 'colour',
    'radius-sm': 'length', 'radius-md': 'length', 'radius-lg': 'length', 'font-size': 'length',
    'font-ui': 'font'
  };
  var FONT_SIZES = { small: 1, 'default': 1, large: 1, xlarge: 1 };

  function tokenValue(kind, value) {
    if (typeof value !== 'string') return '';
    var text = value.trim();
    if (kind === 'colour') { text = text.toLowerCase(); return COLOUR_RE.test(text) || RGB_RE.test(text) ? text : ''; }
    if (kind === 'length') return LENGTH_RE.test(text) ? text : '';
    if (kind === 'font') return FONT_RE.test(text) ? text : '';
    return '';
  }

  function refuse() {
    return Promise.reject(new TypeError('Network access is not available here.'));
  }

  function showStandalone() {
    // Opened outside SynthPulse (no parent or no key): no call is ever made.
    window.fetch = refuse;
    document.addEventListener('DOMContentLoaded', function () {
      var note = document.createElement('div');
      note.className = 'memdash-standalone';
      note.setAttribute('role', 'status');
      note.textContent = 'Open this from Memory in SynthPulse';
      document.body.appendChild(note);
    });
  }

  if (!parentWindow || !key) {
    showStandalone();
    return;
  }

  // ── Language ───────────────────────────────────────────────────────────────
  // The dashboard has no translations of its own. Its screens follow the
  // WebUI language: Dutch from the table below, keyed on the exact English
  // source string, English (the source) for anything else. A MutationObserver
  // applies it to every text node and to placeholder, title and aria-label as
  // app.js renders them; switching back to English restores the source text.
  // <nl-table> Dutch strings keyed on the exact English source (the tests read this block as JSON).
  var NL = {
    "Overview": "Overzicht",
    "Today": "Vandaag",
    "Visualiser": "Visualisatie",
    "Review": "Nakijken",
    "Memories": "Herinneringen",
    "Context Bank": "Context",
    "Lifecycle": "Levensloop",
    "Knowledge Graph": "Kennisnetwerk",
    "Structured memory": "Gestructureerd geheugen",
    "History": "Geschiedenis",
    "Settings": "Instellingen",
    "Memory explorer": "Geheugenverkenner",
    "Open Overview dashboard": "Overzicht openen",
    "Open menu": "Menu openen",
    "Toggle theme": "Thema wisselen",
    "Search memory…": "Zoek in je geheugen…",
    "Search memory": "Zoeken",
    "Private memory, cleanly mapped.": "Je geheugen, overzichtelijk in kaart.",
    "Search, review, and trace working memories, summaries, triples, and consolidation history from one local dashboard.": "Zoek, controleer en volg je herinneringen, samenvattingen, verbanden en samenvoegingen op één plek.",
    "Working": "Werkgeheugen",
    "Episodic": "Langetermijn",
    "Needs review": "Na te kijken",
    "Degraded": "Ingekort",
    "Triples": "Verbanden",
    "Consolidations": "Samenvoegingen",
    "Trust mix": "Betrouwbaarheid",
    "Sources": "Bronnen",
    "Scopes": "Bereik",
    "Top sessions": "Meest actieve gesprekken",
    "Search everything": "Alles doorzoeken",
    "Browse memories": "Herinneringen bekijken",
    "Latest activity": "Laatste activiteit",
    "Open graph": "Netwerk openen",
    "Live memory stream": "Nieuwste herinneringen",
    "Scroll to load older memories.": "Scroll om oudere herinneringen te laden.",
    "Loading older memories…": "Oudere herinneringen laden…",
    "End of memory stream.": "Je hebt alles gezien.",
    "Waiting for memory events…": "Wachten op nieuwe herinneringen…",
    "No data": "Geen gegevens",
    "no data": "geen gegevens",
    "No matching memories.": "Geen herinneringen gevonden.",
    "stated": "zelf gezegd",
    "inferred": "afgeleid",
    "tool": "tool",
    "imported": "geïmporteerd",
    "unknown": "onbekend",
    "hot": "recent",
    "warm": "ouder",
    "cold": "oud",
    "task": "taak",
    "conversation": "gesprek",
    "preference": "voorkeur",
    "import": "import",
    "session": "gesprek",
    "global": "algemeen",
    "working": "werkgeheugen",
    "episodic": "langetermijn",
    "active": "actief",
    "inactive": "niet actief",
    "expired": "verlopen",
    "superseded": "vervangen",
    "memory": "herinnering",
    "memories": "herinneringen",
    "fact": "feit",
    "triple": "verband",
    "triples": "verbanden",
    "consolidation": "samenvoeging",
    "consolidations": "samenvoegingen",
    "no session": "geen gesprek",
    "needs review": "na te kijken",
    "any": "alle",
    "Today in memory": "Vandaag in je geheugen",
    "read-only daily digest": "overzicht van vandaag",
    "Added": "Toegevoegd",
    "Retrieved": "Opgehaald",
    "Lifecycle changes": "Verschoven in de levensloop",
    "Facts": "Feiten",
    "Top entities": "Meest genoemd",
    "Sessions": "Gesprekken",
    "Recalled": "Opgehaald",
    "No memories added today.": "Vandaag zijn er geen herinneringen toegevoegd.",
    "No memories recalled today.": "Vandaag zijn er geen herinneringen opgehaald.",
    "No consolidations today.": "Vandaag zijn er geen samenvoegingen.",
    "memory maps + neural activation views": "je geheugen als kaart en als netwerk",
    "Visualiser mode": "Weergave",
    "Constellation": "Sterrenbeeld",
    "Neural Map": "Netwerkkaart",
    "Refresh visualiser": "Vernieuwen",
    "Reset view": "Beeld herstellen",
    "Pan mode": "Verschuiven",
    "Orbit mode": "Draaien",
    "Rotate mode": "Draaien",
    "Pause rotation": "Draaien stoppen",
    "Resume rotation": "Weer draaien",
    "Pause drift": "Beweging stoppen",
    "Resume drift": "Weer bewegen",
    "Fullscreen": "Volledig scherm",
    "Exit fullscreen": "Volledig scherm sluiten",
    "Drag to rotate · Pan mode/Shift-drag to pan · wheel/pinch to zoom.": "Sleep om te draaien · Verschuiven of Shift en slepen om te verplaatsen · scroll of knijp om te zoomen.",
    "Drag to orbit the neural cloud · Pan mode/Shift-drag to pan · wheel/pinch to zoom.": "Sleep om het netwerk te draaien · Verschuiven of Shift en slepen om te verplaatsen · scroll of knijp om te zoomen.",
    "Drag to orbit · Pan mode to move · pinch to zoom · tap a neuron.": "Sleep om te draaien · Verschuiven om te verplaatsen · knijp om te zoomen · tik op een punt.",
    "Entity/topic": "Onderwerp",
    "Memory": "Herinnering",
    "Link": "Verband",
    "Constellation legend": "Legenda",
    "Interactive 3D memory constellation": "3D-weergave van je geheugen",
    "Interactive 3D memory visualiser": "3D-weergave van je geheugen",
    "Constellation inspector": "Details",
    "Neural inspector": "Details",
    "Graph inspector": "Details",
    "Nothing selected": "Niets gekozen",
    "Pick a star, memory, or link to inspect the underlying read-only source.": "Kies een punt, herinnering of verband om de bron te bekijken.",
    "Pick a neuron hub, memory soma, or synapse to inspect the underlying read-only source.": "Kies een onderwerp, herinnering of verband om de bron te bekijken.",
    "3D visualiser unavailable": "3D-weergave niet beschikbaar",
    "The original Visualiser remains available for this browser.": "Deze browser kan de 3D-weergave niet tonen.",
    "Try the original Visualiser, or reopen this page in a browser that supports the 3D view.": "Open deze pagina in een browser die 3D ondersteunt.",
    "This browser could not start WebGL.": "Deze browser kan geen 3D tonen.",
    "Neuron hub": "Onderwerp",
    "Memory soma": "Herinnering",
    "Synapse": "Verband",
    "Constellation 3D": "Sterrenbeeld in 3D",
    "Neural Map 3D": "Netwerkkaart in 3D",
    "Open memory": "Herinnering openen",
    "Search this": "Hierop zoeken",
    "Selected node": "Gekozen onderwerp",
    "Selected triple": "Gekozen verband",
    "Show in Triples": "In de tabel tonen",
    "No connected edges.": "Geen verbanden.",
    "Trust Review": "Nakijken",
    "triage selected memories: confirm, correct, or forget only what you choose": "bevestig, verbeter of vergeet alleen wat je zelf kiest",
    "Review queue": "Lijst",
    "Search this queue…": "Zoek in deze lijst…",
    "Min importance": "Minimaal belang",
    "Apply filters": "Filters toepassen",
    "Clear": "Wissen",
    "Select listed": "Alles in de lijst kiezen",
    "Confirm selected": "Keuze bevestigen",
    "Set trust": "Betrouwbaarheid instellen",
    "Set expiry": "Einddatum instellen",
    "Forget selected": "Keuze vergeten",
    "Clear selection": "Keuze wissen",
    "Load 100 more": "100 meer laden",
    "Open filtered browser": "Bekijken bij Herinneringen",
    "Select visible": "Zichtbare kiezen",
    "High importance": "Belangrijk",
    "Select memory": "Herinnering kiezen",
    "Review reasons": "Redenen om na te kijken",
    "No review queues available.": "Er zijn geen lijsten om na te kijken.",
    "No items in this queue.": "Deze lijst is leeg.",
    "This queue is clear for now.": "Hier is nu niets te doen.",
    "Memories not directly stated by you: inferred, tool-generated, imported, or unknown.": "Herinneringen die je niet zelf hebt gezegd: afgeleid, door een tool gemaakt, geïmporteerd of onbekend.",
    "Important memories needing review": "Belangrijke herinneringen om na te kijken",
    "Important memories that were inferred, tool-generated, imported, or unknown.": "Belangrijke herinneringen die zijn afgeleid, door een tool gemaakt, geïmporteerd of onbekend zijn.",
    "Episodic memories that have moved down the lifecycle and may carry reduced recall weight.": "Herinneringen die ouder zijn geworden en minder zwaar meetellen bij het ophalen.",
    "Hot or warm episodic memories old enough to be compressed into the next lifecycle tier.": "Recente of oudere herinneringen die oud genoeg zijn om in te korten.",
    "Due for degradation": "Klaar om in te korten",
    "memory browser + recall debug": "bladeren en uitleg bij het ophalen",
    "Recall debug": "Ophalen testen",
    "Memory browser": "Herinneringen bladeren",
    "working + episodic": "werkgeheugen en langetermijn",
    "Search": "Zoeken",
    "Search memory content…": "Zoek in herinneringen…",
    "Set importance": "Belang instellen",
    "Recall debugger": "Ophalen testen",
    "why memories rank": "waarom een herinnering bovenaan staat",
    "Type a recall query…": "Typ een zoekvraag…",
    "Debug recall": "Testen",
    "Type a query to explain approximate recall ranking.": "Typ een zoekvraag om te zien welke herinneringen naar boven komen en waarom.",
    "all tiers": "alle soorten",
    "all sources": "alle bronnen",
    "all scopes": "elk bereik",
    "all sessions": "alle gesprekken",
    "all trust levels": "elke betrouwbaarheid",
    "all lifecycle tiers": "elke fase",
    "hot · full detail": "recent · alle details",
    "warm · compressed": "ouder · ingekort",
    "cold · key signal": "oud · alleen de kern",
    "all confidence": "elke zekerheid",
    "degraded only": "alleen ingekort",
    "due for degradation": "klaar om in te korten",
    "all statuses": "elke status",
    "newest": "nieuwste",
    "oldest": "oudste",
    "importance": "belang",
    "recall count": "vaakst opgehaald",
    "inferred context from active memory": "wat er uit je herinneringen af te leiden is",
    "Pattern insights": "Patronen",
    "Pattern detector": "Patroonherkenning",
    "Memories scanned": "Herinneringen bekeken",
    "Triples scanned": "Verbanden bekeken",
    "Patterns found": "Patronen gevonden",
    "Provider": "Bron",
    "Dashboard": "Overzicht",
    "Content patterns": "Inhoud",
    "No patterns yet.": "Nog geen patronen.",
    "Temporal patterns": "Tijd",
    "Sequence patterns": "Volgorde",
    "Context domains": "Onderwerpen",
    "Dashboard taxonomy": "indeling",
    "Domains": "Onderwerpen",
    "Unclassified": "Niet ingedeeld",
    "Dashboard / visualisers": "Overzichten en weergaven",
    "Preferences": "Voorkeuren",
    "Finance / assets": "Financiën en bezit",
    "Work / business": "Werk en zaken",
    "Projects": "Projecten",
    "Devices": "Apparaten",
    "Origins": "Herkomst",
    "Knowledge graph": "Kennisnetwerk",
    "Direct memory": "Direct onthouden",
    "Conversation": "Gesprek",
    "Migration": "Overgezet",
    "Memory types": "Soorten",
    "Relationship": "Relatie",
    "Fact": "Feit",
    "Project notes": "Projectnotities",
    "Preference": "Voorkeur",
    "Short-term notes": "Korte notities",
    "Temporary context": "Tijdelijke context",
    "Project context": "Projectcontext",
    "Indexed signals": "Signalen",
    "Sensitive": "Gevoelig",
    "Sections": "Onderdelen",
    "Other": "Overig",
    "Other types": "Overige soorten",
    "No inferred profile data found.": "Er is nog niets af te leiden.",
    "hot / warm / cold memory degradation dashboard": "hoe herinneringen ouder worden: recent, ouder, oud",
    "Read-only: no degradation is triggered from this page": "Alleen bekijken: deze pagina kort niets in",
    "Hot memories": "Recente herinneringen",
    "Warm memories": "Oudere herinneringen",
    "Cold memories": "Oude herinneringen",
    "Tier 1 episodic memories retain full detail and full lifecycle weight.": "Fase 1: alle details en het volle gewicht.",
    "Tier 2 episodic memories are compressed and carry reduced recall weight.": "Fase 2: ingekort en minder gewicht bij het ophalen.",
    "Tier 3 episodic memories keep key signal only and carry the lowest lifecycle weight.": "Fase 3: alleen de kern, met het laagste gewicht.",
    "Hot or warm episodic memories old enough to move to the next lifecycle tier.": "Recente of oudere herinneringen die naar de volgende fase kunnen.",
    "Recently degraded": "Onlangs ingekort",
    "Memories already compressed into a lower lifecycle tier.": "Herinneringen die al zijn ingekort.",
    "High-importance degraded": "Belangrijk en ingekort",
    "Important degraded memories worth checking before further lifecycle compression.": "Belangrijke ingekorte herinneringen om te controleren voordat ze verder worden ingekort.",
    "Open lifecycle filter": "Bekijken bij Herinneringen",
    "No lifecycle queues available.": "Er zijn geen lijsten.",
    "relationships + triple table": "verbanden en een tabel met feiten",
    "Relationship graph": "Netwerk",
    "Facts table": "Feitentabel",
    "click nodes / edges to inspect": "klik op een onderwerp of verband voor details",
    "Filter graph by subject / predicate / object…": "Filter op onderwerp, verband of object…",
    "Refresh graph": "Vernieuwen",
    "Scroll to zoom, drag to pan. Click nodes / edges to inspect.": "Scroll om te zoomen, sleep om te verschuiven. Klik op een onderwerp of verband voor details.",
    "Pick a node or edge to inspect connected triples, then jump into the Triples table.": "Kies een onderwerp of verband om de feiten erbij te zien.",
    "knowledge graph facts": "feiten in het kennisnetwerk",
    "Search subject / predicate / object…": "Zoek op onderwerp, verband of object…",
    "Subject": "Onderwerp",
    "Predicate": "Verband",
    "Object": "Object",
    "Confidence": "Zekerheid",
    "No connections match this graph filter.": "Geen verbanden gevonden voor dit filter.",
    "No triples found.": "Geen verbanden gevonden.",
    "structured fact extraction and retrieval": "feiten, tijdlijnen en voorkeuren uit je gesprekken",
    "Timelines": "Tijdlijnen",
    "Instructions": "Instructies",
    "KG": "Netwerk",
    "Table counts": "Aantallen",
    "Tables": "Tabellen",
    "extracted fact triples from conversations": "feiten uit je gesprekken",
    "Search facts…": "Zoek feiten…",
    "temporal event sequences": "gebeurtenissen op volgorde",
    "Search timelines…": "Zoek in tijdlijnen…",
    "extracted instructions and guidelines": "instructies en afspraken",
    "Search instructions…": "Zoek instructies…",
    "knowledge graph triples": "verbanden in het kennisnetwerk",
    "Search KG…": "Zoek in het netwerk…",
    "extracted user preferences": "je voorkeuren",
    "Search preferences…": "Zoek voorkeuren…",
    "No entries found.": "Niets gevonden.",
    "chronological memory events + consolidation history": "alles op volgorde, met de samenvoegingen",
    "Timeline": "Tijdlijn",
    "day / session stream": "per dag of per gesprek",
    "Filter timeline…": "Filter de tijdlijn…",
    "group by day": "per dag",
    "group by session": "per gesprek",
    "Load timeline": "Tijdlijn laden",
    "click entries to inspect": "klik op een regel voor details",
    "Filter summaries / sessions…": "Filter samenvattingen of gesprekken…",
    "Each run shows compressed-memory previews and session actions.": "Elke samenvoeging toont de ingekorte herinneringen en het gesprek erbij.",
    "Inspect": "Bekijken",
    "View session memories": "Herinneringen uit dit gesprek",
    "No timeline events.": "Geen gebeurtenissen.",
    "No consolidations found.": "Geen samenvoegingen gevonden.",
    "Timeline by session": "Tijdlijn per gesprek",
    "No events for this session.": "Geen gebeurtenissen in dit gesprek.",
    "results from memories, triples, and consolidations": "resultaten uit herinneringen, verbanden en samenvoegingen",
    "Search everything…": "Zoek overal…",
    "Search looks across memories, facts, and consolidations.": "Zoeken kijkt in herinneringen, feiten en samenvoegingen.",
    "Search from the sidebar or type a query above.": "Zoek via de zijbalk of typ hierboven een zoekvraag.",
    "Searching memory…": "Zoeken…",
    "Search failed.": "Zoeken is mislukt.",
    "The dashboard could not load search results.": "De zoekresultaten konden niet worden geladen.",
    "Search memories": "Herinneringen zoeken",
    "Detail": "Details",
    "Close detail": "Details sluiten",
    "Memory detail": "Herinnering",
    "Search result detail": "Zoekresultaat",
    "Consolidation detail": "Samenvoeging",
    "Triple detail": "Verband",
    "Triple edge detail": "Verband",
    "Session event detail": "Gebeurtenis",
    "Timeline event detail": "Gebeurtenis",
    "Profile source detail": "Bron",
    "Copy": "Kopiëren",
    "Copy ID": "ID kopiëren",
    "Copy session ID": "Gespreks-ID kopiëren",
    "Open session": "Gesprek openen",
    "Memory ID": "ID van de herinnering",
    "Session ID": "Gespreks-ID",
    "Session": "Gesprek",
    "Source": "Bron",
    "Status": "Status",
    "Importance": "Belang",
    "Trust": "Betrouwbaarheid",
    "Freshness": "Actualiteit",
    "Valid until": "Geldig tot",
    "Superseded by": "Vervangen door",
    "Effective weight": "Gewicht",
    "Why shown": "Waarom je dit ziet",
    "Ranking": "Volgorde",
    "Reason": "Reden",
    "Inspect JSON": "Ruwe gegevens",
    "Confidence unknown": "Zekerheid onbekend",
    "Origin": "Herkomst",
    "Cancel": "Annuleren",
    "Confirm": "Bevestigen",
    "Done": "Klaar",
    "Close dialog": "Venster sluiten",
    "Confirm action": "Bevestigen",
    "Forget memory": "Herinnering vergeten",
    "Forget now": "Nu vergeten",
    "Forget this memory?": "Deze herinnering vergeten?",
    "Forget selected memories?": "Gekozen herinneringen vergeten?",
    "Confirm selected memories?": "Gekozen herinneringen bevestigen?",
    "Edit importance": "Belang wijzigen",
    "Supersede": "Vervangen",
    "Supersede memory": "Herinnering vervangen",
    "Create replacement": "Vervanging maken",
    "Save trust": "Opslaan",
    "Save expiry": "Opslaan",
    "Save importance": "Opslaan",
    "Trust / veracity": "Betrouwbaarheid",
    "Set trust / veracity": "Betrouwbaarheid instellen",
    "Replacement memory content": "Nieuwe tekst van de herinnering",
    "Blank means no scheduled expiry.": "Leeg laten betekent geen einddatum.",
    "You can view these memories but not change them.": "Je kunt deze herinneringen bekijken, maar niet wijzigen.",
    "Forgotten.": "Vergeten.",
    "Saved": "Opgeslagen",
    "Ready": "Klaar",
    "Unavailable": "Niet beschikbaar",
    "Healthy": "In orde",
    "Needs attention": "Aandacht nodig",
    "Needs-review memory": "Herinnering om na te kijken",
    "Dashboard failed to finish loading.": "De verkenner is niet helemaal geladen.",
    "Retry load": "Opnieuw laden",
    "Open this from Memory in SynthPulse": "Open dit via Geheugen in SynthPulse",
    "Explorer": "Verkenner",
    "entity": "onderwerp",
    "Search results for": "Resultaten voor",
    "No results found.": "Niets gevonden.",
    "Try broader terms, a person/project name, or search inside Memories for record-only filters.": "Probeer een ruimere zoekterm, of de naam van een persoon of project.",
    "No memory records matched.": "Geen herinneringen gevonden.",
    "No graph facts matched.": "Geen feiten gevonden.",
    "No consolidation summaries matched.": "Geen samenvoegingen gevonden.",
    "Approximate debugger: uses text matches, importance, and recall_count available in SQLite. It does not expose Mnemosyne's internal vector score unless upstream stores it.": "Een benadering: telt overeenkomende woorden, het belang en hoe vaak een herinnering is opgehaald. De interne score van het geheugen is hier niet te zien.",
    "shown from the current list/search context": "getoond vanuit de huidige lijst of zoekopdracht",
    "needs-review filter matched": "past bij het filter na te kijken",
    "degraded-only filter matched": "past bij het filter alleen ingekort",
    "none": "geen",
    "never": "nooit",
    "not degraded": "niet ingekort",
    "unknown source": "bron onbekend",
    "unknown scope": "bereik onbekend",
    "ID": "ID",
    "review recommended": "nakijken aanbevolen"
  };
  // </nl-table>
  // A source string that means something else in one place: the brand and
  // the two-letter badges of the menu (KG is also a Structured memory tab).
  var NL_CONTEXT = [
    ['.brand-name', 'Memory', 'Geheugen'],
    ['nav button span', 'OV', 'OV'], ['nav button span', 'TD', 'VD'], ['nav button span', 'RV', 'NK'],
    ['nav button span', 'MM', 'HR'], ['nav button span', 'CB', 'CT'], ['nav button span', 'LC', 'LL'],
    ['nav button span', 'KG', 'KN'], ['nav button span', 'SM', 'GG'], ['nav button span', 'HS', 'GS'],
    ['nav button span', 'ST', 'IN']
  ];
  function nlWord(word) {
    return Object.prototype.hasOwnProperty.call(NL, word) ? NL[word] : word;
  }
  function plural(n, one, many) { return String(n).replace(/[.,]/g, '') === '1' ? one : many; }
  var CONFIDENCE = { High: 'Hoge', Medium: 'Gemiddelde', Low: 'Lage' };
  // Strings with numbers or names in them.
  var NL_PATTERNS = [
    [/^([\d.,]+) latest memories$/, function (m) { return m[1] + ' nieuwste herinneringen'; }],
    [/^([\d.,]+) items?$/, function (m) { return m[1] + plural(m[1], ' item', ' items'); }],
    [/^([\d.,]+) entries$/, function (m) { return m[1] + plural(m[1], ' item', ' items'); }],
    [/^([\d.,]+) listed$/, function (m) { return m[1] + ' in de lijst'; }],
    [/^([\d.,]+) total · ([\d.,]+) listed$/, function (m) { return m[1] + ' totaal · ' + m[2] + ' in de lijst'; }],
    [/^([\d.,]+) selected$/, function (m) { return m[1] + ' gekozen'; }],
    [/^([\d.,]+) selected · ([\d.,]+) active$/, function (m) { return m[1] + ' gekozen · ' + m[2] + ' actief'; }],
    [/^([\d.,]+) events$/, function (m) { return m[1] + plural(m[1], ' gebeurtenis', ' gebeurtenissen'); }],
    [/^([\d.,]+) active items?$/, function (m) { return m[1] + plural(m[1], ' actief item', ' actieve items'); }],
    [/^([\d.,]+) connected triples?\.$/, function (m) { return m[1] + plural(m[1], ' verband.', ' verbanden.'); }],
    [/^Needs review · (\d+%)$/, function (m) { return 'Na te kijken · ' + m[1]; }],
    [/^(High|Medium|Low) confidence · (\d+%)$/, function (m) { return CONFIDENCE[m[1]] + ' zekerheid · ' + m[2]; }],
    [/^Tier (\d) after ([\d.,]+) days$/, function (m) { return 'Fase ' + m[1] + ' na ' + m[2] + ' dagen'; }],
    [/^Weights: hot ×(\S+) · warm ×(\S+) · cold ×(\S+)$/, function (m) {
      return 'Gewicht: recent ×' + m[1] + ' · ouder ×' + m[2] + ' · oud ×' + m[3];
    }],
    [/^(hot|warm|cold) · T(\d)$/, function (m) { return nlWord(m[1]) + ' · fase ' + m[2]; }],
    [/^(\w+) trust · ×(\S+)$/, function (m) { return nlWord(m[1]) + ' · ×' + m[2]; }],
    [/^memory type: (.+)$/, function (m) { return 'soort: ' + nlWord(m[1]); }],
    [/^veracity: (\w+) · recall weight (\S+)$/, function (m) { return 'betrouwbaarheid: ' + nlWord(m[1]) + ' · gewicht ' + m[2]; }],
    [/^degradation tier: (\d) · recall weight (\S+)$/, function (m) { return 'fase ' + m[1] + ' · gewicht ' + m[2]; }],
    [/^importance: (\S+)$/, function (m) { return 'belang: ' + m[1]; }],
    [/^scope: (.+)$/, function (m) { return 'bereik: ' + nlWord(m[1]); }],
    [/^Open session: (.+)$/, function (m) { return 'Gesprek openen: ' + m[1]; }],
    [/^Filter memories for (.+)$/, function (m) { return 'Herinneringen filteren op ' + nlWord(m[1]); }],
    [/^Search results for “(.+)”$/, function (m) { return 'Resultaten voor “' + m[1] + '”'; }],
    [/^([\d.,]+) results? · ([\d.,]+) memor(?:y|ys|ies) · ([\d.,]+) facts? · ([\d.,]+) consolidations?$/, function (m) {
      return m[1] + plural(m[1], ' resultaat', ' resultaten') + ' · ' + m[2] + plural(m[2], ' herinnering', ' herinneringen') +
        ' · ' + m[3] + plural(m[3], ' feit', ' feiten') + ' · ' + m[4] + plural(m[4], ' samenvoeging', ' samenvoegingen');
    }],
    [/^(.+) · ([\d.,]+) signal\(s\) · weight (\S+)$/, function (m) {
      return nlWord(m[1]) + ' · ' + m[2] + plural(m[2], ' signaal', ' signalen') + ' · gewicht ' + m[3];
    }],
    [/^Matched terms: (.+)$/, function (m) { return 'Gevonden woorden: ' + m[1]; }],
    [/^Importance contributes (\S+)$/, function (m) { return 'Belang telt mee voor ' + m[1]; }],
    [/^Previously recalled ([\d.,]+) time\(s\)$/, function (m) { return 'Eerder ' + m[1] + ' keer opgehaald'; }],
    [/^Scope: (.+)$/, function (m) { return 'Bereik: ' + nlWord(m[1]); }],
    [/^Source: (.+)$/, function (m) { return 'Bron: ' + nlWord(m[1]); }],
    [/^Trust: (\w+) ×(\S+)$/, function (m) { return 'Betrouwbaarheid: ' + nlWord(m[1]) + ' ×' + m[2]; }],
    [/^Lifecycle: (\w+) ×(\S+)$/, function (m) { return 'Levensloop: ' + nlWord(m[1]) + ' ×' + m[2]; }],
    [/^Effective memory weight: ×(\S+)$/, function (m) { return 'Gewicht van de herinnering: ×' + m[1]; }],
    [/^effective ×(\S+)$/, function (m) { return 'gewicht ×' + m[1]; }],
    [/^(hot|warm|cold) · tier (\d)( · ×\S+)?$/, function (m) { return nlWord(m[1]) + ' · fase ' + m[2] + (m[3] || ''); }],
    [/^not degraded( · ×\S+)?$/, function (m) { return 'niet ingekort' + (m[1] || ''); }],
    [/^(\w+) · recall weight ×(\S+)( · review recommended)?$/, function (m) {
      return nlWord(m[1]) + ' · gewicht ×' + m[2] + (m[3] ? ' · nakijken aanbevolen' : '');
    }],
    [/^(.+?) · degraded (.+) · recall weight ×(\S+)$/, function (m) {
      return (translate(m[1]) || m[1]) + ' · ingekort ' + nlWord(m[2]) + ' · gewicht ×' + m[3];
    }],
    [/^(\w+) · importance (\S+) · recalled (\S+)×$/, function (m) {
      return nlWord(m[1]) + ' · belang ' + m[2] + ' · ' + m[3] + '× opgehaald';
    }],
    [/^created (.+) · last recalled (.+)$/, function (m) { return 'gemaakt ' + nlWord(m[1]) + ' · laatst opgehaald ' + nlWord(m[2]); }],
    [/^(source|scope|session|trust) filter matched (.+)$/, function (m) {
      return 'past bij het filter ' + { source: 'bron', scope: 'bereik', session: 'gesprek', trust: 'betrouwbaarheid' }[m[1]] + ' ' + nlWord(m[2]);
    }],
    [/^([a-z]+) · ([a-z]+(?: [a-z]+)?) · ([a-z]+(?: [a-z]+)?)$/, function (m) {
      return nlWord(m[1]) + ' · ' + nlWord(m[2]) + ' · ' + nlWord(m[3]);
    }],
    [/^(Constellation|Neural Map|Constellation 3D|Neural Map 3D) · (\w+)$/, function (m) { return nlWord(m[1]) + ' · ' + nlWord(m[2]); }]
  ];
  var I18N_ATTRS = ['placeholder', 'title', 'aria-label'];
  // Never translated: memory text, raw JSON and labels that are the user's
  // own data. The detail drawer is a pre that holds HTML (.html-detail).
  var I18N_SKIP = 'script, style, pre:not(.html-detail), code, textarea, .content, .three-labels';
  var lang = params.get('lang') === 'nl' ? 'nl' : 'en';
  var textState = new WeakMap();
  var attrState = new WeakMap();
  var translatedOnce = false;

  function translate(source, el) {
    for (var i = 0; i < NL_CONTEXT.length; i += 1) {
      if (NL_CONTEXT[i][1] === source && el && el.closest && el.closest(NL_CONTEXT[i][0])) return NL_CONTEXT[i][2];
    }
    if (Object.prototype.hasOwnProperty.call(NL, source)) return NL[source];
    for (var j = 0; j < NL_PATTERNS.length; j += 1) {
      var m = NL_PATTERNS[j][0].exec(source);
      if (m) return NL_PATTERNS[j][1](m);
    }
    return null;
  }

  function skipped(el) {
    return !el || (el.closest && el.closest(I18N_SKIP));
  }

  // Keeps the whitespace around the source string.
  function swap(value, source, out) {
    var at = value.indexOf(source);
    return value.slice(0, at) + out + value.slice(at + source.length);
  }

  function applyText(node) {
    var value = node.nodeValue;
    var known = textState.get(node);
    if (known && value === known.out) {
      if (lang === 'nl') return;
      textState.delete(node);
      node.nodeValue = known.src;
      return;
    }
    textState.delete(node);
    if (lang !== 'nl' || !value || skipped(node.parentElement)) return;
    var source = value.trim();
    if (!source || !/[A-Za-z]/.test(source)) return;
    var out = translate(source, node.parentElement);
    if (out === null || out === source) return;
    var full = swap(value, source, out);
    textState.set(node, { src: value, out: full });
    node.nodeValue = full;
  }

  function applyAttr(el, name) {
    var value = el.getAttribute(name);
    var states = attrState.get(el);
    var known = states && states[name];
    if (known && value === known.out) {
      if (lang === 'nl') return;
      delete states[name];
      el.setAttribute(name, known.src);
      return;
    }
    if (states) delete states[name];
    if (lang !== 'nl' || value === null || skipped(el)) return;
    var source = value.trim();
    if (!source || !/[A-Za-z]/.test(source)) return;
    var out = translate(source, el);
    if (out === null || out === source) return;
    if (!states) { states = {}; attrState.set(el, states); }
    states[name] = { src: value, out: out };
    el.setAttribute(name, out);
  }

  function applyTree(rootNode) {
    if (!rootNode) return;
    if (rootNode.nodeType === 3) { applyText(rootNode); return; }
    if (rootNode.nodeType !== 1) return;
    var walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var node = rootNode;
    while (node) {
      if (node.nodeType === 3) applyText(node);
      else for (var i = 0; i < I18N_ATTRS.length; i += 1) if (node.hasAttribute(I18N_ATTRS[i])) applyAttr(node, I18N_ATTRS[i]);
      node = walker.nextNode();
    }
  }

  function setLang(next) {
    next = next === 'nl' ? 'nl' : 'en';
    if (next === lang && translatedOnce) return;
    lang = next;
    document.documentElement.setAttribute('lang', lang);
    if (lang === 'nl' || translatedOnce) applyTree(document.body);
    translatedOnce = true;
  }

  function watchLanguage() {
    if (typeof MutationObserver !== 'function' || !document.body) return;
    new MutationObserver(function (records) {
      if (lang !== 'nl') return;
      records.forEach(function (record) {
        if (record.type === 'characterData') applyText(record.target);
        else if (record.type === 'attributes') applyAttr(record.target, record.attributeName);
        else record.addedNodes.forEach(applyTree);
      });
    }).observe(document.body, {
      subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: I18N_ATTRS
    });
  }

  // The shim runs at the end of the body: the static screens are there already.
  setLang(lang);
  watchLanguage();

  // ── Canvas colours ─────────────────────────────────────────────────────────
  // The 3D visualiser draws with colours from app.js palette functions
  // (constellationColors, neuralColors, colorForTheme). They are globals of
  // the classic app.js script, so they are wrapped here, without changing
  // app.js: with the SynthPulse appearance set, nodes, links, labels and the
  // background come from the --sp-* tokens, read from the computed style. A
  // theme or skin change draws the scene again. The knowledge graph is SVG
  // and follows the tokens through memdash-overrides.css.
  function parseColour(text) {
    var value = String(text || '').trim().toLowerCase();
    var m = /^#([0-9a-f]{3,8})$/.exec(value);
    if (m) {
      var h = m[1];
      if (h.length === 3 || h.length === 4) h = h.split('').map(function (c) { return c + c; }).join('');
      if (h.length !== 6 && h.length !== 8) return null;
      return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
    }
    m = /^rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})/.exec(value);
    if (m) return [Math.min(255, +m[1]), Math.min(255, +m[2]), Math.min(255, +m[3])];
    return null;
  }
  function token(name) {
    return parseColour(getComputedStyle(document.documentElement).getPropertyValue('--sp-' + name));
  }
  function mix(a, b, share) {
    return [0, 1, 2].map(function (i) { return Math.round(a[i] * share + b[i] * (1 - share)); });
  }
  function hex(c) {
    return '#' + c.map(function (v) { return (v < 16 ? '0' : '') + v.toString(16); }).join('');
  }
  function rgba(c, alpha) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + alpha + ')'; }
  function int(c) { return (c[0] << 16) | (c[1] << 8) | c[2]; }

  function palette() {
    var root = document.documentElement;
    if (!root.hasAttribute('data-sp-appearance')) return null;
    var bg = token('bg'), text = token('text'), accent = token('accent');
    if (!bg || !text || !accent) return null;
    return {
      light: root.dataset.theme === 'light',
      bg: bg, text: text, accent: accent,
      muted: token('muted') || mix(text, bg, 0.6),
      // Memories next to topics: the warning tone of the skin, else a shade of the accent.
      second: token('warning') || token('accent-hover') || mix(accent, text, 0.5)
    };
  }

  function wrapPalettes() {
    if (typeof window.constellationColors === 'function') {
      var constellation = window.constellationColors;
      window.constellationColors = function () {
        var base = constellation.apply(this, arguments);
        var p = palette();
        if (!p) return base;
        return Object.assign({}, base, {
          light: p.light, bg: hex(p.bg), nebula: rgba(p.accent, p.light ? 0.1 : 0.14), star: hex(p.accent),
          memory: hex(p.second), text: hex(p.text), muted: rgba(p.muted, 0.8),
          edge: rgba(mix(p.accent, p.text, 0.45), p.light ? 0.5 : 0.44), memoryEdge: rgba(p.second, 0.5)
        });
      };
    }
    if (typeof window.neuralColors === 'function') {
      var neural = window.neuralColors;
      window.neuralColors = function () {
        var base = neural.apply(this, arguments);
        var p = palette();
        if (!p) return base;
        return Object.assign({}, base, {
          light: p.light, bg: hex(p.bg), core: rgba(p.accent, p.light ? 0.16 : 0.26), mid: rgba(p.second, p.light ? 0.1 : 0.2),
          star: hex(p.accent), memory: hex(p.second), text: hex(p.text),
          synapse: rgba(p.accent, p.light ? 0.32 : 0.24), synapseHot: rgba(p.accent, p.light ? 0.6 : 0.52),
          memorySynapse: rgba(p.second, 0.58)
        });
      };
    }
    if (typeof window.colorForTheme === 'function') {
      var forTheme = window.colorForTheme;
      window.colorForTheme = function () {
        var base = forTheme.apply(this, arguments);
        var p = palette();
        if (!p || !base || typeof base !== 'object') return base;
        var neuralMode = false;
        try { neuralMode = threeVis.mode === 'neural'; } catch (_) { neuralMode = false; }
        return Object.assign({}, base, {
          link: int(neuralMode ? p.accent : mix(p.accent, p.text, 0.45)),
          pulse: int(neuralMode ? mix(p.text, p.accent, 0.35) : p.second)
        });
      };
    }
  }

  var repaintTimer = null;
  function repaintCanvases() {
    // Draw the 3D scene again with the new colours (a no-op before the first draw).
    if (repaintTimer) clearTimeout(repaintTimer);
    repaintTimer = setTimeout(function () {
      repaintTimer = null;
      try {
        if (threeVis && threeVis.renderer && threeVis.data && typeof window.renderThreeVisualiser === 'function') {
          window.renderThreeVisualiser(threeVis.data);
        }
      } catch (_) { /* app.js not ready or no scene yet */ }
    }, 60);
  }

  document.addEventListener('DOMContentLoaded', wrapPalettes);

  function applyTheme(msg) {
    if (msg.lang === 'nl' || msg.lang === 'en') setLang(msg.lang);
    var mode = msg.theme === 'light' ? 'light' : 'dark';
    var root = document.documentElement;
    if (typeof window.setTheme === 'function') {
      try { window.setTheme(mode); } catch (_) { root.dataset.theme = mode; }
    } else {
      root.dataset.theme = mode;
    }
    var tokens = msg.tokens && typeof msg.tokens === 'object' ? msg.tokens : null;
    if (tokens) {
      // The full WebUI appearance: memdash-overrides.css maps --sp-* onto the
      // dashboard's own variables while data-sp-appearance is set.
      var applied = 0;
      Object.keys(TOKEN_KINDS).forEach(function (name) {
        var value = tokenValue(TOKEN_KINDS[name], tokens[name]);
        if (value) { root.style.setProperty('--sp-' + name, value); applied += 1; }
        else root.style.removeProperty('--sp-' + name);
      });
      if (applied) root.setAttribute('data-sp-appearance', '');
      else root.removeAttribute('data-sp-appearance');
      root.setAttribute('data-sp-font-size', FONT_SIZES[msg.fontSize] === 1 ? msg.fontSize : 'default');
      repaintCanvases();
      return;
    }
    var colours = msg.colours && typeof msg.colours === 'object' ? msg.colours : {};
    Object.keys(COLOUR_VARS).forEach(function (name) {
      var value = colours[name];
      if (typeof value === 'string' && COLOUR_RE.test(value)) root.style.setProperty(COLOUR_VARS[name], value);
    });
  }

  function toQuery(searchParams) {
    var out = {};
    searchParams.forEach(function (value, name) { out[name] = value; });
    return out;
  }

  window.addEventListener('message', function (event) {
    if (event.source !== parentWindow) return;
    var msg = event.data;
    if (!msg || typeof msg !== 'object' || msg.v !== 1 || msg.k !== key) return;
    if (msg.type === 'memdash:theme') { applyTheme(msg); return; }
    if (msg.type !== 'memdash:res' || typeof msg.id !== 'number') return;
    var entry = pending.get(msg.id);
    if (!entry) return;
    pending.delete(msg.id);
    clearTimeout(entry.timer);
    var status = Number(msg.status) || 502;
    if (status < 200 || status > 599) status = 502;
    var body = JSON.stringify(msg.body === undefined ? null : msg.body);
    entry.resolve(new Response(body, { status: status, headers: { 'Content-Type': 'application/json' } }));
  });

  window.fetch = function (input, init) {
    var raw = typeof input === 'string' ? input : (input && typeof input.url === 'string' ? input.url : '');
    if (typeof raw !== 'string' || raw.indexOf('/api/') !== 0) return refuse();
    var url;
    try { url = new URL(raw, location.href); } catch (_) { return refuse(); }
    if (url.pathname.indexOf('/api/') !== 0) return refuse();
    var method = String((init && init.method) || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'POST') return refuse();
    var body = null;
    if (init && typeof init.body === 'string' && init.body) {
      try { body = JSON.parse(init.body); } catch (_) { return refuse(); }
    }
    var id = nextId++;
    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () {
        pending.delete(id);
        reject(new TypeError('The request timed out.'));
      }, TIMEOUT_MS);
      pending.set(id, { resolve: resolve, reject: reject, timer: timer });
      parentWindow.postMessage({
        v: 1, type: 'memdash:req', k: key, id: id, method: method,
        path: url.pathname.slice('/api/'.length), query: toQuery(url.searchParams), body: body
      }, targetOrigin);
    });
  };

  parentWindow.postMessage({ v: 1, type: 'memdash:ready', k: key }, targetOrigin);
})();
