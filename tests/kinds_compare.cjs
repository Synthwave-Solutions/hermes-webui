// Checks for the "compare" data block (static/interactive-ui/kinds/compare.js).
// Run: node tests/kinds_compare.cjs
'use strict';
const path = require('path');
const assert = require('assert');

const K = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kit-core.js'));
global.SWKit = K;
require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', 'compare.js'));
const plain = v => JSON.parse(JSON.stringify(v));
const build = (value, opts) => K.build('compare', typeof value === 'string' ? value : JSON.stringify(value), Object.assign({lang: 'nl', fence: 'compare'}, opts));

// ── Registration and fences ──────────────────────────────────────────────────
assert.ok(K.extra('compare'), 'the kind registers');
['compare', 'vergelijk', 'vergelijking', 'options', 'opties', 'comparison'].forEach(f => assert.strictEqual(K.kitKind(f), 'compare', f));
assert.strictEqual(K.NAME.nl.compare, 'Vergelijking');
assert.strictEqual(K.NOUN.en.compare, 'comparison');
assert.strictEqual(K.kitKind('table'), 'table', 'built-in fences stay');

// ── Valid ────────────────────────────────────────────────────────────────────
const good = {
  title: 'Boekhoudpakket', lang: 'nl', recommended: 'Moneybird', criteria: ['prijs', 'support'],
  options: [
    {name: 'Exact Online', price: 69, priceUnit: 'per maand', score: 7.5, pros: ['Veel koppelingen'], cons: ['Duurder'],
      facts: {Levertijd: 'Direct', Support: 'Telefoon'}},
    {name: 'Moneybird', price: 32.5, priceUnit: 'maand', score: 8.5, pros: ['Snel te leren', 'Goede app'], cons: [],
      facts: {Levertijd: 'Direct', Support: 'Chat'}, tag: 'Aanrader'},
    {name: 'SnelStart', price: '€ 45 per maand', score: '7/10', pros: ['Loonadministratie erbij'], cons: ['Oudere uitstraling'],
      facts: {support: 'Telefoon', Proefperiode: '30 dagen'}, tag: 'Goedkoopst'}
  ]
};
let r = build(good);
assert.deepStrictEqual(r.errors, []);
assert.deepStrictEqual(r.warnings, []);
const s = r.spec;
assert.strictEqual(s.title, 'Boekhoudpakket');
assert.strictEqual(s.options.length, 3);
assert.strictEqual(s.recommended, 1);
assert.strictEqual(s.scoreMax, 10);
assert.ok(s.hasPrice && s.hasScore);
assert.deepStrictEqual(s.factKeys, ['Levertijd', 'Support', 'Proefperiode'], 'fact keys merge case-insensitively, in order of first use');
assert.strictEqual(s.options[2].facts.Support, 'Telefoon', 'a fact written in other case lands on the shared key');
assert.strictEqual(s.options[1].priceUnit, 'per maand', '"maand" reads as "per maand"');
assert.strictEqual(s.options[2].price, 45, 'a price in text is read');
assert.strictEqual(s.options[2].priceUnit, 'per maand', 'the unit is split off the price text');
assert.strictEqual(s.options[2].score, 7, '"7/10" is read');
assert.strictEqual(s.options[1].tag, '', 'a tag that only says recommended is dropped');
assert.strictEqual(s.options[2].tag, 'Goedkoopst');
assert.deepStrictEqual(s.criteria, ['prijs', 'support']);
assert.ok(r.estHeight > 200 && r.estHeight < 900, 'a sensible height: ' + r.estHeight);
assert.strictEqual(build(good, {fence: 'vergelijk'}).spec.options.length, 3);

// Recommended by a flag on the option, or by a tag, when the block names none.
r = build({title: 'x', options: [{name: 'A'}, {name: 'B', recommended: true}]});
assert.strictEqual(r.spec.recommended, 1);
r = build({title: 'x', options: [{name: 'A', tag: 'Beste keuze'}, {name: 'B'}]});
assert.strictEqual(r.spec.recommended, 0);
r = build({title: 'x', options: [{name: 'A'}, {name: 'B'}]});
assert.strictEqual(r.spec.recommended, -1, 'no label when nothing is recommended');
assert.ok(!r.spec.hasPrice && !r.spec.hasScore);

