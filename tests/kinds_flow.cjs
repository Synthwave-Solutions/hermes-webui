// The "flow" data block (static/interactive-ui/kinds/flow.js) in Node:
// checks, fixes, plain errors, the export table, limits and the layout.
'use strict';
const path = require('path');
const assert = require('assert');

const K = require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kit-core.js'));
global.SWKit = K;
require(path.join(__dirname, '..', 'static', 'interactive-ui', 'kinds', 'flow.js'));
const X = K.extra('flow');
const build = (value, opts) => K.build('flow', typeof value === 'string' ? value : JSON.stringify(value), Object.assign({lang: 'nl'}, opts));

// ── Registration ────────────────────────────────────────────────────────────
assert.ok(X, 'flow registers with SWKit');
['flow', 'flowchart', 'proces', 'processchema', 'stroomschema', 'processtroom', 'procesflow'].forEach(f => assert.strictEqual(K.kitKind(f), 'flow', f));
assert.strictEqual(K.NAME.nl.flow, 'Processchema');
assert.strictEqual(K.kitKind('table'), 'table', 'core fences stay');

// ── A valid spec ────────────────────────────────────────────────────────────
const sales = {
  title: 'Van aanvraag tot getekende offerte', lang: 'nl',
  nodes: [
    {id: 'in', label: 'Aanvraag binnen', type: 'start', owner: 'Website'},
    {id: 'fit', label: 'Past de vraag bij ons?', type: 'decision', owner: 'Marcel'},
    {id: 'nee', label: 'Vriendelijk afwijzen', type: 'end'},
    {id: 'off', label: 'Offerte opstellen', owner: 'Yaser', note: 'Binnen 3 dagen'},
    {id: 'wacht', label: 'Wachten op reactie', type: 'wait'},
    {id: 'ok', label: 'Akkoord?', type: 'decision', owner: 'Klant'},
    {id: 'aanp', label: 'Offerte aanpassen', owner: 'Yaser'},
    {id: 'klaar', label: 'Project starten', type: 'end', owner: 'Michaël'},
  ],
  edges: [
    {from: 'in', to: 'fit'}, {from: 'fit', to: 'off', label: 'Ja'}, {from: 'fit', to: 'nee', label: 'Nee'},
    {from: 'off', to: 'wacht'}, {from: 'wacht', to: 'ok'}, {from: 'ok', to: 'klaar', label: 'Ja'},
    {from: 'ok', to: 'aanp', label: 'Nee'}, {from: 'aanp', to: 'wacht'},
  ],
};
let r = build(sales);
assert.deepStrictEqual(r.errors, []);
assert.deepStrictEqual(r.warnings, []);
assert.strictEqual(r.spec.direction, 'down');
assert.strictEqual(r.spec.nodes.length, 8);
assert.strictEqual(r.spec.edges.length, 8);
assert.deepStrictEqual(r.spec.nodes.map(n => n.type), ['start', 'decision', 'end', 'step', 'wait', 'decision', 'step', 'end']);
assert.ok(r.spec.nodes.filter(n => n.owner).every(n => n.o >= 0), 'several owners get a colour');
assert.strictEqual(r.spec.nodes[2].o, -1, 'a step without owner has no colour');
assert.ok(r.estHeight > 300 && r.estHeight <= 2000);

// Layers: the loop back from "Offerte aanpassen" is a back edge, not a new layer.
const rk = X.rank(r.spec);
assert.deepStrictEqual(rk.layer, [0, 1, 2, 2, 3, 4, 5, 5]);
assert.deepStrictEqual(rk.back, [false, false, false, false, false, false, false, true]);

// Layout: no overlaps, the "yes" path runs straight, the loop goes around the side.
const sizes = r.spec.nodes.map(n => n.type === 'decision' ? {w: 210, h: 90} : {w: 180, h: 46});
const labelW = r.spec.edges.map(e => e.label ? 30 : 0);
const geo = X.layout(r.spec, {dir: 'down', sizes, labelW});
const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
for(let i = 0; i < geo.nodes.length; i++) for(let j = i + 1; j < geo.nodes.length; j++)
  assert.ok(!overlap(geo.nodes[i], geo.nodes[j]), `steps ${i} and ${j} overlap`);
