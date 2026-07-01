import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from shared.db.database import db_session
from sqlalchemy import text

with db_session() as db:
    res = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    for row in res.fetchall():
        if 'interview' in row[0]:
            print('TABLE:', row[0])
            col_res = db.execute(text(f"PRAGMA table_info('{row[0]}')"))
            for col in col_res.fetchall():
                print('  Col:', col[1], col[2])
