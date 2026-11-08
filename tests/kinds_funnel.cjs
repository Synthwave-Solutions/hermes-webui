// The "funnel" data block (static/interactive-ui/kinds/funnel.js) in Node:
// checks, fixes, plain errors, the export table and the limits.
'use strict';
const path = require('path');
const assert = require('assert');

const K = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kit-core.js'));
global.SWKit = K;
require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', 'funnel.js'));
const build = (value, opts) => K.build('funnel', typeof value === 'string' ? value : JSON.stringify(value), Object.assign({lang: 'nl'}, opts));
const dashes = /[\u2013\u2014]/;

// ── Registration ────────────────────────────────────────────────────────────
assert.strictEqual(K.kitKind('funnel'), 'funnel');
assert.strictEqual(K.kitKind('trechter'), 'funnel');
assert.strictEqual(K.NAME.nl.funnel, 'Trechter');
assert.strictEqual(K.NOUN.nl.funnel, 'trechter');
assert.ok(K.extra('funnel') && K.extra('funnel').icon === 'funnel');

// ── A valid funnel ──────────────────────────────────────────────────────────
const ok = build({title: 'Salestrechter Q3', lang: 'nl', source: 'Twenty CRM',
  stages: [{label: 'Leads', value: 1240}, {label: 'Kennismaking', value: 310, note: 'Via website'}, {label: 'Offerte', value: 96}, {label: 'Klant', value: 37}],
  compare: [1100, 260, 90, 30]});
assert.deepStrictEqual(ok.errors, []);
assert.deepStrictEqual(ok.warnings, []);
const s = ok.spec;
assert.strictEqual(s.title, 'Salestrechter Q3');
assert.strictEqual(s.format, 'number');
assert.strictEqual(s.stages.length, 4);
assert.deepStrictEqual(s.stages.map(x => x.conv), [null, 25, 31, 38.5]);
assert.deepStrictEqual(s.stages.map(x => x.fromStart), [100, 25, 7.7, 3]);
assert.deepStrictEqual(s.stages.map(x => x.prev), [1100, 260, 90, 30]);
assert.strictEqual(s.stages[0].w, 100);
assert.strictEqual(s.drop, 1, 'Leads to Kennismaking loses the most');
assert.strictEqual(s.overall, 3);
assert.strictEqual(s.overallPrev, 2.7);
assert.strictEqual(s.compare, true);
assert.ok(ok.estHeight > 200 && ok.estHeight < 600);

// "steps", a two-stage funnel (no biggest drop), English and currency read from the values.
const two = build({title: 'Shop', lang: 'en', steps: [{name: 'Visitors', value: '€ 18.400'}, {name: 'Orders', value: '€ 212'}]});
assert.deepStrictEqual(two.errors, []);
assert.strictEqual(two.spec.lang, 'en');
assert.strictEqual(two.spec.format, 'currency');
assert.strictEqual(two.spec.drop, -1);
assert.strictEqual(two.spec.compare, false);
assert.strictEqual(two.spec.overall, 1.2);

// ── A messy funnel: fixed with plain warnings ───────────────────────────────
const messy = build(`{ // werving
  "steps": [
    {"name": "Sollicitaties ontvangen via de website en vacaturebanken samen", "value": "1.250"},
    ["Eerste selectie", 420],
    {"label": "Telefonisch gesprek", "count": "180"},
    {"label": "", "value": 50},
    {"label": "Assessment", "value": "veel"},
    {"label": "Tweede gesprek", "value": 60},
    {"label": "Aanbod", "value": 75},
    {"label": "Aangenomen", "value": -3},
    "los",
    {"label": "Na een jaar", "value": 15},
    {"label": "Na twee jaar", "value": 11},
  ],
  "format": "procent",
  "compare": [1000, "x", 150],
}`);
assert.deepStrictEqual(messy.errors, []);
const w = messy.warnings.join('\n');
for(const want of ['De titel ontbreekt.', 'heeft 3 waarden, verwacht 11', 'Er zijn 11 fasen; alleen de eerste 8', 'Onbekend format "procent"',
  'is ingekort tot 40 tekens', 'Vergelijkingswaarde 2 is geen getal', 'Fase 4 heeft geen naam', '"Assessment" heeft geen getal',
  '"Aanbod" is groter dan de fase ervoor ("Tweede gesprek")', '"Aangenomen" had een negatieve waarde']) assert.ok(w.includes(want), 'warning: ' + want + '\n' + w);
