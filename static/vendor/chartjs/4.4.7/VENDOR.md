# Chart.js 4.4.7

Source: https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.js and https://cdn.jsdelivr.net/npm/chart.js@4.4.7/LICENSE.md (npm package `chart.js@4.4.7`, archive integrity `sha512-pwkcKfdzTMAU/+jNosKhNL2bHtJc/sSmYgVbuGTEDhzkrhmyihmP7vUc/5ZK9WopidMDHNe3Wm7jOd/WhuHWuw==`).

| File | sha256 |
| --- | --- |
| `chart.umd.js` | `2812cb8825fdc57469eb2f7bb055e9429244e599920511ee477e828499b632cb` |
| `LICENSE.md` (MIT) | `41a84aa2caba645f966a18d9c2056b73e6d3a81d80bc0046bc0011a2634d4cce` |

Both files are unmodified (the hashes match the jsDelivr file list for this version); `chart.umd.js` keeps its MIT header. Only the data block frame uses it: `api/interactive_ui.py` inlines it into `static/interactive-ui/kit.html` and allows it by its sha256 in that frame's CSP. Nothing is loaded from a CDN at run time. `tests/test_interactive_ui.py` checks the hashes above.
