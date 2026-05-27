#!/usr/bin/env python3
"""Seed minimal test data for end-to-end smoke tests.
Creates one job, one candidate, one application, one interview, one offer, one onboarding.
"""
import sqlite3
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///./data/recruitment.db")
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")

def gid():
    return str(uuid.uuid4())[:12]

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now = datetime.now().isoformat()

    # Job
    job_id = gid()
    cur.execute("INSERT OR IGNORE INTO jobs (id, title, department, status, created_at) VALUES (?,?,?,?,?)",
                (job_id, 'Test Job', 'Engineering', 'active', now))

    # Candidate
    candidate_id = gid()
    cur.execute("INSERT OR IGNORE INTO candidates (id, name, email, status, created_at) VALUES (?,?,?,?,?)",
                (candidate_id, 'Test Candidate', 'test@example.com', 'new', now))

    # Application
    application_id = f"app_{candidate_id}"
    cur.execute("INSERT OR IGNORE INTO applications (id, job_id, candidate_id, status, applied_at) VALUES (?,?,?,?,?)",
                (application_id, job_id, candidate_id, 'applied', now))

    # Interview: support either 'interview_sessions' (legacy) or 'interviews' (current)
    interview_id = f"int_{gid()}"
    cur_tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    if 'interview_sessions' in cur_tables:
        cur.execute(
            "INSERT OR IGNORE INTO interview_sessions (id, candidate_id, job_id, phase, overall_score, created_at) VALUES (?,?,?,?,?,?)",
            (interview_id, candidate_id, job_id, 'COMPLETE', 0.8, now),
        )
    elif 'interviews' in cur_tables:
        # current schema expects application_id
        cur.execute(
            "INSERT OR IGNORE INTO interviews (id, application_id, interview_type, scheduled_at, status, created_at) VALUES (?,?,?,?,?,?)",
            (interview_id, application_id, 'PHONE', now, 'COMPLETE', now),
        )
    else:
        print('No interviews table found; skipping interview insert')

    # Offer
    offer_id = gid()
    cur.execute("INSERT OR IGNORE INTO offers (id, application_id, salary_offered, start_date, status, created_at) VALUES (?,?,?,?,?,?)",
                (offer_id, application_id, 70000.0, now, 'pending', now))

    # Onboarding
    onboarding_id = gid()
    cur.execute("INSERT OR IGNORE INTO onboarding (id, candidate_id, offer_id, status, created_at) VALUES (?,?,?,?,?)",
                (onboarding_id, candidate_id, offer_id, 'started', now))

    conn.commit()
    conn.close()
    print('Seed data inserted: job_id=', job_id)

if __name__ == '__main__':
    run()
