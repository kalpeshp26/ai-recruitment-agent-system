import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from shared.db.database import db_session
from sqlalchemy import text

with db_session() as db:
    print("--- INTERVIEW SESSIONS ---")
    res = db.execute(text("SELECT id, session_id, candidate_id, job_id, interview_status, completed_at FROM interview_sessions"))
    for row in res.fetchall():
        print(row)
        
    print("\n--- INTERVIEW EVALUATIONS ---")
    res = db.execute(text("SELECT id, candidate_id, job_id, session_id, final_score, recommendation FROM interview_evaluations"))
    for row in res.fetchall():
        print(row)
        
    print("\n--- APPLICATIONS ---")
    res = db.execute(text("SELECT id, candidate_id, job_id, status, stage FROM applications"))
    for row in res.fetchall():
        print(row)
