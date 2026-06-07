"""
interview/session_manager.py
════════════════════════════════════════════════════════════════════
Interview Session Manager
Automatically creates interview sessions when candidates pass prescreening.
Generates session IDs, URLs, and manages interview lifecycle.
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
INTERVIEW_BASE_URL = os.getenv("INTERVIEW_BASE_URL", "http://localhost:5173")
INTERVIEW_EXPIRY_DAYS = int(os.getenv("INTERVIEW_EXPIRY_DAYS", "7"))


def _ensure_interview_sessions_table(db) -> None:
    """Create/reconcile the lightweight interview session table used by the dashboard."""
    from sqlalchemy import text

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id TEXT PRIMARY KEY,
            session_id TEXT UNIQUE,
            candidate_id TEXT,
            job_id TEXT,
            phase TEXT DEFAULT 'HR',
            interview_status TEXT DEFAULT 'PENDING',
            invited_at TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP
        )
    """))

    existing = {row[1] for row in db.execute(text("PRAGMA table_info(interview_sessions)")).fetchall()}
    columns = {
        "session_id": "TEXT",
        "candidate_id": "TEXT",
        "job_id": "TEXT",
        "phase": "TEXT DEFAULT 'HR'",
        "interview_status": "TEXT DEFAULT 'PENDING'",
        "invited_at": "TIMESTAMP",
        "started_at": "TIMESTAMP",
        "completed_at": "TIMESTAMP",
        "created_at": "TIMESTAMP",
    }
    for name, definition in columns.items():
        if name not in existing:
            db.execute(text(f"ALTER TABLE interview_sessions ADD COLUMN {name} {definition}"))


