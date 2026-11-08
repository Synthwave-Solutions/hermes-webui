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

// ── kpi ──────────────────────────────────────────────────────────────────────
const kpi = build('kpi', {title: 'Kerncijfers oktober', lang: 'nl', source: 'Boekhouding', items: [
  {label: 'MRR', value: 18400, format: 'currency', delta: 12.5, target: 20000, note: 't.o.v. september'},
  {label: 'Churn', value: 2.1, format: 'percent', delta: 0.4, good: 'down'},
  {label: 'Klanten', value: '1.234', delta: -3},
  {label: 'Kosten', value: 9100, format: 'euro', delta: -800, deltaFormat: 'number', good: 'down', target: 10000},
  {label: 'Pijplijn', value: 1250000, format: 'currency', delta: 0}]});
assert.deepStrictEqual(kpi.errors, []);
assert.deepStrictEqual(kpi.warnings, []);
assert.strictEqual(kpi.title, 'Kerncijfers oktober');
assert.deepStrictEqual(plain(kpi.spec.items.map(i => [i.format, i.deltaFormat, i.good, i.tone])), [
  ['currency', 'percent', 'up', 'good'], ['percent', 'number', 'down', 'bad'], ['number', 'percent', 'up', 'bad'],
  ['currency', 'number', 'down', 'good'], ['currency', 'percent', 'up', 'flat']], 'a percentage moves in points; down is good for costs');
assert.strictEqual(kpi.spec.items[2].value, 1234, 'a Dutch number written as text is read');
assert.strictEqual(kpi.spec.items[0].progress, 0.92);
assert.strictEqual(kpi.spec.items[0].met, false);
assert.strictEqual(kpi.spec.items[3].met, true, 'under budget meets a target when down is good');
assert.deepStrictEqual(kpi.spec.items.map(i => K.kpiValueText(i, 'nl')), ['€ 18.400', '2,1%', '1.234', '€ 9.100', '€ 1,3 mln.']);
assert.deepStrictEqual(kpi.spec.items.map(i => K.kpiDeltaText(i, 'nl')), ['+12,5%', '+0,4 pp', '-3%', '€ -800', '0%']);
assert.deepStrictEqual(kpi.spec.items.slice(0, 2).map(i => K.kpiDeltaText(i, 'en')), ['+12.5%', '+0.4 pp']);
assert.ok(kpi.estHeight > 100 && kpi.estHeight < 400, kpi.estHeight);
assert.deepStrictEqual(plain(K.kitTable('kpi', kpi.spec)).header, ['Label', 'Waarde', 'Verandering', 'Doel']);
assert.strictEqual(K.toCsv(K.kitTable('kpi', kpi.spec), {delimiter: ';', decimalComma: true}),
  '﻿Label;Waarde;Verandering;Doel\r\nMRR;18400;12,5;20000\r\nChurn;2,1;0,4;\r\nKlanten;1234;-3;\r\nKosten;9100;-800;10000\r\nPijplijn;1250000;0;\r\n');
assert.deepStrictEqual(plain(K.kitTable('kpi', build('kpi', {title: 'x', lang: 'en', items: [{label: 'a', value: 1}]}).spec)).header, ['Label', 'Value', 'Change', 'Target']);
// Fixable: bad fields are dropped with a warning that names the figure.
const kpiFix = build('kpi', {items: [
  {label: 'Omzet', value: '€ 1.200', format: 'money', delta: 'veel', good: 'sideways', target: -5, deltaFormat: 'ratio', note: 'n'.repeat(100)},
  {label: 'Leeg', value: 'n.v.t.'}, {value: 3}, 'los', ...Array.from({length: 8}, (_, i) => ({label: 'k' + i, value: i}))]});
