"""
Prescreening API — Stage 5 REST endpoints
Provides API access to prescreening chatbot and BGV functionality
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
from dotenv import load_dotenv
from groq import Groq

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.database import get_db
from shared.db.models import Candidate, Job, Application, ChatbotSession, ChatbotAnswer

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logging.getLogger(__name__).error(f"[Prescreening API] Failed to initialize Groq: {e}")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prescreening", tags=["prescreening"])


def _application_stage(status: Optional[str]) -> Optional[int]:
    if status in {"OUTREACH_SENT", "PRESCREENING"}:
        return 5
    if status in {"PRESCREENED", "DONE", "SELECTED", "INTERVIEW", "INTERVIEW_SCHEDULED"}:
        return 6
    return None


class PrescreeningStats(BaseModel):
    total_in_prescreening: int
    sessions_created: int
    sessions_completed: int
    passed: int
    failed: int
    bgv_pending: int
    bgv_cleared: int


@router.get("/stats", response_model=PrescreeningStats)
async def get_prescreening_stats(job_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Get prescreening statistics, optionally filtered by job."""
    
    query = select(Application)
    if job_id:
        query = query.where(Application.job_id == job_id)
    
    result = await db.execute(query)
    applications = result.scalars().all()
    
    in_prescreening = len([a for a in applications if a.status in ["OUTREACH_SENT", "PRESCREENING"]])
    prescreened = len([a for a in applications if a.status in ["PRESCREENED", "DONE"]])

    return PrescreeningStats(
        total_in_prescreening=in_prescreening,
        sessions_created=in_prescreening,
        sessions_completed=prescreened,
        passed=prescreened,
        failed=0,
        bgv_pending=0,
        bgv_cleared=0
    )


