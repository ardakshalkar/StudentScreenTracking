"""Disk-backed archive batches. SQLite contains metadata, never image payloads."""
import hashlib
import io
import json
import sqlite3
import time
import threading
import uuid
import zipfile
from pathlib import Path

from PIL import Image


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.lock = threading.RLock()
        (root / 'archives').mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / 'classroom.db', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY, course TEXT, title TEXT, code TEXT, active INTEGER,
          recording INTEGER, interval INTEGER, created REAL, ended REAL);
        CREATE TABLE IF NOT EXISTS students (
          id TEXT PRIMARY KEY, session_id TEXT, name TEXT, student_id TEXT, token_nonce TEXT);
        CREATE TABLE IF NOT EXISTS samples (
          id TEXT PRIMARY KEY, session_id TEXT, student TEXT, captured REAL,
          archive TEXT, member TEXT, digest TEXT);
        CREATE TABLE IF NOT EXISTS archives (
          path TEXT PRIMARY KEY, session_id TEXT, student TEXT, created REAL,
          sealed INTEGER DEFAULT 0, drive_id TEXT, uploaded INTEGER DEFAULT 0,
          attempts INTEGER DEFAULT 0, retry_at REAL DEFAULT 0, error TEXT);
        CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS auth_flows (key TEXT PRIMARY KEY, expires REAL, payload TEXT);
        ''')
        # A restarted server cannot keep a browser's capture permission/session alive.
        self.db.execute('UPDATE sessions SET active=0, ended=? WHERE active=1', (time.time(),))
        self.db.execute('UPDATE archives SET sealed=1')
        self.db.commit()

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args)]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def execute(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()

    def secret(self, key):
        row = self.one('SELECT value FROM secrets WHERE key=?', (key,))
        return row['value'] if row else None

    def set_secret(self, key, value):
        self.execute('INSERT OR REPLACE INTO secrets VALUES (?,?)', (key, value))

    def put_flow(self, key, payload, ttl):
        with self.lock:
            self.execute('DELETE FROM auth_flows WHERE expires<?', (time.time(),))
            self.execute('INSERT INTO auth_flows VALUES (?,?,?)', (key, time.time()+ttl, json.dumps(payload)))

    def take_flow(self, key):
        # Consume atomically: concurrent callbacks/exchanges cannot replay a grant.
        with self.lock:
            row = self.one('SELECT * FROM auth_flows WHERE key=?', (key,))
            self.execute('DELETE FROM auth_flows WHERE key=?', (key,))
            return json.loads(row['payload']) if row and row['expires'] > time.time() else None

    def record(self, session, student, raw, captured):
        with Image.open(io.BytesIO(raw)) as image:
            image = image.convert('RGB')
            image.thumbnail((1280, 1280))
            # Compare normalized pixels independently of the live compression mode.
            digest = hashlib.sha256(image.resize((64, 36)).tobytes()).hexdigest()
            previous = self.one('SELECT digest FROM samples WHERE session_id=? AND student=? ORDER BY captured DESC LIMIT 1', (session['id'], student))
            if previous and previous['digest'] == digest:
                return False
            output = io.BytesIO()
            image.save(output, 'WEBP', quality=80, method=4)
        bucket = int(captured // 300)
        # Seal early at 4 MB so multipart uploads also stay small when teachers
        # select a five-second interval or students share very complex screens.
        current = self.one('SELECT * FROM archives WHERE session_id=? AND student=? AND sealed=0 ORDER BY created DESC LIMIT 1', (session['id'], student))
        relative = f"archives/{session['id']}/{student}/{bucket}-{uuid.uuid4().hex[:8]}.zip"
        if current and int(current['created'] // 300) == bucket:
            current_path = self.root / current['path']
            if current_path.stat().st_size + len(output.getvalue()) + 2048 <= 4_000_000:
                relative = current['path']
            else:
                self.execute('UPDATE archives SET sealed=1 WHERE path=?', (current['path'],))
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        sample_id = uuid.uuid4().hex
        member = sample_id + '.webp'
        # Images are already compressed; ZIP_STORED avoids wasting CPU recompressing.
        with zipfile.ZipFile(path, 'a', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr(member, output.getvalue())
            archive.writestr(sample_id + '.json', json.dumps({
                'student': student, 'session': session['id'], 'captured_at': captured,
                'student_id': self.one('SELECT student_id FROM students WHERE id=?', (student,))['student_id'],
            }))
        self.execute('INSERT OR IGNORE INTO archives(path,session_id,student,created) VALUES (?,?,?,?)', (relative, session['id'], student, captured))
        self.execute('INSERT INTO samples VALUES (?,?,?,?,?,?,?)', (sample_id, session['id'], student, captured, relative, member, digest))
        return True

    def seal(self):
        for row in self.rows('SELECT a.*,s.active FROM archives a JOIN sessions s ON s.id=a.session_id WHERE sealed=0'):
            if not row['active'] or time.time() // 300 > row['created'] // 300:
                self.execute('UPDATE archives SET sealed=1 WHERE path=?', (row['path'],))

    def delete_archive(self, row):
        (self.root / row['path']).unlink(missing_ok=True)
        self.execute('DELETE FROM samples WHERE archive=?', (row['path'],))
        self.execute('DELETE FROM archives WHERE path=?', (row['path'],))

    def sample_bytes(self, row):
        with zipfile.ZipFile(self.root / row['archive']) as archive:
            return archive.read(row['member'])
