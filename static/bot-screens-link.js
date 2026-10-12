/* Both entries share the existing, server-authorized viewer. Keep its iframe
   alive across panel/tab switches: hiding the UI must not abandon a takeover. */
window.SynthPulseBotScreens={
  available:false,
  mount(){
    const panel=document.getElementById('workspaceScreensPanel');
    if(!this.available||!panel||panel.firstElementChild)return;
    const frame=document.createElement('iframe');
    frame.id='workspaceScreensFrame';
    frame.title='Bot Screens';
    frame.allowFullscreen=true;
    const bot=typeof S!=='undefined'?S.activeProfile:'default';
    frame.src='/static/bot-screens.html?'+new URLSearchParams({embedded:'1',bot:bot||'default'});
    panel.append(frame);
  }
};
window.addEventListener('load',async()=>{
  try{
    const r=await fetch('/api/bot-screen',{cache:'no-store'});
    if(!r.ok)return;
    const data=await r.json();
    if(!data.bots?.length)return;
    window.SynthPulseBotScreens.available=true;
    for(const id of ['btnBotScreens','workspaceScreensTab']){
      const link=document.getElementById(id);
      if(link){link.hidden=false;link.style.display='';}
    }
    if(typeof syncWorkspacePanelUI==='function')syncWorkspacePanelUI();
  }catch(_){}
});
