// The "funnel" data block (static/interactive-ui/kinds/funnel.js) in Node:
// checks, fixes, plain errors, the export table and the limits.
'use strict';
const path = require('path');
const assert = require('assert');

const K = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kit-core.js'));
global.SWKit = K;
const F = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', 'funnel.js'));
const build = (value, opts) => K.build('funnel', typeof value === 'string' ? value : JSON.stringify(value), Object.assign({lang: 'nl'}, opts));
const dashes = /[\u2013\u2014]/;
// The strings the frame shows, with the same formatter the frame uses.
const texts = (spec) => F.texts(spec, (v, type, dec) => K.formatValue(v, type, dec, spec.lang));

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
assert.deepStrictEqual(s.stages.map(x => x.conv), [null, 25, 30.97, 38.54]);
assert.deepStrictEqual(s.stages.map(x => x.fromStart), [100, 25, 7.742, 2.984]);
assert.deepStrictEqual(s.stages.map(x => x.prev), [1100, 260, 90, 30]);
assert.strictEqual(s.stages[0].w, 100);
assert.strictEqual(s.drop, 1, 'Leads to Kennismaking loses the most');
assert.strictEqual(s.overall, 2.984);
assert.strictEqual(s.overallPrev, 2.727);
assert.strictEqual(s.compare, true);
assert.ok(ok.estHeight > 200 && ok.estHeight < 600);

// "steps", a two-stage funnel (no biggest drop), English and currency read from the values.
const two = build({title: 'Shop', lang: 'en', steps: [{name: 'Visitors', value: '€ 18.400'}, {name: 'Orders', value: '€ 212'}]});
assert.deepStrictEqual(two.errors, []);
assert.strictEqual(two.spec.lang, 'en');
assert.strictEqual(two.spec.format, 'currency');
assert.strictEqual(two.spec.drop, -1);
assert.strictEqual(two.spec.compare, false);
assert.strictEqual(two.spec.overall, 1.152);

// ── A messy funnel: fixed with plain warnings ───────────────────────────────
const messy = build(`{ // werving
  "steps": [
    {"name": "Sollicitaties ontvangen via de website en vacaturebanken samen", "value": "1.250"},
    ["Eerste selectie", 420],
    {"label": "Telefonisch gesprek", "count": "180"},
    {"label": "", "value": 50},
    {"label": "Assessment", "value": "ca. 90"},
    {"label": "Tweede gesprek", "value": 60},
    {"label": "Aanbod", "value": 75},
    {"label": "Aangenomen", "value": -3},
    "los",
    {"label": "Na een jaar", "value": 15},
    {"label": "Na twee jaar", "value": 11},
  ],
  "format": "taart",
  "compare": [1000, "x", 150],
}`);
assert.deepStrictEqual(messy.errors, []);
const w = messy.warnings.join('\n');
for(const want of ['De titel ontbreekt.', 'heeft 3 waarden, verwacht 11; ze is weggelaten', 'Er zijn 11 fasen; alleen de eerste 8', 'Onbekend format "taart"',
  'is ingekort tot 40 tekens', 'Fase 4 heeft geen naam',
  '"Aanbod" is groter dan de fase ervoor ("Tweede gesprek")', '"Aangenomen" had een negatieve waarde']) assert.ok(w.includes(want), 'warning: ' + want + '\n' + w);
assert.ok(!dashes.test(w), 'no long dashes in messages');
// Estimates stay estimates: the stage remembers it, so the frame shows "ca." and whole percents.
{ const est = K.build('funnel', JSON.stringify({title: 't', stages: [{label: 'A', value: 'ca. 1.000'}, {label: 'B', value: '>200'}, {label: 'C', value: 50}]}), {lang: 'nl'}).spec;
  assert.deepStrictEqual(est.stages.map(x => x.rough), ['ca', 'gt', '']); }
// A stage without any number stops the block: conversions never jump over a missing stage.
assert.deepStrictEqual(K.build('funnel', JSON.stringify({title: 't', stages: [{label: 'A', value: 10}, {label: 'B', value: 'veel'}, {label: 'C', value: 2}]}), {lang: 'nl'}).errors,
  ['Bij "B" staat geen getal.']);
