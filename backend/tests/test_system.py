import asyncio
import contextlib
import io
import time
import zipfile

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend.config import Settings
from backend.drive import Drive
from backend.main import create_app
from backend.security import issue, verify
from backend.storage import Store

ORIGIN = 'http://localhost:5173'
PASSWORD = 'test-password-12345'


def frame(text='student code', width=640):
    image = Image.new('RGB', (width, 360), '#162631')
    ImageDraw.Draw(image).text((20, 20), text, fill='white')
    output = io.BytesIO()
    image.save(output, 'WEBP', quality=85)
    return output.getvalue()


@pytest.fixture
def client(tmp_path):
    cfg = Settings(data=tmp_path, password=PASSWORD, secret='x' * 40)
    app = create_app(cfg)
    with TestClient(app) as client:
        client.headers['origin'] = ORIGIN
        assert client.post('/api/login', json={'password': PASSWORD}).status_code == 200
        yield client


def classroom(client, recording=False):
    response = client.post('/api/sessions', json={'course':'Python', 'title':'Lab 1', 'recording':recording, 'interval':5})
    assert response.status_code == 200, response.text
    return response.json()


def join(client, session, identity='student-1'):
    response = client.post('/api/join', json={'name':'Student ' + identity, 'student_id':identity, 'code':session['code']})
    assert response.status_code == 200, response.text
    return response.json()


def student_ws(client, joined):
    return client.websocket_connect('/api/ws/student', headers={'origin':'chrome-extension://'+'a'*32})


def until(ws, kind):
    for _ in range(200):
        body = ws.receive_json()
        if body['type'] == kind:
            return body
    raise AssertionError(f'No {kind} message')


def test_auth_and_session_validation(client):
    session = classroom(client)
    assert client.get('/api/sessions', cookies={'teacher':'invalid'}).status_code == 401
    assert client.post('/api/join', json={'name':'A','student_id':'1','code':'ZZZZZZZZ'}).status_code == 404
    joined = join(client, session)
    assert client.post('/api/join', json={'name':'A','student_id':'student-1','code':session['code']}).status_code == 409
    assert client.post('/api/sessions', json={'course':'X','title':'X'}).status_code == 409
    assert client.post('/api/logout', headers={'origin':'https://evil.test'}).status_code == 403
    assert client.get('/api/samples/missing', cookies={'teacher':'invalid'}).status_code == 401
    assert 'token' in joined


def test_real_webp_delivery_focus_and_stop(client):
    session = classroom(client)
    joined = join(client, session)
    token = client.post('/api/ws-ticket').json()['token']
    raw = frame()
    with student_ws(client, joined) as student:
        student.send_json({'token':joined['token']})
        assert student.receive_json()['type'] == 'ready'
        student.send_bytes(raw)
        assert student.receive_json()['type'] == 'ack'
        with client.websocket_connect('/api/ws/teacher/'+session['id'], headers={'origin':ORIGIN}) as teacher:
            teacher.send_json({'token':token})
            result = until(teacher, 'frame')
            import base64
            assert base64.b64decode(result['data']) == raw
            assert result['student'] == joined['student']
            teacher.send_json({'type':'focus','student':joined['student']})
            assert until(student, 'quality')['mode'] == 'focused'
            teacher.send_json({'type':'focus','student':None})
            assert until(student, 'quality')['mode'] == 'overview'
            assert client.patch('/api/sessions/'+session['id']+'/recording',json={'recording':True,'interval':20}).status_code == 200
            assert until(student, 'recording')['recording'] is True
            client.post('/api/sessions/'+session['id']+'/end')
            assert until(student,'session_ended')['type'] == 'session_ended'
            assert client.app.state.live[joined['student']].frame is None
    assert client.post('/api/join', json={'name':'B','student_id':'2','code':session['code']}).status_code == 404


