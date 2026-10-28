import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {createHash} from 'node:crypto';

const built=await build({entryPoints:['extension/src/google-auth.ts'],bundle:true,format:'esm',platform:'browser',write:false});
const {googleSignIn}=await import('data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].text).toString('base64'));

function setup(t,redirect){
  let start,exchange,calls=0;
  const id='a'.repeat(32),uri=`https://${id}.chromiumapp.org/student-login`;
  const original=globalThis.chrome;
  globalThis.chrome={runtime:{id},identity:{getRedirectURL:()=>uri,launchWebAuthFlow:async options=>{
    assert.equal(options.interactive,true);
    return redirect?redirect(start,uri):uri+'#'+new URLSearchParams({client_state:start.client_state,grant:'one-time-grant'});
  }}};
  t.after(()=>{globalThis.chrome=original;});
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    calls++;
    if(url.endsWith('/start')) {start=JSON.parse(options.body);return Response.json({url:'https://accounts.google.com/o/oauth2/v2/auth?scope=openid'});}
    exchange=JSON.parse(options.body);
    return Response.json({token:'application-identity-token',email:'alice@school.edu',name:'Alice'});
  });
  return {get start(){return start;},get exchange(){return exchange;},get calls(){return calls;}};
}

test('Google login binds its single-use grant to extension-generated PKCE and state',async t=>{
  const result=setup(t);
  const identity=await googleSignIn('https://classroom.test','ABCDEFGH');
  assert.equal(identity.email,'alice@school.edu');
  assert.equal(result.start.extension_id,'a'.repeat(32));
  assert.equal(result.start.code,'ABCDEFGH');
  assert.equal(createHash('sha256').update(result.exchange.verifier).digest('base64url'),result.start.challenge);
  assert.equal(result.exchange.grant,'one-time-grant');assert.equal(result.calls,2);
});

test('wrong redirect origin prevents exchanging a Google login grant',async t=>{
  const result=setup(t,(start)=>'https://evil.test/student-login#'+new URLSearchParams({client_state:start.client_state,grant:'stolen'}));
  await assert.rejects(googleSignIn('https://classroom.test','ABCDEFGH'),/state mismatch/);
  assert.equal(result.calls,1);
});

test('wrong state prevents exchanging a Google login grant',async t=>{
  const result=setup(t,(_,uri)=>uri+'#client_state=wrong&grant=stolen');
  await assert.rejects(googleSignIn('https://classroom.test','ABCDEFGH'),/state mismatch/);
  assert.equal(result.calls,1);
});

test('domain rejection reaches student UI without issuing an application credential',async t=>{
  const result=setup(t,(start,uri)=>uri+'#'+new URLSearchParams({client_state:start.client_state,error:'This email domain is not allowed for students'}));
  await assert.rejects(googleSignIn('https://classroom.test','ABCDEFGH'),/domain is not allowed/);
  assert.equal(result.calls,1);
});
