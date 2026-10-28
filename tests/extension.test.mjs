import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';

const result=await build({entryPoints:['extension/src/connection.ts'],bundle:true,format:'esm',platform:'browser',write:false});
const {Connection}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));

function setup(t){
  t.mock.timers.enable({apis:['setTimeout','setInterval','Date']});
  const sockets=[],states=[],fatal=[],messages=[];
  class Socket{
    static OPEN=1;readyState=0;bufferedAmount=0;sent=[];
    constructor(url){this.url=url;sockets.push(this);}
    open(){this.readyState=1;this.onopen();}
    message(body){this.onmessage({data:JSON.stringify(body)});}
    send(data){this.sent.push(data);}
    close(code=1006){this.readyState=3;this.onclose?.({code});}
  }
  t.mock.method(Math,'random',()=>0);
  const original=globalThis.WebSocket;globalThis.WebSocket=Socket;
  t.after(()=>{globalThis.WebSocket=original;});
  let connection;
  connection=new Connection('https://classroom.test','student-secret',body=>messages.push(body),state=>states.push(state),reason=>{fatal.push(reason);connection.stop();},()=>true);
  connection.start();t.after(()=>connection.stop());
  const ready=()=>{const socket=sockets.at(-1);socket.open();socket.message({type:'ready',mode:'overview',recording:false,interval:20});return socket;};
  return {connection,sockets,states,fatal,messages,ready};
}

test('one in-flight frame, ACK unlock, and no offline buffer',async t=>{
  const {connection,ready}=setup(t);const socket=ready();
  assert.equal(socket.url,'wss://classroom.test/api/ws/student');
  assert.equal(JSON.parse(socket.sent[0]).token,'student-secret');
  const frame=new Blob(['image payload']);
  assert.equal(await connection.send(frame),true);
  assert.equal(await connection.send(frame),false);
  socket.message({type:'ack'});
  assert.equal(await connection.send(frame),true);
  socket.bufferedAmount=200000;socket.message({type:'ack'});
  assert.equal(connection.canSend(),false);
  socket.close();assert.equal(await connection.send(frame),false);
});

test('short network interruption reconnects with same credential and no retained frames',async t=>{
  const {connection,ready,sockets,fatal}=setup(t);const first=ready();
  await connection.send(new Blob(['old image']));first.close();
  t.mock.timers.tick(500);assert.equal(sockets.length,2);
  const second=ready();
  assert.deepEqual(JSON.parse(second.sent[0]),{token:'student-secret'});
  assert.equal(second.sent.length,1);assert.equal(connection.canSend(),true);
  assert.equal(fatal.length,0);
});

test('long outage expires capture lease and stops reconnect attempts',t=>{
  const {ready,fatal,sockets}=setup(t);ready().close();
  t.mock.timers.tick(35001);
  assert.equal(fatal.length,1);assert.match(fatal[0],/Capture stopped/);
  const count=sockets.length;t.mock.timers.tick(60000);assert.equal(sockets.length,count);
});

test('ended session is fatal and does not silently recapture',t=>{
  const {ready,fatal,sockets}=setup(t);ready().message({type:'session_ended'});
  assert.match(fatal[0],/Classroom ended/);t.mock.timers.tick(60000);
  assert.equal(sockets.length,1);
});

test('fatal authorization failure never reconnects',t=>{
  const {ready,fatal,sockets}=setup(t);ready().close(4401);
  assert.equal(fatal.length,1);t.mock.timers.tick(60000);assert.equal(sockets.length,1);
});
