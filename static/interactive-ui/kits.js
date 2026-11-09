// Data blocks: the kit frame (shell plus the table, chart, map, kpi and
// timeline renderers).
//
// Runs inside static/interactive-ui/kit.html, which api/interactive_ui.py
// serves with its own CSP: `sandbox allow-scripts` (an opaque origin, no
// popups), scripts only by sha256 hash, no network except map tiles and
// Wikimedia photos. The chat sends one message type with data, `kit`
// ({kit, spec, data, final, restore, lang}); there is no path for HTML or
// scripts. Every value is put on the page with textContent or as a DOM
// property; links leave through the chat's https-only `open` message.
//
// The spec was already checked by SWKit.build() in the chat; this file still
// re-checks what it draws on a map (finite coordinates, the photo host, the
// tile template), because those reach the network.

(function(){
  'use strict';
  var K = window.SWKit;
  var root = document.getElementById('kit-root');
  var host = window.parent;
  var DOC = window.__SWKIT_DOC || null;  // only set in a downloaded copy
  var standalone = !host || host === window;
  if(standalone && !DOC){ root.textContent = 'Open deze weergave vanuit de chat.'; return; }
  var HOST_ORIGIN = (function(){ try{ return new URL(location.href).origin; }catch(_){ return 'null'; } })();
  var HOST_OK = /^https?:\/\//i.test(HOST_ORIGIN);
  var CAP = 0, LANG = 'nl', FULL = false, current = null, lastMsg = null, lastHeight = 0, heightRaf = 0, errorCount = 0;
  var REDUCED = false;
  try{ REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches; }catch(_){}

  function post(msg){
    if(standalone) return;
    try{ host.postMessage(Object.assign({iui:1}, msg), HOST_OK ? HOST_ORIGIN : '*'); }catch(_){}
  }

  // ── Text ────────────────────────────────────────────────────────────────
  var TEXT = {
    nl:{search:'Zoek in tabel', showAll:function(n){ return 'Toon alle ' + n + ' rijen'; }, total:'Totaal',
      count:function(a,b){ return a + ' van ' + b + ' rijen'; }, empty:'Geen rijen', noMatch:'Geen rijen gevonden',
      sortHint:'Sorteren', view:'Weergave', chart:'Grafiek', table:'Tabel',
      chartFail:'Grafiek kon niet laden, hier zijn de cijfers.', places:function(n){ return n === 1 ? '1 locatie' : n + ' locaties'; },
      route:'Route', replay:'Opnieuw afspelen', status:function(i,n,name){ return 'Locatie ' + i + ' van ' + n + ': ' + name; },
      routeNote:'De lijn toont alleen de volgorde, niet de weg.', approx:'Sommige locaties zijn bij benadering.',
      unresolved:'Niet op de kaart gevonden', later:'Wordt nog opgezocht', pendingHead:'Nog niet op de kaart', gaveUp:'Kon nu niet worden opgezocht', tilesFail:'De kaart laadt nu niet. De lijst klopt wel.',
      google:'Open in Google Maps', copyAddr:'Kopieer adressen', photo:function(a,l){ return 'Foto: ' + a + ', ' + l; },
      more:'Meer info', approxPin:'bij benadering', mapLabel:'Kaart', listLabel:'Locaties',
      good:'gunstig', bad:'ongunstig', flat:'gelijk', target:function(p, t){ return p + ' van het doel van ' + t; }, limit:function(p, t){ return p + ' van het budget van ' + t; }, over:function(d, t){ return d + ' boven het budget van ' + t; },
      limitMax:function(p, t){ return p + ' van het maximum van ' + t; }, overMax:function(d, t){ return d + ' boven het maximum van ' + t; },
      today:'Vandaag', milestone:'Mijlpaal', tlLabel:'Planning', pick:'Kies een balk voor de details.'},
    en:{search:'Search table', showAll:function(n){ return 'Show all ' + n + ' rows'; }, total:'Total',
      count:function(a,b){ return a + ' of ' + b + ' rows'; }, empty:'No rows', noMatch:'No rows found',
      sortHint:'Sort', view:'View', chart:'Chart', table:'Table',
      chartFail:'The chart could not load, here are the numbers.', places:function(n){ return n === 1 ? '1 place' : n + ' places'; },
      route:'Route', replay:'Play again', status:function(i,n,name){ return 'Place ' + i + ' of ' + n + ': ' + name; },
      routeNote:'The line shows the order, not the road.', approx:'Some places are approximate.',
      unresolved:'Not found on the map', later:'Still being looked up', pendingHead:'Not on the map yet', gaveUp:'Could not be looked up right now', tilesFail:'The map does not load right now. The list is correct.',
      google:'Open in Google Maps', copyAddr:'Copy addresses', photo:function(a,l){ return 'Photo: ' + a + ', ' + l; },
      more:'More info', approxPin:'approximate', mapLabel:'Map', listLabel:'Places',
      good:'favourable', bad:'unfavourable', flat:'unchanged', target:function(p, t){ return p + ' of target ' + t; }, limit:function(p, t){ return p + ' of budget ' + t; }, over:function(d, t){ return d + ' over budget ' + t; },
      limitMax:function(p, t){ return p + ' of the limit of ' + t; }, overMax:function(d, t){ return d + ' over the limit of ' + t; },
      today:'Today', milestone:'Milestone', tlLabel:'Timeline', pick:'Choose a bar for the details.'}
  };
  function PHONE(){ return (window.innerWidth || 0) < 640 || !!(window.matchMedia && window.matchMedia('(pointer:coarse)').matches); }
  function T(key){ var v = (TEXT[LANG] || TEXT.nl)[key]; var args = Array.prototype.slice.call(arguments, 1); return typeof v === 'function' ? v.apply(null, args) : v; }
  function h(tag, cls, text){ var e = document.createElement(tag); if(cls) e.className = cls; if(text != null) e.textContent = String(text); return e; }
  function fmt(v, type, decimals){ return K.formatValue(v, type, decimals, LANG); }
  // When a place is named after its street address, show the address only once.
  function addrAfterName(name, addr){
    var n = String(name || '').trim().toLowerCase(), a = String(addr || '').trim();
    if(!n || !a) return a;
    if(a.toLowerCase() === n) return '';
    if(a.toLowerCase().indexOf(n) === 0) return a.slice(n.length).replace(/^[\s,;·-]+/, '');
    return a;
  }
  // The target bar already states the goal or budget: a note that only repeats it is dropped.
  function noteRepeatsTarget(note, target, value){
    if(target === null || target === undefined || !isFinite(target)) return false;
    var wants = [String(Math.round(Math.abs(target)))];
    if(isFinite(value) && value !== target) wants.push(String(Math.round(Math.abs(value - target))));
    wants = wants.filter(function(w){ return w.length >= 3; });
    if(!wants.length) return false;
    var nums = String(note).match(/\d[\d.,\s\u00a0\u202f]*\d|\d/g) || [];
    for(var i = 0; i < nums.length; i++){
      var n = nums[i].replace(/[\s\u00a0\u202f]/g, '');
      var whole = n.replace(/[.,]\d{1,2}$/, '').replace(/[.,]/g, '');
      if(wants.indexOf(whole) >= 0) return true;
      var k = n.match(/^(\d+)(?:[.,](\d+))?$/);
      if(k && /\bk\b|duizend|thousand/i.test(note) && wants.indexOf(String(Math.round(parseFloat(k[1] + '.' + (k[2] || '0')) * 1000))) >= 0) return true;
    }
    return false;
  }

  // ── Bridge ──────────────────────────────────────────────────────────────
  function deepFreeze(o){
    if(o && typeof o === 'object' && !Object.isFrozen(o)){ Object.freeze(o); Object.keys(o).forEach(function(k){ deepFreeze(o[k]); }); }
    return o;
  }
  var listeners = [];
  // The chart palette starts with the chat's own accent, so series 1 matches KPI,
  // funnel and compare; a default colour too close to that accent is left out.
  var BASE_PAL = ['#f97316','#3b82f6','#22c55e','#a855f7','#eab308','#ec4899','#14b8a6','#94a3b8'];
  function hueOf(c){
    var m = /^#([0-9a-f]{6})$/i.exec(String(c).trim()), r, g, b;
    if(m){ r = parseInt(m[1].slice(0, 2), 16); g = parseInt(m[1].slice(2, 4), 16); b = parseInt(m[1].slice(4), 16); }
    else { m = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/i.exec(String(c)); if(!m) return null; r = +m[1]; g = +m[2]; b = +m[3]; }
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if(d < 20) return null;
    var h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return (h * 60 + 360) % 360;
  }
  function rebasePalette(){
    var d = document.documentElement, accent = getComputedStyle(d).getPropertyValue('--sw-accent').trim();
    var ha = hueOf(accent);
    if(ha === null) return;
    var rest = BASE_PAL.filter(function(c){ var h = hueOf(c); if(h === null) return true; var dist = Math.abs(h - ha); return Math.min(dist, 360 - dist) > 32; });
    [accent].concat(rest).slice(0, 8).forEach(function(c, i){ d.style.setProperty('--sw-c' + (i + 1), c); });
  }
  function readTheme(){
    var cs = getComputedStyle(document.documentElement), out = {};
    ['bg','surface','surface-2','fg','strong','muted','accent','accent-fg','border','good','warn','bad','info',
     'c1','c2','c3','c4','c5','c6','c7','c8'].forEach(function(k){ out[k.replace(/-([a-z0-9])/g, function(_, c){ return c.toUpperCase(); })] = cs.getPropertyValue('--sw-' + k).trim(); });
    out.mode = document.documentElement.getAttribute('data-theme') || 'dark';
    out.palette = [out.c1, out.c2, out.c3, out.c4, out.c5, out.c6, out.c7, out.c8];
    return out;
  }
  var api = {
    theme: readTheme(), data: null, spec: null,
    open: function(url){
      url = String(url || '');
      if(!/^https:\/\//i.test(url)) return;
      if(standalone){ try{ window.open(url, '_blank', 'noopener,noreferrer'); }catch(_){} return; }
      post({type:'open', url:url});
    },
    copy: function(text){
      text = String(text == null ? '' : text).slice(0, 20000);
      if(standalone){ try{ navigator.clipboard.writeText(text); }catch(_){} return; }
      post({type:'copy', text:text});
    },
    resize: function(){ scheduleHeight(true); },
    onTheme: function(cb){ if(typeof cb === 'function') listeners.push(cb); }
  };
  window.synthwave = api;

  function measure(){ var b = document.body; return Math.ceil(Math.max(b.scrollHeight, b.offsetHeight, root.getBoundingClientRect().bottom + 14)); }
  function scheduleHeight(force){
    if(heightRaf) return;
    heightRaf = requestAnimationFrame(function(){
      heightRaf = 0;
      var hgt = measure();
      if(force || Math.abs(hgt - lastHeight) > 1){ lastHeight = hgt; post({type:'height', height:hgt}); }
    });
  }
  if(typeof ResizeObserver === 'function') new ResizeObserver(function(){ scheduleHeight(false); }).observe(document.body);
  function reportError(message, detail){
    errorCount++;
    if(errorCount > 5) return;
    post({type:'error', message:String(message || 'Unknown error').slice(0, 300), detail:String(detail || '').slice(0, 800)});
  }
  window.addEventListener('error', function(e){
    if(e && e.target && e.target !== window && (e.target.src || e.target.href)) return;  // tiles and photos are handled where they load
    // A ResizeObserver loop notice is a harmless browser message, never a broken block.
    if(/^ResizeObserver loop/i.test(String(e && e.message || ''))) return;
    reportError(e && e.message, e && e.error && e.error.stack);
  }, true);
  window.addEventListener('unhandledrejection', function(e){ var r = e && e.reason; reportError(r && r.message || r, r && r.stack); });
  document.addEventListener('submit', function(e){ e.preventDefault(); }, true);
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if(!a) return;
    e.preventDefault();
    api.open(a.getAttribute('href') || '');
  }, true);
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') post({type:'key', key:'Escape'}); }, true);

  // Kinds in their own files (static/interactive-ui/kinds/*.js) register a
  // renderer here: render(box, spec, restore, ctx) -> {onTheme?}. They build the
  // DOM with ctx.h (textContent only), never with HTML from the spec.
  var RENDERERS = {};
  window.SWKitRender = {
    register: function(kind, fn){ if(/^[a-z][a-z-]{1,20}$/.test(kind) && typeof fn === 'function' && !RENDERERS[kind]) RENDERERS[kind] = fn; },
    h: function(tag, cls, text){ return h(tag, cls, text); },
    fmt: function(v, type, decimals){ return fmt(v, type, decimals); },
    lang: function(){ return LANG; },
    theme: function(){ return api.theme; },
    save: function(values){ saveState(values); },
    resize: function(){ scheduleHeight(true); },
    copy: function(text){ api.copy(text); },
    // On a phone, ask the chat to scroll so this element (a details line) is in view.
    reveal: function(el, from){ revealEl(el, from); }
  };
  // from: the tapped element; it must stay in view while the details come up.
  function revealEl(el, from){
    if(standalone || !el || (window.innerWidth || 0) >= 640) return;
    setTimeout(function(){
      // The chat decides how far to scroll, itself and this frame (it knows what is hidden).
      var r = el.getBoundingClientRect();
      var msg = {type:'reveal', y:Math.round(r.bottom + 8)};
      if(from && from.getBoundingClientRect) msg.from = Math.round(from.getBoundingClientRect().top);
      post(msg);
    }, 60);
  }

  var stateTimer = 0;
  function saveState(values){
    clearTimeout(stateTimer);
    stateTimer = setTimeout(function(){ post({type:'state', values:values}); }, 250);
  }
  function applyTheme(vars, mode){
    var d = document.documentElement;
    if(vars && typeof vars === 'object'){
      Object.keys(vars).forEach(function(k){
        if(/^--sw-[a-z0-9-]+$/.test(k) && typeof vars[k] === 'string' && vars[k].length < 120) d.style.setProperty(k, vars[k]);
      });
    }
    if(mode === 'light' || mode === 'dark') d.setAttribute('data-theme', mode);
    rebasePalette();
    api.theme = readTheme();
    listeners.forEach(function(cb){ try{ cb(api.theme); }catch(_){} });
    if(current && current.onTheme) try{ current.onTheme(); }catch(err){ reportError(err && err.message, err && err.stack); }
  }
  function setFull(on){
    on = !!on;
    if(on === FULL) return;
    FULL = on;
    document.documentElement.classList.toggle('is-full', on);
    if(current && current.onFull) try{ current.onFull(on); }catch(_){}
  }

  // ── Colours ─────────────────────────────────────────────────────────────
  function rgb(color){
    var c = String(color || '').trim(), m;
    if((m = /^#([0-9a-f]{3})$/i.exec(c))) return [parseInt(m[1][0] + m[1][0], 16), parseInt(m[1][1] + m[1][1], 16), parseInt(m[1][2] + m[1][2], 16)];
    if((m = /^#([0-9a-f]{6})/i.exec(c))) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)];
    if((m = /rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i.exec(c))) return [+m[1], +m[2], +m[3]];
    return null;
  }
  function alpha(color, a){ var v = rgb(color); return v ? 'rgba(' + v[0] + ',' + v[1] + ',' + v[2] + ',' + a + ')' : color; }

  // ── Table ───────────────────────────────────────────────────────────────
  function shortUrl(u){
    try{ var x = new URL(u); var s = x.host.replace(/^www\./, '') + (x.pathname === '/' ? '' : x.pathname); return s.length > 42 ? s.slice(0, 41) + '…' : s; }catch(_){ return u; }
  }
  function cellNode(td, v, col, tones){
    var type = col.type;
    if(v === null || v === undefined || v === ''){ td.textContent = ''; return; }
    if(type === 'number' || type === 'currency' || type === 'percent'){
      td.className = 'num';
      td.textContent = typeof v === 'number' ? fmt(v, type, col.decimals) : String(v);
      return;
    }
    if(type === 'status'){
      var tone = tones[String(v).toLowerCase()] || '';
      var pill = h('span', 'k-pill' + (tone ? ' tone-' + tone : ''), v);
      td.appendChild(pill);
      return;
    }
    if(type === 'link' && typeof v === 'string' && /^https:\/\/[^\s]+$/i.test(v)){
      var a = h('a', 'k-link', shortUrl(v));
      a.href = v; a.title = v; a.rel = 'noopener noreferrer';
      td.appendChild(a);
      return;
    }
    td.textContent = fmt(v, type, col.decimals);
  }
  function renderTable(box, spec, view, opt){
    opt = opt || {};
    var wrap = h('div', 'k-table');
    var search = null, count = null;
    if(spec.filter && !opt.compact){
      var tools = h('div', 'k-tools');
      search = h('input', 'k-search');
      search.type = 'search'; search.placeholder = T('search'); search.setAttribute('aria-label', T('search'));
      search.value = view.q || ''; search.maxLength = 120; search.autocomplete = 'off';
      count = h('span', 'k-count');
      count.setAttribute('aria-live', 'polite');
      tools.append(search, count);
      wrap.appendChild(tools);
    }
    var scroll = h('div', 'k-scroll');
    scroll.tabIndex = 0; scroll.setAttribute('role', 'region'); scroll.setAttribute('aria-label', spec.title || T('table'));
    var table = h('table', 'k-grid');
    var thead = h('thead'), headRow = h('tr'), tbody = h('tbody'), tfoot = spec.total ? h('tfoot') : null;
    var ths = spec.columns.map(function(col, ci){
      var th = h('th', (col.type === 'number' || col.type === 'currency' || col.type === 'percent') ? 'num' : '');
      th.scope = 'col';
      if(ci === 0) th.classList.add('k-first');
      var b = h('button', 'k-sort');
      b.type = 'button';
      b.appendChild(h('span', 'k-sort-label', col.label));
      b.appendChild(h('span', 'k-sort-ico'));
      b.title = T('sortHint');
      b.addEventListener('click', function(){
        var s = view.s;
        if(s && s[0] === ci) view.s = s[1] === 'asc' ? [ci, 'desc'] : null;
        else view.s = [ci, 'asc'];
        changed();
      });
      th.appendChild(b);
      headRow.appendChild(th);
      return th;
    });
    thead.appendChild(headRow);
    table.append(thead, tbody);
    if(tfoot) table.appendChild(tfoot);
    scroll.appendChild(table);
    // More columns to the right: a soft edge and one plain line say so.
    var edge = h('div', 'k-scroll-edge');
    edge.appendChild(scroll);
    wrap.appendChild(edge);
    var moreCols = h('p', 'k-more-cols', LANG === 'nl' ? 'Veeg voor meer kolommen' : 'Swipe for more columns');
    moreCols.hidden = true;
    wrap.appendChild(moreCols);
    function edges(){
      // Snapping lines columns up just right of the sticky first column.
      var firstTh = ths[0];
      if(firstTh) scroll.style.scrollPaddingLeft = firstTh.offsetWidth + 'px';
      var over = scroll.scrollWidth - scroll.clientWidth > 2;
      edge.classList.toggle('has-right', over && scroll.scrollLeft < scroll.scrollWidth - scroll.clientWidth - 2);
      edge.classList.toggle('has-left', over && scroll.scrollLeft > 2);
      moreCols.hidden = !over || scroll.scrollLeft > 8;
    }
    scroll.addEventListener('scroll', edges, {passive:true});
    if(typeof ResizeObserver === 'function'){ var ero = new ResizeObserver(function(){ requestAnimationFrame(edges); }); ero.observe(scroll); }
    setTimeout(edges, 0);
    var more = h('button', 'k-more');
    more.type = 'button';
    // On a phone the whole table opens in full screen, so the chat never gets stuck in a long box.
    more.addEventListener('click', function(e){
      if(PHONE() && !FULL && !standalone){ if(e && e.isTrusted) post({type:'full'}); return; }
      view.all = true; changed();
    });
    wrap.appendChild(more);
    if(spec.source && !opt.noSource) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    function changed(){ draw(); if(opt.onChange) opt.onChange(view); }
    function draw(){
      var idx = K.viewIndices(spec, view, LANG);
      // On a phone: as many rows as fit the card (between 3 and 8), the button always in view.
      var phoneRows = 8;
      if(PHONE() && CAP > 0){ var chrome = (spec.filter ? 48 : 0) + 44 + 52 + (spec.subtitle ? 24 : 0) + (spec.total ? 37 : 0) + 30; phoneRows = Math.max(3, Math.min(8, Math.floor((CAP - chrome) / 46))); }
      var limit = (view.all || FULL || opt.all) ? idx.length : Math.min(idx.length, PHONE() ? phoneRows : 50);
      tbody.textContent = '';
      var frag = document.createDocumentFragment();
      for(var r = 0; r < limit; r++){
        var row = spec.rows[idx[r]], tr = h('tr');
        for(var c = 0; c < spec.columns.length; c++){
          var td = h(c === 0 ? 'th' : 'td');
          if(c === 0){ td.scope = 'row'; }
          cellNode(td, row[c], spec.columns[c], spec.tones || {});
          if(c === 0) td.classList.add('k-first');
          tr.appendChild(td);
        }
        frag.appendChild(tr);
      }
      if(!idx.length){
        var tr0 = h('tr', 'k-empty'), td0 = h('td', '', spec.rows.length ? T('noMatch') : T('empty'));
        td0.colSpan = spec.columns.length; tr0.appendChild(td0); frag.appendChild(tr0);
      }
      tbody.appendChild(frag);
      if(tfoot){
        tfoot.textContent = '';
        var sums = K.totals(spec, idx), tr1 = h('tr');
        spec.columns.forEach(function(col, ci){
          var cell = h(ci === 0 ? 'th' : 'td');
          if(ci === 0){ cell.scope = 'row'; cell.classList.add('k-first'); cell.textContent = T('total'); }
          else if(sums[ci] !== null){ cell.className = 'num'; cell.textContent = fmt(sums[ci], col.type, col.decimals); }
          tr1.appendChild(cell);
        });
        tfoot.appendChild(tr1);
      }
      // Too little room (a phone with the keyboard open): only one line and the button.
      var compact = PHONE() && CAP > 0 && CAP < 230 && !FULL && !opt.all;
      wrap.classList.toggle('is-compact', compact);
      more.hidden = !compact && limit >= idx.length;
      more.textContent = compact ? (LANG === 'nl' ? 'Bekijk tabel (' + idx.length + ' rijen)' : 'View table (' + idx.length + ' rows)') : T('showAll', idx.length);
      if(count) count.textContent = view.q ? T('count', idx.length, spec.rows.length) : '';
      ths.forEach(function(th, ci){
        var dir = view.s && view.s[0] === ci ? view.s[1] : '';
        th.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : dir === 'desc' ? 'descending' : 'none');
      });
      scheduleHeight(false);
    }
    if(search){
      var t = 0;
      search.addEventListener('input', function(){
        clearTimeout(t);
        t = setTimeout(function(){ view.q = search.value.slice(0, 120); changed(); }, 120);
      });
    }
    draw();
    return {onFull:function(){ draw(); }, redraw:draw};
  }

  // ── Chart ───────────────────────────────────────────────────────────────
  function chartTableSpec(spec){
    return {title:spec.title, source:'', filter:false, total:false, tones:{}, sort:null,
      columns:[{label:LANG === 'nl' ? 'Categorie' : 'Label', type:'text', decimals:null}].concat(spec.series.map(function(s){ return {label:s.name, type:spec.format, decimals:spec.decimals}; })),
      rows:spec.labels.map(function(l, i){ return [l].concat(spec.series.map(function(s){ return s.data[i]; })); })};
  }
  function renderChart(box, spec, view){
    view.v = view.v === 'table' ? 'table' : 'chart';
    var round = spec.type === 'pie' || spec.type === 'donut';
    var wrap = h('div', 'k-chart');
    var bar = h('div', 'k-tools');
    var seg = h('div', 'k-seg');
    seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', T('view'));
    var bChart = h('button', '', T('chart')), bTable = h('button', '', T('table'));
    bChart.type = bTable.type = 'button';
    seg.append(bChart, bTable);
    bar.appendChild(seg);
    var canvasBox = h('div', 'k-canvas');
    canvasBox.style.height = spec.height + 'px';
    // Lying bars on a phone need room per name.
    if((spec.type === 'bar' || spec.type === 'stacked' || spec.type === 'hbar') && (box.clientWidth || window.innerWidth) < 480 && spec.labels.length > 4) canvasBox.style.height = Math.max(spec.height, 60 + spec.labels.length * 40) + 'px';
    // A radar on a phone follows the width, so the shape is not lost in empty space.
    if(spec.type === 'radar'){ var bw = box.clientWidth || window.innerWidth; if(bw < 480) canvasBox.style.height = Math.max(260, Math.round(bw * 0.86)) + 'px'; }
    var canvas = h('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', spec.title + ': ' + spec.labels.slice(0, 12).join(', '));
    canvasBox.appendChild(canvas);
    var legend = round ? h('ul', 'k-legend') : null;
    var tableBox = h('div', 'k-chart-table');
    var note = h('p', 'k-note', T('chartFail'));
    note.hidden = true;
    wrap.append(bar, note, canvasBox);
    if(legend) wrap.appendChild(legend);
    wrap.appendChild(tableBox);
    if(spec.source) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);
    renderTable(tableBox, chartTableSpec(spec), {s:null, q:'', all:true}, {compact:true, all:true, noSource:true});

    var chart = null, failed = false;
    function f(v){ return fmt(v, spec.format, spec.decimals); }
    function colors(){
      var t = readTheme();
      var pal = t.palette.map(function(c, i){ return c || ['#f97316','#3b82f6','#22c55e','#a855f7','#eab308','#ec4899','#14b8a6','#94a3b8'][i]; });
      return {t:t, pal:pal, accent:t.accent || pal[0], muted:alpha(t.muted || '#9aa1b2', 0.45)};
    }
    function config(){
      var c = colors(), t = c.t, hl = spec.highlight, hlSeries = hl && spec.series.some(function(s){ return s.name === hl; });
      var kind = spec.type === 'hbar' || spec.type === 'stacked' ? 'bar' : spec.type === 'area' ? 'line' : spec.type === 'donut' ? 'doughnut' : spec.type;
      // On a phone, many or long category names read better as lying bars.
      var narrowC = (box.clientWidth || window.innerWidth) < 480;
      var timeLike = !!spec.isoLabels || spec.labels.every(function(l){ return /^(\d{4}([-\/]\d{1,2}){0,2}|q[1-4]( \d{4})?|[a-z]{3,9}\.?( \d{4})?|week \d+|wk \d+|\d{1,2}[-\/]\d{1,2}|(ma|di|wo|do|vr|za|zo|mon|tue|wed|thu|fri|sat|sun)?\.? ?\d{1,2} [a-z]{3,9}\.?( \d{4})?)$/i.test(String(l).trim()); });
      var autoH = narrowC && (spec.type === 'bar' || spec.type === 'stacked') && !timeLike && (spec.labels.length > 4 || spec.labels.some(function(l){ return String(l).length > 10; }));
      var lineLike = spec.type === 'line' || spec.type === 'area';
      var radar = kind === 'radar';
      var datasets = spec.series.map(function(s, i){
        var color = hl ? (hlSeries ? (s.name === hl ? c.accent : c.muted) : c.pal[i % 8]) : c.pal[i % 8];
        var ds = {label:s.name, data:s.data.slice()};
        if(round){
          ds.backgroundColor = spec.labels.map(function(l, j){ return hl ? (l === hl ? c.accent : alpha(c.pal[j % 8], 0.35)) : c.pal[j % 8]; });
          ds.borderColor = t.surface || t.bg || '#171a23'; ds.borderWidth = 2; ds.hoverOffset = 6;
        } else if(radar){
          ds.borderColor = color; ds.backgroundColor = alpha(color, 0.16); ds.borderWidth = 2;
          ds.pointRadius = 3; ds.pointHoverRadius = 5; ds.pointBackgroundColor = color;
        } else if(kind === 'bar'){
          ds.backgroundColor = hl && !hlSeries && spec.series.length === 1 ? spec.labels.map(function(l){ return l === hl ? c.accent : c.muted; }) : color;
          ds.borderRadius = 4; ds.maxBarThickness = 48; ds.borderSkipped = false;
        } else {
          ds.borderColor = color; ds.backgroundColor = alpha(color, spec.type === 'area' ? 0.18 : 0.12);
          ds.fill = spec.type === 'area' ? (i === 0 ? 'origin' : '-1') : false;
          ds.tension = 0.3; ds.borderWidth = 2; ds.spanGaps = true;
          ds.pointRadius = spec.labels.length > 24 ? 0 : 3; ds.pointHoverRadius = 5;
          ds.pointBackgroundColor = color;
          if(hl && !hlSeries){ ds.pointRadius = spec.labels.map(function(l){ return l === hl ? 6 : (spec.labels.length > 24 ? 0 : 3); }); }
        }
        return ds;
      });
      var stacked = spec.type === 'stacked' || (spec.type === 'area' && spec.series.length > 1);
      var horizontal = spec.type === 'hbar' || autoH;
      var valueAxis = {stacked:stacked, beginAtZero:true, grid:{color:alpha(t.border || '#2a2f3d', 0.9), drawTicks:false}, border:{display:false},
        ticks:{color:t.muted, padding:6, maxRotation:0, maxTicksLimit:horizontal && narrowC ? 4 : 8, callback:function(v){ return fmt(v, spec.format, Number.isInteger(v) ? 0 : spec.decimals); }}};
      // The goal line always falls inside the chart.
      if(spec.target && Number.isFinite(spec.target.value)) valueAxis.suggestedMax = spec.target.value * 1.06;
      // Named categories are never skipped on a phone: they wrap instead (dates and months may skip).
      // A line keeps skipping names on a phone (its points are what matter); bars never skip.
      // A line or area always skips names when they do not fit; bars never skip.
      var catTicks = {color:t.muted, autoSkip:timeLike || lineLike, maxRotation:0, font:{size:narrowC ? 10.5 : 12}};
      if(!timeLike && !lineLike) catTicks.callback = function(v, i){ var l = this.getLabelForValue ? this.getLabelForValue(v) : spec.labels[i]; return wrapLabel(l, narrowC ? (horizontal ? 14 : 9) : 16); };
      var catAxis = {stacked:stacked, grid:{display:false}, border:{color:t.border}, ticks:catTicks};
      // A horizontal bar's name column takes at most 45% of the width.
      if(horizontal) catAxis.afterFit = function(sc){ var cap = Math.round((box.clientWidth || window.innerWidth) * 0.45); if(sc.width > cap) sc.width = cap; };
      if(spec.xLabel) (horizontal ? valueAxis : catAxis).title = {display:true, text:spec.xLabel, color:t.muted};
      if(spec.yLabel) (horizontal ? catAxis : valueAxis).title = {display:true, text:spec.yLabel, color:t.muted};
      var target = spec.target;
      var targetPlugin = {id:'swTarget',
        beforeDatasetsDraw:function(ch){
          if(!target) return;
          var sc = horizontal ? ch.scales.x : ch.scales.y, area = ch.chartArea, ctx = ch.ctx;
          if(!sc || !area) return;
          var p = sc.getPixelForValue(target.value);
          if(!Number.isFinite(p)) return;
          ctx.save();
          ctx.strokeStyle = t.muted || t.fg; ctx.globalAlpha = 0.7; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
          ctx.beginPath();
          if(horizontal){ ctx.moveTo(p, area.top); ctx.lineTo(p, area.bottom); } else { ctx.moveTo(area.left, p); ctx.lineTo(area.right, p); }
          ctx.stroke();
          ctx.restore();
        },
        afterDraw:function(ch){
          if(!target) return;
          var area = ch.chartArea, ctx = ch.ctx;
          if(!area) return;
          // A label that already names the amount is shown as it is.
          // Always the chart's own number format: 'Doel 130.000' becomes 'Doel € 130.000'.
          // Strip an amount the label already names ("Doel 130k", "Doel € 130.000"); a year like 2026 stays.
          var raw = String(target.label || ''), base = raw;
          var amountRe = /\(?\s*(k€|[€$£]?)\s*(\d[\d.,]*)\s*(k|duizend|thousand|mln\.?|mio|miljoen|million|m|mld\.?|miljard|bn|b|billion)?\b\.?\s*(%|euro|eur|k€)?\s*\)?/gi;
          base = raw.replace(amountRe, function(all, cur, num, unit, tail){
            // "130,000" is English thousands; the parser reads Dutch first.
            var n = /^\d{1,3}(,\d{3})+(\.\d+)?$/.test(num) ? Number(num.replace(/,/g, '')) : K.parseNumber(num).n;
            if(cur === 'k€') unit = unit || 'k';
            if(!Number.isFinite(n)) return all;
            var u = String(unit || '').toLowerCase().replace('.', ''), mult = !u ? 1 : /^(k|duizend|thousand)$/.test(u) ? 1e3 : /^(mld|miljard|bn|b|billion)$/.test(u) ? 1e9 : 1e6;
            var near = target.value && Math.abs(n * mult - target.value) <= Math.abs(target.value) * 0.25;
            // A year (2026) or another number stays; the goal's own amount goes.
            return near || ((cur || unit || tail) && !/^\d{4}$/.test(num)) ? ' ' : all;
          });
          // Leftovers of a written amount (",-", "~", "±", "/jaar", "USD", brackets) go too.
          base = base.replace(/\/\s*[\p{L}]+/gu, ' ').replace(/\b(usd|eur|euro|gbp|per year|per jaar|a year)\b/gi, ' ').replace(/[,.]-|[~±≈()€$£]/g, ' ');
          base = base.replace(/\s+/g, ' ').replace(/[:,.\s]+$/, '').trim();
          var label = (base ? base + ' ' : '') + f(target.value);
          ctx.save();
          ctx.font = '500 11px ' + (getComputedStyle(document.body).fontFamily || 'sans-serif');
          var tw = ctx.measureText(label).width, y = area.top - 10, xr = area.right;
          ctx.strokeStyle = t.muted || t.fg; ctx.globalAlpha = 0.8; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
          ctx.beginPath(); ctx.moveTo(xr - tw - 22, y); ctx.lineTo(xr - tw - 6, y); ctx.stroke();
          ctx.setLineDash([]); ctx.globalAlpha = 1;
          ctx.fillStyle = t.muted || t.fg; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
          ctx.fillText(label, xr, y);
          ctx.restore();
        }};
      var cfg = {type:kind, data:{labels:spec.labels.slice(), datasets:datasets}, plugins:[targetPlugin],
        options:{responsive:true, maintainAspectRatio:false, animation:REDUCED ? false : {duration:500},
          indexAxis:horizontal ? 'y' : 'x', interaction:{mode:round ? 'nearest' : 'index', intersect:round},
          layout:{padding:{top:target ? 22 : 4, right:8}},
          plugins:{legend:{display:!round && spec.series.length > 1, position:'bottom', labels:{color:t.fg, font:{size:12}, boxWidth:8, boxHeight:8, usePointStyle:true, pointStyle:'rectRounded', pointStyleWidth:10, padding:16}},
            tooltip:{backgroundColor:t.surface2 || t.surface, titleColor:t.strong || t.fg, bodyColor:t.fg, borderColor:t.border, borderWidth:1, padding:10,
              callbacks:{label:function(ctx){
                var v = ctx.parsed && (round ? ctx.parsed : radar ? ctx.parsed.r : (horizontal ? ctx.parsed.x : ctx.parsed.y));
                var name = round ? ctx.label : ctx.dataset.label;
                return ' ' + name + ': ' + f(typeof v === 'number' ? v : ctx.raw);
              }}}}}};
      if(round){ if(kind === 'doughnut'){ cfg.options.cutout = '62%'; cfg.plugins.push(centerPlugin(t)); } }
      else if(radar){
        cfg.options.interaction = {mode:'nearest', intersect:false};
        // The outer ring is the scale the scores are on ("op 10"), never just the highest score.
        var all = [].concat.apply([], spec.series.map(function(s){ return s.data.filter(function(v){ return typeof v === 'number'; }); }));
        var top = Math.max.apply(null, all.concat([0])), low = Math.min.apply(null, all.concat([0]));
        // A 1 to 5 scale is named in the title or subtitle ("op 5", "1 tot 5", "1-5").
        var five = /(op|uit|of|out of)\s*5\b|\b1\s*(tot|-|to|t\/m)\s*5\b|\/\s*5\b/i.test((spec.title || '') + ' ' + (spec.subtitle || ''));
        var rMax = spec.max || (spec.format === 'percent' ? 100 : (low >= 0 && top <= 5 && five ? 5 : (low >= 0 && top <= 10 ? 10 : (low >= 0 && top <= 100 && top > 10 ? 100 : undefined))));
        var narrow = (box.clientWidth || window.innerWidth) < 480;
        // On a phone long criterion names do not fit around the shape: number the
        // axes and list the full names under the chart instead of cutting them.
        var numbered = narrow && spec.labels.some(function(l){ return String(l).length > 18 || String(l).split(/\s+/).some(function(w){ return w.length > 12; }); });
        if(numbered) radarKey();
        cfg.options.scales = {r:{beginAtZero:true, max:rMax, angleLines:{color:alpha(t.border || '#2a2f3d', 0.9)}, grid:{color:alpha(t.border || '#2a2f3d', 0.9)},
          pointLabels:{color:t.fg, font:{size:narrow ? 10.5 : 12}, padding:narrow ? 3 : 8,
            // Long criterion names wrap at words (a very long word gets a hyphen) instead of being cut.
            callback:function(l, i){ return numbered ? String(i + 1) : wrapLabel(l, narrow ? 11 : 16); }},
          ticks:{display:false, maxTicksLimit:5, stepSize:rMax === 10 ? 2 : rMax === 5 ? 1 : undefined}}};
      }
      else cfg.options.scales = horizontal ? {x:valueAxis, y:catAxis} : {x:catAxis, y:valueAxis};
      return cfg;
    }
    function radarKey(){
      if(wrap.querySelector('.k-radar-key')) return;
      var ol = h('ol', 'k-radar-key');
      spec.labels.forEach(function(l){ ol.appendChild(h('li', '', l)); });
      canvasBox.insertAdjacentElement('afterend', ol);
    }
    // Break a long Dutch compound before a familiar last part: "Implementatie-snelheid".
    var TAILS = ['betrouwbaarheid','tevredenheid','dienstverlening','snelheid','kwaliteit','zekerheid','baarheid','verlening','onderzoek','gesprek','overleg','analyse','niveau','kosten','beheer','planning','termijn','ervaring','verhouding','heid','tijd','prijs','proces'];
    function splitAt(w){
      // An existing hyphen is the best place to break.
      var hy = w.indexOf('-');
      if(hy >= 3 && hy < w.length - 3) return hy + 1;
      var lw = w.toLowerCase();
      for(var i = 0; i < TAILS.length; i++){
        var k = lw.lastIndexOf(TAILS[i]);
        if(k >= 4 && k + TAILS[i].length === lw.length && TAILS[i].length >= 4) return k;
      }
      for(var j = 0; j < TAILS.length; j++){
        var m = lw.indexOf(TAILS[j], 4);
        if(m >= 4 && lw.length - m >= 4) return m;
      }
      return 0;
    }
    function wrapLabel(l, max){
      var words = [];
      String(l || '').split(/\s+/).filter(Boolean).forEach(function(w){
        for(var guard = 0; w.length > max + 2 && guard < 4; guard++){ var at = splitAt(w); if(!(at > 0 && at < w.length)) break; var head = w.slice(0, at); words.push(/-$/.test(head) ? head : head + '-'); w = w.slice(at); }
        words.push(w);
      });
      var lines = [], cur = '';
      words.forEach(function(w){ var glue = /-$/.test(cur) ? '' : ' '; if(cur && (cur + glue + w).length > max){ lines.push(cur); cur = w; } else cur = cur ? cur + glue + w : w; });
      if(cur) lines.push(cur);
      // More than three lines: the third ends with an ellipsis (the full name is in the tooltip and table).
      if(lines.length > 3){ lines = lines.slice(0, 3); lines[2] = lines[2].replace(/[-\s]*$/, '') + '…'; }
      return lines.length > 1 ? lines : lines[0] || '';
    }
    // The middle of a donut names the total, so the slices read as parts of it.
    function centerPlugin(t){
      return {id:'swCenter', afterDraw:function(ch){
        if(spec.format === 'percent') return;
        var s = spec.series[0], sum = s.data.reduce(function(a, v){ return a + (v || 0); }, 0), area = ch.chartArea;
        if(!area || !(sum > 0)) return;
        var ctx = ch.ctx, cx = (area.left + area.right) / 2, cy = (area.top + area.bottom) / 2;
        var font = getComputedStyle(document.body).fontFamily || 'sans-serif';
        var r = Math.min(area.right - area.left, area.bottom - area.top) / 2 * 0.62;
        var big = Math.max(12, Math.min(22, r / 3.2));
        ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = t.strong || t.fg; ctx.font = '700 ' + big + 'px ' + font;
        ctx.fillText(f(sum), cx, cy - big * 0.35);
        ctx.fillStyle = t.muted || t.fg; ctx.font = '500 ' + Math.max(10, big * 0.55) + 'px ' + font;
        ctx.fillText(T('total'), cx, cy + big * 0.75);
        ctx.restore();
      }};
    }
    function drawLegend(){
      if(!legend) return;
      legend.textContent = '';
      var c = colors(), s = spec.series[0], sum = s.data.reduce(function(a, v){ return a + (v || 0); }, 0);
      // Percentages that already add up to 100 need no share next to them.
      var whole = spec.format === 'percent' && Math.abs(sum - 100) < 0.6;
      spec.labels.forEach(function(l, j){
        var li = h('li'), sw = h('span', 'k-swatch');
        sw.style.background = spec.highlight ? (l === spec.highlight ? c.accent : alpha(c.pal[j % 8], 0.35)) : c.pal[j % 8];
        var v = s.data[j];
        var share = sum > 0 && v > 0 ? v / sum * 100 : 0;
        var shareText = share > 0 && share < 0.5 ? (LANG === 'nl' ? '<1%' : '<1%') : fmt(Math.round(share), 'percent', 0);
        li.append(sw, h('span', 'k-legend-label', l), h('span', 'k-legend-value', v == null ? '' : f(v) + (sum > 0 && !whole ? ' (' + shareText + ')' : '')));
        legend.appendChild(li);
      });
    }
    function build(){
      if(chart || failed) return;
      try{
        if(typeof Chart !== 'function') throw new Error('Chart.js is not available');
        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
        Chart.defaults.color = readTheme().muted;
        chart = new Chart(canvas, config());
        drawLegend();
      }catch(err){ fail(err); }
    }
    function fail(err){
      if(failed) return;
      failed = true;
      try{ if(chart) chart.destroy(); }catch(_){}
      chart = null;
      note.hidden = false;
      bChart.disabled = true;
      setView('table', true);
      post({type:'log', level:'warn', message:'chart fallback: ' + String(err && err.message || err).slice(0, 200)});
    }
    function setView(v, quiet){
      view.v = v;
      bChart.setAttribute('aria-pressed', String(v === 'chart'));
      bTable.setAttribute('aria-pressed', String(v === 'table'));
      canvasBox.hidden = v !== 'chart';
      if(legend) legend.hidden = v !== 'chart';
      tableBox.hidden = v !== 'table';
      if(v === 'chart') build();
      if(!quiet) saveState({v:v});
      scheduleHeight(true);
    }
    bChart.addEventListener('click', function(){ if(!failed) setView('chart'); });
    bTable.addEventListener('click', function(){ setView('table'); });
    setView(view.v, true);
    setTimeout(function(){ if(view.v === 'chart' && !failed && (!chart || !chart.chartArea)) fail(new Error('the chart did not draw within 8 s')); }, 8000);
    return {
      onTheme:function(){ if(chart){ chart.destroy(); chart = null; build(); } else drawLegend(); },
      onFull:function(){ canvasBox.style.height = FULL ? 'calc(100vh - 150px)' : spec.height + 'px'; if(chart) chart.resize(); }
    };
  }

  // ── Map ─────────────────────────────────────────────────────────────────
  var PHOTO_PREFIX = 'https://upload.wikimedia.org/wikipedia/commons/';
  var CREDIT_PREFIX = 'https://commons.wikimedia.org/wiki/File:';
  function photoOf(r){
    var p = r && r.photo;
    if(!p || typeof p !== 'object') return null;
    if(typeof p.url !== 'string' || p.url.indexOf(PHOTO_PREFIX) !== 0 || /[\s"'<>\\]/.test(p.url)) return null;
    var credit = typeof p.credit_url === 'string' && p.credit_url.indexOf(CREDIT_PREFIX) === 0 ? p.credit_url : '';
    var artist = typeof p.artist === 'string' ? p.artist.slice(0, 120) : '', license = typeof p.license === 'string' ? p.license.slice(0, 60) : '';
    if(!artist || !license) return null;
    return {url:p.url, credit:credit, artist:artist, license:license};
  }
  function inRange(lat, lng){ return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180; }
  function renderMap(box, spec, view, data){
    data = data && typeof data === 'object' ? data : K.mapLocalData(spec);
    var byK = {};
    (Array.isArray(data.places) ? data.places : []).forEach(function(p){ if(p && typeof p.k === 'string') byK[p.k] = p; });
    var tiles = data.tiles && K.tileUrlOk(data.tiles.url) ? data.tiles : K.OSM_TILES;
    var items = spec.places.map(function(p){
      var r = byK[p.k] || {}, lat = Number(r.lat), lng = Number(r.lng);
      var ok = r.status === 'ok' && inRange(lat, lng);
      return {p:p, r:r, ll:ok ? [lat, lng] : null, approx:ok && (r.precision === 'street' || r.precision === 'place' || r.precision === 'city'),
        photo:photoOf(r), later:r.status === 'later'};
    });
    var onMap = items.filter(function(x){ return x.ll; }), missing = items.filter(function(x){ return !x.ll; });
    // Tiles from this server: the calm grey Kadaster map when every place is in
    // the Netherlands, OpenStreetMap otherwise.
    var localStyle = '';
    if(tiles.url === 'local'){
      var inNl = onMap.every(function(x){ return x.ll[0] > 50.6 && x.ll[0] < 53.7 && x.ll[1] > 3.2 && x.ll[1] < 7.3; });
      localStyle = inNl ? 'nl' : 'world';
      var base = String(location.href).split(/[?#]/)[0].replace(/[^\/]*$/, '');
      tiles = {url:base + 'tiles/' + localStyle + '/{z}/{x}/{y}.png', maxZoom:19,
        attribution:localStyle === 'nl' ? (LANG === 'nl' ? 'Kaart: Kadaster / PDOK' : 'Map: Kadaster / PDOK') : ''};
    }
    var isOsm = localStyle === 'world' || /^https:\/\/tile\.openstreetmap\.org\//.test(tiles.url);
    var route = spec.kind === 'route' && onMap.length >= 2;
    var cats = spec.categories || [];

    var wrap = h('div', 'k-map' + (route ? ' is-route' : '') + (localStyle ? ' tiles-' + localStyle : ''));
    var head = h('div', 'k-tools');
    if(cats.length){
      var legendEl = h('div', 'k-cats');
      cats.forEach(function(c, i){ var s = h('span', 'k-cat'); var dot = h('span', 'k-dot'); dot.style.background = 'var(--sw-c' + (i + 2) + ')'; s.append(dot, document.createTextNode(c)); legendEl.appendChild(s); });
      head.appendChild(legendEl);
    }
    var bodyEl = h('div', 'k-map-body');
    var listBox = h('div', 'k-list');
    listBox.setAttribute('aria-label', T('listLabel'));
    var ol = h('ol', 'k-items');
    listBox.appendChild(ol);
    var mapBox = h('div', 'k-map-box');
    var mapEl = h('div', 'k-map-canvas');
    mapEl.setAttribute('role', 'region'); mapEl.setAttribute('aria-label', T('mapLabel') + ': ' + spec.title);
    var tileNote = h('div', 'k-tile-note', T('tilesFail'));
    tileNote.hidden = true;
    tileNote.setAttribute('role', 'status');
    var attrib = h('div', 'k-attrib');
    mapBox.append(mapEl, tileNote, attrib);
    bodyEl.append(listBox, mapBox);
    var status = h('div', 'k-status');
    status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    var foot = h('div', 'k-foot');
    var notes = h('div', 'k-notes');
    if(route) notes.appendChild(h('p', 'k-source', T('routeNote')));
    if(items.some(function(x){ return x.approx; })) notes.appendChild(h('p', 'k-source', T('approx')));
    if(spec.source) notes.appendChild(h('p', 'k-source', spec.source));
    var actions = h('div', 'k-actions');
    var gUrl = K.googleMapsUrl(onMap.map(function(x){ return {lat:x.ll[0], lng:x.ll[1]}; }));
    if(gUrl){
      var bG = h('button', 'k-action k-action--primary', T('google'));
      bG.type = 'button';
      bG.addEventListener('click', function(){ api.open(gUrl); });
      actions.appendChild(bG);
    }
    var bCopy = h('button', 'k-action k-action--quiet', T('copyAddr'));
    bCopy.type = 'button';
    bCopy.addEventListener('click', function(){
      api.copy(spec.places.map(function(p){ var r = byK[p.k] || {}; var a = addrAfterName(p.name, p.address || r.label || ''); return p.n + '. ' + p.name + (a ? ', ' + a : ''); }).join('\n'));
    });
    actions.appendChild(bCopy);
    foot.append(notes, actions);
    if(head.childNodes.length) wrap.appendChild(head);
    wrap.append(bodyEl, status, foot);
    box.appendChild(wrap);

    // List
    var lis = [];
    onMap.forEach(function(x, i){
      var li = h('li', 'k-item'), b = h('button', 'k-item-btn');
      b.type = 'button';
      var num = h('span', 'k-num', String(x.p.n));
      if(x.p.category){ var ci = cats.indexOf(x.p.category); if(ci >= 0) num.style.setProperty('--k-pin', 'var(--sw-c' + (ci + 2) + ')'); }
      var text = h('span', 'k-item-text');
      text.appendChild(h('span', 'k-item-name', x.p.name));
      var meta = [x.p.time, addrAfterName(x.p.name, x.p.address || x.r.label || '')].filter(Boolean).join(' · ');
      if(meta) text.appendChild(h('span', 'k-item-meta', meta));
      if(x.p.note) text.appendChild(h('span', 'k-item-note', x.p.note));
      if(x.approx) text.appendChild(h('span', 'k-item-approx', T('approxPin')));
      b.append(num, text);
      if(x.photo){
        var img = h('img', 'k-thumb');
        img.alt = ''; img.loading = 'lazy'; img.decoding = 'async'; img.referrerPolicy = 'no-referrer'; img.width = 64; img.height = 64;
        img.addEventListener('error', function(){ img.remove(); });
        img.src = x.photo.url;
        b.appendChild(img);
      }
      b.addEventListener('click', function(){ setActive(i, false); });
      b.addEventListener('mouseenter', function(){ hover(i, true); });
      b.addEventListener('mouseleave', function(){ hover(i, false); });
      li.appendChild(b);
      ol.appendChild(li);
      lis.push(li);
    });
    if(missing.length){
      var group = h('div', 'k-missing');
      group.appendChild(h('h4', '', missing.every(function(x){ return x.later; }) ? T('pendingHead') : T('unresolved')));
      var ul = h('ul');
      missing.forEach(function(x){
        var li = h('li');
        li.appendChild(h('span', 'k-item-name', x.p.n + '. ' + x.p.name));
        var meta = [addrAfterName(x.p.name, x.p.address), x.later ? T('later') : x.r && x.r.gaveUp ? T('gaveUp') : ''].filter(Boolean).join(' · ');
        if(meta) li.appendChild(h('span', 'k-item-meta', meta));
        ul.appendChild(li);
      });
      group.appendChild(ul);
      listBox.appendChild(group);
    }

    // Attribution: plain text from the chat, the OpenStreetMap link is fixed.
    if(isOsm){
      attrib.appendChild(document.createTextNode('© '));
      var osm = h('a', '', 'OpenStreetMap');
      osm.href = 'https://www.openstreetmap.org/copyright';
      attrib.appendChild(osm);
    } else attrib.textContent = String(tiles.attribution || '').slice(0, 160);
    (Array.isArray(data.attribution) ? data.attribution : []).forEach(function(a){
      a = String(a || '').slice(0, 60);
      if(a && !/openstreetmap/i.test(a) && !(localStyle === 'nl' && /kadaster|pdok/i.test(a))) attrib.appendChild(document.createTextNode(' · ' + a));
    });

    var map = null, markers = [], pins = [], line = null, active = -1, started = false, loads = 0, errs = 0;
    function hover(i, on){ if(pins[i]) pins[i].classList.toggle('is-hover', on); }
    function showTileNote(){ if(!tileNote.hidden) return; tileNote.hidden = false; wrap.classList.add('tiles-failed'); start(); }
    function start(){
      if(started) return;
      started = true;
      var n = Math.max(1, onMap.length);
      var stagger = Math.min(140, Math.floor((2500 - 550) / Math.max(1, n - 1)));
      wrap.style.setProperty('--k-stagger', stagger + 'ms');
      wrap.style.setProperty('--sw-route-dur', ((n - 1) * stagger + 550) + 'ms');
      void wrap.offsetWidth;
      wrap.classList.add('is-played');
      // Whatever happens to the animation, the pins and route end up shown.
      setTimeout(function(){ wrap.classList.add('is-settled'); }, (n - 1) * stagger + 900);
    }
    function popupNode(x){
      var d = h('div', 'k-pop');
      if(x.photo){
        var img = h('img', 'k-pop-img');
        img.alt = x.p.name; img.loading = 'lazy'; img.decoding = 'async'; img.referrerPolicy = 'no-referrer';
        img.addEventListener('error', function(){ img.remove(); });
        img.src = x.photo.url;
        d.appendChild(img);
      }
      d.appendChild(h('strong', 'k-pop-name', x.p.name));
      var meta = [x.p.time, addrAfterName(x.p.name, x.p.address || x.r.label || '')].filter(Boolean).join(' · ');
      if(meta) d.appendChild(h('span', 'k-pop-meta', meta));
      if(x.p.note) d.appendChild(h('span', 'k-pop-note', x.p.note));
      var linkRow = h('span', 'k-pop-links');
      if(x.photo){
        var credit = h('button', 'k-pop-credit', T('photo', x.photo.artist, x.photo.license));
        credit.type = 'button';
        if(x.photo.credit) credit.addEventListener('click', function(){ api.open(x.photo.credit); });
        else credit.disabled = true;
        linkRow.appendChild(credit);
      }
      if(x.p.url){
        var more = h('a', 'k-pop-more', T('more'));
        more.href = x.p.url; more.rel = 'noopener noreferrer';
        linkRow.appendChild(more);
      }
      if(linkRow.childNodes.length) d.appendChild(linkRow);
      return d;
    }
    // restore: a remembered choice is marked again without moving the map.
    function setActive(i, fromMap, restore){
      if(i < 0 || i >= onMap.length) return;
      active = i;
      var x = onMap[i];
      lis.forEach(function(li, j){ if(j === i) li.setAttribute('aria-current', 'true'); else li.removeAttribute('aria-current'); });
      pins.forEach(function(p, j){ p.classList.toggle('is-active', j === i); });
      status.textContent = T('status', x.p.n, spec.places.length, x.p.name);
      if(map && markers[i] && !restore){
        try{
          map.panTo(x.ll, {animate:!REDUCED, duration:0.6});
          markers[i].unbindPopup();
          markers[i].bindPopup(popupNode(x), {maxWidth:240, minWidth:180, autoPanPadding:[24, 24], className:'k-popup'}).openPopup();
        }catch(err){ reportError(err && err.message, err && err.stack); }
      }
      // Keep the active row in view inside the list itself, never the chat.
      var li = lis[i];
      if(li && listBox.scrollHeight > listBox.clientHeight + 1){
        var top = li.getBoundingClientRect().top - listBox.getBoundingClientRect().top + listBox.scrollTop, bottom = top + li.offsetHeight;
        if(top < listBox.scrollTop) listBox.scrollTop = Math.max(0, top - 8);
        else if(bottom > listBox.scrollTop + listBox.clientHeight) listBox.scrollTop = bottom - listBox.clientHeight + 8;
      }
      if(fromMap) try{ lis[i].querySelector('button').focus({preventScroll:true}); }catch(_){}
      // On a phone the map sits above the list: a tap in the list brings the map into view.
      if(!fromMap && !restore && !standalone && (window.innerWidth || 0) < 640 && mapBox){
        var mt = mapBox.getBoundingClientRect().top;
        // A frame taller than the chat allows has scrolled inside itself: bring the map back there first.
        if(mt < 0){ window.scrollBy(0, mt - 8); mt = mapBox.getBoundingClientRect().top; }
        post({type:'reveal', top:Math.round(mt - 8)});
      }
      if(!restore) saveState({a:i});
    }

    if(typeof L === 'undefined' || !onMap.length){
      if(!onMap.length) mapBox.classList.add('is-empty');
      if(typeof L === 'undefined') showTileNote();
    } else {
      try{
        // On a touch screen one finger scrolls the chat; pinch still zooms the map.
        var coarse = !!(window.matchMedia && window.matchMedia('(pointer:coarse)').matches);
        map = L.map(mapEl, {scrollWheelZoom:false, zoomControl:true, attributionControl:false, keyboard:true, tap:false, dragging:!coarse});
        var layer = L.tileLayer(tiles.url, {maxZoom:Math.max(1, Math.min(19, Number(tiles.maxZoom) || 19)), referrerPolicy:'origin', detectRetina:false});
        layer.on('tileload', function(){ loads++; if(loads === 1){ start(); } });
        layer.on('tileerror', function(){ errs++; if((loads === 0 && errs >= 4) || (errs + loads >= 10 && errs / (errs + loads) > 0.6)) showTileNote(); });
        layer.addTo(map);
        onMap.forEach(function(x, i){
          var pin = h('span', 'sw-pin' + (x.approx ? ' is-approx' : ''), String(x.p.n));
          pin.style.setProperty('--i', String(i));
          if(x.p.category){ var ci = cats.indexOf(x.p.category); if(ci >= 0) pin.style.setProperty('--k-pin', 'var(--sw-c' + (ci + 2) + ')'); }
          pins.push(pin);
          var icon = L.divIcon({className:'sw-pin-wrap', html:pin, iconSize:[28, 34], iconAnchor:[14, 34], popupAnchor:[0, -30]});
          var mk = L.marker(x.ll, {icon:icon, keyboard:true, title:x.p.name, alt:x.p.name, riseOnHover:true}).addTo(map);
          mk.on('click', function(){ setActive(i, true); });
          mk.on('mouseover', function(){ if(lis[i]) lis[i].classList.add('is-hover'); });
          mk.on('mouseout', function(){ if(lis[i]) lis[i].classList.remove('is-hover'); });
          markers.push(mk);
        });
        if(route){
          line = L.polyline(onMap.map(function(x){ return x.ll; }), {className:'sw-route', weight:3, opacity:0.9, lineJoin:'round', lineCap:'round', interactive:false}).addTo(map);
          var path = line.getElement && line.getElement();
          if(path) path.setAttribute('pathLength', '1');
        }
        // Pins stand above their point: leave room for them at the top.
        var fit = function(){
          if(onMap.length === 1) map.setView(onMap[0].ll, 15, {animate:false});
          else map.fitBounds(L.latLngBounds(onMap.map(function(x){ return x.ll; })), {paddingTopLeft:[48, 64], paddingBottomRight:[48, 36], maxZoom:15, animate:false});
        };
        fit();
        var userMoved = false, refit = 0;
        map.on('dragstart zoomstart', function(e){ if(!fitting) userMoved = true; });
        var fitting = false;
        if(typeof ResizeObserver === 'function') new ResizeObserver(function(){
          clearTimeout(refit);
          refit = setTimeout(function(){
            try{
              map.invalidateSize({pan:false});
              // Until the user moves the map, keep every pin in view (full screen, phone width).
              if(!userMoved){ fitting = true; fit(); fitting = false; }
            }catch(_){}
          }, 80);
        }).observe(mapEl);
        setTimeout(start, 1500);
        setTimeout(function(){ if(loads === 0) showTileNote(); }, 8000);
      }catch(err){
        reportError(err && err.message, err && err.stack);
        showTileNote();
      }
    }
    if(REDUCED) start();
    if(typeof view.a === 'number' && view.a >= 0 && view.a < onMap.length){
      var keep = view.a;
      setTimeout(function(){ setActive(keep, false, true); }, 50);
    }
    return {
      // Full screen is for exploring: one finger moves the map there; inline it scrolls the chat.
      onFull:function(on){ if(map && typeof coarse !== 'undefined' && coarse){ try{ if(on) map.dragging.enable(); else map.dragging.disable(); }catch(_){} } setTimeout(function(){ if(map) try{ map.invalidateSize(); }catch(_){} scheduleHeight(true); }, 60); }
    };
  }

  // ── KPI tiles ───────────────────────────────────────────────────────────
  function renderKpi(box, spec){
    var grid = h('div', 'k-kpi');
    grid.setAttribute('role', 'list');
    spec.items.forEach(function(it){
      var tile = h('div', 'k-tile');
      tile.setAttribute('role', 'listitem');
      tile.appendChild(h('span', 'k-tile-label', it.label));
      var value = h('span', 'k-tile-value', K.kpiValueText(it, LANG));
      var full = fmt(it.value, it.format, it.decimals);
      if(full !== value.textContent) value.title = full;
      tile.appendChild(value);
      var meta = h('div', 'k-tile-meta');
      if(it.delta !== null){
        var tone = it.tone || 'flat';
        var pill = h('span', 'k-delta is-' + tone);
        var arrow = h('span', 'k-delta-arrow', it.delta > 0 ? '▲' : it.delta < 0 ? '▼' : '●');
        arrow.setAttribute('aria-hidden', 'true');
        pill.append(arrow, document.createTextNode(K.kpiDeltaText(it, LANG)), h('span', 'k-sr', ', ' + T(tone === 'good' ? 'good' : tone === 'bad' ? 'bad' : 'flat')));
        meta.appendChild(pill);
      }
      if(it.note && !noteRepeatsTarget(it.note, it.target, it.value)) meta.appendChild(h('span', 'k-kpi-note', LANG === 'nl' ? String(it.note).replace(/(\d[\d.,]*)\s*(euro|eur)\b/gi, '€ $1').replace(/€\s*(?=[-\d])/g, '€\u00a0') : it.note));
      if(meta.childNodes.length) tile.appendChild(meta);
      if(it.target !== null){
        var target = h('div', 'k-target' + (it.over ? ' is-over' : it.met ? ' is-met' : ''));
        var bar = h('div', 'k-target-bar'), fill = h('span', 'k-target-fill');
        fill.style.width = Math.round(it.progress * 1000) / 10 + '%';
        bar.appendChild(fill);
        bar.setAttribute('role', 'progressbar');
        bar.setAttribute('aria-valuemin', '0'); bar.setAttribute('aria-valuemax', '100');
        bar.setAttribute('aria-valuenow', String(Math.round(it.progress * 100)));
        var pct = fmt(Math.round(it.value / it.target * 100), 'percent', 0);
        // When the value is written short (millions), the target and the overrun are too.
        var short = Math.abs(it.value) >= 1e6 && it.decimals == null && it.format !== 'percent';
        var tf = function(v){ return short ? K.kpiValueText({value:v, format:it.format, decimals:null}, LANG) : fmt(v, it.format, it.decimals); };
        // "Budget" only for money; a churn or complaints ceiling is a maximum. A percentage
        // over its maximum is said in points, never as a percentage of a percentage.
        var money = it.format === 'currency', pctFmt = it.format === 'percent';
        function targetLine(){
          if(it.over){
            var over = pctFmt ? K.kpiDeltaText({delta:Math.round((it.value - it.target) * 100) / 100, deltaFormat:'number', format:'percent'}, LANG).replace(/^\+/, '') : tf(it.value - it.target);
            return T(money ? 'over' : 'overMax', over, tf(it.target));
          }
          if(it.good !== 'down') return T('target', pct, tf(it.target));
          if(pctFmt) return (LANG === 'nl' ? 'Maximum ' : 'Limit ') + tf(it.target);
          return T(money ? 'limit' : 'limitMax', pct, tf(it.target));
        }
        var text = h('span', 'k-target-text', targetLine());
        bar.setAttribute('aria-label', text.textContent);
        target.append(bar, text);
        tile.appendChild(target);
      }
      grid.appendChild(tile);
    });
    box.appendChild(grid);
    if(spec.source) box.appendChild(h('p', 'k-source', spec.source));
    return {};
  }

  // ── Timeline (Gantt) ────────────────────────────────────────────────────
  function localDay(){ var d = new Date(); return Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5) + 0.5; }
  function pct(x){ return Math.round(x * 100000) / 1000 + '%'; }
  function renderTimeline(box, spec, view){
    var axis = K.timelineAxis(spec, LANG, localDay());
    var span = axis.max - axis.min;
    var used = {};
    spec.items.forEach(function(it){ if(it.status) used[it.status] = true; });
    // Every row already names its status and the today line carries its own
    // label: a legend only helps when some rows have no status word.
    var allNamed = spec.items.every(function(it){ return !!it.status || it.milestone; });
    var wrap = h('div', 'k-tl' + (Object.keys(used).length ? ' has-status' : ''));
    var legend = h('div', 'k-tl-legend');
    ['done', 'doing', 'todo', 'risk'].forEach(function(st){
      if(!used[st] || allNamed) return;
      var s = h('span', 'k-tl-key'), sw = h('span', 'k-tl-swatch is-' + st);
      s.append(sw, document.createTextNode(K.statusWord(st, LANG)));
      legend.appendChild(s);
    });
    // On a phone the today line has no label of its own: name it once.
    if(axis.todayX !== null){
      var nowKey = h('span', 'k-tl-key k-tl-now-key'), nowSw = h('span', 'k-tl-swatch is-today');
      nowKey.append(nowSw, document.createTextNode(T('today')));
      legend.appendChild(nowKey);
    }
    if(legend.childNodes.length) wrap.appendChild(legend);

    var chart = h('div', 'k-tl-chart');
    chart.setAttribute('role', 'group');
    chart.setAttribute('aria-label', T('tlLabel') + ': ' + spec.title);
    var n = spec.items.length;
    chart.style.gridTemplateRows = 'auto repeat(' + n + ', minmax(38px, auto))';
    // Every cell has its own place: the overlay spans all rows of the track column.
    var corner = h('div', 'k-tl-corner');
    corner.style.gridArea = '1 / 1';
    chart.appendChild(corner);
    var axisEl = h('div', 'k-tl-axis');
    axisEl.style.gridArea = '1 / 2';
    axisEl.setAttribute('aria-hidden', 'true');
    axis.ticks.forEach(function(t){
      var tick = h('span', 'k-tl-tick' + (t.minor ? ' is-minor' : ''), t.label);
      tick.style.left = pct(t.x);
      axisEl.appendChild(tick);
    });
    chart.appendChild(axisEl);
    var detail = h('p', 'k-tl-detail');
    detail.setAttribute('role', 'status');
    detail.setAttribute('aria-live', 'polite');
    var bars = [];
    spec.items.forEach(function(it, i){
      var period = K.timelinePeriod(spec, it, LANG);
      var word = K.statusWord(it.status, LANG);
      var cell = h('div', 'k-tl-label');
      cell.appendChild(h('span', 'k-tl-name', it.label));
      var meta = [it.owner, word].filter(Boolean).join(' · ');
      if(meta) cell.appendChild(h('span', 'k-tl-meta', meta));
      cell.appendChild(h('span', 'k-tl-when', period));
      var track = h('div', 'k-tl-track');
      cell.style.gridArea = (i + 2) + ' / 1';
      track.style.gridArea = (i + 2) + ' / 2';
      var b = h('button', (it.milestone ? 'k-tl-ms' : 'k-tl-bar') + (it.status ? ' is-' + it.status : ' is-plain'));
      b.type = 'button';
      b.dataset.k = it.k;
      b.setAttribute('aria-label', [it.label, period, it.milestone ? T('milestone') : '', word].filter(Boolean).join(', '));
      b.setAttribute('aria-pressed', 'false');
      // Very long plans: keep every bar inside its track.
      var x0 = Math.max(0, Math.min(1, (it.s - axis.min) / span));
      var x1 = Math.max(x0, Math.min(1, (it.e - axis.min) / span));
      b.style.left = pct(x0);
      if(!it.milestone) b.style.width = 'max(6px, ' + pct(x1 - x0) + ')';
      b.tabIndex = i === 0 ? 0 : -1;
      b.addEventListener('click', function(){ select(i, false); });
      b.addEventListener('keydown', function(e){
        var to = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -2;
        if(to === -2) return;
        e.preventDefault();
        to = Math.max(0, Math.min(n - 1, to));
        bars.forEach(function(x, j){ x.tabIndex = j === to ? 0 : -1; });
        bars[to].focus();
      });
      track.appendChild(b);
      if(axis.todayX !== null){ var now = h('span', 'k-tl-now'); now.style.left = pct(axis.todayX); now.setAttribute('aria-hidden', 'true'); track.appendChild(now); }
      // The label selects too: on a phone the bar is a thin strip.
      cell.addEventListener('click', function(){ select(i, false); });
      chart.append(cell, track);
      bars.push(b);
    });
    var overlay = h('div', 'k-tl-overlay');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.gridRow = '1 / ' + (n + 2);
    axis.lines.forEach(function(x){ var l = h('span', 'k-tl-line'); l.style.left = pct(x); overlay.appendChild(l); });
    if(axis.todayX !== null){
      var today = h('span', 'k-tl-today');
      today.style.left = pct(axis.todayX);
      today.appendChild(h('span', 'k-tl-today-label', T('today')));
      overlay.appendChild(today);
    }
    chart.appendChild(overlay);
    wrap.append(chart, detail);
    if(spec.source) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    function select(i, restore){
      var it = spec.items[i];
      if(!it) return;
      bars.forEach(function(b, j){ b.setAttribute('aria-pressed', String(j === i)); b.classList.toggle('is-active', j === i); b.tabIndex = j === i ? 0 : -1; });
      var parts = [it.label, K.timelinePeriod(spec, it, LANG), it.milestone ? T('milestone') : '', it.owner, K.statusWord(it.status, LANG), it.note];
      detail.textContent = parts.filter(Boolean).join(' · ');
      detail.classList.add('is-set');
      if(!restore){ saveState({a:i}); revealEl(detail, bars[i]); }
      scheduleHeight(false);
    }
    if(typeof view.a === 'number' && view.a >= 0 && view.a < n) select(view.a, true);
    return {};
  }

  // A donut already names its total in the middle: a subtitle that only says the total goes.
  function subtitleRepeatsTotal(kit, spec){
    if(kit !== 'chart' || spec.type !== 'donut' || spec.format === 'percent' || !spec.series || !spec.series[0]) return false;
    var sum = spec.series[0].data.reduce(function(a, v){ return a + (v || 0); }, 0);
    var digits = String(spec.subtitle).replace(/[^\d]/g, '');
    return /^(totaal|total)\b/i.test(String(spec.subtitle).trim()) || (digits.length >= 3 && digits === String(Math.round(sum)));
  }
  // ── Render ──────────────────────────────────────────────────────────────
  function render(msg){
    var kit = msg.kit, spec = msg.spec;
    if(!spec || typeof spec !== 'object' || (['table', 'chart', 'map', 'kpi', 'timeline'].indexOf(kit) < 0 && !RENDERERS[kit])) return;
    LANG = msg.lang === 'en' ? 'en' : 'nl';
    document.documentElement.lang = LANG;
    lastMsg = msg;
    api.spec = deepFreeze(spec);
    api.data = msg.data && typeof msg.data === 'object' ? deepFreeze(msg.data) : null;
    var restore = msg.restore && typeof msg.restore === 'object' ? msg.restore : {};
    root.textContent = '';
    root.className = 'kit kit-' + kit;
    current = null;
    try{
      if(spec.subtitle && !subtitleRepeatsTotal(kit, spec)) root.appendChild(h('p', 'k-sub', spec.subtitle));
      var box = h('div', 'k-body');
      root.appendChild(box);
      if(kit === 'table'){
        var view = K.initialView(spec);
        if(Array.isArray(restore.s) || restore.s === null) view.s = restore.s;
        if(typeof restore.q === 'string') view.q = restore.q.slice(0, 120);
        if(restore.all === true) view.all = true;
        current = renderTable(box, spec, view, {onChange:function(v){ saveState({s:v.s, q:v.q, all:!!v.all}); }});
      } else if(kit === 'chart'){
        current = renderChart(box, spec, {v:restore.v === 'table' ? 'table' : 'chart'});
      } else if(kit === 'kpi'){
        current = renderKpi(box, spec);
      } else if(kit === 'timeline'){
        current = renderTimeline(box, spec, {a:typeof restore.a === 'number' ? restore.a : -1});
      } else if(RENDERERS[kit]){
        current = RENDERERS[kit](box, spec, restore, window.SWKitRender) || {};
      } else {
        current = renderMap(box, spec, {a:typeof restore.a === 'number' ? restore.a : -1}, api.data);
      }
    }catch(err){
      reportError(err && err.message, err && err.stack);
    }
    // Something was left out to keep the block readable: say so, quietly.
    try{
      var dr = spec.dropped;
      if(dr && dr.total > dr.shown){
        var what = kit === 'chart' ? (LANG === 'nl' ? 'punten' : 'points') : kit === 'map' ? (LANG === 'nl' ? 'plaatsen' : 'places') : (LANG === 'nl' ? 'onderdelen' : 'items');
        var first = dr.last ? (LANG === 'nl' ? 'de laatste ' : 'the last ') : (LANG === 'nl' ? 'de eerste ' : 'the first ');
        root.appendChild(h('p', 'k-note k-dropped', (LANG === 'nl' ? 'Alleen ' : 'Only ') + first + dr.shown + (LANG === 'nl' ? ' van ' : ' of ') + dr.total + ' ' + what + (LANG === 'nl' ? ' getoond.' : ' shown.')));
      }
    }catch(_){}
    try{
      if(spec.leftOut > 0){
        var n1 = spec.leftOut;
        root.appendChild(h('p', 'k-note k-dropped', LANG === 'nl' ? (n1 === 1 ? 'Eén onderdeel kon niet worden getoond.' : n1 + ' onderdelen konden niet worden getoond.') : (n1 === 1 ? 'One item could not be shown.' : n1 + ' items could not be shown.')));
      }
    }catch(_){}
    try{
      var ds = spec.droppedSeries;
      if(ds && ds.total > ds.shown) root.appendChild(h('p', 'k-note k-dropped', (LANG === 'nl' ? 'Alleen de eerste ' + ds.shown + ' van ' + ds.total + ' reeksen getoond.' : 'Only the first ' + ds.shown + ' of ' + ds.total + ' series shown.')));
    }catch(_){}
    post({type:'rendered'});
    scheduleHeight(true);
    setTimeout(function(){ scheduleHeight(true); }, 400);
  }

  if(standalone){
    if(DOC.theme) applyTheme(null, DOC.theme);
    // Kind files come after this script: draw once the page is parsed.
    if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ render(DOC); });
    else render(DOC);
    return;
  }
  window.addEventListener('message', function(e){
    if(e.source !== host || (HOST_OK && e.origin !== HOST_ORIGIN)) return;
    var msg = e.data;
    if(!msg || msg.iui !== 1 || typeof msg.type !== 'string') return;
    if(msg.type === 'theme') applyTheme(msg.vars, msg.mode);
    else if(msg.type === 'kit'){ if(msg.final) render(msg); }
    else if(msg.type === 'scroll'){ var by = Number(msg.by) || 0; if(by > 0 && by < 4000) window.scrollBy(0, by); }
    else if(msg.type === 'measure'){
      if(typeof msg.full === 'boolean') setFull(msg.full);
      // The room the chat gives this card; a phone table shows as many rows as fit.
      if(typeof msg.cap === 'number' && msg.cap > 0 && Math.abs(msg.cap - CAP) > 4){ CAP = msg.cap; if(current && current.redraw && lastMsg && lastMsg.kit === 'table') try{ current.redraw(); }catch(_){} }
      scheduleHeight(true);
    }
  });
  post({type:'ready', kit:1});
})();
