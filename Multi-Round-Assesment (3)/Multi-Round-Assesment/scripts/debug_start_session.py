import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database.db import SessionLocal
from app.services.session_service import create_session
from app.models.user import User

if __name__ == '__main__':
    db = SessionLocal()
    user = db.query(User).first()
    print('Found user:', user)
    try:
        session = create_session(db, user.id)
        print('Created session:', session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Error:', e)
    finally:
        db.close()
