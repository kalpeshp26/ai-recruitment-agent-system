import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

try:
    # Load in the SAME ORDER the server does: router loads shared.db.interview first
    from shared.db.interview import InterviewSession, InterviewTurn
    print("[OK] Loaded shared.db.interview models")
    
    from shared.db.database import db_session
    with db_session() as db:
        count = db.query(InterviewSession).count()
        print(f"[OK] Query successful - {count} sessions found")
        
        turns_count = db.query(InterviewTurn).count()
        print(f"[OK] Turns query - {turns_count} turns found")
        
except Exception as e:
    import traceback
    print(f"[FAILED] {e}")
    traceback.print_exc()
