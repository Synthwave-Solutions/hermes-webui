// Checks for the questions form (```form, ```vraag, ```vragen, ```questions)
// in static/interactive_ui.js, run by tests/test_interactive_ui.py.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(ROOT, 'static', 'interactive_ui.js'), 'utf8');
const sandbox = {
  window: { addEventListener: () => {}, innerHeight: 900 },
  document: { addEventListener: () => {}, documentElement: { lang: 'nl', classList: { contains: () => false } } },
  navigator: { language: 'nl-NL' },
  URL, console, setTimeout, clearTimeout, Map, Set, Intl,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'static', 'interactive-ui', 'kit-core.js'), 'utf8'), sandbox);
vm.runInContext(src + '\nthis.__api={accepts:interactiveUiFenceAccepts,iui:_iui};', sandbox);
const { accepts, iui } = sandbox.__api;
const plain = v => JSON.parse(JSON.stringify(v));
const build = (text, opts) => plain(iui.formSpec(typeof text === 'string' ? text : JSON.stringify(text), opts || {}));

// ── Fences: JSON only ───────────────────────────────────────────────────────
for (const f of ['form', 'vraag', 'vragen', 'questions', 'Form']) {
  assert.strictEqual(accepts(f, '{"fields":[{"label":"Budget"}]}'), true, f);
}
assert.strictEqual(accepts('form', '[{"label":"Budget"}]'), true, 'a bare list of questions');
assert.strictEqual(accepts('form', '<form><input name="x"></form>'), false, 'an HTML form stays code');
assert.strictEqual(accepts('questions', '1. Wat is je budget?\n2. Wanneer start je?'), false, 'a text list stays text');
assert.strictEqual(accepts('form', '   '), false);
assert.ok(iui.FORM_LANGS.has('vraag') && !iui.FORM_LANGS.has('table'));

// ── A clean spec ────────────────────────────────────────────────────────────
const SPEC = {
  title: 'Uitrol Junior AI', lang: 'nl', intro: 'Dan maak ik de planning op maat.',
  fields: [
    { id: 'budget', label: 'Budget', type: 'number', unit: '€ per maand', min: 500, max: 50000, required: true },
    { id: 'start', label: 'Start', type: 'date', min: '2026-11-09' },
    { id: 'teams', label: 'Welke teams doen mee?', type: 'multi', options: ['Sales', 'Finance', 'Operations'], required: true },
    { id: 'tempo', label: 'Tempo', type: 'choice', options: ['Rustig', 'Normaal', 'Snel'], default: 'Normaal' },
    { id: 'uren', label: 'Uren per week', type: 'slider', min: 0, max: 20, unit: 'uur' },
    { id: 'pilot', label: 'Eerst een pilot?', type: 'yesno' },
    { id: 'wensen', label: 'Nog iets?', type: 'text', placeholder: 'Optioneel' },
  ],
};
const ok = build(SPEC);
assert.deepStrictEqual(ok.errors, []);
assert.deepStrictEqual(ok.warnings, []);
assert.strictEqual(ok.spec.title, 'Uitrol Junior AI');
assert.strictEqual(ok.spec.submit, 'Versturen');
assert.deepStrictEqual(ok.spec.fields.map(f => f.type), ['number', 'date', 'multi', 'choice', 'slider', 'yesno', 'text']);
assert.strictEqual(ok.spec.fields[4].step, 1, 'a small whole-number slider moves in steps of 1');
assert.strictEqual(ok.spec.fields[3].default, 'Normaal');
assert.strictEqual(build(Object.assign({}, SPEC, { lang: 'en' })).spec.submit, 'Send');

