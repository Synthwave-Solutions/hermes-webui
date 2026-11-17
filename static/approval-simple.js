/* Approval card: one clear choice first.

   The card opens with two buttons, allow once and deny. The wider choices
   (allow for this conversation, always allow, skip all) sit behind "More
   options", so a risky choice is never one mis-click away from the safe one.
   The buttons themselves, their rules and their keyboard shortcuts stay in
   static/messages.js; this file only decides what is shown first. */
(function(){
  'use strict';
  const EXTRA = ['approvalBtnSession', 'approvalBtnAlways', 'approvalSkipAll'];
  const words = { nl: ['Meer opties', 'Minder opties'], en: ['More options', 'Fewer options'] };
  function label(open){
    let lang = 'nl';
    try { lang = String(localStorage.getItem('hermes-lang') || 'nl').slice(0, 2); } catch (_e) { /* default */ }
    return (words[lang] || words.nl)[open ? 1 : 0];
  }
  function init(){
    const card = document.getElementById('approvalCard'), row = document.getElementById('approvalBtns');
    if (!card || !row || row.querySelector('.approval-more-toggle')) return;
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'approval-more-toggle';
    toggle.setAttribute('aria-controls', EXTRA.join(' '));
    row.appendChild(toggle);
    const set = open => {
      card.classList.toggle('approval-more-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = label(open);
    };
    // Nothing to reveal when the policy allows none of the wider choices.
    const sync = () => { toggle.hidden = !EXTRA.some(id => { const b = document.getElementById(id); return b && !b.hidden; }); };
    toggle.addEventListener('click', () => set(!card.classList.contains('approval-more-open')));
    // Every new request starts with the two clear choices again.
    new MutationObserver(() => { if (!card.classList.contains('visible')) set(false); sync(); })
      .observe(card, { attributes: true, attributeFilter: ['class'] });
    EXTRA.forEach(id => { const b = document.getElementById(id); if (b) new MutationObserver(sync).observe(b, { attributes: true, attributeFilter: ['hidden'] }); });
    card.classList.add('approval-simple');
    set(false); sync();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
