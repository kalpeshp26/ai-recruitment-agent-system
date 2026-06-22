import sqlite3
import os

db_path = os.path.join("data", "recruitment.db")
if not os.path.exists(db_path):
    print("Database path not found at:", db_path)
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Identify test candidates
    cursor.execute("SELECT id, name, email FROM candidates")
    candidates = cursor.fetchall()
    
    test_ids = []
    for cid, name, email in candidates:
        email_str = str(email).lower() if email else ""
        name_str = str(name).lower()
        
        # Test candidate indicators
        is_test = False
        if "test" in name_str or "example.com" in email_str or "test.com" in email_str:
            is_test = True
        elif name_str in ["alice johnson", "bob smith", "carol davis", "alice a", "bob b", "one", "two", "alice jhonson", "original", "clone", "no job"]:
            is_test = True
        elif email_str in ["a@a.com", "b@b.com", "dup@test.com", "test@nojob.com"]:
            is_test = True
            
        if is_test:
            test_ids.append(cid)
            print(f"To Delete -> ID: {cid} | Name: {name} | Email: {email}")
            
    if not test_ids:
        print("No test candidates found to delete.")
    else:
        print(f"\nDeleting {len(test_ids)} test candidates and their related table rows...")
        
        # Delete from related tables
        placeholders = ",".join("?" for _ in test_ids)
        
        # 1. Chatbot answers (joined via chatbot_sessions)
        cursor.execute(f"""
            DELETE FROM chatbot_answers 
            WHERE session_id IN (
                SELECT session_id FROM chatbot_sessions WHERE candidate_id IN ({placeholders})
            )
        """, test_ids)
        print(f"Deleted chatbot answers: {cursor.rowcount}")
        
        # 2. Chatbot sessions
        cursor.execute(f"DELETE FROM chatbot_sessions WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted chatbot sessions: {cursor.rowcount}")
        
        # 3. Interview evaluations
        cursor.execute(f"DELETE FROM interview_evaluations WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted interview evaluations: {cursor.rowcount}")
        
        # 4. Onboarding tasks (joined via onboarding)
        cursor.execute(f"""
            DELETE FROM onboarding_tasks 
            WHERE onboarding_id IN (
                SELECT id FROM onboarding WHERE candidate_id IN ({placeholders})
            )
        """, test_ids)
        print(f"Deleted onboarding tasks: {cursor.rowcount}")
        
        # 5. Onboarding
        cursor.execute(f"DELETE FROM onboarding WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted onboarding entries: {cursor.rowcount}")
        
        # 6. Scores
        cursor.execute(f"DELETE FROM scores WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted scores: {cursor.rowcount}")
        
        # 7. Communications
        cursor.execute(f"DELETE FROM communications WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted communications: {cursor.rowcount}")
        
        # 8. Applications
        cursor.execute(f"DELETE FROM applications WHERE candidate_id IN ({placeholders})", test_ids)
        print(f"Deleted applications: {cursor.rowcount}")
        
        # 9. Finally, delete from candidates
        cursor.execute(f"DELETE FROM candidates WHERE id IN ({placeholders})", test_ids)
        print(f"Deleted candidates: {cursor.rowcount}")
        
        conn.commit()
        print("Database cleanup complete.")
        
    conn.close()
