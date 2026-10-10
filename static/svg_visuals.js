// Inline SVG visuals in chat (plan addendum section 3, package A1).
//
// renderMd (static/ui.js) asks two hooks from this file which fenced blocks and
// raw <svg> runs are visuals (seams AE-1 and AE-2); it builds an escaped
// placeholder itself. postProcessRenderedMessages (AE-4) then calls
// renderSvgVisualBlocks and enhanceSvgMediaCards. Model SVG is never put into
// the live DOM: a sanitised copy is shown as <img src="data:image/svg+xml;
// base64,...">, which cannot run script or load anything. The same rules are
// implemented in Python in api/svg_inline.py; one fixture corpus drives both.
//
// Globals (every one typeof-guarded by ui.js): svgVisualFenceAccepts,
// svgVisualRawSpans, sanitizeSvgSource, renderSvgVisualBlocks,
// enhanceSvgMediaCards, retintSvgVisuals. Internals live in _svgVisuals.

const _svgVisuals=(function(){
  const SVG_NS='http://www.w3.org/2000/svg';
  const XLINK_NS='http://www.w3.org/1999/xlink';
  const XML_NS='http://www.w3.org/XML/1998/namespace';
  const XMLNS_NS='http://www.w3.org/2000/xmlns/';
  const MAX_SOURCE_BYTES=128*1024;
  const MAX_ELEMENTS=4000;
  const MAX_DEPTH=48;
  const MAX_STYLE_BYTES=8*1024;
  const MAX_TITLE=200;
  const MAX_DISPLAY_WIDTH=720;
  const MIN_DISPLAY_WIDTH=320;
  const RETINT_DELAY_MS=50;

  const words=s=>new Set(s.split(/\s+/).filter(Boolean));
  const ALLOWED=words('svg g defs symbol use title desc text tspan textPath path rect circle ellipse line polyline polygon '+
    'linearGradient radialGradient stop pattern clipPath mask marker filter feGaussianBlur feOffset feBlend '+
    'feColorMatrix feComposite feFlood feMerge feMergeNode feDropShadow feMorphology style');
  const FORBIDDEN=words('script foreignobject iframe object embed image img a animate set animatemotion animatetransform '+
    'animatecolor feimage audio video canvas html body head link meta base form input button textarea frame frameset '+
    'discard handler listener');
  const TEXT_ONLY=words('title desc style');
  const GLOBAL_ATTRS=words('id class role aria-label aria-hidden aria-labelledby aria-describedby lang xml:lang xml:space style');
  const PRESENTATION=words('alignment-baseline baseline-shift clip-path clip-rule color color-interpolation '+
    'color-interpolation-filters direction display dominant-baseline fill fill-opacity fill-rule filter flood-color '+
    'flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight isolation '+
    'letter-spacing lighting-color marker-end marker-mid marker-start mask mix-blend-mode opacity overflow paint-order '+
    'pointer-events shape-rendering stop-color stop-opacity stroke stroke-dasharray stroke-dashoffset stroke-linecap '+
    'stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering transform '+
    'transform-origin unicode-bidi vector-effect visibility word-spacing writing-mode');
  const FE='x y width height result ';
  const ELEMENT_ATTRS={
    svg:words('viewBox preserveAspectRatio width height x y version'),
    g:words(''), defs:words(''), title:words(''), desc:words(''),
    symbol:words('viewBox preserveAspectRatio x y width height refX refY'),
    use:words('href x y width height'),
    text:words('x y dx dy rotate textLength lengthAdjust'),
    tspan:words('x y dx dy rotate textLength lengthAdjust'),
    textPath:words('href startOffset method spacing side textLength lengthAdjust'),
    path:words('d pathLength'),
    rect:words('x y width height rx ry pathLength'),
    circle:words('cx cy r pathLength'),
    ellipse:words('cx cy rx ry pathLength'),
    line:words('x1 y1 x2 y2 pathLength'),
    polyline:words('points pathLength'),
    polygon:words('points pathLength'),
    linearGradient:words('x1 y1 x2 y2 gradientUnits gradientTransform spreadMethod href'),
    radialGradient:words('cx cy r fx fy fr gradientUnits gradientTransform spreadMethod href'),
    stop:words('offset'),
    pattern:words('x y width height patternUnits patternContentUnits patternTransform viewBox preserveAspectRatio href'),
    clipPath:words('clipPathUnits'),
    mask:words('x y width height maskUnits maskContentUnits mask-type'),
    marker:words('viewBox preserveAspectRatio refX refY markerUnits markerWidth markerHeight orient'),
    filter:words('x y width height filterUnits primitiveUnits'),
    feGaussianBlur:words(FE+'in stdDeviation edgeMode'),
    feOffset:words(FE+'in dx dy'),
    feBlend:words(FE+'in in2 mode'),
    feColorMatrix:words(FE+'in type values'),
    feComposite:words(FE+'in in2 operator k1 k2 k3 k4'),
    feFlood:words(FE),
    feMerge:words(FE),
    feMergeNode:words('in'),
    feDropShadow:words(FE+'in dx dy stdDeviation'),
    feMorphology:words(FE+'in operator radius'),
    style:words('type media'),
  };
  // Standalone copies, downloads and the paper card use these. The values
  // are the fallbacks the visuals prompt asks the model to write.
  const LIGHT_TOKENS=[
    ['--sp-fg','#1f2937'],['--sp-muted','#6b7280'],['--sp-accent','#f97316'],
    ['--sp-surface','#f3f4f6'],['--sp-border','#d1d5db'],['--sp-bg','#ffffff'],
    ['--sp-ok','#16a34a'],['--sp-warn','#d97706'],['--sp-err','#dc2626'],
  ];
  // Where each token comes from in the page theme (DESIGN.md tokens).
  const THEME_SOURCES={
    '--sp-fg':'--text','--sp-muted':'--muted','--sp-accent':'--accent','--sp-surface':'--surface',
    '--sp-border':'--border','--sp-bg':'--code-bg','--sp-ok':'--success','--sp-warn':'--warning','--sp-err':'--error',
  };
  const DROP_CODES=words('element_dropped attribute_dropped');

  const DOCTYPE_RE=/<!(?:DOCTYPE|ENTITY)/i;
  const BARE_AMP_RE=/&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)/g;
  const BARE_LT_RE=/<(?![A-Za-z_:/!?])/g;
  const CSS_COMMENT_RE=/\/\*[\s\S]*?(?:\*\/|$)/g;
  const COMPACT_RE=/[\s\x00-\x1f]+/g;
  const CSS_FORBIDDEN_RE=/@import|@font-face|expression\(|-moz-binding|behavior:|image-set\(|image\(|cross-fade\(|element\(|paint\(/;
  const SCHEME_RE=/javascript:|vbscript:|livescript:|data:/;
  const STYLE_IMPORT_RE=/@import[^;]*;?/gi;
  const STYLE_FONT_FACE_RE=/@font-face\s*\{[^}]*\}?/gi;
  const CSS_SPACE=' \t\n\r\f';
  const SVG_TAG_RE=/<(\/?)svg(?=[ \t\r\n\/>])/g;
  const HREF_RE=/^#[^\s()'"<>\\]+$/;
  const NUMBER_RE=/^((?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(?:px)?$/;
  const LENGTH_RE=/^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:px)?$/;
  const BOX_PART_RE=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
  const TOKEN_VALUE_RE=/^[#(),.%\w\s-]{1,64}$/;
  const XML_SPACE=' \t\r\n';

  const cache=new WeakMap();      // figure -> {svg, paper, title}
  const mediaCache=new WeakMap(); // media figure -> Promise<result>
  let retintPending=false;
  let drawingLabel='';

  // ── helpers ────────────────────────────────────────────────────────────
  function utf8Len(text){
    if(typeof TextEncoder!=='undefined') return new TextEncoder().encode(text).length;
    let n=0;
    for(const ch of text){const c=ch.codePointAt(0);n+=c<0x80?1:c<0x800?2:c<0x10000?3:4;}
    return n;
  }
  function compact(value){return String(value).replace(COMPACT_RE,'').toLowerCase();}
  function tr(key,fallback){
    try{
      if(typeof t==='function'){const v=t(key);if(v&&v!==key) return v;}
    }catch(_){/* i18n not ready */}
    return fallback||'';
  }
  function newRun(){
    const run={reasons:[],warnings:[]};
    run.reason=code=>{if(run.reasons.indexOf(code)===-1) run.reasons.push(code);};
    run.warn=code=>{if(run.warnings.indexOf(code)===-1) run.warnings.push(code);};
    return run;
  }
  function hasBadUrl(c){
    let i=c.indexOf('url(');
    while(i!==-1){
      let rest=c.slice(i+4);
      if(rest[0]==='"'||rest[0]==="'") rest=rest.slice(1);
      if(rest[0]!=='#') return true;
      i=c.indexOf('url(',i+4);
    }
    return false;
  }
  function cssIssue(text){
    if(String(text).indexOf('\\')!==-1) return 'forbidden_css';
    const c=compact(String(text).replace(CSS_COMMENT_RE,''));
    if(CSS_FORBIDDEN_RE.test(c)) return 'forbidden_css';
    if(SCHEME_RE.test(c)||hasBadUrl(c)) return 'external_reference';
    return null;
  }
  // Plan 3.2 rule 4: a value that could load or run something is dropped.
  function valueIssue(name,value){
    if(name==='style') return cssIssue(value);
    const c=compact(value);
    if(SCHEME_RE.test(c)) return 'external_reference';
    if(c.indexOf('expression(')!==-1||c.indexOf('@import')!==-1) return 'forbidden_css';
    if(hasBadUrl(c)) return 'external_reference';
    if(name!=='aria-label'){
      if(String(value).indexOf('\\')!==-1) return 'forbidden_css';
      if(CSS_FORBIDDEN_RE.test(c)) return 'forbidden_css';
    }
    return null;
  }
  // Every well-formed url() whose target is not a #id becomes none. A linear
  // scan: a regex for this can be made to backtrack. Anything malformed is
  // left for the final check, which then drops the whole block.
  function replaceRemoteUrls(css,onRemote){
    const lower=css.toLowerCase();
    let out='',i=0;
    for(;;){
      const at=lower.indexOf('url(',i);
      if(at===-1){out+=css.slice(i);break;}
      let j=at+4;
      while(j<css.length&&CSS_SPACE.indexOf(css[j])!==-1) j++;
      let target=null,end=-1;
      if(css[j]==='"'||css[j]==="'"){
        const close=css.indexOf(css[j],j+1);
        if(close!==-1){target=css.slice(j+1,close);end=close+1;}
      } else {
        let k=j;
        while(k<css.length&&'\'")'.indexOf(css[k])===-1&&CSS_SPACE.indexOf(css[k])===-1) k++;
        target=css.slice(j,k);
        end=k;
      }
      if(end!==-1){
        let k=end;
        while(k<css.length&&CSS_SPACE.indexOf(css[k])!==-1) k++;
        if(css[k]===')'){
          if(target.trim().charAt(0)==='#') out+=css.slice(i,k+1);
          else {onRemote();out+=css.slice(i,at)+'none';}
          i=k+1;
          continue;
        }
      }
      out+=css.slice(i,at+4);
      i=at+4;
    }
    return out;
  }
  // Plan 3.2 rule 5: @import, @font-face and remote url() leave a <style>.
  function sanitizeStyleText(text,run){
    if(text.indexOf('\\')!==-1){run.reason('forbidden_css');return null;}
    let css=text.replace(CSS_COMMENT_RE,'');
    css=css.replace(STYLE_IMPORT_RE,()=>{run.reason('forbidden_css');return '';});
    css=css.replace(STYLE_FONT_FACE_RE,()=>{run.reason('forbidden_css');return '';});
    css=replaceRemoteUrls(css,()=>run.reason('external_reference'));
    const c=compact(css);
    if(CSS_FORBIDDEN_RE.test(c)){run.reason('forbidden_css');return null;}
    if(SCHEME_RE.test(c)||hasBadUrl(c)){run.reason('external_reference');return null;}
    if(utf8Len(css)>MAX_STYLE_BYTES){run.reason('style_too_large');return null;}
    return css;
  }
  function startTagEnd(text,start){
    let quote='';
    for(let i=start+1;i<text.length;i++){
      const ch=text[i];
      if(quote){if(ch===quote) quote='';continue;}
      if(ch==='"'||ch==="'"){quote=ch;continue;}
      if(ch==='>') return i;
      if(ch==='<') return -1;
    }
    return -1;
  }
  // Where the root element starts: after an optional byte order mark, XML
  // declaration, comments and processing instructions (-1 when one is not
  // closed). A linear scan, where a regex could backtrack exponentially.
  function prologEnd(text){
    let i=0;
    if(text.charCodeAt(0)===0xFEFF) i=1;
    for(;;){
      while(i<text.length&&XML_SPACE.indexOf(text[i])!==-1) i++;
      if(text.startsWith('<!--',i)){
        const end=text.indexOf('-->',i+4);
        if(end===-1) return -1;
        i=end+3;
      } else if(text.startsWith('<?',i)){
        const end=text.indexOf('?>',i+2);
        if(end===-1) return -1;
        i=end+2;
      } else return i;
    }
  }
  // Where <svg must start in an xml fence (plan 3.1): after an optional byte
  // order mark, an optional XML declaration and then comments only.
  function fencePrologEnd(text){
    let i=text.charCodeAt(0)===0xFEFF?1:0;
    if(text.startsWith('<?xml',i)&&i+5<text.length&&(' \t\r\n?').indexOf(text[i+5])!==-1){
      const end=text.indexOf('?>',i+5);
      if(end===-1) return -1;
      i=end+2;
    }
    for(;;){
      while(i<text.length&&XML_SPACE.indexOf(text[i])!==-1) i++;
      if(!text.startsWith('<!--',i)) return i;
      const end=text.indexOf('-->',i+4);
      if(end===-1) return -1;
      i=end+3;
    }
  }
  function startsWithSvgTag(text,i){
    return i!==-1&&text.startsWith('<svg',i)&&i+4<text.length&&(' \t\r\n/>').indexOf(text[i+4])!==-1;
  }
  // Repair the slips XML parsers refuse (bare & and <, a missing xmlns) so a
  // decent drawing is not thrown away; nothing here can create markup.
  function prepare(source,run){
    let text=source.replace(/&nbsp;/g,'&#160;').replace(BARE_AMP_RE,'&amp;').replace(BARE_LT_RE,'&lt;');
    const tagStart=prologEnd(text);
    if(!startsWithSvgTag(text,tagStart)) return text;
    const tagEnd=startTagEnd(text,tagStart);
    if(tagEnd===-1) return text;
    const tag=text.slice(tagStart,tagEnd);
    let extra='';
    if(!/\sxmlns\s*=/.test(tag)){extra+=' xmlns="'+SVG_NS+'"';run.warn('no_xmlns');}
    if(text.indexOf('xlink:')!==-1&&!/xmlns:xlink\s*=/.test(text)) extra+=' xmlns:xlink="'+XLINK_NS+'"';
    if(extra) text=text.slice(0,tagStart+4)+extra+text.slice(tagStart+4);
    return text;
  }
  function parseBox(value){
    const parts=String(value||'').trim().split(/[\s,]+/).filter(Boolean);
    if(parts.length!==4||!parts.every(p=>BOX_PART_RE.test(p))) return null;
    const n=parts.map(Number);
    if(!n.every(Number.isFinite)||n[2]<=0||n[3]<=0) return null;
    return n;
  }
  function positiveNumber(value){
    const m=NUMBER_RE.exec(String(value==null?'':value).trim());
    if(!m) return null;
    const n=Number(m[1]);
    return Number.isFinite(n)&&n>0?n:null;
  }
  function length(raw){
    const m=LENGTH_RE.exec(String(raw).trim());
    if(!m) return null;
    const n=Number(m[1]);
    return Number.isFinite(n)?n:null;
  }
  function fmt(n){return String(Number(n.toFixed(6)));}
  function measure(root){
    let count=0,depth=0;
    const stack=[[root,1]];
    while(stack.length){
      const [el,level]=stack.pop();
      count++;
      if(level>depth) depth=level;
      if(count>MAX_ELEMENTS||depth>MAX_DEPTH) break;
      for(let c=el.firstElementChild;c;c=c.nextElementSibling) stack.push([c,level+1]);
    }
    return {count,depth};
  }
  function attrName(a){
    if(!a.namespaceURI) return a.localName||a.name;
    if(a.namespaceURI===XLINK_NS&&a.localName==='href') return 'href';
    if(a.namespaceURI===XML_NS) return 'xml:'+a.localName;
    return null;
  }
  function copyAttrs(el,node,name,run){
    const allowed=ELEMENT_ATTRS[name]||words('');
    for(const a of Array.from(el.attributes)){
      if(a.namespaceURI===XMLNS_NS||a.name==='xmlns'||a.name.indexOf('xmlns:')===0) continue;
      const local=a.localName||a.name;
      const value=a.value;
      if(/^on/i.test(local)){run.reason('event_handler');continue;}
      const attr=attrName(a);
      if(attr==='xml:base'){run.reason('external_reference');continue;}
      let permitted;
      if(name==='title'||name==='desc') permitted=!!attr&&GLOBAL_ATTRS.has(attr)&&attr!=='style';
      else if(name==='style') permitted=!!attr&&(allowed.has(attr)||(GLOBAL_ATTRS.has(attr)&&attr!=='style'));
      else permitted=!!attr&&(GLOBAL_ATTRS.has(attr)||PRESENTATION.has(attr)||allowed.has(attr));
      if(!permitted){
        const issue=valueIssue(attr||local,value);
        if(attr==='href'&&value.trim().charAt(0)!=='#') run.reason('external_reference');
        else if(issue) run.reason(issue);
        else run.warn('attribute_dropped');
        continue;
      }
      if(attr==='href'){
        const target=value.trim();
        if(!HREF_RE.test(target)){run.reason('external_reference');continue;}
        node.setAttribute('href',target);
        continue;
      }
      const issue=valueIssue(attr,value);
      if(issue){run.reason(issue);continue;}
      if(attr.indexOf('xml:')===0) node.setAttributeNS(XML_NS,attr,value);
      else node.setAttribute(attr,value);
    }
  }
  function build(el,run,doc){
    const ns=el.namespaceURI;
    const local=el.localName;
    let name;
    if(ns===SVG_NS&&local==='a'){run.reason('forbidden_element');name='g';}
    else if(ns!==SVG_NS||!ALLOWED.has(local)){
      if(FORBIDDEN.has(String(local).toLowerCase())) run.reason('forbidden_element');
      else run.warn('element_dropped');
      return null;
    } else name=local;
    const node=doc.createElementNS(SVG_NS,name);
    copyAttrs(el,node,name,run);
    if(name==='style'){
      const kind=String(el.getAttribute('type')||'').trim().toLowerCase();
      if(kind&&kind!=='text/css'){run.reason('forbidden_css');return null;}
      const css=sanitizeStyleText(el.textContent||'',run);
      if(css===null) return null;
      if(css) node.appendChild(doc.createTextNode(css));
      return node;
    }
    if(TEXT_ONLY.has(name)){
      const text=el.textContent||'';
      if(text) node.appendChild(doc.createTextNode(text));
      return node;
    }
    for(let c=el.firstChild;c;c=c.nextSibling){
      if(c.nodeType===1){const child=build(c,run,doc);if(child) node.appendChild(child);}
      else if(c.nodeType===3||c.nodeType===4) node.appendChild(doc.createTextNode(c.nodeValue));
      else if(c.nodeType===7) run.reason('processing_instruction');
    }
    return node;
  }
  function firstTitle(root){
    const title=root.getElementsByTagNameNS(SVG_NS,'title')[0];
    if(!title) return '';
    return String(title.textContent||'').replace(/\s+/g,' ').trim().slice(0,MAX_TITLE);
  }
  function styleProp(node,prop){
    const style=node.getAttribute('style')||'';
    for(const decl of style.split(';')){
      const i=decl.indexOf(':');
      if(i!==-1&&decl.slice(0,i).trim().toLowerCase()===prop) return decl.slice(i+1).trim();
    }
    return null;
  }
  function isBackgroundRect(node,box){
    if(node.localName!=='rect') return false;
    const fill=String(styleProp(node,'fill')||node.getAttribute('fill')||'').trim().toLowerCase();
    if(fill==='none'||fill==='transparent') return false;
    const origin={x:box[0],y:box[1]};
    for(const key of ['x','y']){
      const raw=String(node.getAttribute(key)||'0').trim();
      const v=raw==='0%'?0:length(raw);
      if(v===null||v>origin[key]) return false;
    }
    const size={width:box[2],height:box[3]};
    for(const key of ['width','height']){
      const raw=String(node.getAttribute(key)||'').trim();
      if(raw==='100%') continue;
      const v=length(raw);
      if(v===null||v<size[key]) return false;
    }
    return true;
  }
  // Plan 3.1 paper fallback: no --sp-* token and no full-size background.
  function isPaper(root,svg,box){
    if(svg.indexOf('--sp-')!==-1) return false;
    for(let c=root.firstElementChild;c;c=c.nextElementSibling){
      if(['defs','title','desc','style'].indexOf(c.localName)!==-1) continue;
      return !isBackgroundRect(c,box);
    }
    return true;
  }

  // ── sanitiser (plan 3.2) ───────────────────────────────────────────────
  function sanitize(source){
    const run=newRun();
    const fail=code=>({ok:false,svg:'',title:'',box:null,reasons:[code].concat(run.reasons),paper:false});
    if(typeof source!=='string') return fail('empty');
    if(utf8Len(source)>MAX_SOURCE_BYTES) return fail('too_large');
    if(!source.trim()) return fail('empty');
    if(DOCTYPE_RE.test(source)) return fail('doctype');
    const Serializer=typeof window!=='undefined'&&window?window.XMLSerializer:undefined;
    if(typeof DOMParser==='undefined'||typeof Serializer!=='function') return fail('parse_error');
    const prepared=prepare(source,run);
    let doc;
    try{doc=new DOMParser().parseFromString(prepared,'image/svg+xml');}catch(_){return fail('parse_error');}
    if(!doc||!doc.documentElement||doc.getElementsByTagNameNS('*','parsererror').length) return fail('parse_error');
    for(let n=doc.firstChild;n;n=n.nextSibling){if(n.nodeType===7) run.reason('processing_instruction');}
    const root=doc.documentElement;
    if(root.namespaceURI!==SVG_NS||root.localName!=='svg') return fail('not_svg');
    const size=measure(root);
    if(size.count>MAX_ELEMENTS) return fail('too_many_elements');
    if(size.depth>MAX_DEPTH) return fail('too_deep');
    const clean=build(root,run,doc);
    let box=parseBox(clean.getAttribute('viewBox'));
    if(!box){
      const w=positiveNumber(clean.getAttribute('width'));
      const h=positiveNumber(clean.getAttribute('height'));
      if(w===null||h===null) return fail('no_viewbox');
      box=[0,0,w,h];
      clean.setAttribute('viewBox','0 0 '+fmt(w)+' '+fmt(h));
    }
    if(clean.hasAttribute('width')||clean.hasAttribute('height')){
      run.warn('fixed_size');
      clean.removeAttribute('width');
      clean.removeAttribute('height');
    }
    const svg=new Serializer().serializeToString(clean);
    return {
      ok:true,
      svg,
      title:firstTitle(clean),
      box:{x:box[0],y:box[1],width:box[2],height:box[3]},
      reasons:run.reasons.concat(run.warnings.filter(c=>DROP_CODES.has(c))),
      paper:isPaper(clean,svg,box),
    };
  }

  // ── theme ──────────────────────────────────────────────────────────────
  function themeStyle(tokens){
    const map=new Map(tokens||[]);
    const decls=LIGHT_TOKENS.map(([name,fallback])=>{
      let v=map.get(name);
      if(typeof v!=='string'||!TOKEN_VALUE_RE.test(v)||/url/i.test(v)) v=fallback;
      return name+':'+v.trim();
    });
    return '<style>:root{'+decls.join(';')+';color:var(--sp-fg)}</style>';
  }
  function withTheme(svg,tokens){
    if(typeof svg!=='string'||svg.indexOf('<svg')!==0) return svg;
    const end=startTagEnd(svg,0);
    if(end===-1) return svg;
    const style=themeStyle(tokens||LIGHT_TOKENS);
    if(svg[end-1]==='/') return svg.slice(0,end-1)+'>'+style+'</svg>'+svg.slice(end+1);
    return svg.slice(0,end+1)+style+svg.slice(end+1);
  }
  function currentTokens(){
    let cs=null;
    try{cs=getComputedStyle(document.documentElement);}catch(_){cs=null;}
    return LIGHT_TOKENS.map(([name,fallback])=>{
      const v=cs?String(cs.getPropertyValue(THEME_SOURCES[name])||'').trim():'';
      return [name,v&&TOKEN_VALUE_RE.test(v)&&!/url/i.test(v)?v:fallback];
    });
  }
  function toBase64(text){
    const bytes=new TextEncoder().encode(text);
    let bin='';
    for(let i=0;i<bytes.length;i+=0x8000) bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+0x8000));
    return btoa(bin);
  }
  function dataUri(svg){return 'data:image/svg+xml;base64,'+toBase64(svg);}
  function exportText(entry){return withTheme(entry.svg,LIGHT_TOKENS);}
  function displayUri(entry,tokens){return dataUri(withTheme(entry.svg,entry.paper?LIGHT_TOKENS:(tokens||currentTokens())));}

  // ── renderer hooks (AE-1, AE-2) ────────────────────────────────────────
  function fenceAccepts(lang,code){
    if(typeof lang!=='string'||typeof code!=='string') return false;
    const body=code.trim();
    if(!body) return false;
    if(lang==='svg') return true;
    if(lang==='xml') return startsWithSvgTag(body,fencePrologEnd(body));
    return false;
  }
  // Unclosed fences, tilde fences, table rows and inline code spans are
  // never turned into visuals.
  function excludedRanges(text){
    const ranges=[];
    let offset=0;
    let open=null;
    for(const line of text.split('\n')){
      const lineEnd=offset+line.length;
      const m=/^ {0,3}(`{3,}|~{3,})/.exec(line);
      if(!open){
        if(m) open={start:offset,ch:m[1][0],len:m[1].length};
        else if(/^\s*\|/.test(line)) ranges.push([offset,lineEnd]);
      } else if(m&&m[1][0]===open.ch&&m[1].length>=open.len&&/^ {0,3}[`~]+\s*$/.test(line)){
        ranges.push([open.start,lineEnd]);
        open=null;
      }
      offset=lineEnd+1;
    }
    if(open) ranges.push([open.start,text.length]);
    const code=/`[^`\n]+`/g;
    let m;
    while((m=code.exec(text))) ranges.push([m.index,m.index+m[0].length]);
    ranges.sort((a,b)=>a[0]-b[0]);
    const merged=[];
    for(const r of ranges){
      const last=merged[merged.length-1];
      if(last&&r[0]<=last[1]) last[1]=Math.max(last[1],r[1]);
      else merged.push([r[0],r[1]]);
    }
    return merged;
  }
  // Merged ranges are sorted by start and end: binary search the first one
  // that ends after start.
  function overlaps(ranges,start,end){
    let lo=0,hi=ranges.length;
    while(lo<hi){const mid=(lo+hi)>>1;if(ranges[mid][1]<=start) lo=mid+1;else hi=mid;}
    return lo<ranges.length&&ranges[lo][0]<end;
  }
  // One pass over the <svg and </svg tags: every open tag is matched with
  // the first close tag that leaves the tags between them balanced. A tag
  // that is not closed (no '>') breaks every run still open around it.
  function svgRunEnds(text){
    const opens=[],ends=new Map(),stack=[];
    SVG_TAG_RE.lastIndex=0;
    let m;
    while((m=SVG_TAG_RE.exec(text))){
      const start=m.index;
      if(m[1]){
        const close=text.indexOf('>',start);
        if(close===-1){stack.length=0;break;}
        if(stack.length) ends.set(stack.pop(),close+1);
        SVG_TAG_RE.lastIndex=close+1;
      } else {
        const end=startTagEnd(text,start);
        if(end===-1){stack.length=0;SVG_TAG_RE.lastIndex=start+4;continue;}
        opens.push(start);
        if(text[end-1]!=='/') stack.push(start);
        SVG_TAG_RE.lastIndex=end+1;
      }
    }
    return {opens,ends};
  }
  function rawSpans(text){
    if(typeof text!=='string'||text.indexOf('<svg')===-1) return [];
    const excluded=excludedRanges(text);
    const {opens,ends}=svgRunEnds(text);
    const spans=[];
    let last=0;
    for(const start of opens){
      if(start<last||!ends.has(start)) continue;
      const end=ends.get(start);
      const chunk=text.slice(start,end);
      if(chunk.indexOf('\x00')===-1&&/<\/svg>$/.test(chunk)&&!overlaps(excluded,start,end)) spans.push([start,end]);
      last=end;
    }
    return spans;
  }

  // ── DOM ────────────────────────────────────────────────────────────────
  function el(tag,cls){const n=document.createElement(tag);if(cls) n.className=cls;return n;}
  function button(action,label,iconHtml){
    let b=null;
    if(typeof _createMermaidViewerButton==='function'){
      try{b=_createMermaidViewerButton(label,'fullscreen',()=>onAction(b,action));}catch(_){b=null;}
    }
    if(!b){
      b=el('button','mermaid-viewer-btn');
      b.type='button';
      b.setAttribute('aria-label',label);
      b.setAttribute('title',label);
    }
    b.classList.add('svg-visual-btn');
    b.setAttribute('data-svg-action',action);
    if(iconHtml) b.innerHTML=iconHtml;
    return b;
  }
  function icon(name){return typeof li==='function'?li(name,14):'';}
  function toolbar(){
    const bar=el('div','svg-visual-toolbar');
    bar.setAttribute('role','toolbar');
    bar.setAttribute('aria-label',tr('svg_toolbar_label','Visual actions'));
    const full=typeof _mermaidViewerIcon==='function'?_mermaidViewerIcon('fullscreen'):'';
    bar.appendChild(button('view',tr('svg_view_full','View full size'),full));
    bar.appendChild(button('copy',tr('svg_copy','Copy SVG'),icon('copy')));
    bar.appendChild(button('download',tr('svg_download','Download SVG'),icon('download')));
    const src=button('source',tr('svg_show_source','Show source'),icon('braces'));
    src.setAttribute('aria-pressed','false');
    bar.appendChild(src);
    return bar;
  }
  function displaySize(box){
    const w=Math.round(Math.min(MAX_DISPLAY_WIDTH,Math.max(box.width,MIN_DISPLAY_WIDTH)));
    return {width:w,height:Math.max(1,Math.round(w*box.height/box.width))};
  }
  function buildFigure(res){
    const entry={svg:res.svg,paper:!!res.paper,title:res.title||''};
    const fig=el('figure','svg-visual'+(entry.paper?' svg-visual--paper':''));
    fig.setAttribute('data-rendered','1');
    fig.appendChild(toolbar());
    const img=el('img','svg-visual-img');
    img.setAttribute('role','img');
    img.alt=entry.title||tr('svg_visual_label','Visual');
    img.loading='lazy';
    img.decoding='async';
    const size=displaySize(res.box);
    img.width=size.width;
    img.height=size.height;
    img.src=displayUri(entry);
    fig.appendChild(img);
    if(entry.title){
      const cap=el('figcaption','svg-visual-caption');
      cap.textContent=entry.title;
      fig.appendChild(cap);
    }
    const pre=el('pre','svg-visual-source');
    pre.hidden=true;
    const code=el('code','language-svg');
    code.textContent=entry.svg;
    pre.appendChild(code);
    fig.appendChild(pre);
    cache.set(fig,entry);
    return fig;
  }
  function buildBlocked(source){
    const wrap=el('div','svg-visual-blocked');
    wrap.setAttribute('data-rendered','1');
    const note=el('p','svg-visual-notice');
    note.setAttribute('role','note');
    note.textContent=tr('svg_blocked','');
    const head=el('div','pre-header');
    head.textContent='svg';
    const pre=el('pre');
    const code=el('code','language-svg');
    code.textContent=source;
    pre.appendChild(code);
    if(note.textContent) wrap.appendChild(note);
    wrap.appendChild(head);
    wrap.appendChild(pre);
    return wrap;
  }
  function replaceNode(oldNode,newNode){
    if(oldNode.parentNode) oldNode.parentNode.replaceChild(newNode,oldNode);
  }
  function renderBlocks(root){
    if(typeof document==='undefined') return;
    const scope=root&&typeof root.querySelectorAll==='function'?root:document;
    updateDrawingLabel();
    const blocks=scope.querySelectorAll('.svg-visual-block:not([data-rendered])');
    if(!blocks.length) return;
    blocks.forEach(block=>{
      block.setAttribute('data-rendered','1');
      const source=block.textContent||'';
      let res;
      try{res=sanitize(source);}catch(_){res={ok:false};}
      if(res.ok){
        replaceNode(block,buildFigure(res));
      } else {
        const node=buildBlocked(source);
        replaceNode(block,node);
        try{if(typeof highlightCode==='function') highlightCode(node);}catch(_){/* optional */}
        try{if(typeof addCopyButtons==='function') addCopyButtons(node);}catch(_){/* optional */}
      }
    });
  }
  function mediaUrl(src){
    if(!src||typeof document==='undefined') return null;
    try{
      const url=new URL(src,document.baseURI);
      if(typeof location!=='undefined'&&url.origin!==location.origin) return null;
      if(!/\/api\/media$/.test(url.pathname)) return null;
      return url;
    }catch(_){return null;}
  }
  function enhanceMedia(root){
    if(typeof document==='undefined') return;
    const scope=root&&typeof root.querySelectorAll==='function'?root:document;
    scope.querySelectorAll('img.msg-media-svg:not([data-svg-enhanced])').forEach(img=>{
      if(img.closest('.svg-visual')) return;
      const src=img.getAttribute('src')||'';
      if(!mediaUrl(src)) return;
      img.setAttribute('data-svg-enhanced','1');
      const fig=el('figure','svg-visual svg-visual--media');
      fig.setAttribute('data-rendered','1');
      if(!img.parentNode) return;
      img.parentNode.insertBefore(fig,img);
      fig.appendChild(toolbar());
      fig.appendChild(img);
      const pre=el('pre','svg-visual-source');
      pre.hidden=true;
      pre.appendChild(el('code','language-svg'));
      fig.appendChild(pre);
    });
  }
  function entryFor(fig){
    if(cache.has(fig)) return cache.get(fig);
    // A figure restored from the render cache has no entry: sanitise the
    // stored source again, so only sanitised bytes are ever reused.
    const code=fig.querySelector('pre.svg-visual-source > code');
    if(!code) return null;
    const res=sanitize(code.textContent||'');
    if(!res.ok) return null;
    const entry={svg:res.svg,paper:!!res.paper,title:res.title||''};
    cache.set(fig,entry);
    return entry;
  }
  function mediaEntry(fig){
    if(mediaCache.has(fig)) return mediaCache.get(fig);
    const img=fig.querySelector('img.msg-media-svg');
    const url=mediaUrl(img&&img.getAttribute('src'));
    const p=(url&&typeof fetch==='function'
      ?fetch(url.href,{credentials:'same-origin'}).then(r=>r.ok?r.text():Promise.reject(new Error('media '+r.status)))
      :Promise.reject(new Error('media unavailable')))
      .then(text=>{const res=sanitize(text);if(!res.ok) throw new Error('rejected');return {svg:res.svg,paper:!!res.paper,title:res.title||''};});
    p.catch(()=>mediaCache.delete(fig));
    mediaCache.set(fig,p);
    return p;
  }
  function toast(message){
    try{if(typeof showToast==='function'&&message) showToast(message);}catch(_){/* optional */}
  }
  function copyText(text){
    if(typeof _copyText==='function') return _copyText(text);
    if(typeof navigator!=='undefined'&&navigator.clipboard&&navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return Promise.reject(new Error('clipboard unavailable'));
  }
  function slug(title){
    const s=String(title||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60).replace(/-+$/,'');
    return s||'visual';
  }
  // Downloads build a blob: URL and click a download link; the page never
  // navigates to it, and the URL is revoked right after the click.
  function downloadText(text,name){
    const url=URL.createObjectURL(new Blob([text],{type:'image/svg+xml'}));
    const a=document.createElement('a');
    a.href=url;
    a.download=name;
    a.rel='noopener';
    a.style.display='none';
    document.body.appendChild(a);
    try{a.click();}
    finally{
      a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  }
  function openFull(fig){
    const img=fig.querySelector('img.svg-visual-img, img.msg-media-svg');
    if(!img||typeof _openImgLightbox!=='function') return;
    _openImgLightbox(img);
    const boxes=document.querySelectorAll('.img-lightbox');
    const lb=boxes[boxes.length-1];
    if(lb){
      lb.classList.add('svg-visual-lightbox');
      if(fig.classList.contains('svg-visual--paper')) lb.classList.add('svg-visual-lightbox--paper');
    }
  }
  function showSource(fig,btn,entry){
    const pre=fig.querySelector('pre.svg-visual-source');
    if(!pre) return;
    const code=pre.querySelector('code');
    if(entry&&code&&!code.textContent) code.textContent=entry.svg;
    const show=pre.hidden;
    pre.hidden=!show;
    btn.setAttribute('aria-pressed',show?'true':'false');
    const label=show?tr('svg_hide_source','Hide source'):tr('svg_show_source','Show source');
    btn.setAttribute('aria-label',label);
    btn.setAttribute('title',label);
    if(show&&code&&!code.dataset.highlighted&&typeof Prism!=='undefined'&&Prism&&typeof Prism.highlightElement==='function'){
      try{Prism.highlightElement(code);code.dataset.highlighted='1';}catch(_){/* plain text stays */}
    }
  }
  function onAction(btn,action){
    const fig=btn&&btn.closest&&btn.closest('figure.svg-visual');
    if(!fig) return;
    const media=fig.classList.contains('svg-visual--media');
    if(action==='view'){openFull(fig);return;}
    if(action==='download'&&media){
      const img=fig.querySelector('img.msg-media-svg');
      const url=mediaUrl(img&&img.getAttribute('src'));
      if(!url) return;
      url.searchParams.set('download','1');
      const a=document.createElement('a');
      a.href=url.href;
      a.download='';
      a.style.display='none';
      document.body.appendChild(a);
      try{a.click();}finally{a.remove();}
      return;
    }
    if(media){
      mediaEntry(fig).then(entry=>{
        if(action==='copy') return copyText(exportText(entry)).then(()=>toast(tr('svg_copied','')));
        if(action==='source') showSource(fig,btn,entry);
        return null;
      }).catch(()=>{
        if(action==='copy') toast(tr('copy_failed',''));
        else btn.disabled=true;
      });
      return;
    }
    const entry=entryFor(fig);
    if(action==='copy'){
      if(!entry){toast(tr('copy_failed',''));return;}
      copyText(exportText(entry)).then(()=>toast(tr('svg_copied','')),()=>toast(tr('copy_failed','')));
      return;
    }
    if(action==='download'){
      if(entry) downloadText(exportText(entry),slug(entry.title)+'.svg');
      return;
    }
    if(action==='source') showSource(fig,btn,entry);
  }
  function onDocumentClick(e){
    const target=e.target;
    if(!target||typeof target.closest!=='function') return;
    const btn=target.closest('figure.svg-visual [data-svg-action]');
    if(btn){
      e.preventDefault();
      e.stopPropagation();
      onAction(btn,btn.getAttribute('data-svg-action'));
      return;
    }
    const img=target.closest('figure.svg-visual img.svg-visual-img, figure.svg-visual img.msg-media-svg');
    if(img){
      e.preventDefault();
      openFull(img.closest('figure.svg-visual'));
    }
  }
  function retint(){
    if(typeof document==='undefined') return;
    const tokens=currentTokens();
    document.querySelectorAll('figure.svg-visual[data-rendered]:not(.svg-visual--media)').forEach(fig=>{
      const entry=entryFor(fig);
      const img=fig.querySelector('img.svg-visual-img');
      if(!entry||!img||entry.paper) return;
      const src=displayUri(entry,tokens);
      if(img.getAttribute('src')!==src) img.setAttribute('src',src);
    });
  }
  // Coalesced to one retint per change: the next animation frame, so the
  // visual repaints together with the new theme, or at most 50 ms later when
  // no frame comes (a hidden tab).
  function scheduleRetint(){
    if(retintPending) return;
    retintPending=true;
    const run=()=>{
      if(!retintPending) return;
      retintPending=false;
      retint();
    };
    if(typeof requestAnimationFrame==='function') requestAnimationFrame(run);
    setTimeout(run,RETINT_DELAY_MS);
  }
  // The streaming label is CSS content, so it comes from a custom property
  // that follows the interface language.
  function updateDrawingLabel(){
    if(typeof document==='undefined'||!document.documentElement||!document.documentElement.style) return;
    const label=tr('svg_drawing','');
    if(!label||label===drawingLabel) return;
    drawingLabel=label;
    document.documentElement.style.setProperty('--svg-visual-drawing-label','"'+label.replace(/["\\\n\r]/g,' ')+'"');
  }
  function init(){
    if(typeof document==='undefined'||!document||!document.documentElement||typeof document.addEventListener!=='function') return;
    document.addEventListener('click',onDocumentClick);
    updateDrawingLabel();
    // The locale bundles may arrive after this file runs.
    try{
      const ready=typeof window!=='undefined'&&window?window.i18nReady:null;
      if(ready&&typeof ready.then==='function') ready.then(updateDrawingLabel,updateDrawingLabel);
    }catch(_){/* optional */}
    if(typeof MutationObserver==='function'){
      new MutationObserver(records=>{
        let theme=false,lang=false;
        for(const r of records){if(r.attributeName==='lang') lang=true;else theme=true;}
        if(lang) updateDrawingLabel();
        if(theme) scheduleRetint();
      }).observe(document.documentElement,{attributes:true,attributeFilter:['class','data-skin','lang']});
    }
  }
  init();

  return {
    sanitize,fenceAccepts,rawSpans,renderBlocks,enhanceMedia,retint,
    withTheme,exportText,currentTokens,dataUri,slug,LIGHT_TOKENS,
  };
})();

function svgVisualFenceAccepts(lang,code){return _svgVisuals.fenceAccepts(lang,code);}
function svgVisualRawSpans(text){return _svgVisuals.rawSpans(text);}
function sanitizeSvgSource(src){return _svgVisuals.sanitize(src);}
function renderSvgVisualBlocks(root){return _svgVisuals.renderBlocks(root);}
function enhanceSvgMediaCards(root){return _svgVisuals.enhanceMedia(root);}
function retintSvgVisuals(){return _svgVisuals.retint();}