def test_recording_and_authenticated_playback(client):
    session = classroom(client, True)
    joined = join(client, session)
    with student_ws(client, joined) as ws:
        ws.send_json({'token':joined['token']})
        ws.receive_json()
        ws.send_bytes(frame())
        assert ws.receive_json()['type'] == 'ack'
        deadline = time.time()+5
        samples = []
        while not samples and time.time() < deadline:
            time.sleep(.1)
            samples = client.get(f"/api/sessions/{session['id']}/samples").json()
        assert len(samples) == 1
        assert client.get('/api/samples/'+samples[0]['id']).headers['content-type'] == 'image/webp'
        assert samples[0]['student_id'] == 'student-1'
        # Live frames arriving more often do not become recording samples.
        for i in range(4):
            time.sleep(.2)
            ws.send_bytes(frame('line '+str(i)))
            until(ws, 'ack')
        assert len(client.get(f"/api/sessions/{session['id']}/samples").json()) == 1


def test_reconnect_preserves_student_and_rejects_teacher_token(client):
    session = classroom(client)
    joined = join(client, session)
    for _ in range(2):
        with student_ws(client, joined) as ws:
            ws.send_json({'token':joined['token']})
            assert ws.receive_json()['type'] == 'ready'
            ws.send_bytes(frame())
            assert ws.receive_json()['type'] == 'ack'
    assert len(client.app.state.live) == 1
    token = client.post('/api/ws-ticket').json()['token']
    with student_ws(client, joined) as ws:
        ws.send_json({'token':token})
        assert ws.receive()['code'] == 4401


def test_invalid_images_and_ws_origin(client):
    joined = join(client, classroom(client))
    with student_ws(client, joined) as ws:
        ws.send_json({'token':joined['token']})
        ws.receive_json()
        ws.send_bytes(b'not a screen image'*10)
        assert ws.receive()['code'] == 4400
    with pytest.raises(Exception):
        with client.websocket_connect('/api/ws/teacher/any',headers={'origin':'https://evil.test'}):
            pass


def test_archive_dedup_and_restart_sealing(tmp_path):
    store=Store(tmp_path)
    store.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,NULL)',('session','Python','Lab','12345678',1,1,20,time.time()))
    store.execute('INSERT INTO students VALUES (?,?,?,?,?)',('student','session','Alice','A001','nonce'))
    session=store.one('SELECT * FROM sessions')
    captured=int(time.time()//300)*300+1
    assert store.record(session,'student',frame(),captured)
    assert not store.record(session,'student',frame(),captured+20)
    assert store.record(session,'student',frame('different code'),captured+40)
    rows=store.rows('SELECT * FROM samples')
    assert len(rows)==2
    with zipfile.ZipFile(tmp_path/rows[0]['archive']) as archive:
        assert len(archive.namelist())==4  # two images + two timestamp manifests
    store.db.close()
    restarted=Store(tmp_path)
    assert restarted.one('SELECT * FROM sessions')['active']==0
    assert restarted.one('SELECT * FROM archives')['sealed']==1
    restarted.db.close()


def test_drive_retry_idempotency_encryption_and_retention(tmp_path):
    store=Store(tmp_path)
    cfg=Settings(data=tmp_path,password=PASSWORD,secret='x'*40,google_id='client',google_secret='secret',encryption_key=Fernet.generate_key().decode(),retention_days=1)
    drive=Drive(cfg,store)
    drive.save_tokens({'refresh_token':'private-refresh-token'})
    assert 'private-refresh-token' not in store.secret('google_tokens')
    assert drive.tokens()['refresh_token']=='private-refresh-token'
    store.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,NULL)',('session','Python','Lab','12345678',1,1,20,time.time()))
    store.execute('INSERT INTO students VALUES (?,?,?,?,?)',('student','session','Alice','A001','nonce'))
    store.record(store.one('SELECT * FROM sessions'),'student',frame(),time.time())
    store.execute('UPDATE sessions SET active=0')
    store.seal()
    committed=set()
    creates=[]
    failures=[True]
    def handler(request):
        path=request.url.path
        if path.endswith('/token'):return httpx.Response(200,json={'access_token':'access'})
        if path.endswith('/generateIds'):return httpx.Response(200,json={'ids':['allocated-id']})
        if path.endswith('/allocated-id'):
            if request.method=='DELETE':return httpx.Response(204)
            return httpx.Response(200 if 'allocated-id' in committed else 404,json={})
        if '/upload/' in path:
            creates.append('create')
            committed.add('allocated-id')
            if failures.pop() if failures else False:
                raise httpx.ReadError('Reply lost after successful upload')
            return httpx.Response(200,json={'id':'allocated-id'})
        if request.method=='GET':return httpx.Response(200,json={'files':[{'id':'folder'}]})
        return httpx.Response(200,json={'id':'folder'})
    async def verify_upload():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            row=store.one('SELECT * FROM archives')
            with pytest.raises(httpx.ReadError):await drive.upload(client,row)
            assert store.one('SELECT * FROM archives')['drive_id']=='allocated-id'
            await drive.upload(client,store.one('SELECT * FROM archives'))
            assert len(creates)==1
    asyncio.run(verify_upload())
    store.db.close()


