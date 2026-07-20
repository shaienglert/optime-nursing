import os, socket, subprocess, sys, time
from pathlib import Path
import requests
repo = Path(r"c:\Users\u4\Documents\GitHub\optime-nursing")
backend = repo / "backend"
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
env = os.environ.copy()
env['FRONTEND_ORIGINS'] = ''
env['OPTIME_SMTP_STARTUP_TEST_ENABLED'] = '0'
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)], cwd=backend, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if requests.get(f'http://127.0.0.1:{port}/health', timeout=3).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(5)
    for path in ['/facilities', '/governance/runtime-context']:
        resp = requests.get(f'http://127.0.0.1:{port}{path}', headers={'Origin': 'https://optime-nursing.vercel.app'}, timeout=30)
        print('PATH=', path, 'STATUS=', resp.status_code, 'ALLOW=', resp.headers.get('access-control-allow-origin'))
        print('BODY=', resp.text[:500])
finally:
    proc.terminate()
    try:
        out, _ = proc.communicate(timeout=10)
    except Exception:
        proc.kill()
        out, _ = proc.communicate(timeout=5)
    print('SERVER_LOG_START')
    print((out or '')[-3000:])
    print('SERVER_LOG_END')
