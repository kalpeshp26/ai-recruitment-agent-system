import sqlite3
import uuid

def fix_unlinked():
    conn = sqlite3.connect('data/recruitment.db')
    c = conn.cursor()
    
    # 1. Get the default job ID
    c.execute("SELECT id, title FROM jobs LIMIT 1")
    job = c.fetchone()
    if not job:
        print("No jobs found in the database. Please create a job requisition first.")
        conn.close()
        return
    
    job_id, job_title = job
    print(f"Default Job found: {job_title} ({job_id})")
    
    # 2. Find all candidates without job_id or rejected due to missing job requirements
    c.execute("""
        SELECT id, name FROM candidates 
        WHERE job_id IS NULL OR status = 'rejected' AND rejection_reason LIKE '%No job_id%'
    """)
    candidates = c.fetchall()
    
    if not candidates:
        print("No candidates found that need linking.")
        conn.close()
        return
        
    print(f"Found {len(candidates)} candidate(s) to link:")
    for cid, name in candidates:
        print(f"  - {name} ({cid})")
        
        # Update candidate
        c.execute("""
            UPDATE candidates 
            SET job_id = ?, status = 'uploaded', score = NULL, score_breakdown = NULL, rejection_reason = NULL 
            WHERE id = ?
        """, (job_id, cid))
        
        # Check if Application exists
        c.execute("SELECT id FROM applications WHERE candidate_id = ? AND job_id = ?", (cid, job_id))
        app = c.fetchone()
        if not app:
            app_id = str(uuid.uuid4())
            c.execute("""
                INSERT INTO applications (id, job_id, candidate_id, status, applied_at, updated_at)
                VALUES (?, ?, ?, 'applied', datetime('now'), datetime('now'))
            """, (app_id, job_id, cid))
            print(f"    Created application record {app_id}")
            
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    fix_unlinked()
