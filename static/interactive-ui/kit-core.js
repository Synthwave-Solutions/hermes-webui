// Data blocks: the shared, pure part (no DOM).
//
// A reply may hold a fenced block with JSON (```table, ```chart, ```map,
// ```kpi, ```timeline and their Dutch names) or a ```csv block. The chat never runs model code for
// these: static/interactive_ui.js checks the block with SWKit.build() and
// sends the cleaned spec to the kit frame (static/interactive-ui/kits.js),
// which draws it with its own fixed code. This file is loaded by the chat and
// inlined in the kit frame, so both sides read numbers, sort and export rows
// in exactly the same way. tests/interactive_kits.cjs covers it in Node.
//
// Global: SWKit (also module.exports under Node).

(function(root){
  'use strict';

  const KIT_LANGS={table:'table',tabel:'table',csv:'table',chart:'chart',grafiek:'chart',map:'map',kaart:'map',
    kpi:'kpi',kpis:'kpi','kpi-row':'kpi',timeline:'timeline',tijdlijn:'timeline',planning:'timeline'};
  const LIMITS={title:120,subtitle:200,source:200,label:60,cell:300,columns:12,rows:500,
    chartLabels:60,pieLabels:8,series:6,seriesName:40,mapTitle:100,mapSubtitle:160,places:25,
    placeName:80,address:200,time:20,note:240,category:30,categories:6,tones:20,specBytes:200*1024,
    kpiItems:8,kpiLabel:40,kpiNote:80,tlItems:20,tlLabel:60,tlOwner:40,tlNote:160,tlMaxUnit:1000,tlTicks:12};
  const COLUMN_TYPES=new Set(['text','number','currency','percent','date','status','link']);
  const CHART_TYPES=new Set(['bar','hbar','stacked','line','area','pie','donut','radar']);
  const TONES=new Set(['good','warn','bad','info']);
  const WIKI_LANGS=new Set(['nl','en','de','fr']);
  const NOUN={nl:{table:'tabel',chart:'grafiek',map:'kaart',kpi:'KPI-rij',timeline:'planning'},
    en:{table:'table',chart:'chart',map:'map',kpi:'KPI row',timeline:'timeline'}};
  const NAME={nl:{table:'Tabel',chart:'Grafiek',map:'Kaart',kpi:'Kerncijfers',timeline:'Planning'},
    en:{table:'Table',chart:'Chart',map:'Map',kpi:'Key figures',timeline:'Timeline'}};
  const KPI_FORMATS={number:'number',currency:'currency',euro:'currency',eur:'currency',percent:'percent',percentage:'percent','%':'percent'};
  const DELTA_FORMATS={percent:'percent',pct:'percent','%':'percent',number:'number',absolute:'number',abs:'number',value:'number'};
  const GOOD_DIRS={up:'up',higher:'up',hoger:'up',down:'down',lower:'down',lager:'down'};
  const TL_UNITS={day:'day',days:'day',dag:'day',dagen:'day',week:'week',weeks:'week',weken:'week',month:'month',months:'month',maand:'month',maanden:'month'};
  const TL_STATUS={todo:'todo','to do':'todo',planned:'todo',open:'todo',gepland:'todo','te doen':'todo',
    doing:'doing',active:'doing','in progress':'doing','in-progress':'doing',progress:'doing',bezig:'doing',
    done:'done',complete:'done',completed:'done',klaar:'done',afgerond:'done',
    risk:'risk',blocked:'risk',late:'risk',delayed:'risk',risico:'risk',geblokkeerd:'risk'};
  const STATUS_WORDS={nl:{todo:'Te doen',doing:'Bezig',done:'Klaar',risk:'Risico'},en:{todo:'To do',doing:'In progress',done:'Done',risk:'At risk'}};
  const UNIT_WORDS={nl:{day:['Dag','Dagen'],week:['Week','Weken'],month:['Maand','Maanden']},en:{day:['Day','Days'],week:['Week','Weeks'],month:['Month','Months']}};

  // ── Messages (short sentences, shown in details and sent with "repair") ──
  const MSG={
    nl:{
      json:(line)=>`De gegevens zijn geen geldige JSON${line?` (regel ${line})`:''}.`,
      notObject:()=>'De gegevens moeten één JSON-object zijn.',
      tooBig:()=>'De gegevens zijn te groot (meer dan 200 kB).',
      noTitle:()=>'De titel ontbreekt.',
      cut:(field,max)=>`${field} is ingekort tot ${max} tekens.`,
      noColumns:()=>'Er zijn geen kolommen (columns).',
      manyColumns:(n,max)=>`Er zijn ${n} kolommen; alleen de eerste ${max} worden getoond.`,
      colType:(label,type)=>`Kolom "${label}" heeft een onbekend type "${type}".`,
      noRows:()=>'De rijen (rows) ontbreken.',
      manyRows:(n,max)=>`Er zijn ${n} rijen; alleen de eerste ${max} worden getoond.`,
      rowNotList:(i)=>`Rij ${i} is geen lijst met waarden en is weggelaten.`,
      rowWidth:(i,got,want)=>`Rij ${i} heeft ${got} waarden, verwacht ${want}.`,
      cellValue:(i)=>`Rij ${i} bevat een waarde die geen tekst of getal is.`,
      sortColumn:()=>'De sorteerkolom bestaat niet.',
      csvEmpty:()=>'Het CSV-blok heeft geen kopregel met kolomnamen.',
      chartType:(t)=>`Onbekend grafiektype "${t}"; er is een staafgrafiek van gemaakt.`,
      noLabels:()=>'De labels ontbreken.',
      manyLabels:(n,max)=>`Er zijn ${n} labels; alleen de eerste ${max} worden getoond.`,
      pieOther:(max)=>`Een taartgrafiek toont maximaal ${max} delen; de rest staat samen onder "Overig".`,
      noSeries:()=>'Er zijn geen reeksen (series) met getallen.',
      manySeries:(n,max)=>`Er zijn ${n} reeksen; alleen de eerste ${max} worden getoond.`,
      pieOne:()=>'Een taartgrafiek toont één reeks; alleen de eerste wordt getoond.',
      seriesLength:(name,got,want)=>`Reeks "${name}" heeft ${got} waarden, verwacht ${want}.`,
      seriesValue:(name)=>`Reeks "${name}" bevat een waarde die geen getal is.`,
      pieNegative:()=>'Een taartgrafiek kan geen negatieve waarden tonen; die zijn op 0 gezet.',
      highlight:(h)=>`"${h}" is geen label of reeks; de nadruk is weggelaten.`,
      target:()=>'De doellijn (target) heeft geen getal en is weggelaten.',
      mapKind:(k)=>`Onbekend kaarttype "${k}"; de plaatsen worden zonder route getoond.`,
      routeShort:()=>'Een route heeft minstens twee plaatsen; de lijn is weggelaten.',
      noPlaces:()=>'Er zijn geen plaatsen (places).',
      manyPlaces:(n,max)=>`Er zijn ${n} plaatsen; alleen de eerste ${max} worden getoond.`,
      placeName:(i)=>`Plaats ${i} heeft geen naam en is weggelaten.`,
      placeCoords:(name)=>`Bij "${name}" kloppen de coördinaten niet; ze zijn genegeerd.`,
      placeSwap:(name)=>`Bij "${name}" stonden breedte- en lengtegraad omgedraaid; dat is hersteld.`,
      placeWiki:(name)=>`Bij "${name}" is de Wikipedia-titel ongeldig (gebruik bijvoorbeeld "nl:Rijksmuseum").`,
      placeUrl:(name)=>`Bij "${name}" is de link geen https-adres en is weggelaten.`,
      categories:(max)=>`Er zijn meer dan ${max} categorieën; de rest krijgt geen eigen kleur.`,
      kpiNoItems:()=>'Er zijn geen cijfers (items).',
      kpiNone:()=>'Geen enkel cijfer heeft een label en een getal als waarde (value).',
      kpiMany:(n,max)=>`Er zijn ${n} cijfers; alleen de eerste ${max} worden getoond.`,
      kpiItem:(i)=>`Cijfer ${i} is geen object met label en value en is weggelaten.`,
      kpiLabel:(i)=>`Cijfer ${i} heeft geen label en is weggelaten.`,
      kpiValue:(l)=>`"${l}" heeft geen getal als waarde (value) en is weggelaten.`,
      kpiFormat:(l,f)=>`"${l}" heeft een onbekend format "${f}"; gebruik number, currency of percent.`,
      kpiDelta:(l)=>`De verandering (delta) van "${l}" is geen getal en is weggelaten.`,
      kpiDeltaFormat:(l,f)=>`"${l}" heeft een onbekend deltaFormat "${f}"; gebruik percent of number.`,
      kpiGood:(l,g)=>`"${l}" heeft good "${g}"; gebruik up of down. Nu geldt up.`,
      kpiTarget:(l)=>`Het doel (target) van "${l}" is geen getal boven 0 en is weggelaten.`,
      tlNoItems:()=>'Er zijn geen onderdelen (items).',
      tlNone:()=>'Geen enkel onderdeel heeft een label en een geldige start (een getal of JJJJ-MM-DD).',
      tlMany:(n,max)=>`Er zijn ${n} onderdelen; alleen de eerste ${max} worden getoond.`,
      tlItem:(i)=>`Onderdeel ${i} is geen object met label en start en is weggelaten.`,
      tlLabel:(i)=>`Onderdeel ${i} heeft geen label en is weggelaten.`,
      tlBadStart:(l)=>`"${l}" heeft geen geldige start (een getal of JJJJ-MM-DD) en is weggelaten.`,
      tlNoEnd:(l)=>`"${l}" heeft geen geldige end en is als mijlpaal getoond.`,
      tlSwap:(l)=>`Bij "${l}" lag end voor start; die zijn omgedraaid.`,
      tlStatus:(l,st)=>`"${l}" heeft een onbekende status "${st}"; gebruik todo, doing, done of risk.`,
      tlUnit:(u)=>`Onbekende unit "${u}"; gebruik day, week of month. Nu geldt week.`,
      tlStart:()=>'De start van de planning is geen datum (JJJJ-MM-DD) en is genegeerd.',
      tlNoBase:(d)=>`Getallen bij start en end tellen vanaf de start van de planning; die ontbrak, dus is ${d} gebruikt.`,
      tlToday:()=>'today is geen getal of datum (JJJJ-MM-DD); de lijn voor vandaag is weggelaten.',
      tlTodayDate:()=>'today is een datum, maar de onderdelen gebruiken getallen zonder start; de lijn voor vandaag is weggelaten.',
    },
    en:{
      json:(line)=>`The data is not valid JSON${line?` (line ${line})`:''}.`,
      notObject:()=>'The data must be one JSON object.',
      tooBig:()=>'The data is too large (more than 200 kB).',
      noTitle:()=>'The title is missing.',
      cut:(field,max)=>`${field} was shortened to ${max} characters.`,
      noColumns:()=>'There are no columns.',
      manyColumns:(n,max)=>`There are ${n} columns; only the first ${max} are shown.`,
      colType:(label,type)=>`Column "${label}" has an unknown type "${type}".`,
      noRows:()=>'The rows are missing.',
      manyRows:(n,max)=>`There are ${n} rows; only the first ${max} are shown.`,
      rowNotList:(i)=>`Row ${i} is not a list of values and was left out.`,
      rowWidth:(i,got,want)=>`Row ${i} has ${got} values, expected ${want}.`,
      cellValue:(i)=>`Row ${i} holds a value that is not text or a number.`,
      sortColumn:()=>'The sort column does not exist.',
      csvEmpty:()=>'The CSV block has no header row with column names.',
      chartType:(t)=>`Unknown chart type "${t}"; a bar chart was drawn instead.`,
      noLabels:()=>'The labels are missing.',
      manyLabels:(n,max)=>`There are ${n} labels; only the first ${max} are shown.`,
      pieOther:(max)=>`A pie chart shows at most ${max} slices; the rest is grouped under "Other".`,
      noSeries:()=>'There are no series with numbers.',
      manySeries:(n,max)=>`There are ${n} series; only the first ${max} are shown.`,
      pieOne:()=>'A pie chart shows one series; only the first is shown.',
      seriesLength:(name,got,want)=>`Series "${name}" has ${got} values, expected ${want}.`,
      seriesValue:(name)=>`Series "${name}" holds a value that is not a number.`,
      pieNegative:()=>'A pie chart cannot show negative values; they were set to 0.',
      highlight:(h)=>`"${h}" is not a label or series; the highlight was left out.`,
      target:()=>'The target line has no number and was left out.',
      mapKind:(k)=>`Unknown map type "${k}"; the places are shown without a route.`,
      routeShort:()=>'A route needs at least two places; the line was left out.',
      noPlaces:()=>'There are no places.',
      manyPlaces:(n,max)=>`There are ${n} places; only the first ${max} are shown.`,
      placeName:(i)=>`Place ${i} has no name and was left out.`,
      placeCoords:(name)=>`The coordinates of "${name}" are not valid and were ignored.`,
      placeSwap:(name)=>`Latitude and longitude of "${name}" were swapped; this was fixed.`,
      placeWiki:(name)=>`The Wikipedia title of "${name}" is not valid (use for example "en:Rijksmuseum").`,
      placeUrl:(name)=>`The link of "${name}" is not an https address and was left out.`,
      categories:(max)=>`There are more than ${max} categories; the rest gets no colour of its own.`,
      kpiNoItems:()=>'There are no figures (items).',
      kpiNone:()=>'No figure has a label and a number as its value.',
      kpiMany:(n,max)=>`There are ${n} figures; only the first ${max} are shown.`,
      kpiItem:(i)=>`Figure ${i} is not an object with label and value and was left out.`,
      kpiLabel:(i)=>`Figure ${i} has no label and was left out.`,
      kpiValue:(l)=>`"${l}" has no number as its value and was left out.`,
      kpiFormat:(l,f)=>`"${l}" has an unknown format "${f}"; use number, currency or percent.`,
      kpiDelta:(l)=>`The change (delta) of "${l}" is not a number and was left out.`,
      kpiDeltaFormat:(l,f)=>`"${l}" has an unknown deltaFormat "${f}"; use percent or number.`,
      kpiGood:(l,g)=>`"${l}" has good "${g}"; use up or down. Up is used now.`,
      kpiTarget:(l)=>`The target of "${l}" is not a number above 0 and was left out.`,
      tlNoItems:()=>'There are no items.',
      tlNone:()=>'No item has a label and a valid start (a number or YYYY-MM-DD).',
      tlMany:(n,max)=>`There are ${n} items; only the first ${max} are shown.`,
      tlItem:(i)=>`Item ${i} is not an object with label and start and was left out.`,
      tlLabel:(i)=>`Item ${i} has no label and was left out.`,
      tlBadStart:(l)=>`"${l}" has no valid start (a number or YYYY-MM-DD) and was left out.`,
      tlNoEnd:(l)=>`"${l}" has no valid end and is shown as a milestone.`,
      tlSwap:(l)=>`The end of "${l}" was before its start; they were swapped.`,
      tlStatus:(l,st)=>`"${l}" has an unknown status "${st}"; use todo, doing, done or risk.`,
      tlUnit:(u)=>`Unknown unit "${u}"; use day, week or month. Week is used now.`,
      tlStart:()=>'The start of the timeline is not a date (YYYY-MM-DD) and was ignored.',
      tlNoBase:(d)=>`Numbers in start and end count from the start of the timeline; it was missing, so ${d} was used.`,
      tlToday:()=>'today is not a number or a date (YYYY-MM-DD); the line for today was left out.',
      tlTodayDate:()=>'today is a date, but the items use numbers without a start; the line for today was left out.',
    },
  };
  // The kind for a fence info string ('' when it is not a data block).
  function kitKind(lang){const l=String(lang||'').toLowerCase();return Object.prototype.hasOwnProperty.call(KIT_LANGS,l)?KIT_LANGS[l]:'';}
  function pickLang(lang){return String(lang||'').toLowerCase().startsWith('nl')?'nl':'en';}
  function messenger(lang){const table=MSG[pickLang(lang)];return (key,...args)=>table[key](...args);}

  // ── Lenient JSON: // and /* */ comments and trailing commas are allowed ──
  // Comments and trailing commas are replaced by spaces (newlines kept), so a
  // position in the cleaned text is the same position in the original.
  function cleanJson(text){
    const s=String(text==null?'':text).replace(/^\uFEFF/,'');
    let out='', i=0, inStr=false;
    while(i<s.length){
      const c=s[i];
      if(inStr){
        out+=c;
        if(c==='\\'&&i+1<s.length){out+=s[i+1];i+=2;continue;}
        if(c==='"') inStr=false;
        i++;continue;
      }
      if(c==='"'){inStr=true;out+=c;i++;continue;}
      if(c==='/'&&s[i+1]==='/'){
        while(i<s.length&&s[i]!=='\n'){out+=' ';i++;}
        continue;
      }
      if(c==='/'&&s[i+1]==='*'){
        out+='  ';i+=2;
        while(i<s.length&&!(s[i]==='*'&&s[i+1]==='/')){out+=s[i]==='\n'?'\n':' ';i++;}
        if(i<s.length){out+='  ';i+=2;}
        continue;
      }
      if(c===','){
        // A comma followed (after spaces and comments) by } or ] is trailing.
        const nx=s[nextSignificant(s,i+1)];
        if(nx==='}'||nx===']'){out+=' ';i++;continue;}
      }
      out+=c;i++;
    }
    return out;
  }
  function nextSignificant(s,j){
    while(j<s.length){
      if(/\s/.test(s[j])){j++;continue;}
      if(s[j]==='/'&&s[j+1]==='/'){while(j<s.length&&s[j]!=='\n')j++;continue;}
      if(s[j]==='/'&&s[j+1]==='*'){const e=s.indexOf('*/',j+2);j=e<0?s.length:e+2;continue;}
      break;
    }
    return j;
  }
  function lineOf(text,pos){
    if(!(pos>=0)) return 0;
    return String(text).slice(0,pos).split('\n').length;
  }
  function parseKit(text){
    const cleaned=cleanJson(text);
    try{
      return {ok:true,value:JSON.parse(cleaned)};
    }catch(err){
      const msg=String(err&&err.message||'');
      let line=0;
      const lm=/line (\d+)/i.exec(msg);
      const pm=/position (\d+)/i.exec(msg);
      if(lm) line=+lm[1];
      else if(pm) line=lineOf(cleaned,+pm[1]);
      else if(/unexpected end/i.test(msg)) line=cleaned.split('\n').length;
      return {ok:false,line,error:msg};
    }
  }

  // ── CSV (RFC 4180 quotes; delimiter , ; or tab, read from the first line) ─
  function detectDelimiter(text){
    const counts={',':0,';':0,'\t':0};
    let inQ=false;
    for(let i=0;i<text.length;i++){
      const c=text[i];
      if(c==='"'){inQ=!inQ;continue;}
      if(!inQ&&(c==='\n'||c==='\r')) break;
      if(!inQ&&c in counts) counts[c]++;
    }
    if(counts['\t']>0&&counts['\t']>=counts[',']&&counts['\t']>=counts[';']) return '\t';
    if(counts[';']>0&&counts[';']>=counts[',']) return ';';
    return ',';
  }
  function parseCsv(text,delimiter){
    const s=String(text==null?'':text).replace(/^\uFEFF/,'');
    const d=delimiter||detectDelimiter(s);
    const rows=[];
    let row=[], field='', inQ=false, quoted=false, i=0;
    const endField=()=>{row.push(quoted?field:field.trim());field='';quoted=false;};
    const endRow=()=>{endField();if(!(row.length===1&&row[0]===''&&!quoted))rows.push(row);row=[];};
    while(i<s.length){
      const c=s[i];
      if(inQ){
        if(c==='"'){
          if(s[i+1]==='"'){field+='"';i+=2;continue;}
          inQ=false;i++;continue;
        }
        field+=c;i++;continue;
      }
      if(c==='"'&&field.trim()===''){inQ=true;quoted=true;field='';i++;continue;}
      if(c===d){endField();i++;continue;}
      if(c==='\r'){if(s[i+1]==='\n')i++;endRow();i++;continue;}
      if(c==='\n'){endRow();i++;continue;}
      field+=c;i++;
    }
    if(field!==''||quoted||row.length) endRow();
    return {rows,delimiter:d};
  }

  // ── Numbers in Dutch or English notation, with euro and percent signs ────
  // Returns {n, kind} where kind is 'number', 'currency' or 'percent'; n is NaN
  // when the text is not a number. Dutch comes first when it is ambiguous:
  // "1.500" is fifteen hundred, "1,5" is one and a half.
  function parseNumber(value){
    if(typeof value==='number') return {n:Number.isFinite(value)?value:NaN,kind:'number'};
    if(typeof value!=='string') return {n:NaN,kind:'number'};
    const raw=value.trim();
    // A space between digits is only a thousands separator ("1 234 567"),
    // never a phone number or a code ("06 12345678").
    if(/\d[\u00a0\u202f\u2009 ]+\d/.test(raw)&&!/^[^\d]*\d{1,3}([\u00a0\u202f\u2009 ]\d{3})+([.,]\d+)?[^\d]*$/.test(raw)) return {n:NaN,kind:'number'};
    let s=raw.replace(/[\u00a0\u202f\u2009 ]/g,'');
    if(!s||s.length>40) return {n:NaN,kind:'number'};
    let kind='number', neg=false;
    if(/^\(.*\)$/.test(s)){neg=true;s=s.slice(1,-1);}
    if(/^[-\u2212]/.test(s)){neg=!neg;s=s.slice(1);}
    else if(s[0]==='+') s=s.slice(1);
    if(/^(€|eur|\$|usd|£|gbp)/i.test(s)){kind='currency';s=s.replace(/^(€|eur|\$|usd|£|gbp)/i,'');}
    if(/(€|eur|\$|usd|£|gbp)$/i.test(s)){kind='currency';s=s.replace(/(€|eur|\$|usd|£|gbp)$/i,'');}
    if(/%$/.test(s)){kind='percent';s=s.slice(0,-1);}
    if(/^[-\u2212]/.test(s)){neg=!neg;s=s.slice(1);}
    s=s.replace(/,-$/,'').replace(/\.-$/,'');
    if(!/^[0-9][0-9.,]*$|^[.,][0-9]+$/.test(s)) return {n:NaN,kind:'number'};
    const dots=(s.match(/\./g)||[]).length, commas=(s.match(/,/g)||[]).length;
    let norm;
    if(dots&&commas){
      // The last separator is the decimal one.
      if(s.lastIndexOf(',')>s.lastIndexOf('.')){
        if(!/^\d{1,3}(\.\d{3})*,\d+$/.test(s)) return {n:NaN,kind};
        norm=s.replace(/\./g,'').replace(',','.');
      } else {
        if(!/^\d{1,3}(,\d{3})*\.\d+$/.test(s)) return {n:NaN,kind};
        norm=s.replace(/,/g,'');
      }
    } else if(commas){
      if(commas>1){if(!/^\d{1,3}(,\d{3})+$/.test(s)) return {n:NaN,kind};norm=s.replace(/,/g,'');}
      else norm=s.replace(',','.');
    } else if(dots){
      if(dots>1){if(!/^\d{1,3}(\.\d{3})+$/.test(s)) return {n:NaN,kind};norm=s.replace(/\./g,'');}
      else if(/^[1-9]\d{0,2}\.\d{3}$/.test(s)) norm=s.replace('.','');
      else norm=s;
    } else norm=s;
    // Leading zeros mark codes and phone numbers, not amounts ("007", "0612345678").
    if(/^0\d/.test(norm)) return {n:NaN,kind:'number'};
    const n=Number(norm);
    return {n:Number.isFinite(n)?(neg?-n:n):NaN,kind};
  }
  const DATE_RE=/^\d{4}-\d{2}-\d{2}$/;

  // ── Small helpers ────────────────────────────────────────────────────────
  function isObj(v){return !!v&&typeof v==='object'&&!Array.isArray(v);}
  function str(v,max,warn,field){
    if(v==null) return '';
    let s=typeof v==='string'?v:(typeof v==='number'||typeof v==='boolean')?String(v):'';
    s=s.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g,'').trim();
    if(max&&s.length>max){if(warn&&field)warn('cut',field,max);s=s.slice(0,max-1).trimEnd()+'…';}
    return s;
  }
  function clampInt(v,min,max,dflt){const n=Math.round(Number(v));return Number.isFinite(n)?Math.max(min,Math.min(max,n)):dflt;}
  // "Bron: input van de gebruiker" tells the user nothing: only outside sources are shown.
function outsideSource(v){
  if(!v) return v;
  const t=String(v).toLowerCase();
  if(/\b(gebruiker|user|jij|jou|jouw|you|your|conversation|gesprek|chat|this chat|dit gesprek)\b/.test(t)&&!/https?:|\.(nl|com|org|eu|io)\b|cbs|rapport|report|productive|snelstart|twenty|attio|google|excel|sheet/.test(t)) return '';
  return v;
}
function base(spec,lang,kind,m,warnings,limits){
    const warn=(k,...a)=>warnings.push(m(k,...a));
    let title=str(spec.title,limits.title,warn,lang==='nl'?'De titel':'The title');
    if(!title){warn('noTitle');title=NAME[lang][kind];}
    return {
      title,
      subtitle:str(spec.subtitle,limits.subtitle,warn,lang==='nl'?'De ondertitel':'The subtitle'),
      source:outsideSource(str(spec.source,LIMITS.source,warn,lang==='nl'?'De bron':'The source')),
      example:spec.example===true,
    };
  }

  // ── table ────────────────────────────────────────────────────────────────
  function normalizeCell(v){
    if(v==null) return null;
    if(typeof v==='number') return Number.isFinite(v)?v:null;
    if(typeof v==='boolean') return v;
    if(typeof v==='string') return str(v,LIMITS.cell);
    return undefined;
  }
  function validateTable(spec,lang){
    const m=messenger(lang), errors=[], warnings=[];
    const warn=(k,...a)=>warnings.push(m(k,...a));
    const out=base(spec,lang,'table',m,warnings,LIMITS);
    let cols=Array.isArray(spec.columns)?spec.columns:null;
    if(!cols||!cols.length){errors.push(m('noColumns'));return {errors,warnings};}
    if(cols.length>LIMITS.columns){warn('manyColumns',cols.length,LIMITS.columns);cols=cols.slice(0,LIMITS.columns);}
    const columns=cols.map((c,i)=>{
      const o=isObj(c)?c:{label:c};
      const label=str(o.label!=null?o.label:(o.name!=null?o.name:o.title),LIMITS.label)||(lang==='nl'?'Kolom ':'Column ')+(i+1);
      let type=typeof o.type==='string'?o.type.trim().toLowerCase():'';
      if(type&&!COLUMN_TYPES.has(type)){warn('colType',label,type);type='';}
      const col={label,type,decimals:o.decimals==null?null:clampInt(o.decimals,0,2,null)};
      return col;
    });
    const want=columns.length;
    let rows=spec.rows;
    if(!Array.isArray(rows)){
      if(rows==null){warn('noRows');rows=[];}
      else{errors.push(m('noRows'));return {errors,warnings};}
    }
    if(rows.length>LIMITS.rows){warn('manyRows',rows.length,LIMITS.rows);rows=rows.slice(0,LIMITS.rows);}
    const outRows=[];
    let widthWarnings=0, cellWarned=false;
    rows.forEach((r,ri)=>{
      if(isObj(r)) r=columns.map(c=>Object.prototype.hasOwnProperty.call(r,c.label)?r[c.label]:null);
      if(!Array.isArray(r)){warn('rowNotList',ri+1);return;}
      if(r.length!==want){
        if(widthWarnings<3) warn('rowWidth',ri+1,r.length,want);
        widthWarnings++;
        r=r.slice(0,want);while(r.length<want)r.push(null);
      }
      outRows.push(r.map(v=>{const c=normalizeCell(v);if(c===undefined){if(!cellWarned){cellWarned=true;warn('cellValue',ri+1);}return null;}return c;}));
    });
    // Type per column: explicit, else read from the cells (90% rule).
    columns.forEach((col,ci)=>{
      const cells=outRows.map(r=>r[ci]).filter(v=>v!==null&&v!=='');
      if(!col.type){
        if(!cells.length){col.type='text';return;}
        let nums=0, cur=0, pct=0, dates=0;
        cells.forEach(v=>{
          if(typeof v==='number'){nums++;return;}
          if(typeof v==='string'&&DATE_RE.test(v)){dates++;return;}
          const p=parseNumber(v);
          if(Number.isFinite(p.n)){nums++;if(p.kind==='currency')cur++;if(p.kind==='percent')pct++;}
        });
        if(dates/cells.length>=0.9) col.type='date';
        else if(nums/cells.length>=0.9) col.type=cur>nums/2?'currency':pct>nums/2?'percent':'number';
        else col.type='text';
      }
      if(col.type==='number'||col.type==='currency'||col.type==='percent'){
        outRows.forEach(r=>{
          const v=r[ci];
          if(typeof v==='string'&&v!==''){const p=parseNumber(v);if(Number.isFinite(p.n))r[ci]=p.n;}
          else if(typeof v==='boolean') r[ci]=String(v);
        });
      } else {
        outRows.forEach(r=>{if(typeof r[ci]==='number'||typeof r[ci]==='boolean')r[ci]=String(r[ci]);});
      }
      if(col.type==='link') outRows.forEach(r=>{if(typeof r[ci]==='string'&&r[ci]&&!/^https:\/\/[^\s]+$/i.test(r[ci]))col.mixedLinks=true;});
    });
    let sort=null;
    if(isObj(spec.sort)){
      let ci=-1;
      if(typeof spec.sort.column==='number') ci=Math.round(spec.sort.column);
      else if(typeof spec.sort.column==='string') ci=columns.findIndex(c=>c.label.toLowerCase()===spec.sort.column.trim().toLowerCase());
      if(ci>=0&&ci<columns.length) sort={col:ci,dir:String(spec.sort.dir||'').toLowerCase()==='desc'?'desc':'asc'};
      else warn('sortColumn');
    }
    const tones={};
    if(isObj(spec.tones)){
      Object.keys(spec.tones).slice(0,LIMITS.tones).forEach(k=>{
        const t=String(spec.tones[k]||'').toLowerCase();
        if(TONES.has(t)) tones[str(k,LIMITS.cell).toLowerCase()]=t;
      });
    }
    return {errors,warnings,spec:Object.assign(out,{
      columns,rows:outRows,sort,
      total:spec.total===true,
      filter:typeof spec.filter==='boolean'?spec.filter:outRows.length>10,
      tones,
    })};
  }
  function csvSpec(text,lang){
    const parsed=parseCsv(text);
    const rows=parsed.rows.filter(r=>r.some(c=>String(c).trim()!==''));
    if(!rows.length) return null;
    return {title:NAME[pickLang(lang)].table,columns:rows[0],rows:rows.slice(1)};
  }

  // ── chart ────────────────────────────────────────────────────────────────
  function validateChart(spec,lang){
    const kinds=new Set();
    const m=messenger(lang), errors=[], warnings=[];
    const warn=(k,...a)=>warnings.push(m(k,...a));
    const out=base(spec,lang,'chart',m,warnings,LIMITS);
    let type=typeof spec.type==='string'?spec.type.trim().toLowerCase():'bar';
    if(type==='doughnut') type='donut';
    if(type==='horizontal'||type==='horizontalbar'||type==='barh') type='hbar';
    if(type==='spider'||type==='web'||type==='spin'||type==='spinneweb') type='radar';
    if(!CHART_TYPES.has(type)){warn('chartType',type);type='bar';}
    const round=type==='pie'||type==='donut';
    let labels=Array.isArray(spec.labels)?spec.labels.map(l=>str(l,LIMITS.label)):null;
    let seriesIn=Array.isArray(spec.series)?spec.series:null;
    if(!seriesIn&&Array.isArray(spec.data)) seriesIn=[{name:out.title,data:spec.data}];
    if(!seriesIn&&Array.isArray(spec.values)) seriesIn=[{name:out.title,data:spec.values}];
    if(!labels||!labels.length){errors.push(m('noLabels'));return {errors,warnings};}
    if(!round&&labels.length>LIMITS.chartLabels){warn('manyLabels',labels.length,LIMITS.chartLabels);labels=labels.slice(0,LIMITS.chartLabels);}
    if(!seriesIn||!seriesIn.length){errors.push(m('noSeries'));return {errors,warnings};}
    if(round&&seriesIn.length>1){warn('pieOne');seriesIn=seriesIn.slice(0,1);}
    if(seriesIn.length>LIMITS.series){warn('manySeries',seriesIn.length,LIMITS.series);seriesIn=seriesIn.slice(0,LIMITS.series);}
    const want=labels.length;
    let series=seriesIn.map((s,si)=>{
      const o=isObj(s)?s:{data:s};
      const name=str(o.name!=null?o.name:o.label,LIMITS.seriesName)||(lang==='nl'?'Reeks ':'Series ')+(si+1);
      let data=Array.isArray(o.data)?o.data:Array.isArray(o.values)?o.values:[];
      if(data.length!==want){warn('seriesLength',name,data.length,want);data=data.slice(0,want);while(data.length<want)data.push(null);}
      let bad=false;
      data=data.map(v=>{
        if(v==null) return null;
        const p=parseNumber(v);
        if(!Number.isFinite(p.n)){bad=true;return null;}
        kinds.add(typeof v==='number'?'plain':p.kind);
        return p.n;
      });
      if(bad) warn('seriesValue',name);
      return {name,data};
    }).filter(s=>s.data.some(v=>v!==null));
    if(!series.length){errors.push(m('noSeries'));return {errors,warnings};}
    if(round){
      const s=series[0];
      if(s.data.some(v=>v!==null&&v<0)){warn('pieNegative');s.data=s.data.map(v=>v!==null&&v<0?0:v);}
      if(labels.length>LIMITS.pieLabels){
        warn('pieOther',LIMITS.pieLabels);
        const keep=LIMITS.pieLabels-1;
        const rest=s.data.slice(keep).reduce((a,v)=>a+(v||0),0);
        labels=labels.slice(0,keep).concat([lang==='nl'?'Overig':'Other']);
        s.data=s.data.slice(0,keep).concat([rest]);
      }
    }
    // Amounts written as "€ 12.500" or "12,5%" keep their unit when the format is missing.
    const inferred=kinds.size===1&&(kinds.has('currency')||kinds.has('percent'))?[...kinds][0]:'number';
    let format=typeof spec.format==='string'?spec.format.trim().toLowerCase():inferred;
    if(format==='euro'||format==='eur') format='currency';
    if(!['number','currency','percent'].includes(format)) format='number';
    let highlight='';
    if(spec.highlight!=null&&spec.highlight!==''){
      const h=str(spec.highlight,LIMITS.label);
      const hit=labels.find(l=>l.toLowerCase()===h.toLowerCase())||series.map(s=>s.name).find(n=>n.toLowerCase()===h.toLowerCase());
      if(hit) highlight=hit;else warn('highlight',h);
    }
    let target=null;
    if(isObj(spec.target)||typeof spec.target==='number'){
      const t=isObj(spec.target)?spec.target:{value:spec.target};
      const p=parseNumber(t.value);
      if(Number.isFinite(p.n)&&!round) target={value:p.n,label:str(t.label,40)};
      else if(!round) warn('target');
    }
    // A radar needs at least three axes to be a shape; with fewer it is a bar chart.
    if(type==='radar'&&labels.length<3) type='bar';
    if(type==='radar'&&target) target=null;
    const height=spec.height==null?(type==='hbar'?Math.max(220,Math.min(480,60+labels.length*28*Math.max(1,series.length*0.6))):type==='radar'?340:300):clampInt(spec.height,180,480,300);
    return {errors,warnings,spec:Object.assign(out,{
      type,labels,series,format,
      decimals:spec.decimals==null?null:clampInt(spec.decimals,0,2,null),
      highlight,target,
      xLabel:str(spec.xLabel,40),yLabel:str(spec.yLabel,40),
      max:type==='radar'&&Number.isFinite(Number(spec.max))&&Number(spec.max)>0?Number(spec.max):null,
      height:Math.round(height),
    })};
  }

  // ── map ──────────────────────────────────────────────────────────────────
  function coordsOk(lat,lng){return Number.isFinite(lat)&&Number.isFinite(lng)&&Math.abs(lat)<=90&&Math.abs(lng)<=180;}
  function toNum(v){if(typeof v==='number')return v;if(typeof v==='string'&&v.trim()!==''){const n=Number(v.trim().replace(',','.'));return n;}return NaN;}
  function validateMap(spec,lang){
    const m=messenger(lang), errors=[], warnings=[];
    const warn=(k,...a)=>warnings.push(m(k,...a));
    const out=base(spec,lang,'map',m,warnings,{title:LIMITS.mapTitle,subtitle:LIMITS.mapSubtitle});
    let kind=typeof spec.kind==='string'?spec.kind.trim().toLowerCase():(spec.route===true?'route':'places');
    if(kind!=='places'&&kind!=='route'){warn('mapKind',kind);kind='places';}
    let region=Array.isArray(spec.region)?spec.region:(typeof spec.region==='string'?[spec.region]:['nl']);
    region=region.map(r=>String(r||'').trim().toLowerCase()).filter(r=>/^[a-z]{2}$/.test(r)).slice(0,5);
    if(!region.length) region=['nl'];
    let places=Array.isArray(spec.places)?spec.places:(Array.isArray(spec.stops)?spec.stops:null);
    if(!places||!places.length){errors.push(m('noPlaces'));return {errors,warnings};}
    if(places.length>LIMITS.places){warn('manyPlaces',places.length,LIMITS.places);places=places.slice(0,LIMITS.places);}
    const cats=[];
    let catWarned=false;
    const outPlaces=[];
    places.forEach((p,i)=>{
      if(!isObj(p)){warn('placeName',i+1);return;}
      const name=str(p.name!=null?p.name:p.title,LIMITS.placeName);
      if(!name){warn('placeName',i+1);return;}
      const place={k:String(outPlaces.length),n:outPlaces.length+1,name,
        address:str(p.address,LIMITS.address),time:str(p.time,LIMITS.time),note:str(p.note,LIMITS.note),
        category:str(p.category,LIMITS.category),wiki:'',url:'',lat:null,lng:null};
      let lat=toNum(p.lat!=null?p.lat:p.latitude), lng=toNum(p.lng!=null?p.lng:(p.lon!=null?p.lon:p.longitude));
      const hasLat=p.lat!=null||p.latitude!=null, hasLng=p.lng!=null||p.lon!=null||p.longitude!=null;
      if(hasLat||hasLng){
        if(coordsOk(lat,lng)){
          // A Dutch or Belgian place written as (lng, lat) lands in the Gulf of Guinea.
          if(lat>=2.5&&lat<=7.5&&lng>=49&&lng<=54&&region.some(r=>r==='nl'||r==='be'||r==='lu')){warn('placeSwap',name);const t=lat;lat=lng;lng=t;}
          place.lat=lat;place.lng=lng;
        } else warn('placeCoords',name);
      }
      if(p.wiki!=null&&p.wiki!==''){
        const w=/^([a-z]{2}):(.{1,160})$/.exec(String(p.wiki).trim());
        if(w&&WIKI_LANGS.has(w[1])&&!/[\u0000-\u001f<>\[\]{}|#]/.test(w[2])) place.wiki=w[1]+':'+w[2].trim();
        else warn('placeWiki',name);
      }
      if(p.url!=null&&p.url!==''){
        const u=String(p.url).trim();
        if(/^https:\/\/[^\s<>"']{1,500}$/i.test(u)) place.url=u;else warn('placeUrl',name);
      }
      if(place.category){
        if(!cats.includes(place.category)){
          if(cats.length<LIMITS.categories) cats.push(place.category);
          else {if(!catWarned){catWarned=true;warn('categories',LIMITS.categories);}place.category='';}
        }
      }
      outPlaces.push(place);
    });
    if(!outPlaces.length){errors.push(m('noPlaces'));return {errors,warnings};}
    if(kind==='route'&&outPlaces.length<2){warn('routeShort');kind='places';}
    return {errors,warnings,spec:Object.assign(out,{kind,region,photos:spec.photos===true,places:outPlaces,categories:cats})};
  }

  // ── kpi ──────────────────────────────────────────────────────────────────
  function fieldName(lang,nl,en){return lang==='nl'?nl:en;}
  function kpiNumber(v){
    if(typeof v==='number') return Number.isFinite(v)?{n:v,kind:''}:null;
    if(typeof v!=='string'||!v.trim()) return null;
    const p=parseNumber(v);
    return Number.isFinite(p.n)?{n:p.n,kind:p.kind==='number'?'':p.kind}:null;
  }
  // Which way the change points and whether that is good news.
  function kpiTone(delta,good){
    if(delta===null||delta===undefined) return '';
    if(delta===0) return 'flat';
    return (delta>0)===(good!=='down')?'good':'bad';
  }
  function validateKpi(spec,lang){
    const m=messenger(lang), errors=[], warnings=[];
    const warn=(k,...a)=>warnings.push(m(k,...a));
    const out=base(spec,lang,'kpi',m,warnings,LIMITS);
    let items=Array.isArray(spec.items)?spec.items:(Array.isArray(spec.metrics)?spec.metrics:null);
    if(!items||!items.length){errors.push(m('kpiNoItems'));return {errors,warnings};}
    if(items.length>LIMITS.kpiItems){warn('kpiMany',items.length,LIMITS.kpiItems);items=items.slice(0,LIMITS.kpiItems);}
    const outItems=[];
    items.forEach((it,i)=>{
      if(!isObj(it)){warn('kpiItem',i+1);return;}
      const label=str(it.label!=null?it.label:(it.name!=null?it.name:it.title),LIMITS.kpiLabel,warn,fieldName(lang,`Het label van cijfer ${i+1}`,`The label of figure ${i+1}`));
      if(!label){warn('kpiLabel',i+1);return;}
      const v=kpiNumber(it.value);
      if(!v){warn('kpiValue',label);return;}
      let format=typeof it.format==='string'?it.format.trim().toLowerCase():'';
      if(format&&!KPI_FORMATS[format]){warn('kpiFormat',label,it.format);format='';}
      format=format?KPI_FORMATS[format]:(v.kind||'number');
      let delta=null;
      if(it.delta!=null&&it.delta!==''){const d=kpiNumber(it.delta);if(d)delta=d.n;else warn('kpiDelta',label);}
      let deltaFormat=typeof it.deltaFormat==='string'?it.deltaFormat.trim().toLowerCase():'';
      if(deltaFormat&&!DELTA_FORMATS[deltaFormat]){warn('kpiDeltaFormat',label,it.deltaFormat);deltaFormat='';}
      // A percentage moves in points by default; anything else in percent.
      deltaFormat=deltaFormat?DELTA_FORMATS[deltaFormat]:(format==='percent'?'number':'percent');
      const goodRaw=it.good!=null?it.good:it.better;
      let good='up';
      if(goodRaw!=null&&goodRaw!==''){const g=GOOD_DIRS[String(goodRaw).trim().toLowerCase()];if(g)good=g;else warn('kpiGood',label,str(goodRaw,20));}
      let target=null;
      if(it.target!=null&&it.target!==''){const t=kpiNumber(it.target);if(t&&t.n>0)target=t.n;else warn('kpiTarget',label);}
      const item={label,value:v.n,format,decimals:it.decimals==null?null:clampInt(it.decimals,0,2,null),
        delta,deltaFormat,good,target,note:str(it.note,LIMITS.kpiNote,warn,fieldName(lang,`De notitie van "${label}"`,`The note of "${label}"`)),
        tone:kpiTone(delta,good)};
      if(target!==null){
        item.progress=Math.max(0,Math.min(1,v.n/target));
        item.met=good==='down'?v.n<=target:v.n>=target;
        // A cost or churn figure above its target is an overrun, not a goal reached.
        item.over=good==='down'&&v.n>target;
      }
      outItems.push(item);
    });
    if(!outItems.length){errors.push(m('kpiNone'));return {errors,warnings};}
    return {errors,warnings,spec:Object.assign(out,{items:outItems})};
  }
  const kpiFormatters=new Map();
  function kpiFormatter(lang,key,opts){
    const l=pickLang(lang)==='nl'?'nl-NL':'en-GB', k=l+'|'+key;
    let f=kpiFormatters.get(k);
    if(!f){f=new Intl.NumberFormat(l,opts);kpiFormatters.set(k,f);}
    return f;
  }
  function autoDecimals(v,decimals){return decimals!=null?decimals:(Number.isInteger(v)?0:Math.min(2,Math.max(1,(String(v).split('.')[1]||'').length)));}
  // The big number on a tile: millions are written short ("1,2 mln").
  function kpiValueText(item,lang){
    const v=item.value;
    if(Math.abs(v)>=1e6&&item.decimals==null&&item.format!=='percent'){
      // Two decimals so value, percentage and target agree ("1,25 mln." against "1,5 mln.").
      const o={notation:'compact',compactDisplay:'short',minimumFractionDigits:0,maximumFractionDigits:2};
      if(item.format==='currency'){o.style='currency';o.currency='EUR';}
      return kpiFormatter(lang,'c|'+item.format,o).format(v);
    }
    return formatValue(v,item.format,item.decimals,lang);
  }
  // The change with its sign: "+12,5%", "+€ 1.200", "-0,4 pp".
  function kpiDeltaText(item,lang){
    const d=item.delta;
    if(d===null||d===undefined) return '';
    // The change keeps its own precision: 0,4 procentpunt must not round to 0.
    const dec=autoDecimals(d,item.deltaDecimals!=null?item.deltaDecimals:null);
    const o={signDisplay:'exceptZero',minimumFractionDigits:dec,maximumFractionDigits:dec};
    if(item.deltaFormat==='percent') return kpiFormatter(lang,'dp'+dec,Object.assign({style:'percent'},o)).format(d/100);
    if(item.format==='currency') return kpiFormatter(lang,'dc'+dec,Object.assign({style:'currency',currency:'EUR'},o)).format(d);
    const text=kpiFormatter(lang,'dn'+dec,o).format(d);
    return item.format==='percent'?text+(pickLang(lang)==='nl'?' procentpunt':' pts'):text;
  }

  // ── timeline ─────────────────────────────────────────────────────────────
  // Dates are whole days since 1970-01-01 (UTC), so a plan never shifts with
  // the browser's time zone. A bar runs from the start of its first day (or
  // unit) to the end of its last: end is included.
  const DAY_MS=864e5;
  function dayOf(iso){
    if(typeof iso!=='string'||!DATE_RE.test(iso.trim())) return NaN;
    const [y,mo,d]=iso.trim().split('-').map(Number);
    const t=Date.UTC(y,mo-1,d), dt=new Date(t);
    if(dt.getUTCFullYear()!==y||dt.getUTCMonth()!==mo-1||dt.getUTCDate()!==d) return NaN;
    return Math.round(t/DAY_MS);
  }
  function isoOf(day){return new Date(Math.round(day)*DAY_MS).toISOString().slice(0,10);}
  function addMonths(day,n){
    const d=new Date(day*DAY_MS), y=d.getUTCFullYear(), mo=d.getUTCMonth()+n;
    const last=new Date(Date.UTC(y,mo+1,0)).getUTCDate();
    return Math.round(Date.UTC(y,mo,Math.min(d.getUTCDate(),last))/DAY_MS);
  }
  function unitDay(baseDay,unit,n){
    const whole=Math.floor(n), frac=n-whole;
    const at=k=>unit==='day'?baseDay+k:unit==='week'?baseDay+7*k:addMonths(baseDay,k);
    const a=at(whole);
    return frac?a+frac*(at(whole+1)-a):a;
  }
  function monday(day){return day-(((day+3)%7)+7)%7;}
  // A position: a unit number ({n}) or a date ({d}, a YYYY-MM month also counts).
  function readPos(v){
    if(typeof v==='number') return Number.isFinite(v)&&v>=0&&v<=LIMITS.tlMaxUnit?{n:v}:null;
    if(typeof v!=='string') return null;
    const s=v.trim();
    if(/^\d+(\.\d+)?$/.test(s)){const n=Number(s);return n<=LIMITS.tlMaxUnit?{n}:null;}
    if(DATE_RE.test(s)){const d=dayOf(s);return Number.isFinite(d)?{d}:null;}
    const mm=/^(\d{4})-(\d{2})$/.exec(s);
    if(mm&&+mm[2]>=1&&+mm[2]<=12) return {d:Math.round(Date.UTC(+mm[1],+mm[2]-1,1)/DAY_MS),last:Math.round(Date.UTC(+mm[1],+mm[2],0)/DAY_MS)};
    return null;
  }
  function validateTimeline(spec,lang){
    const m=messenger(lang), errors=[], warnings=[];
    const warn=(k,...a)=>warnings.push(m(k,...a));
    const out=base(spec,lang,'timeline',m,warnings,LIMITS);
    let unit='week';
    if(spec.unit!=null&&spec.unit!==''){const u=TL_UNITS[String(spec.unit).trim().toLowerCase()];if(u)unit=u;else warn('tlUnit',str(spec.unit,20));}
    let baseDay=NaN;
    if(spec.start!=null&&spec.start!==''){const p=readPos(spec.start);if(p&&p.d!=null)baseDay=p.d;else warn('tlStart');}
    let items=Array.isArray(spec.items)?spec.items:(Array.isArray(spec.tasks)?spec.tasks:null);
    if(!items||!items.length){errors.push(m('tlNoItems'));return {errors,warnings};}
    if(items.length>LIMITS.tlItems){warn('tlMany',items.length,LIMITS.tlItems);items=items.slice(0,LIMITS.tlItems);}
    const raw=[];
    items.forEach((it,i)=>{
      if(!isObj(it)){warn('tlItem',i+1);return;}
      const label=str(it.label!=null?it.label:(it.title!=null?it.title:it.name),LIMITS.tlLabel,warn,fieldName(lang,`Het label van onderdeel ${i+1}`,`The label of item ${i+1}`));
      if(!label){warn('tlLabel',i+1);return;}
      let sp=readPos(it.start!=null?it.start:it.date);
      if(!sp){warn('tlBadStart',label);return;}
      let ms=it.milestone===true, ep=null;
      if(!ms){
        ep=it.end!=null&&it.end!==''?readPos(it.end):null;
        if(!ep){warn('tlNoEnd',label);ms=true;}
      }
      let status='';
      if(it.status!=null&&it.status!==''){
        const st=TL_STATUS[String(it.status).trim().toLowerCase()];
        if(st) status=st;else{warn('tlStatus',label,str(it.status,30));status='todo';}
      }
      raw.push({label,sp,ep,ms,status,
        owner:str(it.owner,LIMITS.tlOwner,warn,fieldName(lang,`De eigenaar van "${label}"`,`The owner of "${label}"`)),
        note:str(it.note,LIMITS.tlNote,warn,fieldName(lang,`De notitie van "${label}"`,`The note of "${label}"`))});
    });
    if(!raw.length){errors.push(m('tlNone'));return {errors,warnings};}
    const nums=[], dates=[];
    raw.forEach(r=>[r.sp,r.ep].forEach(p=>{if(p){if(p.n!=null)nums.push(p.n);else dates.push(p.d);}}));
    let todayPos=null;
    if(spec.today!=null&&spec.today!==''){todayPos=readPos(spec.today);if(!todayPos)warn('tlToday');}
    const dateMode=Number.isFinite(baseDay)||dates.length>0;
    if(dateMode&&!Number.isFinite(baseDay)&&(nums.length||(todayPos&&todayPos.n!=null))){
      baseDay=Math.min(...dates);
      warn('tlNoBase',isoOf(baseDay));
    }
    // Unit numbers count from 1 ("week 1" is the first week) unless the block uses 0.
    const first=nums.concat(todayPos&&todayPos.n!=null?[todayPos.n]:[]).some(n=>n<1)?0:1;
    const startOf=p=>p.n!=null?(dateMode?unitDay(baseDay,unit,p.n-first):p.n):p.d;
    const endOf=p=>p.n!=null?(dateMode?unitDay(baseDay,unit,p.n+1-first):p.n+1):(p.last!=null?p.last:p.d)+1;
    const midOf=p=>p.n!=null?(startOf(p)+(dateMode?unitDay(baseDay,unit,p.n+1-first):p.n+1))/2:p.d+0.5;
    const outItems=raw.map((r,i)=>{
      const item={k:String(i),label:r.label,owner:r.owner,status:r.status,note:r.note,milestone:r.ms};
      let sp=r.sp, ep=r.ep;
      if(r.ms){
        item.s=item.e=midOf(sp);
      } else {
        if(startOf(ep)<startOf(sp)){warn('tlSwap',r.label);const t=sp;sp=ep;ep=t;}
        item.s=startOf(sp);item.e=Math.max(endOf(ep),item.s);
      }
      if(dateMode){
        item.from=isoOf(startOf(sp));
        item.to=r.ms?item.from:isoOf(Math.ceil(item.e)-1);
      } else {item.from=sp.n;item.to=r.ms?sp.n:ep.n;}
      return item;
    });
    let today=null;
    if(todayPos){
      if(todayPos.d!=null&&!dateMode) warn('tlTodayDate');
      else today=midOf(todayPos);
    }
    return {errors,warnings,spec:Object.assign(out,{unit,mode:dateMode?'date':'index',
      start:Number.isFinite(baseDay)?isoOf(baseDay):'',first,today,todayAuto:dateMode&&(spec.today==null||spec.today===''),items:outItems})};
  }
  const dateFormatters=new Map();
  function dayText(day,lang,opts){
    const l=pickLang(lang)==='nl'?'nl-NL':'en-GB', key=l+JSON.stringify(opts);
    let f=dateFormatters.get(key);
    if(!f){f=new Intl.DateTimeFormat(l,Object.assign({timeZone:'UTC'},opts));dateFormatters.set(key,f);}
    return f.format(new Date(Math.round(day)*DAY_MS));
  }
  function unitWord(unit,lang,plural){return UNIT_WORDS[pickLang(lang)][unit][plural?1:0];}
  // "9 nov t/m 20 nov 2026", "Week 2 t/m 5" (or "9 Nov to 20 Nov 2026", "Weeks 2 to 5").
  function timelinePeriod(spec,item,lang){
    const nl=pickLang(lang)==='nl', through=nl?' t/m ':' to ';
    if(spec.mode==='date'){
      const a=dayOf(item.from), b=dayOf(item.to);
      if(a===b) return dayText(a,lang,{day:'numeric',month:'short',year:'numeric'});
      const sameYear=item.from.slice(0,4)===item.to.slice(0,4);
      return dayText(a,lang,sameYear?{day:'numeric',month:'short'}:{day:'numeric',month:'short',year:'numeric'})+through+dayText(b,lang,{day:'numeric',month:'short',year:'numeric'});
    }
    const num=n=>formatValue(n,'number',null,lang);
    if(item.from===item.to) return unitWord(spec.unit,lang,false)+' '+num(item.from);
    return unitWord(spec.unit,lang,!nl)+' '+num(item.from)+through+num(item.to);
  }
  function statusWord(status,lang){return status?STATUS_WORDS[pickLang(lang)][status]||'':'';}
  // The visible range, the ticks (x from 0 to 1) and where today falls.
  // nowDay is the local date (days since 1970) for a plan without "today".
  function timelineAxis(spec,lang,nowDay){
    let min=Math.min(...spec.items.map(i=>i.s)), max=Math.max(...spec.items.map(i=>i.e));
    const ticks=[];
    let bounds=[];
    if(spec.mode==='date'){
      const baseDay=dayOf(spec.start);
      if(spec.unit==='month'){
        const d0=new Date(Math.floor(min)*DAY_MS);
        let at=Math.round(Date.UTC(d0.getUTCFullYear(),d0.getUTCMonth(),1)/DAY_MS);
        while(bounds.length<240){bounds.push(at);if(at>=max&&bounds.length>1)break;at=addMonths(at,1);}
      } else {
        const len=spec.unit==='week'?7:1;
        const anchor=spec.unit==='week'?(Number.isFinite(baseDay)?baseDay:monday(Math.floor(min))):0;
        let at=anchor+len*Math.floor((Math.floor(min)-anchor)/len);
        while(bounds.length<800){bounds.push(at);if(at>=max&&bounds.length>1)break;at+=len;}
      }
    } else {
      for(let k=Math.floor(min);bounds.length<800;k++){bounds.push(k);if(k>=max&&bounds.length>1)break;}
    }
    min=bounds[0];max=bounds[bounds.length-1];
    const span=Math.max(1e-9,max-min), cells=bounds.length-1;
    const step=Math.max(1,Math.ceil(cells/LIMITS.tlTicks));
    let prevYear='';
    for(let i=0;i<cells;i+=step){
      const at=bounds[i];
      let label;
      if(spec.mode==='date'){
        if(spec.unit==='month'){
          const y=isoOf(at).slice(0,4);
          label=dayText(at,lang,y!==prevYear?{month:'short',year:'numeric'}:{month:'short'});
          prevYear=y;
        } else label=dayText(at,lang,{day:'numeric',month:'short'});
      } else {
        const n=formatValue(at,'number',null,lang);
        label=i===0||cells<=8?unitWord(spec.unit,lang,false)+' '+n:n;
      }
      ticks.push({x:(at-min)/span,label,minor:false});
    }
    if(ticks.length>7) ticks.forEach((t,i)=>{t.minor=i%2===1;});
    let today=spec.today;
    if(today===null&&spec.todayAuto&&Number.isFinite(nowDay)) today=nowDay;
    const todayX=today!==null&&today>=min&&today<=max?(today-min)/span:null;
    return {min,max,ticks,todayX,lines:bounds.slice(1,-1).map(b=>(b-min)/span)};
  }

  // ── Extra kinds ──────────────────────────────────────────────────────────
  // A kind in its own file (static/interactive-ui/kinds/*.js) registers here:
  // register(kind, {fences:[...], name:{nl,en}, noun:{nl,en}, icon, streamHeight,
  //   validate(raw, lang, helpers) -> {errors, warnings, spec}, estHeight(spec), table(spec)}).
  // The same file registers its renderer with SWKitRender inside the kit frame.
  const EXTRA={};
  function register(kind,def){
    if(!/^[a-z][a-z-]{1,20}$/.test(kind)||!def||typeof def.validate!=='function'||EXTRA[kind]||KIT_LANGS[kind]) return false;
    EXTRA[kind]=def;
    [kind].concat(Array.isArray(def.fences)?def.fences:[]).forEach(f=>{f=String(f).toLowerCase();if(/^[a-z][a-z-]{1,20}$/.test(f)&&!KIT_LANGS[f]||KIT_LANGS[f]===kind)KIT_LANGS[f]=kind;});
    ['nl','en'].forEach(l=>{
      if(def.noun&&def.noun[l]) NOUN[l][kind]=String(def.noun[l]);
      if(def.name&&def.name[l]) NAME[l][kind]=String(def.name[l]);
    });
    return true;
  }
  function extra(kind){return Object.prototype.hasOwnProperty.call(EXTRA,kind)?EXTRA[kind]:null;}
  // What a kind file may use to validate.
  function helpers(lang){
    const m=messenger(lang);
    return {m,str,isObj,clampInt,parseNumber,kpiNumber,base:(spec,kind,warnings)=>base(spec,lang,kind,m,warnings,LIMITS),
      fieldName:(nl,en)=>fieldName(lang,nl,en),pickLang,LIMITS,formatValue};
  }

  // ── Entry point ──────────────────────────────────────────────────────────
  function estHeight(kind,spec){
    if(!spec) return 120;
    const x=extra(kind);
    if(x){try{return Math.max(80,Math.min(2000,Math.round(Number(x.estHeight?x.estHeight(spec):300))||300));}catch(_){return 300;}}
    if(kind==='table'){
      const shown=Math.min(spec.rows.length,50);
      return Math.round(28+(spec.subtitle?24:0)+(spec.filter?48:0)+Math.min(440,42+Math.max(1,shown)*37+(spec.total?37:0))+(spec.rows.length>50?48:0)+(spec.source?28:0));
    }
    if(kind==='chart') return Math.round(spec.height+(spec.subtitle?24:0)+76+(spec.source?28:0)+(spec.type==='pie'||spec.type==='donut'?Math.ceil(spec.labels.length/2)*26:0));
    if(kind==='map') return 460;
    if(kind==='kpi'){
      // Four tiles to a row in a chat column; the frame reports its real height.
      const rows=Math.ceil(spec.items.length/4);
      const tile=88+(spec.items.some(i=>i.note)?20:0)+(spec.items.some(i=>i.target!==null)?28:0);
      return Math.round(24+(spec.subtitle?24:0)+rows*tile+(rows-1)*10+(spec.source?28:0));
    }
    if(kind==='timeline') return Math.round(24+(spec.subtitle?24:0)+34+30+spec.items.length*38+40+(spec.source?28:0));
    return 300;
  }
  // build(kind, text, {lang, fence}) -> {spec, title, errors, warnings, estHeight}
  function build(kind,text,opts){
    let lang=pickLang(opts&&opts.lang);
    let m=messenger(lang);
    const fence=String(opts&&opts.fence||'').toLowerCase();
    const src=String(text==null?'':text);
    const res={spec:null,title:'',errors:[],warnings:[],estHeight:120,kind};
    if(src.length>LIMITS.specBytes){res.errors.push(m('tooBig'));return res;}
    let raw;
    if(fence==='csv'){
      raw=csvSpec(src,lang);
      if(!raw){res.errors.push(m('csvEmpty'));return res;}
    } else {
      const parsed=parseKit(src);
      if(!parsed.ok){res.errors.push(m('json',parsed.line));return res;}
      raw=parsed.value;
      if(!isObj(raw)){res.errors.push(m('notObject'));return res;}
    }
    // The block may name the conversation language; it sets labels and number format.
    const own=String(raw&&raw.lang||'').toLowerCase();
    if(own==='nl'||own==='en'){lang=own;m=messenger(lang);}
    const x=extra(kind);
    const fn=x?((raw,l)=>x.validate(raw,l,helpers(l))):({table:validateTable,chart:validateChart,map:validateMap,kpi:validateKpi,timeline:validateTimeline}[kind]||null);
    if(!fn){res.errors.push(m('notObject'));return res;}
    let r;
    try{r=fn(raw,lang)||{errors:[m('notObject')],warnings:[]};}catch(err){r={errors:[m('notObject')],warnings:[]};}
    r.errors=Array.isArray(r.errors)?r.errors:[];r.warnings=Array.isArray(r.warnings)?r.warnings:[];
    res.errors=r.errors;res.warnings=r.warnings;
    if(r.spec&&!r.errors.length){r.spec.lang=lang;res.spec=r.spec;res.title=r.spec.title;res.estHeight=estHeight(kind,r.spec);}
    else res.title=str(raw&&raw.title,LIMITS.title);
    return res;
  }
  // The title of a block that is still streaming.
  function streamingTitle(text){
    const mt=/"title"\s*:\s*"((?:[^"\\]|\\.){1,120})"/.exec(String(text||''));
    if(!mt) return '';
    try{return JSON.parse('"'+mt[1]+'"').slice(0,120);}catch(_){return mt[1].slice(0,120);}
  }

  // ── Sorting, filtering and display text (shared by the frame and exports) ─
  const collators={};
  function collator(lang){const l=pickLang(lang);return collators[l]||(collators[l]=new Intl.Collator(l==='nl'?'nl':'en',{numeric:true,sensitivity:'base'}));}
  function compareCells(a,b,type,lang){
    const ea=a===null||a===''||a===undefined, eb=b===null||b===''||b===undefined;
    if(ea||eb) return ea&&eb?0:ea?1:-1;
    if(typeof a==='number'&&typeof b==='number') return a-b;
    if(typeof a==='number') return -1;
    if(typeof b==='number') return 1;
    return collator(lang).compare(String(a),String(b));
  }
  const formatters=new Map();
  function numberFormat(lang,type,decimals,value){
    const l=pickLang(lang)==='nl'?'nl-NL':'en-GB';
    const auto=decimals==null;
    const frac=auto?(Number.isInteger(value)?0:Math.min(2,Math.max(1,(String(value).split('.')[1]||'').length))):decimals;
    let min=frac, max=frac;
    if(type==='currency'&&auto&&frac>0){min=2;max=2;}
    const key=l+'|'+type+'|'+min+'|'+max;
    let f=formatters.get(key);
    if(!f){
      const o={minimumFractionDigits:min,maximumFractionDigits:max};
      if(type==='currency'){o.style='currency';o.currency='EUR';}
      else if(type==='percent') o.style='percent';
      f=new Intl.NumberFormat(l,o);
      formatters.set(key,f);
    }
    return f;
  }
  function formatValue(value,type,decimals,lang){
    if(value===null||value===undefined||value==='') return '';
    if(typeof value==='number'){
      if(type==='percent') return numberFormat(lang,'percent',decimals,value).format(value/100);
      return numberFormat(lang,type==='currency'?'currency':'number',decimals,value).format(value);
    }
    if(type==='date'&&typeof value==='string'&&DATE_RE.test(value)){
      const d=new Date(value+'T12:00:00Z');
      if(!isNaN(d)) return new Intl.DateTimeFormat(pickLang(lang)==='nl'?'nl-NL':'en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(d);
    }
    return String(value);
  }
  // Row indices for the current view: filter text, then sort (or the original order).
  function viewIndices(spec,view,lang){
    const q=String(view&&view.q||'').trim().toLowerCase();
    let idx=spec.rows.map((_,i)=>i);
    if(q){
      idx=idx.filter(i=>spec.rows[i].some((v,ci)=>{
        if(v===null||v===undefined) return false;
        const col=spec.columns[ci]||{};
        return String(v).toLowerCase().includes(q)||formatValue(v,col.type,col.decimals,lang).toLowerCase().includes(q);
      }));
    }
    const s=view&&Array.isArray(view.s)?{col:view.s[0],dir:view.s[1]}:null;
    if(s&&s.col>=0&&s.col<spec.columns.length&&(s.dir==='asc'||s.dir==='desc')){
      const type=spec.columns[s.col].type;
      const empty=v=>v===null||v===''||v===undefined;
      idx.sort((a,b)=>{
        const va=spec.rows[a][s.col], vb=spec.rows[b][s.col];
        // Empty cells stay at the bottom in both directions.
        if(empty(va)||empty(vb)) return (empty(va)-empty(vb))||a-b;
        const c=compareCells(va,vb,type,lang);
        return (s.dir==='desc'?-c:c)||a-b;
      });
    }
    return idx;
  }
  function initialView(spec){return {s:spec.sort?[spec.sort.col,spec.sort.dir]:null,q:'',all:false};}
  function totals(spec,idx){
    return spec.columns.map((c,ci)=>{
      if(c.type!=='number'&&c.type!=='currency') return null;
      let sum=0, any=false;
      idx.forEach(i=>{const v=spec.rows[i][ci];if(typeof v==='number'){sum+=v;any=true;}});
      return any?Math.round(sum*1e6)/1e6:null;
    });
  }

  // ── Export (CSV for Dutch Excel and TSV for pasting) ─────────────────────
  // kitTable(kind, spec, view, data) -> {header:[...], rows:[[...]]} with raw values.
  function kitTable(kind,spec,view,data){
    if(!spec) return {header:[],rows:[]};
    if(kind==='table'){
      const idx=viewIndices(spec,view||initialView(spec));
      return {header:spec.columns.map(c=>c.label),rows:idx.map(i=>spec.rows[i]),types:spec.columns.map(c=>c.type)};
    }
    if(kind==='chart'){
      const en=spec.lang==='en';
      return {header:[en?'Label':'Categorie'].concat(spec.series.map(s=>s.name)),
        rows:spec.labels.map((l,i)=>[l].concat(spec.series.map(s=>s.data[i]))),
        types:['text'].concat(spec.series.map(()=>spec.format))};
    }
    if(kind==='map'){
      const byK={};
      ((data&&data.places)||[]).forEach(p=>{if(p&&typeof p.k==='string')byK[p.k]=p;});
      const en=spec.lang==='en';
      return {header:en?['No.','Name','Address','Time','Note','Latitude','Longitude']:['Nr','Naam','Adres','Tijd','Notitie','Breedtegraad','Lengtegraad'],
        rows:spec.places.map(p=>{
          const r=byK[p.k]||{};
          const lat=Number.isFinite(r.lat)?r.lat:p.lat, lng=Number.isFinite(r.lng)?r.lng:p.lng;
          return [p.n,p.name,p.address||r.label||'',p.time,p.note,Number.isFinite(lat)?lat:null,Number.isFinite(lng)?lng:null];
        }),types:['number','text','text','text','text','number','number']};
    }
    if(kind==='kpi'){
      const en=spec.lang==='en';
      return {header:en?['Figure','Value','Change','Target']:['Cijfer','Waarde','Verandering','Doel'],
        rows:spec.items.map(i=>[i.label,i.value,i.delta,i.target]),
        types:['text','number','number','number']};
    }
    const x=extra(kind);
    if(x){try{const t=x.table?x.table(spec,view,data):null;if(t&&Array.isArray(t.header)&&Array.isArray(t.rows))return t;}catch(_){}return {header:[],rows:[]};}
    if(kind==='timeline'){
      const en=spec.lang==='en', lang=en?'en':'nl', pos=spec.mode==='date'?'date':'number';
      return {header:en?['Item','Start','End','Owner','Status','Milestone','Note']:['Onderdeel','Start','Einde','Eigenaar','Status','Mijlpaal','Notitie'],
        rows:spec.items.map(i=>[i.label,i.from,i.to,i.owner,statusWord(i.status,lang),i.milestone?(en?'yes':'ja'):'',i.note]),
        types:['text',pos,pos,'text','text','text','text']};
    }
    return {header:[],rows:[]};
  }
  function exportCell(v,decimalComma){
    if(v===null||v===undefined) return '';
    if(typeof v==='number'){const s=String(Math.round(v*1e8)/1e8);return decimalComma?s.replace('.',','):s;}
    let s=String(v);
    // Spreadsheet formula injection: a text cell never starts a formula.
    if(/^[=+\-@\t\r]/.test(s)) s="'"+s;
    return s;
  }
  function toCsv(table,opts){
    const delim=(opts&&opts.delimiter)||';', comma=!(opts&&opts.decimalComma===false);
    const q=s=>(s.includes(delim)||/["\r\n]/.test(s))?'"'+s.replace(/"/g,'""')+'"':s;
    const lines=[table.header.map(h=>q(exportCell(h,comma)))].concat(table.rows.map(r=>r.map(v=>q(exportCell(v,comma)))));
    return '\uFEFF'+lines.map(l=>l.join(delim)).join('\r\n')+'\r\n';
  }
  function toTsv(table,opts){
    const comma=!(opts&&opts.decimalComma===false);
    const clean=s=>s.replace(/[\t\r\n]+/g,' ');
    return [table.header].concat(table.rows).map(r=>r.map(v=>clean(exportCell(v,comma))).join('\t')).join('\n');
  }

  // ── Map helpers ──────────────────────────────────────────────────────────
  // "local": tiles come from this server (PDOK for the Netherlands, OSM elsewhere).
  const OSM_TILES={url:'local',maxZoom:19};
  function mapRequest(spec,lang){
    return {v:1,lang:pickLang(lang),region:spec.region,photos:!!spec.photos,
      places:spec.places.map(p=>{
        const o={k:p.k,name:p.name,q:(p.address||p.name).slice(0,200)};
        if(Number.isFinite(p.lat)&&Number.isFinite(p.lng)){o.lat=p.lat;o.lng=p.lng;}
        if(p.wiki) o.wiki=p.wiki;
        return o;
      })};
  }
  // What the map can show without the server: only the given coordinates.
  function mapLocalData(spec,status){
    return {places:spec.places.map(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng)
      ?{k:p.k,status:'ok',lat:p.lat,lng:p.lng,precision:'given',source:'given',label:''}
      :{k:p.k,status:status||'not_found'}),
      tiles:Object.assign({},OSM_TILES),attribution:[]};
  }
  function tileUrlOk(url){
    return typeof url==='string'&&url.length<300&&/^https:\/\/[a-z0-9.-]+(:\d{2,5})?\/[^\s"'<>\\]*$/i.test(url)
      &&url.includes('{z}')&&url.includes('{x}')&&url.includes('{y}')&&!/\{(?![zxy]\})/.test(url.replace(/\{r\}/g,''));
  }
  function googleMapsUrl(points){
    const pts=points.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng)).map(p=>p.lat.toFixed(6)+','+p.lng.toFixed(6));
    if(!pts.length) return '';
    if(pts.length===1) return 'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(pts[0]);
    const mid=pts.slice(1,-1).slice(0,9);
    return 'https://www.google.com/maps/dir/?api=1&origin='+encodeURIComponent(pts[0])+'&destination='+encodeURIComponent(pts[pts.length-1])
      +(mid.length?'&waypoints='+encodeURIComponent(mid.join('|')):'')+'&travelmode=driving';
  }

  const api={register,extra,KIT_LANGS,kitKind,LIMITS,NOUN,NAME,pickLang,cleanJson,parseKit,parseCsv,detectDelimiter,parseNumber,
    validateTable,validateChart,validateMap,validateKpi,validateTimeline,build,estHeight,streamingTitle,compareCells,formatValue,viewIndices,
    initialView,totals,kitTable,toCsv,toTsv,mapRequest,mapLocalData,tileUrlOk,googleMapsUrl,OSM_TILES,
    kpiValueText,kpiDeltaText,timelineAxis,timelinePeriod,statusWord,dayOf,isoOf,STATUS_WORDS};
  root.SWKit=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
