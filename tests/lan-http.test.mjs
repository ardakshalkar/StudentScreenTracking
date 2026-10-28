import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';

const result=await build({entryPoints:['extension/src/config.ts'],bundle:true,format:'esm',platform:'browser',write:false});
const {serverURL,isLanHTTP}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));

test('LAN HTTP requires explicit student opt-in for RFC1918 private IPv4 only',()=>{
  for(const host of ['10.0.0.4','172.16.0.2','172.31.255.254','192.168.1.20']) {
    assert.throws(()=>serverURL(`http://${host}:5173`),/explicitly enable LAN HTTP/);
    assert.equal(serverURL(`http://${host}:5173`,true),`http://${host}:5173`);
    assert.equal(isLanHTTP(`http://${host}:5173`),true);
  }
});

test('LAN opt-in never enables arbitrary internet HTTP or ambiguous hostnames',()=>{
  for(const host of ['8.8.8.8','172.15.0.1','172.32.0.1','169.254.0.1','100.64.0.1','example.com','teacher.local','192.168.1.20.evil.test','[fd00::1]']) {
    assert.throws(()=>serverURL(`http://${host}:5173`,true));
  }
  for(const value of ['http://user:password@192.168.1.20','http://192.168.1.20/api','http://192.168.1.20?key=value','ftp://192.168.1.20'])assert.throws(()=>serverURL(value,true));
});

test('HTTPS and loopback development retain their current behavior',()=>{
  assert.equal(serverURL('https://classroom.example.edu/'),'https://classroom.example.edu');
  assert.equal(serverURL('http://localhost:5173'),'http://localhost:5173');
  assert.equal(serverURL('http://127.0.0.1:8000'),'http://127.0.0.1:8000');
  assert.equal(isLanHTTP('https://192.168.1.20'),false);
});
