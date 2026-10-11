/* Job financial metadata lives centrally, never in the scheduler execution spec. */
(function(){
 'use strict';
 function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
 window.SynthPulseJobCosts={async mount(job,container){
  const current=String(job.id),key=_cronOwnerProfileName(job),generation=Symbol();container._jobCostsGeneration=generation;
  let info;try{info=await api('/api/msp/overview');}catch(_){return;}
  if(!info.permissions?.billing||!container.isConnected||container._jobCostsGeneration!==generation||_currentCronDetail!==job)return;
  const nl=document.documentElement.lang.startsWith('nl')||localStorage.getItem('sp-feature-guide-language')==='nl';
  const box=el('section');box.className='detail-card';box.id='cronJobCosts';box.append(el('h3',nl?'Realisatie en supportkosten':'Implementation and support costs'));
  const guide=el('button',nl?'Interactieve gids':'Interactive guide');guide.type='button';guide.onclick=()=>window.SynthPulseHelp?.startFeatureTour(['webui.msp.job-costs'],{locale:nl?'nl':'en'});box.append(guide);
  let row=info.scheduled_jobs?.jobs?.find(r=>r.job_id===current&&r.profile===key);
  const form=el('form'),hours=el('input'),rate=el('input'),notice=el('p');
  function field(label,input,value){const l=el('label',label);input.type='number';input.min='0';input.max='1000000';input.step='.01';input.value=value;l.append(input);form.append(l);}
  field(nl?'Realisatie-uren':'Implementation hours',hours,(row?.hours_hundredths||0)/100);hours.required=true;
  field(nl?'Afgesproken uurtarief (euro excl. btw, leeg = nog afspreken)':'Agreed hourly rate (EUR excl. VAT, empty = to be agreed)',rate,row?.hourly_cents==null?'':row.hourly_cents/100);
  const preview=el('p');function recalc(){const value=Number(hours.value)*Number(rate.value);preview.textContent=rate.value===''?(nl?'Tarief nog afspreken.':'Rate to be agreed.'):(nl?'Jobbedrag: €':'Job value: €')+value.toFixed(2)+(nl?' · Jaarlijks support (15%): €':' · Annual support (15%): €')+(value*.15).toFixed(2);}
  hours.oninput=rate.oninput=recalc;recalc();form.append(preview);
  const save=el('button',nl?'Uren en tarief opslaan':'Save hours and rate');save.className='app-button';save.type='submit';form.append(save,notice);
  form.onsubmit=async e=>{e.preventDefault();save.disabled=true;notice.textContent='';try{row=await api('/api/msp/job-cost',{method:'POST',body:JSON.stringify({job_id:current,profile:key,title:String(job.name||job.id).slice(0,200),hours_hundredths:Math.round(Number(hours.value)*100),hourly_cents:rate.value===''?null:Math.round(Number(rate.value)*100),expected_revision:row?.revision||0})});notice.textContent=nl?'Opgeslagen. De uren tellen mee bij Mijn MSP.':'Saved. Hours are included in My MSP.';}catch(_){notice.textContent=nl?'Opslaan mislukt. Open de taak opnieuw als iemand de bedragen heeft gewijzigd.':'Could not save. Reopen the job if someone changed the amounts.';}finally{save.disabled=false;}};
  box.append(form,el('p',nl?'Jaarlijks support is 15% van het eenmalige jobbedrag. Dit wordt niet per uitvoering berekend. Opslaan maakt geen factuur aan.':'Annual support is 15% of the one-time job value. It is not charged per execution. Saving creates no invoice.'));container.querySelector('.main-view-content')?.append(box);
 }};
})();
