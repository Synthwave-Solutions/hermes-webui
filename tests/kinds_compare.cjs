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
['compare', 'vergelijk', 'vergelijking', 'options', 'opties'].forEach(f => assert.strictEqual(K.kitKind(f), 'compare', f));
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
['Optie 4 heeft geen naam', 'Optie 5 is geen object', 'meer dan één aanrader', 'Er zijn 5 opties; alleen 4', 'komt vaker voor',
  'scoreMax "7"', 'De minpunten van "Bechtle"', 'De prijs van "Bechtle (2)"', 'alleen de eerste 6', 'Het feit "Garantie" bij "Centralpoint"']
  .forEach(part => assert.ok(w.includes(part), 'warning about: ' + part + '\n' + w));
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
assert.deepStrictEqual(r.errors, ['Een vergelijking heeft minstens twee opties met een naam (name); er is er 1.']);
r = build({title: 'x', options: 'geen'});
assert.deepStrictEqual(r.errors, ['Er zijn geen opties (options) om te vergelijken.']);
r = build({title: 'x', lang: 'en', options: []});
assert.deepStrictEqual(r.errors, ['There are no options to compare.']);
r = build('{"title": "x", "options": [');
assert.strictEqual(r.errors.length, 1);
assert.ok(/geen geldige JSON/.test(r.errors[0]));

// ── Export ──────────────────────────────────────────────────────────────────
const t = K.kitTable('compare', build(good).spec);
assert.deepStrictEqual(t.header, ['Optie', 'Prijs', 'Score', 'Pluspunten', 'Minpunten', 'Levertijd', 'Support', 'Proefperiode']);
assert.deepStrictEqual(plain(t.rows[1]), ['Moneybird', 32.5, 8.5, 'Snel te leren; Goede app', '', 'Direct', 'Chat', null]);
assert.deepStrictEqual(plain(t.rows[2]).slice(0, 3), ['SnelStart', 45, 7]);
assert.strictEqual(t.types[1], 'currency');
const csv = K.toCsv(t);
assert.ok(csv.startsWith('﻿Optie;Prijs;Score;Pluspunten;Minpunten;Levertijd;Support;Proefperiode\r\n'));
assert.ok(csv.includes('Moneybird;32,5;8,5;Snel te leren; Goede app'.replace('Snel te leren; Goede app', '"Snel te leren; Goede app"')), 'decimal comma and quoting');
const te = K.kitTable('compare', build(Object.assign({}, good, {lang: 'en'})).spec);
assert.deepStrictEqual(te.header.slice(0, 5), ['Option', 'Price', 'Score', 'Pros', 'Cons']);
assert.strictEqual(K.kitTable('compare', ms).rows[3][1], 'Op aanvraag', 'a text price is exported as text');

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
r = build({title: 'x', criteria: Array(20).fill('prijs'), options: [{name: 'A'}, {name: 'B'}]});
assert.strictEqual(r.spec.criteria.length, 6);
// Nothing in the cleaned spec carries markup or functions: it is a plain clone.
assert.deepStrictEqual(plain(build(good).spec), build(good).spec);

// No em or en dashes in anything the user sees.
const fs = require('fs');
['compare.js', 'compare.css'].forEach(f => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', f), 'utf8');
  const dashes = new RegExp('[' + String.fromCharCode(0x2013, 0x2014) + ']');
  assert.ok(!dashes.test(src), 'no long dashes in ' + f);
});

console.log('ok');
