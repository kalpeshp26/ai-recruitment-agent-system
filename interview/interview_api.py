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
                               j.title as job_title, e.final_score, e.recommendation
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        LEFT JOIN interview_evaluations e ON e.session_id = i.session_id
                        WHERE i.job_id = :job_id
                        ORDER BY i.invited_at DESC
                    """)
                    results = db.execute(query, {"job_id": job_id}).fetchall()
                else:
                    query = text("""
                        SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                               i.invited_at, i.started_at, i.completed_at,
                               c.name as candidate_name, c.email as candidate_email,
                               j.title as job_title, e.final_score, e.recommendation
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        LEFT JOIN interview_evaluations e ON e.session_id = i.session_id
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
                        "final_score": row[10],
                        "recommendation": row[11]
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
                from sqlalchemy import text
                db.execute(text("""
                    UPDATE interview_sessions
                    SET interview_status = 'SENT', invited_at = :now
                    WHERE session_id = :session_id
                """), {
                    "now": datetime.now(),
                    "session_id": session_id
                })
                db.commit()
                logger.info(f"Interview email resent successfully for session {session_id}")
                return {
                    "success": True,
                    "message": f"Interview email resent to {candidate.email}",
                    "session_id": session_id
                }
            else:
                from sqlalchemy import text
                db.execute(text("""
                    UPDATE interview_sessions
                    SET interview_status = 'FAILED'
                    WHERE session_id = :session_id
                """), {
                    "session_id": session_id
                })
                db.commit()
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
async def terminate_interview(interview_id: str, request: dict):
    """Terminate interview session early, calculate partial results, and save as COMPLETED."""
    from shared.db.database import db_session
    from shared.db.models import InterviewEvaluation, Application, Candidate, Job
    from shared.db.interview import InterviewSession, InterviewTurn
    from shared.queue.event_bus import event_bus
    from shared.queue.event_topics import EventTopics
    from sqlalchemy import text
    from datetime import datetime
    import uuid
    import asyncio
    
    try:
        session_id = request.get('session_id') or interview_id
        
        with db_session() as db:
            # 1. Find interview session
            session_obj = db.query(InterviewSession).filter(
                (InterviewSession.session_id == session_id) | (InterviewSession.id == session_id)
            ).first()
            
            if not session_obj:
                raise HTTPException(status_code=404, detail="Interview session not found")
                
            # Get key info
            db_session_id = session_obj.id
            candidate_id = session_obj.candidate_id
            job_id = session_obj.job_id
            
            # 2. Get candidate name and job title
            candidate = db.query(Candidate).filter_by(id=candidate_id).first()
            job = db.query(Job).filter_by(id=job_id).first()
            candidate_name = candidate.name if candidate else "Candidate"
            candidate_email = candidate.email if candidate else ""
            job_title = job.title if job else "Position"
            
            # 3. Retrieve all answered turns so far
            turns = db.query(InterviewTurn).filter(
                InterviewTurn.interview_id == db_session_id
            ).all()
            
            # 4. Calculate overall score and recommendation
            if turns:
                avg_content = sum(t.content_score for t in turns if t.content_score is not None) / len(turns)
                avg_behavior = sum(t.behavior_score for t in turns if t.behavior_score is not None) / len(turns)
                overall_score = (avg_content + avg_behavior) / 2
            else:
                avg_content = 0.0
                avg_behavior = 0.0
                overall_score = 0.0
                
            # Determine recommendation
            if overall_score >= 0.7:
                recommendation = "hire"
            elif overall_score >= 0.5:
                recommendation = "maybe"
            else:
                recommendation = "reject"
                
            # 5. Update interview session status to completed
            session_obj.status = "completed"
            session_obj.interview_status = "COMPLETED"
            session_obj.completed_at = datetime.utcnow()
            
            db.commit()
            
            # 6. Publish interview completion event so process_interview_completed_event executes
            # and updates evaluations & applications tables synchronously
            await event_bus.publish(
                EventTopics.INTERVIEW_COMPLETED,
                {
                    "interview_id": session_obj.session_id,
                    "candidate_id": candidate_id,
                    "job_id": job_id,
                    "overall_score": overall_score,
                    "content_score": avg_content,
                    "behavior_score": avg_behavior,
                    "recommendation": recommendation,
                    "total_turns": len(turns),
                    "completed_at": session_obj.completed_at.isoformat(),
                    "strengths": f"Completed {len(turns)} turns before manual termination.",
                    "weaknesses": "Interview ended early by candidate/recruiter."
                },
                agent="interview_system"
            )
            
            logger.info(f"Interview session {session_id} ended early. Saved progress for candidate {candidate_id}")
            
            return {
                "success": True,
                "message": "Interview completed successfully. Progress saved.",
                "interview_id": db_session_id,
                "session_id": session_obj.session_id
            }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to terminate/complete interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/validate/{session_id}")
