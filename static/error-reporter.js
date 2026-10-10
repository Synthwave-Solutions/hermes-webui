// Browser error reports for support (plan 3.3, W7).
//
// Off unless GET /api/settings says support_telemetry is true, which the
// server only does when operational telemetry and diagnostic payloads are
// both switched on for this installation. Until then this file installs no
// error listener and sends no report. When on, it reports uncaught errors and
// unhandled promise rejections to the same-origin route POST
// /api/client-errors: the error type, a shortened message, the page path
// without its query, and stack frames from this WebUI's own static files
// only. The server redacts and rate limits every report; nothing here holds
// or sees a key.
(function(){
  'use strict';
  var w=typeof window!=='undefined'?window:null;
  if(!w||typeof w.addEventListener!=='function'||typeof w.fetch!=='function')return;

  var MAX_REPORTS=10;
  var MAX_MESSAGE=500;
  var MAX_FRAMES=20;
  var MAX_STACK=8000;
  var SETTINGS_WAIT_MS=15000;
  var TYPE_RE=/^[A-Za-z_$][A-Za-z0-9_$.]{0,63}$/;
  var CHROME_FRAME_RE=/^\s*at (?:(.*?) \()?(.*?):(\d+):(\d+)\)?\s*$/;
  var GECKO_FRAME_RE=/^\s*(.*?)@(.*?):(\d+):(\d+)\s*$/;

  var checked=false;
  var installed=false;
  var sent=0;
  var seen={};

  function resolve(rel){
    var base=(w.document&&w.document.baseURI)||(w.location&&w.location.href)||'';
    return new URL(rel,base);
  }

  function ownStaticPath(file){
    try{
      var url=resolve(String(file||''));
      if(!w.location||url.origin!==w.location.origin)return '';
      var at=url.pathname.lastIndexOf('/static/');
      return at<0?'':url.pathname.slice(at+1);
    }catch(_){return '';}
  }

  function framesOf(stack){
    var out=[];
    var lines=String(stack||'').slice(0,MAX_STACK).split('\n');
    for(var i=0;i<lines.length&&out.length<MAX_FRAMES;i++){
      var m=CHROME_FRAME_RE.exec(lines[i])||GECKO_FRAME_RE.exec(lines[i]);
      if(!m)continue;
      var file=ownStaticPath(m[2]);
      if(!file)continue;
      out.push({'function':String(m[1]||'?').slice(0,100),'file':file});
    }
    // Stacks list the innermost call first; reports list it last.
    return out.reverse();
  }

  function pagePath(){
    try{return String((w.location&&w.location.pathname)||'/').slice(0,256);}catch(_){return '/';}
  }

  function buildReport(kind,error,fallbackMessage){
    var type='Error';
    var message='';
    var stack='';
    if(error&&typeof error==='object'){
      if(typeof error.name==='string'&&TYPE_RE.test(error.name))type=error.name;
      if(typeof error.message==='string')message=error.message;
      if(typeof error.stack==='string')stack=error.stack;
    }else if(error!==undefined&&error!==null){
      message=String(error);
    }
    if(!message&&typeof fallbackMessage==='string')message=fallbackMessage;
    if(kind==='unhandledrejection'&&!(error&&typeof error==='object'&&typeof error.name==='string'))type='UnhandledRejection';
    return {
      kind:kind,
      type:type,
      message:String(message).slice(0,MAX_MESSAGE),
      frames:framesOf(stack),
      url_path:pagePath()
    };
  }

  function send(report){
    if(sent>=MAX_REPORTS)return;
    var first=report.frames.length?report.frames[report.frames.length-1]:null;
    var signature=report.type+'|'+report.message+'|'+(first?first.file+':'+first['function']:'');
    if(Object.prototype.hasOwnProperty.call(seen,signature))return;
    seen[signature]=true;
    sent+=1;
    try{
      var pending=w.fetch(resolve('api/client-errors').toString(),{
        method:'POST',
        credentials:'same-origin',
        keepalive:true,
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(report)
      });
      if(pending&&typeof pending.catch==='function')pending.catch(function(){});
    }catch(_){}
  }

  function onError(event){
    try{
      if(!event)return;
      var error=event.error;
      // Cross-origin scripts only say "Script error." and carry nothing useful.
      if(!error&&(!event.message||event.message==='Script error.'))return;
      send(buildReport('error',error,event.message));
    }catch(_){}
  }

  function onRejection(event){
    try{
      if(!event)return;
      send(buildReport('unhandledrejection',event.reason,''));
    }catch(_){}
  }

  function install(){
    if(installed)return;
    installed=true;
    w.addEventListener('error',onError);
    w.addEventListener('unhandledrejection',onRejection);
  }

  function check(){
    if(checked)return;
    checked=true;
    try{
      var pending=w.fetch(resolve('api/settings').toString(),{
        credentials:'same-origin',
        cache:'no-store',
        headers:{'Accept':'application/json'}
      });
      if(!pending||typeof pending.then!=='function')return;
      pending.then(function(response){
        return response&&response.ok?response.json():null;
      }).then(function(settings){
        if(settings&&settings.support_telemetry===true)install();
      }).catch(function(){});
    }catch(_){}
  }

  // Read the flag once the app has booted (or after a fallback wait), so the
  // settings request never competes with the first paint.
  w.addEventListener('synpulse:boot-ready',check);
  if(typeof w.setTimeout==='function')w.setTimeout(check,SETTINGS_WAIT_MS);
})();
