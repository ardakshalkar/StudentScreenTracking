"""Google student sign-in, separate from the teacher's optional Drive grant."""
import asyncio
import base64
import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel, Field
import requests

from .security import issue, verify


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')


def checked_identity(claims, settings, nonce=None):
    if nonce is not None and not hmac.compare_digest(str(claims.get('nonce', '')), nonce):
        raise ValueError('Google login nonce mismatch')
    email = str(claims.get('email', '')).strip().lower()
    if claims.get('email_verified') is not True or email.count('@') != 1 or not claims.get('sub'):
        raise ValueError('A verified Google email is required')
    domain = email.rsplit('@', 1)[1]
    if domain not in settings.allowed_student_domains:
        raise ValueError('This email domain is not allowed for students')
    # Google is authoritative for Gmail and for managed Workspace identities.
    # An email suffix alone is insufficient proof of Workspace membership.
    if domain != 'gmail.com' and str(claims.get('hd', '')).lower() != domain:
        raise ValueError('Use a managed Google Workspace account in an allowed domain')
    return {'sub': claims['sub'], 'email': email, 'email_verified': True,
            'hd': claims.get('hd', ''), 'name': str(claims.get('name') or email)[:80]}


def verify_google_token(token, audience):
    class BoundedRequest(GoogleRequest):
        def __call__(self, *args, **kwargs):
            kwargs['timeout'] = 10
            return super().__call__(*args, **kwargs)
    with requests.Session() as session:
        # Verifies Google's signature, audience, issuer and expiry, not just JWT decoding.
        return id_token.verify_oauth2_token(token, BoundedRequest(session=session), audience=audience)


def student_claims(settings, token, role='student_identity'):
    payload = verify(settings.secret, token, role)
    identity = payload.get('google')
    if not isinstance(identity, dict):
        raise ValueError('Google student sign-in required')
    return payload, checked_identity(identity, settings)


def install_student_auth(app, cfg, throttle):
    class Start(BaseModel):
        code: str = Field(pattern=r'^[A-Z2-9]{8}$')
        extension_id: str = Field(pattern=r'^[a-p]{32}$')
        challenge: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')
        client_state: str = Field(min_length=32, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')

    class Exchange(BaseModel):
        grant: str = Field(min_length=32, max_length=128)
        verifier: str = Field(min_length=43, max_length=128, pattern=r'^[A-Za-z0-9._~-]+$')

    def enabled():
        if cfg.student_auth != 'google':
            raise HTTPException(404, 'Google student sign-in is not enabled')

    def active(sid):
        if not app.state.store.one('SELECT id FROM sessions WHERE id=? AND active=1', (sid,)):
            raise HTTPException(403, 'Classroom has ended')

    @app.get('/api/student-auth/config')
    def config():
        result={'mode': cfg.student_auth, 'allowed_domains': sorted(cfg.allowed_student_domains)}
        if cfg.lan_http:result['lan_http']=True
        return result

    @app.post('/api/student-auth/start')
    def start(body: Start, request: Request):
        enabled()
        throttle('student-auth:' + request.client.host, 120)
        expected_origin = 'chrome-extension://' + body.extension_id
        ids = {value.strip() for value in cfg.extension_ids.split(',') if value.strip()}
        if request.headers.get('origin') != expected_origin or (ids and body.extension_id not in ids):
            raise HTTPException(403, 'Unapproved extension')
        classroom = app.state.store.one('SELECT id FROM sessions WHERE code=? AND active=1', (body.code,))
        if not classroom:
            raise HTTPException(404, 'Invalid or ended classroom code')
        state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        app.state.store.put_flow('oauth:' + state, {
            'redirect': f'https://{body.extension_id}.chromiumapp.org/student-login', 'nonce': nonce,
            'verifier': verifier, 'challenge': body.challenge, 'client_state': body.client_state, 'session': classroom['id'],
        }, 600)
        params = {'client_id': cfg.student_google_id, 'redirect_uri': cfg.origin + '/api/student-auth/callback',
            'response_type': 'code', 'scope': 'openid email profile', 'state': state, 'nonce': nonce,
            'code_challenge': challenge(verifier), 'code_challenge_method': 'S256', 'prompt': 'select_account'}
        if len(cfg.allowed_student_domains) == 1 and 'gmail.com' not in cfg.allowed_student_domains:
            params['hd'] = next(iter(cfg.allowed_student_domains))  # UX hint; enforced again after verification.
        return {'url': 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)}

    @app.get('/api/student-auth/callback')
    async def callback(state: str = '', code: str = '', error: str = ''):
        enabled()
        flow = app.state.store.take_flow('oauth:' + state)
        if not flow:
            raise HTTPException(400, 'Invalid, expired, or reused Google login state')
        result = {'client_state': flow['client_state']}
        try:
            active(flow['session'])
            if error or not code:
                raise ValueError('Google sign-in was cancelled')
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post('https://oauth2.googleapis.com/token', data={
                    'client_id': cfg.student_google_id, 'client_secret': cfg.student_google_secret,
                    'redirect_uri': cfg.origin + '/api/student-auth/callback', 'grant_type': 'authorization_code',
                    'code': code, 'code_verifier': flow['verifier']})
                response.raise_for_status()
                tokens = response.json()
            try:
                claims = await asyncio.to_thread(verify_google_token, tokens['id_token'], cfg.student_google_id)
            except Exception:
                # Verification libraries can include token contents in diagnostic
                # errors. Never reflect those diagnostics into a redirect URL.
                raise ValueError('Google identity could not be verified. Please sign in again.') from None
            identity = checked_identity(claims, cfg, flow['nonce'])
            grant = secrets.token_urlsafe(32)
            app.state.store.put_flow('grant:' + grant, {'google': identity, 'challenge': flow['challenge'], 'session': flow['session']}, 60)
            result['grant'] = grant
            # Google access/ID tokens are discarded, not stored or sent to students.
        except ValueError as exc:
            result['error'] = str(exc)
        except HTTPException as exc:
            result['error'] = str(exc.detail)
        except Exception:
            result['error'] = 'Google sign-in could not be verified. Please try again.'
        return RedirectResponse(flow['redirect'] + '#' + urlencode(result), status_code=303)

    @app.post('/api/student-auth/exchange')
    def exchange(body: Exchange, request: Request):
        enabled()
        throttle('student-exchange:' + request.client.host, 120)
        flow = app.state.store.take_flow('grant:' + body.grant)
        if not flow or not hmac.compare_digest(flow['challenge'], challenge(body.verifier)):
            raise HTTPException(401, 'Invalid, expired, or reused student login grant')
        active(flow['session'])
        identity = checked_identity(flow['google'], cfg)
        return {'token': issue(cfg.secret, 'student_identity', identity['sub'], ttl=3600, google=identity, session=flow['session']),
                'email': identity['email'], 'name': identity['name']}
