// Data block "funnel" (```funnel, ```trechter): a conversion funnel such as a
// sales pipeline, website visitors to customers or a recruitment process.
//
// {"title", "stages":[{"label", "value", "note"?}], "format"?:"number|currency|percent",
//  "compare"?:[values of a previous period]}  ("steps" also works)
//
// The checks run in the chat (SWKit only); the renderer only registers inside
// the kit frame, where SWKitRender exists. Every text goes in with textContent.

(function(root){
  'use strict';
  // Models write rough numbers: "ca. 900", "120+", "± 300", "1,2k", "2 mln".
  function approx(v, H){
    var n = H.kpiNumber(v);
    if(n || typeof v !== 'string') return n;
    var t0 = v.trim(), rough = /^(>|>=)/.test(t0) || /\+$/.test(t0) ? 'gt' : /^(<|<=)/.test(t0) ? 'lt' : 'ca';
    var s = t0.replace(/^(ca\.?|circa|ongeveer|about|approx\.?|around|±|~|≈|>=|<=|>|<)\s*/i, '').replace(/\s*\+$/, '');
    var mult = 1, mm = /^(.*?)\s*(k|duizend|thousand|mln|mio|miljoen|million|m)\.?$/i.exec(s);
    if(mm){ s = mm[1]; mult = /^(k|duizend|thousand)$/i.test(mm[2]) ? 1e3 : 1e6; }
    n = H.kpiNumber(s);
    return n ? {n:Math.round(n.n * mult * 100) / 100, kind:n.kind, rough:rough} : null;
  }
  var K = root.SWKit;
  if(!K) return;

  var LIM = {stages:8, label:40, note:80, minStages:2};
  var FORMATS = {number:'number', count:'number', aantal:'number', stuks:'number', integer:'number', currency:'currency', euro:'currency', eur:'currency', bedrag:'currency',
    percent:'percent', percentage:'percent', procent:'percent', '%':'percent'};

  var MSG = {
    nl:{
      noStages:function(){ return 'Er zijn geen fasen (stages).'; },
      cut:function(field, max){ return field + ' is ingekort tot ' + max + ' tekens.'; },
      tooFew:function(n){ return 'Een trechter heeft minstens twee fasen met een naam en een getal; er ' + (n === 1 ? 'is er 1' : 'zijn er ' + n) + '.'; },
      allZero:function(){ return 'Alle fasen hebben de waarde 0; er is geen trechter te tonen.'; },
      many:function(n, max){ return 'Er zijn ' + n + ' fasen; alleen de eerste ' + max + ' worden getoond.'; },
      asMap:function(){ return 'De fasen stonden als lijst van namen met getallen; ze zijn in die volgorde getoond.'; },
      item:function(i){ return 'Fase ' + i + ' is geen object met label en value en is weggelaten.'; },
      label:function(i){ return 'Fase ' + i + ' heeft geen naam (label) en is weggelaten.'; },
      value:function(l){ return 'Bij "' + l + '" staat geen getal.'; },
      negative:function(l){ return '"' + l + '" had een negatieve waarde; die is op 0 gezet.'; },
      grows:function(l, prev){ return '"' + l + '" is groter dan de fase ervoor ("' + prev + '"); controleer de volgorde.'; },
      format:function(f){ return 'Onbekend format "' + f + '"; gebruik number, currency of percent. Nu geldt number.'; },
      firstZero:function(l){ return 'De eerste fase ("' + l + '") is 0; de conversie vanaf het begin is niet te berekenen.'; },
      compareLength:function(got, want){ return 'De vergelijking (compare) heeft ' + got + ' waarden, verwacht ' + want + '; ze is weggelaten.'; },
      compareValue:function(i){ return 'Vergelijkingswaarde ' + i + ' is geen getal en is weggelaten.'; },
      compareType:function(){ return 'De vergelijking (compare) is geen lijst met getallen en is weggelaten.'; },
      labelField:function(i){ return 'De naam van fase ' + i; },
      noteField:function(l){ return 'De notitie van "' + l + '"'; }
    },
    en:{
      noStages:function(){ return 'There are no stages.'; },
      cut:function(field, max){ return field + ' was shortened to ' + max + ' characters.'; },
      tooFew:function(n){ return 'A funnel needs at least two stages with a name and a number; there ' + (n === 1 ? 'is 1' : 'are ' + n) + '.'; },
      allZero:function(){ return 'Every stage has the value 0; there is no funnel to show.'; },
      many:function(n, max){ return 'There are ' + n + ' stages; only the first ' + max + ' are shown.'; },
      asMap:function(){ return 'The stages came as names with numbers; they are shown in that order.'; },
      item:function(i){ return 'Stage ' + i + ' is not an object with label and value and was left out.'; },
      label:function(i){ return 'Stage ' + i + ' has no name (label) and was left out.'; },
      value:function(l){ return 'Stage "' + l + '" has no number.'; },
      negative:function(l){ return '"' + l + '" had a negative value; it was set to 0.'; },
      grows:function(l, prev){ return '"' + l + '" is larger than the stage before it ("' + prev + '"); check the order.'; },
      format:function(f){ return 'Unknown format "' + f + '"; use number, currency or percent. Now number is used.'; },
      firstZero:function(l){ return 'The first stage ("' + l + '") is 0; the conversion from the start cannot be worked out.'; },
      compareLength:function(got, want){ return 'The comparison (compare) has ' + got + ' values, expected ' + want + '; it was left out.'; },
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
  // A share from 0 to 100 with four significant digits: 37 of 250.000 stays
  // 0,0148 and never becomes 0. Only the text (pctText) rounds further.
  function share(a, b){ return b > 0 ? Number((a / b * 100).toPrecision(4)) : null; }

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
    // A list of the wrong length would put numbers next to the wrong stages.
    if(compareIn && compareIn.length !== list.length){ warn('compareLength', compareIn.length, list.length); compareIn = null; }
    if(list.length > LIM.stages){ warn('many', list.length, LIM.stages); list = list.slice(0, LIM.stages); }

    var fmtRaw = typeof raw.format === 'string' ? raw.format.trim().toLowerCase() : '';
    var format = '';
    if(fmtRaw){ format = FORMATS[fmtRaw] || ''; if(!format) warn('format', H.str(raw.format, 20)); }
    var sawCurrency = false, sawPercent = false;
    if(errors.length) return {errors:errors, warnings:warnings};
    var stages = [], anyCompare = false;
    list.forEach(function(it, i){
      if(Array.isArray(it) && it.length >= 2) it = {label:it[0], value:it[1], note:it[2]};
      if(!H.isObj(it)){ warn('item', i + 1); return; }
      var label = H.str(it.label != null ? it.label : (it.name != null ? it.name : (it.stage != null ? it.stage : it.title)), LIM.label, warn, m('labelField', i + 1));
      if(!label){ warn('label', i + 1); return; }
      var vRaw = it.value != null ? it.value : (it.count != null ? it.count : (it.amount != null ? it.amount : it.n));
      var v = approx(vRaw, H);
      // A stage without a number is never skipped: the conversions would jump over it.
      if(!v){ errors.push(m('value', label)); return; }
      if(v.kind === 'currency') sawCurrency = true;
      if(v.kind === 'percent') sawPercent = true;
      var value = v.n;
      if(value < 0){ warn('negative', label); value = 0; }
      var prev = null;
      var cRaw = it.compare != null ? it.compare : (it.previous != null ? it.previous : (compareIn ? compareIn[i] : null));
      if(cRaw != null && cRaw !== ''){
        var c = H.kpiNumber(cRaw);
        if(c && c.n >= 0){ prev = c.n; anyCompare = true; }
        else warn('compareValue', i + 1);
      }
      stages.push({label:label, value:value, prev:prev, rough:v.rough || '', note:H.str(it.note, LIM.note, warn, m('noteField', label))});
    });
    if(errors.length) return {errors:errors.slice(0, 1), warnings:warnings};
    if(stages.length < LIM.minStages){ errors.push(m('tooFew', stages.length)); return {errors:errors, warnings:warnings}; }
    if(stages.every(function(s){ return s.value === 0; })){ errors.push(m('allZero')); return {errors:errors, warnings:warnings}; }
    if(!format) format = sawCurrency ? 'currency' : sawPercent ? 'percent' : 'number';
    if(stages[0].value === 0) warn('firstZero', stages[0].label);

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
    stages.forEach(function(s){ s.w = max > 0 ? Number((s.value / max * 100).toPrecision(4)) : 0; });
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
    var what = spec.format === 'currency' ? (en ? 'Value' : 'Waarde') : spec.format === 'percent' ? (en ? 'Share' : 'Aandeel') : (en ? 'Count' : 'Aantal');
    var header = en ? [what, 'From previous', 'From start'] : [what, 'Conversie vanaf vorige', 'Conversie vanaf begin'];
    header.unshift(en ? 'Stage' : 'Fase');
    var types = ['text', spec.format, 'percent', 'percent'];
    if(spec.compare){ header.push(en ? 'Previous period' : 'Vorige periode'); types.push(spec.format); }
    return {header:header, types:types, rows:spec.stages.map(function(s){
      var r = [s.label, s.value, s.conv, s.fromStart];
      if(spec.compare) r.push(s.prev);
      return r;
    })};
  }

  // ── Texts (pure, so the Node test reads the same strings the frame shows) ──
  var TEXT = {
    nl:{overall:function(a, b, p){ return 'Van ' + a + ' naar ' + b + ': ' + p; },
      overallPrev:function(p){ return 'vorige periode ' + p; },
      drop:function(a, b, p){ return 'Grootste uitval: van ' + a + ' naar ' + b + ' (' + p + ' gaat door)'; },
      moveOn:'gaat door naar deze fase', through:'door', grows:'meer dan de fase ervoor', prev:function(v){ return 'vorige periode ' + v; },
      fromPrev:function(p, l){ return p + ' van ' + l; }, fromStart:function(p){ return p + ' van het begin'; },
      label:'Trechter', pick:'Kies een fase voor de details.'},
    en:{overall:function(a, b, p){ return 'From ' + a + ' to ' + b + ': ' + p; },
      overallPrev:function(p){ return 'previous period ' + p; },
      drop:function(a, b, p){ return 'Biggest drop: from ' + a + ' to ' + b + ' (' + p + ' move on)'; },
      moveOn:'move on to this stage', through:'through', grows:'more than the stage before', prev:function(v){ return 'previous period ' + v; },
      fromPrev:function(p, l){ return p + ' of ' + l; }, fromStart:function(p){ return p + ' of the start'; },
      label:'Funnel', pick:'Choose a stage for the details.'}
  };
  // fmt(value, type, decimals) is ctx.fmt in the frame and K.formatValue in Node.
  function texts(spec, fmt){
    var lang = spec.lang === 'en' ? 'en' : 'nl';
    var t = function(key){ var v = TEXT[lang][key]; return typeof v === 'function' ? v.apply(null, Array.prototype.slice.call(arguments, 1)) : v; };
    var num = function(v){ return fmt(v, spec.format, null); };
    // An estimate stays an estimate: "ca. 900", and shares from it in whole percents.
    var ROUGH = {nl:{ca:'ca.', gt:'meer dan', lt:'minder dan', lt1:'minder dan 1%'}, en:{ca:'about', gt:'more than', lt:'less than', lt1:'less than 1%'}}[lang];
    var numS = function(s){ return (s.rough ? ROUGH[s.rough] + ' ' : '') + num(s.value); };
    var anyRough = spec.stages.some(function(s){ return s.rough; });
    // A share from an estimate is an estimate too: "ca. 4%", never "3,9%".
    var pctR = function(p, rough){ if(p === null || p === undefined) return ''; if(!rough) return pct(p); return p > 0 && p < 1 ? ROUGH.lt1 : ROUGH.ca + ' ' + fmt(Math.round(p), 'percent', 0); };
    // 0% only for a real 0. From 10% whole numbers (38%), from 0,1% one decimal
    // (4,2%, 0,4%), below that two significant digits (0,015%), and never a
    // rounded 100% for a share that is not quite all.
    var pct = function(p){
      if(p === null || p === undefined) return '';
      if(p === 0) return fmt(0, 'percent', 0);
      if(p < 0.001) return '<' + fmt(0.001, 'percent', 3);
      if(p < 0.1){ var r = Number(p.toPrecision(2)); return fmt(r, 'percent', Math.min(4, (String(r).split('.')[1] || '').length)); }
      if(p < 10) return fmt(p, 'percent', 1);
      if(p >= 99.5 && p < 100) return fmt(p, 'percent', p >= 99.95 ? 2 : 1);
      return fmt(p, 'percent', 0);
    };
    var stages = spec.stages;
    // Each part only when its number exists: no " van Oud" after a stage of 0.
    function shares(i){
      var s = stages[i], out = [];
      var rp = !!(s.rough || (i && stages[i - 1].rough)), rs = !!(s.rough || stages[0].rough);
      if(i && s.conv !== null) out.push(t('fromPrev', pctR(s.conv, rp), stages[i - 1].label));
      if(i && s.fromStart !== null) out.push(t('fromStart', pctR(s.fromStart, rs)));
      return out;
    }
    return {
      t:t, num:num, numS:numS, pct:pct,
      overall:function(){ return spec.overall === null ? '' : t('overall', stages[0].label, stages[stages.length - 1].label, pctR(spec.overall, anyRough)); },
      overallPrev:function(){ return spec.overallPrev === null ? '' : t('overallPrev', pct(spec.overallPrev)); },
      drop:function(){ return spec.drop < 0 ? '' : t('drop', stages[spec.drop - 1].label, stages[spec.drop].label, pctR(stages[spec.drop].conv, !!(stages[spec.drop].rough || stages[spec.drop - 1].rough))); },
      chip:function(i){ return pctR(stages[i].conv, !!(stages[i].rough || stages[i - 1].rough)); },
      aria:function(i){ var s = stages[i], p = [s.label, numS(s)]; if(i && s.conv !== null) p.push(t('fromPrev', pctR(s.conv, !!(s.rough || stages[i - 1].rough)), stages[i - 1].label)); return p.join(', '); },
      detail:function(i){
        var s = stages[i], parts = [s.label, numS(s)].concat(shares(i));
        if(spec.compare && s.prev !== null) parts.push(t('prev', num(s.prev)));
        if(s.note) parts.push(s.note);
        return parts.filter(Boolean).join(' · ');
      }
    };
  }

  K.register('funnel', {
    fences:['funnel', 'trechter'],
    name:{nl:'Trechter', en:'Funnel'},
    noun:{nl:'trechter', en:'funnel'},
    icon:'funnel',
    streamHeight:320,
    validate:validate, estHeight:estHeight, table:table
  });
  if(typeof module !== 'undefined' && module.exports) module.exports = {validate:validate, table:table, estHeight:estHeight, texts:texts, LIMITS:LIM};

  // ── Renderer (kit frame only) ──────────────────────────────────────────────
  var R = root.SWKitRender;
  if(!R) return;

  R.register('funnel', function(box, spec, restore, ctx){
    var X = texts(Object.assign({}, spec, {lang:ctx.lang() === 'en' ? 'en' : 'nl'}), ctx.fmt);
    var t = X.t, num = X.num;
    var h = ctx.h;
    var stages = spec.stages, n = stages.length;
    // The grow-in plays once: any saved state (a choice, or -1 for "drawn
    // before") draws the bars in place.
    var seen = !!(restore && typeof restore.a === 'number');

    var wrap = h('div', 'k-fn' + (seen ? ' is-settled' : ''));
    if(spec.overall !== null){
      var sum = h('p', 'k-fn-overall');
      sum.appendChild(h('span', 'k-fn-overall-main', X.overall()));
      if(spec.overallPrev !== null) sum.appendChild(h('span', 'k-fn-overall-prev', X.overallPrev()));
      wrap.appendChild(sum);
    }
    var list = h('div', 'k-fn-list');
    list.setAttribute('role', 'group');
    list.setAttribute('aria-label', t('label') + ': ' + spec.title);
    var detail = h('p', 'k-fn-detail');
    detail.setAttribute('role', 'status');
    detail.setAttribute('aria-live', 'polite');
    var buttons = [], rows = [];
    // Every bar starts at the width of the longest number in the block and adds
    // its share of the rest, so a larger value always gets a wider bar.
    var valueTexts = stages.map(function(s){ return X.numS ? X.numS(s) : num(s.value); });
    var minEm = (1.8 + Math.max.apply(null, valueTexts.map(function(x){ return x.length; })) * 0.62).toFixed(2);

    stages.forEach(function(s, i){
      if(i > 0){
        var step = h('div', 'k-fn-step' + (i === spec.drop ? ' is-drop' : '') + (s.grows ? ' is-grows' : ''));
        step.appendChild(h('span', 'k-fn-gap'));
        var chip = h('span', 'k-fn-chip');
        var arrow = h('span', 'k-fn-arrow', s.grows ? '↑' : '↓');
        arrow.setAttribute('aria-hidden', 'true');
        // "25% door" reads as the share that moves on, never as a drop of 25%.
        chip.append(arrow, document.createTextNode(X.chip(i) + (s.conv === null || s.grows ? '' : ' ' + t('through'))), h('span', 'k-sr', ' ' + (s.grows ? t('grows') : t('moveOn'))));
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
      b.style.width = 'calc(' + minEm + 'em + (100% - ' + minEm + 'em) * ' + (s.w / 100) + ')';
      b.appendChild(h('span', 'k-fn-value', valueTexts[i]));
      b.setAttribute('aria-label', X.aria(i));
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
    // The amber chip already marks the biggest drop; the sentence is for screen readers.
    if(spec.drop >= 0) wrap.appendChild(h('p', 'k-sr', X.drop()));
    wrap.appendChild(detail);
    if(spec.source) wrap.appendChild(h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    function select(i, isRestore){
      if(!stages[i]) return;
      buttons.forEach(function(x, j){ x.setAttribute('aria-pressed', String(j === i)); x.tabIndex = j === i ? 0 : -1; rows[j].classList.toggle('is-active', j === i); });
      detail.textContent = X.detail(i);
      detail.classList.add('is-set');
      if(!isRestore){ ctx.save({a:i}); if(ctx.reveal) ctx.reveal(detail); }
      ctx.resize();
    }
    if(seen && restore.a >= 0 && restore.a < n) select(restore.a, true);
    else if(!seen) ctx.save({a:-1});
    return {};
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
