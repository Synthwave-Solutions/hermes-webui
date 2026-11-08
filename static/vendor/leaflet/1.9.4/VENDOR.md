# Leaflet 1.9.4

Source: https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js, https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css and https://cdn.jsdelivr.net/npm/leaflet@1.9.4/LICENSE (npm package `leaflet@1.9.4`, archive integrity `sha512-nxS1ynzJOmOlHp+iL3FyWqK89GtNL8U8rvlMOsQdTTssxZwCXh8N2NB3GDQOL+YR3XnWyZAxwQixURb+FA74PA==`).

| File | sha256 |
| --- | --- |
| `leaflet.js` | `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a` |
| `leaflet.css` | `a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6` |
| `LICENSE` (BSD-2-Clause) | `53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb` |

All files are unmodified (the hashes match the jsDelivr file list for this version); `leaflet.js` keeps its license header. Only the data block frame uses it: `api/interactive_ui.py` inlines the script and the stylesheet into `static/interactive-ui/kit.html` and allows the script by its sha256 in that frame's CSP. The default marker images are not vendored (the map uses its own numbered pins). Nothing is loaded from a CDN at run time. `tests/test_interactive_ui.py` checks the hashes above.
