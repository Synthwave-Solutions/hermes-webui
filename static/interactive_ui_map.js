// Map blocks: coordinates and photos from the server (POST /api/map/resolve).
//
// static/interactive_ui.js calls interactiveUiMapResolve(spec, key, opts)
// once a ```map block is complete. One call per block: the answer is kept
// in sessionStorage under 'iui-map:'+key, so scrolling or re-rendering the
// chat does not ask again. Places the server could not look up yet
// ('later', for example while the shared geocoding budget is in use) get one
// more try after 3 s; opts.onUpdate receives the merged answer.
//
// Global: interactiveUiMapResolve.

const _iuiMap=(function(){
  const PREFIX='iui-map:', RETRY_MS=3000, TIMEOUT_MS=20000;
  const inflight=new Map();
  function read(key){
    try{const raw=sessionStorage.getItem(PREFIX+key);return raw?JSON.parse(raw):null;}catch(_){return null;}
  }
  function write(key,data){
    try{sessionStorage.setItem(PREFIX+key,JSON.stringify(data));}catch(_){}
  }
  function pending(data){return !!(data&&Array.isArray(data.places)&&data.places.some(p=>p&&p.status==='later'));}
  async function call(body){
    const ctl=typeof AbortController==='function'?new AbortController():null;
    const timer=ctl?setTimeout(()=>ctl.abort(),TIMEOUT_MS):0;
    try{
      // The page's fetch wrapper adds the CSRF header for same-origin posts.
      const res=await fetch(new URL('api/map/resolve',document.baseURI||location.href).href,{
        method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body),signal:ctl?ctl.signal:undefined});
      if(!res.ok) throw new Error('map resolve '+res.status);
      const data=await res.json();
      if(!data||!Array.isArray(data.places)) throw new Error('map resolve: bad answer');
      return data;
    } finally {
      if(timer) clearTimeout(timer);
    }
  }
  function merge(base,update){
    const byK=new Map((update.places||[]).map(p=>[p.k,p]));
    const attribution=[...new Set([...(base.attribution||[]),...(update.attribution||[])])];
    return Object.assign({},base,{places:base.places.map(p=>p.status==='later'&&byK.has(p.k)?byK.get(p.k):p),attribution});
  }
  function resolve(spec,key,opts){
    opts=opts||{};
    const K=typeof SWKit!=='undefined'?SWKit:null;
    if(!K||!spec||!Array.isArray(spec.places)) return Promise.reject(new Error('map helpers unavailable'));
    const cached=key&&read(key);
    if(cached&&!pending(cached)) return Promise.resolve(cached);
    if(key&&inflight.has(key)) return inflight.get(key);
    const body=K.mapRequest(spec,opts.lang||'nl');
    const job=call(body).then(data=>{
      if(key) write(key,data);
      // Keep asking while places wait (the server spaces lookups out); after the
      // last round they say plainly that they could not be looked up now.
      const MAX_ROUNDS=6;
      const giveUp=d=>Object.assign({},d,{places:d.places.map(p=>p.status==='later'?Object.assign({},p,{status:'not_found',gaveUp:true}):p)});
      const done=d=>{if(key)write(key,d);if(typeof opts.onUpdate==='function')opts.onUpdate(d);};
      const retry=(round,cur)=>setTimeout(()=>{
        const again=Object.assign({},body,{places:body.places.filter(p=>cur.places.some(r=>r.k===p.k&&r.status==='later'))});
        if(!again.places.length) return;
        call(again).then(update=>{
          const merged=merge(cur,update);
          if(pending(merged)&&round<MAX_ROUNDS){done(merged);retry(round+1,merged);}
          else done(pending(merged)?giveUp(merged):merged);
        },()=>{if(round<MAX_ROUNDS)retry(round+1,cur);else done(giveUp(cur));});
      },RETRY_MS);
      if(pending(data)) retry(1,data);
      return data;
    }).finally(()=>{if(key)inflight.delete(key);});
    if(key) inflight.set(key,job);
    return job;
  }
  return {resolve,merge};
})();

function interactiveUiMapResolve(spec,key,opts){return _iuiMap.resolve(spec,key,opts);}
