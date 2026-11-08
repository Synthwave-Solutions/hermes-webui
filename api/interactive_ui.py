"""Interactive answers in chat: the sandbox frame and the prompt block.

An assistant reply may carry a fenced block with the info string
``interactive-ui``. The chat (``static/interactive_ui.js``) shows it as a small
live app inside the answer: it loads ``FRAME_PATH`` in an iframe and sends the
block's CSS, markup and scripts to it with ``postMessage``.

The frame document is the only thing served here, always with its own headers:

* ``sandbox allow-scripts allow-forms allow-popups`` in the CSP (never
  ``allow-same-origin``), so the widget runs in an opaque origin without the
  WebUI cookie, storage or DOM, also when it is opened in its own tab.
* Scripts and styles only inline or from the public CDNs in ``CDN_HOSTS``;
  ``connect-src`` is limited to the same CDNs (module imports and source
  maps), so generated code cannot send data anywhere else.
* ``form-action 'none'`` and no ``allow-top-navigation``: a widget cannot
  navigate the chat away.
* No cookie is set and the document is never cached.

``prompt_block`` is appended to the WebUI runtime instructions (see
``api/streaming.py``) so every bot knows when and how to answer this way. The
switch is ``webui_interactive_ui`` in the config; ``HERMES_WEBUI_INTERACTIVE_UI``
(``1`` or ``0``) overrides it. The default is on.

The approach (ordered streaming of CSS, markup and script into an isolated
frame, a validated host bridge for follow-up prompts) follows CopilotKit's
Open Generative UI / Open Intelligent UI (MIT); no code is vendored.
"""

from __future__ import annotations

import os

FRAME_PATH = "/static/interactive-ui/frame.html"
CONFIG_KEY = "webui_interactive_ui"
ENV_VAR = "HERMES_WEBUI_INTERACTIVE_UI"
DEFAULT_ENABLED = True

CDN_HOSTS = (
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
    "https://cdnjs.cloudflare.com",
    "https://esm.sh",
)
_CDN = " ".join(CDN_HOSTS)

