import {loadConfig,serverURL,isLanHTTP,type Identity,type Joined} from './config';
import {joinClassroom} from './auth';
import {chooseScreen,cancelPicker} from './capture';
import {Compressor} from './compression';
import {Connection,type ServerMessage} from './connection';
import {qualities,type Mode} from './quality';
import {policy,googleSignIn} from './google-auth';

const $ = <T extends HTMLElement>(id:string)=>document.getElementById(id) as T;
const status=$('status'), start=$<HTMLButtonElement>('start'), stop=$<HTMLButtonElement>('stop');
const video=$<HTMLVideoElement>('source');
const compressor=new Compressor($<HTMLCanvasElement>('canvas'));
let identity:Identity, joined:Joined|undefined, stream:MediaStream|undefined, connection:Connection|undefined;
let mode:Mode='overview', timer:ReturnType<typeof setTimeout>|undefined, busy=false;
let healthyAt=0, previousVideoTime=-1, active=false;
let generation=0;
function setStatus(value:string) {status.textContent=value; document.title=active?'● Sharing — Classroom':'Classroom sharing controls';}
function recording(body:ServerMessage) {
  if(typeof body.recording==='boolean') $('recording').textContent=body.recording?`RECORDING ON · a changed screenshot every ${body.interval} seconds`:'Recording off · live viewing only';
}
function setMode(value:Mode) {
  mode=value;compressor.reset();
  $('quality').textContent=value==='focused'?'Teacher is viewing your screen · 1600px · 3 fps':'Overview · 640px · every 2.5 seconds';
}
function message(body:ServerMessage) {
  recording(body);
  if(body.mode) setMode(body.mode);
  if(body.type==='ready') compressor.reset();
}
function end(reason='Not sharing — capture stopped') {
  generation++;active=false;clearTimeout(timer);cancelPicker();
  connection?.stop();connection=undefined;
  stream?.getTracks().forEach(track=>track.stop());stream=undefined;
  video.srcObject=null;compressor.reset();
  start.disabled=!joined;stop.disabled=true;$<HTMLButtonElement>('connect').disabled=false;
  setStatus(reason);void chrome.action.setBadgeText({text:''});
}
function enteredIdentity():Identity {
  return {server:serverURL($<HTMLInputElement>('server').value.trim(),$<HTMLInputElement>('lanHttp').checked),name:$<HTMLInputElement>('name').value.trim(),studentId:$<HTMLInputElement>('studentId').value.trim(),code:$<HTMLInputElement>('code').value.trim().toUpperCase()};
}
function didJoin() {
  recording({type:'recording',...joined});start.disabled=false;
  $('account').textContent=joined?.email?`Signed in as ${joined.email}`:'Joined using classroom code and student ID.';
  setStatus('Joined. Click Start Sharing to select a screen or window.');
}
function showTransport(server:string) {
  $('transport').textContent=isLanHTTP(server)?'LAN HTTP / WS — screenshots, identities and passwords are NOT encrypted. Code-only classroom.':'HTTPS/WSS is used for remote secure classrooms. Localhost HTTP is for development.';
}
$('server').addEventListener('input',()=>{if(active)end('Server address changed. Sharing stopped; join again.');joined=undefined;start.disabled=true;$('google').hidden=true;});
$('lanHttp').addEventListener('change',()=>{
  if(active)end('Connection setting changed. Sharing stopped; join again.');
  joined=undefined;start.disabled=true;$('google').hidden=true;
});
async function tick(owner:number) {
  if(!active||owner!==generation) return;
  const started=Date.now();
  if(video.currentTime!==previousVideoTime && video.readyState>=2 && stream?.getVideoTracks()[0]?.readyState==='live') {healthyAt=Date.now();previousVideoTime=video.currentTime;}
  const sender=connection;
  if(sender?.canSend() && Date.now()-healthyAt<10000) {
    try {const blob=await compressor.frame(video,mode);if(active&&owner===generation&&blob&&!(await sender.send(blob))) compressor.reset();}
    catch(error) {$('detail').textContent=String(error);}
  }
  if(active&&owner===generation) timer=setTimeout(()=>void tick(owner),Math.max(50,qualities[mode].interval-(Date.now()-started)));
}
for(const [key,value] of Object.entries(await loadConfig())) {
  const element=document.getElementById(key) as HTMLInputElement|null;
  if(element) element.value=value;
}
if(!$<HTMLInputElement>('server').value) $<HTMLInputElement>('server').value='http://localhost:5173';
$('join').addEventListener('submit',async event=> {
  event.preventDefault();if(active||busy)return;
  const button=$<HTMLButtonElement>('connect');button.disabled=true;start.disabled=true;joined=undefined;
  try {
    identity=enteredIdentity();
    showTransport(identity.server);
    // Permission request is made directly from the submit user gesture, before I/O.
    const allowed=await chrome.permissions.request({origins:[identity.server+'/*']});
    if(!allowed) throw Error('Server access was declined. Nothing is being shared.');
    const settings=await policy(identity.server);
    if(isLanHTTP(identity.server)&&(!settings.lan_http||settings.mode!=='code'))throw Error('The teacher must enable ALLOW_LAN_HTTP=true and STUDENT_AUTH_MODE=code on this server.');
    $('google').hidden=settings.mode!=='google';$('manualIdentity').hidden=settings.mode==='google';
    if(settings.mode==='google') {
      $('account').textContent='Allowed Google email domains: '+settings.allowed_domains.join(', ');
      setStatus('Click Sign in with Google & join to verify your school account.');
    } else {
      if(!identity.name||!identity.studentId)throw Error('Enter your name and student ID for this code-only classroom.');
      joined=await joinClassroom(identity);didJoin();
    }
  } catch(error) {setStatus(error instanceof Error?error.message:String(error));}
  finally {button.disabled=false;}
});
$('google').addEventListener('click',async()=> {
  if(active||busy)return;
  busy=true;start.disabled=true;joined=undefined;
  const button=$<HTMLButtonElement>('google');button.disabled=true;$<HTMLButtonElement>('connect').disabled=true;
  try {
    identity=enteredIdentity();
    if(isLanHTTP(identity.server))throw Error('Google sign-in requires the HTTPS classroom address. LAN HTTP supports code-only joining.');
    if(!/^[A-Z2-9]{8}$/.test(identity.code))throw Error('Enter the eight-character classroom code.');
    const account=await googleSignIn(identity.server,identity.code);
    identity={...identity,name:account.name,studentId:account.email};
    $<HTMLInputElement>('name').value=identity.name;$<HTMLInputElement>('studentId').value=identity.studentId;
    joined=await joinClassroom(identity,account);didJoin();
  } catch(error) {setStatus(error instanceof Error?error.message:String(error));}
  finally {busy=false;button.disabled=false;$<HTMLButtonElement>('connect').disabled=false;}
});
start.addEventListener('click',async()=> {
  if(!joined||active||busy)return;
  if(!$<HTMLInputElement>('consent').checked) {setStatus('Read the sharing disclosure and check the acknowledgement before selecting a screen.');$('consent').focus();return;}
  busy=true;start.disabled=true;$<HTMLButtonElement>('connect').disabled=true;
  const owner=++generation;
  try {
    const selected=await chooseScreen();
    if(owner!==generation){selected.getTracks().forEach(track=>track.stop());return;}
    stream=selected;
    stream.getVideoTracks()[0].onended=()=>end('Chrome ended screen sharing. Capture stopped.');
    video.srcObject=stream;await video.play();
    active=true;healthyAt=Date.now();previousVideoTime=-1;setMode('overview');
    stop.disabled=false;void chrome.action.setBadgeBackgroundColor({color:'#c33c45'});void chrome.action.setBadgeText({text:'LIVE'});
    connection=new Connection(identity.server,joined.token,message,setStatus,reason=>end(reason),()=>active&&Date.now()-healthyAt<10000);
    connection.start();void tick(owner);
  } catch(error) {end(error instanceof Error?error.message:String(error));}
  finally {busy=false;}
});
stop.addEventListener('click',()=>end());
chrome.runtime.onMessage.addListener((body,sender,reply)=> {
  if(sender.id!==chrome.runtime.id||body.target!=='capture') return;
  if(body.type==='stop') end();
  reply({status:status.textContent});
});
window.addEventListener('pagehide',()=>end());
