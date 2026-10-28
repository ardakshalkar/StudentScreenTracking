"""Optional OAuth + durable, idempotent archive uploader; no student credentials."""
import json
import time

import httpx
from cryptography.fernet import Fernet


class Drive:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store

    def save_tokens(self, tokens):
        old = self.tokens() or {}
        old.update(tokens)
        self.store.set_secret('google_tokens', Fernet(self.settings.encryption_key.encode()).encrypt(json.dumps(old).encode()).decode())

    def tokens(self):
        value = self.store.secret('google_tokens')
        if not value or not self.settings.google_enabled:
            return None
        return json.loads(Fernet(self.settings.encryption_key.encode()).decrypt(value.encode()))

    async def access_token(self, client):
        tokens = self.tokens()
        if not tokens or not tokens.get('refresh_token'):
            return None
        response = await client.post('https://oauth2.googleapis.com/token', data={
            'client_id': self.settings.google_id, 'client_secret': self.settings.google_secret,
            'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token',
        })
        response.raise_for_status()
        return response.json()['access_token']

    async def folder(self, client, name, parent='root'):
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        response = await client.get('https://www.googleapis.com/drive/v3/files', params={
            'q': f"name='{escaped}' and '{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            'fields': 'files(id)', 'pageSize': 1,
        })
        response.raise_for_status()
        found = response.json()['files']
        if found:
            return found[0]['id']
        response = await client.post('https://www.googleapis.com/drive/v3/files', json={
            'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent],
        })
        response.raise_for_status()
        return response.json()['id']

    async def upload(self, client, row):
        # Persist a preallocated Drive ID BEFORE upload. Retrying the same ID cannot
        # create a duplicate, even if Google committed a request whose reply was lost.
        drive_id = row['drive_id']
        if not drive_id:
            result = await client.get('https://www.googleapis.com/drive/v3/files/generateIds', params={'count': 1, 'space': 'drive'})
            result.raise_for_status()
            drive_id = result.json()['ids'][0]
            self.store.execute('UPDATE archives SET drive_id=? WHERE path=?', (drive_id, row['path']))
        existing = await client.get(f'https://www.googleapis.com/drive/v3/files/{drive_id}', params={'fields': 'id'})
        if existing.status_code == 200:
            return
        if existing.status_code != 404:
            existing.raise_for_status()
        session = self.store.one('SELECT * FROM sessions WHERE id=?', (row['session_id'],))
        parent = await self.folder(client, 'Classroom Screens')
        parent = await self.folder(client, session['course'], parent)
        parent = await self.folder(client, session['title'] + ' ' + session['id'][:8], parent)
        student = self.store.one('SELECT * FROM students WHERE id=?', (row['student'],))
        parent = await self.folder(client, student['student_id'] + ' ' + row['student'][:8], parent)
        metadata = json.dumps({'id': drive_id, 'name': row['path'].split('/')[-1], 'parents': [parent], 'mimeType': 'application/zip'})
        # Drive requires multipart/related (not form-data). Stream bounded chunks.
        boundary = 'classroom_archive_boundary'
        prefix = f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadata}\r\n--{boundary}\r\nContent-Type: application/zip\r\n\r\n'.encode()
        suffix = f'\r\n--{boundary}--\r\n'.encode()
        async def parts():
            yield prefix
            with (self.store.root / row['path']).open('rb') as archive:
                while chunk := archive.read(65536):
                    yield chunk
            yield suffix
        response = await client.post('https://www.googleapis.com/upload/drive/v3/files', params={'uploadType': 'multipart'},
            content=parts(), headers={'Content-Type': 'multipart/related; boundary=' + boundary,
                'Content-Length': str(len(prefix) + (self.store.root / row['path']).stat().st_size + len(suffix))})
        response.raise_for_status()

    async def tick(self):
        connected = self.settings.google_enabled and bool(self.store.secret('google_tokens'))
        cutoff = time.time() - self.settings.retention_days * 86400
        expired = self.store.rows('SELECT * FROM archives WHERE created<? AND sealed=1', (cutoff,))
        # Local retention must still run when Google credentials expire or Google
        # is unavailable. Remote deletion metadata survives until a successful retry.
        for row in expired:
            (self.store.root / row['path']).unlink(missing_ok=True)
            self.store.execute('DELETE FROM samples WHERE archive=?', (row['path'],))
            if not row['drive_id']:
                self.store.delete_archive(row)
        async with httpx.AsyncClient(timeout=60) as client:
            token = await self.access_token(client) if connected else None
            if token:
                client.headers['Authorization'] = 'Bearer ' + token
            # Retention applies to both local and Drive copies. Failed remote deletes
            # retain metadata for retry, but local student images are still removed.
            for row in expired:
                if not row['drive_id']:
                    continue
                if row['drive_id']:
                    if not token:
                        continue
                    response = await client.delete('https://www.googleapis.com/drive/v3/files/' + row['drive_id'])
                    if response.status_code not in (204, 404):
                        continue
                self.store.delete_archive(row)
            if not token:
                return
            rows = self.store.rows('SELECT * FROM archives WHERE sealed=1 AND uploaded=0 AND created>=? AND retry_at<=? LIMIT 5', (cutoff, time.time()))
            for row in rows:
                try:
                    await self.upload(client, row)
                    self.store.execute('UPDATE archives SET uploaded=1,error=NULL WHERE path=?', (row['path'],))
                except Exception as exc:
                    attempts = row['attempts'] + 1
                    self.store.execute('UPDATE archives SET attempts=?,retry_at=?,error=? WHERE path=?',
                        (attempts, time.time() + min(3600, 2 ** min(attempts, 11)), type(exc).__name__, row['path']))
