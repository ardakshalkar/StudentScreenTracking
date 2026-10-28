import base64
import hashlib
import hmac
import json
import time


def issue(secret, role, subject, ttl=43200, **extra):
    payload = json.dumps(dict(role=role, sub=subject, exp=time.time() + ttl, **extra), separators=(',', ':')).encode()
    data = base64.urlsafe_b64encode(payload).decode().rstrip('=')
    signature = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return data + '.' + signature


def verify(secret, token, role):
    try:
        data, signature = token.split('.')
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError('signature')
        payload = json.loads(base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)))
        if payload['role'] != role or payload['exp'] <= time.time():
            raise ValueError('expired or wrong role')
        return payload
    except Exception as exc:
        raise ValueError('Invalid credentials') from exc
