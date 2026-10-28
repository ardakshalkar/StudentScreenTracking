export interface Identity {server:string; name:string; studentId:string; code:string}
export interface Joined {token:string; session:string; student:string; recording:boolean; interval:number; key:string; email?:string|null}
export const identityKey = (identity:Identity) => JSON.stringify(identity);
export async function loadConfig():Promise<Partial<Identity>> {
  return (await chrome.storage.local.get('identity')).identity || {};
}
export async function saveConfig(identity:Identity) { await chrome.storage.local.set({identity}); }
export function isPrivateIPv4(host:string):boolean {
  if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return false;
  const parts=host.split('.').map(Number);
  if(parts.some(part=>part>255)) return false;
  return parts[0]===10 || (parts[0]===172&&parts[1]>=16&&parts[1]<=31) || (parts[0]===192&&parts[1]===168);
}
export function isLanHTTP(origin:string):boolean {
  const url=new URL(origin);return url.protocol==='http:'&&isPrivateIPv4(url.hostname);
}
export function serverURL(value:string,allowLanHTTP=false):string {
  const url = new URL(value);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw Error('Use a server origin, such as https://classroom.example.edu');
  if (url.protocol !== 'https:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    if(!allowLanHTTP||!isPrivateIPv4(url.hostname)) throw Error('Use HTTPS, or explicitly enable LAN HTTP for a private IPv4 address such as http://192.168.1.20:5173.');
  }
  return url.origin;
}