FRAME_CSP = (
    "sandbox allow-scripts allow-forms allow-popups; "
    "default-src 'none'; "
    f"script-src 'unsafe-inline' 'unsafe-eval' blob: {_CDN}; "
    f"style-src 'unsafe-inline' {_CDN} https://fonts.googleapis.com; "
    f"font-src data: {_CDN} https://fonts.gstatic.com; "
    "img-src data: blob: https:; "
    "media-src data: blob: https:; "
    f"connect-src {_CDN}; "
    "worker-src blob:; "
    "frame-src 'none'; object-src 'none'; manifest-src 'none'; "
    "base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)

PERMISSIONS_POLICY = ", ".join(
    f"{feature}=()" for feature in (
        "accelerometer", "ambient-light-sensor", "autoplay", "battery", "bluetooth", "camera",
        "clipboard-read", "display-capture", "encrypted-media", "geolocation", "gyroscope",
        "hid", "idle-detection", "magnetometer", "microphone", "midi", "payment",
        "publickey-credentials-get", "screen-wake-lock", "serial", "usb", "web-share",
        "xr-spatial-tracking",
    )
)

# Base theme every widget gets. The host sends the chat's colours as
# --sw-* variables; the fallbacks below are the Synthwave dark palette.
BASE_CSS = r"""
:root{--sw-bg:#0f1117;--sw-surface:#171a23;--sw-surface-2:#1f2330;--sw-fg:#e6e8ef;--sw-strong:#ffffff;
--sw-muted:#9aa1b2;--sw-accent:#f97316;--sw-accent-fg:#ffffff;--sw-accent-soft:rgba(249,115,22,.14);
--sw-border:#2a2f3d;--sw-good:#22c55e;--sw-warn:#eab308;--sw-bad:#ef4444;--sw-info:#3b82f6;
--sw-radius:12px;--sw-radius-sm:8px;--sw-font:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--sw-mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
--sw-c1:#f97316;--sw-c2:#3b82f6;--sw-c3:#22c55e;--sw-c4:#a855f7;--sw-c5:#eab308;--sw-c6:#ec4899;--sw-c7:#14b8a6;--sw-c8:#94a3b8;
color-scheme:dark}
:root[data-theme=light]{color-scheme:light;--sw-bg:#ffffff;--sw-surface:#ffffff;--sw-surface-2:#f1f3f7;--sw-fg:#1f2430;
--sw-strong:#0b0e14;--sw-muted:#5b6475;--sw-accent-soft:rgba(249,115,22,.12);--sw-border:#dfe3ea}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:var(--sw-fg);font:14px/1.5 var(--sw-font);-webkit-font-smoothing:antialiased}
body{padding:14px}
#iui-root{min-height:20px}
h1,h2,h3,h4{color:var(--sw-strong);line-height:1.25;margin:0 0 .5em}
h1{font-size:1.35rem}h2{font-size:1.15rem}h3{font-size:1rem}
p{margin:0 0 .75em}small,.muted{color:var(--sw-muted)}
a{color:var(--sw-accent)}
button,.btn{font:inherit;font-weight:500;cursor:pointer;border:1px solid var(--sw-border);background:var(--sw-surface-2);color:var(--sw-fg);
padding:.5em .95em;border-radius:var(--sw-radius-sm);transition:background .15s,border-color .15s,transform .05s}
button:hover,.btn:hover{border-color:var(--sw-accent)}
button:active,.btn:active{transform:translateY(1px)}
button.primary,.btn.primary{background:var(--sw-accent);border-color:var(--sw-accent);color:var(--sw-accent-fg)}
button.ghost{background:transparent}
button:disabled{opacity:.5;cursor:not-allowed}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--sw-accent);outline-offset:2px}
input,select,textarea{font:inherit;color:var(--sw-fg);background:var(--sw-surface);border:1px solid var(--sw-border);border-radius:var(--sw-radius-sm);padding:.45em .65em}
input[type=range]{-webkit-appearance:none;appearance:none;padding:0;border:0;background:transparent;width:100%;height:22px;cursor:pointer}
input[type=range]::-webkit-slider-runnable-track{height:6px;border-radius:999px;background:linear-gradient(to right,var(--sw-accent) var(--sw-fill,0%),var(--sw-surface-2) var(--sw-fill,0%));border:1px solid var(--sw-border)}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;margin-top:-7px;border-radius:50%;background:var(--sw-accent);border:3px solid var(--sw-bg);box-shadow:0 0 0 1px var(--sw-accent),0 2px 6px rgba(0,0,0,.25)}
input[type=range]::-moz-range-track{height:6px;border-radius:999px;background:var(--sw-surface-2);border:1px solid var(--sw-border)}
input[type=range]::-moz-range-progress{height:6px;border-radius:999px;background:var(--sw-accent)}
input[type=range]::-moz-range-thumb{width:16px;height:16px;border-radius:50%;background:var(--sw-accent);border:3px solid var(--sw-bg)}
input[type=range]:focus-visible{outline:2px solid var(--sw-accent);outline-offset:4px;border-radius:999px}
input[type=checkbox],input[type=radio]{accent-color:var(--sw-accent)}
label{display:block;font-size:.85rem;color:var(--sw-muted);margin:0 0 .3em}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{text-align:left;padding:.5em .7em;border-bottom:1px solid var(--sw-border)}
th{color:var(--sw-muted);font-weight:600;font-size:.82rem}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}

.card{background:var(--sw-surface);border:1px solid var(--sw-border);border-radius:var(--sw-radius);padding:14px 16px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(var(--min,180px),1fr))}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.stack{display:flex;flex-direction:column;gap:10px}
.spacer{flex:1}
.stat{display:flex;flex-direction:column;gap:2px}
.stat .label{font-size:.82rem;color:var(--sw-muted)}
.stat .value{font-size:1.6rem;font-weight:700;color:var(--sw-strong);font-variant-numeric:tabular-nums}
.stat .delta.up{color:var(--sw-good)}.stat .delta.down{color:var(--sw-bad)}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:.75rem;font-weight:600;padding:.15em .55em;border-radius:999px;background:var(--sw-accent-soft);color:var(--sw-accent)}
.badge.good{background:rgba(34,197,94,.14);color:var(--sw-good)}.badge.bad{background:rgba(239,68,68,.14);color:var(--sw-bad)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--sw-border);margin-bottom:12px}
.tabs button{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;color:var(--sw-muted)}
.tabs button.active,.tabs button[aria-selected=true]{color:var(--sw-strong);border-bottom-color:var(--sw-accent)}
.chip{display:inline-flex;padding:.3em .75em;border-radius:999px;border:1px solid var(--sw-border);cursor:pointer;font-size:.85rem}
.chip.active{border-color:var(--sw-accent);background:var(--sw-accent-soft);color:var(--sw-strong)}
.bar{height:8px;border-radius:999px;background:var(--sw-surface-2);overflow:hidden}
.bar>span{display:block;height:100%;background:var(--sw-accent);border-radius:inherit;transition:width .3s}
.note{font-size:.8rem;color:var(--sw-muted);border-left:3px solid var(--sw-border);padding-left:8px}
.followup{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
canvas{max-width:100%}
svg{max-width:100%}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}}
@media (pointer:coarse){button,.btn,select,input[type=checkbox],input[type=radio],.chip{min-height:44px}input[type=range]{height:44px}}
"""

# Bare module imports that widgets may use (import * as THREE from "three").
IMPORT_MAP = (
    '{"imports":{'
    '"three":"https://esm.sh/three@0.170.0",'
    '"three/addons/":"https://esm.sh/three@0.170.0/examples/jsm/",'
    '"three/examples/jsm/":"https://esm.sh/three@0.170.0/examples/jsm/",'
    '"d3":"https://esm.sh/d3@7",'
    '"gsap":"https://esm.sh/gsap@3",'
    '"chart.js":"https://esm.sh/chart.js@4",'
    '"chart.js/auto":"https://esm.sh/chart.js@4/auto",'
    '"leaflet":"https://esm.sh/leaflet@1.9.4"'
    '}}'
)

# Runs inside the frame. It renders what the host sends, runs scripts in
# order once the block is complete, reports its height and errors, and gives
# the widget a small API (window.synthwave).
SHELL_JS = r"""
(function(){
  'use strict';
  var root = document.getElementById('iui-root');
  var userStyle = document.getElementById('iui-user-style');
  var host = window.parent;
  // Only ever runs inside the chat: frame-ancestors 'self' keeps other sites
  // from framing it, and a top-level visit renders nothing.
  if(!host || host === window){
    root.textContent = 'Open deze weergave vanuit de chat.';
    return;
  }
  var HOST_ORIGIN = (function(){ try{ return new URL(location.href).origin; }catch(_){ return 'null'; } })();
  var HOST_OK = /^https?:\/\//i.test(HOST_ORIGIN);
  var finalDone = false, lastHeight = 0, lastDelta = null, warnedVh = false, heightRaf = 0, errorCount = 0;
  var pendingRestore = null, lastHtml = null, listeners = [];
  var dclSeen = document.readyState !== 'loading', loadSeen = document.readyState === 'complete';
  document.addEventListener('DOMContentLoaded', function(){ dclSeen = true; });
  window.addEventListener('load', function(){ dclSeen = true; loadSeen = true; scheduleHeight(true); });
  function post(msg){ try{ host.postMessage(Object.assign({iui:1}, msg), HOST_OK ? HOST_ORIGIN : '*'); }catch(_){} }

  // Make common model habits harmless in an opaque origin.
  function memoryStorage(){
    var data = {};
    return { getItem:function(k){ k=String(k); return Object.prototype.hasOwnProperty.call(data,k) ? data[k] : null; },
      setItem:function(k,v){ data[String(k)] = String(v); }, removeItem:function(k){ delete data[String(k)]; },
      clear:function(){ data = {}; }, key:function(i){ return Object.keys(data)[i] || null; },
      get length(){ return Object.keys(data).length; } };
  }
  ['localStorage','sessionStorage'].forEach(function(name){
    var ok = false; try{ ok = !!window[name] && (window[name].length >= 0); }catch(_){}
    if(!ok){ try{ Object.defineProperty(window, name, {value:memoryStorage(), configurable:true}); }catch(_){} }
  });
  document.write = document.writeln = function(){
    try{ root.insertAdjacentHTML('beforeend', Array.prototype.join.call(arguments, '')); }catch(_){}
  };
  ['alert','confirm','prompt'].forEach(function(n){ window[n] = function(){ post({type:'log', level:'warn', message:n+'() is not available'}); return n === 'confirm' ? false : null; }; });

  function readTheme(){
    var cs = getComputedStyle(document.documentElement), out = {};
    ['bg','surface','surface-2','fg','strong','muted','accent','accent-fg','border','good','warn','bad','info',
     'c1','c2','c3','c4','c5','c6','c7','c8'].forEach(function(k){ out[k.replace(/-([a-z0-9])/g,function(_,c){return c.toUpperCase();})] = cs.getPropertyValue('--sw-'+k).trim(); });
    out.mode = document.documentElement.getAttribute('data-theme') || 'dark';
    out.palette = [out.c1,out.c2,out.c3,out.c4,out.c5,out.c6,out.c7,out.c8];
    return out;
  }
  var api = {
    theme: null,
    sendPrompt: function(text){
      text = String(text == null ? '' : text).trim();
      if(!text) return false;
      post({type:'prompt', text:text.slice(0, 4000)});
      return true;
    },
    copy: function(text){ post({type:'copy', text:String(text == null ? '' : text).slice(0, 20000)}); },
    resize: function(){ scheduleHeight(true); },
    onTheme: function(cb){ if(typeof cb === 'function') listeners.push(cb); }
  };
  window.synthwave = api;
  // Compatibility with widgets written for Open Generative UI.
  window.Websandbox = {connection:{remote:{
    sendPrompt:function(o){ return Promise.resolve(api.sendPrompt(o && o.text != null ? o.text : o)); },
    openLink:function(o){ var u = String(o && o.url != null ? o.url : o || ''); if(/^https:\/\//i.test(u)) post({type:'open', url:u}); return Promise.resolve(true); }
  }}};

  function measure(){
    var b = document.body;
    return Math.ceil(Math.max(b.scrollHeight, b.offsetHeight, root.getBoundingClientRect().bottom + 14));
  }
  // Content sized to the frame (100vh, height:100%) would grow it forever:
  // a growth that tracks the viewport is ignored.
  function scheduleHeight(force){
    if(heightRaf) return;
    heightRaf = requestAnimationFrame(function(){
      heightRaf = 0;
      var h = measure(), vh = window.innerHeight || 0, delta = h - vh;
      var chasing = !force && h > lastHeight + 1 && lastDelta !== null && vh > 0 && Math.abs(delta - lastDelta) <= 2;
      if(chasing){
        if(!warnedVh){ warnedVh = true; post({type:'log', level:'warn', message:'Content is sized to the frame (100vh or 100%); give it a fixed height'}); }
        return;
      }
      if(force || Math.abs(h - lastHeight) > 1){ lastHeight = h; lastDelta = delta; post({type:'height', height:h}); }
    });
  }
  if(typeof ResizeObserver === 'function'){ new ResizeObserver(function(){ scheduleHeight(false); }).observe(document.body); }

  function reportError(message, detail){
    errorCount++;
    if(errorCount > 5) return;
    post({type:'error', message:String(message || 'Unknown error').slice(0, 300), detail:String(detail || '').slice(0, 800)});
  }
  window.addEventListener('error', function(e){
    if(e && e.target && e.target !== window && (e.target.src || e.target.href)){
      if(e.target.tagName === 'SCRIPT') reportError('Could not load ' + (e.target.src || e.target.href));
      return;
    }
    reportError(e && e.message, e && e.error && e.error.stack);
  }, true);
  window.addEventListener('unhandledrejection', function(e){ var r = e && e.reason; reportError(r && r.message || r, r && r.stack); });
  document.addEventListener('securitypolicyviolation', function(e){
    // The server also sends a report-only policy; those reports block nothing.
    if(e.disposition === 'report') return;
    if(/^(img|media|font)-src/.test(e.effectiveDirective || e.violatedDirective || '')) return;
    reportError('Blocked: ' + (e.blockedURI || e.violatedDirective), e.violatedDirective);
  });
  document.addEventListener('submit', function(e){ e.preventDefault(); }, false);
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if(!a) return;
    var href = a.getAttribute('href') || '';
    if(href.charAt(0) === '#') return;
    e.preventDefault();
    if(/^https?:\/\//i.test(href)) post({type:'open', url:href});
  }, true);
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') post({type:'key', key:'Escape'}); }, true);

  function syncRange(el){
    if(!el || el.type !== 'range') return;
    var min = +el.min || 0, max = el.max === '' ? 100 : +el.max, v = +el.value;
    var pct = max > min ? ((v - min) / (max - min)) * 100 : 0;
    el.style.setProperty('--sw-fill', Math.max(0, Math.min(100, pct)) + '%');
  }
  function syncAllRanges(){ Array.prototype.forEach.call(document.querySelectorAll('input[type=range]'), syncRange); }
  document.addEventListener('input', function(e){ syncRange(e.target); queueState(); }, true);
  document.addEventListener('change', function(e){ syncRange(e.target); queueState(); }, true);

  // Remember the user's settings so a re-rendered chat can put them back.
  var stateTimer = 0, restoring = false;
  function controls(){ return Array.prototype.filter.call(document.querySelectorAll('#iui-root input, #iui-root select, #iui-root textarea'), function(el){
    return (el.id || el.name) && el.type !== 'password' && el.type !== 'file' && el.type !== 'hidden'; }); }
  function keyOf(el){ return el.id ? '#' + el.id : (el.type === 'radio' ? 'r:' + el.name + ':' + el.value : 'n:' + el.name); }
  function snapshot(){
    var out = {};
    controls().forEach(function(el){ out[keyOf(el)] = (el.type === 'checkbox' || el.type === 'radio') ? !!el.checked : String(el.value).slice(0, 2000); });
    return out;
  }
  function queueState(){
    if(restoring || !finalDone) return;
    clearTimeout(stateTimer);
    stateTimer = setTimeout(function(){ post({type:'state', values:snapshot()}); }, 250);
  }
  function restore(values){
    if(!values || typeof values !== 'object') return;
    restoring = true;
    try{
      controls().forEach(function(el){
        var k = keyOf(el);
        if(!Object.prototype.hasOwnProperty.call(values, k)) return;
        var v = values[k];
        if(el.type === 'checkbox' || el.type === 'radio'){ if(el.checked === !!v) return; el.checked = !!v; }
        else { if(el.value === String(v)) return; el.value = String(v); }
        try{ el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }catch(err){ reportError(err && err.message, err && err.stack); }
      });
    } finally { restoring = false; syncAllRanges(); }
  }

  function applyTheme(vars, mode){
    var d = document.documentElement;
    if(vars && typeof vars === 'object'){
      Object.keys(vars).forEach(function(k){
        if(/^--sw-[a-z0-9-]+$/.test(k) && typeof vars[k] === 'string' && vars[k].length < 120) d.style.setProperty(k, vars[k]);
      });
    }
    if(mode === 'light' || mode === 'dark') d.setAttribute('data-theme', mode);
    api.theme = readTheme();
    listeners.forEach(function(cb){ try{ cb(api.theme); }catch(_){} });
  }
  function finish(){
    syncAllRanges(); setTimeout(syncAllRanges, 50);
    // Scripts arrive after the page loaded: replay the start events models listen for.
    if(dclSeen){ try{ document.dispatchEvent(new Event('DOMContentLoaded', {bubbles:true})); }catch(_){} }
    if(loadSeen){ try{ window.dispatchEvent(new Event('load')); }catch(_){} }
    if(pendingRestore){ restore(pendingRestore); pendingRestore = null; }
    post({type:'rendered'});
    lastDelta = null; scheduleHeight(true); setTimeout(function(){ scheduleHeight(true); }, 400);
  }
  function runScripts(list, i){
    if(i >= list.length){ finish(); return; }
    var item = list[i] || {}, el = document.createElement('script'), done = false;
    function next(){ if(done) return; done = true; runScripts(list, i + 1); }
    if(item.type === 'module') el.type = 'module';
    if(item.src){
      el.src = item.src; el.async = false; el.crossOrigin = 'anonymous';
      el.onload = next;
      el.onerror = function(){ reportError('Could not load ' + item.src); next(); };
      setTimeout(next, 10000);
      document.body.appendChild(el);
    } else if(item.type === 'module'){
      el.textContent = String(item.code || '');
      el.onload = next; el.onerror = next; setTimeout(next, 8000);
      try{ document.body.appendChild(el); }catch(err){ reportError(err && err.message, err && err.stack); next(); }
    } else {
      el.textContent = String(item.code || '');
      try{ document.body.appendChild(el); }catch(err){ reportError(err && err.message, err && err.stack); }
      next();
    }
  }
  function render(msg){
    if(finalDone) return;
    if(typeof msg.css === 'string') userStyle.textContent = msg.css;
    if(typeof msg.html === 'string' && (msg.final || msg.html !== lastHtml)){
      // Compare with what was sent last, not with innerHTML: re-setting the
      // same markup would reset what the user is typing while it streams.
      lastHtml = msg.html;
      root.innerHTML = msg.html;
      syncAllRanges();
    }
    scheduleHeight(false);
    if(msg.final){
      finalDone = true;
      pendingRestore = msg.restore && typeof msg.restore === 'object' ? msg.restore : null;
      runScripts(Array.isArray(msg.scripts) ? msg.scripts : [], 0);
    }
  }
  window.addEventListener('message', function(e){
    if(e.source !== host || (HOST_OK && e.origin !== HOST_ORIGIN)) return;
    var msg = e.data;
    if(!msg || msg.iui !== 1 || typeof msg.type !== 'string') return;
    if(msg.type === 'theme') applyTheme(msg.vars, msg.mode);
    else if(msg.type === 'render') render(msg);
    else if(msg.type === 'measure') scheduleHeight(true);
  });
  api.theme = readTheme();
  post({type:'ready'});
})();
"""

FRAME_HTML = (
    "<!doctype html>\n<html lang=\"nl\" data-theme=\"dark\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    "<meta name=\"referrer\" content=\"no-referrer\">"
    "<title>Interactieve weergave</title>"
    "<script type=\"importmap\">" + IMPORT_MAP + "</script>"
    "<style id=\"iui-base\">" + BASE_CSS + "</style>"
    "<style id=\"iui-user-style\"></style>"
    "</head><body><div id=\"iui-root\"></div>"
    "<script>" + SHELL_JS + "</script></body></html>\n"
)
FRAME_BYTES = FRAME_HTML.encode("utf-8")


def headers() -> list[tuple[str, str]]:
    return [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Security-Policy", FRAME_CSP),
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "SAMEORIGIN"),
        ("Referrer-Policy", "no-referrer"),
        ("Cache-Control", "no-store"),
        ("Permissions-Policy", PERMISSIONS_POLICY),
        ("Cross-Origin-Resource-Policy", "same-origin"),
    ]


