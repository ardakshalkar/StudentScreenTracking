import asyncio
import base64
import contextlib
import hashlib
import hmac
import io
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .config import Settings
from .drive import Drive
from .security import issue, verify
from .storage import Store
from .student_auth import install_student_auth, student_claims

log = logging.getLogger('classroom')
MAX_FRAME = 1_000_000


@dataclass
class Live:
    id: str
    name: str
    student_id: str
    session: str
    ws: WebSocket | None = None
    frame: bytes | None = None
    frame_at: float = 0
    heartbeat_at: float = 0
    capture_at: float = 0
    last_record: float = 0
    seq: int = 0
    mode: str = 'overview'
    last_received: float = 0


def validate_frame(raw):
    if not 20 <= len(raw) <= MAX_FRAME:
        raise ValueError('Frame too large or empty')
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != 'WEBP' or image.width > 3840 or image.height > 3840 or image.width * image.height > 4_000_000:
            raise ValueError('Only bounded WebP screenshots accepted')
        image.load()


def create_app(settings=None):
    cfg = settings or Settings()
    live: dict[str, Live] = {}
    viewers = {}  # viewer -> {session, focus, expires}; focus leases expire in 15s
    limits = {}

    def throttle(key, count, period=60):
        now = time.monotonic()
        values = [t for t in limits.get(key, []) if now - t < period]
        if len(values) >= count:
            raise HTTPException(429, 'Too many requests; try again later')
        values.append(now)
        limits[key] = values
        if len(limits) > 2000:
            for old in list(limits)[:1000]:
                if not limits[old] or now - limits[old][-1] > period:
                    limits.pop(old, None)

    async def safe_send(ws, message):
        try:
            await asyncio.wait_for(ws.send_json(message), 2)
        except Exception:
            with contextlib.suppress(Exception):
                await ws.close(code=1013)

    async def update_modes():
        now = time.time()
        for key, viewer in list(viewers.items()):
            if viewer['expires'] < now:
                viewers.pop(key, None)
        focused = {v['focus'] for v in viewers.values() if v['focus']}
        for student in list(live.values()):
            mode = 'focused' if student.id in focused else 'overview'
            if student.mode != mode:
                student.mode = mode
                if student.ws:
                    await safe_send(student.ws, {'type': 'quality', 'mode': mode})

    async def recorder():
        while True:
            await asyncio.sleep(1)
            await update_modes()
            for student in list(live.values()):
                session = app.state.store.one('SELECT * FROM sessions WHERE id=?', (student.session,))
                now = time.time()
                if session and session['active'] and session['recording'] and student.ws and student.frame and now - student.heartbeat_at < 15 and now - student.last_record >= session['interval']:
                    student.last_record = now
                    raw, captured = student.frame, student.frame_at
                    try:
                        await asyncio.to_thread(app.state.store.record, session, student.id, raw, captured)
                    except Exception:
                        log.exception('Recording sample failed')
            app.state.store.seal()

    async def drive_worker():
        while True:
            try:
                await app.state.drive.tick()
                app.state.drive_error = None
            except Exception as exc:
                app.state.drive_error = type(exc).__name__
                log.warning('Drive maintenance will retry: %s', type(exc).__name__)
            await asyncio.sleep(30)

    @asynccontextmanager
    async def lifespan(app):
        cfg.validate()
        app.state.store = Store(cfg.data)
        app.state.drive = Drive(cfg, app.state.store)
        app.state.drive_error = None
        tasks = [asyncio.create_task(recorder()), asyncio.create_task(drive_worker())]
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        app.state.store.db.close()

    app = FastAPI(lifespan=lifespan)
    app.state.live = live
    app.state.settings = cfg
    ids = [x.strip() for x in cfg.extension_ids.split(',') if x.strip()]
    extension_regex = r'chrome-extension://(' + '|'.join(ids) + ')' if ids else r'chrome-extension://[a-p]{32}'
    app.add_middleware(CORSMiddleware, allow_origins=[cfg.origin], allow_origin_regex=extension_regex,
                       allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type', 'Authorization'])

    @app.middleware('http')
    async def headers_and_csrf(request, call_next):
        if request.method in ('POST', 'PATCH', 'DELETE') and request.url.path not in ('/api/join', '/api/student-auth/start', '/api/student-auth/exchange'):
            if request.headers.get('origin') != cfg.origin:
                return Response('Invalid request origin', status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    install_student_auth(app, cfg, throttle)

    def teacher(request: Request):
        try:
            return verify(cfg.secret, request.cookies.get('teacher', ''), 'teacher')
        except ValueError:
            raise HTTPException(401, 'Teacher login required')

    def session(sid, active=False):
        result = app.state.store.one('SELECT * FROM sessions WHERE id=?', (sid,))
        if not result or (active and not result['active']):
            raise HTTPException(404, 'Classroom session unavailable')
        return result

    class Login(BaseModel):
        password: str = Field(max_length=200)

    @app.post('/api/login')
    def login(body: Login, request: Request, response: Response):
        throttle('login:' + request.client.host, 10)
        if not hmac.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(cfg.password.encode()).digest()):
            raise HTTPException(401, 'Incorrect password')
        response.set_cookie('teacher', issue(cfg.secret, 'teacher', 'teacher'), httponly=True,
                            secure=cfg.origin.startswith('https:'), samesite='strict', max_age=43200, path='/api')
        return {'ok': True}

    @app.post('/api/logout')
    def logout(response: Response, _=Depends(teacher)):
        response.delete_cookie('teacher', path='/api')
        return {'ok': True}

    @app.get('/api/me')
    def me(_=Depends(teacher)):
        return {'teacher': True}

    class NewSession(BaseModel):
        course: str = Field(min_length=1, max_length=100)
        title: str = Field(min_length=1, max_length=100)
        recording: bool = False
        interval: int = Field(default=20, ge=5, le=3600)

    @app.get('/api/sessions')
    def sessions(_=Depends(teacher)):
        return app.state.store.rows('SELECT * FROM sessions ORDER BY created DESC')

    @app.post('/api/sessions')
    def new_session(body: NewSession, _=Depends(teacher)):
        if app.state.store.one('SELECT id FROM sessions WHERE active=1'):
            raise HTTPException(409, 'End the active classroom first')
        live.clear()
        sid = uuid.uuid4().hex
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
        app.state.store.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,NULL)',
            (sid, body.course, body.title, code, 1, body.recording, body.interval, time.time()))
        return session(sid)

    class Recording(BaseModel):
        recording: bool
        interval: int = Field(ge=5, le=3600)

    @app.patch('/api/sessions/{sid}/recording')
    async def recording(sid: str, body: Recording, _=Depends(teacher)):
        session(sid, True)
        app.state.store.execute('UPDATE sessions SET recording=?,interval=? WHERE id=?', (body.recording, body.interval, sid))
        for student in list(live.values()):
            if student.session == sid and student.ws:
                await safe_send(student.ws, {'type': 'recording', **body.model_dump()})
        return session(sid)

    @app.post('/api/sessions/{sid}/end')
    async def end(sid: str, _=Depends(teacher)):
        session(sid, True)
        app.state.store.execute('UPDATE sessions SET active=0,ended=? WHERE id=?', (time.time(), sid))
        for student in list(live.values()):
            if student.session == sid:
                ws = student.ws
                student.frame = None
                student.ws = None
                if ws:
                    await safe_send(ws, {'type': 'session_ended'})
                    with contextlib.suppress(Exception):
                        await ws.close(code=4004)
        app.state.store.seal()
        return {'ok': True}

    class Join(BaseModel):
        code: str = Field(min_length=8, max_length=8, pattern=r'^[A-Z2-9]+$')
        name: str = Field(min_length=1, max_length=80)
        student_id: str = Field(min_length=1, max_length=254)

    @app.post('/api/join')
    def join(body: Join, request: Request):
        throttle('join:' + request.client.host, 120)
        found = app.state.store.one('SELECT * FROM sessions WHERE code=? AND active=1', (body.code,))
        if not found:
            raise HTTPException(404, 'Invalid or ended classroom code')
        identity = None
        if cfg.student_auth == 'google':
            try:
                payload, identity = student_claims(cfg, request.headers.get('authorization', '').removeprefix('Bearer '))
                if payload.get('session') != found['id']:
                    raise ValueError('Sign in for this classroom')
            except ValueError as exc:
                raise HTTPException(401, str(exc))
            body.name, body.student_id = identity['name'], identity['email']
        existing = app.state.store.one('SELECT * FROM students WHERE session_id=? AND student_id=?', (found['id'], body.student_id))
        if existing and not identity:
            raise HTTPException(409, 'This ID already joined. Resume from the original extension or use a unique ID.')
        count = app.state.store.one('SELECT COUNT(*) AS n FROM students WHERE session_id=?', (found['id'],))['n']
        if not existing and count >= cfg.max_students:
            raise HTTPException(409, 'Classroom is full')
        student, nonce = (existing['id'], existing['token_nonce']) if existing else (uuid.uuid4().hex, secrets.token_hex(16))
        if not existing:
            app.state.store.execute('INSERT INTO students VALUES (?,?,?,?,?)', (student, found['id'], body.name, body.student_id, nonce))
        return {'token': issue(cfg.secret, 'student', student, session=found['id'], nonce=nonce, **({'google': identity} if identity else {})),
                'session': found['id'], 'student': student, 'recording': bool(found['recording']), 'interval': found['interval'],
                'email': identity['email'] if identity else None}

    @app.post('/api/ws-ticket')
    def ticket(_=Depends(teacher)):
        return {'token': issue(cfg.secret, 'teacher', 'teacher', ttl=43200)}

    @app.get('/api/sessions/{sid}/samples')
    def samples(sid: str, _=Depends(teacher)):
        session(sid)
        return app.state.store.rows('SELECT s.id,s.student,s.captured,t.name,t.student_id FROM samples s JOIN students t ON t.id=s.student WHERE s.session_id=? ORDER BY captured LIMIT 20000', (sid,))

    @app.get('/api/samples/{sample_id}')
    def sample(sample_id: str, _=Depends(teacher)):
        row = app.state.store.one('SELECT * FROM samples WHERE id=?', (sample_id,))
        if not row:
            raise HTTPException(404)
        try:
            return Response(app.state.store.sample_bytes(row), media_type='image/webp')
        except (FileNotFoundError, KeyError):
            raise HTTPException(404)

    @app.get('/api/drive')
    def drive_status(_=Depends(teacher)):
        return {'configured': cfg.google_enabled, 'connected': bool(app.state.store.secret('google_tokens')),
            'pending': app.state.store.one('SELECT COUNT(*) AS n FROM archives WHERE uploaded=0')['n'],
            'last_error': app.state.drive_error, 'retention_days': cfg.retention_days}

    @app.get('/api/drive/connect')
    def drive_connect(_=Depends(teacher)):
        if not cfg.google_enabled:
            raise HTTPException(400, 'Google Drive is not configured')
        nonce = secrets.token_urlsafe(32)
        app.state.store.set_secret('oauth_state', issue(cfg.secret, 'oauth', nonce, ttl=600))
        params = {'client_id': cfg.google_id, 'redirect_uri': cfg.origin + '/api/drive/callback',
            'response_type': 'code', 'scope': 'https://www.googleapis.com/auth/drive.file',
            'access_type': 'offline', 'prompt': 'consent', 'state': nonce}
        return RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params))

    @app.get('/api/drive/callback')
    async def drive_callback(state: str = '', code: str = ''):
        try:
            expected = verify(cfg.secret, app.state.store.secret('oauth_state') or '', 'oauth')['sub']
            if not hmac.compare_digest(state, expected) or not code:
                raise ValueError()
        except ValueError:
            raise HTTPException(400, 'Invalid or expired OAuth state')
        app.state.store.set_secret('oauth_state', '')
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post('https://oauth2.googleapis.com/token', data={
                'client_id': cfg.google_id, 'client_secret': cfg.google_secret, 'code': code,
                'redirect_uri': cfg.origin + '/api/drive/callback', 'grant_type': 'authorization_code'})
            if response.status_code != 200:
                raise HTTPException(400, 'Google authorization failed; reconnect from dashboard')
            app.state.drive.save_tokens(response.json())
        return RedirectResponse(cfg.origin + '/?drive=connected')

    async def authenticate_ws(ws, role):
        origin = ws.headers.get('origin', '')
        if role == 'teacher' and origin != cfg.origin:
            await ws.close(code=4403)
            return None
        if role == 'student' and origin:
            extension_id = origin.removeprefix('chrome-extension://')
            if not origin.startswith('chrome-extension://') or (ids and extension_id not in ids):
                await ws.close(code=4403)
                return None
        await ws.accept()
        try:
            body = await asyncio.wait_for(ws.receive_json(), 5)
            payload = verify(cfg.secret, body.get('token', ''), role)
            if role == 'student' and cfg.student_auth == 'google':
                student_claims(cfg, body.get('token', ''), role='student')
            return payload
        except Exception:
            await ws.close(code=4401)
            return None

    @app.websocket('/api/ws/student')
    async def student_socket(ws: WebSocket):
        auth = await authenticate_ws(ws, 'student')
        if not auth:
            return
        row = app.state.store.one('SELECT * FROM students WHERE id=? AND token_nonce=? AND session_id=?', (auth['sub'], auth.get('nonce'), auth.get('session')))
        found = app.state.store.one('SELECT * FROM sessions WHERE id=? AND active=1', (auth.get('session'),))
        if not row or not found:
            await ws.close(code=4004)
            return
        student = live.setdefault(row['id'], Live(row['id'], row['name'], row['student_id'], row['session_id']))
        previous = student.ws
        student.ws = ws
        student.heartbeat_at = time.time()
        if previous:
            await previous.close(code=4009)
        await safe_send(ws, {'type': 'ready', 'mode': student.mode, 'recording': bool(found['recording']), 'interval': found['interval']})
        try:
            while True:
                message = await asyncio.wait_for(ws.receive(), 20)
                if student.ws is not ws:
                    break
                if auth['exp'] < time.time():
                    await ws.close(code=4401)
                    break
                if message['type'] == 'websocket.disconnect':
                    break
                if not app.state.store.one('SELECT id FROM sessions WHERE id=? AND active=1', (student.session,)):
                    await ws.close(code=4004)
                    break
                raw = message.get('bytes')
                now = time.time()
                if raw is not None:
                    # Hard ingress cap; the extension itself uses ACK backpressure.
                    if now - student.last_received < .18:
                        await safe_send(ws, {'type': 'ack'})
                        continue
                    student.last_received = now
                    try:
                        await asyncio.to_thread(validate_frame, raw)
                    except (ValueError, OSError, UnidentifiedImageError):
                        await ws.close(code=4400)
                        break
                    student.frame, student.frame_at = raw, now
                    student.heartbeat_at = student.capture_at = now
                    student.seq += 1
                    await safe_send(ws, {'type': 'ack'})
                elif message.get('text'):
                    import json
                    body = json.loads(message['text'])
                    if body.get('type') == 'heartbeat':
                        student.heartbeat_at = now
                        if body.get('captureHealthy') is True:
                            student.capture_at = now
                        current = session(student.session)
                        await safe_send(ws, {'type': 'heartbeat', 'recording': bool(current['recording']), 'interval': current['interval']})
                    elif body.get('type') == 'stop':
                        student.frame = None
                        await ws.close(code=1000)
                        break
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, RuntimeError):
            pass
        finally:
            if student.ws is ws:
                student.ws = None
                student.frame = None

    @app.websocket('/api/ws/teacher/{sid}')
    async def teacher_socket(ws: WebSocket, sid: str):
        auth = await authenticate_ws(ws, 'teacher')
        if not auth:
            return
        if not app.state.store.one('SELECT id FROM sessions WHERE id=?', (sid,)):
            await ws.close(code=4404)
            return
        viewer_id = uuid.uuid4().hex
        viewer = {'session': sid, 'focus': None, 'expires': time.time() + 15}
        viewers[viewer_id] = viewer
        sent = {}

        async def sender():
            while time.time() < auth['exp']:
                current = session(sid)
                students = []
                for student in list(live.values()):
                    if student.session != sid:
                        continue
                    now = time.time()
                    status = 'disconnected' if not student.ws or now - student.heartbeat_at > 15 else ('frozen' if now - student.capture_at > 15 else 'sharing')
                    students.append({'id': student.id, 'name': student.name, 'student_id': student.student_id,
                        'status': status, 'frame_at': student.frame_at, 'heartbeat_at': student.heartbeat_at,
                        'capture_at': student.capture_at, 'mode': student.mode})
                    if student.frame and sent.get(student.id) != student.seq:
                        # One newest frame per student; no FIFO or accumulated history.
                        await asyncio.wait_for(ws.send_json({'type': 'frame', 'student': student.id,
                            'at': student.frame_at, 'data': base64.b64encode(student.frame).decode()}), 3)
                        sent[student.id] = student.seq
                await asyncio.wait_for(ws.send_json({'type': 'roster', 'students': students, 'active': bool(current['active']),
                    'recording': bool(current['recording']), 'interval': current['interval']}), 3)
                await asyncio.sleep(.25)
            await ws.close(code=4401)

        send_task = asyncio.create_task(sender())
        try:
            while not send_task.done():
                body = await asyncio.wait_for(ws.receive_json(), 15)
                viewer['expires'] = time.time() + 15
                if body.get('type') == 'focus':
                    target = body.get('student')
                    if target is not None and (target not in live or live[target].session != sid):
                        continue
                    other = {v['focus'] for key, v in viewers.items() if key != viewer_id and v['focus'] and v['expires'] > time.time()}
                    if target and target not in other and len(other) >= cfg.max_focus:
                        await safe_send(ws, {'type': 'error', 'message': 'Focused stream limit reached'})
                        continue
                    viewer['focus'] = target
                    await update_modes()
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, RuntimeError):
            pass
        finally:
            send_task.cancel()
            await asyncio.gather(send_task, return_exceptions=True)
            viewers.pop(viewer_id, None)
            await update_modes()

    @app.get('/api/health')
    def health():
        return {'ok': True}

    return app


app = create_app()