const cx = i => geo.nodes[i].x + geo.nodes[i].w / 2;
assert.ok(Math.abs(cx(1) - cx(3)) < 1, 'the yes branch sits under the decision');
assert.ok(Math.abs(cx(5) - cx(7)) < 1, 'the second yes branch too');
assert.ok(cx(2) > cx(1), 'the no branch goes to the side');
geo.edges.forEach(e => e.pts.forEach(p => assert.ok(p[0] >= 0 && p[1] >= 0 && p[0] <= geo.w && p[1] <= geo.h, 'edges stay inside')));
const loop = geo.edges[7];
assert.strictEqual(loop.back, true);
assert.ok(Math.max(...loop.pts.map(p => p[0])) > geo.nodes[6].x + geo.nodes[6].w, 'the loop runs outside the steps');
geo.edges.forEach(e => assert.ok(e.pts.length >= 2 && Math.hypot(...e.end) > 0.99));
geo.edges.forEach((e, j) => { if(labelW[j]) assert.ok(e.label && e.label.w === 30); });
assert.ok(geo.w > 0 && geo.h > 0);
const right = X.layout(r.spec, {dir: 'right', sizes, labelW});
assert.ok(right.w > right.h, 'right runs sideways');

// ── Export table ────────────────────────────────────────────────────────────
let t = K.kitTable('flow', r.spec);
assert.deepStrictEqual(t.header, ['Stap', 'Type', 'Eigenaar', 'Volgende stappen']);
assert.deepStrictEqual(t.rows[1], ['Past de vraag bij ons?', 'Keuze', 'Marcel', 'Offerte opstellen (Ja); Vriendelijk afwijzen (Nee)']);
assert.deepStrictEqual(t.rows[2], ['Vriendelijk afwijzen', 'Einde', '', '']);
assert.deepStrictEqual(t.rows[4][1], 'Wachten');
assert.ok(K.toCsv(t).includes('Stap;Type;Eigenaar;Volgende stappen'));
const en = build(Object.assign({}, sales, {lang: 'en'}));
assert.deepStrictEqual(K.kitTable('flow', en.spec).header, ['Step', 'Type', 'Owner', 'Next steps']);
assert.strictEqual(K.kitTable('flow', en.spec).rows[1][1], 'Decision');

// ── A fixable spec: aliases, strings, labels as references, warnings ────────
r = build(`{
  // comments and trailing commas are fine
  "direction": "diagonal",
  "steps": [
    "Aanvraag ontvangen",
    {"id": 2, "title": "Gegevens controleren", "type": "taak", "role": "Binnendienst"},
    {"id": "check", "label": "Krediet in orde?", "type": "vraag"},
    {"id": "check", "label": "Tweede check", "type": "rhombus"},
    {"label": ""},
    42,
    {"id": "x", "name": "Order bevestigen", "type": "einde", "owner": "${'Heel lang '.repeat(8)}"},
  ],
  "links": [
    "Aanvraag ontvangen -> 2",
    {"source": 2, "target": "check"},
    {"from": "check", "to": "x", "label": "Ja"},
    {"from": "check", "to": "bestaat-niet", "label": "Nee"},
    {"from": "check", "to": "x"},
    {"to": "x"},
    ["x", "tweede check", "fout"],
  ],
}`);
assert.deepStrictEqual(r.errors, []);
assert.strictEqual(r.spec.title, 'Processchema', 'a missing title gets the kind name');
assert.strictEqual(r.spec.direction, 'down');
assert.deepStrictEqual(r.spec.nodes.map(n => [n.label, n.type]), [
  ['Aanvraag ontvangen', 'step'], ['Gegevens controleren', 'step'], ['Krediet in orde?', 'decision'],
  ['Tweede check', 'step'], ['Order bevestigen', 'end']]);
assert.strictEqual(r.spec.nodes[1].owner, 'Binnendienst');
assert.ok(r.spec.nodes[4].owner.length <= 40);
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t, e.label]), [[0, 1, ''], [1, 2, ''], [2, 4, 'Ja'], [4, 3, 'fout']]);
const w = r.warnings.join('\n');
['De titel ontbreekt', 'richting', '"check" komt vaker voor', 'onbekend type "rhombus"', 'Stap 5 heeft geen label',
  'Stap 6 is geen object', 'ingekort tot 40', 'onbekende stap "bestaat-niet"', 'staat er vaker in', 'Verbinding 6 heeft geen from en to']
  .forEach(s => assert.ok(w.includes(s), 'warning: ' + s));