assert.deepStrictEqual(K.build('funnel', JSON.stringify({title: 't', stages: [{label: 'A', value: 'ca. 1.240'}, {label: 'B', value: '310+'}, {label: 'C', value: '1,2k'}]}), {lang: 'nl'}).spec.stages.map(x => x.value), [1240, 310, 1200]);
const ms = messy.spec;
assert.strictEqual(ms.title, 'Trechter');
assert.strictEqual(ms.format, 'number');
assert.deepStrictEqual(ms.stages.map(x => x.label), ['Sollicitaties ontvangen via de website…', 'Eerste selectie', 'Telefonisch gesprek', 'Assessment', 'Tweede gesprek', 'Aanbod', 'Aangenomen']);
assert.ok(ms.stages[0].label.length <= 40);
assert.deepStrictEqual(ms.stages.map(x => x.value), [1250, 420, 180, 90, 60, 75, 0]);
assert.strictEqual(ms.stages[5].grows, true);
assert.strictEqual(ms.stages[5].conv, 125, 'a growing stage is still drawn');
assert.strictEqual(ms.stages[6].conv, 0);
assert.strictEqual(ms.drop, 6, 'the biggest drop never points at a growing stage');
// A compare list of the wrong length is dropped as a whole, never applied by position.
assert.deepStrictEqual(ms.stages.map(x => x.prev), [null, null, null, null, null, null, null]);
assert.strictEqual(ms.compare, false);
assert.strictEqual(K.kitTable('funnel', ms).header.length, 5, 'no Vorige periode column; Schatting because Assessment is ca. 90');
assert.strictEqual(K.kitTable('funnel', ms).header[4], 'Schatting');
// A list of the right length with one bad value: only that value is left out.
const badCmp = build({title: 'Cmp', stages: [{label: 'A', value: 10}, {label: 'B', value: 5}, {label: 'C', value: 2}], compare: [9, 'x', 1]});
assert.ok(badCmp.warnings.join('\n').includes('Vergelijkingswaarde 2 is geen getal'));
assert.deepStrictEqual(badCmp.spec.stages.map(x => x.prev), [9, null, 1]);
// A map of names to numbers keeps its order.
const asMap = build({title: 'Kort', stages: {Bezoek: 900, Aanvraag: 90, Klant: 9}});
assert.deepStrictEqual(asMap.errors, []);
assert.deepStrictEqual(asMap.spec.stages.map(x => x.label), ['Bezoek', 'Aanvraag', 'Klant']);
assert.strictEqual(asMap.warnings.length, 1);
// After a stage of 0 there is no share.
const zero = build({title: 'Nul', stages: [{label: 'A', value: 10}, {label: 'B', value: 0}, {label: 'C', value: 0}]});
assert.deepStrictEqual(zero.errors, []);
assert.strictEqual(zero.spec.stages[2].conv, null);

// ── Very small shares stay visible ──────────────────────────────────────────
const web = build({title: 'Web', stages: [{label: 'Bezoekers', value: 250000}, {label: 'Product bekeken', value: 9100}, {label: 'Winkelmand', value: 4800},
  {label: 'Afrekenen', value: 3900}, {label: 'Betaald', value: 3600}, {label: 'Proefperiode', value: 410}, {label: 'Abonnement', value: 37}]});
assert.deepStrictEqual(web.errors, []);
const wl = web.spec.stages[6];
assert.ok(wl.fromStart > 0 && Math.abs(wl.fromStart - 0.0148) < 1e-9, 'the share is not rounded away: ' + wl.fromStart);
assert.ok(web.spec.overall > 0);
const wt = texts(web.spec);
assert.strictEqual(wt.overall(), 'Van Bezoekers naar Abonnement: 0,015%');
assert.ok(wt.detail(6).includes('0,015% van het begin'), wt.detail(6));
assert.strictEqual(K.kitTable('funnel', web.spec).rows[6][3], 0.015, 'the export keeps the small share as the block shows it');
// Bars always grow with the value, even 37 against 250.000.
const ws = web.spec.stages.map(x => x.w);
for(let i = 1; i < ws.length; i++) assert.ok(ws[i] < ws[i - 1] && ws[i] > 0, 'bar widths: ' + ws);
// The percent text: a real 0 is 0%, tiny is never 0, nearly all is never 100%.
const pt = texts(ok.spec).pct;
assert.strictEqual(pt(0), '0%');
assert.strictEqual(pt(0.0148), '0,015%');
assert.strictEqual(pt(0.05), '0,05%');
assert.strictEqual(pt(0.0004), '<0,001%');
assert.strictEqual(pt(0.4), '0,4%');
assert.strictEqual(pt(4.2), '4,2%');
assert.strictEqual(pt(38.54), '39%');
assert.strictEqual(pt(99.7), '99,7%');
assert.strictEqual(pt(100), '100%');
assert.strictEqual(pt(null), '');
const z = texts(zero.spec);
assert.ok(z.detail(1).includes('0% van A'), z.detail(1));

