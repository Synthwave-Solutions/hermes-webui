/* Job support commitments are central metadata, independent of execution state. */
(function(){
 'use strict';
 function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
 window.SynthPulseJobCosts={async mount(job,container){
  const current=String(job.id),key=_cronOwnerProfileName(job),generation=Symbol();container._jobCostsGeneration=generation;
  const valid=()=>container.isConnected&&container._jobCostsGeneration===generation&&_currentCronDetail===job;
  let info;try{info=await api('/api/msp/overview');}catch(_){return;}
  if(!info.permissions?.billing||!valid())return;
  const nl=document.documentElement.lang.startsWith('nl')||localStorage.getItem('sp-feature-guide-language')==='nl',t=(a,b)=>nl?a:b;
  const box=el('section');box.className='detail-card';box.id='cronJobCosts';box.append(el('h3',t('Jaarlijkse support','Annual support')));
  const guide=el('button',t('Interactieve gids','Interactive guide'));guide.className='app-button';guide.type='button';guide.onclick=()=>window.SynthPulseHelp?.startFeatureTour(['webui.msp.job-costs'],{locale:nl?'nl':'en'});box.append(guide);
  let row=info.scheduled_jobs?.jobs?.find(r=>r.job_id===current&&r.profile===key);
  const form=el('form'),annual=el('input'),enabled=el('input'),hours=el('input'),rate=el('input'),notice=el('p');notice.setAttribute('role','status');
  function field(parent,label,input,value){const l=el('label',label);input.type='number';input.min='0';input.max='1000000';input.step='.01';input.value=value;input.setAttribute('aria-label',label);l.append(input);parent.append(l);}
  field(form,t('Supporturen per jaar','Support hours per year'),annual,Number(((row?.annual_support_minutes||0)/60).toFixed(2)));annual.max='1666.66';
  const toggle=el('label',t('Jaarlijkse support inschakelen','Enable annual support'));enabled.type='checkbox';enabled.checked=!!row?.support_enabled;enabled.setAttribute('role','switch');enabled.setAttribute('aria-label',t('Jaarlijkse support inschakelen','Enable annual support'));toggle.className='job-support-toggle';toggle.prepend(enabled);form.append(toggle);
  const locked=el('p');
  function state(){annual.disabled=enabled.disabled=!!row?.support_enabled;annual.required=enabled.checked;annual.min=enabled.checked?'0.02':'0';locked.textContent=row?.support_enabled?t('Ingeschakeld. Alleen je MSP kan dit wijzigen of uitschakelen.','Enabled. Only your MSP can change or disable this.'):t('Deze uren tellen mee in je jaarlijkse support. Extra uren worden beschikbaar na afspraak en betaling.','These hours count toward annual support. Extra hours become available after agreement and payment.');}
  enabled.onchange=state;state();form.append(locked);
  const details=el('details'),summary=el('summary',t('Realisatie & tarief','Implementation & rate'));details.append(summary);
  field(details,t('Realisatie-uren','Implementation hours'),hours,(row?.hours_hundredths||0)/100);hours.required=true;
  field(details,t('Afgesproken uurtarief (EUR excl. btw)','Agreed hourly rate (EUR excl. VAT)'),rate,row?.hourly_cents==null?'':row.hourly_cents/100);
  const preview=el('p');function recalc(){const h=Math.round(Number(hours.value)*100),r=Math.round(Number(rate.value)*100);const suggested=(h*9+50)/100;preview.textContent=t('Suggestie: ','Suggestion: ')+Number((Math.floor(suggested)/60).toFixed(2))+t(' uur/jaar (15%).',' hours/year (15%).');if(rate.value!==''&&Number.isSafeInteger(h)&&Number.isSafeInteger(r)){const cents=Math.round(Math.round(h*r/100)*15/100);preview.textContent+=' '+new Intl.NumberFormat(nl?'nl-NL':'en-GB',{style:'currency',currency:'EUR'}).format(cents/100)+t(' support per jaar excl. btw.',' annual support excl. VAT.');}}
  hours.oninput=rate.oninput=recalc;recalc();details.append(preview);form.append(details);
  const save=el('button',t('Opslaan','Save'));save.className='app-button';save.type='submit';form.append(save,notice);
  form.onsubmit=async e=>{e.preventDefault();save.disabled=true;notice.textContent='';try{
   const minutes=Math.round(Number(annual.value)*60);
   const result=await api('/api/msp/job-cost',{method:'POST',body:JSON.stringify({job_id:current,profile:key,title:String(job.name||job.id).slice(0,200),hours_hundredths:Math.round(Number(hours.value)*100),hourly_cents:rate.value===''?null:Math.round(Number(rate.value)*100),support_minutes:row?.support_enabled?row.support_minutes:(minutes||null),support_enabled:enabled.checked,expected_revision:row?.revision||0})});
   if(!valid())return;row=result;enabled.checked=!!row.support_enabled;annual.value=Number((row.annual_support_minutes/60).toFixed(2));state();notice.textContent=row.support_enabled?t('Opgeslagen en meegenomen in je jaarlijkse support.','Saved and included in your annual support.'):t('Opgeslagen.','Saved.');
  }catch(_){if(valid())notice.textContent=t('Opslaan mislukt. Heropen de taak om de actuele afspraak te laden.','Could not save. Reopen the job to load the current agreement.');}finally{save.disabled=false;}};
  box.append(form);container.querySelector('.main-view-content')?.append(box);
 }};
})();
