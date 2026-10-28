export {};
const status = document.querySelector('#status')!;
async function openControls() {
  const url=chrome.runtime.getURL('session.html');
  const tabs=await chrome.tabs.query({});
  const existing=tabs.find(tab=>tab.url===url);
  if(existing?.id) {await chrome.tabs.update(existing.id,{active:true});await chrome.windows.update(existing.windowId,{focused:true});}
  else await chrome.windows.create({url,type:'popup',width:680,height:860});
  window.close();
}
document.querySelector('#open')!.addEventListener('click',()=>void openControls());
document.querySelector('#stop')!.addEventListener('click',async()=> {
  try {await chrome.runtime.sendMessage({target:'capture',type:'stop'});status.textContent='Sharing stopped';}
  catch {status.textContent='No sharing window is open';}
});
chrome.runtime.sendMessage({target:'capture',type:'status'}).then(result=>{if(result)status.textContent=result.status;}).catch(()=>{});