// Without links the steps follow each other; numbers point to steps when there are no ids.
r = build({title: 'Onboarding', steps: ['Contract', 'Account maken', 'Eerste dag']});
assert.deepStrictEqual(r.errors, []);
assert.deepStrictEqual(r.warnings, []);
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t]), [[0, 1], [1, 2]]);
r = build({title: 'Nummers', steps: ['A', 'B', 'C'], edges: [[1, 3], [3, 2]]});
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t]), [[0, 2], [2, 1]]);
r = build({title: 'Next', nodes: [{id: 'a', label: 'A', next: ['b', {to: 'c', label: 'Soms'}]}, {id: 'b', label: 'B'}, {id: 'c', label: 'C'}]});
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t, e.label]), [[0, 1, ''], [0, 2, 'Soms']]);
r = build({title: 'Alle links fout', steps: ['A', 'B'], edges: [{from: 'p', to: 'q'}]});
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t]), [[0, 1]]);
assert.ok(r.warnings.some(s => s.includes('op volgorde verbonden')));
r = build({title: 'Los', nodes: [{id: 'a', label: 'A'}, {id: 'b', label: 'B'}, {id: 'c', label: 'Los eiland'}], edges: [{from: 'a', to: 'b'}]});
assert.ok(r.warnings.some(s => s.includes('"Los eiland" is met geen enkele')));
r = build({title: 'Lus', nodes: [{id: 'a', label: 'Herinnering', type: 'wait'}, {id: 'b', label: 'Klaar', type: 'end'}],
  edges: [{from: 'a', to: 'a', label: 'Elke week'}, {from: 'a', to: 'b'}]});
assert.deepStrictEqual(r.errors, []);
const selfGeo = X.layout(r.spec, {dir: 'down', sizes: [{w: 160, h: 44}, {w: 120, h: 36}], labelW: [60, 0]});
assert.strictEqual(selfGeo.edges[0].back, true);
assert.ok(selfGeo.edges[0].label.x > selfGeo.nodes[0].x + selfGeo.nodes[0].w, 'a self loop label sits beside the step');

// ── Fatal specs: one plain sentence ────────────────────────────────────────
assert.deepStrictEqual(build({title: 'Leeg'}).errors, ['Er zijn geen stappen (nodes).']);
assert.deepStrictEqual(build({title: 'Leeg', nodes: []}).errors, ['Er zijn geen stappen (nodes).']);
assert.deepStrictEqual(build({title: 'Kapot', nodes: [{}, null, 7, {label: ''}]}).errors, ['Geen enkele stap heeft een naam (label).']);
assert.deepStrictEqual(build({title: 'Leeg', nodes: []}, {lang: 'en'}).errors, ['There are no steps (nodes).']);
assert.strictEqual(build('{"title": "x", "nodes": [').errors.length, 1, 'broken JSON is one error');
assert.strictEqual(build({title: 'Leeg'}).spec, null);

// ── Limits ─────────────────────────────────────────────────────────────────
const many = Array.from({length: 40}, (_, i) => ({id: 'n' + i, label: 'Stap ' + i + ' '.repeat(3) + 'x'.repeat(80)}));
const links = Array.from({length: 39}, (_, i) => ({from: 'n' + i, to: 'n' + (i + 1), label: 'y'.repeat(40)}))
  .concat(Array.from({length: 30}, (_, i) => ({from: 'n' + i, to: 'n' + ((i + 5) % 30)})));
r = build({title: 'T'.repeat(300), lang: 'en', nodes: many, edges: links});
assert.deepStrictEqual(r.errors, []);
assert.strictEqual(r.spec.nodes.length, 30);
assert.ok(r.spec.edges.length <= 50);
assert.ok(r.spec.title.length <= 120);
assert.ok(r.spec.nodes.every(n => n.label.length <= 60));
assert.ok(r.spec.edges.every(e => e.label.length <= 24));
assert.ok(r.warnings.some(s => s.includes('There are 40 steps; only the first 30')));
assert.ok(r.warnings.some(s => s.includes('There are 69 links; only the first 50')));
assert.ok(r.warnings.some(s => /links? to steps? that (is|are) not shown/.test(s)), 'links to cut steps are one warning');
assert.ok(r.warnings.filter(s => s.includes('The label of link')).length <= 3, 'cut link labels: three, then one sum');
assert.ok(r.warnings.some(s => /more link labels were shortened/.test(s)));
assert.ok(r.warnings.length < 50, 'cut text is reported, but not once per edge');
const big = X.layout(r.spec, {dir: 'down', sizes: r.spec.nodes.map(() => ({w: 150, h: 50})), labelW: r.spec.edges.map(e => e.label ? 80 : 0)});
for(let i = 0; i < big.nodes.length; i++) for(let j = i + 1; j < big.nodes.length; j++)
  assert.ok(!overlap(big.nodes[i], big.nodes[j]), `big: steps ${i} and ${j} overlap`);
