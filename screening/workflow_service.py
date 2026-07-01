"""
screening/workflow_service.py
Service for managing candidate pipeline stages and enforcing business transition rules.
"""
from enum import Enum
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.db.models import Candidate, Application

logger = logging.getLogger(__name__)

class CandidateStage(str, Enum):
    NEW = "new"
    PRESCREENING = "prescreening"
    INTERVIEW = "interview"
    REJECTED = "rejected"

ALLOWED_TRANSITIONS = {
    CandidateStage.NEW: [CandidateStage.PRESCREENING, CandidateStage.INTERVIEW, CandidateStage.REJECTED],
    CandidateStage.PRESCREENING: [CandidateStage.INTERVIEW, CandidateStage.REJECTED],
    CandidateStage.INTERVIEW: [CandidateStage.REJECTED],
    CandidateStage.REJECTED: [CandidateStage.PRESCREENING, CandidateStage.INTERVIEW]
}

async def update_candidate_stage(db: AsyncSession, candidate_id: str, new_stage: CandidateStage) -> Candidate:
    """Updates candidate status and corresponding Application status with transition validation."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    current_stage = candidate.status or "new"
    
    # Normalize input
    try:
        new_stage_enum = CandidateStage(new_stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")
        
    # Check transitions (allow no-op transitions)
    if current_stage != new_stage_enum:
        allowed = ALLOWED_TRANSITIONS.get(current_stage, [])
        if new_stage_enum not in allowed:
            raise HTTPException(
                status_code=400, 
                detail=f"Transition from '{current_stage}' to '{new_stage_enum.value}' is not allowed"
            )
        
    # Update candidate stage
    old_stage = candidate.status
    candidate.status = new_stage_enum.value
    
    # Log audit trail
    logger.info(f"AUDIT: Candidate {candidate_id} ({candidate.name}) stage changed from '{old_stage}' to '{new_stage_enum.value}'")
    
    # Update application status
    if candidate.job_id:
        app_result = await db.execute(
            select(Application).where(
                Application.candidate_id == candidate.id,
                Application.job_id == candidate.job_id
            )
        )
        application = app_result.scalar_one_or_none()
        if application:
            old_app_status = application.status
            if new_stage_enum == CandidateStage.INTERVIEW:
                application.status = "INTERVIEW_PENDING"
                
                # Automatically create interview session and send invite email
                try:
                    from interview.interview_email_sender import send_interview_invitation_email
                    from shared.db.models import Job
                    from datetime import datetime, timedelta
                    import uuid
                    from sqlalchemy import text
                    import os
                    
                    # Fetch job details
                    job_res = await db.execute(select(Job).where(Job.id == candidate.job_id).limit(1))
                    job = job_res.scalar_one_or_none()
                    job_title = job.title if job else "Software Engineer"
                    
                    # Check for existing active session
                    existing_res = await db.execute(text("""
                        SELECT session_id
                        FROM interview_sessions
                        WHERE candidate_id = :candidate_id
                          AND job_id = :job_id
                          AND COALESCE(interview_status, 'PENDING') IN ('PENDING', 'IN_PROGRESS')
                        ORDER BY created_at DESC
                        LIMIT 1
                    """), {
                        "candidate_id": candidate.id,
                        "job_id": candidate.job_id,
                    })
                    existing = existing_res.fetchone()
                    
                    if existing:
                        session_id = existing[0]
                    else:
                        session_id = f"sess_{uuid.uuid4().hex[:12]}"
                        await db.execute(text("""
                            INSERT INTO interview_sessions
                            (session_id, candidate_id, job_id, phase, interview_status, invited_at, created_at)
                            VALUES
                            (:session_id, :candidate_id, :job_id, 'HR', 'PENDING', :invited_at, :created_at)
                        """), {
                            "session_id": session_id,
                            "candidate_id": candidate.id,
                            "job_id": candidate.job_id,
                            "invited_at": datetime.now(),
                            "created_at": datetime.now()
                        })
                        await db.commit()
                    
                    interview_base_url = os.getenv("INTERVIEW_BASE_URL", "http://localhost:5173")
                    interview_url = f"{interview_base_url}/interview/session/{session_id}"
                    
                    deadline = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
                    # Send email
                    email_sent = send_interview_invitation_email(
                        candidate_email=candidate.email,
                        candidate_name=candidate.name,
                        job_title=job_title,
                        interview_url=interview_url,
                        completion_deadline=deadline,
                        session_id=session_id
                    )
                    
                    # Track invitation status (SENT or FAILED)
                    inv_status = "SENT" if email_sent else "FAILED"
                    await db.execute(text("""
                        UPDATE interview_sessions
                        SET interview_status = :inv_status
                        WHERE session_id = :session_id
                    """), {
                        "inv_status": inv_status,
                        "session_id": session_id
                    })
                    await db.commit()
                except Exception as ex:
                    logger.error(f"Failed to automatically trigger interview session or email: {ex}")
            elif new_stage_enum == CandidateStage.PRESCREENING:
                application.status = "SHORTLISTED"
                
                # Auto-generate session details if not exists
                from shared.db.models import ChatbotSession, Job
                import json
                import uuid
                from datetime import datetime, timedelta
                
                session_res = await db.execute(
                    select(ChatbotSession).where(
                        ChatbotSession.candidate_id == candidate.id,
                        ChatbotSession.job_id == candidate.job_id
                    ).limit(1)
                )
                session = session_res.scalar_one_or_none()
                if not session:
                    from prescreening.prescreening_api import _generate_questions_groq
                    
                    # Fetch job
                    job_res = await db.execute(select(Job).where(Job.id == candidate.job_id).limit(1))
                    job = job_res.scalar_one_or_none()
                    job_title = job.title if job else "Software Engineer"
                    job_desc = job.description if job else ""
                    
                    questions = _generate_questions_groq(job_title, job_desc)
                    token = str(uuid.uuid4())
                    expires_at = datetime.utcnow() + timedelta(hours=48)
                    
                    session = ChatbotSession(
                        session_id=str(uuid.uuid4()),
                        candidate_id=candidate.id,
                        job_id=candidate.job_id,
                        token=token,
                        created_at=datetime.utcnow(),
                        expires_at=expires_at,
                        status="IN_PROGRESS",
                        questions=json.dumps(questions)
                    )
                    db.add(session)
                    await db.flush()
                
                # Publish event to trigger automated invitation email
                from shared.queue.event_bus import event_bus
                from shared.queue.event_topics import EventTopics
                try:
                    await event_bus.publish(
                        EventTopics.CANDIDATE_SHORTLISTED,
                        {
                            "candidate_id": candidate.id,
                            "job_id": candidate.job_id,
                            "name": candidate.name,
                            "email": candidate.email,
                        },
                        agent="workflow_service_auto"
                    )
                    logger.info(f"Published candidate.shortlisted event for candidate {candidate.id}")
                except Exception as event_error:
                    logger.error(f"Failed to publish candidate.shortlisted event: {event_error}")
            elif new_stage_enum == CandidateStage.REJECTED:
                application.status = "REJECTED"
            elif new_stage_enum == CandidateStage.NEW:
                application.status = "applied"
            logger.info(f"AUDIT: Application {application.id} status updated from '{old_app_status}' to '{application.status}'")
            
    await db.commit()
    return candidate
