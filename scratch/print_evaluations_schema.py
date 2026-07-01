import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from shared.db.database import db_session
from sqlalchemy import text

with db_session() as db:
    res = db.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='interview_evaluations'"))
    print(res.fetchone()[0])
