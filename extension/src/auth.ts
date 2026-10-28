import {type Identity, type Joined, identityKey, saveConfig} from './config';
import {type GoogleIdentity} from './google-auth';
export async function joinClassroom(identity:Identity, google?:GoogleIdentity):Promise<Joined> {
  await saveConfig(identity);
  const saved = (await chrome.storage.local.get('joined')).joined as Joined|undefined;
  if (!google && saved?.key === identityKey(identity)) {
    try { if (JSON.parse(atob(saved.token.split('.')[0].replace(/-/g,'+').replace(/_/g,'/'))).exp > Date.now()/1000 + 60) return saved; } catch { /* rejoin */ }
  }
  const response = await fetch(identity.server + '/api/join', {method:'POST',headers:{'Content-Type':'application/json',...(google?{Authorization:'Bearer '+google.token}:{})},body:JSON.stringify({name:identity.name,student_id:identity.studentId,code:identity.code}),signal:AbortSignal.timeout(10000)});
  const body = await response.json();
  if (!response.ok) throw Error(typeof body.detail === 'string' ? body.detail : 'Check your name, ID, and eight-character classroom code.');
  const joined:Joined = {...body,key:identityKey(identity)};
  await chrome.storage.local.set({joined});
  return joined;
}