// Scores out of 100 and percentages.
r = build({title: 'x', options: [{name: 'A', score: 85}, {name: 'B', score: '72%'}]});
assert.strictEqual(r.spec.scoreMax, 100);
assert.deepStrictEqual(r.spec.options.map(o => o.score), [85, 72]);
r = build({title: 'x', options: [{name: 'A', score: '8/10'}, {name: 'B', score: '90%'}]});
assert.strictEqual(r.spec.scoreMax, 100);
assert.strictEqual(r.spec.options[0].score, 80, 'a score with its own scale moves to the shared one');
r = build({title: 'x', scoreMax: 5, options: [{name: 'A', score: 4.5}, {name: 'B', score: 3}]});
assert.strictEqual(r.spec.scoreMax, 5);

// Free, text prices and booleans.
r = build({title: 'x', lang: 'en', options: [{name: 'A', price: 0, facts: {SSO: true}}, {name: 'B', price: 'on request', facts: {SSO: false}}]});
assert.strictEqual(r.spec.options[0].price, 0);
assert.strictEqual(r.spec.options[1].priceText, 'On request');
assert.deepStrictEqual(r.spec.options.map(o => o.facts.SSO), ['Yes', 'No']);
assert.strictEqual(r.spec.lang, 'en');

// ── Fixable: warnings, still drawn ───────────────────────────────────────────
const messy = `{
  // comments and trailing commas are fine
  "title": "Laptops",
  "recommended": "Bechtle",
  "scoreMax": 7,
  "criteria": "prijs, levertijd; garantie",
  "opties": [
    "Dell Direct",
    {"naam": "Bechtle", "prijs": "€ 1.249,-", "score": "85%", "voordelen": "Snelle levering", "nadelen": [null, 12, "Alleen zakelijk"],
     "facts": {"Levertijd": "1 week", "Garantie": true, "Aantal": 25}},
    {"name": "Bechtle", "price": -5, "tag": "aanrader"},
    {"price": 300},
    42,
    {"name": "Centralpoint", "price": "op aanvraag", "priceUnit": "/stuk", "facts": [{"label": "Levertijd", "value": "2 weken"}, {"label": "Garantie", "value": {"a": 1}}],
     "pros": ["a", "b", "c", "d", "e", "f", "g", "h"]},
    {"name": "Coolblue Zakelijk", "price": 1199},
  ],
}`;
r = build(messy);
assert.deepStrictEqual(r.errors, []);
const w = r.warnings.join('\n');
['Optie 4 heeft geen naam', 'Optie 5 is geen object', 'Er zijn 5 opties; alleen 4', 'komt vaker voor',
  'scoreMax "7"', 'De minpunten van "Bechtle"', 'De prijs van "Bechtle (2)"', 'alleen de eerste 6', 'Het feit "Garantie" bij "Centralpoint"']
  .forEach(part => assert.ok(w.includes(part), 'warning about: ' + part + '\n' + w));
assert.ok(!w.includes('meer dan één aanrader'), 'two options with the same name are not two recommendations');
const ms = r.spec;
assert.deepStrictEqual(ms.options.map(o => o.name), ['Dell Direct', 'Bechtle', 'Bechtle (2)', 'Centralpoint']);
assert.strictEqual(ms.recommended, 1);
assert.strictEqual(ms.options[1].price, 1249, 'Dutch price with ",-"');
assert.strictEqual(ms.options[1].score, 85);
assert.deepStrictEqual(ms.options[1].pros, ['Snelle levering'], 'one string becomes a list');
assert.deepStrictEqual(ms.options[1].cons, ['Alleen zakelijk'], 'only text stays in a list');
assert.strictEqual(ms.options[1].facts.Garantie, 'Ja');
assert.strictEqual(ms.options[1].facts.Aantal, 25);
assert.strictEqual(ms.options[2].price, null);
assert.strictEqual(ms.options[2].tag, '', 'a second "aanrader" tag never competes with the label');
assert.strictEqual(ms.options[3].priceText, 'Op aanvraag');
assert.strictEqual(ms.options[3].priceUnit, 'per stuk');
assert.strictEqual(ms.options[3].pros.length, 6);
assert.deepStrictEqual(ms.criteria, ['prijs', 'levertijd', 'garantie']);
assert.strictEqual(ms.options[0].facts.Levertijd, undefined, 'a missing fact stays missing');

