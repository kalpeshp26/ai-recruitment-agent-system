import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
resp = client.post('/api/intake/jobs', json={'title':'TC Job','department':'TC'})
print('STATUS', resp.status_code)
print('BODY', resp.text)
try:
    print('JSON', resp.json())
except Exception as e:
    print('No JSON', e)
