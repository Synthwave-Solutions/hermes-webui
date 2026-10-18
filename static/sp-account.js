/* Visible "Log out" (🚪) in the navigation rail and the mobile nav.
 *
 * Shown only when sign-in is enabled and this browser is signed in (password,
 * passkey or SSO/OIDC: all of them use the same server session cookie). It
 * reuses the existing POST /api/auth/logout, which invalidates the server
 * session and clears the cookie, then returns to the login screen.
 */
(function(root){
  'use strict';
  const COPY={
    nl:{label:'Uitloggen',confirm_title:'Uitloggen?',confirm_body:'Je gaat terug naar het inlogscherm. Lopende antwoorden gaan op de achtergrond gewoon door.',confirm_ok:'Uitloggen',failed:'Uitloggen lukte niet. Probeer het opnieuw.'},
    en:{label:'Log out',confirm_title:'Log out?',confirm_body:'You will return to the sign-in screen. Replies that are still running keep going in the background.',confirm_ok:'Log out',failed:'Could not log out. Please try again.'},
  };
  function lang(){
    const ft=root.SynPulseFriendlyTools;
    return ft&&typeof ft.lang==='function'?ft.lang():'en';
  }
  function text(key){ return (COPY[lang()]||COPY.en)[key]; }
  function buttons(){
    return ['spLogoutRail','spLogoutMobile'].map(id=>root.document.getElementById(id)).filter(Boolean);
  }
  function label(){
    const l=text('label');
    buttons().forEach(btn=>{
      btn.setAttribute('aria-label',l);
      btn.setAttribute('data-tooltip',l);
      btn.setAttribute('data-label',l);
      btn.title=l;
    });
  }
  async function refresh(){
    try{
      const r=await fetch(new URL('api/auth/status',root.document.baseURI||root.location.href),{cache:'no-store',credentials:'same-origin'});
      if(!r.ok) return;
      const st=await r.json();
      const show=!!(st&&st.auth_enabled&&st.logged_in);
      label();
      buttons().forEach(btn=>{ btn.hidden=!show; });
    }catch(_){ /* stays hidden */ }
  }
  async function spLogout(){
    if(typeof root.showConfirmDialog==='function'){
      const ok=await root.showConfirmDialog({title:text('confirm_title'),message:text('confirm_body'),confirmLabel:text('confirm_ok'),danger:false,focusCancel:false});
      if(!ok) return;
    }
    try{
      // Same call as Settings > Sign Out (panels.js signOut), via the shared api() helper.
      const data=typeof root.api==='function'
        ?await root.api('/api/auth/logout',{method:'POST',body:'{}'})
        :await (await fetch(new URL('api/auth/logout',root.document.baseURI||root.location.href),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'})).json();
      root.location.href=(data&&data.trusted_logout_url)||'login';
    }catch(_){
      if(typeof root.showToast==='function') root.showToast(text('failed'),3000,'error');
    }
  }
  root.spLogout=spLogout;
  if(root.document){
    if(root.document.readyState==='loading') root.document.addEventListener('DOMContentLoaded',refresh);
    else refresh();
  }
})(typeof window!=='undefined'?window:globalThis);