assert.ok(r.estHeight <= 2000);
assert.strictEqual(build('{"title":"x","nodes":[]}'.padEnd(210 * 1024, ' ')).errors.length, 1, 'too big');

// ── Regressions ────────────────────────────────────────────────────────────
// A loop back into a decision never ends on the side point a branch leaves from.
const segsOf = e => e.pts.slice(1).map((p, k) => [e.pts[k], p]);
const same = (a, b) => Math.abs(a[0] - b[0]) < 0.5 && Math.abs(a[1] - b[1]) < 0.5;
function noBackOnPorts(g, label){
  g.edges.forEach((e, j) => {
    if(!e.back) return;
    const end = e.pts[e.pts.length - 1];
    g.edges.forEach((o, k) => { if(!o.back && k !== j) assert.ok(!same(o.pts[0], end), `${label}: back edge ${j} ends where edge ${k} starts`); });
  });
}
r = build({title: 'Lus', nodes: [{id: 'a', label: 'Klopt het?', type: 'decision'}, {id: 'b', label: 'Door'}, {id: 'c', label: 'Herstellen'}],
  edges: [{from: 'a', to: 'b', label: 'Ja'}, {from: 'a', to: 'c', label: 'Nee'}, {from: 'c', to: 'a'}]});
['down', 'right'].forEach(dir => {
  const g = X.layout(r.spec, {dir, sizes: [{w: 180, h: 80}, {w: 140, h: 44}, {w: 140, h: 44}], labelW: [24, 30, 0]});
  noBackOnPorts(g, 'small ' + dir);
});
const onb = {title: 'Onboarding', nodes: [
  {id: 'c', label: 'Contract getekend', type: 'start'}, {id: 'acc', label: 'Accounts aanmaken'}, {id: 'lap', label: 'Laptop nodig?', type: 'decision'},
  {id: 'best', label: 'Laptop bestellen'}, {id: 'lev', label: 'Wachten op levering', type: 'wait'}, {id: 'eigen', label: 'Eigen laptop inrichten'},
  {id: 'buddy', label: 'Buddy koppelen'}, {id: 'vog', label: 'VOG binnen?', type: 'decision'}, {id: 'herinn', label: 'Herinnering sturen'},
  {id: 'dag1', label: 'Eerste werkdag', type: 'end'}, {id: 'stop', label: 'Start uitstellen', type: 'end'}],
  edges: [['c', 'acc'], ['acc', 'lap'], ['lap', 'best', 'Ja, nieuwe'], ['lap', 'eigen', 'Nee, eigen'], ['lap', 'buddy', 'Heeft er al één'],
    ['best', 'lev'], ['lev', 'buddy'], ['eigen', 'buddy'], ['buddy', 'vog'], ['vog', 'dag1', 'Ja'], ['vog', 'herinn', 'Nee'],
    ['herinn', 'vog', 'Na 3 dagen'], ['herinn', 'stop', 'Na 2 weken']]};
r = build(onb);
assert.deepStrictEqual(r.errors, []);
const onbSizes = w => r.spec.nodes.map(n => n.type === 'decision' ? {w: Math.round(w * 1.18), h: 64} : {w, h: 52});
const onbLab = r.spec.edges.map(e => e.label ? e.label.length * 6 + 11 : 0);
[184, 116, 92].forEach(w => {
  const g = X.layout(r.spec, {dir: 'down', sizes: onbSizes(w), labelW: onbLab, gapCross: w < 116 ? 10 : 16, uprightLanes: true});
  noBackOnPorts(g, 'onboarding ' + w);
  for(let i = 0; i < g.nodes.length; i++) for(let j = i + 1; j < g.nodes.length; j++) assert.ok(!overlap(g.nodes[i], g.nodes[j]), `onboarding ${w}: ${i} and ${j}`);
});

