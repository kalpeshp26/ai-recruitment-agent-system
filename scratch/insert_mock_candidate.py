import sqlite3
import uuid
import json
from datetime import datetime

DB_PATH = "data/recruitment.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Get first job
        cur.execute("SELECT id, title FROM jobs LIMIT 1")
        job = cur.fetchone()
        if not job:
            print("[ERROR] No job found in database. Creating a mock job 'Python Developer'...")
            job_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO jobs (id, title, description, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, "Python Developer", "Full Stack Developer with Python focus", "active", datetime.now().isoformat()))
            job_title = "Python Developer"
        else:
            job_id, job_title = job
            
        # Create candidate
        candidate_id = str(uuid.uuid4())
        name = "Jane Doe"
        email = "jane.doe@example.com"
        phone = "+1-555-0199"
        location = "San Francisco, CA"
        
        cur.execute("""
            INSERT INTO candidates (id, name, email, phone, location, experience_years, skills, source, status, created_at, job_id, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            name,
            email,
            phone,
            location,
            4.5,
            json.dumps(["Python", "FastAPI", "SQLite", "Git"]),
            "referral",
            "applied",
            datetime.now().isoformat(),
            job_id,
            85.0
        ))
        
        # Create application
        app_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO applications (id, candidate_id, job_id, status, match_score, applied_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            app_id,
            candidate_id,
            job_id,
            "SHORTLISTED",
            0.85,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        print(f"[SUCCESS] Inserted candidate '{name}' ({email}) for job '{job_title}'")
        print(f"Candidate ID: {candidate_id}")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Transaction failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
