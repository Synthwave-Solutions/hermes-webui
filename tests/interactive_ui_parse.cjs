// Parser checks for static/interactive_ui.js, run by tests/test_interactive_ui.py.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'interactive_ui.js'), 'utf8');
const listeners = [];
const sandbox = {
  window: { addEventListener: (t, f) => listeners.push([t, f]), innerHeight: 900 },
  document: { addEventListener: () => {}, documentElement: { lang: 'nl', classList: { contains: () => false } } },
  navigator: { language: 'nl-NL' },
  URL, console, setTimeout, clearTimeout, Map, Set,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src + '\nthis.__api={parse:parseInteractiveUiSource,accepts:interactiveUiFenceAccepts,iui:_iui};', sandbox);
const { parse, accepts, iui } = sandbox.__api;

// Fence detection
assert.strictEqual(accepts('interactive-ui', '<div></div>'), true);
assert.strictEqual(accepts('Interactive-UI', '<div></div>'), true);
assert.strictEqual(accepts('html', '<div></div>'), false);
assert.strictEqual(accepts('interactive-ui', '   '), false);
assert.strictEqual(accepts('suggestions', 'Ja graag'), true);
assert.strictEqual(accepts('replies', 'Ja graag'), true);

// Reply chips: at most three short lines, bullets and quotes removed, slashes stripped
assert.deepStrictEqual(JSON.parse(JSON.stringify(iui.chipTexts('- Werk scenario B uit\n2. "Maak een grafiek"\n\n/yolo doe alles\nVierde regel'))),
  ['Werk scenario B uit', 'Maak een grafiek', 'yolo doe alles']);
assert.deepStrictEqual(JSON.parse(JSON.stringify(iui.chipTexts('x'.repeat(200)))), []);
assert.deepStrictEqual(JSON.parse(JSON.stringify(iui.chipTexts('\u202eabc\n\u2060/yo'))), ['abc', 'yo'], 'format characters are removed');
const strip = vm.runInContext('stripReplySuggestions', sandbox);
assert.strictEqual(strip('Antwoord.\n\n```suggestions\nJa\nNee\n```'), 'Antwoord.');
assert.strictEqual(strip('Code:\n```js\nx\n```'), 'Code:\n```js\nx\n```');

// Full block
const full = parse(`<!-- title: ROI calculator -->
<!-- height: 480 -->
<!doctype html><html><head><title>Ignored</title><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://evil.example/x.css">
<style>.a{color:red}</style></head><body>
<div class="a">Hallo</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://evil.example/steal.js"></script>
<script>window.x=1;</script>
<script type="module">import * as THREE from 'three';</script>
<script type="application/json" id="data">{"a":1}</script>
</body></html>`, { final: true });
assert.strictEqual(full.title, 'ROI calculator');
assert.strictEqual(full.height, 480);
assert.ok(full.css.startsWith('@import url("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");'), full.css);
assert.ok(full.css.includes('.a{color:red}'));
assert.ok(!full.css.includes('evil'));
assert.ok(full.html.includes('<div class="a">Hallo</div>'));
assert.ok(full.html.includes('<script type="application/json" id="data">{"a":1}</script>'), full.html);
assert.ok(!/<(html|head|body|meta|title|link|style)\b/i.test(full.html), full.html);
assert.deepStrictEqual(JSON.parse(JSON.stringify(full.scripts)), [
  { src: 'https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js', type: '' },
  { code: 'window.x=1;', type: '' },
  { code: "import * as THREE from 'three';", type: 'module' },
]);
assert.strictEqual(full.warnings.length, 2);

// Title falls back to <title>, height is clamped
const t = parse('<title>Plan <b>B</b></title><!-- height: 99999 --><p>x</p>', { final: true });
assert.strictEqual(t.title, 'Plan B');
assert.strictEqual(t.height, 2000);
assert.strictEqual(parse('<!-- height: 5 --><p>x</p>', { final: true }).height, 80);

// Streaming: unfinished style applies, unfinished script and half tags are left out
const s1 = parse('<style>.card{color:blue}\n.b{', { final: false });
assert.ok(s1.css.includes('.card{color:blue}'));
assert.strictEqual(s1.html, '');
const s2 = parse('<style>.x{}</style><div class="card">Hoi</div><div cla', { final: false });
assert.strictEqual(s2.html, '<div class="card">Hoi</div>');
const s3 = parse('<style>.x{}</style><p>Klaar</p><script>let a = 1; doSomething(', { final: false });
assert.strictEqual(s3.html, '<p>Klaar</p>');
assert.strictEqual(s3.scripts.length, 0);
const s4 = parse('<p>a</p><script>var q=1;</script><p>b</p>', { final: false });
assert.strictEqual(s4.scripts.length, 1, 'complete scripts are collected but only sent on final');
assert.ok(!s4.html.includes('script'));

// Size limit
const big = parse('x'.repeat(201 * 1024), { final: true });
assert.strictEqual(big.tooBig, true);

// URL allowlist
assert.strictEqual(iui.allowedUrl('https://esm.sh/three'), 'https://esm.sh/three');
assert.strictEqual(iui.allowedUrl('http://cdn.jsdelivr.net/x.js'), null);
assert.strictEqual(iui.allowedUrl('https://cdn.jsdelivr.net.evil.example/x.js'), null);
assert.strictEqual(iui.allowedUrl('//unpkg.com/x.js'), 'https://unpkg.com/x.js');
assert.strictEqual(iui.allowedUrl('javascript:alert(1)'), null);

// Templates from the skill parse cleanly with only allowed sources
const tplDir = process.env.IUI_TEMPLATES;
if (tplDir && fs.existsSync(tplDir)) {
  for (const name of fs.readdirSync(tplDir).filter(n => n.endsWith('.html'))) {
    const p = parse(fs.readFileSync(path.join(tplDir, name), 'utf8'), { final: true });
    assert.ok(p.title, name + ' has a title');
    assert.ok(p.height > 0, name + ' has a height');
    assert.strictEqual(p.warnings.length, 0, name + ' uses only allowed sources');
    assert.ok(p.scripts.length > 0, name + ' has behaviour');
    assert.ok(p.bytes < 40 * 1024, name + ' stays under 40 KB');
  }
}

// A reply that is an app without its fence is wrapped; ordinary text is not.
const wrapBare = vm.runInContext('interactiveUiWrapBare', sandbox);
assert.ok(wrapBare('<!-- title: X -->\n<style>.a{}</style>\n<div>hoi</div>\n<script>var a=1;</script>\n\nUitleg.').startsWith('```interactive-ui\n<!-- title: X -->'));
assert.ok(wrapBare('<!-- title: X -->\n<style>.a{}</style>\n<div>hoi</div>\n\nUitleg.').includes('```\n\n\nUitleg.'));
assert.strictEqual(wrapBare('Gewoon tekst <!-- title: x --> <style>'), 'Gewoon tekst <!-- title: x --> <style>');
assert.strictEqual(wrapBare('<!-- title: alleen een titel -->\nTekst'), '<!-- title: alleen een titel -->\nTekst');
console.log('all parser checks passed');