// Phones: a three-way decision with a loop fits 362 px at narrow widths, with
// the lane label turned along the lane so it adds no width.
const three = {title: 'Escalatie', steps: [
  {id: 'm', label: 'Melding', type: 'start'}, {id: 'p', label: 'Prioriteit?', type: 'decision'}, {id: 'h', label: 'Hoog: direct bellen'},
  {id: 'mid', label: 'Midden: binnen 4 uur'}, {id: 'l', label: 'Laag: in de wachtrij'}, {id: 'x', label: 'Opgelost', type: 'end'}],
  links: ['m -> p', {from: 'p', to: 'h', label: 'Hoog'}, {from: 'p', to: 'mid', label: 'Midden'}, {from: 'p', to: 'l', label: 'Laag'},
    'h -> x', 'mid -> x', 'l -> x', {from: 'x', to: 'm', label: 'Heropend'}]};
r = build(three);
assert.deepStrictEqual(r.errors, []);
assert.deepStrictEqual(r.warnings, []);
const threeLab = r.spec.edges.map(e => e.label ? e.label.length * 6 + 11 : 0);
const threeAt = (w, gap, opt) => X.layout(r.spec, Object.assign({dir: 'down', labelW: threeLab, gapCross: gap,
  sizes: r.spec.nodes.map(n => n.type === 'decision' ? {w: Math.round(w * 1.18), h: 60} : n.type === 'start' || n.type === 'end' ? {w: 96, h: 36} : {w, h: 52})}, opt));
const g116 = threeAt(116, 16, {uprightLanes: true}), g92 = threeAt(92, 10, {uprightLanes: true, lane: 13, laneStep: 10});
assert.ok(g92.w < g116.w, 'narrower steps make a narrower drawing');
assert.ok(g92.w <= 362, 'a three-way decision fits a phone at 92 px steps: ' + g92.w);
const up = g92.edges[7].label;
assert.ok(up.upright && up.w === 16 && up.h === threeLab[7], 'the lane label is turned');
assert.ok(threeAt(116, 16, {}).w > g116.w, 'a turned lane label adds less width than a flat one');

// Link strings: ">" inside a label, chains, mermaid labels and trailing labels.
const approval = {title: 'Goedkeuring', nodes: [
  {id: 'in', label: 'Factuur binnen', type: 'start'}, {id: 'b', label: 'Bedrag > 5000?', type: 'decision'},
  {id: 'd', label: 'Directie'}, {id: 'm', label: 'Manager'}, {id: 'k', label: 'Check'}, {id: 'z', label: 'Betalen (SEPA)', type: 'end'}]};
r = build(Object.assign({}, approval, {edges: ['Factuur binnen -> Bedrag > 5000?', 'Bedrag > 5000? -> Directie: Ja', 'Bedrag > 5000? -> Manager (Nee)',
  'Directie -> Check -> Betalen (SEPA)', 'Manager -->|Akkoord| Check']}));
assert.deepStrictEqual(r.warnings, []);
const lab = e => [r.spec.nodes[e.f].label, r.spec.nodes[e.t].label, e.label];
assert.deepStrictEqual(r.spec.edges.map(lab), [
  ['Factuur binnen', 'Bedrag > 5000?', ''], ['Bedrag > 5000?', 'Directie', 'Ja'], ['Bedrag > 5000?', 'Manager', 'Nee'],
  ['Directie', 'Check', ''], ['Check', 'Betalen (SEPA)', ''], ['Manager', 'Check', 'Akkoord']]);
r = build(Object.assign({}, approval, {edges: ['Factuur binnen > Bedrag > 5000?', 'Bedrag > 5000? > Directie', 'in>m', 'Check => z']}));
assert.deepStrictEqual(r.warnings.filter(s => !s.includes('met geen enkele')), []);
assert.deepStrictEqual(r.spec.edges.map(e => [e.f, e.t]), [[0, 1], [1, 2], [0, 3], [4, 5]]);
r = build(Object.assign({}, approval, {edges: ['Check: Ja -> Nergens']}));
assert.ok(r.warnings.some(s => s.includes('onbekende stap "Check: Ja"')), 'an unknown step is named as written');