assert.deepStrictEqual(kpiFix.errors, []);
for (const w of ['De titel ontbreekt.', '"Omzet" heeft een onbekend format "money"; gebruik number, currency of percent.',
  'De verandering (delta) van "Omzet" is geen getal en is weggelaten.', '"Omzet" heeft good "sideways"; gebruik up of down. Nu geldt up.',
  'Het doel (target) van "Omzet" is geen getal boven 0 en is weggelaten.', '"Omzet" heeft een onbekend deltaFormat "ratio"; gebruik percent of number.',
  'De notitie van "Omzet" is ingekort tot 80 tekens.', '"Leeg" heeft geen getal als waarde (value) en is weggelaten.',
  'Cijfer 3 heeft geen label en is weggelaten.', 'Cijfer 4 is geen object met label en value en is weggelaten.',
  'Er zijn 12 cijfers; alleen de eerste 8 worden getoond.']) {
  assert.ok(kpiFix.warnings.includes(w), w + ' in ' + JSON.stringify(kpiFix.warnings));
}
assert.strictEqual(kpiFix.spec.title, 'Kerncijfers');
const omzet = kpiFix.spec.items[0];
assert.deepStrictEqual([omzet.value, omzet.format, omzet.delta, omzet.good, omzet.target], [1200, 'currency', null, 'up', null], 'the euro sign sets the format');
assert.ok(omzet.note.length <= 80);
assert.strictEqual(kpiFix.spec.items.length, 5);
// Fatal: nothing to show.
assert.deepStrictEqual(build('kpi', {title: 'x', items: []}).errors, ['Er zijn geen cijfers (items).']);
assert.deepStrictEqual(build('kpi', {title: 'x', items: [{label: 'a', value: 'veel'}]}).errors, ['Geen enkel cijfer heeft een label en een getal als waarde (value).']);
assert.deepStrictEqual(build('kpi', {title: 'x', lang: 'en', items: 'MRR 18k'}).errors, ['There are no figures (items).']);

// ── timeline ─────────────────────────────────────────────────────────────────
const plan = build('timeline', {title: 'Uitrol', lang: 'nl', unit: 'week', start: '2026-11-09', today: 3, source: 'Projectplan', items: [
  {label: 'Kick-off', start: 1, milestone: true, owner: 'Michaël'},
  {label: 'Bouw', start: 2, end: 5, status: 'doing', owner: 'Senna', note: 'Twee sprints'},
  {label: 'Acceptatietest', start: 6, end: 7, status: 'risk'},
  {label: 'Ontwerp', start: 1, end: 2, status: 'klaar'},
  {label: 'Training', start: 7, end: 7, status: 'todo'},
  {label: 'Live', start: 8, milestone: true}]});
assert.deepStrictEqual(plan.errors, []);
assert.deepStrictEqual(plan.warnings, []);
assert.strictEqual(plan.spec.mode, 'date');
assert.deepStrictEqual(plain(plan.spec.items.map(i => [i.from, i.to, i.status, i.milestone])), [
  ['2026-11-09', '2026-11-09', '', true], ['2026-11-16', '2026-12-13', 'doing', false], ['2026-12-14', '2026-12-27', 'risk', false],
  ['2026-11-09', '2026-11-22', 'done', false], ['2026-12-21', '2026-12-27', 'todo', false], ['2026-12-28', '2026-12-28', '', true]],
  'week 1 starts on "start" and end is included; Dutch status words are read');
assert.deepStrictEqual(plan.spec.items.map(i => K.timelinePeriod(plan.spec, i, 'nl')),
  ['9 nov 2026', '16 nov t/m 13 dec 2026', '14 dec t/m 27 dec 2026', '9 nov t/m 22 nov 2026', '21 dec t/m 27 dec 2026', '28 dec 2026']);