// More than four options: the recommended one is kept.
r = build({title: 'x', recommended: 'F', options: ['A', 'B', 'C', 'D', 'E', 'F'].map(n => ({name: n}))});
assert.deepStrictEqual(r.spec.options.map(o => o.name), ['A', 'B', 'C', 'F']);
assert.strictEqual(r.spec.recommended, 3);
r = build({title: 'x', recommended: 'Z', options: [{name: 'A'}, {name: 'B'}]});
assert.strictEqual(r.spec.recommended, -1);
assert.ok(r.warnings.some(x => x.includes('"Z" is geen van de opties')));
r = build({options: [{name: 'A'}, {name: 'B'}]});
assert.strictEqual(r.spec.title, 'Vergelijking', 'a missing title falls back to the name');
assert.ok(r.warnings.some(x => x.includes('titel ontbreekt')));

// ── Fatal: one plain sentence ───────────────────────────────────────────────
r = build({title: 'x', options: [{name: 'Alleen deze'}, {price: 4}]});
assert.strictEqual(r.spec, null);
assert.deepStrictEqual(r.errors, ['Een vergelijking heeft minstens twee opties met een naam; er is er 1.']);
r = build({title: 'x', options: 'geen'});
assert.deepStrictEqual(r.errors, ['Er zijn geen opties (options) om te vergelijken.']);
r = build({title: 'x', lang: 'en', options: []});
assert.deepStrictEqual(r.errors, ['There are no options to compare.']);
r = build('{"title": "x", "options": [');
assert.strictEqual(r.errors.length, 1);
assert.ok(/geen geldige JSON/.test(r.errors[0]));

// ── Export ──────────────────────────────────────────────────────────────────
const t = K.kitTable('compare', build(good).spec);
assert.deepStrictEqual(t.header, ['Optie', 'Aanrader', 'Prijs (€)', 'Eenheid', 'Score (van 10)', 'Pluspunten', 'Minpunten', 'Levertijd', 'Support', 'Proefperiode']);
assert.deepStrictEqual(plain(t.rows[1]), ['Moneybird', 'Ja', 32.5, 'per maand', 8.5, 'Snel te leren; Goede app', '', 'Direct', 'Chat', null]);
assert.deepStrictEqual(plain(t.rows[2]).slice(0, 5), ['SnelStart', null, 45, 'per maand', 7]);
assert.strictEqual(t.types[2], 'currency');
assert.strictEqual(t.types.length, t.header.length);
const csv = K.toCsv(t);
assert.ok(csv.startsWith('\ufeffOptie;Aanrader;Prijs (€);Eenheid;Score (van 10);Pluspunten;Minpunten;Levertijd;Support;Proefperiode\r\n'), csv.split('\n')[0]);
assert.ok(csv.includes('Moneybird;Ja;32,5;per maand;8,5;"Snel te leren; Goede app"'), 'decimal comma and quoting');
const te = K.kitTable('compare', build(Object.assign({}, good, {lang: 'en'})).spec);
assert.deepStrictEqual(te.header.slice(0, 7), ['Option', 'Recommended', 'Price (€)', 'Unit', 'Score (of 10)', 'Pros', 'Cons']);
assert.strictEqual(K.kitTable('compare', ms).rows[3][2], 'Op aanvraag', 'a text price is exported as text');
// Without a recommendation, units or scores the extra columns stay out.
const bare = K.kitTable('compare', build({title: 'x', options: [{name: 'A', price: 4}, {name: 'B'}]}).spec);
assert.deepStrictEqual(bare.header, ['Optie', 'Prijs (€)', 'Score', 'Pluspunten', 'Minpunten']);

// ── Limits ──────────────────────────────────────────────────────────────────
const long = 'x'.repeat(400);
r = build({title: long, options: [0, 1, 2].map(i => ({name: long + i, tag: long, priceUnit: long, price: 1,
  pros: Array(20).fill(long), cons: Array(20).fill(long), facts: Object.fromEntries(Array.from({length: 20}, (_, k) => ['k' + k + long, long]))}))});