assert.ok(!dashes.test(w), 'no long dashes in messages');
const ms = messy.spec;
assert.strictEqual(ms.title, 'Trechter');
assert.strictEqual(ms.format, 'number');
assert.deepStrictEqual(ms.stages.map(x => x.label), ['Sollicitaties ontvangen via de website…', 'Eerste selectie', 'Telefonisch gesprek', 'Tweede gesprek', 'Aanbod', 'Aangenomen']);
assert.ok(ms.stages[0].label.length <= 40);
assert.deepStrictEqual(ms.stages.map(x => x.value), [1250, 420, 180, 60, 75, 0]);
assert.strictEqual(ms.stages[4].grows, true);
assert.strictEqual(ms.stages[4].conv, 125, 'a growing stage is still drawn');
assert.strictEqual(ms.stages[5].conv, 0);
assert.strictEqual(ms.drop, 5, 'the biggest drop never points at a growing stage');
assert.deepStrictEqual(ms.stages.map(x => x.prev), [1000, null, 150, null, null, null]);
// A map of names to numbers keeps its order.
const asMap = build({title: 'Kort', stages: {Bezoek: 900, Aanvraag: 90, Klant: 9}});
assert.deepStrictEqual(asMap.errors, []);
assert.deepStrictEqual(asMap.spec.stages.map(x => x.label), ['Bezoek', 'Aanvraag', 'Klant']);
assert.strictEqual(asMap.warnings.length, 1);
// After a stage of 0 there is no share.
const zero = build({title: 'Nul', stages: [{label: 'A', value: 10}, {label: 'B', value: 0}, {label: 'C', value: 0}]});
assert.deepStrictEqual(zero.errors, []);
assert.strictEqual(zero.spec.stages[2].conv, null);

// ── Fatal: one plain error each ─────────────────────────────────────────────
const noStages = build({title: 'Leeg'});
assert.deepStrictEqual(noStages.errors, ['Er zijn geen fasen (stages).']);
assert.strictEqual(noStages.spec, null);
const oneStage = build({title: 'Eén', stages: [{label: 'A', value: 'geen'}, {label: 'B', value: 4}]});
assert.strictEqual(oneStage.errors.length, 1);
assert.ok(/minstens twee fasen/.test(oneStage.errors[0]) && /er is er 1/.test(oneStage.errors[0]));
const allZero = build({title: 'Nul', stages: [{label: 'A', value: 0}, {label: 'B', value: 0}]});
assert.strictEqual(allZero.errors.length, 1);
assert.ok(/waarde 0/.test(allZero.errors[0]));
const en = build({title: 'x', lang: 'en', stages: []});
assert.deepStrictEqual(en.errors, ['There are no stages.']);
assert.strictEqual(build('{"title": "x", "stages": [').errors.length, 1, 'broken JSON gives one error');
assert.strictEqual(build('[1,2]').errors.length, 1);

// ── Export table ────────────────────────────────────────────────────────────
const t = K.kitTable('funnel', s);
assert.deepStrictEqual(t.header, ['Fase', 'Aantal', 'Conversie vanaf vorige', 'Conversie vanaf begin', 'Vorige periode']);
assert.deepStrictEqual(t.types, ['text', 'number', 'percent', 'percent', 'number']);
assert.deepStrictEqual(t.rows[0], ['Leads', 1240, null, 100, 1100]);
assert.deepStrictEqual(t.rows[3], ['Klant', 37, 38.5, 3, 30]);
const t2 = K.kitTable('funnel', two.spec);
assert.deepStrictEqual(t2.header, ['Stage', 'Value', 'From previous', 'From start']);
assert.deepStrictEqual(t2.rows[1], ['Orders', 212, 1.2, 1.2]);
const csv = K.toCsv(t);
assert.ok(csv.startsWith('﻿Fase;Aantal;Conversie vanaf vorige;Conversie vanaf begin;Vorige periode\r\n'));
assert.ok(csv.includes('Klant;37;38,5;3;30\r\n'));
const plain4 = build({title: 'Vier', stages: [{label: 'A', value: 4}, {label: 'B', value: 2}]});
assert.deepStrictEqual(K.kitTable('funnel', plain4.spec).header, ['Fase', 'Aantal', 'Conversie vanaf vorige', 'Conversie vanaf begin']);

// ── Limits ──────────────────────────────────────────────────────────────────
const big = build({title: 'x'.repeat(300), subtitle: 'y'.repeat(400),
  stages: Array.from({length: 40}, (_, i) => ({label: 'Fase ' + i + ' ' + 'z'.repeat(80), value: 1000 - i, note: 'n'.repeat(200)}))});
assert.deepStrictEqual(big.errors, []);
assert.strictEqual(big.spec.stages.length, 8);
assert.ok(big.spec.title.length <= K.LIMITS.title);
assert.ok(big.spec.subtitle.length <= K.LIMITS.subtitle);
big.spec.stages.forEach(x => { assert.ok(x.label.length <= 40); assert.ok(x.note.length <= 80); });
assert.ok(big.estHeight <= 2000);
assert.ok(build('{"title":"x","stages":"' + 'a'.repeat(210 * 1024) + '"}').errors[0].includes('te groot'));
// Control characters never reach the frame.
const ctl = build({title: 'a\u0007b', stages: [{label: 'x\u0000y', value: 2}, {label: 'z', value: 1}]});
assert.strictEqual(ctl.spec.title, 'ab');
assert.strictEqual(ctl.spec.stages[0].label, 'xy');

console.log('ok');