@router.get("/candidates")
async def get_prescreening_candidates(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get candidates in prescreening stage."""
    query = select(Candidate).join(Application)
    
    if job_id:
        query = query.where(Application.job_id == job_id)
    
    if status:
        query = query.where(Application.status == status)
    else:
        # Default to prescreening-related statuses
        query = query.where(Application.status.in_(["OUTREACH_SENT", "PRESCREENING", "PRESCREENED", "DONE"]))
    
    query = query.limit(limit)
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    result_list = []
    for c in candidates:
        # Get application info
        app_result = await db.execute(
            select(Application).where(
                Application.candidate_id == c.id,
                Application.job_id == job_id if job_id else True
            ).limit(1)
        )
        app = app_result.scalar_one_or_none()
        
        candidate_data = {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "location": c.location,
            "status": c.status,
            "application_status": app.status if app else None,
            "application_stage": _application_stage(app.status) if app else None,
            "score": c.score,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        result_list.append(candidate_data)
    
    return result_list


@router.get("/sessions")
async def get_prescreening_sessions(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get prescreening chatbot sessions."""
    from shared.db.models import ChatbotSession, ChatbotAnswer
    
    query = select(ChatbotSession)
    
    if job_id:
        query = query.where(ChatbotSession.job_id == job_id)
    
    if status:
        query = query.where(ChatbotSession.status == status)
    
    query = query.limit(limit).order_by(ChatbotSession.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    result_list = []
    for session in sessions:
        # Get candidate info
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == session.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        # Get job info
        job_result = await db.execute(
            select(Job).where(Job.id == session.job_id)
        )
        job = job_result.scalar_one_or_none()
        
        # Get answers and calculate score/verdict
        answers_result = await db.execute(
            select(ChatbotAnswer).where(ChatbotAnswer.session_id == session.session_id)
        )
        answers = answers_result.scalars().all()
        
        # Calculate average score and verdict
        avg_score = None
        verdict = None
        if answers:
            score_map = {"Excellent": 4.0, "Good": 3.0, "Average": 2.0, "Poor": 1.0}
            scores = [score_map.get(ans.ai_score, 0) for ans in answers if ans.ai_score]
            if scores:
                avg_score = sum(scores) / len(scores)
                # Determine verdict based on avg score
                if avg_score >= 3.0:
                    verdict = "PASS"
                elif avg_score >= 2.5:
                    verdict = "BORDERLINE"
                else:
                    verdict = "FAIL"
        
        # Parse questions
        questions = []
        if session.questions:
            try:
                questions = json.loads(session.questions)
            except:
                questions = []
        
        session_data = {
            "session_id": session.session_id,
            "candidate_id": session.candidate_id,
            "candidate_name": candidate.name if candidate else "Unknown",
            "candidate_email": candidate.email if candidate else None,
            "job_id": session.job_id,
            "job_title": job.title if job else "Unknown",
            "status": session.status,
            "token": session.token,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "total_questions": len(questions),
            "answered_questions": len(answers),
            "questions": questions,
            "avg_score": avg_score,
            "verdict": verdict,
            "interview_session_id": None
        }
        if verdict == "PASS":
            try:
                from sqlalchemy import text
                interview_result = await db.execute(
                    text("""
                        SELECT session_id
                        FROM interview_sessions
                        WHERE candidate_id = :candidate_id
                          AND job_id = :job_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {"candidate_id": session.candidate_id, "job_id": session.job_id}
                )
                interview_row = interview_result.fetchone()
                if interview_row:
                    session_data["interview_session_id"] = interview_row[0]
            except Exception:
                session_data["interview_session_id"] = None
        result_list.append(session_data)
    
    return result_list


@router.get("/jobs")
async def get_jobs_with_prescreening(db: AsyncSession = Depends(get_db)):
    """Get jobs with prescreening statistics."""
    result = await db.execute(select(Job))
    jobs = result.scalars().all()
    
    result_list = []
    for job in jobs:
        # Get applications for this job
        apps_result = await db.execute(
            select(Application).where(Application.job_id == job.id)
        )
        applications = apps_result.scalars().all()
        
        in_prescreening = len([a for a in applications if a.status in ["OUTREACH_SENT", "PRESCREENING"]])
        prescreened = len([a for a in applications if a.status in ["PRESCREENED", "DONE"]])
        
        job_data = {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "location": job.location,
            "status": job.status,
            "in_prescreening_count": in_prescreening,
            "prescreened_count": prescreened,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }
        result_list.append(job_data)
    
    return result_list


# ── CUSTOM DYNAMIC PRESCREENING FLOW FOR CANDIDATE ───────────────────────────

def _generate_questions_groq(job_title: str, jd_text: str) -> list[str]:
    """Generate 6 pre-screening questions dynamically using Groq Llama AI."""
    if not groq_client:
        logger.warning("[Prescreening API] Groq client not initialized, using fallback questions")
        return [
            "What motivated you to apply for this position at our company?",
            "Describe your most relevant work experience for this role.",
            "What are your key technical skills and how have you applied them?",
            "How do you handle tight deadlines and pressure in a work environment?",
            "What are your salary expectations for this position?",
            "When would you be available to start if selected?"
        ]
    
    prompt = (
        f"Generate exactly 6 pre-screening interview questions for a {job_title} position.\n"
        f"Job Description: {jd_text[:2000] if jd_text else 'Not specified'}\n\n"
        f"Focus the questions on:\n"
        f"1. Motivation and interest in the role\n"
        f"2. Relevant work experience\n"
        f"3. Key technical skills\n"
        f"4. Work style and handling pressure\n"
        f"5. Salary expectations\n"
        f"6. Availability to start\n\n"
        f"Return ONLY a JSON array of 6 question strings. No explanation. No markdown code fences. No numbering. "
        f"Example: [\"Question 1?\", \"Question 2?\", ...]"
    )
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert HR recruitment assistant. Return only a valid JSON array of strings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        text = completion.choices[0].message.content.strip()
        
        # Clean markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
            
        questions = json.loads(text.strip())
        return [str(q) for q in questions[:6]]
    except Exception as e:
        logger.error(f"Failed to generate questions via Groq: {e}")
        # Return fallback fixed questions
        return [
            f"What motivated you to apply for this {job_title} position?",
            f"Describe your most relevant work experience for a {job_title} role.",
            "What are your key technical skills and how have you applied them?",
            "How do you handle tight deadlines and pressure in a work environment?",
            "What are your salary expectations for this position?",
            "When would you be available to start if selected?"
        ]


class StartSessionRequest(BaseModel):
    candidate_id: str


class AnswerSubmit(BaseModel):
    question_index: int
    question: str
    answer: str


class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: list[AnswerSubmit]


@router.get("/all-candidates")
async def get_all_candidates(db: AsyncSession = Depends(get_db)):
    """Get all candidates for the dropdown selection."""
    query = select(Candidate)
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    result_list = []
    for c in candidates:
        # Get candidate's job
        job_title = "Unknown Job"
        if c.job_id:
            job_result = await db.execute(select(Job).where(Job.id == c.job_id).limit(1))
            job = job_result.scalar_one_or_none()
            if job:
                job_title = job.title
                
        result_list.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "job_id": c.job_id,
            "job_title": job_title
        })
    return result_list


@router.post("/start-session")
async def start_prescreening_session_custom(req: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    """Start a new prescreening session for the candidate and dynamically generate questions."""
    # 1. Fetch candidate
    candidate_result = await db.execute(select(Candidate).where(Candidate.id == req.candidate_id).limit(1))
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # 2. Fetch job
    if not candidate.job_id:
        raise HTTPException(status_code=400, detail="Candidate is not assigned to a job")
        
    job_result = await db.execute(select(Job).where(Job.id == candidate.job_id).limit(1))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 3. Generate questions dynamically using Groq
    questions = _generate_questions_groq(job.title, job.description or "")
    
    # 4. Create or update ChatbotSession
    session_result = await db.execute(
        select(ChatbotSession).where(
            ChatbotSession.candidate_id == candidate.id,
            ChatbotSession.job_id == job.id
        ).limit(1)
    )
    session = session_result.scalar_one_or_none()
    
    token = str(uuid.uuid4())
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=48)
    
    if session:
        session.token = token
        session.status = "IN_PROGRESS"
        session.questions = json.dumps(questions)
        session.expires_at = expires_at
        session.completed_at = None
    else:
        session = ChatbotSession(
            session_id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            job_id=job.id,
            token=token,
            created_at=now,
            expires_at=expires_at,
            status="IN_PROGRESS",
            questions=json.dumps(questions)
        )
        db.add(session)
        
    await db.commit()
    
    return {
        "success": True,
        "session_id": session.session_id,
        "token": token,
        "questions": [{ "id": i + 1, "question": q, "minChars": 100 } for i, q in enumerate(questions)],
        "job_title": job.title,
        "candidate_name": candidate.name
    }


@router.post("/submit-answers")
async def submit_prescreening_answers_custom(req: SubmitAnswersRequest, db: AsyncSession = Depends(get_db)):
    """Submit candidate answers, mark session completed, and run Groq evaluation synchronously."""
    # 1. Fetch chatbot session
    session_result = await db.execute(
        select(ChatbotSession).where(ChatbotSession.session_id == req.session_id).limit(1)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Delete any existing answers for this session
    from sqlalchemy import delete
    await db.execute(delete(ChatbotAnswer).where(ChatbotAnswer.session_id == session.session_id))
    
    # 3. Save answers
    for ans in req.answers:
        answer_rec = ChatbotAnswer(
            answer_id=str(uuid.uuid4()),
            session_id=session.session_id,
            question_index=ans.question_index,
            question=ans.question,
            answer=ans.answer,
            answered_at=datetime.utcnow()
        )
        db.add(answer_rec)
        
    # 4. Mark session completed
    session.status = "COMPLETED"
    session.completed_at = datetime.utcnow()
    await db.commit()
    
    # 5. Evaluate answers synchronously using answer_evaluator
    from prescreening.answer_evaluator import evaluate_session
    try:
        summary = evaluate_session(session.session_id)
    except Exception as e:
        logger.error(f"Sync evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI evaluation failed: {str(e)}")

    # 6. Re-confirm session status as COMPLETED in the async DB (evaluate_session uses sync db_session)
    session_refresh = await db.execute(
        select(ChatbotSession).where(ChatbotSession.session_id == req.session_id).limit(1)
    )
    session_obj = session_refresh.scalar_one_or_none()
    if session_obj and session_obj.status != "COMPLETED":
        session_obj.status = "COMPLETED"
        session_obj.completed_at = datetime.utcnow()
        await db.commit()
        
    # 6. Fetch created interview session ID if passed or borderline
    interview_session_id = summary.get("interview_session_id")
    if summary.get("verdict") in ["PASS", "BORDERLINE"] and not interview_session_id:
        from sqlalchemy import text
        query = text("SELECT session_id FROM interview_sessions WHERE candidate_id = :cid ORDER BY created_at DESC LIMIT 1")
        res = await db.execute(query, {"cid": session.candidate_id})
        row = res.fetchone()
        if row:
            interview_session_id = row[0]
            
    return {
        "success": True,
        "verdict": summary.get("verdict", "FAIL"),
        "avg_score": summary.get("avg_score", 0.0),
        "interview_session_id": interview_session_id
    }