assert.deepStrictEqual(r.errors, []);
assert.ok(r.spec.title.length <= 120);
r.spec.options.forEach(o => {
  assert.ok(o.name.length <= 50, 'name');
  assert.ok(o.tag.length <= 32, 'tag');
  assert.ok(o.priceUnit.length <= 24, 'unit');
  assert.strictEqual(o.pros.length, 6);
  assert.strictEqual(o.cons.length, 6);
  o.pros.concat(o.cons).forEach(p => assert.ok(p.length <= 140));
  Object.keys(o.facts).forEach(k => { assert.ok(k.length <= 32); assert.ok(String(o.facts[k]).length <= 80); });
});
assert.strictEqual(r.spec.factKeys.length, 8);
assert.ok(r.warnings.some(x => x.includes('meer dan 8 soorten feiten')));
r = build({title: 'x', criteria: Array.from({length: 20}, (_, i) => 'punt ' + i), options: [{name: 'A'}, {name: 'B'}]});
assert.strictEqual(r.spec.criteria.length, 6);
assert.ok(r.warnings.some(x => x.includes('meer dan 6 criteria')));
// Nothing in the cleaned spec carries markup or functions: it is a plain clone.
assert.deepStrictEqual(plain(build(good).spec), build(good).spec);

// ── Review round: scales, currencies, units, recommended, odd keys ─────────
const two = (a, b, extra) => build(Object.assign({title: 'x', options: [Object.assign({name: 'A'}, a), Object.assign({name: 'B'}, b)]}, extra || {}));
const scores = r => r.spec.options.map(o => o.score);

// Every score has its own scale before they share one.
r = two({score: 8.5}, {score: '72%'});
assert.strictEqual(r.spec.scoreMax, 100);
assert.deepStrictEqual(scores(r), [85, 72], 'a plain 8,5 is out of 10, next to a percentage');
r = two({score: '8,5'}, {score: '72%'});
assert.deepStrictEqual(scores(r), [85, 72]);
r = two({score: 8}, {score: '4/5'});
assert.strictEqual(r.spec.scoreMax, 10);
assert.deepStrictEqual(scores(r), [8, 8], 'a plain 8 is never dropped next to "4/5"');
assert.deepStrictEqual(r.warnings, []);
r = two({score: '8/10'}, {score: 85});
assert.strictEqual(r.spec.scoreMax, 100);
assert.deepStrictEqual(scores(r), [80, 85]);
r = two({score: '4 van 5'}, {score: '3/5'});
assert.strictEqual(r.spec.scoreMax, 5);
assert.deepStrictEqual(scores(r), [4, 3]);
r = two({score: 7}, {score: '7/10'});
assert.deepStrictEqual(scores(r), [7, 7]);
assert.strictEqual(r.spec.scoreMax, 10);
r = two({score: '12/10'}, {score: 6});
assert.deepStrictEqual(scores(r), [null, 6]);
assert.ok(r.warnings.some(x => x.includes('De score van "A"')));
r = two({score: 8}, {score: 4}, {scoreMax: 5});
assert.deepStrictEqual(scores(r), [null, 4], 'the block scale wins over the guess');
r = two({score: 140}, {score: 50});
assert.deepStrictEqual(scores(r), [null, 50]);

// Prices in another currency are never shown as euros.
r = two({price: '$ 54,000', priceUnit: 'per jaar'}, {price: '£ 20'});
assert.strictEqual(r.spec.options[0].price, null, '"$ 54,000" is not 54 euro');
assert.strictEqual(r.spec.options[0].priceText, '$ 54,000');
assert.strictEqual(r.spec.options[0].priceUnit, 'per jaar');
assert.strictEqual(r.spec.options[1].priceText, '£ 20');
assert.ok(r.warnings.some(x => x.includes('De prijs van "A" staat niet in euro')));
r = two({price: '$ 99 per month'}, {price: '99 USD'});
assert.strictEqual(r.spec.options[0].priceText, '$ 99 per month');
assert.strictEqual(r.spec.options[1].priceText, '99 USD');
r = two({price: 54000, currency: 'USD'}, {price: 12, currency: 'EUR'});
assert.ok(/54\.000/.test(r.spec.options[0].priceText) && /US\$|USD/.test(r.spec.options[0].priceText), r.spec.options[0].priceText);
assert.strictEqual(r.spec.options[0].price, null);
assert.strictEqual(r.spec.options[1].price, 12);
r = two({price: '54,000'}, {price: 3}, {currency: 'usd', lang: 'en'});
assert.strictEqual(r.spec.options[0].priceText, 'USD 54,000');
assert.ok(/^US\$|^\$|USD/.test(r.spec.options[1].priceText));
assert.ok(r.warnings.some(x => x.includes('The price of "A" is not in euros')));
assert.strictEqual(K.kitTable('compare', r.spec).rows[0][1], 'USD 54,000', 'the export keeps the text, never 54 as a euro amount');
r = two({price: '45 euro'}, {price: '€ 45 p/m'});
assert.deepStrictEqual(r.spec.options.map(o => o.price), [45, 45]);
assert.strictEqual(r.spec.options[1].priceUnit, 'per maand', '"p/m" is per maand');

