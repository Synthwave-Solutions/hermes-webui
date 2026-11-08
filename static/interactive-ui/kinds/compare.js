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
      recWhich:function(r){ return 'De aanrader (recommended: ' + r + ') wijst geen van de opties aan; geef de naam of het nummer van een optie. Het label is weggelaten.'; },
      currency:function(n){ return 'De prijs van "' + n + '" staat niet in euro en wordt als tekst getoond.'; },
      manyCriteria:function(max){ return 'Er zijn meer dan ' + max + ' criteria; alleen de eerste ' + max + ' worden getoond.'; },
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
      recWhich:function(r){ return 'The recommended value (' + r + ') points at none of the options; give the name or the number of an option. The label was left out.'; },
      currency:function(n){ return 'The price of "' + n + '" is not in euros and is shown as text.'; },
      manyCriteria:function(max){ return 'There are more than ' + max + ' criteria; only the first ' + max + ' are shown.'; },
      recMany:function(n){ return 'More than one option is recommended; only "' + n + '" gets the label.'; },
      criteria:function(){ return 'The criteria are not a list of short words; anything that is not text was left out.'; },
      pros:'The pros', cons:'The cons'
    }
  };

  function first(o, keys){
    for(var i = 0; i < keys.length; i++) if(own(o, keys[i]) && o[keys[i]] !== undefined && o[keys[i]] !== null) return o[keys[i]];
    return undefined;
  }
  function own(o, k){ return Object.prototype.hasOwnProperty.call(o, k); }
  // Labels come from the model: "constructor" or "__proto__" must stay plain keys.
  function put(o, k, v){ Object.defineProperty(o, k, {value:v, enumerable:true, writable:true, configurable:true}); }
  function norm(s){ return String(s || '').trim().toLowerCase().replace(/\s+/g, ' '); }

  // Only a bare noun gets "per" in front: "maand" and "/maand" read as "per
  // maand", but "maandelijks", "exclusief btw" or "eenmalig" stay as written.
  var PER_NOUN = /^(maand|mnd|jaar|jr|week|wk|dag|uur|kwartaal|stuk|gebruiker|medewerker|persoon|licentie|werkplek|plek|apparaat|locatie|vestiging|user|seat|month|mo|year|yr|day|hour|quarter|piece|unit|item|license|licence|employee|person|device|site|location)(\b|$)/i;
  function unitText(u){
    u = String(u || '').trim().replace(/\s+/g, ' ');
    if(/^(p\/m|p\.m\.?|pm|\/m)$/i.test(u)) return 'per maand';
    if(/^(p\/j|p\.j\.?|\/j|p\/y)$/i.test(u)) return 'per jaar';
    u = u.replace(/^\/\s*/, '');
    if(!u) return '';
    return PER_NOUN.test(u) ? 'per ' + u : u;
  }

  // Amounts are shown in euros, so a price in another currency stays text:
  // "$ 54,000" must never turn into "€ 54".
  var FOREIGN = /[$£¥₹]|\b(usd|gbp|chf|jpy|sek|nok|dkk|pln|cad|aud|dollars?|pounds?|ponden?)\b/i;
  function currencyOf(v){
    var c = typeof v === 'string' ? v.trim().toUpperCase() : '';
    if(c === '€' || c === 'EURO') c = 'EUR';
    return /^[A-Z]{3}$/.test(c) ? c : '';
  }
  function foreignText(n, code, lang){
    try{ return new Intl.NumberFormat(lang === 'en' ? 'en-GB' : 'nl-NL', {style:'currency', currency:code}).format(n); }
    catch(_){ return code + ' ' + n; }
  }
  // A price: a number, "€ 49,-", "45 euro" or "€ 49 per maand" (the unit is split off).
  function readPrice(v, H, code){
    var foreign = code && code !== 'EUR';
    if(typeof v === 'number'){
      if(!Number.isFinite(v)) return {bad:true};
      return foreign ? {n:v, foreign:code} : {n:v};
    }
    if(typeof v !== 'string' || !v.trim()) return {bad:true};
    var t = v.trim().replace(/\s+/g, ' ');
    if(FOREIGN.test(t) || (foreign && !/€|\beur\b/i.test(t))) return {text:foreign && !FOREIGN.test(t) ? code + ' ' + t : t, foreign:true};
    var e = t.replace(/\beuro\b/ig, 'EUR');
    var p = H.parseNumber(e);
    if(Number.isFinite(p.n)) return {n:p.n};
    var m = /^(.*?\d(?:[\d.,]*\d)?(?:,-|\.-)?(?:\s*(?:€|eur(?![a-z])))?)\s*(\/.*|[a-zÀ-ɏ].*)$/i.exec(e);
    if(m){ var q = H.parseNumber(m[1]); if(Number.isFinite(q.n)) return {n:q.n, unit:m[2]}; }
    return {text:t};
  }
  // A score: 8, "8,5", "8/10", "4 van 5" or "85%". max is its own scale when it says one.
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
    var cutWarn = function(k){ warn(H.m.apply(null, arguments)); };
    var out = H.base(raw, 'compare', warnings);
    var list = first(raw, ['options', 'opties', 'items', 'choices', 'keuzes']);
    if(!Array.isArray(list) || !list.length){ errors.push(L.noOptions()); return {errors:errors, warnings:warnings}; }

    // Which option is recommended: by name, by position (1 is the first; 0 is
    // read as the first too), or flagged on the option.
    var recRaw = first(raw, ['recommended', 'aanrader', 'aanbevolen', 'recommendation']);
    var recName = typeof recRaw === 'string' ? norm(recRaw) : '';
    var recPos = -1, recWhich = false;
    var posOf = function(v){ var r = Math.round(v); if(r === 0) r = 1; return r >= 1 && r <= list.length ? r - 1 : -1; };
    if(typeof recRaw === 'number'){ recPos = posOf(recRaw); recWhich = true; }
    else if(recRaw !== undefined && typeof recRaw !== 'string') recWhich = true;

    var opts = [];
    list.forEach(function(o, i){
      if(typeof o === 'string' && o.trim()) o = {name:o};
      if(!H.isObj(o)){ warn(L.item(i + 1)); return; }
      var rawName = first(o, ['name', 'naam', 'title', 'label', 'option', 'optie']);
      var name = H.str(rawName, LIM.name, cutWarn, H.fieldName('De naam van optie ' + (i + 1), 'The name of option ' + (i + 1)));
      if(!name){ warn(L.name(i + 1)); return; }
      opts.push({o:o, i:i, name:name, full:norm(H.str(rawName))});
    });
    // "2" as text: a name first, a position when no option is called that.
    if(recName && /^\d+$/.test(recName) && !opts.some(function(x){ return x.full === recName; })){
      recPos = posOf(Number(recName)); recName = ''; recWhich = true;
    }

    var recIdx = -1, recNames = [];
    opts.forEach(function(x, k){
      var tag = norm(first(x.o, ['tag', 'badge']));
      var flagged = x.o.recommended === true || x.o.aanrader === true || x.o.aanbevolen === true;
      var hit = recName ? x.full === recName || norm(x.name) === recName : recPos >= 0 ? recPos === x.i : (flagged || REC_WORDS.test(tag));
      if(!hit) return;
      if(recNames.indexOf(x.full) < 0) recNames.push(x.full);
      if(recIdx < 0) recIdx = k;
    });
    if(recName && recIdx < 0) warn(L.rec(H.str(recRaw, LIM.name)));
    if(recWhich && recIdx < 0) warn(L.recWhich(H.str(typeof recRaw === 'object' ? JSON.stringify(recRaw) : recRaw, 24)));
    // Two options with the same name are one choice, not two recommendations.
    if(recNames.length > 1) warn(L.recMany(opts[recIdx].name));

    // More than four: keep the first ones, and the recommended one.
    if(opts.length > LIM.options){
      warn(L.many(opts.length, LIM.options));
      var keep = opts.slice(0, LIM.options);
      if(recIdx >= LIM.options){ keep = opts.slice(0, LIM.options - 1).concat([opts[recIdx]]); recIdx = LIM.options - 1; }
      opts = keep;
    }
    if(opts.length < 2){ errors.push(L.tooFew(opts.length)); return {errors:errors, warnings:warnings}; }

    // Duplicate names get a number, so the cards and the export stay apart.
    var seen = new Map();
    opts.forEach(function(x){
      var k = norm(x.name), c = (seen.get(k) || 0) + 1;
      seen.set(k, c);
      if(c > 1){ warn(L.dup(x.name)); x.name = x.name.slice(0, LIM.name - 4) + ' (' + c + ')'; }
    });

    var scoreMaxRaw = raw.scoreMax != null ? raw.scoreMax : raw.scoreScale;
    var scoreMax = null;
    if(scoreMaxRaw != null && scoreMaxRaw !== ''){
      var sm = Number(scoreMaxRaw);
      if(sm === 5 || sm === 10 || sm === 100) scoreMax = sm; else warn(L.scoreMax(H.str(scoreMaxRaw, 12)));
    }
    var blockCur = currencyOf(first(raw, ['currency', 'valuta']));

    var factKeys = [], factNorm = new Map(), factsCut = false;
    var options = opts.map(function(x){
      var o = x.o, name = x.name;
      var opt = {name:name, price:null, priceText:'', priceUnit:'', score:null, scoreMax:null, pros:[], cons:[], facts:{}, tag:''};
      var priceField = H.fieldName('De prijs van "' + name + '"', 'The price of "' + name + '"');
      var unitField = H.fieldName('De eenheid van de prijs van "' + name + '"', 'The price unit of "' + name + '"');
      var pv = first(o, ['price', 'prijs', 'cost', 'kosten', 'bedrag']);
      if(pv !== undefined && pv !== ''){
        var pr = readPrice(pv, H, currencyOf(first(o, ['currency', 'valuta'])) || blockCur);
        if(pr.foreign){
          warn(L.currency(name));
          var ft = pr.text || foreignText(pr.n, pr.foreign, lang);
          opt.priceText = H.str(ft, LIM.priceText, cutWarn, priceField);
        }
        else if(pr.text) opt.priceText = H.str(pr.text.charAt(0).toUpperCase() + pr.text.slice(1), LIM.priceText, cutWarn, priceField);
        else if(pr.bad || pr.n < 0) warn(L.price(name));
        else { opt.price = pr.n; if(pr.unit) opt.priceUnit = H.str(unitText(pr.unit), LIM.unit, cutWarn, unitField); }
      }
      var uv = first(o, ['priceUnit', 'unit', 'per', 'eenheid', 'prijsEenheid']);
      if(uv !== undefined && (opt.price !== null || opt.priceText)) opt.priceUnit = H.str(unitText(H.str(uv, 60)), LIM.unit, cutWarn, unitField) || opt.priceUnit;
      var sv = first(o, ['score', 'rating', 'cijfer', 'waardering']);
      if(sv !== undefined && sv !== ''){
        var sc = readScore(sv, H);
        // A plain number has its own scale too: up to 10 is out of 10, above that out of 100.
        if(sc && sc.n >= 0){ opt.score = sc.n; opt.scoreMax = sc.max || scoreMax || (sc.n <= 10 ? 10 : 100); }
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
        var key = H.str(p[0], LIM.factKey, cutWarn, H.fieldName('Een feit van "' + name + '"', 'A fact of "' + name + '"'));
        if(!key){ warn(L.facts(name)); return; }
        var v = p[1], val;
        if(typeof v === 'number' && Number.isFinite(v)) val = v;
        else if(typeof v === 'boolean') val = lang === 'en' ? (v ? 'Yes' : 'No') : (v ? 'Ja' : 'Nee');
        else if(typeof v === 'string' && v.trim()) val = H.str(v, LIM.factValue, cutWarn, H.fieldName('Het feit "' + key + '" van "' + name + '"', 'The fact "' + key + '" of "' + name + '"'));
        else { warn(L.fact(name, key)); return; }
        var nk = norm(key);
        if(!factNorm.has(nk)){
          if(factKeys.length >= LIM.facts){ factsCut = true; return; }
          factNorm.set(nk, key); factKeys.push(key);
        }
        put(opt.facts, factNorm.get(nk), val);
      });
      var tag = H.str(first(o, ['tag', 'badge']), LIM.tag, cutWarn, H.fieldName('Het label van "' + name + '"', 'The tag of "' + name + '"'));
      opt.tag = tag;
      return opt;
    });
    if(factsCut) warn(L.manyFacts(LIM.facts));

    // One scale for all scores: the block's scoreMax, or the largest scale of
    // the scores; every score is moved onto it ("8,5" next to "72%" is 85 of 100).
    var scale = scoreMax || Math.max.apply(null, [0].concat(options.map(function(o){ return o.scoreMax || 0; }))) || 10;
    options.forEach(function(o){
      if(o.score === null) return;
      var v = o.score > o.scoreMax ? NaN : o.score / o.scoreMax * scale;
      if(!(v >= 0 && v <= scale)){ warn(L.score(o.name, o.scoreMax)); o.score = null; }
      else o.score = Math.round(v * 10) / 10;
    });
    options.forEach(function(o){ delete o.scoreMax; });

    // A tag that only says "recommended" is the label's job (and only one card has it).
    options.forEach(function(o){ if(REC_WORDS.test(norm(o.tag))) o.tag = ''; });

    var criteria = [];
    var cr = first(raw, ['criteria', 'criteria_nl', 'vergelijkOp']);
    if(cr !== undefined){
      if(typeof cr === 'string') cr = cr.split(/\s*[,;]\s*/).filter(function(c){ return c.trim(); });
      if(!Array.isArray(cr)) warn(L.criteria());
      else {
        var badC = false, seenC = [];
        cr.forEach(function(c){
          var s = typeof c === 'string' ? H.str(c, LIM.criterion, cutWarn, H.fieldName('Een criterium', 'A criterion')) : '';
          if(!s){ if(c !== '' && c != null) badC = true; return; }
          if(seenC.indexOf(norm(s)) >= 0) return;
          seenC.push(norm(s)); criteria.push(s);
        });
        if(badC) warn(L.criteria());
        if(criteria.length > LIM.criteria){ warn(L.manyCriteria(LIM.criteria)); criteria = criteria.slice(0, LIM.criteria); }
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

  // The height the chat reserves before the frame reports its own: rows are
  // as tall as their tallest cell, so count the wrapped lines per card at a
  // typical chat width (about 720 px).
  function estHeight(spec){
    var n = spec.options.length, text = (720 - (n - 1) * 10) / n - 30;
    var lines = function(s, px){ return Math.max(1, Math.ceil(String(s).length * px / text)); };
    var most = function(fn){ return Math.max.apply(null, spec.options.map(fn)); };
    var h = spec.subtitle ? 26 : 0;
    if(spec.criteria.length) h += 12 + Math.ceil((spec.criteria.join(', ').length + 16) * 7 / 690) * 20;
    h += 4;
    if(spec.recommended >= 0 || spec.options.some(function(o){ return o.tag; })){
      h += 12 + most(function(o, i){ return Math.ceil(((i === spec.recommended ? 90 : 0) + (o.tag ? o.tag.length * 6.6 + 24 : 0)) / text) || 1; }) * 22;
    }
    h += 14 + most(function(o){ return lines(o.name, 9.4); }) * 21;
    if(spec.hasPrice) h += 12 + most(function(o){
      var amount = o.priceText ? lines(o.priceText, 8.6) * 21 : 26;
      return amount + (o.priceUnit && (o.priceText || String(o.price).length * 13 + o.priceUnit.length * 6.3 > text) ? lines(o.priceUnit, 6.3) * 16 : 0);
    });
    if(spec.hasScore) h += 45;
    spec.factKeys.forEach(function(k){
      h += 17 + most(function(o){ return lines(k, 6.3) * 17 + (own(o.facts, k) ? lines(o.facts[k], 7.6) : 1) * 19; });
    });
    ['pros', 'cons'].forEach(function(r){
      if(!spec.options.some(function(o){ return o[r].length; })) return;
      h += (r === 'cons' ? 12 : 8) + most(function(o){ return o[r].reduce(function(t, it){ return t + lines(it, 7.4) * 19 + 5; }, 0); });
    });
    return Math.round(h + (spec.source ? 30 : 0));
  }

  // The export keeps what the cards say: the recommended option, the price
  // unit next to the price and the scale in the score header.
  function table(spec){
    var en = spec.lang === 'en';
    var hasUnit = spec.options.some(function(o){ return !!o.priceUnit; });
    var hasRec = spec.recommended >= 0;
    var header = [en ? 'Option' : 'Optie'], types = ['text'];
    if(hasRec){ header.push(en ? 'Recommended' : 'Aanrader'); types.push('text'); }
    header.push(en ? 'Price' : 'Prijs'); types.push('currency');
    if(hasUnit){ header.push(en ? 'Unit' : 'Eenheid'); types.push('text'); }
    header.push(spec.hasScore ? (en ? 'Score (of ' : 'Score (van ') + spec.scoreMax + ')' : 'Score'); types.push('number');
    header.push(en ? 'Pros' : 'Pluspunten', en ? 'Cons' : 'Minpunten'); types.push('text', 'text');
    var rows = spec.options.map(function(o, i){
      var row = [o.name];
      if(hasRec) row.push(i === spec.recommended ? (en ? 'Yes' : 'Ja') : null);
      row.push(o.price !== null ? o.price : (o.priceText || null));
      if(hasUnit) row.push(o.priceUnit || null);
      row.push(o.score, o.pros.join('; '), o.cons.join('; '));
      return row.concat(spec.factKeys.map(function(k){ return own(o.facts, k) ? o.facts[k] : null; }));
    });
    return {header:header.concat(spec.factKeys), rows:rows, types:types.concat(spec.factKeys.map(function(k){
      return spec.options.every(function(o){ return !own(o.facts, k) || typeof o.facts[k] === 'number'; }) ? 'number' : 'text';
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

  var uid = 0;
  // Side by side only while every card keeps about 165 px; narrower, the cards swipe.
  function needsSwipe(width, n){ return width < Math.max(560, n * 165 + (n - 1) * 10); }

  root.SWKitRender.register('compare', function(box, spec, restore, ctx){
    var h = ctx.h, T = TEXT[ctx.lang() === 'en' ? 'en' : 'nl'];
    var n = spec.options.length, rows = rowsOf(spec), id = 'kcmp' + (++uid);
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
      card.tabIndex = -1;
      card.style.gridRow = 'span ' + rows.length;
      // The name and the position label the card; the price, score and facts
      // describe it, so a screen reader still reads them on focus.
      var pos = h('span', 'k-sr', ', ' + T.option(i + 1, n));
      pos.id = id + '-' + i + '-pos';
      var described = [];
      rows.forEach(function(r){
        var cell;
        if(r === 'top'){
          cell = h('div', 'k-cmp-top');
          if(rec) cell.appendChild(h('span', 'k-cmp-badge is-rec', T.rec));
          if(o.tag) cell.appendChild(h('span', 'k-cmp-badge', o.tag));
        } else if(r === 'name'){
          cell = h('div', 'k-cmp-name', o.name);
          cell.appendChild(pos);
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
          var key = spec.factKeys[Number(r.slice(4))], has = own(o.facts, key), fv = has ? o.facts[key] : undefined;
          cell = h('div', 'k-cmp-fact');
          cell.appendChild(h('span', 'k-cmp-label', key));
          cell.appendChild(h('span', 'k-cmp-value' + (has ? '' : ' k-cmp-missing'), has ? (typeof fv === 'number' ? ctx.fmt(fv, 'number') : String(fv)) : T.unknown));
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
        if(r === 'name') cell.id = id + '-' + i + '-name';
        else if(r !== 'pros' && r !== 'cons' && cell.textContent){ cell.id = id + '-' + i + '-' + r; described.push(cell.id); }
        card.appendChild(cell);
      });
      card.setAttribute('aria-labelledby', id + '-' + i + '-name');
      if(described.length) card.setAttribute('aria-describedby', described.join(' '));
      grid.appendChild(card);
      return card;
    });
    box.appendChild(grid);

    // When the cards swipe, the dots show where you are and jump there.
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

    var swipe = false;
    function layout(){
      var w = box.clientWidth || grid.clientWidth;
      var next = !!w && needsSwipe(w, n);
      if(next === swipe) return false;
      swipe = next;
      grid.classList.toggle('is-swipe', swipe);
      dots.hidden = !swipe;
      return true;
    }
    dots.hidden = true;
    layout();

    // One tab stop for the cards: the active one. The arrow keys move it.
    var active = -1;
    function setActive(i){
      if(i === active) return;
      active = i;
      cards.forEach(function(c, k){ c.tabIndex = k === i ? 0 : -1; });
      dotBtns.forEach(function(b, k){ b.setAttribute('aria-current', k === i ? 'true' : 'false'); });
    }
    function scrollToCard(i, smooth){
      if(!swipe) return;
      var pad = parseFloat(getComputedStyle(grid).paddingLeft) || 0;
      var left = cards[i].offsetLeft - grid.offsetLeft - pad;
      if(smooth && grid.scrollTo) grid.scrollTo({left:left, behavior:REDUCED ? 'auto' : 'smooth'});
      else grid.scrollLeft = left;
    }
    function go(i, focus){
      i = Math.max(0, Math.min(n - 1, i));
      scrollToCard(i, true);
      if(focus) cards[i].focus({preventScroll:true});
      setActive(i);
      ctx.save({i:i});
    }
    var scrollTimer = 0;
    grid.addEventListener('scroll', function(){
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function(){
        var best = 0, dist = Infinity, left = grid.scrollLeft;
        cards.forEach(function(c, k){ var d = Math.abs(c.offsetLeft - grid.offsetLeft - left); if(d < dist){ dist = d; best = k; } });
        if(best !== active){ setActive(best); ctx.save({i:best}); }
      }, 90);
    }, {passive:true});
    cards.forEach(function(card, i){
      card.addEventListener('keydown', function(e){
        if(e.target !== card) return;
        var to = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -2;
        if(to === -2) return;
        e.preventDefault();
        go(to, true);
      });
      card.addEventListener('focus', function(){ setActive(i); });
    });
    var start = restore && typeof restore.i === 'number' && restore.i >= 0 && restore.i < n ? Math.round(restore.i) : 0;
    setActive(start);
    if(start > 0) requestAnimationFrame(function(){ scrollToCard(start, false); });
    if(typeof ResizeObserver === 'function'){
      var ro = new ResizeObserver(function(){
        if(!box.isConnected){ ro.disconnect(); return; }
        if(layout()){ scrollToCard(active, false); ctx.resize(); }
      });
      ro.observe(box);
    }
    ctx.resize();
    return {onTheme:function(){}};
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
