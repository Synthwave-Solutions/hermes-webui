/* Phone: the daily destinations within thumb reach.

   A bar under the page with the overview, conversations, bots and approvals,
   plus "More" for the full menu. It is part of the page flow (not floating), so
   it never covers the composer, and it steps aside while the keyboard is open.
   Destinations the viewer may not open are left out. Wider screens keep the rail. */
(function(){
  'use strict';
  const ITEMS = ['studio', 'chat', 'profiles', 'approvals'];
  const SHORT = { nl: { studio: 'Overzicht', chat: 'Chat', profiles: 'Bots', approvals: 'Goedkeuren', more: 'Meer' },
                  en: { studio: 'Overview', chat: 'Chat', profiles: 'Bots', approvals: 'Approvals', more: 'More' } };
  const MORE_ICON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></svg>';
  function words(){
    let lang = 'nl';
    try { lang = String(localStorage.getItem('hermes-lang') || 'nl').slice(0, 2); } catch (_e) { /* default */ }
    return SHORT[lang] || SHORT.nl;
  }
  let nav = null;
  function source(panel){ return document.querySelector('.sidebar-nav .nav-tab[data-panel="' + panel + '"]'); }
  function shown(tab){ return !!tab && tab.style.display !== 'none' && !tab.hidden; }
  function build(){
    const w = words();
    nav.replaceChildren();
    for (const panel of ITEMS) {
      const tab = source(panel);
      if (!shown(tab)) continue;
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'sp-bottom-item'; b.dataset.bottomPanel = panel;
      const icon = tab.querySelector('svg');
      b.innerHTML = (icon ? icon.outerHTML : '') + '<span></span>';
      b.lastElementChild.textContent = w[panel];
      // Straight to the page itself; the side drawer with its lists stays behind "More".
      b.onclick = async () => {
        if (typeof switchPanel === 'function') await switchPanel(panel);
        if (typeof closeMobileSidebar === 'function') closeMobileSidebar();
      };
      nav.appendChild(b);
    }
    const more = document.createElement('button');
    more.type = 'button'; more.className = 'sp-bottom-item'; more.dataset.bottomMore = '';
    more.innerHTML = MORE_ICON + '<span></span>'; more.lastElementChild.textContent = w.more;
    more.onclick = () => { if (typeof toggleMobileSidebar === 'function') toggleMobileSidebar(); };
    nav.appendChild(more);
    sync();
  }
  function sync(){
    if (!nav) return;
    nav.querySelectorAll('[data-bottom-panel]').forEach(b => {
      const tab = source(b.dataset.bottomPanel), active = !!tab && tab.classList.contains('active');
      b.classList.toggle('active', active);
      if (active) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
      // Mirror the counter the navigation already carries (static/today.js).
      const count = tab && tab.querySelector('.sp-nav-count');
      let mine = b.querySelector('.sp-nav-count');
      if (!count) { if (mine) mine.remove(); return; }
      if (!mine) { mine = document.createElement('span'); mine.className = 'sp-nav-count'; b.appendChild(mine); }
      mine.textContent = count.textContent;
    });
  }
  function init(){
    const layout = document.querySelector('.layout'), side = document.querySelector('.sidebar-nav');
    if (!layout || !side || nav) return;
    nav = document.createElement('nav');
    nav.className = 'sp-bottom-nav';
    nav.setAttribute('aria-label', words().more === 'More' ? 'Main destinations' : 'Hoofdonderdelen');
    layout.after(nav);
    build();
    // Which tabs exist, which is active and their counters all change on the source tabs.
    let queued = false;
    new MutationObserver(records => {
      if (queued) return; queued = true;
      const rebuild = records.some(r => r.type === 'attributes' && (r.attributeName === 'style' || r.attributeName === 'hidden'));
      requestAnimationFrame(() => { queued = false; if (rebuild || nav.dataset.lang !== words().more) { nav.dataset.lang = words().more; build(); } else sync(); });
    }).observe(side, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
    // The keyboard takes half the screen: give the space back while someone types.
    const typing = el => !!el && (el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT' && !/^(checkbox|radio|button|submit|file|range|color)$/i.test(el.type)) || el.isContentEditable);
    document.addEventListener('focusin', ev => { if (typing(ev.target)) nav.classList.add('is-typing'); });
    document.addEventListener('focusout', () => { setTimeout(() => { if (!typing(document.activeElement)) nav.classList.remove('is-typing'); }, 80); });
  }
  if (document.readyState === 'complete') init(); else window.addEventListener('load', init);
})();
