# guida.js 0.2.0

Source: https://registry.npmjs.org/guida.js/-/guida.js-0.2.0.tgz

Npm archive integrity: `sha512-pErltqXtFQwVVeBbzASZ3L5TyZRh9GY1AqcG9KP4EGvxLQIreg6Dfa64x7sf+fx+maQn4KqsuWk4YIGt6wRmEg==` (shasum `14cef71d961fb5e0875e5e64d0fd0fce89334873`).

`guida.umd.js` is the unmodified `dist/index.js` of that archive (UMD build, global `SpotlightOnboarding`), sha256 `f59fc2684a1b8d9c2e85d065d2462a3dcb971a9e177fbf71236adae8fcc20e69`. `LICENSE` (MIT) and `package.json` are the upstream files from the same archive. No install scripts were executed and nothing is loaded from a CDN.

Only `static/help-tour.js` calls this library. It escapes titles and descriptions before they reach it (the library writes them with `innerHTML`), relabels its buttons from the WebUI locale, adds dialog roles, keyboard support and focus handling, keeps its completion flag in wrapped storage calls, and hides its own completion card. Theme overrides live in `static/help-tour.css`.
