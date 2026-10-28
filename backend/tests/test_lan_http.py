import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def cfg(tmp_path,**changes):
    return Settings(data=tmp_path,password='lan-test-password',secret='lan-test-secret-at-least-32-characters',origin='http://192.168.1.20:5173',**changes)


def test_http_lan_requires_explicit_server_opt_in(tmp_path):
    with pytest.raises(RuntimeError,match='ALLOW_LAN_HTTP'):cfg(tmp_path).validate()
    cfg(tmp_path,allow_lan_http=True).validate()


@pytest.mark.parametrize('origin',['http://8.8.8.8','http://172.15.0.1','http://172.32.0.1','http://169.254.0.1','http://teacher.local','http://school.edu','http://100.64.0.1'])
def test_allow_lan_never_enables_public_http(tmp_path,origin):
    settings=cfg(tmp_path,allow_lan_http=True);settings.origin=origin
    with pytest.raises(RuntimeError):settings.validate()


def test_google_login_and_drive_oauth_cannot_use_lan_http(tmp_path):
    with pytest.raises(RuntimeError,match='code-only'):cfg(tmp_path,allow_lan_http=True,student_auth='google').validate()
    with pytest.raises(RuntimeError,match='Google Drive'):cfg(tmp_path,allow_lan_http=True,google_id='id',google_secret='secret',encryption_key='key').validate()


def test_lan_teacher_and_student_protocol_with_exact_origin(tmp_path):
    settings=cfg(tmp_path,allow_lan_http=True)
    with TestClient(create_app(settings)) as client:
        client.headers['origin']=settings.origin
        assert client.get('/api/student-auth/config').json()=={'mode':'code','allowed_domains':[],'lan_http':True}
        response=client.post('/api/login',json={'password':settings.password})
        assert response.status_code==200
        assert 'HttpOnly' in response.headers['set-cookie'] and 'Secure;' not in response.headers['set-cookie']
        classroom=client.post('/api/sessions',json={'course':'Wi-Fi','title':'LAN test'}).json()
        joined=client.post('/api/join',json={'code':classroom['code'],'name':'Alice','student_id':'LAN-1'}).json()
        with client.websocket_connect('/api/ws/student',headers={'origin':'chrome-extension://'+'a'*32}) as student:
            student.send_json({'token':joined['token']})
            assert student.receive_json()['type']=='ready'
        assert client.post('/api/logout',headers={'origin':'http://localhost:5173'}).status_code==403
        token=client.post('/api/ws-ticket').json()['token']
        with client.websocket_connect('/api/ws/teacher/'+classroom['id'],headers={'origin':settings.origin}) as teacher:
            teacher.send_json({'token':token})
            assert teacher.receive_json()['type']=='roster'
