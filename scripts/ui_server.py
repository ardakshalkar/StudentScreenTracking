"""Isolated, disposable backend used only by Playwright."""
import os
from pathlib import Path
import sys
import tempfile

import uvicorn

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='classroom-ui-') as directory:
    os.environ.update(DATA_DIR=directory,TEACHER_PASSWORD='ui-test-password-only',APP_SECRET='isolated-ui-test-secret-at-least-32-characters',
        PUBLIC_ORIGIN='http://localhost:5179',GOOGLE_CLIENT_ID='',GOOGLE_CLIENT_SECRET='',TOKEN_ENCRYPTION_KEY='',EXTENSION_IDS='',STUDENT_AUTH_MODE='code')
    uvicorn.run('backend.main:app',host='127.0.0.1',port=8012,ws_max_size=1_100_000,ws_max_queue=1)