def test_token_scope_and_expiry():
    token=issue('secret','student','one',ttl=-1)
    with pytest.raises(ValueError):verify('secret',token,'student')
    with pytest.raises(ValueError):verify('secret',issue('secret','teacher','teacher'),'student')


def test_focus_limit_and_teacher_disconnect_cleanup(client):
    session=classroom(client)
    joined=[join(client,session,str(i)) for i in range(3)]
    token=client.post('/api/ws-ticket').json()['token']
    with contextlib.ExitStack() as stack:
        sockets=[]
        for credentials in joined:
            ws=stack.enter_context(student_ws(client,credentials))
            ws.send_json({'token':credentials['token']});until(ws,'ready');sockets.append(ws)
        teachers=[]
        for i in range(3):
            ws=stack.enter_context(client.websocket_connect('/api/ws/teacher/'+session['id'],headers={'origin':ORIGIN}))
            ws.send_json({'token':token});until(ws,'roster');teachers.append(ws)
            ws.send_json({'type':'focus','student':joined[i]['student']})
            if i<2:assert until(sockets[i],'quality')['mode']=='focused'
        assert until(teachers[2],'error')['message']=='Focused stream limit reached'
        teachers[0].close()
        assert until(sockets[0],'quality')['mode']=='overview'
        teachers[2].send_json({'type':'focus','student':joined[2]['student']})
        assert until(sockets[2],'quality')['mode']=='focused'


def test_local_retention_without_drive(tmp_path):
    store=Store(tmp_path)
    cfg=Settings(data=tmp_path,password=PASSWORD,secret='x'*40,retention_days=1,google_id='',google_secret='',encryption_key='')
    captured=time.time()-3*86400
    store.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,NULL)',('session','Python','Lab','12345678',1,1,20,captured))
    store.execute('INSERT INTO students VALUES (?,?,?,?,?)',('student','session','Alice','A001','nonce'))
    store.record(store.one('SELECT * FROM sessions'),'student',frame(),captured)
    store.execute('UPDATE sessions SET active=0');store.seal()
    path=tmp_path/store.one('SELECT * FROM archives')['path']
    assert path.exists()
    asyncio.run(Drive(cfg,store).tick())
    assert not path.exists()
    assert not store.rows('SELECT * FROM samples')
    assert not store.rows('SELECT * FROM archives')
    store.db.close()


def test_durable_upload_retry(tmp_path,monkeypatch):
    store=Store(tmp_path)
    cfg=Settings(data=tmp_path,password=PASSWORD,secret='x'*40,google_id='client',google_secret='secret',encryption_key=Fernet.generate_key().decode())
    drive=Drive(cfg,store);drive.save_tokens({'refresh_token':'private'})
    store.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,NULL)',('session','Python','Lab','12345678',1,1,20,time.time()))
    store.execute('INSERT INTO students VALUES (?,?,?,?,?)',('student','session','Alice','A001','nonce'))
    store.record(store.one('SELECT * FROM sessions'),'student',frame(),time.time())
    store.execute('UPDATE sessions SET active=0');store.seal()
    async def access(client):return 'access'
    failures=[True]
    async def upload(client,row):
        if failures.pop() if failures else False:raise httpx.ReadError('offline')
    monkeypatch.setattr(drive,'access_token',access);monkeypatch.setattr(drive,'upload',upload)
    asyncio.run(drive.tick())
    row=store.one('SELECT * FROM archives')
    assert row['attempts']==1 and row['retry_at']>time.time() and row['uploaded']==0
    store.execute('UPDATE archives SET retry_at=0')
    asyncio.run(drive.tick())
    assert store.one('SELECT * FROM archives')['uploaded']==1
    store.db.close()
