// Data block checks for static/interactive-ui/kit-core.js (and the fence seam
// in static/interactive_ui.js), run by tests/test_interactive_kits.py.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const K = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kit-core.js'));
const plain = v => JSON.parse(JSON.stringify(v));
const build = (kind, value, opts) => K.build(kind, typeof value === 'string' ? value : JSON.stringify(value), Object.assign({lang: 'nl'}, opts));

// ── Lenient JSON ─────────────────────────────────────────────────────────────
assert.deepStrictEqual(plain(K.parseKit('{"a":1, // note\n "b":[1,2,],\n /* c */ "c":"x // not a comment",}').value),
  {a: 1, b: [1, 2], c: 'x // not a comment'});
assert.deepStrictEqual(plain(K.parseKit('\uFEFF{"a":"b,}"}').value), {a: 'b,}'}, 'commas and braces in strings stay');
assert.deepStrictEqual(plain(K.parseKit('{"a":[1, /* x */ ], }').value), {a: [1]}, 'a comma before a comment and ] is trailing');
const bad = K.parseKit('{\n "a": 1\n "b": 2\n}');
assert.strictEqual(bad.ok, false);
assert.strictEqual(bad.line, 3, 'the error names the line');

// ── CSV ──────────────────────────────────────────────────────────────────────
assert.deepStrictEqual(K.parseCsv('a,b\n"x, y","He said ""hi"""\n').rows, [['a', 'b'], ['x, y', 'He said "hi"']]);
assert.deepStrictEqual(K.parseCsv('naam;bedrag\r\n"De Vries; BV";"1.234,50"\r\nB;2\r\n').rows,
  [['naam', 'bedrag'], ['De Vries; BV', '1.234,50'], ['B', '2']]);
assert.strictEqual(K.parseCsv('a;b\n1;2').delimiter, ';');
assert.strictEqual(K.parseCsv('a\tb\n1\t2').delimiter, '\t');
assert.strictEqual(K.parseCsv('a,b,c;d\n1,2').delimiter, ',', 'the most frequent separator wins');
assert.strictEqual(K.parseCsv('a,b;c\n1,2').delimiter, ';', 'a tie goes to the Dutch separator');
assert.deepStrictEqual(K.parseCsv('a,b\n"line\nbreak",2').rows, [['a', 'b'], ['line\nbreak', '2']], 'newlines inside quotes');
assert.deepStrictEqual(K.parseCsv('"a;b";c\n1;2').rows, [['a;b', 'c'], ['1', '2']], 'quoted delimiter in the header');
const csv = K.build('table', 'Naam;Plaats;Bedrag\n"Jansen; Zonen";Utrecht;"1.234,50"\nVan Dijk;Den Haag;2.100\n', {lang: 'nl', fence: 'csv'});
assert.deepStrictEqual(csv.errors, []);
assert.deepStrictEqual(plain(csv.spec.columns.map(c => [c.label, c.type])), [['Naam', 'text'], ['Plaats', 'text'], ['Bedrag', 'number']]);
assert.deepStrictEqual(plain(csv.spec.rows), [['Jansen; Zonen', 'Utrecht', 1234.5], ['Van Dijk', 'Den Haag', 2100]]);
assert.strictEqual(csv.title, 'Tabel');
assert.deepStrictEqual(K.build('table', '\n\n', {fence: 'csv'}).errors.length, 1, 'an empty csv block is fatal');

// ── Numbers ──────────────────────────────────────────────────────────────────
const num = v => K.parseNumber(v).n;
for (const [text, value] of [['1.234,50', 1234.5], ['1,234.50', 1234.5], ['€ 1.234', 1234], ['€12,50', 12.5], ['12%', 12],
  ['12,5 %', 12.5], ['1.500', 1500], ['1,5', 1.5], ['0.125', 0.125], ['-3,2', -3.2], ['(5)', -5], ['1.234.567', 1234567],
  ['1,234,567', 1234567], ['EUR 99', 99], ['€ 10,-', 10], ['\u2212 7', -7], [42, 42]]) {
  assert.strictEqual(num(text), value, `parseNumber(${JSON.stringify(text)})`);
}
assert.strictEqual(num('1 234 567'), 1234567, 'spaces as thousands separator');
for (const text of ['abc', '1.2.3', '1,23,4', '', '12-11-2026', '06 12345678', '0612345678', '007', '1234 AB', null, true]) {
  assert.ok(Number.isNaN(num(text)), `parseNumber(${JSON.stringify(text)}) is not a number`);
}
assert.strictEqual(K.parseNumber('€ 5').kind, 'currency');
assert.strictEqual(K.parseNumber('5%').kind, 'percent');

