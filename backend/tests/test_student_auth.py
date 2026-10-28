import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.security import issue, verify
from backend.student_auth import challenge, checked_identity
import backend.student_auth as auth_module

ORIGIN='http://localhost:5173'
EXTENSION='a'*32
PASSWORD='google-tests-password'


@pytest.fixture
def google_client(tmp_path):
    cfg=Settings(data=tmp_path,password=PASSWORD,secret='g'*40,student_auth='google',
        student_domains='school.edu, gmail.com',student_google_id='student-client',student_google_secret='student-secret',extension_ids=EXTENSION)
    with TestClient(create_app(cfg)) as client:
        client.headers['origin']=ORIGIN
        client.post('/api/login',json={'password':PASSWORD})
        classroom=client.post('/api/sessions',json={'course':'Python','title':'Google class'}).json()
        yield client,cfg,classroom


def claims(email='alice@school.edu',**overrides):
    return dict(sub='google-subject-alice',email=email,email_verified=True,hd='school.edu',name='Verified Alice',**overrides)


def identity_token(cfg,classroom,identity=None):
    identity=identity or claims()
    return issue(cfg.secret,'student_identity',identity['sub'],google=identity,session=classroom['id'])


def join(client,classroom,token=None):
    headers={'Authorization':'Bearer '+token} if token else {}
    return client.post('/api/join',headers=headers,json={'code':classroom['code'],'name':'Forged Name','student_id':'forged@other.test'})


def test_google_required_and_verified_email_overrides_user_input(google_client):
    client,cfg,classroom=google_client
    assert client.get('/api/student-auth/config').json()=={'mode':'google','allowed_domains':['gmail.com','school.edu']}
    assert join(client,classroom).status_code==401
    response=join(client,classroom,identity_token(cfg,classroom))
    assert response.status_code==200,response.text
    joined=response.json()
    assert joined['email']=='alice@school.edu'
    student=client.app.state.store.one('SELECT * FROM students')
    assert student['name']=='Verified Alice' and student['student_id']=='alice@school.edu'
    signed=verify(cfg.secret,joined['token'],'student')
    assert signed['google']['email']=='alice@school.edu'
    # Reauthentication may resume the same identity even after local storage loss.
    assert join(client,classroom,identity_token(cfg,classroom)).json()['student']==joined['student']


@pytest.mark.parametrize('identity',[
    {'sub':'alice','email':'alice@other.edu','email_verified':True,'hd':'other.edu'},
    {'sub':'alice','email':'alice@sub.school.edu','email_verified':True,'hd':'school.edu'},
    {'sub':'alice','email':'alice@school.edu.evil.test','email_verified':True,'hd':'school.edu'},
    {'sub':'alice','email':'alice@school.edu','email_verified':False,'hd':'school.edu'},
    {'sub':'alice','email':'alice@school.edu','email_verified':True},
    {'sub':'alice','email':'alice@school.edu','email_verified':True,'hd':'other.edu'},
])
def test_reject_disallowed_unverified_and_unmanaged_accounts(google_client,identity):
    client,cfg,classroom=google_client
    assert join(client,classroom,identity_token(cfg,classroom,identity)).status_code==401


def test_allowlisted_gmail_and_case_normalization(google_client):
    client,cfg,classroom=google_client
    identity={'sub':'gmail-alice','email':'Alice@GMAIL.COM','email_verified':True,'name':'Alice'}
    assert join(client,classroom,identity_token(cfg,classroom,identity)).json()['email']=='alice@gmail.com'


def test_websockets_reject_legacy_or_disallowed_credentials(google_client):
    client,cfg,classroom=google_client
    joined=join(client,classroom,identity_token(cfg,classroom)).json()
    payload=verify(cfg.secret,joined['token'],'student')
    legacy=issue(cfg.secret,'student',payload['sub'],session=payload['session'],nonce=payload['nonce'])
    for token in (legacy,issue(cfg.secret,'student',payload['sub'],session=payload['session'],nonce=payload['nonce'],google=claims('alice@evil.test'))):
        with client.websocket_connect('/api/ws/student',headers={'origin':'chrome-extension://'+EXTENSION}) as ws:
            ws.send_json({'token':token})
            assert ws.receive()['code']==4401
    with client.websocket_connect('/api/ws/student',headers={'origin':'chrome-extension://'+EXTENSION}) as ws:
        ws.send_json({'token':joined['token']})
        assert ws.receive_json()['type']=='ready'


