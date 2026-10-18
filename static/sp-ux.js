/* Small SynthPulse UX helpers shared by several panels. */
(function (root) {
  'use strict';
  // First-run empty state: when a list has nothing yet, swap "Select a X" for
  // "No X yet. Create your first X" with one line of explanation and a button.
  function spSetFirstRun(emptyId, isEmpty) {
    const box = root.document && root.document.getElementById(emptyId);
    if (!box) return;
    if (isEmpty) box.setAttribute('data-sp-first', '1');
    else box.removeAttribute('data-sp-first');
    const first = box.querySelector('.sp-empty-first');
    if (first) first.hidden = !isEmpty;
  }
  root.spSetFirstRun = spSetFirstRun;
})(typeof window !== 'undefined' ? window : globalThis);
(function (root) {
  'use strict';
  // The built-in profile is called "default" internally; people see "Standaardbot".
  function spProfileLabel(name) {
    const raw = String(name || '');
    if (raw !== 'default') return raw;
    return typeof root.spT === 'function' ? root.spT('profile_default_display', 'Standard bot') : 'Standard bot';
  }
  root.spProfileLabel = spProfileLabel;
})(typeof window !== 'undefined' ? window : globalThis);
(function (root) {
  'use strict';
  // Chip labels are written as the raw profile id in several places; show the
  // friendly name for the built-in "default" bot without touching those writers.
  function watch(id) {
    const el = root.document && root.document.getElementById(id);
    if (!el || el._spWatched) return;
    el._spWatched = true;
    const fix = () => {
      if (el.textContent === 'default') {
        const label = root.spProfileLabel('default');
        if (label && label !== 'default') el.textContent = label;
      }
    };
    new MutationObserver(fix).observe(el, {childList: true, characterData: true, subtree: true});
    fix();
  }
  function start() { ['profileChipLabel', 'titlebarProfileLabel'].forEach(watch); }
  if (root.document) {
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', start);
    else start();
  }
})(typeof window !== 'undefined' ? window : globalThis);
