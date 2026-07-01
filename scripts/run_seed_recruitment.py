import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/recruitment.db'

import scripts.seed_test_data as s
s.run()
print('Seed runner completed')