// Units: only a bare noun gets "per".
const unit = u => two({price: 10, priceUnit: u}, {price: 5}).spec.options[0].priceUnit;
assert.strictEqual(unit('maand'), 'per maand');
assert.strictEqual(unit('/stuk'), 'per stuk');
assert.strictEqual(unit('gebruiker per maand'), 'per gebruiker per maand');
assert.strictEqual(unit('user'), 'per user');
assert.strictEqual(unit('per jaar'), 'per jaar');
assert.strictEqual(unit('p.m.'), 'per maand');
['maandelijks', 'jaarlijks', 'exclusief btw', 'inclusief btw', 'excl. btw', 'eenmalig', 'totaal', 'monthly', 'yearly', 'vanaf']
  .forEach(u => assert.strictEqual(unit(u), u, u + ' stays as written'));
assert.strictEqual(two({price: '€ 45 maandelijks'}, {price: 1}).spec.options[0].priceUnit, 'maandelijks');
assert.strictEqual(two({price: '€ 45 /mnd'}, {price: 1}).spec.options[0].priceUnit, 'per mnd');
r = two({price: '€ 45 per ' + 'zeer lange omschrijving van de eenheid'}, {price: 1});
assert.ok(r.spec.options[0].priceUnit.length <= 24);
assert.ok(r.warnings.some(x => x.includes('De eenheid van de prijs van "A" is ingekort')), 'a unit split off a price warns when cut');

// Recommended by position, 0, out of range, true, and long names.
const rec = (v, list) => build({title: 'x', recommended: v, options: list || [{name: 'A'}, {name: 'B'}, {name: 'C'}]});
assert.strictEqual(rec(2).spec.recommended, 1);
assert.strictEqual(rec('3').spec.recommended, 2, 'a number as text is a position');
assert.strictEqual(rec(0).spec.recommended, 0, '0 is read as the first option');
assert.strictEqual(rec(0).warnings.length, 0);
r = rec(9);
assert.strictEqual(r.spec.recommended, -1);
assert.ok(r.warnings.some(x => x.includes('(recommended: 9) wijst geen van de opties aan')), r.warnings.join('\n'));
r = rec(true);
assert.strictEqual(r.spec.recommended, -1);
assert.ok(r.warnings.some(x => x.includes('(recommended: true)')));
r = rec(true, [{name: 'A'}, {name: 'B', recommended: true}]);
assert.strictEqual(r.spec.recommended, 1, 'a flag on the option still counts');
assert.deepStrictEqual(r.warnings, []);
r = rec(1, [{price: 3}, {name: 'A'}, {name: 'B'}]);
assert.strictEqual(r.spec.recommended, -1, 'position 1 is the dropped entry, not "A"');
assert.ok(r.warnings.some(x => x.includes('(recommended: 1)')));
assert.strictEqual(rec(2, [{price: 3}, {name: 'A'}, {name: 'B'}]).spec.recommended, 0);
r = rec('2', [{name: '1'}, {name: '2'}]);
assert.strictEqual(r.spec.recommended, 1, 'a name that is a number is a name first');
const longName = 'Microsoft 365 Business Premium met Defender for Business en Intune Suite';
assert.ok(longName.length > 50);
r = rec(longName, [{name: 'Google Workspace'}, {name: longName}]);
assert.strictEqual(r.spec.recommended, 1, 'a cut name still matches its full recommended name');
assert.ok(!r.warnings.some(x => x.includes('geen van de opties')), r.warnings.join('\n'));
r = rec('Bechtle', [{name: 'Bechtle'}, {name: 'Bechtle'}, {name: 'Dell'}]);
assert.strictEqual(r.spec.recommended, 0);
assert.ok(!r.warnings.some(x => x.includes('meer dan één aanrader')));
r = rec(undefined, [{name: 'A', recommended: true}, {name: 'B', aanrader: true}]);
assert.ok(r.warnings.some(x => x.includes('meer dan één aanrader')), 'two different flagged options do warn');

