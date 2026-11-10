// Premium layer behaviour (10 Nov 2026).
//
// Two small things the stylesheet cannot do alone:
//   1. the project filter in the chat sidebar folds to four rows once the
//      list of projects gets long, with one quiet control to show all;
//   2. a team form marks itself as changed, so the save button only asks for
//      attention when there is something to save.
// Everything here works through delegated listeners and data attributes.
(function(){
  'use strict';
  const OPEN_KEY = 'sp-project-bar-open';
  const ROWS = 4, MIN_CHIPS = 10;
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const TEXT = {
    nl: { more: n => `Alle ${n} projecten tonen`, less: 'Minder projecten tonen', all: 'Alles', none: 'Zonder project', none_title: 'Gesprekken die nog niet bij een project horen' },
    en: { more: n => `Show all ${n} projects`, less: 'Show fewer projects', all: 'All', none: 'Unassigned', none_title: 'Show conversations not yet assigned to a project' }
  };
  const isOpen = () => { try { return localStorage.getItem(OPEN_KEY) === '1'; } catch (_e) { return false; } };

  const projectCount = bar => Math.max(0, bar.querySelectorAll('.project-chip:not(.no-project)').length - 1);

  function localise(bar){
    const text = TEXT[lang()];
    const first = bar.querySelector('.project-chip');
    if (first && first.childElementCount === 0 && first.textContent === 'All') first.textContent = text.all;
    const none = bar.querySelector('.project-chip.no-project');
    if (none) { none.textContent = text.none; none.title = text.none_title; }
  }

  function foldProjectBars(){
    document.querySelectorAll('.project-bar:not([data-sp-clamp])').forEach(bar => {
      bar.dataset.spClamp = 'off';
      localise(bar);
      const chips = bar.querySelectorAll('.project-chip');
      if (chips.length < MIN_CHIPS) return;
      // A collapsed section has no height yet: measure again once it opens.
      if (!chips[0].offsetHeight) { delete bar.dataset.spClamp; return; }
      const gap = parseFloat(getComputedStyle(bar).rowGap) || 4;
      const top = parseFloat(getComputedStyle(bar).paddingTop) || 0;
      const limit = Math.round(top + ROWS * chips[0].offsetHeight + (ROWS - 1) * gap + 2);
      if (bar.scrollHeight <= limit + chips[0].offsetHeight) return;
      // Never hide the project that is filtering the list right now.
      const active = bar.querySelector('.project-chip.active');
      const activeHidden = !!active && (active.offsetTop - bar.offsetTop) >= limit;
      const open = isOpen() || activeHidden;
      // The "new project" button stays in reach while the list is folded.
      const create = bar.querySelector('.project-create-btn');
      if (create && chips[1]) bar.insertBefore(create, chips[1]);
      bar.style.setProperty('--sp-clamp', limit + 'px');
      bar.dataset.spClamp = open ? 'open' : 'closed';
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'project-bar-more';
      toggle.dataset.spProjectMore = '1';
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.textContent = open ? TEXT[lang()].less : TEXT[lang()].more(projectCount(bar));
      bar.insertAdjacentElement('afterend', toggle);
    });
  }

  let queued = false;
  function schedule(){
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; foldProjectBars(); });
  }

  document.addEventListener('click', event => {
    const toggle = event.target.closest('[data-sp-project-more]');
    if (!toggle) return;
    event.preventDefault();
    event.stopPropagation();
    const bar = toggle.previousElementSibling;
    if (!bar || !bar.classList.contains('project-bar')) return;
    const open = bar.dataset.spClamp !== 'open';
    try { localStorage.setItem(OPEN_KEY, open ? '1' : '0'); } catch (_e) { /* private mode: the choice lasts this page */ }
    bar.dataset.spClamp = open ? 'open' : 'closed';
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.textContent = open ? TEXT[lang()].less : TEXT[lang()].more(projectCount(bar));
  });

  // A team form that changed asks for its save button.
  const markDirty = event => {
    const form = event.target.closest && event.target.closest('[data-om-team-form]');
    if (form) form.dataset.dirty = '1';
  };
  document.addEventListener('toggle', event => {
    if (event.target.classList && event.target.classList.contains('sidebar-projects-section')) schedule();
  }, true);
  document.addEventListener('input', markDirty);
  document.addEventListener('change', markDirty);

  function start(){
    const list = document.querySelector('.session-list');
    if (list) new MutationObserver(schedule).observe(list, { childList: true });
    schedule();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
