# Vendored: memory dashboard single-page app

Served by the WebUI as the Memory explorer frame (plan addendum 6.6.4). The
frame runs with `Content-Security-Policy: sandbox allow-scripts` and
`connect-src 'none'`: an opaque origin without cookies, storage or network.

| Item | Value |
|------|-------|
| Repository | https://github.com/wysie/mnemosyne-dashboard |
| Commit | `a918e5e0841fdc85baad7ab582432b2b7499b2f2` |
| Version | 0.14.0 |
| Licence | MIT, the upstream contributors (`LICENSE`, unmodified) |
| three.js | r160, MIT, Copyright 2010-2023 Three.js Authors (notice below) |
| Rebuild | `python3 scripts/memdash_vendor.py` (`--check` fails on any drift) |

## Files taken

| File | Treatment | Upstream sha256 |
|------|-----------|-----------------|
| `static/index.html` | rewritten from `tests/fixtures/memdash_upstream/a918e5e/index.html` | `e0960c649d97db0e78c0aec1f8300086a650d2e653baaaa6e94d3a4e004820b5` |
| `static/app.js` | rewritten from `tests/fixtures/memdash_upstream/a918e5e/app.js` | `6be2877b01619d8f10f086a791e54a4d1897ae6ea2544291191eaa681e969dbb` |
| `static/style.css` | unmodified | `db7f345589a048b6a11e6a92db3b0e6861cd95725887b5bce5ab5642c58f5db8` |
| `static/favicon.svg` | unmodified (not linked) | `2dbcbd5abf1b70bcfcaec92f641f40c7fad0da3112515ca6d8397fb1c248e4eb` |
| `static/vendor/three.module.min.js` | unmodified | `3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6` |
| `LICENSE` | unmodified | `d89209ee7aa7ceae54947726a9ab95d0e2fb679e975c52490394c2bf3e8c1f87` |
| `dashboard_core.py` | unmodified, in `api/third_party/mnemosyne_dashboard/`, hardened at import by `patches.py` (reader child only) | `836cd334bf7f26b45e886c92c60362092163ba0211cb0df553ba8d43c7e871b7` |

Our own files here: `memdash-shim.js` (the fetch, storage and EventSource
shim), `memdash-overrides.css` (hidden settings, login and footer, the system
font stack, the light-theme stat number fix) and this file.

## Files not taken

`server.py`, `config.py` and the plugin `__init__.py` (agent tools that accept
a host, a database path and a password), `plugin.yaml`, `brand-fonts.css` and
every font file, the tests, scripts and screenshots. The explorer therefore has
no second listener, no `0.0.0.0` bind and no configuration route. The upstream
write methods, full-database backups and content audit log are never used
(`patches.py` makes them raise).

## Rewrite table (summary; the exact rules and match counts are in the script)

| File | Rule |
|------|------|
| `index.html` | title "Memory explorer"; no favicon and font links; `style.css`, then `memdash-overrides.css`, and `memdash-shim.js` before `app.js`, all relative with a content hash; footer credit links removed; brand, labyrinth, structured memory and settings copy without internal product names; "Expire selected" becomes "Forget selected"; no em or en dash |
| `app.js` | `localStorage` becomes `__mdStore` (4); the three.js import becomes `import('./vendor/three.module.min.js')`; pattern provider label, graph empty state and labyrinth copy without internal product names; "Expire ..." becomes "Forget ..."; "Backups and audit entries will be created." becomes "This is recorded."; the Settings hint becomes the read-only note; no em or en dash |

`fetch` and `EventSource` stay untouched in `app.js`; the shim handles them.

## three.js licence

The MIT License

Copyright 2010-2023 Three.js Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
