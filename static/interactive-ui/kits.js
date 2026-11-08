// Data blocks: the kit frame (shell plus the table, chart and map renderers).
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
  var LANG = 'nl', FULL = false, current = null, lastMsg = null, lastHeight = 0, heightRaf = 0, errorCount = 0;
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
      unresolved:'Niet op de kaart gevonden', later:'Wordt nog opgezocht', tilesFail:'De kaart laadt nu niet. De lijst klopt wel.',
      google:'Open in Google Maps', copyAddr:'Kopieer adressen', photo:function(a,l){ return 'Foto: ' + a + ', ' + l; },
      more:'Meer info', approxPin:'bij benadering', mapLabel:'Kaart', listLabel:'Locaties'},
    en:{search:'Search table', showAll:function(n){ return 'Show all ' + n + ' rows'; }, total:'Total',
      count:function(a,b){ return a + ' of ' + b + ' rows'; }, empty:'No rows', noMatch:'No rows found',
      sortHint:'Sort', view:'View', chart:'Chart', table:'Table',
      chartFail:'The chart could not load, here are the numbers.', places:function(n){ return n === 1 ? '1 place' : n + ' places'; },
      route:'Route', replay:'Play again', status:function(i,n,name){ return 'Place ' + i + ' of ' + n + ': ' + name; },
      routeNote:'The line shows the order, not the road.', approx:'Some places are approximate.',
      unresolved:'Not found on the map', later:'Still being looked up', tilesFail:'The map does not load right now. The list is correct.',
      google:'Open in Google Maps', copyAddr:'Copy addresses', photo:function(a,l){ return 'Photo: ' + a + ', ' + l; },
      more:'More info', approxPin:'approximate', mapLabel:'Map', listLabel:'Places'}
  };
  function T(key){ var v = (TEXT[LANG] || TEXT.nl)[key]; var args = Array.prototype.slice.call(arguments, 1); return typeof v === 'function' ? v.apply(null, args) : v; }
  function h(tag, cls, text){ var e = document.createElement(tag); if(cls) e.className = cls; if(text != null) e.textContent = String(text); return e; }
  function fmt(v, type, decimals){ return K.formatValue(v, type, decimals, LANG); }

  // ── Bridge ──────────────────────────────────────────────────────────────
  function deepFreeze(o){
    if(o && typeof o === 'object' && !Object.isFrozen(o)){ Object.freeze(o); Object.keys(o).forEach(function(k){ deepFreeze(o[k]); }); }
    return o;
  }
  var listeners = [];
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
    wrap.appendChild(scroll);
    var more = h('button', 'k-more');
    more.type = 'button';
    more.addEventListener('click', function(){ view.all = true; changed(); });
    wrap.appendChild(more);
    if(spec.source && !opt.noSource) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    function changed(){ draw(); if(opt.onChange) opt.onChange(view); }
    function draw(){
      var idx = K.viewIndices(spec, view, LANG);
      var limit = (view.all || FULL || opt.all) ? idx.length : Math.min(idx.length, 50);
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
      more.hidden = limit >= idx.length;
      more.textContent = T('showAll', idx.length);
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
      var datasets = spec.series.map(function(s, i){
        var color = hl ? (hlSeries ? (s.name === hl ? c.accent : c.muted) : c.pal[i % 8]) : c.pal[i % 8];
        var ds = {label:s.name, data:s.data.slice()};
        if(round){
          ds.backgroundColor = spec.labels.map(function(l, j){ return hl ? (l === hl ? c.accent : alpha(c.pal[j % 8], 0.35)) : c.pal[j % 8]; });
          ds.borderColor = t.surface || t.bg || '#171a23'; ds.borderWidth = 2; ds.hoverOffset = 6;
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
      var horizontal = spec.type === 'hbar';
      var valueAxis = {stacked:stacked, beginAtZero:true, grid:{color:alpha(t.border || '#2a2f3d', 0.9), drawTicks:false}, border:{display:false},
        ticks:{color:t.muted, padding:6, callback:function(v){ return f(v); }}};
      var catAxis = {stacked:stacked, grid:{display:false}, border:{color:t.border}, ticks:{color:t.muted, autoSkip:true, maxRotation:0}};
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
          var label = target.label && /\d/.test(target.label) ? target.label : (target.label ? target.label + ': ' : '') + f(target.value);
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
          plugins:{legend:{display:!round && spec.series.length > 1, position:'bottom', labels:{color:t.fg, boxWidth:10, boxHeight:10, usePointStyle:true, padding:14}},
            tooltip:{backgroundColor:t.surface2 || t.surface, titleColor:t.strong || t.fg, bodyColor:t.fg, borderColor:t.border, borderWidth:1, padding:10,
              callbacks:{label:function(ctx){
                var v = ctx.parsed && (round ? ctx.parsed : (horizontal ? ctx.parsed.x : ctx.parsed.y));
                var name = round ? ctx.label : ctx.dataset.label;
                return ' ' + name + ': ' + f(typeof v === 'number' ? v : ctx.raw);
              }}}}}};
      if(round){ if(kind === 'doughnut') cfg.options.cutout = '62%'; }
      else cfg.options.scales = horizontal ? {x:valueAxis, y:catAxis} : {x:catAxis, y:valueAxis};
      return cfg;
    }
    function drawLegend(){
      if(!legend) return;
      legend.textContent = '';
      var c = colors(), s = spec.series[0], sum = s.data.reduce(function(a, v){ return a + (v || 0); }, 0);
      spec.labels.forEach(function(l, j){
        var li = h('li'), sw = h('span', 'k-swatch');
        sw.style.background = spec.highlight ? (l === spec.highlight ? c.accent : alpha(c.pal[j % 8], 0.35)) : c.pal[j % 8];
        var v = s.data[j];
        li.append(sw, h('span', 'k-legend-label', l), h('span', 'k-legend-value', v == null ? '' : f(v) + (sum > 0 ? ' (' + fmt(Math.round(v / sum * 1000) / 10, 'percent', 1) + ')' : '')));
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
    var isOsm = /^https:\/\/tile\.openstreetmap\.org\//.test(tiles.url);
    var items = spec.places.map(function(p){
      var r = byK[p.k] || {}, lat = Number(r.lat), lng = Number(r.lng);
      var ok = r.status === 'ok' && inRange(lat, lng);
      return {p:p, r:r, ll:ok ? [lat, lng] : null, approx:ok && (r.precision === 'street' || r.precision === 'place' || r.precision === 'city'),
        photo:photoOf(r), later:r.status === 'later'};
    });
    var onMap = items.filter(function(x){ return x.ll; }), missing = items.filter(function(x){ return !x.ll; });
    var route = spec.kind === 'route' && onMap.length >= 2;
    var cats = spec.categories || [];

    var wrap = h('div', 'k-map' + (route ? ' is-route' : ''));
    var head = h('div', 'k-tools');
    var chips = h('div', 'k-chips');
    chips.appendChild(h('span', 'k-chip', T('places', spec.places.length)));
    head.appendChild(chips);
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
      api.copy(spec.places.map(function(p){ var r = byK[p.k] || {}; var a = p.address || r.label || ''; return p.n + '. ' + p.name + (a ? ', ' + a : ''); }).join('\n'));
    });
    actions.appendChild(bCopy);
    foot.append(notes, actions);
    wrap.append(head, bodyEl, status, foot);
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
      var meta = [x.p.time, x.p.address || x.r.label || ''].filter(Boolean).join(' · ');
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
      group.appendChild(h('h4', '', T('unresolved')));
      var ul = h('ul');
      missing.forEach(function(x){
        var li = h('li');
        li.appendChild(h('span', 'k-item-name', x.p.n + '. ' + x.p.name));
        var meta = [x.p.address, x.later ? T('later') : ''].filter(Boolean).join(' · ');
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
      if(a && !/openstreetmap/i.test(a)) attrib.appendChild(document.createTextNode(' · ' + a));
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
      var meta = [x.p.time, x.p.address || x.r.label || ''].filter(Boolean).join(' · ');
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
      if(!restore) saveState({a:i});
    }

    if(typeof L === 'undefined' || !onMap.length){
      if(!onMap.length) mapBox.classList.add('is-empty');
      if(typeof L === 'undefined') showTileNote();
    } else {
      try{
        map = L.map(mapEl, {scrollWheelZoom:false, zoomControl:true, attributionControl:false, keyboard:true, tap:false});
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
          else map.fitBounds(L.latLngBounds(onMap.map(function(x){ return x.ll; })), {paddingTopLeft:[28, 46], paddingBottomRight:[28, 18], maxZoom:15, animate:false});
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
      onFull:function(){ setTimeout(function(){ if(map) try{ map.invalidateSize(); }catch(_){} scheduleHeight(true); }, 60); }
    };
  }

  // ── Render ──────────────────────────────────────────────────────────────
  function render(msg){
    var kit = msg.kit, spec = msg.spec;
    if(!spec || typeof spec !== 'object' || (kit !== 'table' && kit !== 'chart' && kit !== 'map')) return;
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
      if(spec.subtitle) root.appendChild(h('p', 'k-sub', spec.subtitle));
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
      } else {
        current = renderMap(box, spec, {a:typeof restore.a === 'number' ? restore.a : -1}, api.data);
      }
    }catch(err){
      reportError(err && err.message, err && err.stack);
    }
    post({type:'rendered'});
    scheduleHeight(true);
    setTimeout(function(){ scheduleHeight(true); }, 400);
  }

  if(standalone){
    if(DOC.theme) applyTheme(null, DOC.theme);
    render(DOC);
    return;
  }
  window.addEventListener('message', function(e){
    if(e.source !== host || (HOST_OK && e.origin !== HOST_ORIGIN)) return;
    var msg = e.data;
    if(!msg || msg.iui !== 1 || typeof msg.type !== 'string') return;
    if(msg.type === 'theme') applyTheme(msg.vars, msg.mode);
    else if(msg.type === 'kit'){ if(msg.final) render(msg); }
    else if(msg.type === 'measure'){ if(typeof msg.full === 'boolean') setFull(msg.full); scheduleHeight(true); }
  });
  post({type:'ready', kit:1});
})();