// ── table ────────────────────────────────────────────────────────────────────
const table = build('table', {title: 'Klanten', columns: ['Naam', {label: 'Omzet', type: 'currency'}, 'Groei', 'Sinds'],
  rows: [['A', '€ 1.200', '12%', '2024-03-01'], ['B', 800, '5%', '2025-01-15'], ['C', null, '-2%', '2023-11-30']],
  sort: {column: 'Omzet', dir: 'desc'}, total: true});
assert.deepStrictEqual(table.errors, []);
assert.deepStrictEqual(table.warnings, []);
assert.deepStrictEqual(plain(table.spec.columns.map(c => c.type)), ['text', 'currency', 'percent', 'date'], 'types read from the cells (90% rule)');
assert.deepStrictEqual(plain(table.spec.rows[0]), ['A', 1200, 12, '2024-03-01']);
assert.deepStrictEqual(plain(table.spec.sort), {col: 1, dir: 'desc'});
assert.strictEqual(table.spec.filter, false, 'search only shows for more than 10 rows by default');
assert.ok(table.estHeight > 100 && table.estHeight < 400);
// Fixable: rows padded or cut, with a warning that names the row.
const fixable = build('table', {title: 'T', columns: ['a', 'b', 'c', 'd', 'e'], rows: [[1, 2, 3, 4, 5], [1, 2, 3, 4], [1, 2, 3, 4, 5, 6], {a: 'x', e: 'y'}, 'no']});
assert.deepStrictEqual(fixable.errors, []);
assert.ok(fixable.warnings.includes('Rij 2 heeft 4 waarden, verwacht 5.'), fixable.warnings);
assert.ok(fixable.warnings.includes('Rij 3 heeft 6 waarden, verwacht 5.'), fixable.warnings);
assert.ok(fixable.warnings.includes('Rij 5 is geen lijst met waarden en is weggelaten.'), fixable.warnings);
assert.deepStrictEqual(plain(fixable.spec.rows.map(r => r.length)), [5, 5, 5, 5]);
assert.deepStrictEqual(plain(fixable.spec.rows[3]), ['x', null, null, null, 'y'], 'an object row is read by column label');
// Limits: 12 columns, 500 rows, long text cut.
const big = build('table', {title: 'x'.repeat(200), columns: Array.from({length: 14}, (_, i) => 'k' + i), rows: Array.from({length: 520}, () => Array(14).fill('y'))});
assert.strictEqual(big.spec.columns.length, 12);
assert.strictEqual(big.spec.rows.length, 500);
assert.ok(big.spec.title.length <= 120);
assert.strictEqual(big.spec.filter, true);
assert.ok(build('table', {title: 't', columns: ['a'], rows: [['y'.repeat(400)]]}).spec.rows[0][0].length <= 300, 'long cells are cut');
assert.deepStrictEqual(build('table', '{"title":"t","columns":["a"],"rows":[["' + 'y'.repeat(210 * 1024) + '"]]}').errors, ['De gegevens zijn te groot (meer dan 200 kB).']);
// English messages for an English chat.
assert.ok(build('table', {title: 'T', columns: ['a', 'b'], rows: [[1]]}, {lang: 'en'}).warnings.includes('Row 1 has 1 values, expected 2.'));
// Fatal: nothing can be drawn.
assert.deepStrictEqual(build('table', '{"title": "x", "columns": [').errors.length, 1);
assert.ok(/geen geldige JSON/.test(build('table', '{"title": "x", "columns": [').errors[0]));
assert.deepStrictEqual(build('table', {title: 'x', rows: [[1]]}).errors, ['Er zijn geen kolommen (columns).']);
assert.deepStrictEqual(build('table', '[1, 2]').errors, ['De gegevens moeten één JSON-object zijn.']);
assert.ok(build('table', {title: 'x', columns: ['a'], rows: []}).spec, 'an empty table is allowed');
// A missing title is fixable.
const untitled = build('table', {columns: ['a'], rows: [[1]]});
assert.strictEqual(untitled.spec.title, 'Tabel');
assert.ok(untitled.warnings.includes('De titel ontbreekt.'));
// Status tones only take the four known values.
assert.deepStrictEqual(plain(build('table', {title: 't', columns: [{label: 's', type: 'status'}], rows: [['Klaar']], tones: {Klaar: 'good', Oud: 'purple'}}).spec.tones), {klaar: 'good'});