// ── Texts after a stage of 0 have no empty parts ────────────────────────────
const mid = build({title: 'Mid', stages: [{label: 'Oud', value: 0}, {label: 'Nieuw', value: 50}, {label: 'Klant', value: 10}], compare: [40, 50, 5]});
assert.deepStrictEqual(mid.errors, []);
assert.ok(mid.warnings.join('\n').includes('De eerste fase ("Oud") is 0'), 'a first stage of 0 is not dropped silently');
const mt = texts(mid.spec);
assert.strictEqual(mt.overall(), '');
assert.strictEqual(mt.detail(1), 'Nieuw · 50 · vorige periode 50');
assert.strictEqual(mt.aria(1), 'Nieuw, 50');
assert.strictEqual(mt.chip(1), '');
assert.strictEqual(mt.detail(2), 'Klant · 10 · 20% van Nieuw · vorige periode 5');
assert.strictEqual(mt.aria(2), 'Klant, 10, 20% van Nieuw');
const mid0 = build({title: 'Mid0', stages: [{label: 'A', value: 100}, {label: 'B', value: 0}, {label: 'C', value: 5}]});
const m0 = texts(mid0.spec);
assert.strictEqual(m0.detail(2), 'C · 5 · 5,0% van het begin');
assert.strictEqual(m0.aria(2), 'C, 5');
for(const x of [mt.detail(1), mt.aria(1), m0.detail(2), m0.aria(2)]) assert.ok(!/(^|[·,]) *(van|of) /.test(x) && !/ {2}/.test(x), 'no dangling part: ' + x);
// The normal texts.
const st = texts(s);
assert.strictEqual(st.overall(), 'Van Leads naar Klant: 3,0%');
assert.strictEqual(st.overallPrev(), 'vorige periode 2,7%');
assert.strictEqual(st.drop(), 'Grootste uitval: van Leads naar Kennismaking (25% gaat door)');
assert.strictEqual(st.detail(1), 'Kennismaking · 310 · 25% van Leads · 25% van het begin · vorige periode 260 · Via website');
assert.strictEqual(st.aria(3), 'Klant, 37, 39% van Offerte');
assert.strictEqual(st.detail(0), 'Leads · 1.240 · vorige periode 1.100');
// A tie for the biggest drop points at the first one.
const tie = build({title: 'Gelijk', stages: [{label: 'A', value: 1000}, {label: 'B', value: 500}, {label: 'C', value: 250}, {label: 'D', value: 200}]});
assert.strictEqual(tie.spec.drop, 1);

// ── Percent stages keep their sign ──────────────────────────────────────────
const pc = build({title: 'Pct', stages: [{label: 'Bereik', value: '100%'}, {label: 'Klik', value: '12%'}, {label: 'Koop', value: '1,5%'}]});
assert.deepStrictEqual(pc.errors, []);
assert.deepStrictEqual(pc.warnings, []);
assert.strictEqual(pc.spec.format, 'percent');
const pct = texts(pc.spec);
assert.strictEqual(pct.num(pc.spec.stages[2].value), '1,5%');
assert.strictEqual(pct.detail(1), 'Klik · 12% · 12% van Bereik · 12% van het begin');
const pcT = K.kitTable('funnel', pc.spec);
assert.deepStrictEqual(pcT.header, ['Fase', 'Aandeel', 'Conversie vanaf vorige (%)', 'Conversie vanaf begin (%)']);
assert.deepStrictEqual(pcT.types, ['text', 'percent', 'number', 'number']);
assert.strictEqual(build({title: 'P', format: 'procent', stages: [{label: 'A', value: 50}, {label: 'B', value: 5}]}).spec.format, 'percent');

// ── Fatal: one plain error each ─────────────────────────────────────────────
const noStages = build({title: 'Leeg'});
assert.deepStrictEqual(noStages.errors, ['Er zijn geen fasen (stages).']);
assert.strictEqual(noStages.spec, null);
const oneStage = build({title: 'Eén', stages: [{label: 'B', value: 4}]});
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
assert.deepStrictEqual(t.header, ['Fase', 'Aantal', 'Conversie vanaf vorige (%)', 'Conversie vanaf begin (%)', 'Vorige periode']);
assert.deepStrictEqual(t.types, ['text', 'number', 'number', 'number', 'number']);
assert.deepStrictEqual(t.rows[0], ['Leads', 1240, null, 100, 1100]);
assert.deepStrictEqual(t.rows[3], ['Klant', 37, 38.5, 3, 30]);
const t2 = K.kitTable('funnel', two.spec);
assert.deepStrictEqual(t2.header, ['Stage', 'Value', 'From previous (%)', 'From start (%)']);
assert.deepStrictEqual(t2.rows[1], ['Orders', 212, 1.2, 1.2]);
const csv = K.toCsv(t);
assert.ok(csv.startsWith('﻿Fase;Aantal;Conversie vanaf vorige (%);Conversie vanaf begin (%);Vorige periode\r\n'));
assert.ok(csv.includes('Klant;37;38,5;3;30\r\n'), csv);
const plain4 = build({title: 'Vier', stages: [{label: 'A', value: 4}, {label: 'B', value: 2}]});
assert.deepStrictEqual(K.kitTable('funnel', plain4.spec).header, ['Fase', 'Aantal', 'Conversie vanaf vorige (%)', 'Conversie vanaf begin (%)']);

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
