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
['flow', 'flowchart', 'proces', 'processchema', 'stroomschema'].forEach(f => assert.strictEqual(K.kitKind(f), 'flow', f));
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
assert.ok(r.warnings.length < 70, 'cut text is reported, but not once per edge');
const big = X.layout(r.spec, {dir: 'down', sizes: r.spec.nodes.map(() => ({w: 150, h: 50})), labelW: r.spec.edges.map(e => e.label ? 80 : 0)});
for(let i = 0; i < big.nodes.length; i++) for(let j = i + 1; j < big.nodes.length; j++)
  assert.ok(!overlap(big.nodes[i], big.nodes[j]), `big: steps ${i} and ${j} overlap`);
assert.ok(r.estHeight <= 2000);
assert.strictEqual(build('{"title":"x","nodes":[]}'.padEnd(210 * 1024, ' ')).errors.length, 1, 'too big');

console.log('ok');