// Keys of Object.prototype are plain unknown words, never functions.
r = build({title: 'Proto', direction: 'constructor', nodes: [{id: 'a', label: 'A', type: 'constructor'}, {id: 'b', label: 'B', type: '__proto__'},
  {id: 'c', label: 'C', type: 'toString'}], edges: [{from: 'a', to: 'constructor'}, {from: 'a', to: 'b'}, {from: 'b', to: 'c'}]});
assert.deepStrictEqual(r.spec.nodes.map(n => n.type), ['step', 'step', 'step']);
assert.strictEqual(r.spec.direction, 'down');
assert.ok(r.warnings.some(s => s.includes('onbekend type "constructor"')));
assert.ok(r.warnings.some(s => s.includes('onbekend type "__proto__"')));
assert.ok(r.warnings.some(s => s.includes('Onbekende richting')));
assert.ok(r.warnings.some(s => s.includes('onbekende stap "constructor"')), 'not counted as a cut step');
assert.doesNotThrow(() => structuredClone(r.spec));
assert.strictEqual(K.kitTable('flow', r.spec).rows[0][1], 'Stap');
const longList = Array.from({length: 32}, (_, i) => ({id: 'n' + i, label: 'S' + i}));
r = build({title: 'Proto cut', nodes: longList, edges: [{from: 'n0', to: 'constructor'}, {from: 'n0', to: 'n31'}]});
assert.ok(r.warnings.some(s => s.includes('onbekende stap "constructor"')));
assert.ok(r.warnings.some(s => s.includes('1 verbinding naar een stap die niet wordt getoond')));

// A second step with the same id gets its own id, and the warning names it.
r = build({title: 'Dubbel', nodes: [{id: 'a', label: 'Eerste'}, {id: 'a', label: 'Tweede'}, {id: 'a-2', label: 'Derde'}, {id: 'z', label: 'Eind'}],
  edges: [{from: 'a', to: 'z'}, {from: 'a-3', to: 'z'}, {from: 'a-2', to: 'z'}]});
assert.ok(r.warnings.some(s => s.includes('"a" komt vaker voor; "Tweede" heet nu "a-3"')), r.warnings.join('|'));
assert.ok(r.warnings.some(s => s.includes('"a-2" komt vaker voor')) === false);
assert.deepStrictEqual(r.spec.edges.map(e => [r.spec.nodes[e.f].label, r.spec.nodes[e.t].label]), [['Eerste', 'Eind'], ['Tweede', 'Eind'], ['Derde', 'Eind']]);

// A label of a link that bends sits on its own run, clear of other lines and steps.
const escal = {title: 'Escalatie', nodes: [
  {id: 'm', label: 'Melding', type: 'start'}, {id: 'c', label: 'Compleet?', type: 'decision'}, {id: 't', label: 'Tech lead inschakelen'},
  {id: 'w', label: 'Wachten op klant', type: 'wait'}, {id: 'o', label: 'Oplossing bouwen'}, {id: 'k', label: 'Klaar', type: 'end'}],
  edges: [['m', 'c'], ['c', 't', 'Ja'], ['c', 'w', 'Nee'], ['t', 'o'], ['w', 'o', 'Info compleet'], ['o', 'k']]};
r = build(escal);
const eg = X.layout(r.spec, {dir: 'down', labelW: r.spec.edges.map(e => e.label ? e.label.length * 6 + 11 : 0),
  sizes: r.spec.nodes.map(n => n.type === 'decision' ? {w: 200, h: 70} : {w: 170, h: 46})});
const hitR = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const ic = eg.edges[4];
assert.ok(ic.label, 'labelled');
eg.nodes.forEach((b, i) => assert.ok(!hitR(ic.label, b), 'label clear of step ' + i));
eg.edges.forEach((e, j) => { if(j !== 4) segsOf(e).forEach(([a, b]) => assert.ok(!hitR(ic.label, {x: Math.min(a[0], b[0]) - 1, y: Math.min(a[1], b[1]) - 1, w: Math.abs(a[0] - b[0]) + 2, h: Math.abs(a[1] - b[1]) + 2}), 'label clear of edge ' + j)); });
const icx = ic.label.x + ic.label.w / 2, tx = eg.nodes[4].x + eg.nodes[4].w / 2, sx2 = eg.nodes[3].x + eg.nodes[3].w / 2;
assert.ok(Math.min(tx, sx2) - 1 <= icx && icx <= Math.max(tx, sx2) + 1, 'between the source and the target column');

console.log('ok');
