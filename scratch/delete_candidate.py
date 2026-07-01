import sqlite3

DB_PATH = "data/recruitment.db"
CANDIDATE_NAME = "Divesh Developer"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Find candidate ID
        cur.execute("SELECT id FROM candidates WHERE name = ?", (CANDIDATE_NAME,))
        rows = cur.fetchall()
        if not rows:
            print(f"[INFO] No candidate found with name '{CANDIDATE_NAME}'")
            return
            
        candidate_ids = [r[0] for r in rows]
        print(f"[INFO] Found {len(candidate_ids)} candidate record(s) matching '{CANDIDATE_NAME}': {candidate_ids}")
        
        for candidate_id in candidate_ids:
            # 1. Fetch chatbot sessions to delete answers
            cur.execute("SELECT session_id FROM chatbot_sessions WHERE candidate_id = ?", (candidate_id,))
            sessions = [r[0] for r in cur.fetchall()]
            for session_id in sessions:
                cur.execute("DELETE FROM chatbot_answers WHERE session_id = ?", (session_id,))
                print(f"  - Deleted chatbot answers for session {session_id}")
            
            # 2. Fetch interview sessions to delete turns
            cur.execute("SELECT id FROM interview_sessions WHERE candidate_id = ?", (candidate_id,))
            int_sessions = [r[0] for r in cur.fetchall()]
            for int_id in int_sessions:
                cur.execute("DELETE FROM interview_turns WHERE interview_id = ?", (int_id,))
                print(f"  - Deleted interview turns for session {int_id}")
                
            # 3. Delete from standard tables
            tables_by_candidate_id = [
                "applications",
                "communications",
                "chatbot_sessions",
                "interview_sessions",
                "interview_evaluations",
                "scores"
            ]
            
            for table in tables_by_candidate_id:
                cur.execute(f"DELETE FROM {table} WHERE candidate_id = ?", (candidate_id,))
                print(f"  - Deleted records from {table}")
                
            cur.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
            print("  - Deleted candidate from candidates table")
                
        conn.commit()
        print(f"[SUCCESS] Cleaned all records for candidate '{CANDIDATE_NAME}' from the database.")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Transaction failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
