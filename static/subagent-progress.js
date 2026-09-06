/* Present structured worker lifecycle events through the existing turn worklog.
 * This projector is scoped to one stream; it never receives model reasoning. */
(function(root){
  'use strict';
  const rank={queued:0,running:1,completed:2,failed:2,cancelled:2};
  function createProjector(restoredCalls){
    const seen=new Map();
    function project(data){
      if(!data||typeof data!=='object') return null;
      const id=String(data.id||'');
      const status=String(data.status||'');
      if(!/^[A-Za-z0-9_.:-]{1,160}$/.test(id)||!Object.hasOwn(rank,status)) return null;
      const prior=seen.get(id);
      if(prior&&rank[prior.status]>rank[status]) return null;
      if(prior&&rank[prior.status]===2) return null;
      if(!prior&&seen.size>=256) return null;
      const integer=(value,max)=>Math.max(0,Math.min(max,Math.floor(Number(value)||0)));
      const args={
        status,task_index:integer(data.task_index,1000),task_count:integer(data.task_count,1000),
        task:String(data.summary||'').replace(/[\r\n\t]+/g,' ').slice(0,120),
        tool_count:integer(data.tool_count,100000),
      };
      if(prior) args.tool_count=Math.max(args.tool_count,prior.tool_count||0);
      const signature=JSON.stringify(args);
      if(prior&&prior.signature===signature) return null;
      seen.set(id,{status,signature,tool_count:args.tool_count});
      return {
        event:rank[status]===2?'tool_complete':'tool',
        data:{
          tid:'subagent:'+id,name:'subagent_progress',args,
          preview:args.task, snippet:args.task,
          duration:Number.isFinite(Number(data.duration_seconds))?Math.max(0,Number(data.duration_seconds)):undefined,
          is_error:status==='failed',
        },
      };
    }
    for(const tc of Array.isArray(restoredCalls)?restoredCalls:[]){
      if(tc?.name!=='subagent_progress'||!String(tc.tid||'').startsWith('subagent:')) continue;
      const a=tc.args||{};
      project({id:tc.tid.slice(9),...a,summary:a.task});
    }
    return project;
  }
  function label(tc,translate){
    const a=tc&&tc.args||{};
    const names={queued:'Queued',running:'Working',completed:'Completed',failed:'Failed',cancelled:'Stopped'};
    if(!Object.hasOwn(names,a.status)) return '';
    const key='subagent_status_'+a.status;
    const translated=typeof translate==='function'?translate(key):key;
    const state=translated&&translated!==key?translated:names[a.status];
    const index=Number(a.task_index)||0;
    const count=Number(a.task_count)||0;
    const worker=count>1?`Sub-agent ${index+1}/${count}`:'Sub-agent';
    const task=String(a.task||'').slice(0,120);
    return `${worker} · ${state}${task?' · '+task:''}`;
  }
  const api={createProjector,label};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.SynPulseSubagentProgress=api;
})(typeof window!=='undefined'?window:globalThis);
