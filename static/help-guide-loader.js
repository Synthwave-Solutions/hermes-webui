/* Keep optional feature catalogs off the chat's initial loading path. */
(function(){
  'use strict';
  const source=new URL(document.currentScript.src,document.baseURI);
  const loads=new Map();
  let pending=null;
  function script(name){
    if(loads.has(name))return loads.get(name);
    const url=new URL(name,source);url.search=source.search;
    const promise=new Promise((resolve,reject)=>{
      const node=document.createElement('script');node.src=url.href;node.async=true;
      node.onload=()=>resolve();
      node.onerror=()=>{loads.delete(name);node.remove();reject(new Error('Feature guide unavailable'));};
      document.head.appendChild(node);
    });
    loads.set(name,promise);return promise;
  }
  function load(){
    if(window.SynthPulseFeatureGuide)return Promise.resolve(window.SynthPulseFeatureGuide);
    if(pending)return pending;
    pending=Promise.all(['help-features.js','help-msp-features.js','help-feature-targets.js'].map(script))
      .then(()=>script('help-guide.js'))
      .then(()=>{if(!window.SynthPulseFeatureGuide){loads.delete('help-guide.js');throw new Error('Feature guide unavailable');}return window.SynthPulseFeatureGuide;})
      .catch(error=>{pending=null;throw error;});
    return pending;
  }
  window.loadSynthPulseFeatureGuide=load;
  document.addEventListener('click',async event=>{
    const button=event.target.closest?.('[data-help-guide]');
    if(!button||window.SynthPulseFeatureGuide)return;
    event.preventDefault();event.stopImmediatePropagation();
    button.setAttribute('aria-busy','true');
    try{const guide=await load();guide.open({area:button.dataset.helpGuide,trigger:button});}
    catch(_){if(typeof showToast==='function')showToast(t('help_guide_load_failed'));}
    finally{button.removeAttribute('aria-busy');}
  },true);
  // Existing guide initialization owns deep-link opening after the scripts load.
  if(new URL(location.href).searchParams.has('help_feature')){
    load().catch(()=>{if(typeof showToast==='function')showToast(t('help_guide_load_failed'));});
  }
})();
