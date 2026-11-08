// Data block "funnel" (```funnel, ```trechter): a conversion funnel such as a
// sales pipeline, website visitors to customers or a recruitment process.
//
// {"title", "stages":[{"label", "value", "note"?}], "format"?:"number|currency",
//  "compare"?:[values of a previous period]}  ("steps" also works)
//
// The checks run in the chat (SWKit only); the renderer only registers inside
// the kit frame, where SWKitRender exists. Every text goes in with textContent.

(function(root){
  'use strict';
  var K = root.SWKit;
  if(!K) return;

  var LIM = {stages:8, label:40, note:80, minStages:2};
  var FORMATS = {number:'number', count:'number', aantal:'number', stuks:'number', integer:'number', currency:'currency', euro:'currency', eur:'currency', bedrag:'currency'};

  var MSG = {
    nl:{
      noStages:function(){ return 'Er zijn geen fasen (stages).'; },
      cut:function(field, max){ return field + ' is ingekort tot ' + max + ' tekens.'; },
      tooFew:function(n){ return 'Een trechter heeft minstens twee fasen met een naam en een getal; er ' + (n === 1 ? 'is er 1' : 'zijn er ' + n) + '. Stuur het volledige trechter-blok opnieuw.'; },
      allZero:function(){ return 'Alle fasen hebben de waarde 0; er is geen trechter te tonen.'; },
      many:function(n, max){ return 'Er zijn ' + n + ' fasen; alleen de eerste ' + max + ' worden getoond.'; },
      asMap:function(){ return 'De fasen stonden als lijst van namen met getallen; ze zijn in die volgorde getoond.'; },
      item:function(i){ return 'Fase ' + i + ' is geen object met label en value en is weggelaten.'; },
      label:function(i){ return 'Fase ' + i + ' heeft geen naam (label) en is weggelaten.'; },
      value:function(l){ return '"' + l + '" heeft geen getal als waarde (value) en is weggelaten.'; },
      negative:function(l){ return '"' + l + '" had een negatieve waarde; die is op 0 gezet.'; },
      grows:function(l, prev){ return '"' + l + '" is groter dan de fase ervoor ("' + prev + '"); controleer de volgorde.'; },
      format:function(f){ return 'Onbekend format "' + f + '"; gebruik number of currency. Nu geldt number.'; },
      compareLength:function(got, want){ return 'De vergelijking (compare) heeft ' + got + ' waarden, verwacht ' + want + '.'; },
      compareValue:function(i){ return 'Vergelijkingswaarde ' + i + ' is geen getal en is weggelaten.'; },
      compareType:function(){ return 'De vergelijking (compare) is geen lijst met getallen en is weggelaten.'; },
      labelField:function(i){ return 'De naam van fase ' + i; },
      noteField:function(l){ return 'De notitie van "' + l + '"'; }
    },
    en:{
      noStages:function(){ return 'There are no stages.'; },
      cut:function(field, max){ return field + ' was shortened to ' + max + ' characters.'; },
      tooFew:function(n){ return 'A funnel needs at least two stages with a name and a number; there ' + (n === 1 ? 'is 1' : 'are ' + n) + '. Send the complete funnel block again.'; },
      allZero:function(){ return 'Every stage has the value 0; there is no funnel to show.'; },
      many:function(n, max){ return 'There are ' + n + ' stages; only the first ' + max + ' are shown.'; },
      asMap:function(){ return 'The stages came as names with numbers; they are shown in that order.'; },
      item:function(i){ return 'Stage ' + i + ' is not an object with label and value and was left out.'; },
      label:function(i){ return 'Stage ' + i + ' has no name (label) and was left out.'; },
      value:function(l){ return '"' + l + '" has no number as its value and was left out.'; },
      negative:function(l){ return '"' + l + '" had a negative value; it was set to 0.'; },
      grows:function(l, prev){ return '"' + l + '" is larger than the stage before it ("' + prev + '"); check the order.'; },
      format:function(f){ return 'Unknown format "' + f + '"; use number or currency. Now number is used.'; },
      compareLength:function(got, want){ return 'The comparison (compare) has ' + got + ' values, expected ' + want + '.'; },
      compareValue:function(i){ return 'Comparison value ' + i + ' is not a number and was left out.'; },
      compareType:function(){ return 'The comparison (compare) is not a list of numbers and was left out.'; },
      labelField:function(i){ return 'The name of stage ' + i; },
      noteField:function(l){ return 'The note of "' + l + '"'; }
    }
  };
  function messenger(lang){
    var t = MSG[lang === 'en' ? 'en' : 'nl'];
    return function(key){ var f = t[key]; return f ? f.apply(null, Array.prototype.slice.call(arguments, 1)) : String(key); };
  }
  // A share as a number from 0 to 100, one decimal: the export and the chips read the same value.
  function share(a, b){ return b > 0 ? Math.round(a / b * 1000) / 10 : null; }

  function validate(raw, lang, H){
    var m = messenger(lang), warnings = [], errors = [];
    var warn = function(){ warnings.push(m.apply(null, arguments)); };
    var out = H.base(raw, 'funnel', warnings);
    var list = raw.stages != null ? raw.stages : raw.steps != null ? raw.steps : raw.items;
    // {"Leads": 1200, "Offerte": 300} keeps its order: turn it into stages.
    if(H.isObj(list)){
      list = Object.keys(list).map(function(k){ return {label:k, value:list[k]}; });
      if(list.length) warn('asMap');
    }
    if(!Array.isArray(list) || !list.length){ errors.push(m('noStages')); return {errors:errors, warnings:warnings}; }
    var compareIn = raw.compare != null ? raw.compare : raw.previous;
    if(compareIn != null && !Array.isArray(compareIn)){ warn('compareType'); compareIn = null; }
    if(compareIn && compareIn.length !== list.length) warn('compareLength', compareIn.length, list.length);
    if(list.length > LIM.stages){ warn('many', list.length, LIM.stages); list = list.slice(0, LIM.stages); }

    var fmtRaw = typeof raw.format === 'string' ? raw.format.trim().toLowerCase() : '';
    var format = '';
    if(fmtRaw){ format = FORMATS[fmtRaw] || ''; if(!format) warn('format', H.str(raw.format, 20)); }
    var sawCurrency = false;
    var stages = [], anyCompare = false;
    list.forEach(function(it, i){
      if(Array.isArray(it) && it.length >= 2) it = {label:it[0], value:it[1], note:it[2]};
      if(!H.isObj(it)){ warn('item', i + 1); return; }
      var label = H.str(it.label != null ? it.label : (it.name != null ? it.name : (it.stage != null ? it.stage : it.title)), LIM.label, warn, m('labelField', i + 1));
      if(!label){ warn('label', i + 1); return; }
      var vRaw = it.value != null ? it.value : (it.count != null ? it.count : (it.amount != null ? it.amount : it.n));
      var v = H.kpiNumber(vRaw);
      if(!v){ warn('value', label); return; }
      if(v.kind === 'currency') sawCurrency = true;
      var value = v.n;
      if(value < 0){ warn('negative', label); value = 0; }
      var prev = null;
      var cRaw = it.compare != null ? it.compare : (it.previous != null ? it.previous : (compareIn ? compareIn[i] : null));
      if(cRaw != null && cRaw !== ''){
        var c = H.kpiNumber(cRaw);
        if(c && c.n >= 0){ prev = c.n; anyCompare = true; }
        else warn('compareValue', i + 1);
      }
      stages.push({label:label, value:value, prev:prev, note:H.str(it.note, LIM.note, warn, m('noteField', label))});
    });
    if(stages.length < LIM.minStages){ errors.push(m('tooFew', stages.length)); return {errors:errors, warnings:warnings}; }
    if(stages.every(function(s){ return s.value === 0; })){ errors.push(m('allZero')); return {errors:errors, warnings:warnings}; }
    if(!format) format = sawCurrency ? 'currency' : 'number';

    var first = stages[0].value, max = 0, drop = -1, dropConv = Infinity;
    stages.forEach(function(s, i){
      max = Math.max(max, s.value);
      s.k = 's' + i;
      s.conv = i ? share(s.value, stages[i - 1].value) : null;
      s.fromStart = i ? share(s.value, first) : (first > 0 ? 100 : null);
      s.grows = i > 0 && s.value > stages[i - 1].value;
      if(s.grows) warn('grows', s.label, stages[i - 1].label);
      if(i && s.conv !== null && s.conv < 100 && s.conv < dropConv){ dropConv = s.conv; drop = i; }
      if(!anyCompare) s.prev = null;
    });
    stages.forEach(function(s){ s.w = max > 0 ? Math.round(s.value / max * 1000) / 10 : 0; });
    var last = stages[stages.length - 1];
    var overall = share(last.value, first);
    var overallPrev = anyCompare && stages[0].prev !== null && last.prev !== null ? share(last.prev, stages[0].prev) : null;
    return {errors:errors, warnings:warnings, spec:Object.assign(out, {
      stages:stages, format:format, compare:anyCompare,
      // The biggest drop only means something when there is more than one step.
      drop:stages.length >= 3 ? drop : -1,
      overall:overall, overallPrev:overallPrev
    })};
  }

  function estHeight(spec){
    var n = spec.stages.length;
    return Math.round(24 + (spec.subtitle ? 24 : 0) + 30 + n * 46 + (n - 1) * 30 + (spec.drop >= 0 ? 30 : 0) + 26 + (spec.source ? 28 : 0));
  }

  function table(spec){
    var en = spec.lang === 'en';
    var header = en ? [spec.format === 'currency' ? 'Value' : 'Count', 'From previous', 'From start'] : [spec.format === 'currency' ? 'Waarde' : 'Aantal', 'Conversie vanaf vorige', 'Conversie vanaf begin'];
    header.unshift(en ? 'Stage' : 'Fase');
    var types = ['text', spec.format, 'percent', 'percent'];
    if(spec.compare){ header.push(en ? 'Previous period' : 'Vorige periode'); types.push(spec.format); }
    return {header:header, types:types, rows:spec.stages.map(function(s){
      var r = [s.label, s.value, s.conv, s.fromStart];
      if(spec.compare) r.push(s.prev);
      return r;
    })};
  }

  K.register('funnel', {
    fences:['funnel', 'trechter'],
    name:{nl:'Trechter', en:'Funnel'},
    noun:{nl:'trechter', en:'funnel'},
    icon:'funnel',
    streamHeight:320,
    validate:validate, estHeight:estHeight, table:table
  });
  if(typeof module !== 'undefined' && module.exports) module.exports = {validate:validate, table:table, estHeight:estHeight, LIMITS:LIM};

  // ── Renderer (kit frame only) ──────────────────────────────────────────────
  var R = root.SWKitRender;
  if(!R) return;
  var TEXT = {
    nl:{overall:function(a, b, p){ return 'Van ' + a + ' naar ' + b + ': ' + p; },
      overallPrev:function(p){ return 'vorige periode ' + p; },
      drop:function(a, b, p){ return 'Grootste uitval: van ' + a + ' naar ' + b + ' (' + p + ' gaat door)'; },
      moveOn:'gaat door naar deze fase', grows:'meer dan de fase ervoor', prev:function(v){ return 'vorige periode ' + v; },
      fromPrev:function(p, l){ return p + ' van ' + l; }, fromStart:function(p){ return p + ' van het begin'; },
      label:'Trechter', pick:'Kies een fase voor de details.'},
    en:{overall:function(a, b, p){ return 'From ' + a + ' to ' + b + ': ' + p; },
      overallPrev:function(p){ return 'previous period ' + p; },
      drop:function(a, b, p){ return 'Biggest drop: from ' + a + ' to ' + b + ' (' + p + ' move on)'; },
      moveOn:'move on to this stage', grows:'more than the stage before', prev:function(v){ return 'previous period ' + v; },
      fromPrev:function(p, l){ return p + ' of ' + l; }, fromStart:function(p){ return p + ' of the start'; },
      label:'Funnel', pick:'Choose a stage for the details.'}
  };

  R.register('funnel', function(box, spec, restore, ctx){
    var lang = ctx.lang() === 'en' ? 'en' : 'nl';
    var t = function(key){ var v = TEXT[lang][key]; return typeof v === 'function' ? v.apply(null, Array.prototype.slice.call(arguments, 1)) : v; };
    var h = ctx.h;
    var num = function(v){ return ctx.fmt(v, spec.format, null); };
    // Under 10% one decimal counts (4,2%, 3,0%); 38% does not need one.
    var pct = function(p){ return p === null ? '' : ctx.fmt(p, 'percent', p < 10 ? 1 : 0); };
    var stages = spec.stages, n = stages.length, first = stages[0], last = stages[n - 1];

    var wrap = h('div', 'k-fn' + (restore && typeof restore.a === 'number' ? ' is-settled' : ''));
    if(spec.overall !== null){
      var sum = h('p', 'k-fn-overall');
      sum.appendChild(h('span', 'k-fn-overall-main', t('overall', first.label, last.label, pct(spec.overall))));
      if(spec.overallPrev !== null) sum.appendChild(h('span', 'k-fn-overall-prev', t('overallPrev', pct(spec.overallPrev))));
      wrap.appendChild(sum);
    }
    var list = h('div', 'k-fn-list');
    list.setAttribute('role', 'group');
    list.setAttribute('aria-label', t('label') + ': ' + spec.title);
    var detail = h('p', 'k-fn-detail');
    detail.setAttribute('role', 'status');
    detail.setAttribute('aria-live', 'polite');
    var buttons = [], rows = [];

    stages.forEach(function(s, i){
      if(i > 0){
        var step = h('div', 'k-fn-step' + (i === spec.drop ? ' is-drop' : '') + (s.grows ? ' is-grows' : ''));
        step.appendChild(h('span', 'k-fn-gap'));
        var chip = h('span', 'k-fn-chip');
        var arrow = h('span', 'k-fn-arrow', s.grows ? '↑' : '↓');
        arrow.setAttribute('aria-hidden', 'true');
        chip.append(arrow, document.createTextNode(pct(s.conv)), h('span', 'k-sr', ' ' + (s.grows ? t('grows') : t('moveOn'))));
        // After a stage of 0 there is no share to show: the arrow alone keeps the rhythm.
        if(s.conv === null) chip.classList.add('is-empty');
        step.appendChild(chip);
        list.appendChild(step);
      }
      var row = h('div', 'k-fn-row' + (i === spec.drop ? ' is-drop' : ''));
      row.style.setProperty('--i', String(i));
      var lab = h('div', 'k-fn-label');
      lab.appendChild(h('span', 'k-fn-name', s.label));
      var meta = [];
      if(s.note) meta.push(s.note);
      if(spec.compare && s.prev !== null) meta.push(t('prev', num(s.prev)));
      if(meta.length) lab.appendChild(h('span', 'k-fn-meta', meta.join(' · ')));
      var track = h('div', 'k-fn-track');
      var b = h('button', 'k-fn-bar');
      b.type = 'button';
      var text = num(s.value);
      // Just wide enough for its own number, so small stages still differ in width.
      b.style.width = 'max(' + (1.8 + text.length * 0.62).toFixed(2) + 'em, ' + s.w + '%)';
      b.appendChild(h('span', 'k-fn-value', text));
      b.setAttribute('aria-label', [s.label, num(s.value), i ? t('fromPrev', pct(s.conv), stages[i - 1].label) : ''].filter(Boolean).join(', '));
      b.setAttribute('aria-pressed', 'false');
      b.tabIndex = i === 0 ? 0 : -1;
      b.addEventListener('click', function(){ select(i, false); });
      b.addEventListener('keydown', function(e){
        var to = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -2;
        if(to === -2) return;
        e.preventDefault();
        to = Math.max(0, Math.min(n - 1, to));
        buttons.forEach(function(x, j){ x.tabIndex = j === to ? 0 : -1; });
        buttons[to].focus();
      });
      lab.addEventListener('click', function(){ select(i, false); });
      track.appendChild(b);
      row.append(lab, track);
      list.appendChild(row);
      buttons.push(b); rows.push(row);
    });
    wrap.appendChild(list);
    if(spec.drop >= 0){
      var d = stages[spec.drop];
      wrap.appendChild(h('p', 'k-fn-drop', t('drop', stages[spec.drop - 1].label, d.label, pct(d.conv))));
    }
    wrap.appendChild(detail);
    if(spec.source) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    function select(i, isRestore){
      var s = stages[i];
      if(!s) return;
      buttons.forEach(function(x, j){ x.setAttribute('aria-pressed', String(j === i)); x.tabIndex = j === i ? 0 : -1; rows[j].classList.toggle('is-active', j === i); });
      var parts = [s.label, num(s.value)];
      if(i){ parts.push(t('fromPrev', pct(s.conv), stages[i - 1].label)); parts.push(t('fromStart', pct(s.fromStart))); }
      if(spec.compare && s.prev !== null) parts.push(t('prev', num(s.prev)));
      if(s.note) parts.push(s.note);
      detail.textContent = parts.filter(Boolean).join(' · ');
      detail.classList.add('is-set');
      if(!isRestore) ctx.save({a:i});
      ctx.resize();
    }
    if(restore && typeof restore.a === 'number' && restore.a >= 0 && restore.a < n) select(restore.a, true);
    return {};
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
