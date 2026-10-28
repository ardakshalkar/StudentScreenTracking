"""Explicitly synthetic transport load test. Never used by the teacher UI."""
import argparse
import asyncio
import base64
import io
import json
import os
import time

import httpx
import websockets
from PIL import Image, ImageDraw


def screenshot(index, tick, width):
    image=Image.new('RGB',(width,int(width*.5625)),'#17252f')
    draw=ImageDraw.Draw(image)
    for row in range(30):
        draw.text((20,20+row*10),f'SIMULATED LOAD TEST — Student {index:02d} / frame {tick} / code line {row}: print(value + {tick})',fill='#dce9e6')
    output=io.BytesIO();image.save(output,'WEBP',quality=85)
    return output.getvalue()


async def main(args):
    headers={'Origin':args.url}
    started=time.monotonic()
    received={}; transmitted=0; total_bytes=0; focused=asyncio.Event()
    async with httpx.AsyncClient(base_url=args.url,headers=headers,timeout=20) as client:
        response=await client.post('/api/login',json={'password':os.environ['TEACHER_PASSWORD']});response.raise_for_status()
        response=await client.post('/api/sessions',json={'course':'Synthetic load test','title':f'{args.students} students','recording':True,'interval':20})
        response.raise_for_status();session=response.json()
        joins=[]
        for index in range(args.students):
            response=await client.post('/api/join',json={'name':f'Simulated {index:02d}','student_id':f'load-{index:02d}','code':session['code']})
            response.raise_for_status();joins.append(response.json())
        ticket=(await client.post('/api/ws-ticket')).json()['token']
        ws_url=args.url.replace('http','ws',1)
        deadline=time.monotonic()+args.seconds
        async def student(index,joined):
            nonlocal transmitted,total_bytes
            mode='overview';ack=asyncio.Event();ack.set()
            async with websockets.connect(ws_url+'/api/ws/student',max_size=1_100_000,additional_headers={'Origin':'chrome-extension://'+'a'*32},max_queue=1) as ws:
                await ws.send(json.dumps({'token':joined['token']}))
                ready=json.loads(await ws.recv());assert ready['type']=='ready'
                async def receiver():
                    nonlocal mode
                    async for message in ws:
                        body=json.loads(message)
                        if body['type']=='ack':ack.set()
                        if body['type']=='quality':
                            mode=body['mode']
                            if index==0 and mode=='focused':focused.set()
                async def heartbeat():
                    while True:
                        await ws.send(json.dumps({'type':'heartbeat','captureHealthy':True}));await asyncio.sleep(5)
                tasks=[asyncio.create_task(receiver()),asyncio.create_task(heartbeat())]
                try:
                    tick=0
                    while time.monotonic()<deadline:
                        await asyncio.wait_for(ack.wait(),10);ack.clear()
                        raw=await asyncio.to_thread(screenshot,index,tick,1600 if mode=='focused' else 640)
                        await ws.send(raw);transmitted+=1;total_bytes+=len(raw);tick+=1
                        await asyncio.sleep(.333 if mode=='focused' else 2.5)
                finally:
                    for task in tasks:task.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
        async def teacher():
            async with websockets.connect(ws_url+'/api/ws/teacher/'+session['id'],origin=args.url,max_size=2_000_000,max_queue=1) as ws:
                await ws.send(json.dumps({'token':ticket}))
                async def controls():
                    await asyncio.sleep(2)
                    await ws.send(json.dumps({'type':'focus','student':joins[0]['student']}))
                    while True:
                        await ws.send(json.dumps({'type':'heartbeat'}));await asyncio.sleep(5)
                controls_task=asyncio.create_task(controls())
                try:
                    while time.monotonic()<deadline+1:
                        body=json.loads(await asyncio.wait_for(ws.recv(),5))
                        if body['type']=='frame':
                            raw=base64.b64decode(body['data'])
                            assert raw[:4]==b'RIFF'
                            received[body['student']]=received.get(body['student'],0)+1
                finally:
                    controls_task.cancel();await asyncio.gather(controls_task,return_exceptions=True)
        try:
            await asyncio.gather(teacher(),*(student(i,joined) for i,joined in enumerate(joins)))
            samples=(await client.get('/api/sessions/'+session['id']+'/samples')).json()
            assert len(received)==args.students, f'Only {len(received)} students delivered frames'
            assert all(n>=2 for n in received.values()),'Some streams did not update'
            assert focused.is_set(),'Focused mode was not activated'
            assert len(samples)>=args.students,'Recording missed initial samples'
            print(json.dumps({'students':len(received),'seconds':round(time.monotonic()-started,2),'transmitted_frames':transmitted,
                'teacher_frames':sum(received.values()),'minimum_frames_per_student':min(received.values()),'transmitted_MB':round(total_bytes/1e6,2),
                'recorded_samples':len(samples),'focused_mode':True,'result':'PASS'},indent=2))
        finally:
            await client.post('/api/sessions/'+session['id']+'/end')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://localhost:8000');parser.add_argument('--students',type=int,default=30);parser.add_argument('--seconds',type=int,default=25)
    asyncio.run(main(parser.parse_args()))
