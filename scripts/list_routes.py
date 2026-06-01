import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.main import app
for r in app.routes:
    try:
        print(r.path, getattr(r, 'methods', None))
    except Exception:
        pass