def test_oauth_state_pkce_and_single_use_exchange(google_client,monkeypatch):
    client,cfg,classroom=google_client
    verifier='v'*64
    response=client.post('/api/student-auth/start',headers={'origin':'chrome-extension://'+EXTENSION},json={
        'code':classroom['code'],'extension_id':EXTENSION,'challenge':challenge(verifier),'client_state':'c'*40})
    assert response.status_code==200,response.text
    params=parse_qs(urlparse(response.json()['url']).query)
    assert params['scope']==['openid email profile']
    assert params['code_challenge_method']==['S256']
    assert params['client_id']==['student-client']
    assert 'drive' not in response.json()['url']
    state=params['state'][0]
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,data):
            assert url=='https://oauth2.googleapis.com/token'
            assert data['client_secret']=='student-secret'
            assert challenge(data['code_verifier'])==params['code_challenge'][0]
            return httpx.Response(200,json={'id_token':'signed-google-token','access_token':'must-not-leave-server'},request=httpx.Request('POST',url))
    monkeypatch.setattr(auth_module.httpx,'AsyncClient',FakeClient)
    def verify_google(token,audience):
        assert token=='signed-google-token' and audience=='student-client'
        return {**claims(),'nonce':params['nonce'][0]}
    monkeypatch.setattr(auth_module,'verify_google_token',verify_google)
    callback=client.get('/api/student-auth/callback',params={'code':'one-time-google-code','state':state},follow_redirects=False)
    assert callback.status_code==303
    redirect=urlparse(callback.headers['location'])
    assert redirect.netloc==EXTENSION+'.chromiumapp.org' and redirect.path=='/student-login'
    result=parse_qs(redirect.fragment)
    assert result['client_state']==['c'*40] and 'error' not in result
    assert 'must-not-leave-server' not in callback.headers['location']
    assert client.get('/api/student-auth/callback',params={'code':'replay','state':state}).status_code==400
    token_response=client.post('/api/student-auth/exchange',json={'grant':result['grant'][0],'verifier':verifier})
    assert token_response.status_code==200,token_response.text
    assert token_response.json()['email']=='alice@school.edu'
    assert client.post('/api/student-auth/exchange',json={'grant':result['grant'][0],'verifier':verifier}).status_code==401
    assert join(client,classroom,token_response.json()['token']).status_code==200


def test_wrong_pkce_expired_grant_and_classroom_binding(google_client):
    client,cfg,classroom=google_client
    client.app.state.store.put_flow('grant:'+'a'*40,{'google':claims(),'challenge':challenge('v'*64),'session':classroom['id']},60)
    assert client.post('/api/student-auth/exchange',json={'grant':'a'*40,'verifier':'wrong'*13}).status_code==401
    client.app.state.store.put_flow('grant:'+'b'*40,{'google':claims(),'challenge':challenge('v'*64),'session':classroom['id']},-1)
    assert client.post('/api/student-auth/exchange',json={'grant':'b'*40,'verifier':'v'*64}).status_code==401
    wrong_session={**classroom,'id':'not-this-classroom'}
    assert join(client,classroom,identity_token(cfg,wrong_session)).status_code==401
    client.post('/api/sessions/'+classroom['id']+'/end')
    assert join(client,classroom,identity_token(cfg,classroom)).status_code==404


def test_nonce_and_config_fail_closed(tmp_path):
    cfg=Settings(data=tmp_path,password=PASSWORD,secret='x'*40,student_auth='google')
    with pytest.raises(RuntimeError):cfg.validate()
    cfg.student_google_id='id';cfg.student_google_secret='secret';cfg.student_domains='*.school.edu'
    with pytest.raises(RuntimeError):cfg.validate()
    cfg.student_domains='school.edu';cfg.validate()
    with pytest.raises(ValueError):checked_identity({**claims(),'nonce':'wrong'},cfg,nonce='expected')


def test_login_start_rejects_unregistered_extension_and_bad_classroom(google_client):
    client,cfg,classroom=google_client
    body={'code':classroom['code'],'extension_id':'b'*32,'challenge':challenge('v'*64),'client_state':'c'*40}
    assert client.post('/api/student-auth/start',headers={'origin':'chrome-extension://'+'b'*32},json=body).status_code==403
    body.update(extension_id=EXTENSION,code='ZZZZZZZZ')
    assert client.post('/api/student-auth/start',headers={'origin':'chrome-extension://'+EXTENSION},json=body).status_code==404