// ── The message sent as the user's reply ────────────────────────────────────
const year = new Date().getFullYear();
const msg = plain(iui.formMessage(ok.spec, {
  budget: 5000, start: `${year}-12-01`, teams: ['Operations', 'Sales'], tempo: 'Snel', uren: 7, pilot: true, wensen: 'Vooral de training.',
}));
assert.strictEqual(msg.text, [
  'Mijn antwoorden:',
  '- Budget: € 5.000 per maand',
  '- Start: 1 december',
  '- Welke teams doen mee? Sales en Operations',
  '- Tempo: Snel',
  '- Uren per week: 7 uur',
  '- Eerst een pilot? Ja',
  '- Nog iets? Vooral de training.',
].join('\n'));
assert.strictEqual(msg.display.budget, '€ 5.000 per maand');
assert.ok(!/[\u2013\u2014]/.test(msg.text), 'no long dashes in the message');
assert.ok(!/"|\{|budget|multi|slider|yesno/.test(msg.text.replace('Budget', '')), 'nothing technical in the message');
// Another year is written out; unanswered questions are left out; one answer is singular.
const one = plain(iui.formMessage(ok.spec, { start: '2031-03-05', pilot: false, teams: [], wensen: '  ' }));
assert.strictEqual(one.text, 'Mijn antwoorden:\n- Start: 5 maart 2031\n- Eerst een pilot? Nee');
assert.strictEqual(plain(iui.formMessage(ok.spec, { pilot: false })).text, 'Mijn antwoord:\n- Eerst een pilot? Nee');
assert.strictEqual(plain(iui.formMessage(ok.spec, {})).text, '', 'no answers, no message');
// English
const en = build({ lang: 'en', fields: [{ label: 'Budget', type: 'number', unit: 'EUR' }, { label: 'Teams', type: 'multi', options: ['A', 'B', 'C'] }, { label: 'Pilot first?', type: 'yesno' }] });
assert.strictEqual(en.spec.title, 'A few questions');
assert.strictEqual(plain(iui.formMessage(en.spec, { budget: 1250.5, teams: ['C', 'A', 'B'], 'pilot-first': true })).text,
  'My answers:\n- Budget: € 1,250.50\n- Teams: A, B and C\n- Pilot first? Yes');
// Read back from the sent message (a reload in another tab).
assert.deepStrictEqual(plain(iui.formAnswersFrom(ok.spec, msg.text)), msg.display);
assert.deepStrictEqual(plain(iui.formAnswersFrom(ok.spec, 'Gewoon een ander bericht')), {});

// ── Checks on submit ────────────────────────────────────────────────────────
const F = Object.fromEntries(ok.spec.fields.map(f => [f.id, f]));
const check = (id, v) => plain(iui.formCheck(F[id], v, 'nl'));
assert.deepStrictEqual(check('budget', ''), { error: 'Vul dit nog in.' });
assert.deepStrictEqual(check('budget', '5.000'), { value: 5000 }, 'Dutch thousands');
assert.deepStrictEqual(check('budget', '€ 7.500,50'), { value: 7500.5 });
assert.deepStrictEqual(check('budget', 'veel'), { error: 'Vul een getal in, bijvoorbeeld 1.500.' });
assert.deepStrictEqual(check('budget', '100'), { error: 'Kies een getal van € 500 per maand tot en met € 50.000 per maand.' });
assert.deepStrictEqual(check('teams', []), { error: 'Kies een antwoord.' });
assert.deepStrictEqual(check('tempo', null), { value: null }, 'optional and empty is fine');
assert.deepStrictEqual(check('start', '2026-11-01'), { error: 'Kies 9 november of later.'.replace('november', 'november' + (year === 2026 ? '' : ' 2026')) });
assert.deepStrictEqual(check('start', 'morgen'), { error: 'Kies een datum, bijvoorbeeld 1-12-2026.' });
assert.deepStrictEqual(check('wensen', 'a\n\n- Budget: 0'), { value: 'a - Budget: 0' }, 'an answer cannot add lines of its own');
assert.strictEqual(check('wensen', 'x'.repeat(900)).value.length, 500);

// ── Amounts with cents and fractional steps never break the formatter ────
// Intl throws when the minimum decimals exceed the maximum; a typed 7.500,50
// under a whole-euro step used to make Versturen do nothing.
const euro = build({ lang: 'nl', fields: [
  { id: 'budget', label: 'Budget', type: 'number', unit: '€ per maand', step: 1 },
  { id: 'prijs', label: 'Prijs', type: 'slider', unit: '€', min: 0, max: 5, step: 0.5 },
  { id: 'honderd', label: 'Per honderd', type: 'number', unit: '€', step: 100 },
  { id: 'kwart', label: 'Kwart', type: 'slider', min: 0, max: 1, step: 0.25 },
] }).spec;
const E = Object.fromEntries(euro.fields.map(f => [f.id, f]));
const typed = plain(iui.formCheck(E.budget, '7.500,50', 'nl'));
assert.deepStrictEqual(typed, { value: 7500.5 });
assert.strictEqual(plain(iui.formMessage(euro, { budget: typed.value })).text, 'Mijn antwoord:\n- Budget: € 7.500,50 per maand', 'cents are kept as typed');
assert.strictEqual(iui.formNumberText(2.5, E.prijs, 'nl'), '€ 2,50');
assert.strictEqual(iui.formNumberText(2, E.prijs, 'nl'), '€ 2');
assert.strictEqual(iui.formNumberText(0, E.prijs, 'nl'), '€ 0');
assert.strictEqual(iui.formNumberText(1250.5, E.honderd, 'nl'), '€ 1.250,50');
assert.strictEqual(iui.formNumberText(0.25, E.kwart, 'nl'), '0,25');
assert.strictEqual(iui.formNumberText(0.1 + 0.2, E.kwart, 'nl'), '0,3', 'float noise is not shown');
assert.strictEqual(iui.formNumberText(2.5, E.prijs, 'en'), '€ 2.50');
assert.strictEqual(plain(iui.formMessage(euro, { prijs: 2.5, kwart: 0.75 })).text, 'Mijn antwoorden:\n- Prijs: € 2,50\n- Kwart: 0,75');

// ── English numbers: comma for thousands, dot for decimals ─────────────────
const enNum = build({ lang: 'en', fields: [{ id: 'budget', label: 'Budget', type: 'number', unit: '€', min: 500 }] }).spec.fields[0];
const enCheck = v => plain(iui.formCheck(enNum, v, 'en'));
assert.deepStrictEqual(enCheck('1,500'), { value: 1500 }, 'the example in the hint is accepted as written');
assert.deepStrictEqual(enCheck('€1,500.75'), { value: 1500.75 });
assert.deepStrictEqual(enCheck('12,345,678'), { value: 12345678 });
assert.deepStrictEqual(enCheck('2500.5'), { value: 2500.5 });
assert.deepStrictEqual(enCheck('750,5'), { value: 750.5 }, 'a lone decimal comma still works');
assert.deepStrictEqual(enCheck('1.500'), { error: 'Choose € 500 or more.' }, '1.500 is one and a half in English');
assert.deepStrictEqual(enCheck('lots'), { error: 'Enter a number, for example 1,500.' });
assert.deepStrictEqual(enCheck('1,50,0'), { error: 'Enter a number, for example 1,500.' });
assert.deepStrictEqual(check('budget', '1.500'), { value: 1500 }, 'Dutch stays Dutch');

// ── Dates typed the Dutch way, day first ───────────────────────────────────
const NOW = { now: new Date('2026-11-08T12:00:00Z') };
const pd = (v, o) => iui.formDateParse(v, Object.assign({}, NOW, o || {}));
assert.strictEqual(pd('2026-12-01'), '2026-12-01');
assert.strictEqual(pd('1-12-2026'), '2026-12-01');
assert.strictEqual(pd('01/12/2026'), '2026-12-01');
assert.strictEqual(pd('1.12.26'), '2026-12-01');
assert.strictEqual(pd('1 december'), '2026-12-01');
assert.strictEqual(pd('1 dec 2026'), '2026-12-01');
assert.strictEqual(pd('1e december'), '2026-12-01');
assert.strictEqual(pd('3 mrt. 2027'), '2027-03-03');
assert.strictEqual(pd('December 1, 2026'), '2026-12-01');
assert.strictEqual(pd('1/12'), '2026-12-01', 'no year: this year');
assert.strictEqual(pd('15-1', { min: '2026-11-09' }), '2027-01-15', 'no year and before the earliest date: next year');
assert.strictEqual(pd('31-2-2026'), '', 'an impossible date');
assert.strictEqual(pd('12/31/2026'), '', 'month first is not a date here');
assert.strictEqual(pd('morgen'), '');
assert.strictEqual(iui.formDateInput('2026-12-01', 'nl'), '01-12-2026');
assert.strictEqual(iui.formDateInput('2026-12-01', 'en'), '01/12/2026');
assert.strictEqual(iui.formDateEcho('2026-12-01', 'nl'), 'dinsdag 1 december 2026');
assert.ok(/^Tuesday,? 1 December 2026$/.test(iui.formDateEcho('2026-12-01', 'en')));
assert.deepStrictEqual(plain(iui.formCheck(F.start, '1-12-2026', 'nl')), { value: '2026-12-01' });
assert.deepStrictEqual(plain(iui.formCheck(F.start, '1 november 2026', 'nl')), { error: 'Kies 9 november' + (year === 2026 ? '' : ' 2026') + ' of later.' });
assert.strictEqual(build({ fields: [{ label: 'Start', type: 'date', min: '2026-01-01' }] }).spec.fields[0].min, '2026-01-01');

// ── A messy spec: fixed where possible ──────────────────────────────────────
const messy = build(`// written by the model
{"title":"Intake","lang":"nl","fields":[
  "Wat is de bedrijfsnaam?",
  {"label":"Sector","type":"dropdown","options":["Bouw","Zorg","Zorg",{"label":"Overheid","value":"gov"},"a","b","c","d","e","f","g","h","i","j"],"default":"gov"},
  {"label":"Medewerkers","type":"getal","min":"1.000","max":10,"default":"veel"},
  {"type":"text"},
  {"label":"Tevredenheid","type":"schaal"},
  {"label":"Kanalen","type":"multi","options":["Alleen e-mail"]},
  {"label":"Akkoord","type":"ja-nee","default":"ja","required":"ja"},
  {"label":"Startdatum","type":"datum","default":"2026-02-30"},
  {"label":"Extra"},
],}`);
assert.deepStrictEqual(messy.errors, []);
const mf = messy.spec.fields;
assert.deepStrictEqual(mf.map(f => f.label), ['Wat is de bedrijfsnaam?', 'Sector', 'Medewerkers', 'Tevredenheid', 'Kanalen', 'Akkoord', 'Startdatum']);
assert.deepStrictEqual(mf.map(f => f.type), ['text', 'choice', 'number', 'slider', 'text', 'yesno', 'date']);
assert.strictEqual(mf[1].options.length, 12, 'at most 12 options');
assert.strictEqual(mf[1].default, 'Overheid', 'a default may name the option value');
assert.deepStrictEqual([mf[2].min, mf[2].max, mf[2].default], [10, 1000, undefined], 'min and max swapped, a bad default dropped');
assert.deepStrictEqual([mf[3].min, mf[3].max], [0, 10], 'a slider without range gets 0 to 10');
assert.strictEqual(mf[5].required, true);
assert.strictEqual(mf[5].default, true);
assert.strictEqual(mf[6].default, undefined, 'an impossible date is dropped');
assert.strictEqual(new Set(mf.map(f => f.id)).size, mf.length, 'ids are unique');
for (const w of ['9 vragen', 'dubbele optie', 'omgedraaid', 'geen "label"', 'open vraag', '0 tot en met 10']) {
  assert.ok(messy.warnings.some(x => x.includes(w)), `warning about ${w}: ${messy.warnings.join(' | ')}`);
}
// Too many fields, labels too long, a bare list, a single question at the top level.
const many = build({ fields: Array.from({ length: 12 }, (_, i) => ({ label: 'Vraag ' + (i + 1) + ' ' + 'x'.repeat(i ? 0 : 200) })) });
assert.strictEqual(many.spec.fields.length, 8);
assert.ok(many.spec.fields[0].label.length <= 80 && many.spec.fields[0].label.endsWith('…'));
assert.strictEqual(build([{ label: 'Budget', type: 'number' }]).spec.fields[0].type, 'number');
const single = build({ label: 'Wanneer wil je starten?', type: 'date' });
assert.strictEqual(single.spec.fields.length, 1);
assert.strictEqual(single.spec.title, 'Een vraag');
// A single question with only a title, and questions as a map with ids as keys.
const titled = build({ title: 'Wat is je budget?', type: 'number', unit: '€' });
assert.deepStrictEqual(titled.errors, []);
assert.deepStrictEqual([titled.spec.fields[0].label, titled.spec.fields[0].type, titled.spec.title], ['Wat is je budget?', 'number', 'Een vraag']);
assert.deepStrictEqual(build({ title: 'Kies', options: ['A', 'B'] }).spec.fields[0].type, 'choice');
assert.deepStrictEqual(build({ title: 'Alleen een titel' }).errors, ['Er staan geen vragen in de lijst "fields".'], 'a title alone is no question');
const mapped = build({ title: 'Intake', fields: { budget: { label: 'Budget', type: 'number' }, start: { type: 'date', question: 'Wanneer?' }, team: 'Welk team?' } });
assert.deepStrictEqual(mapped.errors, []);
assert.deepStrictEqual(mapped.spec.fields.map(f => [f.id, f.label, f.type]), [['budget', 'Budget', 'number'], ['start', 'Wanneer?', 'date'], ['team', 'Welk team?', 'text']]);
assert.strictEqual(mapped.spec.title, 'Intake');
// Ids that collide or hold odd characters.
const ids = build({ fields: [{ id: 'a b', label: 'A' }, { id: 'a-b', label: 'B' }, { label: 'Één keer' }] }).spec.fields.map(f => f.id);
assert.deepStrictEqual(ids, ['a-b', 'a-b-2', 'een-keer']);
// Format and control characters are removed from what the user sees.
assert.strictEqual(build({ fields: [{ label: 'Bud‮get\u0007' }] }).spec.fields[0].label, 'Budget');

// ── Nothing to draw: one plain error for the repair prompt ─────────────────
assert.deepStrictEqual(build('{"title":"x", "fields": [ {"label": "x" }').errors, ['De vragen zijn geen geldige JSON (regel 1).']);
assert.deepStrictEqual(build('"tekst"').errors, ['De vragen moeten één JSON-object zijn met een lijst "fields".']);
assert.deepStrictEqual(build({ title: 'Leeg', fields: [] }).errors, ['Er staan geen vragen in de lijst "fields".']);
assert.deepStrictEqual(build({ fields: [{ type: 'text' }, 7] }).errors, ['Geen enkele vraag is bruikbaar: elke vraag heeft een "label" nodig.']);
assert.deepStrictEqual(build({ lang: 'en', fields: [] }).errors, ['There are no questions in the "fields" list.']);
assert.strictEqual(build('{"fields":[' + '{"label":"x"},'.repeat(6000) + '{"label":"y"}]}').errors.length, 1, 'too big');

// ── The host builds the form with textContent only ─────────────────────────
const section = src.slice(src.indexOf('// ── Questions form'), src.indexOf('// A reply that names a bot'));
assert.ok(section.length > 1000);
const inner = section.match(/innerHTML\s*=[^;]*/g) || [];
assert.deepStrictEqual(inner, ['innerHTML=icon(name)'], 'only fixed icons are set as HTML');
assert.ok(!/insertAdjacentHTML|outerHTML|document\.write/.test(section));
assert.ok(section.includes("if(!ev||!ev.isTrusted||card.classList.contains('is-locked')"), 'only a real click sends');
assert.ok(section.includes('sendPrompt(out.text'), 'the same safe send path as the chips');
assert.ok(!/type=f\.type==='date'\?'date'/.test(section), 'no browser date box: its format follows the browser language');
assert.ok(section.includes(".msg-row:not(.msg-row-btw):not([data-btw])"), 'a /btw side question is not a newer message');
const css = fs.readFileSync(path.join(ROOT, 'static', 'interactive_ui.css'), 'utf8');
assert.ok(!/:has\(~ \.msg-row\)/.test(css), 'the CSS ignores /btw rows too');

console.log('all form checks passed');
