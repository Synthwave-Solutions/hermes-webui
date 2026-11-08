// Data block "flow": a process diagram (onboarding, approval, sales,
// escalation) drawn from JSON with a simple layered layout.
//
// Shape: {"title", "direction":"down|right", "nodes":[{"id", "label",
// "type":"start|step|decision|end|wait", "owner"?, "note"?}],
// "edges":[{"from", "to", "label"?}]}. "steps" and "links" work too, and a
// link may be a string ("A -> B -> C", "A -> B: Ja"); without edges the
// steps are linked in order. Cycles are allowed: a step that goes
// back is drawn around the side.
//
// Loaded twice: in the chat (checks only, SWKit) and in the kit frame (SWKit
// plus SWKitRender). The frame builds every element with textContent or as a
// DOM or SVG property; nothing from the spec becomes markup.
(function(root){
  'use strict';
  var K = root.SWKit;
  if(!K) return;

  var LIM = {nodes:30, edges:50, label:60, owner:40, note:160, edgeLabel:24, id:40, owners:6};
  var TYPES = {start:'start', begin:'start', beginpunt:'start', trigger:'start', aanleiding:'start',
    step:'step', stap:'step', task:'step', taak:'step', action:'step', actie:'step', process:'step', proces:'step', activity:'step', activiteit:'step',
    decision:'decision', beslissing:'decision', besluit:'decision', keuze:'decision', choice:'decision', question:'decision', vraag:'decision', condition:'decision', check:'decision', controle:'decision', 'if':'decision',
    end:'end', einde:'end', eind:'end', stop:'end', finish:'end', klaar:'end', done:'end', afgerond:'end', result:'end', resultaat:'end',
    wait:'wait', wachten:'wait', wacht:'wait', waiting:'wait', delay:'wait', pauze:'wait', pause:'wait', timer:'wait'};
  var DIRS = {down:'down', vertical:'down', verticaal:'down', td:'down', tb:'down', omlaag:'down', onder:'down', top:'down',
    right:'right', horizontal:'right', horizontaal:'right', lr:'right', rechts:'right', left:'right'};
  var YES = /^(ja|yes|ok|oké|okay|akkoord|goed|goedgekeurd|approved|accepted|klopt|wel|true|y)(?![a-z])/;
  var NO = /^(nee|no|niet|geen|afgekeurd|afgewezen|rejected|declined|false|n)(?![a-z])/;
  var own = function(o, k){ return Object.prototype.hasOwnProperty.call(o, k); };
  var TYPE_WORDS = {nl:{start:'Start', step:'Stap', decision:'Keuze', end:'Einde', wait:'Wachten'},
    en:{start:'Start', step:'Step', decision:'Decision', end:'End', wait:'Wait'}};

  var MSG = {
    nl:{
      noNodes:function(){ return 'Er zijn geen stappen (nodes).'; },
      none:function(){ return 'Geen enkele stap heeft een naam (label).'; },
      many:function(n, max){ return 'Er zijn ' + n + ' stappen; alleen de eerste ' + max + ' worden getoond.'; },
      manyEdges:function(n, max){ return 'Er zijn ' + n + ' verbindingen; alleen de eerste ' + max + ' worden getoond.'; },
      node:function(i){ return 'Stap ' + i + ' is geen object met een label en is weggelaten.'; },
      noLabel:function(i, id){ return id ? 'Stap ' + i + ' heeft geen label; de id "' + id + '" is als naam gebruikt.' : 'Stap ' + i + ' heeft geen label en is weggelaten.'; },
      dupId:function(id, l, nid){ return 'De id "' + id + '" komt vaker voor; "' + l + '" heet nu "' + nid + '". Verbindingen met "' + id + '" gaan naar de eerste stap.'; },
      type:function(l, t){ return '"' + l + '" heeft een onbekend type "' + t + '"; gebruik start, step, decision, end of wait. Nu geldt step.'; },
      dir:function(d){ return 'Onbekende richting (direction) "' + d + '"; gebruik down of right. Nu geldt down.'; },
      edge:function(i){ return 'Verbinding ' + i + ' heeft geen from en to en is weggelaten.'; },
      edgeRef:function(i, ref){ return 'Verbinding ' + i + ' verwijst naar een onbekende stap "' + ref + '" en is weggelaten.'; },
      edgeDup:function(a, b){ return 'De verbinding van "' + a + '" naar "' + b + '" staat er vaker in; één is weggelaten.'; },
      noEdges:function(){ return 'Geen enkele verbinding klopte; de stappen zijn op volgorde verbonden.'; },
      moreRefs:function(n){ return 'Nog ' + n + (n === 1 ? ' verbinding verwijst' : ' verbindingen verwijzen') + ' naar een onbekende stap en ' + (n === 1 ? 'is' : 'zijn') + ' weggelaten.'; },
      cutEdges:function(n){ return n === 1 ? '1 verbinding naar een stap die niet wordt getoond, is weggelaten.' : n + ' verbindingen naar stappen die niet worden getoond, zijn weggelaten.'; },
      alone:function(l){ return '"' + l + '" is met geen enkele andere stap verbonden.'; },
      cutLabel:function(i){ return 'Het label van stap ' + i; },
      cutOwner:function(l){ return 'De eigenaar van "' + l + '"'; },
      cutNote:function(l){ return 'De notitie van "' + l + '"'; },
      cutEdge:function(i){ return 'Het label van verbinding ' + i; },
      moreCuts:function(n){ return 'Nog ' + n + (n === 1 ? ' label van een verbinding is' : ' labels van verbindingen zijn') + ' ingekort.'; }
    },
    en:{
      noNodes:function(){ return 'There are no steps (nodes).'; },
      none:function(){ return 'No step has a name (label).'; },
      many:function(n, max){ return 'There are ' + n + ' steps; only the first ' + max + ' are shown.'; },
      manyEdges:function(n, max){ return 'There are ' + n + ' links; only the first ' + max + ' are shown.'; },
      node:function(i){ return 'Step ' + i + ' is not an object with a label and was left out.'; },
      noLabel:function(i, id){ return id ? 'Step ' + i + ' has no label; its id "' + id + '" is used as its name.' : 'Step ' + i + ' has no label and was left out.'; },
      dupId:function(id, l, nid){ return 'The id "' + id + '" is used more than once; "' + l + '" is now "' + nid + '". Links with "' + id + '" go to the first step.'; },
      type:function(l, t){ return '"' + l + '" has an unknown type "' + t + '"; use start, step, decision, end or wait. Step is used now.'; },
      dir:function(d){ return 'Unknown direction "' + d + '"; use down or right. Down is used now.'; },
      edge:function(i){ return 'Link ' + i + ' has no from and to and was left out.'; },
      edgeRef:function(i, ref){ return 'Link ' + i + ' points to an unknown step "' + ref + '" and was left out.'; },
      edgeDup:function(a, b){ return 'The link from "' + a + '" to "' + b + '" appears more than once; one was left out.'; },
      noEdges:function(){ return 'No link was valid; the steps are linked in order.'; },
      moreRefs:function(n){ return n + ' more ' + (n === 1 ? 'link points' : 'links point') + ' to an unknown step and ' + (n === 1 ? 'was' : 'were') + ' left out.'; },
      cutEdges:function(n){ return n === 1 ? '1 link to a step that is not shown was left out.' : n + ' links to steps that are not shown were left out.'; },
      alone:function(l){ return '"' + l + '" is not linked to any other step.'; },
      cutLabel:function(i){ return 'The label of step ' + i; },
      cutOwner:function(l){ return 'The owner of "' + l + '"'; },
      cutNote:function(l){ return 'The note of "' + l + '"'; },
      cutEdge:function(i){ return 'The label of link ' + i; },
      moreCuts:function(n){ return n + ' more link ' + (n === 1 ? 'label was' : 'labels were') + ' shortened.'; }
    }
  };

  // "A -> B", "A --> B -> C", "A -->|Ja| B", "A -> B: Ja", "A -> B (Ja)" and,
  // without a real arrow, "A > B". A ">" inside a label ("Bedrag > 5000?")
  // only splits when nothing better is there. Returns readings in order of
  // preference: [[{ref, label, alt:[{ref, label}]}...]...]; validate picks the
  // first in which every step exists.
  function splits(s){
    s = String(s).trim();
    var out = [];
    function reading(parts){
      if(parts.length < 2 || parts.some(function(x){ return !x.trim(); })) return;
      out.push(parts.map(function(x, k){
        var q = {ref:x.trim(), label:''}, m;
        if(k && (m = /^\|([^|]*)\|\s*([\s\S]+)$/.exec(q.ref))){ q.label = m[1].trim(); q.ref = m[2].trim(); }
        if(k && (m = /^(.+?)\s*:\s*([^:]+)$/.exec(q.ref))) (q.alt = q.alt || []).push({ref:m[1], label:m[2].trim()});
        if(k && (m = /^(.+?)\s*\(([^()]+)\)$/.exec(q.ref))) (q.alt = q.alt || []).push({ref:m[1], label:m[2].trim()});
        return q;
      }));
    }
    var strong = s.split(/\s*(?:-+>|=+>|→)\s*/);
    if(strong.length > 1){
      reading(strong);
      if(strong.length > 2) reading([strong.slice(0, -1).join(' -> '), strong[strong.length - 1]]);
      return out;
    }
    var spaced = s.split(/\s+>\s+/);
    if(spaced.length > 1){
      reading([spaced.slice(0, -1).join(' > '), spaced[spaced.length - 1]]);
      if(spaced.length > 2){ reading(spaced); reading([spaced[0], spaced.slice(1).join(' > ')]); }
      return out;
    }
    var bare = s.split('>');
    if(bare.length === 2) reading(bare);
    return out;
  }

  // ── Checks ──────────────────────────────────────────────────────────────
  function validate(raw, lang, H){
    var L = H.pickLang(lang), M = MSG[L], warnings = [], errors = [];
    var warn = function(s){ warnings.push(s); };
    var cutWarn = function(k){ var a = Array.prototype.slice.call(arguments, 1); warnings.push(H.m.apply(null, [k].concat(a))); };
    var out = H.base(raw, 'flow', warnings);
    var direction = 'down';
    if(raw.direction != null && raw.direction !== ''){
      var dk = String(raw.direction).trim().toLowerCase();
      if(own(DIRS, dk)) direction = DIRS[dk]; else warn(M.dir(H.str(raw.direction, 20)));
    }
    var list = Array.isArray(raw.nodes) ? raw.nodes : Array.isArray(raw.steps) ? raw.steps : null;
    if(!list || !list.length){ errors.push(M.noNodes()); return {errors:errors, warnings:warnings}; }
    var cutRefs = Object.create(null);
    if(list.length > LIM.nodes){
      warn(M.many(list.length, LIM.nodes));
      list.slice(LIM.nodes).forEach(function(it){
        if(typeof it === 'string') cutRefs[it.trim().toLowerCase()] = true;
        else if(H.isObj(it)) [it.id, it.key, it.label, it.title, it.name].forEach(function(x){ if(x != null && x !== '') cutRefs[String(x).trim().toLowerCase()] = true; });
      });
      list = list.slice(0, LIM.nodes);
    }
    var nodes = [], byId = {}, byLower = {}, byLabel = {}, anyId = false, nexts = [];
    // Ids given anywhere in the list, so a made-up id never takes one of them.
    var taken = Object.create(null);
    list.forEach(function(it){ if(H.isObj(it)){ var x = H.str(it.id != null ? it.id : it.key, LIM.id); if(x) taken[x] = true; } });
    list.forEach(function(it, i){
      if(typeof it === 'string') it = {label:it};
      if(!H.isObj(it)){ warn(M.node(i + 1)); return; }
      var id = H.str(it.id != null ? it.id : it.key, LIM.id);
      var label = H.str(it.label != null ? it.label : it.title != null ? it.title : it.name != null ? it.name : it.text, LIM.label, cutWarn, M.cutLabel(i + 1));
      if(!label){
        if(id){ warn(M.noLabel(i + 1, id)); label = id.slice(0, LIM.label); }
        else { warn(M.noLabel(i + 1, '')); return; }
      }
      if(id) anyId = true;
      if(id && own(byId, id)){
        // The second one gets an id of its own; links with the old id keep going to the first.
        var nid, q2 = 2;
        do { nid = id.slice(0, LIM.id - 3) + '-' + q2++; } while(own(byId, nid) || taken[nid]);
        warn(M.dupId(id, label, nid)); id = nid;
      }
      var type = 'step';
      if(it.type != null && it.type !== '' || it.shape != null && it.shape !== ''){
        var t = String(it.type != null && it.type !== '' ? it.type : it.shape).trim().toLowerCase();
        if(own(TYPES, t)) type = TYPES[t]; else warn(M.type(label, H.str(t, 20)));
      }
      var k = nodes.length;
      var node = {k:k, label:label, type:type,
        owner:H.str(it.owner != null ? it.owner : it.role != null ? it.role : it.who, LIM.owner, cutWarn, M.cutOwner(label)),
        note:H.str(it.note != null ? it.note : it.description, LIM.note, cutWarn, M.cutNote(label)), o:-1};
      if(id){ byId[id] = k; var lo = id.toLowerCase(); if(!Object.prototype.hasOwnProperty.call(byLower, lo)) byLower[lo] = k; }
      var ll = label.toLowerCase();
      if(!Object.prototype.hasOwnProperty.call(byLabel, ll)) byLabel[ll] = k;
      nodes.push(node);
      if(it.next != null) nexts.push([k, it.next]);
    });
    if(!nodes.length){ errors.push(M.none()); return {errors:errors, warnings:warnings}; }
    // Owners get a colour of their own (only when there are several).
    var owners = [];
    nodes.forEach(function(n){ if(n.owner && owners.indexOf(n.owner) < 0) owners.push(n.owner); });
    if(owners.length > 1) nodes.forEach(function(n){ var i = owners.indexOf(n.owner); n.o = i >= 0 && i < LIM.owners ? i : -1; });

    // A reference is an id, a label or (when no step has an id) a step number.
    var zeroBased = false;
    function resolve(ref){
      if(ref == null || ref === '') return -1;
      var s = String(ref).trim();
      if(Object.prototype.hasOwnProperty.call(byId, s)) return byId[s];
      var lo = s.toLowerCase();
      if(Object.prototype.hasOwnProperty.call(byLower, lo)) return byLower[lo];
      if(Object.prototype.hasOwnProperty.call(byLabel, lo)) return byLabel[lo];
      if(!anyId && /^\d+$/.test(s)){ var n = +s - (zeroBased ? 0 : 1); if(n >= 0 && n < nodes.length) return n; }
      return -1;
    }
    var rawEdges = Array.isArray(raw.edges) ? raw.edges : Array.isArray(raw.links) ? raw.links : Array.isArray(raw.connections) ? raw.connections : [];
    rawEdges = rawEdges.map(function(e){
      if(Array.isArray(e)) return {from:e[0], to:e[1], label:e[2]};
      if(typeof e === 'string'){ var sp = splits(e); return sp.length ? {splits:sp} : e; }
      return e;
    });
    nexts.forEach(function(p){
      (Array.isArray(p[1]) ? p[1] : [p[1]]).forEach(function(x){
        if(H.isObj(x)) rawEdges.push({from:p[0], fromIndex:true, to:x.to != null ? x.to : x.id, label:x.label});
        else rawEdges.push({from:p[0], fromIndex:true, to:x});
      });
    });
    if(!anyId) zeroBased = rawEdges.some(function(e){
      if(!H.isObj(e) || e.fromIndex) return false;
      if(e.splits) return e.splits[0].some(function(q){ return q.ref === '0'; });
      return e.from === 0 || e.to === 0 || e.from === '0' || e.to === '0';
    });
    var given = rawEdges.length;
    if(rawEdges.length > LIM.edges){ warn(M.manyEdges(rawEdges.length, LIM.edges)); rawEdges = rawEdges.slice(0, LIM.edges); }
    var edges = [], seen = {}, unknown = 0, toCut = 0, labelCuts = 0;
    var edgeCut = function(k, field, max){ if(++labelCuts <= 3) cutWarn(k, field, max); };
    function bad(i, ref){
      if(cutRefs[String(ref).trim().toLowerCase()]) toCut++;
      else if(++unknown <= 5) warn(M.edgeRef(i + 1, H.str(ref, 40)));
    }
    function add(i, f, t, label){
      if(edges.length >= LIM.edges) return;
      var key = f + '>' + t;
      if(seen[key]){ warn(M.edgeDup(nodes[f].label, nodes[t].label)); return; }
      seen[key] = true;
      edges.push({f:f, t:t, label:H.str(label, LIM.edgeLabel, edgeCut, M.cutEdge(i + 1))});
    }
    rawEdges.forEach(function(e, i){
      if(!H.isObj(e)){ warn(M.edge(i + 1)); return; }
      if(e.splits){
        // The first reading in which every step exists wins; otherwise the first.
        var pick = null;
        e.splits.some(function(sp){
          var got = sp.map(function(q){
            var k = resolve(q.ref);
            if(k < 0 && q.alt) for(var a = 0; a < q.alt.length && k < 0; a++){ k = resolve(q.alt[a].ref); if(k >= 0) return {k:k, label:q.alt[a].label || q.label}; }
            return {k:k, label:q.label};
          });
          if(got.every(function(g){ return g.k >= 0; })){ pick = got; return true; }
          return false;
        });
        if(!pick){ var miss = e.splits[0].filter(function(q){ return resolve(q.ref) < 0; })[0]; bad(i, miss ? miss.ref : ''); return; }
        for(var c = 0; c + 1 < pick.length; c++) add(i, pick[c].k, pick[c + 1].k, pick[c + 1].label);
        return;
      }
      var fr = e.from != null ? e.from : e.source != null ? e.source : e.van;
      var to = e.to != null ? e.to : e.target != null ? e.target : e.naar;
      if(fr == null || fr === '' || to == null || to === ''){ warn(M.edge(i + 1)); return; }
      var f = e.fromIndex ? fr : resolve(fr), t = resolve(to);
      if(f < 0 || t < 0){ bad(i, f < 0 ? fr : to); return; }
      add(i, f, t, e.label != null ? e.label : e.text != null ? e.text : e.condition);
    });
    if(labelCuts > 3) warn(M.moreCuts(labelCuts - 3));
    if(unknown > 5) warn(M.moreRefs(unknown - 5));
    if(toCut) warn(M.cutEdges(toCut));
    if(!edges.length && nodes.length > 1){
      if(given) warn(M.noEdges());
      for(var i = 0; i + 1 < nodes.length; i++) edges.push({f:i, t:i + 1, label:''});
    }
    if(nodes.length > 1){
      var linked = nodes.map(function(){ return false; });
      edges.forEach(function(e){ if(e.f !== e.t){ linked[e.f] = true; linked[e.t] = true; } });
      nodes.forEach(function(n, j){ if(!linked[j]) warn(M.alone(n.label)); });
    }
    return {errors:errors, warnings:warnings, spec:Object.assign(out, {direction:direction, nodes:nodes, edges:edges})};
  }

  // ── Layers: break cycles, then longest path ─────────────────────────────
  // Returns {layer:[...], back:[bool per edge], order:[dfs index per node]}.
  function rank(spec){
    var n = spec.nodes.length, out = [], i;
    for(i = 0; i < n; i++) out.push([]);
    spec.edges.forEach(function(e, j){ if(e.f !== e.t) out[e.f].push(j); });
    var state = [], order = [], back = spec.edges.map(function(e){ return e.f === e.t; }), seq = 0;
    for(i = 0; i < n; i++){ state.push(0); order.push(0); }
    var indeg = spec.nodes.map(function(){ return 0; });
    spec.edges.forEach(function(e){ if(e.f !== e.t) indeg[e.t]++; });
    function visit(v){
      state[v] = 1; order[v] = seq++;
      out[v].forEach(function(j){
        var t = spec.edges[j].t;
        if(state[t] === 1) back[j] = true;
        else if(state[t] === 0) visit(t);
      });
      state[v] = 2;
    }
    var roots = [];
    for(i = 0; i < n; i++) if(spec.nodes[i].type === 'start') roots.push(i);
    for(i = 0; i < n; i++) if(indeg[i] === 0 && roots.indexOf(i) < 0) roots.push(i);
    for(i = 0; i < n; i++) roots.push(i);
    roots.forEach(function(v){ if(state[v] === 0) visit(v); });
    // Longest path over the forward edges, in topological order.
    var preds = [], succs = [], deg = [], layer = [];
    for(i = 0; i < n; i++){ preds.push([]); succs.push([]); deg.push(0); layer.push(0); }
    spec.edges.forEach(function(e, j){ if(!back[j]){ preds[e.t].push(e.f); succs[e.f].push(e.t); deg[e.t]++; } });
    var queue = [], topo = [];
    for(i = 0; i < n; i++) if(!deg[i]) queue.push(i);
    queue.sort(function(a, b){ return order[a] - order[b]; });
    while(queue.length){
      var v = queue.shift(); topo.push(v);
      succs[v].forEach(function(t){ layer[t] = Math.max(layer[t], layer[v] + 1); if(--deg[t] === 0) queue.push(t); });
    }
    // A later entry point (not a start) sits just above the step it leads to.
    topo.slice().reverse().forEach(function(v){
      if(!preds[v].length && succs[v].length && spec.nodes[v].type !== 'start'){
        var m = Math.min.apply(null, succs[v].map(function(t){ return layer[t]; }));
        if(m - 1 > layer[v]) layer[v] = m - 1;
      }
    });
    return {layer:layer, back:back, order:order};
  }

  // ── Layout ──────────────────────────────────────────────────────────────
  // layout(spec, {dir, sizes:[{w,h}], labelW:[per edge], gapMain, gapCross})
  // -> {w, h, nodes:[{x,y,w,h}], edges:[{pts:[[x,y]...], end:[dx,dy], label:{x,y,w,h}|null, back}]}
  // Everything is computed on a "main" axis (the flow) and a "cross" axis and
  // mapped to x and y at the end, so down and right share one algorithm.
  function layout(spec, opt){
    var dir = opt.dir === 'right' ? 'right' : 'down';
    var gapMain = opt.gapMain || 44, gapCross = opt.gapCross || 28, DUMMY = 8, LANE = opt.lane || 18, LANE_STEP = opt.laneStep || 12, LH = 16;
    // Upright lane labels (phones): turned along the lane, so they add no width.
    var upright = !!opt.uprightLanes && dir === 'down';
    var r = rank(spec), n = spec.nodes.length;
    var cs = [], ms = [], layerOf = [], isReal = [], dfs = [];
    spec.nodes.forEach(function(nd, i){
      var s = opt.sizes[i] || {w:160, h:44};
      cs.push(dir === 'down' ? s.w : s.h); ms.push(dir === 'down' ? s.h : s.w);
      layerOf.push(r.layer[i]); isReal.push(true); dfs.push(r.order[i]);
    });
    // Long forward edges get one pass-through point per layer they cross.
    var chains = spec.edges.map(function(e, j){
      if(r.back[j]) return null;
      var c = [e.f];
      for(var l = layerOf[e.f] + 1; l < layerOf[e.t]; l++){
        var d = cs.length;
        cs.push(DUMMY); ms.push(0); layerOf.push(l); isReal.push(false); dfs.push(dfs[e.f] + 0.5 + j / 1000);
        c.push(d);
      }
      c.push(e.t);
      return c;
    });
    var total = cs.length, nl = 0, i;
    for(i = 0; i < total; i++) nl = Math.max(nl, layerOf[i] + 1);
    var up = [], down = [];
    for(i = 0; i < total; i++){ up.push([]); down.push([]); }
    chains.forEach(function(c){ if(c) for(var q = 0; q + 1 < c.length; q++){ down[c[q]].push(c[q + 1]); up[c[q + 1]].push(c[q]); } });
    var layers = [];
    for(i = 0; i < nl; i++) layers.push([]);
    for(i = 0; i < total; i++) layers[layerOf[i]].push(i);
    layers.forEach(function(L){ L.sort(function(a, b){ return dfs[a] - dfs[b]; }); });

    // Order within a layer: barycenter sweeps, keep the fewest crossings.
    var pos = [];
    function index(){ layers.forEach(function(L){ L.forEach(function(v, k){ pos[v] = k; }); }); }
    function crossings(){
      var c = 0;
      for(var l = 0; l + 1 < nl; l++){
        var segs = [];
        layers[l].forEach(function(v){ down[v].forEach(function(t){ segs.push([pos[v], pos[t]]); }); });
        for(var a = 0; a < segs.length; a++) for(var b = a + 1; b < segs.length; b++)
          if((segs[a][0] - segs[b][0]) * (segs[a][1] - segs[b][1]) < 0) c++;
      }
      return c;
    }
    index();
    var best = layers.map(function(L){ return L.slice(); }), bestC = crossings();
    for(var it = 0; it < 8 && bestC > 0; it++){
      var downPass = it % 2 === 0;
      for(var s = 0; s < nl; s++){
        var l = downPass ? s : nl - 1 - s, ref = downPass ? up : down;
        var bc = {};
        layers[l].forEach(function(v){
          var nb = ref[v];
          bc[v] = nb.length ? nb.reduce(function(a, u){ return a + pos[u]; }, 0) / nb.length : pos[v];
        });
        layers[l].sort(function(a, b){ return (bc[a] - bc[b]) || (pos[a] - pos[b]); });
        layers[l].forEach(function(v, k){ pos[v] = k; });
      }
      var c = crossings();
      if(c < bestC){ bestC = c; best = layers.map(function(L){ return L.slice(); }); }
    }
    layers = best; index();

    // The main path runs straight: each step lines up with one child (the
    // "yes" branch, not an end, else the first link) and that child with it.
    var alignUp = [], alignDown = [];
    function score(j){
      var e = spec.edges[j], lab = String(e.label || '').trim().toLowerCase(), s = -j / 1000;
      if(YES.test(lab)) s += 2; else if(NO.test(lab)) s -= 2;
      if(spec.nodes[e.t].type === 'end') s -= 1;
      return s;
    }
    [true, false].forEach(function(real){ layers.forEach(function(L){
      // Steps already on the main path claim their child first.
      L.slice().sort(function(a, b){ return (alignUp[a] == null) - (alignUp[b] == null); }).forEach(function(v){
        if(isReal[v] !== real) return;
        var nx = -1;
        if(isReal[v]){
          var bestS = -Infinity;
          chains.forEach(function(c, j){ if(c && c[0] === v){ var sc = score(j); if(sc > bestS){ bestS = sc; nx = c[1]; } } });
        } else nx = down[v][0];
        if(nx >= 0 && alignUp[nx] == null){ alignUp[nx] = v; alignDown[v] = nx; }
      });
    }); });
    // Cross positions: pull each element toward its neighbours, keep order
    // and spacing (weighted isotonic regression with minimum gaps).
    var cc = [];
    layers.forEach(function(L){
      var x = 0;
      L.forEach(function(v, k){ if(k) x += (cs[L[k - 1]] + cs[v]) / 2 + gap(L[k - 1], v); cc[v] = x; });
      var mid = x / 2;
      L.forEach(function(v){ cc[v] -= mid; });
    });
    function gap(a, b){ return isReal[a] && isReal[b] ? gapCross : isReal[a] || isReal[b] ? gapCross * 0.6 : 6; }
    function place(L, want, wt){
      var off = [0], k;
      for(k = 1; k < L.length; k++) off.push(off[k - 1] + (cs[L[k - 1]] + cs[L[k]]) / 2 + gap(L[k - 1], L[k]));
      var blocks = [];
      for(k = 0; k < L.length; k++){
        blocks.push({sum:wt[k] * (want[k] - off[k]), cnt:wt[k], from:k, to:k});
        while(blocks.length > 1){
          var b = blocks[blocks.length - 1], a = blocks[blocks.length - 2];
          if(a.sum / a.cnt <= b.sum / b.cnt) break;
          a.sum += b.sum; a.cnt += b.cnt; a.to = b.to; blocks.pop();
        }
      }
      blocks.forEach(function(b){ for(var q = b.from; q <= b.to; q++) cc[L[q]] = b.sum / b.cnt + off[q]; });
    }
    function sweep(fromUp, fromDown){
      for(var s2 = 0; s2 < nl; s2++){
        var L = layers[fromDown && !fromUp ? nl - 1 - s2 : s2], want = [], wt = [];
        L.forEach(function(v){
          var sum = 0, w = 0;
          function add(u, ww){ sum += cc[u] * ww; w += ww; }
          if(fromUp){ if(alignUp[v] != null) add(alignUp[v], 8); up[v].forEach(function(u){ if(u !== alignUp[v]) add(u, 1); }); }
          if(fromDown){ if(alignDown[v] != null) add(alignDown[v], 8); down[v].forEach(function(u){ if(u !== alignDown[v]) add(u, 1); }); }
          if(!w){ sum = cc[v] * 0.5; w = 0.5; }
          want.push(sum / w); wt.push(w);
        });
        place(L, want, wt);
      }
    }
    for(var p = 0; p < 4; p++){ sweep(true, false); sweep(false, true); }
    sweep(true, true); sweep(true, false);
    // Finally put every aligned child exactly under its parent where it fits.
    layers.forEach(function(L){
      place(L, L.map(function(v){ return alignUp[v] != null ? cc[alignUp[v]] : cc[v]; }), L.map(function(v){ return alignUp[v] == null ? 1 : isReal[v] && isReal[alignUp[v]] ? 1000 : 30; }));
    });

    // Main positions per layer.
    var ls = [], lt = [], at = 0;
    for(i = 0; i < nl; i++){
      var th = 0;
      layers[i].forEach(function(v){ th = Math.max(th, ms[v]); });
      ls.push(at); lt.push(th); at += th + gapMain;
    }
    function mStart(v){ return isReal[v] ? ls[layerOf[v]] + (lt[layerOf[v]] - ms[v]) / 2 : ls[layerOf[v]]; }
    function mEnd(v){ return isReal[v] ? mStart(v) + ms[v] : ls[layerOf[v]] + lt[layerOf[v]]; }
    function mMid(v){ return (mStart(v) + mEnd(v)) / 2; }
    function gapAfter(l){ return ls[l] + lt[l] + gapMain / 2; }
    // Is anything between v and the outside on this side, in v's layer?
    function clear(v, side){ return layers[layerOf[v]].every(function(u){ return u === v || !isReal[u] || (cc[u] - cc[v]) * side < 0; }); }
    var isDecision = function(v){ return v < n && spec.nodes[v].type === 'decision'; };
    // The diamond's border at a main offset from its middle.
    function sideAt(v, dm){ return isDecision(v) ? cs[v] / 2 * Math.max(0, 1 - Math.abs(dm) / (ms[v] / 2)) : cs[v] / 2; }

    // Decision ports: the two outer branches leave from the diamond's points.
    var port = spec.edges.map(function(){ return 0; }), used = {};
    for(var v0 = 0; v0 < n; v0++){
      if(!isDecision(v0)) continue;
      var outs = [];
      chains.forEach(function(c, j){ if(c && c[0] === v0) outs.push(j); });
      if(outs.length < 2) continue;
      outs.sort(function(a, b){ return cc[chains[a][1]] - cc[chains[b][1]]; });
      var cand = [[outs[0], -1], [outs[outs.length - 1], 1]];
      cand.forEach(function(pr){
        var nx = chains[pr[0]][1], dx = (cc[nx] - cc[v0]) * pr[1];
        if(dx >= cs[v0] / 2 + 2 && clearBetween(v0, nx)) { port[pr[0]] = pr[1]; used[v0 + ':' + pr[1]] = true; }
      });
    }
    function clearBetween(v, nx){
      var a = Math.min(cc[v], cc[nx]), b = Math.max(cc[v], cc[nx]);
      return layers[layerOf[v]].every(function(u){ return u === v || cc[u] + cs[u] / 2 < a || cc[u] - cs[u] / 2 > b; });
    }

    var res = [], lanes = [];
    spec.edges.forEach(function(e, j){
      var pts = [], lab = null, lw = (opt.labelW && opt.labelW[j]) || 0, c = chains[j];
      if(c){
        var v = c[0], cur;
        if(port[j]){ pts.push([cc[v] + port[j] * cs[v] / 2, mMid(v)]); cur = cc[c[1]]; pts.push([cur, mMid(v)]); }
        else { cur = cc[v]; pts.push([cur, mEnd(v)]); }
        for(var q = 1; q < c.length; q++){
          var w = c[q], ym = gapAfter(layerOf[c[q - 1]]);
          if(Math.abs(cur - cc[w]) > 0.5){ pts.push([cur, ym]); pts.push([cc[w], ym]); cur = cc[w]; }
          if(isReal[w]) pts.push([cc[w], mStart(w)]);
        }
        if(lw){
          if(port[j]) lab = {c:cc[v] + port[j] * (cs[v] / 2 + 5), m:mMid(v), side:port[j], kind:'port'};
          else { var sd = cc[c[1]] < cc[v] - 1 ? -1 : 1; lab = {c:cc[c[1]] + sd * 5, m:gapAfter(layerOf[v]) + 3, side:sd, kind:'gap'}; }
        }
        res.push({pts:pts, lab:lab, back:false});
        return;
      }
      var f = e.f, t = e.t;
      if(f === t){
        var x0 = cc[f] + sideAt(f, 7), ext = cc[f] + cs[f] / 2 + 16, m0 = mMid(f);
        pts = [[x0, m0 - 7], [ext, m0 - 7], [ext, m0 + 7], [x0, m0 + 7]];
        if(lw) lab = {c:ext + 5, m:m0, side:1, kind:'lane'};
        res.push({pts:pts, lab:lab, back:true});
        return;
      }
      // Going back: around the nearest side, close to the steps it passes.
      var l0 = Math.min(layerOf[f], layerOf[t]), l1 = Math.max(layerOf[f], layerOf[t]), lo = Infinity, hi = -Infinity;
      for(var l = l0; l <= l1; l++) layers[l].forEach(function(u){ lo = Math.min(lo, cc[u] - cs[u] / 2); hi = Math.max(hi, cc[u] + cs[u] / 2); });
      function cost(sd){
        var edge = sd > 0 ? hi : lo, c2 = Math.abs(edge - cc[f] - sd * cs[f] / 2) + Math.abs(edge - cc[t] - sd * cs[t] / 2);
        if(!clear(f, sd) || used[f + ':' + sd]) c2 += 400;
        if(!clear(t, sd) || used[t + ':' + sd]) c2 += 400;
        return c2;
      }
      var side = cost(1) <= cost(-1) ? 1 : -1;
      var m0b = Math.min(mMid(f), mMid(t)) - 20, m1b = Math.max(mMid(f), mMid(t)) + 20;
      var lane = side > 0 ? hi + LANE : lo - LANE;
      while(lanes.some(function(x){ return Math.abs(x.c - lane) < LANE_STEP - 1 && x.m0 < m1b && m0b < x.m1; })) lane += side * LANE_STEP;
      lanes.push({c:lane, m0:m0b, m1:m1b});
      if(clear(f, side) && !used[f + ':' + side]){ pts.push([cc[f] + side * cs[f] / 2, mMid(f)]); pts.push([lane, mMid(f)]); }
      else { var yo = gapAfter(layerOf[f]) + 6; pts.push([cc[f], mEnd(f)]); pts.push([cc[f], yo]); pts.push([lane, yo]); }
      // A side point a decision's branch already leaves from is not an entry.
      if(clear(t, side) && !used[t + ':' + side]){ pts.push([lane, mMid(t)]); pts.push([cc[t] + side * sideAt(t, 0), mMid(t)]); }
      else {
        var yi = layerOf[t] ? gapAfter(layerOf[t] - 1) - 6 : ls[0] - 12;
        pts.push([lane, yi]); pts.push([cc[t], yi]); pts.push([cc[t], mStart(t)]);
      }
      if(lw) lab = {c:lane + side * 5, m:(pts[1][1] + pts[pts.length - 2][1]) / 2, side:side, kind:'lane'};
      res.push({pts:pts, lab:lab, back:true});
    });

    // Map to x and y, then shift everything into view.
    function xy(p){ return dir === 'down' ? [p[0], p[1]] : [p[1], p[0]]; }
    var boxes = [];
    for(i = 0; i < n; i++){
      var b0 = xy([cc[i] - cs[i] / 2, mStart(i)]);
      boxes.push({x:b0[0], y:b0[1], w:opt.sizes[i].w, h:opt.sizes[i].h});
    }
    var edgesOut = res.map(function(rr, j){
      var pts2 = simplify(rr.pts).map(xy), label = null;
      if(rr.lab){
        var lw2 = opt.labelW[j], q = xy([rr.lab.c, rr.lab.m]), lx, ly;
        if(rr.lab.kind === 'lane' && upright){
          // Centred on the lane line, reading upwards; the box is turned too.
          lx = q[0] - rr.lab.side * 5 - LH / 2; ly = q[1] - lw2 / 2;
          label = {x:lx, y:ly, w:LH, h:lw2, upright:true};
        } else if(rr.lab.kind === 'lane'){
          if(dir === 'down'){ lx = rr.lab.side > 0 ? q[0] : q[0] - lw2; ly = q[1] - LH / 2; }
          else { lx = q[0] - lw2 / 2; ly = rr.lab.side > 0 ? q[1] : q[1] - LH; }
        } else if(rr.lab.kind === 'port'){
          if(dir === 'down'){ lx = rr.lab.side > 0 ? q[0] : q[0] - lw2; ly = q[1] - LH - 2; }
          else { lx = q[0] - lw2 - 5; ly = rr.lab.side > 0 ? q[1] + 2 : q[1] - LH - 2; }
        } else {
          if(dir === 'down'){ lx = rr.lab.side > 0 ? q[0] : q[0] - lw2; ly = q[1]; }
          else { lx = q[0] + 1; ly = q[1] - LH - 3 - 5; }
        }
        if(!label) label = {x:lx, y:ly, w:lw2, h:LH};
        if(rr.lab.kind === 'gap') label.gap = true;
      }
      var a = pts2[pts2.length - 2], z = pts2[pts2.length - 1], len = Math.hypot(z[0] - a[0], z[1] - a[1]) || 1;
      return {f:spec.edges[j].f, t:spec.edges[j].t, pts:pts2, end:[(z[0] - a[0]) / len, (z[1] - a[1]) / len], label:label, back:rr.back};
    });
    placeGapLabels(edgesOut, boxes, dir, LH);
    var x0b = Infinity, y0b = Infinity, x1b = -Infinity, y1b = -Infinity;
    function grow(x, y, w, h){ x0b = Math.min(x0b, x); y0b = Math.min(y0b, y); x1b = Math.max(x1b, x + w); y1b = Math.max(y1b, y + h); }
    boxes.forEach(function(b){ grow(b.x, b.y, b.w, b.h); });
    edgesOut.forEach(function(e){ e.pts.forEach(function(p){ grow(p[0] - 4, p[1] - 4, 8, 8); }); if(e.label) grow(e.label.x, e.label.y, e.label.w, e.label.h); });
    var pad = 4, sx = pad - x0b, sy = pad - y0b;
    boxes.forEach(function(b){ b.x += sx; b.y += sy; });
    edgesOut.forEach(function(e){ e.pts = e.pts.map(function(p){ return [p[0] + sx, p[1] + sy]; }); if(e.label){ e.label.x += sx; e.label.y += sy; } });
    return {w:Math.ceil(x1b - x0b + 2 * pad), h:Math.ceil(y1b - y0b + 2 * pad), dir:dir, nodes:boxes, edges:edgesOut, layers:nl, crossings:bestC};
  }
  // A label of a link that bends sits on its own run through the gap (between
  // the two columns), not next to another arrow into the same step. Each spot
  // is tried in turn and taken when it touches no step, line or other label.
  function placeGapLabels(edges, boxes, dir, LH){
    function hit(a, b){ return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
    var segs = [], placed = [];
    edges.forEach(function(e){
      for(var k = 0; k + 1 < e.pts.length; k++){
        var a = e.pts[k], b = e.pts[k + 1];
        segs.push({x:Math.min(a[0], b[0]) - 1, y:Math.min(a[1], b[1]) - 1, w:Math.abs(b[0] - a[0]) + 2, h:Math.abs(b[1] - a[1]) + 2});
      }
      if(e.label && !e.label.gap) placed.push(e.label);
    });
    function free(r){
      return !boxes.some(function(b){ return hit(r, b); }) && !segs.some(function(g){ return hit(r, g); }) && !placed.some(function(l){ return hit(r, l); });
    }
    edges.forEach(function(e){
      var lb = e.label;
      if(!lb || !lb.gap) return;
      var w = lb.w, cand = [], run = null, k;
      for(k = 0; k + 1 < e.pts.length && !run; k++){
        var a = e.pts[k], b = e.pts[k + 1];
        var across = dir === 'down' ? Math.abs(a[1] - b[1]) < 0.5 && Math.abs(a[0] - b[0]) > 0.5 : Math.abs(a[0] - b[0]) < 0.5 && Math.abs(a[1] - b[1]) > 0.5;
        if(across) run = [a, b];
      }
      // A run several links share (a fan out of one step) is no place for a
      // label: then it goes by the column of the step it leads to.
      var shared = run && edges.some(function(o){
        if(o === e) return false;
        for(var q = 0; q + 1 < o.pts.length; q++){
          var c = o.pts[q], d = o.pts[q + 1], ax = dir === 'down' ? 1 : 0, bx = 1 - ax;
          if(Math.abs(c[ax] - run[0][ax]) < 0.5 && Math.abs(d[ax] - run[0][ax]) < 0.5 &&
            Math.min(Math.max(c[bx], d[bx]), Math.max(run[0][bx], run[1][bx])) - Math.max(Math.min(c[bx], d[bx]), Math.min(run[0][bx], run[1][bx])) > 2) return true;
        }
        return false;
      });
      if(run && dir === 'down'){
        var y = run[0][1], x1 = run[0][0], x2 = run[1][0], mid = (x1 + x2) / 2, sd = x2 > x1 ? 1 : -1;
        var byTarget = [{x:sd > 0 ? x2 - 5 - w : x2 + 5, y:y + 3}, {x:sd > 0 ? x2 + 5 : x2 - 5 - w, y:y + 3}];
        if(shared) cand = cand.concat(byTarget);
        if(Math.abs(x2 - x1) >= w + 10){ cand.push({x:mid - w / 2, y:y - LH - 2}); cand.push({x:mid - w / 2, y:y + 2}); }
        cand.push({x:sd > 0 ? x1 + 5 : x1 - 5 - w, y:y - LH - 3});
        if(!shared) cand = cand.concat(byTarget);
      } else if(run){
        var x = run[0][0], my = (run[0][1] + run[1][1]) / 2;
        if(shared) cand.push({x:lb.x, y:lb.y});
        cand.push({x:x + 4, y:my - LH / 2}); cand.push({x:x - 4 - w, y:my - LH / 2});
      }
      cand.push({x:lb.x, y:lb.y});
      for(k = 0; k < cand.length; k++){
        var r = {x:cand[k].x, y:cand[k].y, w:w, h:LH};
        if(free(r)){ lb.x = r.x; lb.y = r.y; break; }
      }
      placed.push(lb);
    });
  }
  function simplify(pts){
    var out = [];
    pts.forEach(function(p){
      var l = out[out.length - 1];
      if(l && Math.abs(l[0] - p[0]) < 0.5 && Math.abs(l[1] - p[1]) < 0.5) return;
      out.push(p);
      var k = out.length;
      if(k >= 3){
        var a = out[k - 3], b = out[k - 2], c = out[k - 1];
        if((Math.abs(a[0] - b[0]) < 0.5 && Math.abs(b[0] - c[0]) < 0.5) || (Math.abs(a[1] - b[1]) < 0.5 && Math.abs(b[1] - c[1]) < 0.5)) out.splice(k - 2, 1);
      }
    });
    return out;
  }

  function typeWord(type, lang){ return TYPE_WORDS[lang === 'en' ? 'en' : 'nl'][type] || ''; }
  function nextText(spec, k){
    return spec.edges.filter(function(e){ return e.f === k; }).map(function(e){ return spec.nodes[e.t].label + (e.label ? ' (' + e.label + ')' : ''); });
  }

  K.register('flow', {
    fences:['flowchart', 'proces', 'processchema', 'stroomschema', 'processtroom', 'procesflow'],
    name:{nl:'Processchema', en:'Flowchart'},
    noun:{nl:'processtroom', en:'flowchart'},
    icon:'flow',
    streamHeight:420,
    validate:validate,
    rank:rank,
    layout:layout,
    estHeight:function(spec){
      var nl = 1;
      try{ var r = rank(spec); nl = Math.max.apply(null, r.layer) + 1; }catch(_){}
      return 24 + (spec.subtitle ? 24 : 0) + nl * 64 + (nl - 1) * 44 + 40 + (spec.source ? 28 : 0);
    },
    table:function(spec){
      var en = spec.lang === 'en', lang = en ? 'en' : 'nl';
      return {header:en ? ['Step', 'Type', 'Owner', 'Next steps'] : ['Stap', 'Type', 'Eigenaar', 'Volgende stappen'],
        rows:spec.nodes.map(function(nd){ return [nd.label, typeWord(nd.type, lang), nd.owner, nextText(spec, nd.k).join('; ')]; }),
        types:['text', 'text', 'text', 'text']};
    }
  });

  // ── Drawing (kit frame only) ────────────────────────────────────────────
  var R = root.SWKitRender;
  if(!R || typeof document === 'undefined') return;
  var SVG = 'http://www.w3.org/2000/svg';
  var TEXT = {
    nl:{pick:'Kies een stap voor de details.', next:'Daarna', label:'Processchema', back:'terug naar'},
    en:{pick:'Choose a step for the details.', next:'Then', label:'Flowchart', back:'back to'}
  };
  function svg(tag, cls){ var e = document.createElementNS(SVG, tag); if(cls) e.setAttribute('class', cls); return e; }
  function rounded(pts, rad){
    var d = 'M' + r1(pts[0][0]) + ' ' + r1(pts[0][1]);
    for(var i = 1; i < pts.length; i++){
      var p = pts[i];
      if(i < pts.length - 1){
        var a = pts[i - 1], b = pts[i + 1];
        var l1 = Math.hypot(p[0] - a[0], p[1] - a[1]), l2 = Math.hypot(b[0] - p[0], b[1] - p[1]);
        var rr = Math.min(rad, l1 / 2, l2 / 2);
        var p1 = [p[0] - (p[0] - a[0]) / l1 * rr, p[1] - (p[1] - a[1]) / l1 * rr];
        var p2 = [p[0] + (b[0] - p[0]) / l2 * rr, p[1] + (b[1] - p[1]) / l2 * rr];
        d += ' L' + r1(p1[0]) + ' ' + r1(p1[1]) + ' Q' + r1(p[0]) + ' ' + r1(p[1]) + ' ' + r1(p2[0]) + ' ' + r1(p2[1]);
      } else d += ' L' + r1(p[0]) + ' ' + r1(p[1]);
    }
    return d;
  }
  function r1(v){ return Math.round(v * 10) / 10; }

  R.register('flow', function(box, spec, restore, ctx){
    var LANG = ctx.lang() === 'en' ? 'en' : 'nl', T = TEXT[LANG];
    var n = spec.nodes.length;
    var wrap = ctx.h('div', 'k-flow');
    var scroll = ctx.h('div', 'k-flow-scroll');
    var canvas = ctx.h('div', 'k-flow-canvas');
    canvas.setAttribute('role', 'group');
    canvas.setAttribute('aria-label', T.label + ': ' + spec.title);
    var detail = ctx.h('p', 'k-flow-detail', T.pick);
    detail.setAttribute('role', 'status');
    detail.setAttribute('aria-live', 'polite');
    var sizer = ctx.h('div', 'k-flow-sizer');
    sizer.appendChild(canvas);
    scroll.appendChild(sizer);
    wrap.append(scroll, detail);
    if(spec.source) wrap.appendChild(ctx.h('p', 'k-source', spec.source));
    box.appendChild(wrap);

    var edgeSvg = svg('svg', 'k-flow-edges');
    edgeSvg.setAttribute('aria-hidden', 'true');
    edgeSvg.setAttribute('focusable', 'false');
    canvas.appendChild(edgeSvg);
    var labelEls = spec.edges.map(function(e){
      if(!e.label) return null;
      var s = ctx.h('span', 'k-flow-elabel', e.label);
      s.setAttribute('aria-hidden', 'true');
      canvas.appendChild(s);
      return s;
    });
    var nodeEls = spec.nodes.map(function(nd, i){
      var b = ctx.h('button', 'k-flow-node is-' + nd.type);
      b.type = 'button';
      if(nd.type === 'decision'){
        var sh = svg('svg', 'k-flow-diamond');
        sh.setAttribute('aria-hidden', 'true');
        sh.setAttribute('preserveAspectRatio', 'none');
        sh.setAttribute('viewBox', '0 0 100 100');
        var poly = svg('polygon');
        poly.setAttribute('points', '50,1.5 98.5,50 50,98.5 1.5,50');
        poly.setAttribute('vector-effect', 'non-scaling-stroke');
        sh.appendChild(poly);
        b.appendChild(sh);
      }
      var inner = ctx.h('span', 'k-flow-text');
      inner.appendChild(ctx.h('span', 'k-flow-label', nd.label));
      if(nd.owner){
        var ow = ctx.h('span', 'k-flow-owner');
        var dot = ctx.h('span', 'k-flow-dot' + (nd.o >= 0 ? ' is-o' + nd.o : ''));
        dot.setAttribute('aria-hidden', 'true');
        ow.append(dot, document.createTextNode(nd.owner));
        inner.appendChild(ow);
      }
      b.appendChild(inner);
      var next = nextText(spec, i);
      b.setAttribute('aria-label', [nd.label, nd.type === 'step' ? '' : typeWord(nd.type, LANG), nd.owner].filter(Boolean).join(', '));
      b.setAttribute('aria-pressed', 'false');
      b.tabIndex = i === 0 ? 0 : -1;
      b.addEventListener('click', function(){ select(i, false); });
      b.addEventListener('keydown', function(e){
        var at = readOrder.indexOf(i), to;
        if(e.key === 'ArrowDown' || e.key === 'ArrowRight') to = at + 1;
        else if(e.key === 'ArrowUp' || e.key === 'ArrowLeft') to = at - 1;
        else if(e.key === 'Home') to = 0;
        else if(e.key === 'End') to = n - 1;
        else return;
        e.preventDefault();
        var target = readOrder[Math.max(0, Math.min(n - 1, to))];
        nodeEls.forEach(function(x, j){ x.tabIndex = j === target ? 0 : -1; });
        nodeEls[target].focus();
      });
      b._next = next;
      canvas.appendChild(b);
      return b;
    });
    var pathEls = [], headEls = [], readOrder = [], active = -1, lastW = 0, geo = null;

    function measure(W, phone, right){
      var sizes = [];
      nodeEls.forEach(function(b, i){
        var t = spec.nodes[i].type;
        b.style.left = '0px'; b.style.top = '0px'; b.style.height = '';
        if(t === 'start' || t === 'end'){
          b.style.width = ''; b.style.maxWidth = W + 'px';
          var w = Math.min(W, Math.max(Math.min(W, 96), Math.ceil(b.offsetWidth) + 1));
          b.style.maxWidth = ''; b.style.width = w + 'px';
          sizes.push({w:w, h:Math.max(36, b.offsetHeight)});
        } else if(t === 'decision'){
          var DW = Math.round(W * (right ? 1.04 : 1.18)), tw = Math.round(DW * 0.6);
          b.style.width = DW + 'px';
          b.style.paddingLeft = b.style.paddingRight = Math.round((DW - tw) / 2) + 'px';
          var th = b.querySelector('.k-flow-text').offsetHeight;
          sizes.push({w:DW, h:Math.max(phone ? 60 : 64, Math.ceil(th / 0.4 * 0.86 + 4))});
        } else {
          b.style.width = W + 'px';
          sizes.push({w:W, h:Math.max(44, b.offsetHeight)});
        }
      });
      return sizes;
    }
    function draw(){
      var avail = Math.max(240, Math.floor(box.clientWidth || 600));
      if(Math.abs(avail - lastW) < 4 && geo) return;
      lastW = avail;
      var phone = avail < 480;
      canvas.style.width = '2000px'; canvas.style.transform = '';
      labelEls.forEach(function(sp){ if(sp) sp.classList.remove('is-up'); });
      var labelW = labelEls.map(function(sp){ return sp ? Math.ceil(sp.offsetWidth) + 1 : 0; });
      var hasLabels = labelW.some(Boolean);
      // Each try: a step width and, on phones, tighter gaps and lanes for the
      // narrow ones. A try wins when it fits at the scale it may shrink to.
      var tries = phone
        ? [[220, 16, 1], [184, 16, 1], [156, 16, 1], [132, 16, 1], [116, 16, 1], [116, 12, 0.92, 14], [100, 10, 0.9, 13], [92, 10, 0.84, 13]]
        : [[184, 30, 1], [164, 30, 1], [144, 30, 1], [124, 30, 0.84]];
      var rightTries = [[168, 22, 1], [148, 22, 1], [132, 22, 0.84]];
      var dirs = spec.direction === 'right' && !phone ? ['right', 'down'] : ['down'];
      var pick = null;
      for(var d = 0; d < dirs.length && !pick; d++){
        var ws = dirs[d] === 'right' ? rightTries : tries;
        for(var k = 0; k < ws.length; k++){
          var tr = ws[k], sizes = measure(tr[0], phone, dirs[d] === 'right');
          var g = layout(spec, {dir:dirs[d], sizes:sizes, labelW:labelW,
            gapMain:dirs[d] === 'right' ? (hasLabels ? 52 : 44) : (hasLabels ? 50 : 40), gapCross:tr[1],
            lane:tr[3], laneStep:tr[3] ? 10 : 0, uprightLanes:phone});
          g.minScale = tr[2];
          // Right first: only when it fits as it is, else the page runs down.
          var lastDir = d === dirs.length - 1;
          if(g.w <= avail || (lastDir && g.w * tr[2] <= avail)){ pick = g; break; }
          if(lastDir && k === ws.length - 1) pick = g;
        }
      }
      geo = pick;
      // A little too wide: shrink it a bit; far too wide: scroll sideways.
      var scale = geo.w > avail ? Math.max(0.84, avail / geo.w) : 1;
      canvas.style.width = geo.w + 'px';
      canvas.style.height = geo.h + 'px';
      canvas.style.transform = scale < 1 ? 'scale(' + r1(scale * 1000) / 1000 + ')' : '';
      sizer.style.width = Math.ceil(geo.w * scale) + 'px';
      sizer.style.height = Math.ceil(geo.h * scale) + 'px';
      var wide = geo.w * scale > avail + 1;
      scroll.classList.toggle('is-wide', wide);
      fades();
      if(wide) scroll.tabIndex = 0; else scroll.removeAttribute('tabindex');
      canvas.classList.toggle('is-right', geo.dir === 'right');
      // Sizes of the chosen width were measured last only for the last try: set them now.
      nodeEls.forEach(function(b, i){
        var g2 = geo.nodes[i], t = spec.nodes[i].type;
        b.style.left = r1(g2.x) + 'px'; b.style.top = r1(g2.y) + 'px';
        b.style.width = g2.w + 'px'; b.style.height = g2.h + 'px';
        if(t === 'decision'){ var tw = Math.round(g2.w * 0.6); b.style.paddingLeft = b.style.paddingRight = Math.round((g2.w - tw) / 2) + 'px'; }
      });
      edgeSvg.textContent = '';
      edgeSvg.setAttribute('width', geo.w); edgeSvg.setAttribute('height', geo.h);
      edgeSvg.setAttribute('viewBox', '0 0 ' + geo.w + ' ' + geo.h);
      pathEls = []; headEls = [];
      geo.edges.forEach(function(e, j){
        var g3 = svg('g', 'k-flow-edge' + (e.back ? ' is-back' : ''));
        var pts = e.pts.slice(), z = pts[pts.length - 1], AL = 7, AW = 4.2;
        // The line stops at the arrow's base so its tip stays sharp.
        pts[pts.length - 1] = [z[0] - e.end[0] * (AL - 1), z[1] - e.end[1] * (AL - 1)];
        var path = svg('path', 'k-flow-line');
        path.setAttribute('d', rounded(pts, 7));
        var head = svg('path', 'k-flow-head');
        var bx = z[0] - e.end[0] * AL, by = z[1] - e.end[1] * AL, px = -e.end[1] * AW, py = e.end[0] * AW;
        head.setAttribute('d', 'M' + r1(z[0]) + ' ' + r1(z[1]) + ' L' + r1(bx + px) + ' ' + r1(by + py) + ' L' + r1(bx - px) + ' ' + r1(by - py) + ' Z');
        g3.append(path, head);
        edgeSvg.appendChild(g3);
        pathEls.push(g3);
        var s = labelEls[j];
        if(s && e.label){
          s.classList.toggle('is-up', !!e.label.upright);
          s.style.left = r1(e.label.x) + 'px'; s.style.top = r1(e.label.y) + 'px';
        }
      });
      // Reading order for the arrow keys: top to bottom, then left to right.
      readOrder = spec.nodes.map(function(_, i){ return i; }).sort(function(a, b){
        var A = geo.nodes[a], B = geo.nodes[b];
        var ka = geo.dir === 'down' ? [A.y + A.h / 2, A.x] : [A.x + A.w / 2, A.y], kb = geo.dir === 'down' ? [B.y + B.h / 2, B.x] : [B.x + B.w / 2, B.y];
        return (Math.abs(ka[0] - kb[0]) > 8 ? ka[0] - kb[0] : ka[1] - kb[1]) || a - b;
      });
      // Tab follows the drawing, not the order of the JSON.
      var focused = nodeEls.indexOf(document.activeElement);
      readOrder.forEach(function(i){ canvas.appendChild(nodeEls[i]); });
      if(focused >= 0) nodeEls[focused].focus({preventScroll:true});
      if(active >= 0) mark(active);
      else nodeEls.forEach(function(x, j){ x.tabIndex = j === readOrder[0] ? 0 : -1; });
      ctx.resize();
    }
    // Where the drawing scrolls sideways, the edge that hides more fades out.
    function fades(){
      var max = scroll.scrollWidth - scroll.clientWidth;
      scroll.classList.toggle('has-left', max > 1 && scroll.scrollLeft > 1);
      scroll.classList.toggle('has-right', max > 1 && scroll.scrollLeft < max - 1);
    }
    scroll.addEventListener('scroll', fades, {passive:true});
    function mark(i){
      canvas.classList.toggle('has-active', i >= 0);
      nodeEls.forEach(function(b, j){
        b.setAttribute('aria-pressed', String(j === i)); b.classList.toggle('is-active', j === i); b.tabIndex = j === i ? 0 : -1;
        var near = spec.edges.some(function(e){ return (e.f === i && e.t === j) || (e.t === i && e.f === j); });
        b.classList.toggle('is-near', j !== i && near);
      });
      spec.edges.forEach(function(e, j){
        var hot = e.f === i || e.t === i;
        if(pathEls[j]) pathEls[j].classList.toggle('is-hot', hot);
        if(labelEls[j]) labelEls[j].classList.toggle('is-hot', hot);
      });
    }
    function select(i, quiet){
      var nd = spec.nodes[i];
      if(!nd) return;
      active = i;
      mark(i);
      var next = nodeEls[i]._next;
      var parts = [nd.label, nd.type === 'step' ? '' : typeWord(nd.type, LANG), nd.owner, nd.note, next.length ? T.next + ': ' + next.join('; ') : ''];
      detail.textContent = parts.filter(Boolean).join(' · ');
      detail.classList.add('is-set');
      if(!quiet) ctx.save({a:i});
      ctx.resize();
    }

    draw();
    if(typeof restore.a === 'number' && restore.a >= 0 && restore.a < n) select(restore.a, true);
    var raf = 0;
    if(typeof ResizeObserver === 'function'){
      new ResizeObserver(function(){
        if(raf) return;
        raf = requestAnimationFrame(function(){ raf = 0; draw(); });
      }).observe(box);
    }
    return {onTheme:function(){}, onFull:function(){ lastW = 0; draw(); }};
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
