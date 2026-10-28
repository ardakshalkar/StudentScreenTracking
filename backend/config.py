import os
import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass
class Settings:
    data: Path = field(default_factory=lambda: Path(os.getenv('DATA_DIR', './data')))
    password: str = field(default_factory=lambda: os.getenv('TEACHER_PASSWORD', ''))
    secret: str = field(default_factory=lambda: os.getenv('APP_SECRET', ''))
    origin: str = field(default_factory=lambda: os.getenv('PUBLIC_ORIGIN', 'http://localhost:5173').rstrip('/'))
    extension_ids: str = field(default_factory=lambda: os.getenv('EXTENSION_IDS', ''))
    google_id: str = field(default_factory=lambda: os.getenv('GOOGLE_CLIENT_ID', ''))
    google_secret: str = field(default_factory=lambda: os.getenv('GOOGLE_CLIENT_SECRET', ''))
    encryption_key: str = field(default_factory=lambda: os.getenv('TOKEN_ENCRYPTION_KEY', ''))
    student_auth: str = field(default_factory=lambda: os.getenv('STUDENT_AUTH_MODE', 'code').strip().lower())
    student_domains: str = field(default_factory=lambda: os.getenv('STUDENT_ALLOWED_DOMAINS', ''))
    student_google_id: str = field(default_factory=lambda: os.getenv('STUDENT_GOOGLE_CLIENT_ID', ''))
    student_google_secret: str = field(default_factory=lambda: os.getenv('STUDENT_GOOGLE_CLIENT_SECRET', ''))
    allow_lan_http: bool = field(default_factory=lambda: os.getenv('ALLOW_LAN_HTTP', '').strip().lower() in ('1','true','yes'))
    max_students: int = 35
    max_focus: int = 2
    retention_days: int = field(default_factory=lambda: int(os.getenv('RETENTION_DAYS', '30')))

    @property
    def google_enabled(self):
        return bool(self.google_id and self.google_secret and self.encryption_key)

    @property
    def allowed_student_domains(self):
        return {domain.strip().lower() for domain in self.student_domains.split(',') if domain.strip()}

    @property
    def lan_http(self):
        url=urlsplit(self.origin)
        try:
            address=ipaddress.ip_address(url.hostname or '')
            private=address.version==4 and any(address in ipaddress.ip_network(network) for network in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
        except ValueError:
            private=False
        return url.scheme=='http' and private

    def validate(self):
        url=urlsplit(self.origin)
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
            raise RuntimeError('PUBLIC_ORIGIN must be an HTTP(S) origin without credentials, a path or query')
        if url.scheme=='http' and url.hostname not in ('localhost','127.0.0.1','::1'):
            if not self.allow_lan_http or not self.lan_http:
                raise RuntimeError('Remote HTTP requires ALLOW_LAN_HTTP=true and an RFC1918 private IPv4 PUBLIC_ORIGIN')
            if self.student_auth!='code' or self.google_enabled:
                raise RuntimeError('LAN HTTP requires code-only joining and disabled Google Drive OAuth. Use HTTPS for Google login/Drive connection.')
        if len(self.password) < 12 or len(self.secret) < 32:
            raise RuntimeError('Set TEACHER_PASSWORD (12+ characters) and APP_SECRET (32+ characters).')
        if self.retention_days < 1:
            raise RuntimeError('RETENTION_DAYS must be positive')
        if self.student_auth not in ('code', 'google'):
            raise RuntimeError('STUDENT_AUTH_MODE must be code or google')
        if self.student_auth == 'google':
            if not self.student_google_id or not self.student_google_secret or not self.allowed_student_domains:
                raise RuntimeError('Google student login requires STUDENT_GOOGLE_CLIENT_ID, STUDENT_GOOGLE_CLIENT_SECRET and STUDENT_ALLOWED_DOMAINS')
            import re
            if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+', d) for d in self.allowed_student_domains):
                raise RuntimeError('Use exact email domains, without @, wildcards, schemes, or paths')
