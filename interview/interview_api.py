"""
interview/interview_api.py
Interview session management API endpoints for Stage 6
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["Stage 6: Interview"])


@router.get("/sessions")
async def list_interview_sessions(job_id: Optional[str] = None):
    """List all interview sessions with candidate details - includes candidates who passed prescreening."""
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job, Application, ChatbotSession
    from sqlalchemy import text, select
    import json

    try:
        with db_session() as db:
            sessions_dict = {}  # Use dict to deduplicate by candidate_id + job_id

            # First, get interview sessions from the interview_sessions table
            try:
                if job_id:
                    query = text("""
                        SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                               i.invited_at, i.started_at, i.completed_at,
                               c.name as candidate_name, c.email as candidate_email,
                               j.title as job_title
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        WHERE i.job_id = :job_id
                        ORDER BY i.invited_at DESC
                    """)
                    results = db.execute(query, {"job_id": job_id}).fetchall()
                else:
                    query = text("""
                        SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                               i.invited_at, i.started_at, i.completed_at,
                               c.name as candidate_name, c.email as candidate_email,
                               j.title as job_title
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        ORDER BY i.invited_at DESC
                    """)
                    results = db.execute(query).fetchall()

                for row in results:
                    key = f"{row[1]}_{row[2]}"  # candidate_id_job_id
                    sessions_dict[key] = {
                        "session_id": row[0],
                        "candidate_id": row[1],
                        "job_id": row[2],
                        "status": row[3] or "PENDING",
                        "invited_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
                        "started_at": row[5].isoformat() if hasattr(row[5], "isoformat") else row[5],
                        "completed_at": row[6].isoformat() if hasattr(row[6], "isoformat") else row[6],
                        "candidate_name": row[7],
                        "candidate_email": row[8],
                        "job_title": row[9],
                        "final_score": None
                    }

                logger.info(f"Retrieved {len(sessions_dict)} interview sessions from interview_sessions table")
            except Exception as table_error:
                logger.warning(f"interview_sessions table query failed: {table_error}")

            # Second, get candidates who completed prescreening from Application table
            # This ensures all candidates with status DONE, PRESCREENED, or INTERVIEW_PENDING are included
            query = select(Application).where(
                Application.status.in_(["DONE", "PRESCREENED", "INTERVIEW_PENDING"])
            ).order_by(Application.updated_at.desc())

            if job_id:
                query = query.where(Application.job_id == job_id)

            result = db.execute(query)
            applications = result.scalars().all()

            for app in applications:
                key = f"{app.candidate_id}_{app.job_id}"
                
                # Only add if not already in sessions_dict (interview_sessions takes precedence)
                if key not in sessions_dict:
                    # Get candidate details
                    candidate = db.execute(
                        select(Candidate).where(Candidate.id == app.candidate_id).limit(1)
                    )
                    cand = candidate.scalar_one_or_none()

                    # Get job details
                    job = db.execute(
                        select(Job).where(Job.id == app.job_id).limit(1)
                    )
                    job_obj = job.scalar_one_or_none()

                    # Generate a session ID based on application
                    session_id = f"prescreen_{app.candidate_id[:8]}_{app.job_id[:8]}"

                    sessions_dict[key] = {
                        "session_id": session_id,
                        "candidate_id": app.candidate_id,
                        "job_id": app.job_id,
                        "status": "PENDING",
                        "invited_at": app.updated_at.isoformat() if app.updated_at else None,
                        "started_at": None,
                        "completed_at": None,
                        "candidate_name": cand.name if cand else "Unknown",
                        "candidate_email": cand.email if cand else None,
                        "job_title": job_obj.title if job_obj else "Unknown",
                        "final_score": None
                    }

            # Third, get candidates from chatbot_sessions with PASS/BORDERLINE verdicts
            # This is a fallback for candidates whose application status might not be updated
            query = select(ChatbotSession).where(
                ChatbotSession.status == "COMPLETED"
            ).order_by(ChatbotSession.created_at.desc())

            if job_id:
                query = query.where(ChatbotSession.job_id == job_id)

            result = db.execute(query)
            chatbot_sessions = result.scalars().all()

            for session in chatbot_sessions:
                key = f"{session.candidate_id}_{session.job_id}"
                
                # Only add if not already in sessions_dict
                if key not in sessions_dict:
                    # Check if the session has a PASS or BORDERLINE verdict in summary
                    try:
                        if session.summary:
                            summary_data = json.loads(session.summary) if isinstance(session.summary, str) else session.summary
                            verdict = summary_data.get("verdict") if isinstance(summary_data, dict) else None
                            
                            # Only include if verdict is PASS or BORDERLINE
                            if verdict in ["PASS", "BORDERLINE"]:
                                # Get candidate details
                                candidate = db.execute(
                                    select(Candidate).where(Candidate.id == session.candidate_id).limit(1)
                                )
                                cand = candidate.scalar_one_or_none()

                                # Get job details
                                job = db.execute(
                                    select(Job).where(Job.id == session.job_id).limit(1)
                                )
                                job_obj = job.scalar_one_or_none()

                                sessions_dict[key] = {
                                    "session_id": session.session_id,
                                    "candidate_id": session.candidate_id,
                                    "job_id": session.job_id,
                                    "status": "PENDING",
                                    "invited_at": session.created_at.isoformat() if session.created_at else None,
                                    "started_at": None,
                                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                                    "candidate_name": cand.name if cand else "Unknown",
                                    "candidate_email": cand.email if cand else None,
                                    "job_title": job_obj.title if job_obj else "Unknown",
                                    "final_score": None
                                }
                    except Exception as json_error:
                        logger.warning(f"Failed to parse summary for session {session.session_id}: {json_error}")

            logger.info(f"Total sessions (including prescreening): {len(sessions_dict)}")
            return {"success": True, "sessions": list(sessions_dict.values())}

    except Exception as e:
        logger.error(f"Failed to list interview sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resend/{session_id}")
async def resend_interview_email(session_id: str):
    """Resend interview invitation email to candidate."""
    from interview.session_manager import get_interview_session
    from interview.interview_email_sender import send_interview_invitation_email
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job
    from datetime import datetime, timedelta
    import os
    
    try:
        # Get session details
        session = get_interview_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Get candidate and job details
        with db_session() as db:
            candidate = db.query(Candidate).filter_by(id=session['candidate_id']).first()
            job = db.query(Job).filter_by(id=session['job_id']).first()
            
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Generate interview URL
            interview_base_url = os.getenv("INTERVIEW_BASE_URL", "http://localhost:5173")
            interview_url = f"{interview_base_url}/interview/session/{session_id}"
            
            # Calculate new deadline
            deadline = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
            
            # Send email
            email_sent = send_interview_invitation_email(
                candidate_email=candidate.email,
                candidate_name=candidate.name,
                job_title=job.title,
                interview_url=interview_url,
                completion_deadline=deadline,
                session_id=session_id
            )
            
            if email_sent:
                logger.info(f"Interview email resent successfully for session {session_id}")
                return {
                    "success": True,
                    "message": f"Interview email resent to {candidate.email}",
                    "session_id": session_id
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to send email")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend interview email for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_interview_stats(job_id: Optional[str] = None):
    """Get interview statistics."""
    from shared.db.database import db_session
    from sqlalchemy import text
    
    try:
        with db_session() as db:
            if job_id:
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN interview_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN interview_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN interview_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN interview_status = 'EXPIRED' THEN 1 ELSE 0 END) as expired
                    FROM interview_sessions
                    WHERE job_id = :job_id
                """)
                result = db.execute(query, {"job_id": job_id}).fetchone()
            else:
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN interview_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN interview_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN interview_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN interview_status = 'EXPIRED' THEN 1 ELSE 0 END) as expired
                    FROM interview_sessions
                """)
                result = db.execute(query).fetchone()
            
            return {
                "success": True,
                "stats": {
                    "total": result[0] or 0,
                    "pending": result[1] or 0,
                    "in_progress": result[2] or 0,
                    "completed": result[3] or 0,
                    "expired": result[4] or 0
                }
            }
    except Exception as e:
        logger.error(f"Failed to get interview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/session/{interview_id}/terminate")
async def terminate_interview(interview_id: int, request: dict):
    """Terminate interview session early and save partial results."""
    from shared.db.database import db_session
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        session_id = request.get('session_id')
        
        with db_session() as db:
            # Update interview session status
            query = text("""
                UPDATE interview_sessions
                SET interview_status = 'TERMINATED',
                    completed_at = :completed_at
                WHERE session_id = :session_id
            """)
            db.execute(query, {
                "session_id": session_id,
                "completed_at": datetime.now().isoformat()
            })
            db.commit()
            
            logger.info(f"Interview {interview_id} (session {session_id}) terminated by candidate")
            
            return {
                "success": True,
                "message": "Interview terminated. Progress saved.",
                "interview_id": interview_id,
                "session_id": session_id
            }
            
    except Exception as e:
        logger.error(f"Failed to terminate interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/validate/{session_id}")
async def validate_interview_session(session_id: str):
    """Validate that an interview session is active and return associated candidate/job details."""
    from interview.session_manager import get_interview_session
    try:
        session = get_interview_session(session_id)
        if session:
            status = session.get("status") or "PENDING"
            
            # Check if completed/expired/terminated
            if status in ["COMPLETED", "TERMINATED", "EXPIRED", "completed", "terminated", "expired"]:
                return {
                    "success": True,
                    "valid": False,
                    "message": f"Interview session is already {status.lower()}"
                }
                
            return {
                "success": True,
                "valid": True,
                "session_id": session["session_id"],
                "candidate_id": session["candidate_id"],
                "job_id": session["job_id"],
                "status": status,
                "message": "Session is valid"
            }
        else:
            return {
                "success": True,
                "valid": False,
                "message": "Invalid or expired session ID"
            }
    except Exception as e:
        logger.error(f"Failed to validate interview session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/completed-candidates")
async def get_completed_candidates():
    """Get candidates who have completed their interviews (status COMPLETED or evaluated)."""
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job, InterviewEvaluation, Application, InterviewSession
    from sqlalchemy import text, select

    try:
        with db_session() as db:
            candidates_dict = {}  # Use dict to deduplicate by candidate_id + job_id

            # First, get candidates from interview_sessions with COMPLETED status
            try:
                query = text("""
                    SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                           i.completed_at,
                           c.name as candidate_name, c.email as candidate_email,
                           j.title as job_title
                    FROM interview_sessions i
                    LEFT JOIN candidates c ON c.id = i.candidate_id
                    LEFT JOIN jobs j ON j.id = i.job_id
                    WHERE i.interview_status = 'COMPLETED'
                    ORDER BY i.completed_at DESC
                """)
                results = db.execute(query).fetchall()

                for row in results:
                    key = f"{row[1]}_{row[2]}"  # candidate_id_job_id
                    candidates_dict[key] = {
                        "session_id": row[0],
                        "candidate_id": row[1],
                        "job_id": row[2],
                        "status": row[3],
                        "completed_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
                        "candidate_name": row[5],
                        "candidate_email": row[6],
                        "job_title": row[7]
                    }

                logger.info(f"Retrieved {len(candidates_dict)} candidates from interview_sessions")
            except Exception as table_error:
                logger.warning(f"interview_sessions query failed: {table_error}")

            # Second, get candidates who have interview evaluations (they completed the interview)
            try:
                query = select(InterviewEvaluation).order_by(InterviewEvaluation.evaluated_at.desc())
                result = db.execute(query)
                evaluations = result.scalars().all()

                for eval in evaluations:
                    key = f"{eval.candidate_id}_{eval.job_id}"
                    
                    # Only add if not already in candidates_dict
                    if key not in candidates_dict:
                        # Get candidate details
                        candidate = db.execute(
                            select(Candidate).where(Candidate.id == eval.candidate_id).limit(1)
                        )
                        cand = candidate.scalar_one_or_none()

                        # Get job details
                        job = db.execute(
                            select(Job).where(Job.id == eval.job_id).limit(1)
                        )
                        job_obj = job.scalar_one_or_none()

                        if cand and job_obj:
                            candidates_dict[key] = {
                                "session_id": f"eval_{eval.id}",
                                "candidate_id": eval.candidate_id,
                                "job_id": eval.job_id,
                                "status": "COMPLETED",
                                "completed_at": eval.evaluated_at.isoformat() if eval.evaluated_at else None,
                                "candidate_name": cand.name,
                                "candidate_email": cand.email,
                                "job_title": job_obj.title
                            }

                logger.info(f"Added candidates from evaluations, total: {len(candidates_dict)}")
            except Exception as eval_error:
                logger.warning(f"Evaluations query failed: {eval_error}")

            # Third, get candidates with Application status HIRED or OFFER_ACCEPTED
            try:
                query = select(Application).where(
                    Application.status.in_(["HIRED", "OFFER_ACCEPTED", "OFFER_SENT"])
                ).order_by(Application.updated_at.desc())
                result = db.execute(query)
                applications = result.scalars().all()

                for app in applications:
                    key = f"{app.candidate_id}_{app.job_id}"
                    
                    # Only add if not already in candidates_dict
                    if key not in candidates_dict:
                        # Get candidate details
                        candidate = db.execute(
                            select(Candidate).where(Candidate.id == app.candidate_id).limit(1)
                        )
                        cand = candidate.scalar_one_or_none()

                        # Get job details
                        job = db.execute(
                            select(Job).where(Job.id == app.job_id).limit(1)
                        )
                        job_obj = job.scalar_one_or_none()

                        if cand and job_obj:
                            candidates_dict[key] = {
                                "session_id": f"app_{app.id}",
                                "candidate_id": app.candidate_id,
                                "job_id": app.job_id,
                                "status": "COMPLETED",
                                "completed_at": app.updated_at.isoformat() if app.updated_at else None,
                                "candidate_name": cand.name,
                                "candidate_email": cand.email,
                                "job_title": job_obj.title
                            }

                logger.info(f"Added candidates from applications, total: {len(candidates_dict)}")
            except Exception as app_error:
                logger.warning(f"Applications query failed: {app_error}")

            # Fourth, get candidates from InterviewSession table (published interview data)
            try:
                query = select(InterviewSession).order_by(InterviewSession.completed_at.desc())
                result = db.execute(query)
                interview_sessions = result.scalars().all()

                for session in interview_sessions:
                    key = f"{session.candidate_id}_{session.job_id}"
                    
                    # Only add if not already in candidates_dict and session is completed
                    if key not in candidates_dict and session.status == "COMPLETED":
                        # Get candidate details
                        candidate = db.execute(
                            select(Candidate).where(Candidate.id == session.candidate_id).limit(1)
                        )
                        cand = candidate.scalar_one_or_none()

                        # Get job details
                        job = db.execute(
                            select(Job).where(Job.id == session.job_id).limit(1)
                        )
                        job_obj = job.scalar_one_or_none()

                        if cand and job_obj:
                            candidates_dict[key] = {
                                "session_id": session.session_id,
                                "candidate_id": session.candidate_id,
                                "job_id": session.job_id,
                                "status": "COMPLETED",
                                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                                "candidate_name": cand.name,
                                "candidate_email": cand.email,
                                "job_title": job_obj.title
                            }

                logger.info(f"Added candidates from InterviewSession, total: {len(candidates_dict)}")
            except Exception as session_error:
                logger.warning(f"InterviewSession query failed: {session_error}")

            logger.info(f"Total completed candidates: {len(candidates_dict)}")
            return {"success": True, "candidates": list(candidates_dict.values())}

    except Exception as e:
        logger.error(f"Failed to get completed candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