def create_interview_session(
    candidate_id: str,
    job_id: str,
    candidate_name: str,
    candidate_email: str,
    job_title: str
) -> Optional[Dict]:
    """
    Create a new interview session for a candidate.
    
    Args:
        candidate_id: Candidate database ID
        job_id: Job database ID
        candidate_name: Candidate's full name
        candidate_email: Candidate's email
        job_title: Job title
    
    Returns:
        Dict with session details or None if failed:
        {
            "session_id": "sess_abc123",
            "interview_url": "http://localhost:5173/interview/session/sess_abc123",
            "status": "PENDING"
        }
    """
    try:
        from shared.db.database import db_session
        from sqlalchemy import text
        
        # Generate unique session ID
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        # Generate interview URL
        interview_url = f"{INTERVIEW_BASE_URL}/interview/session/{session_id}"
        
        # Create session in database
        with db_session() as db:
            _ensure_interview_sessions_table(db)

            existing = db.execute(text("""
                SELECT session_id
                FROM interview_sessions
                WHERE candidate_id = :candidate_id
                  AND job_id = :job_id
                  AND COALESCE(interview_status, 'PENDING') IN ('PENDING', 'IN_PROGRESS')
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                "candidate_id": candidate_id,
                "job_id": job_id,
            }).fetchone()

            if existing:
                session_id = existing[0]
                interview_url = f"{INTERVIEW_BASE_URL}/interview/session/{session_id}"
                logger.info(f"Reusing interview session: {session_id} for candidate {candidate_id}")
            else:
                query = text("""
                    INSERT INTO interview_sessions
                    (session_id, candidate_id, job_id, phase, interview_status, invited_at, created_at)
                    VALUES
                    (:session_id, :candidate_id, :job_id, 'HR', 'PENDING', :invited_at, :created_at)
                """)

                db.execute(query, {
                    "session_id": session_id,
                    "candidate_id": candidate_id,
                    "job_id": job_id,
                    "invited_at": datetime.now(),
                    "created_at": datetime.now()
                })
                db.commit()
                logger.info(f"Interview session created: {session_id} for candidate {candidate_id}")
            
            # Also update candidate application status
            try:
                from shared.db.models import Application
                app = db.query(Application).filter_by(
                    candidate_id=candidate_id,
                    job_id=job_id
                ).first()
                
                if app:
                    app.status = "INTERVIEW_PENDING"
                    app.stage = 6
                    db.commit()
                    logger.info(f"Updated application status to INTERVIEW_PENDING for candidate {candidate_id}")
            except Exception as e:
                logger.error(f"Failed to update application status: {e}")
        
        # Return session details
        session_data = {
            "session_id": session_id,
            "interview_url": interview_url,
            "status": "PENDING",
            "candidate_id": candidate_id,
            "job_id": job_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "job_title": job_title
        }
        
        return session_data
        
    except Exception as e:
        logger.error(f"Failed to create interview session for candidate {candidate_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_interview_session(session_id: str) -> Optional[Dict]:
    """
    Retrieve interview session details.
    """
    try:
        from shared.db.database import db_session
        from sqlalchemy import text
        
        with db_session() as db:
            query = text("""
                SELECT session_id, candidate_id, job_id, phase, interview_status, 
                       invited_at, started_at, completed_at
                FROM interview_sessions
                WHERE session_id = :session_id
            """)
            
            result = db.execute(query, {"session_id": session_id}).fetchone()
            
            if result:
                return {
                    "session_id": result[0],
                    "candidate_id": result[1],
                    "job_id": result[2],
                    "phase": result[3],
                    "status": result[4],
                    "invited_at": result[5],
                    "started_at": result[6],
                    "completed_at": result[7]
                }
            return None
            
    except Exception as e:
        logger.error(f"Failed to retrieve interview session {session_id}: {e}")
        return None


def update_interview_status(session_id: str, status: str) -> bool:
    """
    Update interview session status.
    """
    try:
        from shared.db.database import db_session
        from sqlalchemy import text
        
        with db_session() as db:
            timestamp_field = None
            if status == "IN_PROGRESS":
                timestamp_field = "started_at"
            elif status == "COMPLETED":
                timestamp_field = "completed_at"
            
            if timestamp_field:
                query = text(f"""
                    UPDATE interview_sessions 
                    SET interview_status = :status, {timestamp_field} = :timestamp
                    WHERE session_id = :session_id
                """)
                db.execute(query, {
                    "status": status,
                    "timestamp": datetime.now(),
                    "session_id": session_id
                })
            else:
                query = text("""
                    UPDATE interview_sessions 
                    SET interview_status = :status
                    WHERE session_id = :session_id
                """)
                db.execute(query, {"status": status, "session_id": session_id})
            
            db.commit()
            logger.info(f"Updated interview session {session_id} status to {status}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update interview status for {session_id}: {e}")
        return False


def list_pending_interviews(job_id: Optional[str] = None) -> list:
    """
    List all pending interview sessions.
    
    Args:
        job_id: Optional job ID to filter by
    
    Returns:
        List of interview session dicts
    """
    try:
        from shared.db.database import db_session
        from sqlalchemy import text
        
        with db_session() as db:
            if job_id:
                query = text("""
                    SELECT session_id, candidate_id, job_id, interview_status, 
                           invited_at
                    FROM interview_sessions
                    WHERE job_id = :job_id AND interview_status IN ('PENDING', 'IN_PROGRESS')
                    ORDER BY invited_at DESC
                """)
                result = db.execute(query, {"job_id": job_id})
            else:
                query = text("""
                    SELECT session_id, candidate_id, job_id, interview_status, 
                           invited_at
                    FROM interview_sessions
                    WHERE interview_status IN ('PENDING', 'IN_PROGRESS')
                    ORDER BY invited_at DESC
                """)
                result = db.execute(query)
            
            sessions = []
            for row in result:
                sessions.append({
                    "session_id": row[0],
                    "candidate_id": row[1],
                    "job_id": row[2],
                    "status": row[3],
                    "invited_at": row[4]
                })
            
            return sessions
            
    except Exception as e:
        logger.error(f"Failed to list pending interviews: {e}")
        return []
