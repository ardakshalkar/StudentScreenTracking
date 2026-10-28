"""Start an isolated real server, run the 30-student test, then stop it."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request


def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='classroom-load-') as directory:
        env={**os.environ,'DATA_DIR':directory,'TEACHER_PASSWORD':'load-test-password-only','APP_SECRET':'isolated-load-test-secret-at-least-32-characters',
             'PUBLIC_ORIGIN':'http://localhost:8011','GOOGLE_CLIENT_ID':'','GOOGLE_CLIENT_SECRET':'','TOKEN_ENCRYPTION_KEY':'','EXTENSION_IDS':'','STUDENT_AUTH_MODE':'code'}
        with open(root/'load-server.log','w') as output:
            server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--port','8011','--host','127.0.0.1',
                '--ws-max-size','1100000','--ws-max-queue','1'],cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if server.poll() is not None:raise RuntimeError('Load server failed: see load-server.log')
                    try:
                        urllib.request.urlopen('http://localhost:8011/api/health',timeout=1)
                        break
                    except Exception:time.sleep(.1)
                else:raise RuntimeError('Load server did not start')
                result=subprocess.run([sys.executable,'scripts/load_test.py','--url','http://localhost:8011',*sys.argv[1:]],cwd=root,env=env)
                if result.returncode:raise SystemExit(result.returncode)
            finally:
                server.terminate()
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:server.kill();server.wait()


if __name__=='__main__':main()
