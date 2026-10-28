export interface ServerMessage {type:string; mode?:'overview'|'focused'; recording?:boolean; interval?:number}
export class Connection {
  private ws?:WebSocket;
  private retry?:ReturnType<typeof setTimeout>;
  private heartbeat?:ReturnType<typeof setInterval>;
  private stopped=false;
  private attempts=0;
  private pendingAt:number|null=null;
  private ready=false;
  private lastServerAt=Date.now();
  constructor(private server:string,private token:string,private onMessage:(body:ServerMessage)=>void,
    private onState:(state:string)=>void,private onFatal:(reason:string)=>void,private captureHealthy:()=>boolean) {}
  start() {this.connect();}
  private connect() {
    if (this.stopped) return;
    this.onState('Connecting…');
    const ws = this.ws = new WebSocket(this.server.replace(/^http/,'ws') + '/api/ws/student');
    const handshake = setTimeout(()=>ws.close(),10000);
    ws.onopen = () => ws.send(JSON.stringify({token:this.token}));
    ws.onmessage = event => {
      let body:ServerMessage;
      try {body=JSON.parse(event.data);} catch {ws.close(); return;}
      this.lastServerAt=Date.now();
      if (body.type === 'ready') {
        clearTimeout(handshake); this.attempts=0;this.pendingAt=null;this.ready=true;this.onState('Sharing — connected');
      }
      if (body.type === 'ack') this.pendingAt=null;
      if (body.type === 'session_ended') { this.onFatal('Classroom ended. Capture stopped.'); return; }
      this.onMessage(body);
    };
    ws.onclose = event => {
      clearTimeout(handshake); this.ready=false;this.pendingAt=null;
      if (this.stopped) return;
      if ([4004,4009,4400,4401,4403].includes(event.code)) {
        this.onFatal(event.code===4004?'Classroom ended. Capture stopped.':'Sharing authorization ended or connection replaced. Join again.');return;
      }
      this.onState('Sharing paused — reconnecting; no frames are queued');
      const delay=Math.min(15000,500*2**Math.min(this.attempts++,5))+Math.random()*400;
      this.retry=setTimeout(()=>this.connect(),delay);
    };
    ws.onerror=()=>ws.close();
    if (!this.heartbeat) this.heartbeat=setInterval(()=> {
      if (this.stopped) return;
      // A short outage resumes with the SAME authorized stream. A longer outage
      // expires the classroom lease; never keep capturing indefinitely offline.
      if (Date.now()-this.lastServerAt>30000) {this.onFatal('Server unavailable for 30 seconds. Capture stopped. Start Sharing again after reconnecting.');return;}
      if (this.pendingAt!==null && Date.now()-this.pendingAt>10000) this.ws?.close();
      if (this.ws?.readyState===WebSocket.OPEN && this.ready) this.ws.send(JSON.stringify({type:'heartbeat',captureHealthy:this.captureHealthy()}));
    },5000);
  }
  canSend() {return this.ready && this.ws?.readyState===WebSocket.OPEN && this.pendingAt===null && this.ws.bufferedAmount<100000;}
  async send(blob:Blob) {
    const data = await blob.arrayBuffer();
    if (!this.canSend() || this.stopped) return false;
    this.pendingAt=Date.now();this.ws!.send(data);return true;
  }
  stop() {
    this.stopped=true;this.ready=false;
    clearTimeout(this.retry);clearInterval(this.heartbeat);
    if (this.ws?.readyState===WebSocket.OPEN) this.ws.send(JSON.stringify({type:'stop'}));
    this.ws?.close(1000);this.ws=undefined;
  }
}