// Names and labels that look like object internals stay plain text.
r = build({title: 'x', options: [{name: 'constructor', facts: {Constructor: 'ja', toString: 'nee'}}, {name: 'toString', facts: {__proto__: 'x'}}, {name: 'hasOwnProperty'}]});
assert.deepStrictEqual(r.spec.options.map(o => o.name), ['constructor', 'toString', 'hasOwnProperty']);
assert.ok(!r.warnings.some(x => x.includes('komt vaker voor')), r.warnings.join('\n'));
assert.deepStrictEqual(r.spec.factKeys, ['Constructor', 'toString']);
assert.strictEqual(r.spec.options[0].facts.Constructor, 'ja');
r = build('{"title":"x","options":[{"name":"A","facts":{"__proto__":"waarde","Prijs":"1"}},{"name":"B"}]}');
assert.deepStrictEqual(r.spec.factKeys, ['__proto__', 'Prijs']);
assert.ok(Object.prototype.hasOwnProperty.call(r.spec.options[0].facts, '__proto__'));
assert.deepStrictEqual(plain(K.kitTable('compare', r.spec).rows[1]).slice(-2), [null, null], 'a missing fact is empty, never an inherited value');
r = build({title: 'x', options: [{name: 'A', facts: {constructor: 'ja'}}, {name: 'B', facts: {Levertijd: '1 week'}}]});
assert.deepStrictEqual(plain(K.kitTable('compare', r.spec).rows[1]).slice(-2), [null, '1 week']);

// Criteria: empty parts, doubles and cuts.
r = build({title: 'x', criteria: 'prijs, support,', options: [{name: 'A'}, {name: 'B'}]});
assert.deepStrictEqual(r.spec.criteria, ['prijs', 'support']);
assert.deepStrictEqual(r.warnings, [], 'a trailing comma is no problem');
r = build({title: 'x', criteria: ['prijs', 'Prijs', 'support', 'prijs'], options: [{name: 'A'}, {name: 'B'}]});
assert.deepStrictEqual(r.spec.criteria, ['prijs', 'support']);
r = build({title: 'x', criteria: ['y'.repeat(60)], options: [{name: 'A', facts: {['k'.repeat(40)]: 'v'}}, {name: 'B'}]});
assert.ok(r.warnings.some(x => x.includes('Een criterium is ingekort tot 40')));
assert.ok(r.warnings.some(x => x.includes('Een feit van "A" is ingekort tot 32')));

// English warnings.
r = build({title: 'x', lang: 'en', recommended: 7, criteria: Array.from({length: 8}, (_, i) => 'c' + i),
  options: [{name: 'A', price: '£ 5', score: '12/10'}, {name: 'A'}]});
const we = r.warnings.join('\n');
['points at none of the options', 'is not in euros', 'more than 6 criteria', 'The score of "A"', 'appears more than once']
  .forEach(part => assert.ok(we.includes(part), 'English warning about: ' + part + '\n' + we));

// The height estimate grows with long text.
const tall = build({title: 'x', options: [0, 1, 2, 3].map(i => ({name: 'Optie ' + i, price: 10, score: 7,
  pros: Array(5).fill('Een pluspunt dat over meerdere regels loopt in een smalle kaart'), facts: {Support: 'Telefoon, mail en chat op werkdagen van 8 tot 18 uur'}}))});
const short = build({title: 'x', options: [0, 1, 2, 3].map(i => ({name: 'Optie ' + i, price: 10, score: 7, pros: Array(5).fill('Kort'), facts: {Support: 'Mail'}}))});
assert.ok(tall.estHeight > short.estHeight + 150, tall.estHeight + ' vs ' + short.estHeight);

// No em or en dashes in anything the user sees.
const fs = require('fs');
['compare.js', 'compare.css'].forEach(f => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', f), 'utf8');
  const dashes = new RegExp('[' + String.fromCharCode(0x2013, 0x2014) + ']');
  assert.ok(!dashes.test(src), 'no long dashes in ' + f);
});

console.log('ok');
