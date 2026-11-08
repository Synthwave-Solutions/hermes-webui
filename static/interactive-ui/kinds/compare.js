// Data block "compare": two to four option cards side by side, to help a
// business user choose between suppliers, plans, tools or scenarios.
//
// Shape: {"title", "options":[{"name", "price"?, "priceUnit"?, "score"?,
//   "pros":[...], "cons":[...], "facts"?:{"Levertijd":"3 weken"}, "tag"?}],
//   "recommended"?:"<name>", "criteria"?:[...]}
//
// Loaded by the chat (checks only, SWKit) and by the kit frame (checks plus
// the renderer, SWKitRender). Every value reaches the page with textContent.
(function(root){
  'use strict';
  var K = root.SWKit;
  if(!K) return;

  var LIM = {options:4, name:50, tag:32, unit:24, priceText:40, items:6, item:140, facts:8, factKey:32, factValue:80,
    criteria:6, criterion:40};
  var REC_WORDS = /^(aanrader|aanbevolen|onze aanrader|beste keuze|advies|recommended|our pick|best choice|top pick)$/i;

  var MSG = {
    nl:{
      noOptions:function(){ return 'Er zijn geen opties (options) om te vergelijken.'; },
      tooFew:function(n){ return 'Een vergelijking heeft minstens twee opties met een naam (name); er ' + (n === 1 ? 'is er 1' : 'zijn er ' + n) + '.'; },
      many:function(n, max){ return 'Er zijn ' + n + ' opties; alleen ' + max + ' worden getoond.'; },
      item:function(i){ return 'Optie ' + i + ' is geen object met een naam en is weggelaten.'; },
      name:function(i){ return 'Optie ' + i + ' heeft geen naam (name) en is weggelaten.'; },
      dup:function(n){ return 'De naam "' + n + '" komt vaker voor; er is een nummer achter gezet.'; },
      price:function(n){ return 'De prijs van "' + n + '" is geen getal van 0 of meer en is weggelaten.'; },
      score:function(n, max){ return 'De score van "' + n + '" is geen getal van 0 tot en met ' + max + ' en is weggelaten.'; },
      scoreMax:function(v){ return 'scoreMax "' + v + '" wordt niet gebruikt; kies 5, 10 of 100.'; },
      list:function(n, what){ return what + ' van "' + n + '" moeten een lijst met korte zinnen zijn; wat geen tekst is, is weggelaten.'; },
      manyItems:function(n, what, max){ return what + ' van "' + n + '": alleen de eerste ' + max + ' worden getoond.'; },
      facts:function(n){ return 'De feiten (facts) van "' + n + '" zijn geen object met label en waarde en zijn weggelaten.'; },
      fact:function(n, k){ return 'Het feit "' + k + '" bij "' + n + '" heeft geen tekst of getal als waarde en is weggelaten.'; },
      manyFacts:function(max){ return 'Er zijn meer dan ' + max + ' soorten feiten; alleen de eerste ' + max + ' worden getoond.'; },
      rec:function(r){ return 'De aanrader "' + r + '" is geen van de opties; het label is weggelaten.'; },
      recMany:function(n){ return 'Er is meer dan één aanrader; alleen "' + n + '" krijgt het label.'; },
      criteria:function(){ return 'De criteria zijn geen lijst met korte woorden; wat geen tekst is, is weggelaten.'; },
      pros:'De pluspunten', cons:'De minpunten'
    },
    en:{
      noOptions:function(){ return 'There are no options to compare.'; },
      tooFew:function(n){ return 'A comparison needs at least two options with a name; there ' + (n === 1 ? 'is 1' : 'are ' + n) + '.'; },
      many:function(n, max){ return 'There are ' + n + ' options; only ' + max + ' are shown.'; },
      item:function(i){ return 'Option ' + i + ' is not an object with a name and was left out.'; },
      name:function(i){ return 'Option ' + i + ' has no name and was left out.'; },
      dup:function(n){ return 'The name "' + n + '" appears more than once; a number was added.'; },
      price:function(n){ return 'The price of "' + n + '" is not a number of 0 or more and was left out.'; },
      score:function(n, max){ return 'The score of "' + n + '" is not a number from 0 to ' + max + ' and was left out.'; },
      scoreMax:function(v){ return 'scoreMax "' + v + '" is not used; choose 5, 10 or 100.'; },
      list:function(n, what){ return what + ' of "' + n + '" must be a list of short sentences; anything that is not text was left out.'; },
      manyItems:function(n, what, max){ return what + ' of "' + n + '": only the first ' + max + ' are shown.'; },
      facts:function(n){ return 'The facts of "' + n + '" are not an object with labels and values and were left out.'; },
      fact:function(n, k){ return 'The fact "' + k + '" of "' + n + '" has no text or number as its value and was left out.'; },
      manyFacts:function(max){ return 'There are more than ' + max + ' kinds of facts; only the first ' + max + ' are shown.'; },
      rec:function(r){ return 'The recommended option "' + r + '" is not one of the options; the label was left out.'; },
      recMany:function(n){ return 'More than one option is recommended; only "' + n + '" gets the label.'; },
      criteria:function(){ return 'The criteria are not a list of short words; anything that is not text was left out.'; },
      pros:'The pros', cons:'The cons'
    }
  };

  function first(o, keys){
    for(var i = 0; i < keys.length; i++) if(o[keys[i]] !== undefined && o[keys[i]] !== null) return o[keys[i]];
    return undefined;
  }
  function norm(s){ return String(s || '').trim().toLowerCase().replace(/\s+/g, ' '); }
  // "maand" and "/maand" read as "per maand".
  function unitText(u){
    u = String(u || '').trim().replace(/^\/\s*/, '');
    if(!u) return '';
    if(/^(per|p\.|pp|ex|excl|incl|eenmalig|one-off|once|vanaf|from)\b/i.test(u)) return u;
    return 'per ' + u;
  }
  // A price: a number, "€ 49,-" or "€ 49 per maand" (the unit is split off).
  function readPrice(v, H){
    if(typeof v === 'number') return Number.isFinite(v) ? {n:v} : {bad:true};
    if(typeof v !== 'string' || !v.trim()) return {bad:true};
    var p = H.parseNumber(v);
    if(Number.isFinite(p.n)) return {n:p.n};
    var m = /^(.*?\d(?:[\d.,]*\d)?(?:,-)?)\s*(?:\/|per\s+|p\/)\s*(.+)$/i.exec(v.trim());
    if(m){ var q = H.parseNumber(m[1]); if(Number.isFinite(q.n)) return {n:q.n, unit:unitText(m[2])}; }
    return {text:v};
  }
  // A score: 8, "8,5", "8/10" or "85%".
  function readScore(v, H){
    if(typeof v === 'number') return Number.isFinite(v) ? {n:v} : null;
    if(typeof v !== 'string') return null;
    var m = /^\s*([\d.,]+)\s*(?:\/|van|of|uit|out of)\s*(\d+)\s*$/i.exec(v);
    if(m){ var a = H.parseNumber(m[1]), b = Number(m[2]); return Number.isFinite(a.n) && b > 0 ? {n:a.n, max:b} : null; }
    var p = H.parseNumber(v);
    if(!Number.isFinite(p.n)) return null;
    return p.kind === 'percent' ? {n:p.n, max:100} : {n:p.n};
  }

  function validate(raw, lang, H){
    var L = MSG[lang === 'en' ? 'en' : 'nl'];
    var errors = [], warnings = [];
    var warn = function(msg){ if(warnings.indexOf(msg) < 0) warnings.push(msg); };
    var cutWarn = function(k){ warnings.push(H.m.apply(null, arguments)); };
    var out = H.base(raw, 'compare', warnings);
    var list = first(raw, ['options', 'opties', 'items', 'choices', 'keuzes']);
    if(!Array.isArray(list) || !list.length){ errors.push(L.noOptions()); return {errors:errors, warnings:warnings}; }

    // Which option is recommended: by name, by position, or flagged on the option.
    var recRaw = first(raw, ['recommended', 'aanrader', 'aanbevolen', 'recommendation']);
    var recName = typeof recRaw === 'string' ? norm(recRaw) : '';
    var recPos = typeof recRaw === 'number' && recRaw >= 1 && recRaw <= list.length ? Math.round(recRaw) - 1 : -1;

    var opts = [];
    list.forEach(function(o, i){
      if(typeof o === 'string' && o.trim()) o = {name:o};
      if(!H.isObj(o)){ warn(L.item(i + 1)); return; }
      var name = H.str(first(o, ['name', 'naam', 'title', 'label', 'option', 'optie']), LIM.name, cutWarn, H.fieldName('De naam van optie ' + (i + 1), 'The name of option ' + (i + 1)));
      if(!name){ warn(L.name(i + 1)); return; }
      opts.push({o:o, i:i, name:name});
    });

    var recIdx = -1, recCount = 0;
    opts.forEach(function(x, k){
      var tag = norm(first(x.o, ['tag', 'badge']));
      var flagged = x.o.recommended === true || x.o.aanrader === true || x.o.aanbevolen === true;
      var hit = (recName && norm(x.name) === recName) || recPos === x.i || (!recName && recPos < 0 && (flagged || REC_WORDS.test(tag)));
      if(hit){ recCount++; if(recIdx < 0) recIdx = k; }
    });
    if(recName && recIdx < 0) warn(L.rec(H.str(recRaw, LIM.name)));
    if(recCount > 1 && recIdx >= 0) warn(L.recMany(opts[recIdx].name));

    // More than four: keep the first ones, and the recommended one.
    if(opts.length > LIM.options){
      warn(L.many(opts.length, LIM.options));
      var keep = opts.slice(0, LIM.options);
      if(recIdx >= LIM.options){ keep = opts.slice(0, LIM.options - 1).concat([opts[recIdx]]); recIdx = LIM.options - 1; }
      opts = keep;
    }
    if(opts.length < 2){ errors.push(L.tooFew(opts.length)); return {errors:errors, warnings:warnings}; }

    // Duplicate names get a number, so the cards and the export stay apart.
    var seen = {};
    opts.forEach(function(x){
      var k = norm(x.name);
      if(seen[k]){ seen[k]++; warn(L.dup(x.name)); x.name = x.name.slice(0, LIM.name - 4) + ' (' + seen[k] + ')'; }
      else seen[k] = 1;
    });

    var scoreMaxRaw = raw.scoreMax != null ? raw.scoreMax : raw.scoreScale;
    var scoreMax = null;
    if(scoreMaxRaw != null && scoreMaxRaw !== ''){
      var sm = Number(scoreMaxRaw);
      if(sm === 5 || sm === 10 || sm === 100) scoreMax = sm; else warn(L.scoreMax(H.str(scoreMaxRaw, 12)));
    }

    var factKeys = [], factNorm = {}, factsCut = false;
    var options = opts.map(function(x){
      var o = x.o, name = x.name;
      var opt = {name:name, price:null, priceText:'', priceUnit:'', score:null, scoreMax:null, pros:[], cons:[], facts:{}, tag:''};
      var pv = first(o, ['price', 'prijs', 'cost', 'kosten', 'bedrag']);
      if(pv !== undefined && pv !== ''){
        var pr = readPrice(pv, H);
        if(pr.text) opt.priceText = H.str(pr.text.trim().charAt(0).toUpperCase() + pr.text.trim().slice(1), LIM.priceText, cutWarn, H.fieldName('De prijs van "' + name + '"', 'The price of "' + name + '"'));
        else if(pr.bad || pr.n < 0) warn(L.price(name));
        else { opt.price = pr.n; if(pr.unit) opt.priceUnit = H.str(pr.unit, LIM.unit); }
      }
      var uv = first(o, ['priceUnit', 'unit', 'per', 'eenheid', 'prijsEenheid']);
      if(uv !== undefined && (opt.price !== null || opt.priceText)) opt.priceUnit = H.str(unitText(H.str(uv, 60)), LIM.unit, cutWarn, H.fieldName('De eenheid van de prijs van "' + name + '"', 'The price unit of "' + name + '"')) || opt.priceUnit;
      var sv = first(o, ['score', 'rating', 'cijfer', 'waardering']);
      if(sv !== undefined && sv !== ''){
        var sc = readScore(sv, H);
        if(sc && sc.n >= 0){ opt.score = sc.n; opt.scoreMax = sc.max || null; }
        else warn(L.score(name, scoreMax || 10));
      }
      ['pros', 'cons'].forEach(function(which){
        var v = first(o, which === 'pros' ? ['pros', 'plus', 'pluspunten', 'plussen', 'voordelen', 'advantages'] : ['cons', 'minus', 'minpunten', 'minnen', 'nadelen', 'disadvantages']);
        if(v === undefined) return;
        if(typeof v === 'string') v = [v];
        if(!Array.isArray(v)){ warn(L.list(name, L[which])); return; }
        var items = [], bad = false;
        v.forEach(function(it){
          var s = typeof it === 'string' ? H.str(it, LIM.item, cutWarn, H.fieldName(L[which] + ' van "' + name + '"', L[which] + ' of "' + name + '"')) : '';
          if(s) items.push(s); else if(it !== '' && it != null) bad = true;
        });
        if(bad) warn(L.list(name, L[which]));
        if(items.length > LIM.items){ warn(L.manyItems(name, L[which], LIM.items)); items = items.slice(0, LIM.items); }
        opt[which] = items;
      });
      var fv = first(o, ['facts', 'feiten', 'details', 'kenmerken', 'specs']);
      var pairs = [];
      if(H.isObj(fv)) Object.keys(fv).forEach(function(k){ pairs.push([k, fv[k]]); });
      else if(Array.isArray(fv)) fv.forEach(function(f){ if(H.isObj(f)) pairs.push([first(f, ['label', 'name', 'key', 'naam']), first(f, ['value', 'waarde'])]); else pairs.push([null, null]); });
      else if(fv !== undefined) warn(L.facts(name));
      pairs.forEach(function(p){
        var key = H.str(p[0], LIM.factKey);
        if(!key){ warn(L.facts(name)); return; }
        var v = p[1], val;
        if(typeof v === 'number' && Number.isFinite(v)) val = v;
        else if(typeof v === 'boolean') val = lang === 'en' ? (v ? 'Yes' : 'No') : (v ? 'Ja' : 'Nee');
        else if(typeof v === 'string' && v.trim()) val = H.str(v, LIM.factValue, cutWarn, H.fieldName('Het feit "' + key + '" van "' + name + '"', 'The fact "' + key + '" of "' + name + '"'));
        else { warn(L.fact(name, key)); return; }
        var nk = norm(key);
        if(!factNorm[nk]){
          if(factKeys.length >= LIM.facts){ factsCut = true; return; }
          factNorm[nk] = key; factKeys.push(key);
        }
        opt.facts[factNorm[nk]] = val;
      });
      var tag = H.str(first(o, ['tag', 'badge']), LIM.tag, cutWarn, H.fieldName('Het label van "' + name + '"', 'The tag of "' + name + '"'));
      opt.tag = tag;
      return opt;
    });
    if(factsCut) warn(L.manyFacts(LIM.facts));

    // One scale for all scores: 10 unless a score or the block says otherwise.
    var given = options.map(function(o){ return o.scoreMax; }).filter(Boolean);
    var scale = scoreMax || (given.length ? Math.max.apply(null, given) : 0);
    if(!scale) scale = options.some(function(o){ return o.score !== null && o.score > 10; }) ? 100 : 10;
    options.forEach(function(o){
      if(o.score === null) return;
      var v = o.scoreMax && o.scoreMax !== scale ? o.score / o.scoreMax * scale : o.score;
      if(!(v >= 0 && v <= scale)){ warn(L.score(o.name, scale)); o.score = null; }
      else o.score = Math.round(v * 10) / 10;
    });
    options.forEach(function(o){ delete o.scoreMax; });

    // A tag that only says "recommended" is the label's job (and only one card has it).
    options.forEach(function(o){ if(REC_WORDS.test(norm(o.tag))) o.tag = ''; });

    var criteria = [];
    var cr = first(raw, ['criteria', 'criteria_nl', 'vergelijkOp']);
    if(cr !== undefined){
      if(typeof cr === 'string') cr = cr.split(/\s*[,;]\s*/);
      if(!Array.isArray(cr)) warn(L.criteria());
      else {
        var badC = false;
        cr.forEach(function(c){ var s = typeof c === 'string' ? H.str(c, LIM.criterion) : ''; if(s) criteria.push(s); else badC = true; });
        if(badC) warn(L.criteria());
        criteria = criteria.slice(0, LIM.criteria);
      }
    }

    return {errors:errors, warnings:warnings, spec:Object.assign(out, {
      options:options, recommended:recIdx, criteria:criteria, scoreMax:scale, factKeys:factKeys,
      hasPrice:options.some(function(o){ return o.price !== null || !!o.priceText; }),
      hasScore:options.some(function(o){ return o.score !== null; })
    })};
  }

  function rowsOf(spec){
    var hasTop = spec.recommended >= 0 || spec.options.some(function(o){ return !!o.tag; });
    var rows = [];
    if(hasTop) rows.push('top');
    rows.push('name');
    if(spec.hasPrice) rows.push('price');
    if(spec.hasScore) rows.push('score');
    spec.factKeys.forEach(function(k, i){ rows.push('fact' + i); });
    if(spec.options.some(function(o){ return o.pros.length; })) rows.push('pros');
    if(spec.options.some(function(o){ return o.cons.length; })) rows.push('cons');
    return rows;
  }

  function estHeight(spec){
    var max = function(k){ return Math.max.apply(null, spec.options.map(function(o){ return o[k].length; })); };
    var h = 24 + (spec.subtitle ? 24 : 0) + (spec.criteria.length ? 26 : 0) + 30;
    h += (spec.recommended >= 0 || spec.options.some(function(o){ return o.tag; }) ? 28 : 0) + 30;
    h += (spec.hasPrice ? 40 : 0) + (spec.hasScore ? 40 : 0) + spec.factKeys.length * 36;
    h += max('pros') * 26 + max('cons') * 26 + (max('pros') && max('cons') ? 12 : 0);
    return Math.round(h + (spec.source ? 28 : 0));
  }

  function table(spec){
    var en = spec.lang === 'en';
    var header = (en ? ['Option', 'Price', 'Score', 'Pros', 'Cons'] : ['Optie', 'Prijs', 'Score', 'Pluspunten', 'Minpunten']).concat(spec.factKeys);
    var rows = spec.options.map(function(o){
      var price = o.price !== null ? o.price : (o.priceText || null);
      return [o.name, price, o.score, o.pros.join('; '), o.cons.join('; ')].concat(spec.factKeys.map(function(k){
        return o.facts[k] === undefined ? null : o.facts[k];
      }));
    });
    return {header:header, rows:rows, types:['text', 'currency', 'number', 'text', 'text'].concat(spec.factKeys.map(function(k){
      return spec.options.every(function(o){ return o.facts[k] === undefined || typeof o.facts[k] === 'number'; }) ? 'number' : 'text';
    }))};
  }

  K.register('compare', {
    fences:['compare', 'vergelijk', 'vergelijking', 'options', 'opties', 'comparison'],
    name:{nl:'Vergelijking', en:'Comparison'},
    noun:{nl:'vergelijking', en:'comparison'},
    icon:'compare',
    streamHeight:360,
    validate:validate, estHeight:estHeight, table:table
  });

  // ── Renderer (kit frame only) ─────────────────────────────────────────────
  if(!root.SWKitRender || typeof document === 'undefined') return;
  var TEXT = {
    nl:{rec:'Aanrader', score:'Score', of:function(v, m){ return v + ' van ' + m; }, unknown:'Niet bekend', free:'Gratis',
      pro:'Pluspunt: ', con:'Minpunt: ', criteria:'Vergeleken op: ', and:' en ', option:function(i, n){ return 'Optie ' + i + ' van ' + n; },
      show:function(name){ return 'Toon ' + name; }, list:'Opties'},
    en:{rec:'Recommended', score:'Score', of:function(v, m){ return v + ' of ' + m; }, unknown:'Not known', free:'Free',
      pro:'Pro: ', con:'Con: ', criteria:'Compared on: ', and:' and ', option:function(i, n){ return 'Option ' + i + ' of ' + n; },
      show:function(name){ return 'Show ' + name; }, list:'Options'}
  };
  var REDUCED = false;
  try{ REDUCED = root.matchMedia('(prefers-reduced-motion: reduce)').matches; }catch(_){}

  root.SWKitRender.register('compare', function(box, spec, restore, ctx){
    var h = ctx.h, T = TEXT[ctx.lang() === 'en' ? 'en' : 'nl'];
    var n = spec.options.length, rows = rowsOf(spec);
    if(spec.criteria.length){
      var c = spec.criteria;
      var joined = c.length > 1 ? c.slice(0, -1).join(', ') + T.and + c[c.length - 1] : c[0];
      box.appendChild(h('p', 'k-note k-cmp-criteria', T.criteria + joined));
    }
    var grid = h('div', 'k-cmp');
    grid.setAttribute('role', 'list');
    grid.setAttribute('aria-label', T.list);
    grid.style.setProperty('--k-cols', String(n));
    grid.style.setProperty('--k-rows', String(rows.length));
    var cards = spec.options.map(function(o, i){
      var rec = i === spec.recommended;
      var card = h('div', 'k-cmp-card' + (rec ? ' is-rec' : ''));
      card.setAttribute('role', 'listitem');
      card.tabIndex = 0;
      card.style.gridRow = 'span ' + rows.length;
      card.setAttribute('aria-label', T.option(i + 1, n) + ': ' + o.name + (rec ? ', ' + T.rec.toLowerCase() : ''));
      rows.forEach(function(r){
        var cell;
        if(r === 'top'){
          cell = h('div', 'k-cmp-top');
          if(rec) cell.appendChild(h('span', 'k-cmp-badge is-rec', T.rec));
          if(o.tag){ var tg = h('span', 'k-cmp-badge', o.tag); tg.title = o.tag; cell.appendChild(tg); }
        } else if(r === 'name'){
          cell = h('div', 'k-cmp-name', o.name);
        } else if(r === 'price'){
          cell = h('div', 'k-cmp-price');
          if(o.price !== null) cell.appendChild(h('span', 'k-cmp-amount', o.price === 0 ? T.free : ctx.fmt(o.price, 'currency')));
          else if(o.priceText) cell.appendChild(h('span', 'k-cmp-amount is-text', o.priceText));
          else cell.appendChild(h('span', 'k-cmp-missing', T.unknown));
          if(o.priceUnit && (o.price || o.priceText)) cell.appendChild(h('span', 'k-cmp-unit', o.priceUnit));
        } else if(r === 'score'){
          cell = h('div', 'k-cmp-score');
          var line = h('div', 'k-cmp-row');
          line.appendChild(h('span', 'k-cmp-label', T.score));
          var val = o.score === null ? T.unknown : T.of(ctx.fmt(o.score, 'number'), ctx.fmt(spec.scoreMax, 'number'));
          line.appendChild(h('span', 'k-cmp-value' + (o.score === null ? ' k-cmp-missing' : ''), val));
          cell.appendChild(line);
          if(o.score !== null){
            var bar = h('div', 'k-cmp-bar'), fill = h('span', 'k-cmp-fill');
            fill.style.width = Math.max(0, Math.min(100, o.score / spec.scoreMax * 100)) + '%';
            bar.appendChild(fill);
            bar.setAttribute('aria-hidden', 'true');
            cell.appendChild(bar);
          }
        } else if(r.indexOf('fact') === 0){
          var key = spec.factKeys[Number(r.slice(4))], fv = o.facts[key];
          cell = h('div', 'k-cmp-fact');
          cell.appendChild(h('span', 'k-cmp-label', key));
          cell.appendChild(h('span', 'k-cmp-value' + (fv === undefined ? ' k-cmp-missing' : ''), fv === undefined ? T.unknown : (typeof fv === 'number' ? ctx.fmt(fv, 'number') : fv)));
        } else {
          cell = h('ul', 'k-cmp-list is-' + r);
          o[r].forEach(function(t){
            var li = h('li');
            var ico = h('span', 'k-cmp-ico', r === 'pros' ? '✓' : '−');
            ico.setAttribute('aria-hidden', 'true');
            li.append(ico, h('span', 'k-sr', r === 'pros' ? T.pro : T.con), h('span', 'k-cmp-text', t));
            cell.appendChild(li);
          });
        }
        cell.classList.add('k-cmp-cell');
        card.appendChild(cell);
      });
      grid.appendChild(card);
      return card;
    });
    box.appendChild(grid);

    // On a phone the cards swipe; the dots show where you are and jump there.
    var dots = h('div', 'k-cmp-dots');
    var dotBtns = spec.options.map(function(o, i){
      var b = h('button', 'k-cmp-dot');
      b.type = 'button';
      b.setAttribute('aria-label', T.show(o.name));
      b.addEventListener('click', function(){ go(i, true); });
      dots.appendChild(b);
      return b;
    });
    box.appendChild(dots);
    if(spec.source) box.appendChild(h('p', 'k-source', spec.source));

    var active = -1;
    function swiping(){ return grid.scrollWidth > grid.clientWidth + 4; }
    function setActive(i){
      if(i === active) return;
      active = i;
      dotBtns.forEach(function(b, k){ b.setAttribute('aria-current', k === i ? 'true' : 'false'); });
    }
    function go(i, focus){
      i = Math.max(0, Math.min(n - 1, i));
      var card = cards[i];
      if(swiping()) grid.scrollTo({left:card.offsetLeft - grid.offsetLeft - parseFloat(getComputedStyle(grid).paddingLeft || 0), behavior:REDUCED ? 'auto' : 'smooth'});
      if(focus) card.focus({preventScroll:true});
      setActive(i);
    }
    var scrollTimer = 0;
    grid.addEventListener('scroll', function(){
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function(){
        var best = 0, dist = Infinity, left = grid.scrollLeft;
        cards.forEach(function(c, k){ var d = Math.abs(c.offsetLeft - grid.offsetLeft - left); if(d < dist){ dist = d; best = k; } });
        setActive(best);
        ctx.save({i:best});
      }, 90);
    }, {passive:true});
    cards.forEach(function(card, i){
      card.addEventListener('keydown', function(e){
        var to = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -2;
        if(to === -2) return;
        e.preventDefault();
        go(to, true);
      });
      card.addEventListener('focus', function(){ setActive(i); });
    });
    var start = restore && typeof restore.i === 'number' && restore.i >= 0 && restore.i < n ? Math.round(restore.i) : 0;
    setActive(start);
    if(start > 0) requestAnimationFrame(function(){ if(swiping()) grid.scrollLeft = cards[start].offsetLeft - grid.offsetLeft; });
    ctx.resize();
    return {onTheme:function(){}};
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