async def validate_interview_session(session_id: str):
    """Validate that an interview session is active and return associated candidate/job details."""
    from interview.session_manager import get_interview_session
    from shared.db.database import db_session
    from shared.db.models import Candidate
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
                
            # Fetch candidate name and email
            candidate_name = "Candidate"
            candidate_email = "candidate@example.com"
            try:
                with db_session() as db:
                    candidate = db.query(Candidate).filter_by(id=session["candidate_id"]).first()
                    if candidate:
                        candidate_name = candidate.name
                        candidate_email = candidate.email
            except Exception as db_err:
                logger.warning(f"Failed to fetch candidate details for session validation: {db_err}")
                
            return {
                "success": True,
                "valid": True,
                "session_id": session["session_id"],
                "candidate_id": session["candidate_id"],
                "job_id": session["job_id"],
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
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
    from shared.db.models import Candidate, Job, InterviewEvaluation, Application
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
                query = select(InterviewEvaluation).where(
                    InterviewEvaluation.recommendation.in_(["HIRE", "STRONG_HIRE"])
                ).order_by(InterviewEvaluation.created_at.desc())
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
                                "completed_at": eval.created_at.isoformat() if eval.created_at else None,
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

            logger.info(f"Total completed candidates: {len(candidates_dict)}")
            return {"success": True, "candidates": list(candidates_dict.values())}

    except Exception as e:
        logger.error(f"Failed to get completed candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/turns")
async def get_session_turns(session_id: str):
    """Retrieve detailed turns and evaluation scorecard for a session."""
    from shared.db.database import db_session
    from sqlalchemy import text
    try:
        with db_session() as db:
            # Get interview session
            session_row = db.execute(text("""
                SELECT id, candidate_id, job_id, interview_status, invited_at, started_at, completed_at
                FROM interview_sessions
                WHERE session_id = :session_id
            """), {"session_id": session_id}).fetchone()
            
            if not session_row:
                raise HTTPException(status_code=404, detail="Interview session not found")
                
            # Get candidate name and job title
            from shared.db.models import Candidate, Job
            candidate = db.query(Candidate).filter_by(id=session_row[1]).first()
            job = db.query(Job).filter_by(id=session_row[2]).first()
            candidate_name = candidate.name if candidate else "Unknown Candidate"
            candidate_email = candidate.email if candidate else ""
            job_title = job.title if job else "Position TBD"
                
            # Get evaluation
            eval_row = db.execute(text("""
                SELECT content_score, behavior_score, final_score, recommendation, evaluator_notes
                FROM interview_evaluations
                WHERE session_id = :session_id
            """), {"session_id": session_id}).fetchone()
            
            # Get turns
            turns_res = db.execute(text("""
                SELECT turn_number, question_text, question_difficulty, candidate_response, 
                       response_time_sec, content_score, behavior_score, final_score, is_followup
                FROM interview_turns
                WHERE interview_id = :interview_db_id
                ORDER BY turn_number ASC, is_followup ASC
            """), {"interview_db_id": session_row[0]}).fetchall()
            
            turns = []
            for t in turns_res:
                turns.append({
                    "turn_number": t[0],
                    "question_text": t[1],
                    "difficulty": t[2],
                    "response": t[3],
                    "response_time": t[4],
                    "content_score": t[5],
                    "behavior_score": t[6],
                    "final_score": t[7],
                    "is_followup": bool(t[8])
                })
                
            evaluation = None
            if eval_row:
                evaluation = {
                    "technical_score": eval_row[0],
                    "behavior_score": eval_row[1],
                    "final_score": eval_row[2],
                    "recommendation": eval_row[3],
                    "summary": eval_row[4]
                }
                
            return {
                "success": True,
                "session_id": session_id,
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "job_title": job_title,
                "status": session_row[3],
                "invited_at": session_row[4].isoformat() if hasattr(session_row[4], "isoformat") else session_row[4],
                "started_at": session_row[5].isoformat() if hasattr(session_row[5], "isoformat") else session_row[5],
                "completed_at": session_row[6].isoformat() if hasattr(session_row[6], "isoformat") else session_row[6],
                "turns": turns,
                "evaluation": evaluation
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get turns for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