// ── View, totals and export ──────────────────────────────────────────────────
const spec = table.spec;
assert.deepStrictEqual(K.viewIndices(spec, {s: [1, 'asc'], q: ''}, 'nl'), [1, 0, 2], 'empty cells sort last');
assert.deepStrictEqual(K.viewIndices(spec, {s: [1, 'desc'], q: ''}, 'nl'), [0, 1, 2]);
assert.deepStrictEqual(K.viewIndices(spec, {s: null, q: 'b'}, 'nl'), [1]);
assert.deepStrictEqual(K.viewIndices(spec, {s: null, q: '1.200'}, 'nl'), [0], 'search also matches the shown number');
assert.deepStrictEqual(plain(K.totals(spec, [0, 1, 2])), [null, 2000, null, null]);
const exported = K.toCsv(K.kitTable('table', spec, {s: [1, 'asc'], q: ''}), {delimiter: ';', decimalComma: true});
assert.ok(exported.startsWith('\uFEFFNaam;Omzet;Groei;Sinds\r\n'), exported);
assert.ok(exported.includes('B;800;5;2025-01-15\r\n'));
const injected = K.toCsv({header: ['a', 'b'], rows: [['=HYPERLINK("x")', 1.5], ['a;b', 'say "hi"'], [-2, '@x']]}, {delimiter: ';', decimalComma: true});
assert.strictEqual(injected, '\uFEFFa;b\r\n"\'=HYPERLINK(""x"")";1,5\r\n"a;b";"say ""hi"""\r\n-2;\'@x\r\n', 'formulas never start a cell; numbers use a decimal comma');
assert.strictEqual(K.toTsv({header: ['a', 'b'], rows: [['x\ty', 2.25]]}), 'a\tb\nx y\t2,25');
assert.strictEqual(K.formatValue(1234.5, 'currency', null, 'nl'), '€\u00a01.234,50');
assert.strictEqual(K.formatValue(12.5, 'percent', null, 'nl'), '12,5%');
assert.strictEqual(K.formatValue(1234567, 'number', null, 'nl'), '1.234.567');
assert.strictEqual(K.formatValue('2026-11-08', 'date', null, 'nl'), '8 nov 2026');

// ── chart ────────────────────────────────────────────────────────────────────
const chart = build('chart', {type: 'line', title: 'Omzet', labels: ['Jan', 'Feb', 'Mrt'],
  series: [{name: 'Omzet', data: [100, '1.200', null]}, {name: 'Kosten', data: [50, 60]}], format: 'euro', highlight: 'omzet',
  target: {value: 1000, label: 'Doel'}, height: 900});
