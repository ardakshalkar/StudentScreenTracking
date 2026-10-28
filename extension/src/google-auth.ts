export interface GoogleIdentity {token:string; email:string; name:string}
export interface StudentPolicy {mode:'code'|'google'; allowed_domains:string[]; lan_http?:boolean}
export async function policy(server:string):Promise<StudentPolicy> {
  const response=await fetch(server+'/api/student-auth/config',{signal:AbortSignal.timeout(10000)});
  if(!response.ok) throw Error('Cannot load the classroom sign-in settings.');
  return response.json();
}
function randomValue() {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)),v=>v.toString(16).padStart(2,'0')).join('');
}
async function challenge(verifier:string) {
  const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
  return btoa(String.fromCharCode(...digest)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
export async function googleSignIn(server:string,code:string):Promise<GoogleIdentity> {
  const verifier=randomValue(),state=randomValue();
  const response=await fetch(server+'/api/student-auth/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code,extension_id:chrome.runtime.id,challenge:await challenge(verifier),client_state:state}),signal:AbortSignal.timeout(10000)});
  const body=await response.json();
  if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Google sign-in could not start.');
  const destination=new URL(body.url);
  if(destination.origin!=='https://accounts.google.com')throw Error('Unexpected Google sign-in provider.');
  const returned=await chrome.identity.launchWebAuthFlow({url:destination.href,interactive:true});
  if(!returned)throw Error('Google sign-in was cancelled.');
  const url=new URL(returned),expected=new URL(chrome.identity.getRedirectURL('student-login'));
  const result=new URLSearchParams(url.hash.slice(1));
  if(url.origin!==expected.origin||url.pathname!==expected.pathname||result.get('client_state')!==state)throw Error('Google sign-in state mismatch. Please try again.');
  if(result.has('error'))throw Error(result.get('error')!);
  const exchanged=await fetch(server+'/api/student-auth/exchange',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({grant:result.get('grant'),verifier}),signal:AbortSignal.timeout(10000)});
  const identity=await exchanged.json();
  if(!exchanged.ok)throw Error(typeof identity.detail==='string'?identity.detail:'Google sign-in could not be completed.');
  return identity;
}