def serve(handler, parsed) -> bool:
    """Serve the frame document; False for any other path."""
    path = str(getattr(parsed, "path", "") or "")
    if path.startswith("/session/"):
        path = path[len("/session"):]
    if path != FRAME_PATH or getattr(parsed, "params", ""):
        return False
    handler.send_response(200)
    for header, value in headers():
        handler.send_header(header, value)
    handler.send_header("Content-Length", str(len(FRAME_BYTES)))
    handler.end_headers()
    if getattr(handler, "command", "GET") == "HEAD":
        return True
    try:
        handler.wfile.write(FRAME_BYTES)
    except (BrokenPipeError, ConnectionResetError):
        pass
    return True


PROMPT = """
WebUI interactive answers:
- A fenced block with the info string interactive-ui renders as a live mini app (HTML, CSS, JavaScript) inside your reply. Use it only when trying things out beats reading: a calculator or what-if model with the user's numbers, a chart of real data from the conversation or tools, a comparison with filters or weights, a plan or timeline to explore, a map. Also when the user asks for something interactive, a dashboard, calculator or simulation. Otherwise answer in text, a markdown table or one mermaid diagram. At most one per reply. For a follow-up, answer in text unless the user asks to change the app.
- Order: <!-- title: Short title --> and <!-- height: 420 --> (expected height in px), then one <style>, then readable markup with real labels and default results, then <script> tags last. Markup shows while streaming; scripts run when the block is complete, after the page has loaded, so run setup code directly (DOMContentLoaded and load are replayed, but do not rely on them). Never close the block early; keep it under 25 KB.
- Scripts: plain inline scripts or <script src> from cdn.jsdelivr.net, unpkg.com, cdnjs.cloudflare.com or esm.sh only; anything else is removed. No Tailwind, Bootstrap, jQuery or font links: write plain CSS. Use addEventListener in the script rather than onclick attributes. Classic scripts cannot use top-level await or import; for modules use <script type="module"> with bare imports three, d3, gsap, chart.js or leaflet. No fetch to other hosts, no document.write, no alert, confirm or prompt; storage is temporary. Put all data inline.
- Layout: the frame grows to its content, so never size anything to 100vh, height:100% or innerHeight; give charts a fixed-height container (Chart.js with maintainAspectRatio:false inside a div of e.g. 260px). It must work at 360 px wide.
- Look: the frame already follows the chat theme. Use only the variables --sw-fg, --sw-strong, --sw-muted, --sw-surface, --sw-surface-2, --sw-border, --sw-accent, --sw-accent-soft, --sw-good, --sw-bad and the chart palette synthwave.theme.palette (in canvas use synthwave.theme.fg, muted and border). Never hardcode colours, greys, white or black, and never set a body background. Ready classes: .card .grid .row .stack .stat(.label .value) .badge .chip .bar .note, button.primary.
- Maps: Leaflet with tiles https://tile.openstreetmap.org/{z}/{x}/{y}.png and the tileLayer option referrerPolicy:'origin' (without it the tiles are refused), credit OpenStreetMap.
- Follow-ups: a button may call synthwave.sendPrompt("...") with the chosen values; the user confirms it before it is sent. synthwave.onTheme(cb) fires on a theme switch, redraw charts there.
- Content: labels in the user's language, Dutch number and currency format for Dutch users (Intl.NumberFormat('nl-NL')), real numbers, assumptions labelled as examples in the app itself. Always add one or two sentences outside the block with the takeaway.
- For templates load the skill interactive-ui when it is available.
""".strip()


def _parse_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0 if value in (0, 1) else None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
    return None


def enabled(config_data=None) -> bool:
    env_value = _parse_flag(os.environ.get(ENV_VAR))
    if env_value is not None:
        return env_value
    if isinstance(config_data, dict):
        config_value = _parse_flag(config_data.get(CONFIG_KEY))
        if config_value is not None:
            return config_value
    return DEFAULT_ENABLED


def prompt_block(config_data=None) -> str:
    return PROMPT if enabled(config_data) else ""