assert.deepStrictEqual(chart.errors, []);
assert.deepStrictEqual(plain(chart.spec.series), [{name: 'Omzet', data: [100, 1200, null]}, {name: 'Kosten', data: [50, 60, null]}]);
assert.ok(chart.warnings.includes('Reeks "Kosten" heeft 2 waarden, verwacht 3.'));
assert.strictEqual(chart.spec.format, 'currency');
assert.strictEqual(chart.spec.highlight, 'Omzet', 'highlight matches a series name');
assert.deepStrictEqual(plain(chart.spec.target), {value: 1000, label: 'Doel'});
assert.strictEqual(chart.spec.height, 480);
const pie = build('chart', {type: 'doughnut', title: 'Mix', labels: 'abcdefghij'.split(''), series: [{name: 'x', data: [1, 2, 3, 4, 5, 6, 7, 8, 9, -10]}, {name: 'y', data: []}]});
assert.strictEqual(pie.spec.type, 'donut');
assert.strictEqual(pie.spec.labels.length, 8);
assert.strictEqual(pie.spec.labels[7], 'Overig');
assert.deepStrictEqual(plain(pie.spec.series[0].data), [1, 2, 3, 4, 5, 6, 7, 8 + 9 + 0], 'the rest is summed; negatives become 0');
assert.strictEqual(pie.spec.series.length, 1);
const shorthand = build('chart', {title: 'x', labels: ['a', 'b'], data: [1, 2], type: 'radar'});
assert.strictEqual(shorthand.spec.type, 'bar');
assert.ok(shorthand.warnings[0].startsWith('Onbekend grafiektype'));
assert.deepStrictEqual(plain(shorthand.spec.series), [{name: 'x', data: [1, 2]}]);
assert.deepStrictEqual(build('chart', {title: 'x', labels: [], series: [{data: [1]}]}).errors, ['De labels ontbreken.']);
assert.deepStrictEqual(build('chart', {title: 'x', labels: ['a'], series: [{data: ['n/a']}]}).errors, ['Er zijn geen reeksen (series) met getallen.']);
assert.ok(build('chart', {title: 'x', labels: ['a'], series: [{data: [1]}], highlight: 'zz'}).warnings.some(w => w.includes('"zz"')));
assert.deepStrictEqual(plain(K.kitTable('chart', chart.spec)), {header: ['Categorie', 'Omzet', 'Kosten'],
  rows: [['Jan', 100, 50], ['Feb', 1200, 60], ['Mrt', null, null]], types: ['text', 'currency', 'currency']});

// ── map ──────────────────────────────────────────────────────────────────────
const map = build('map', {title: 'Route', kind: 'route', photos: true, places: [
  {name: 'Rijksmuseum', lat: 4.8852, lng: 52.36, wiki: 'nl:Rijksmuseum', url: 'https://www.rijksmuseum.nl'},
  {name: 'Kantoor', address: 'Taurusavenue 1, Hoofddorp', time: '10:00', category: 'werk'},
  {name: 'Bad', lat: 999, lng: 4, wiki: 'xx:Nope', url: 'javascript:alert(1)'},
  {address: 'zonder naam'},
  {name: 'Lon', lat: '52.1', lon: '5.1'},
]});
assert.deepStrictEqual(map.errors, []);
const [rijks, kantoor, badPlace, lon] = map.spec.places;
assert.deepStrictEqual([rijks.lat, rijks.lng], [52.36, 4.8852], 'NL lat/lng swap is fixed');
assert.ok(map.warnings.includes('Bij "Rijksmuseum" stonden breedte- en lengtegraad omgedraaid; dat is hersteld.'));
assert.strictEqual(rijks.wiki, 'nl:Rijksmuseum');
assert.strictEqual(rijks.url, 'https://www.rijksmuseum.nl');
assert.deepStrictEqual([badPlace.lat, badPlace.wiki, badPlace.url], [null, '', ''], 'bad coordinates, wiki and links are dropped');
assert.ok(map.warnings.includes('Plaats 4 heeft geen naam en is weggelaten.'));
assert.deepStrictEqual([lon.lat, lon.lng], [52.1, 5.1], 'lon is read as lng');
assert.deepStrictEqual(plain(map.spec.places.map(p => [p.k, p.n])), [['0', 1], ['1', 2], ['2', 3], ['3', 4]]);
assert.deepStrictEqual(plain(map.spec.region), ['nl']);
assert.strictEqual(map.spec.kind, 'route');
assert.deepStrictEqual(plain(map.spec.categories), ['werk']);
assert.deepStrictEqual(plain(K.mapRequest(map.spec, 'nl')), {v: 1, lang: 'nl', region: ['nl'], photos: true, places: [
  {k: '0', name: 'Rijksmuseum', q: 'Rijksmuseum', lat: 52.36, lng: 4.8852, wiki: 'nl:Rijksmuseum'},
  {k: '1', name: 'Kantoor', q: 'Taurusavenue 1, Hoofddorp'},
  {k: '2', name: 'Bad', q: 'Bad'},
  {k: '3', name: 'Lon', q: 'Lon', lat: 52.1, lng: 5.1}]});
