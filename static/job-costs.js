/* Implementation effort drives annual support; enabled commitments are MSP-managed. */
(function(){
 'use strict';
 function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
 window.SynthPulseJobCosts={async mount(job,container){
  const current=String(job.id),key=_cronOwnerProfileName(job),generation=Symbol();container._jobCostsGeneration=generation;
  const valid=()=>container.isConnected&&container._jobCostsGeneration===generation&&_currentCronDetail===job;
  let info;try{info=await api('/api/msp/overview');}catch(_){return;}
  if(!info.permissions?.billing||!valid())return;
  const manager=info.permissions?.manage_job_support===true;
  const nl=document.documentElement.lang.startsWith('nl')||localStorage.getItem('sp-feature-guide-language')==='nl',t=(a,b)=>nl?a:b;
  const box=el('section');box.className='detail-card';box.id='cronJobCosts';box.append(el('h3',t('Implementatie & jaarlijkse support','Implementation & annual support')));
  const guide=el('button',t('Interactieve gids','Interactive guide'));guide.className='app-button';guide.type='button';guide.onclick=()=>window.SynthPulseHelp?.startFeatureTour(['webui.msp.job-costs'],{locale:nl?'nl':'en'});box.append(guide);
  let row=info.scheduled_jobs?.jobs?.find(r=>r.job_id===current&&r.profile===key);
  const form=el('form'),enabled=el('input'),hours=el('input'),notice=el('p');notice.setAttribute('role','status');
  function field(label,input,value){const l=el('label',label);input.type='number';input.min='0';input.max='1000000';input.step='.01';input.value=value;input.setAttribute('aria-label',label);l.append(input);form.append(l);}
  field(t('Implementatie-uren','Implementation hours'),hours,(row?.hours_hundredths||0)/100);hours.max='11111.11';hours.required=true;
  const preview=el('p');preview.id='cronSupportCalculation';preview.setAttribute('aria-live','polite');form.append(preview);
  function recalc(){const h=Math.round(Number(hours.value)*100),minutes=row?.support_enabled&&h===row.hours_hundredths?row.annual_support_minutes:Math.floor((h*9+50)/100);
   preview.textContent=Number((h/100).toFixed(2))+t(' implementatie-uren × 15% = ',' implementation hours × 15% = ')+Number((minutes/60).toFixed(2))+t(' supporturen per jaar.',' annual support hours.');
   if(row?.support_enabled&&minutes!==Math.floor((h*9+50)/100))preview.textContent=Number((minutes/60).toFixed(2))+t(' supporturen per jaar volgens bestaande afspraak.',' annual support hours under the existing agreement.');
  }
  const toggle=el('label',t('Jaarlijkse support inschakelen','Enable annual support'));enabled.type='checkbox';enabled.checked=!!row?.support_enabled;enabled.setAttribute('role','switch');enabled.setAttribute('aria-label',t('Jaarlijkse support inschakelen','Enable annual support'));toggle.className='job-support-toggle';toggle.prepend(enabled);form.append(toggle);
  const locked=el('p');
  function state(){hours.disabled=enabled.disabled=!manager;hours.min=enabled.checked?'0.06':'0';locked.textContent=!manager?t('Je MSP beheert deze uren en de support.','Your MSP manages these hours and support.'):t('Bij inschakelen worden deze uren toegevoegd aan je jaarlijkse supporttotaal.','Enabling adds these hours to your annual support total.');}
  enabled.onchange=state;hours.oninput=recalc;state();recalc();form.append(locked);
  const save=el('button',t('Opslaan','Save'));save.className='app-button';save.type='submit';if(manager)form.append(save);form.append(notice);
  form.onsubmit=async e=>{e.preventDefault();save.disabled=true;notice.textContent='';try{
   const result=await api('/api/msp/job-cost',{method:'POST',body:JSON.stringify({job_id:current,profile:key,title:String(job.name||job.id).slice(0,200),hours_hundredths:Math.round(Number(hours.value)*100),hourly_cents:row?.hourly_cents??null,support_enabled:enabled.checked,expected_revision:row?.revision||0})});
   if(!valid())return;row=result;enabled.checked=!!row.support_enabled;hours.value=row.hours_hundredths/100;state();recalc();notice.textContent=row.support_enabled?t('Opgeslagen: uren zijn meegenomen in je jaarlijkse support.','Saved: hours are included in your annual support.'):t('Opgeslagen.','Saved.');
  }catch(_){if(valid())notice.textContent=t('Opslaan mislukt. Heropen de taak om de actuele afspraak te laden.','Could not save. Reopen the job to load the current agreement.');}finally{save.disabled=false;}};
  box.append(form);container.querySelector('.main-view-content')?.append(box);
 }};
})();
