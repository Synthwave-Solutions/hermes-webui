/* Capability-driven entry in Bots; screen ACLs remain server-side. */
window.addEventListener('load',async()=>{try{const r=await fetch('/api/bot-screen',{cache:'no-store'});if(!r.ok)return;const data=await r.json();const link=document.getElementById('btnBotScreens');if(link&&data.bots?.length){link.hidden=false;link.style.display='';}}catch(_){}});
