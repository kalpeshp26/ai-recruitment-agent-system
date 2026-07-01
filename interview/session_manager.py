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


async def process_interview_completed_event(payload: dict) -> None:
    """
    Synchronizes interview completion results to the main recruitment database.
    Ensures idempotency and audit safety.
    """
    from shared.db.database import db_session
    from shared.db.models import Application, Candidate, InterviewEvaluation, Job
    from sqlalchemy import select
    import uuid
    from datetime import datetime

    interview_id = payload.get("interview_id")
    candidate_id = payload.get("candidate_id")
    job_id = payload.get("job_id")
    overall_score = payload.get("overall_score", 0.0)
    content_score = payload.get("content_score", 0.0)
    behavior_score = payload.get("behavior_score", 0.0)
    communication_score = payload.get("communication_score", 0.0)
    confidence_score = payload.get("confidence_score", 1.0)
    recommendation = payload.get("recommendation", "reject")
    completed_at = payload.get("completed_at")
    strengths = payload.get("strengths", "")
    weaknesses = payload.get("weaknesses", "")

    logger.info(f"Syncing completed interview session {interview_id} for candidate {candidate_id}")

    # Normalize recommendation string
    rec_str = "REJECT"
    rec_lower = str(recommendation).lower()
    if "strong" in rec_lower:
        rec_str = "STRONG_HIRE"
    elif "hire" in rec_lower:
        rec_str = "HIRE"
    elif "maybe" in rec_lower or "hold" in rec_lower:
        rec_str = "HOLD"

    with db_session() as db:
        # Fallback database lookup if candidate_id or job_id is missing
        if not candidate_id or not job_id:
            try:
                from sqlalchemy import text
                row = db.execute(text(
                    "SELECT candidate_id, job_id FROM interview_sessions WHERE session_id = :sid AND candidate_id IS NOT NULL LIMIT 1"
                ), {"sid": str(interview_id)}).fetchone()
                if row:
                    if not candidate_id:
                        candidate_id = row[0]
                    if not job_id:
                        job_id = row[1]
            except Exception as e:
                logger.error(f"Error looking up candidate/job context: {e}")

        # 1. Update lightweight interview_sessions
        try:
            from sqlalchemy import text
            comp_dt = datetime.fromisoformat(completed_at) if completed_at else datetime.utcnow()
            db.execute(text("""
                UPDATE interview_sessions
                SET interview_status = 'COMPLETED', completed_at = :comp_dt
                WHERE session_id = :session_id OR (candidate_id = :candidate_id AND job_id = :job_id)
            """), {
                "comp_dt": comp_dt,
                "session_id": str(interview_id),
                "candidate_id": candidate_id,
                "job_id": job_id
            })
            db.commit()
        except Exception as e:
            logger.error(f"Error updating interview_sessions: {e}")
            db.rollback()

        # 2. Add or update InterviewEvaluation record (Idempotent check)
        try:
            eval_res = db.execute(
                select(InterviewEvaluation).where(
                    InterviewEvaluation.session_id == str(interview_id)
                )
            )
            evaluation = eval_res.scalar_one_or_none()

            # Retrieve candidate answers to construct an automated summary
            summary_notes = "Candidate successfully completed the AI automated interview round. "
            try:
                from shared.db.interview import InterviewTurn, InterviewSession
                session_obj = db.query(InterviewSession).filter(
                    (InterviewSession.session_id == str(interview_id)) | (InterviewSession.id == str(interview_id))
                ).first()
                db_session_id = session_obj.id if session_obj else interview_id
                
                turns = db.query(InterviewTurn).filter(
                    (InterviewTurn.interview_id == db_session_id) | (InterviewTurn.interview_id == str(interview_id))
                ).order_by(InterviewTurn.turn_number.asc()).all()
                if turns:
                    summary_notes += f"Completed {len(turns)} turns. "
                    scores = [t.final_score for t in turns if t.final_score is not None]
                    if scores:
                        summary_notes += f"Final score averaged {round(sum(scores)/len(scores)*100, 1)}%."
            except Exception as e:
                logger.warning(f"Could not read turns: {e}")

            # Scale to 0-100 range for the UI representation if values are decimal
            scale_final = overall_score * 100 if overall_score <= 1.0 else overall_score
            scale_content = content_score * 100 if content_score <= 1.0 else content_score
            scale_behavior = behavior_score * 100 if behavior_score <= 1.0 else behavior_score
            scale_communication = communication_score * 100 if communication_score <= 1.0 else communication_score
            scale_confidence = confidence_score * 100 if confidence_score <= 1.0 else confidence_score

            if not evaluation:
                evaluation = InterviewEvaluation(
                    id=f"eval_{uuid.uuid4().hex[:8]}",
                    candidate_id=candidate_id,
                    job_id=job_id,
                    session_id=str(interview_id),
                    interview_id=str(interview_id),
                    phase="HR",
                    content_score=round(scale_content, 1),
                    behavior_score=round(scale_behavior, 1),
                    communication_score=round(scale_communication, 1),
                    confidence_score=round(scale_confidence, 1),
                    final_score=round(scale_final, 1),
                    ai_recommendation=rec_str,
                    recommendation=rec_str,  # Legacy backup
                    evaluator_notes=summary_notes,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    ai_generated_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                db.add(evaluation)
            else:
                evaluation.content_score = round(scale_content, 1)
                evaluation.behavior_score = round(scale_behavior, 1)
                evaluation.communication_score = round(scale_communication, 1)
                evaluation.confidence_score = round(scale_confidence, 1)
                evaluation.final_score = round(scale_final, 1)
                evaluation.ai_recommendation = rec_str
                evaluation.recommendation = rec_str  # Legacy backup
                evaluation.evaluator_notes = summary_notes
                evaluation.strengths = strengths
                evaluation.weaknesses = weaknesses
                evaluation.ai_generated_at = datetime.utcnow()
                evaluation.updated_at = datetime.utcnow()

            db.commit()
        except Exception as e:
            logger.error(f"Error persisting InterviewEvaluation record: {e}")
            db.rollback()

        # 3. Update candidate Application stage status to INTERVIEW_COMPLETED
        try:
            app = db.query(Application).filter_by(
                candidate_id=candidate_id,
                job_id=job_id
            ).first()
            if app:
                app.status = "INTERVIEW_COMPLETED"
                app.stage = 6
                db.commit()
                logger.info(f"Updated Application status to INTERVIEW_COMPLETED for candidate {candidate_id}")
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            db.rollback()

