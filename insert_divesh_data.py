#!/usr/bin/env python3
"""
Insert Divesh Rahul Lokhande's data across all recruitment stages
"""
import sqlite3
from datetime import datetime
import json
import uuid

DB_PATH = "data/recruitment.db"

def insert_divesh_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Get the Web Developer job ID, fallback to any available job if not found
        cur.execute("SELECT id, title FROM jobs WHERE title = 'Web Developer' LIMIT 1")
        job_result = cur.fetchone()
        if not job_result:
            cur.execute("SELECT id, title FROM jobs LIMIT 1")
            job_result = cur.fetchone()
            
        if not job_result:
            print("[ERROR] No job found in jobs table. Please create a job first.")
            return
        job_id = job_result[0]
        job_title = job_result[1]
        print(f"[SUCCESS] Using job '{job_title}' with ID: {job_id}")
        
        # Check if Divesh already exists as a candidate
        cur.execute("SELECT id FROM candidates WHERE name = 'Divesh Rahul Lokhande' LIMIT 1")
        candidate_result = cur.fetchone()
        
        if candidate_result:
            candidate_id = candidate_result[0]
            print(f"[INFO] Found existing candidate Divesh with ID: {candidate_id}")
        else:
            # Insert Divesh as a candidate
            candidate_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO candidates (id, name, email, phone, location, experience_years, skills, source, status, created_at, job_id, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id,
                "Divesh Rahul Lokhande",
                "diveshlokhande72@gmail.com",
                "+91-9876543210",
                "Mumbai, India",
                3.0,
                json.dumps(["JavaScript", "React", "Node.js", "HTML", "CSS"]),
                "uploaded",
                "shortlisted",
                datetime.now().isoformat(),
                job_id,
                83.0
            ))
            print(f"[SUCCESS] Created candidate Divesh with ID: {candidate_id}")
        
        # Stage 3: Insert application with screening results
        cur.execute("SELECT id FROM applications WHERE candidate_id = ? AND job_id = ?", (candidate_id, job_id))
        app_row = cur.fetchone()
        if not app_row:
            app_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO applications (id, candidate_id, job_id, status, match_score, applied_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                app_id,
                candidate_id,
                job_id,
                "SHORTLISTED",
                0.88,
                datetime.now().isoformat()
            ))
            print("✅ Stage 3: Added screening results - application status: SHORTLISTED")
        else:
            app_id = app_row[0]
            cur.execute("""
                UPDATE applications 
                SET status = 'SHORTLISTED', match_score = 0.88
                WHERE candidate_id = ? AND job_id = ?
            """, (candidate_id, job_id))
            print("✅ Stage 3: Updated screening results - application status: SHORTLISTED")
        
        # Stage 4: Insert outreach communication
        cur.execute("SELECT id FROM communications WHERE candidate_id = ? AND job_id = ?", (candidate_id, job_id))
        if not cur.fetchone():
            comm_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO communications (id, candidate_id, job_id, communication_type, direction, subject, content, sent_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comm_id,
                candidate_id,
                job_id,
                "OUTREACH",
                "OUTBOUND",
                "Exciting Opportunity",
                "Outreach email sent with chatbot URL",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print("✅ Stage 4: Added outreach communication in communications table")
            
        cur.execute("""
            UPDATE applications 
            SET status = 'OUTREACH_SENT'
            WHERE candidate_id = ? AND job_id = ?
        """, (candidate_id, job_id))
        print("✅ Stage 4: Updated application status to: OUTREACH_SENT")
        
        # Stage 5: Insert prescreening session
        cur.execute("SELECT session_id FROM chatbot_sessions WHERE candidate_id = ?", (candidate_id,))
        if not cur.fetchone():
            session_id = str(uuid.uuid4())
            token = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO chatbot_sessions (session_id, candidate_id, job_id, token, status, created_at, expires_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                candidate_id,
                job_id,
                token,
                "COMPLETED",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print("✅ Stage 5: Added prescreening session - status: COMPLETED")
        else:
            cur.execute("""
                UPDATE chatbot_sessions 
                SET status = 'COMPLETED', completed_at = ?
                WHERE candidate_id = ?
            """, (datetime.now().isoformat(), candidate_id))
            print("✅ Stage 5: Updated prescreening session status to: COMPLETED")
            
        cur.execute("""
            UPDATE applications 
            SET status = 'PRESCREENED'
            WHERE candidate_id = ? AND job_id = ?
        """, (candidate_id, job_id))
        print("✅ Stage 5: Updated application status to: PRESCREENED")
        
        # Stage 6 & 7: Insert interview session
        cur.execute("SELECT id FROM interview_sessions WHERE candidate_id = ?", (candidate_id,))
        interview_result = cur.fetchone()
        
        if not interview_result:
            cur.execute("""
                INSERT INTO interview_sessions (
                    session_id, candidate_id, job_id, phase, total_turns, current_turn, status, interview_status, created_at, started_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                12345,
                candidate_id,
                job_id,
                "COMPLETE",
                8,
                8,
                "COMPLETED",
                "completed",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            interview_id = cur.lastrowid
            print(f"✅ Stage 6 & 7: Added interview session - status: COMPLETED")
        else:
            interview_id = interview_result[0]
            cur.execute("""
                UPDATE interview_sessions 
                SET phase = 'COMPLETE', total_turns = 8, current_turn = 8, status = 'COMPLETED', interview_status = 'completed', completed_at = ?
                WHERE candidate_id = ?
            """, (datetime.now().isoformat(), candidate_id))
            print(f"✅ Stage 6 & 7: Updated interview session status to: COMPLETED")
            
        cur.execute("""
            UPDATE applications 
            SET status = 'SELECTED'
            WHERE candidate_id = ? AND job_id = ?
        """, (candidate_id, job_id))
        print("✅ Stage 7: Updated application status to: SELECTED")
        
        # Commit all changes
        conn.commit()
        print("\n🎉 Successfully inserted Divesh Rahul Lokhande's data across all stages!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting data: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    insert_divesh_data()