const local = K.mapLocalData(map.spec);
assert.deepStrictEqual(plain(local.places.map(p => p.status)), ['ok', 'not_found', 'not_found', 'ok']);
assert.strictEqual(local.tiles.url, 'https://tile.openstreetmap.org/{z}/{x}/{y}.png');
const oneStop = build('map', {title: 'x', kind: 'route', places: [{name: 'A'}]});
assert.strictEqual(oneStop.spec.kind, 'places', 'a route needs two places');
assert.deepStrictEqual(build('map', {title: 'x', places: [{note: 'no name'}]}).errors, ['Er zijn geen plaatsen (places).']);
assert.strictEqual(build('map', {title: 'x', places: Array.from({length: 30}, (_, i) => ({name: 'p' + i}))}).spec.places.length, 25);
assert.ok(build('map', {title: 'x', places: 'abcdefgh'.split('').map(c => ({name: c, category: c}))}).warnings.some(w => w.includes('categorieën')));
// Google Maps: one place is a search, more is directions with at most 9 waypoints.
assert.strictEqual(K.googleMapsUrl([{lat: 52, lng: 4}]), 'https://www.google.com/maps/search/?api=1&query=52.000000%2C4.000000');
const dir = K.googleMapsUrl(Array.from({length: 14}, (_, i) => ({lat: 52 + i / 100, lng: 4})));
assert.ok(dir.startsWith('https://www.google.com/maps/dir/?api=1&origin=52.000000%2C4.000000&destination=52.130000%2C4.000000'));
assert.strictEqual(decodeURIComponent(dir.split('waypoints=')[1].split('&')[0]).split('|').length, 9);
assert.strictEqual(K.googleMapsUrl([{lat: NaN, lng: 4}]), '');
// Tile templates the frame accepts.
assert.ok(K.tileUrlOk('https://tile.openstreetmap.org/{z}/{x}/{y}.png'));
assert.ok(K.tileUrlOk('https://tiles.example.nl/osm/{z}/{x}/{y}{r}.png'));
for (const url of ['http://tile.openstreetmap.org/{z}/{x}/{y}.png', 'https://evil/{z}/{x}.png', 'https://a.b/{z}/{x}/{y}.png?k={key}',
  'javascript:alert(1)//{z}{x}{y}', 'https://a.b/{z}/{x}/{y}.png" onerror="x']) {
  assert.ok(!K.tileUrlOk(url), url);
}

// ── Streaming title and fence seam ───────────────────────────────────────────
assert.strictEqual(K.streamingTitle('{"type":"bar","title":"Omzet \\"Q3\\"", "lab'), 'Omzet "Q3"');
assert.strictEqual(K.streamingTitle('{"title":"Half'), '');
assert.strictEqual(K.kitKind('Grafiek'), 'chart');
assert.strictEqual(K.kitKind('constructor'), '', 'no inherited keys');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'interactive_ui.js'), 'utf8');
const sandbox = {
  window: {addEventListener: () => {}, innerHeight: 900}, document: {addEventListener: () => {}, documentElement: {lang: 'nl', classList: {contains: () => false}}},
  navigator: {language: 'nl-NL'}, URL, console, setTimeout, clearTimeout, Map, Set, SWKit: K,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src + '\nthis.__accepts=interactiveUiFenceAccepts;', sandbox);
const accepts = sandbox.__accepts;
assert.strictEqual(accepts('table', '{"title":"x"}'), true);
assert.strictEqual(accepts('tabel', '  {"title":"x"}'), true);
assert.strictEqual(accepts('kaart', '{"title":"x"}'), true);
assert.strictEqual(accepts('chart', "new Chart(ctx, {type: 'bar'})"), false, 'a ```chart with code stays code');
assert.strictEqual(accepts('map', 'Amsterdam'), false);
assert.strictEqual(accepts('csv', 'a,b\n1,2'), true, 'csv is always a table');
assert.strictEqual(accepts('csv', '   '), false);
assert.strictEqual(accepts('json', '{"title":"x"}'), false);
assert.strictEqual(accepts('constructor', '{}'), false);
sandbox.SWKit = undefined;
assert.strictEqual(accepts('table', '{"title":"x"}'), false, 'without the kit helpers a data block stays code');

console.log('all kit checks passed');