assert.strictEqual(K.timelinePeriod(plan.spec, plan.spec.items[1], 'en'), '16 Nov to 13 Dec 2026');
const axis = K.timelineAxis(plan.spec, 'nl', K.dayOf('2030-01-01'));
assert.strictEqual(K.isoOf(axis.min), '2026-11-09');
assert.strictEqual(K.isoOf(axis.max), '2027-01-04');
assert.deepStrictEqual(axis.ticks.map(t => t.label), ['9 nov', '16 nov', '23 nov', '30 nov', '7 dec', '14 dec', '21 dec', '28 dec']);
assert.deepStrictEqual(axis.ticks.map(t => t.minor), [false, true, false, true, false, true, false, true], 'every other label can hide on a narrow frame');
assert.strictEqual(axis.todayX, 0.3125, 'today: 3 is the middle of week 3');
assert.ok(plan.estHeight > 200 && plan.estHeight < 520, plan.estHeight);
assert.deepStrictEqual(plain(K.kitTable('timeline', plan.spec).rows[1]), ['Bouw', '2026-11-16', '2026-12-13', 'Senna', 'Bezig', '', 'Twee sprints']);
assert.deepStrictEqual(plain(K.kitTable('timeline', plan.spec).header), ['Onderdeel', 'Start', 'Einde', 'Eigenaar', 'Status', 'Mijlpaal', 'Notitie']);
assert.ok(K.toCsv(K.kitTable('timeline', plan.spec)).includes('Kick-off;2026-11-09;2026-11-09;Michaël;;ja;\r\n'));
// Unit numbers without a start date: an index axis; without "today" no line.
const idx = build('timeline', {title: 'Sprints', lang: 'en', unit: 'weeks', items: [{label: 'A', start: 1, end: 3, status: 'done'}, {label: 'B', start: 4, end: 6}]});
assert.deepStrictEqual(idx.warnings, []);
assert.deepStrictEqual([idx.spec.mode, idx.spec.unit, idx.spec.todayAuto], ['index', 'week', false]);
const idxAxis = K.timelineAxis(idx.spec, 'en', K.dayOf('2026-11-08'));
assert.deepStrictEqual(idxAxis.ticks.map(t => t.label), ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']);
assert.strictEqual(idxAxis.todayX, null);
assert.strictEqual(K.timelinePeriod(idx.spec, idx.spec.items[0], 'en'), 'Weeks 1 to 3');
assert.strictEqual(K.timelinePeriod(idx.spec, idx.spec.items[0], 'nl'), 'Week 1 t/m 3');
assert.deepStrictEqual(plain(K.kitTable('timeline', idx.spec).rows[0]), ['A', 1, 3, '', 'Done', '', '']);
// Dates by month; a plan with dates and no "today" uses the browser's date.
const months = build('timeline', {title: 'Roadmap', unit: 'month', items: [{label: 'Fase 1', start: '2026-11-03', end: '2027-02-10'}, {label: 'Fase 2', start: '2027-03', end: '2027-04'}]});
assert.deepStrictEqual(plain(months.spec.items.map(i => [i.from, i.to])), [['2026-11-03', '2027-02-10'], ['2027-03-01', '2027-04-30']], 'a YYYY-MM end is the end of that month');
assert.strictEqual(months.spec.todayAuto, true);
const mAxis = K.timelineAxis(months.spec, 'nl', K.dayOf('2026-12-01') + 0.5);
assert.deepStrictEqual(mAxis.ticks.map(t => t.label), ['nov 2026', 'dec', 'jan 2027', 'feb', 'mrt', 'apr']);
assert.ok(mAxis.todayX > 0.16 && mAxis.todayX < 0.17, mAxis.todayX);
assert.strictEqual(K.timelineAxis(months.spec, 'nl', K.dayOf('2031-01-01')).todayX, null, 'today outside the range draws no line');
// Fixable: swapped ends, a missing end, unknown status and unit, numbers without a start date.
const tlFix = build('timeline', {unit: 'fortnight', today: 'gisteren', items: [
  {label: 'Terug', start: '2026-12-10', end: '2026-12-01', status: 'paars'}, {label: 'Los', start: 3},
  {title: 'Alias', date: '2026-12-05'}, {start: 1, end: 2}, {label: 'Kapot', start: 'morgen'}, 7,
  {label: 'L'.repeat(80), start: '2026-12-02', end: '2026-12-03', owner: 'O'.repeat(50)}]});
assert.deepStrictEqual(tlFix.errors, []);
for (const w of ['De titel ontbreekt.', 'Onbekende unit "fortnight"; gebruik day, week of month. Nu geldt week.',
  'Bij "Terug" lag end voor start; die zijn omgedraaid.', '"Terug" heeft een onbekende status "paars"; gebruik todo, doing, done of risk.',
  '"Los" heeft geen geldige end en is als mijlpaal getoond.', 'Onderdeel 4 heeft geen label en is weggelaten.',
  '"Kapot" heeft geen geldige start (een getal of JJJJ-MM-DD) en is weggelaten.', 'Onderdeel 6 is geen object met label en start en is weggelaten.',
  'today is geen getal of datum (JJJJ-MM-DD); de lijn voor vandaag is weggelaten.',
  'Getallen bij start en end tellen vanaf de start van de planning; die ontbrak, dus is 2026-12-01 gebruikt.',
  'Het label van onderdeel 7 is ingekort tot 60 tekens.']) {
  assert.ok(tlFix.warnings.includes(w), w + ' in ' + JSON.stringify(tlFix.warnings));
}
assert.strictEqual(tlFix.spec.title, 'Planning');
assert.deepStrictEqual(plain(tlFix.spec.items.map(i => [i.label.slice(0, 6), i.from, i.to, i.status, i.milestone])), [
  ['Terug', '2026-12-01', '2026-12-10', 'todo', false], ['Los', '2026-12-15', '2026-12-15', '', true], ['Alias', '2026-12-05', '2026-12-05', '', true],
  ['LLLLLL', '2026-12-02', '2026-12-03', '', false]]);
assert.strictEqual(tlFix.spec.today, null);
assert.strictEqual(tlFix.spec.todayAuto, false, 'an unreadable today is left out, not replaced by the browser date');
assert.ok(tlFix.spec.items[3].owner.length <= 40);
assert.ok(build('timeline', {title: 't', items: [{label: 'a', start: 1, end: 2}], today: '2026-11-08'}).warnings.includes(
  'today is een datum, maar de onderdelen gebruiken getallen zonder start; de lijn voor vandaag is weggelaten.'));
assert.strictEqual(build('timeline', {title: 't', items: Array.from({length: 25}, (_, i) => ({label: 'x' + i, start: i, end: i + 1}))}).spec.items.length, 20);
assert.strictEqual(build('timeline', {title: 't', items: [{label: 'a', start: 0, end: 1}]}).spec.first, 0, 'a block that uses 0 counts from 0');
assert.ok(build('timeline', {title: 't', start: '2026-13-01', items: [{label: 'a', start: 1, end: 2}]}).warnings.includes('De start van de planning is geen datum (JJJJ-MM-DD) en is genegeerd.'));
// Fatal.
assert.deepStrictEqual(build('timeline', {title: 'x', items: []}).errors, ['Er zijn geen onderdelen (items).']);
assert.deepStrictEqual(build('timeline', {title: 'x', items: [{label: 'a', start: '30-02-2026'}, {label: 'b', start: -1}]}).errors,
  ['Geen enkel onderdeel heeft een label en een geldige start (een getal of JJJJ-MM-DD).']);
assert.deepStrictEqual(build('timeline', {title: 'x', lang: 'en', items: [{label: 'a'}]}).errors, ['No item has a label and a valid start (a number or YYYY-MM-DD).']);
assert.ok(Number.isNaN(K.dayOf('2026-02-30')), 'impossible dates are not dates');

// ── Streaming title and fence seam ───────────────────────────────────────────
assert.strictEqual(K.streamingTitle('{"type":"bar","title":"Omzet \\"Q3\\"", "lab'), 'Omzet "Q3"');
assert.strictEqual(K.streamingTitle('{"title":"Half'), '');
assert.strictEqual(K.kitKind('Grafiek'), 'chart');
assert.strictEqual(K.kitKind('constructor'), '', 'no inherited keys');
for (const [lang, kind] of [['kpi', 'kpi'], ['KPIs', 'kpi'], ['kpi-row', 'kpi'], ['timeline', 'timeline'], ['tijdlijn', 'timeline'], ['Planning', 'timeline']]) {
  assert.strictEqual(K.kitKind(lang), kind, lang);
}

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
assert.strictEqual(accepts('kpi-row', '{"items":[]}'), true);
assert.strictEqual(accepts('tijdlijn', '{"items":[]}'), true);
assert.strictEqual(accepts('planning', '- Week 1: kick-off\n- Week 2: bouw'), false, 'a plain text plan stays text');
sandbox.SWKit = undefined;
assert.strictEqual(accepts('table', '{"title":"x"}'), false, 'without the kit helpers a data block stays code');

console.log('all kit checks passed');
