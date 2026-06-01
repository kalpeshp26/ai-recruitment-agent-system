import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path so imports work when run from scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/recruitment.db'
import asyncio
from shared.db.database import init_db
asyncio.run(init_db())
print('Initialized data/recruitment.db')
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/recruitment.db'
import asyncio
from shared.db.database import init_db
asyncio.run(init_db())
print('Initialized data/recruitment.db')
