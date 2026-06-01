"""
Live interview API router used by the dashboard and candidate interview flow.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from backend.config import settings
from backend.database.db import get_db
from backend.models.interview import InterviewAnswer, InterviewEvaluation, InterviewQuestion, InterviewSession, ProctoringViolation
from backend.prompts import FALLBACK_QUESTIONS
from backend.schemas.interview import (
    EndInterviewRequest,
    EndInterviewResponse,
    InterviewResultResponse,
    NextQuestionResponse,
    ProctoringEventRequest,
    ProctoringEventResponse,
    SessionStatusResponse,
    SkipQuestionRequest,
    SkipQuestionResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    STTRequest,
    STTResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    TTSRequest,
    TTSResponse,
)
from backend.services import ai_service, stt_service, tts_service
from backend.services.interview_service import calculate_final_score, get_session_status, start_or_resume_session

router = APIRouter()


async def verify_access(request: Request, db: AsyncSession = Depends(get_db)) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_authorization")

    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
        return user_id
    except JWTError:
        res = await db.execute(select(InterviewSession).where(InterviewSession.session_token == token))
        session = res.scalars().first()
        if session:
            return session.user_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")


def _candidate_name(user_id: str) -> str:
    return user_id.replace("user-", "").replace("_", " ").title() if user_id else "Unknown"


@router.get("/sessions")
async def list_sessions(user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(InterviewSession, InterviewEvaluation)
        .outerjoin(InterviewEvaluation, InterviewEvaluation.session_id == InterviewSession.id)
        .order_by(InterviewSession.start_time.desc())
    )

    sessions = []
    for session, evaluation in rows.all():
        sessions.append(
            {
                "interview_id": session.id,
                "session_id": session.id,
                "candidate_name": _candidate_name(session.user_id),
                "candidate_email": None,
                "job_title": session.role,
                "phase": "COMPLETE" if session.status == "COMPLETED" else ("IN_PROGRESS" if session.status not in {"TERMINATED", "COMPLETED"} else session.status),
                "overall_score": float((evaluation.final_score if evaluation else 0.0) / 100.0),
                "created_at": session.start_time,
                "updated_at": session.last_activity_at,
                "final_score": float(evaluation.final_score) if evaluation else None,
                "evaluation_id": evaluation.id if evaluation else None,
            }
        )
    return sessions


@router.post("/start", response_model=StartInterviewResponse, status_code=201)
async def start_interview(req: StartInterviewRequest, db: AsyncSession = Depends(get_db)):
    if req.answer_mode not in ("voice", "text"):
        raise HTTPException(status_code=400, detail="invalid_answer_mode")

    user_id = f"user-{req.role}"
    session = await start_or_resume_session(db, user_id=user_id, role=req.role, answer_mode=req.answer_mode)
    return StartInterviewResponse(
        session_id=session.id,
        session_token=session.session_token,
        status=session.status,
        start_time=session.start_time,
        answer_mode=session.answer_mode,
    )


@router.get("/session/{session_id}/status", response_model=SessionStatusResponse)
async def session_status(session_id: str, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    try:
        data = await get_session_status(db, session_id)
        return SessionStatusResponse(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")


@router.get("/session/{session_id}/next-question", response_model=NextQuestionResponse)
async def next_question(session_id: str, force_refresh: Optional[bool] = False, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    q = select(InterviewQuestion).where(InterviewQuestion.session_id == session_id).order_by(InterviewQuestion.question_index.desc()).limit(1)
    res = await db.execute(q)
    last = res.scalars().first()
    next_index = (last.question_index + 1) if last else 0
    if next_index >= settings.INTELLIHIRE_MAX_QUESTIONS:
        raise HTTPException(status_code=400, detail="no_more_questions")

    question_bank = FALLBACK_QUESTIONS.get("medium") or FALLBACK_QUESTIONS.get("easy") or ["Describe a challenging problem you solved."]
    question_text = question_bank[next_index % len(question_bank)]
    question_id = __import__("uuid").uuid4().hex
    question = InterviewQuestion(
        id=question_id,
        session_id=session_id,
        question_text=question_text,
        difficulty="medium",
        category="general",
        time_limit=120,
        question_index=next_index,
    )
    db.add(question)
    await db.flush()

    return NextQuestionResponse(
        question_id=question_id,
        question_text=question_text,
        difficulty="medium",
        category="general",
        time_limit=120,
        question_index=next_index,
        tts_audio_url=None,
    )


@router.post("/session/{session_id}/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(session_id: str, req: dict, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    try:
        model = SubmitAnswerRequest.model_validate(req)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    transcript = model.answer_text or ""
    if model.answer_audio_url and not transcript:
        try:
            transcript = await stt_service.transcribe_audio(b"")
        except Exception:
            raise HTTPException(status_code=422, detail="stt_failed")

    question_res = await db.execute(select(InterviewQuestion.question_text).where(InterviewQuestion.id == model.question_id))
    question_text = question_res.scalar_one_or_none() or ""
    eval_res = await ai_service.evaluate_answer(question=question_text, answer=transcript, difficulty="medium", role="", time_taken_ms=model.response_time_ms)

    answer_id = __import__("uuid").uuid4().hex
    answer = InterviewAnswer(
        id=answer_id,
        question_id=model.question_id,
        answer_text=transcript,
        answer_audio_url=model.answer_audio_url,
        ai_feedback=eval_res.get("summary", ""),
        scores={
            "technical": eval_res.get("technical", 5.0),
            "communication": eval_res.get("communication", 5.0),
            "confidence": eval_res.get("confidence", 5.0),
            "problem_solving": eval_res.get("problem_solving", 5.0),
            "total": eval_res.get("total", 5.0),
        },
        response_time=model.response_time_ms,
        is_skipped=False,
    )
    db.add(answer)
    await db.flush()

    return SubmitAnswerResponse(
        answer_id=answer_id,
        scores=answer.scores,
        ai_feedback=answer.ai_feedback or "",
        rl={"state_before": "", "action_taken": "same", "reward": 0.0, "state_after": ""},
        next_question_available=True,
    )


@router.post("/session/{session_id}/skip-question", response_model=SkipQuestionResponse)
async def skip_question(session_id: str, req: SkipQuestionRequest, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    answer_id = __import__("uuid").uuid4().hex
    answer = InterviewAnswer(
        id=answer_id,
        question_id=req.question_id,
        answer_text=None,
        answer_audio_url=None,
        ai_feedback=None,
        scores={"technical": 0.0, "communication": 0.0, "confidence": 0.0, "problem_solving": 0.0, "total": 0.0},
        response_time=0,
        is_skipped=True,
    )
    db.add(answer)
    res = await db.execute(select(InterviewQuestion).where(InterviewQuestion.id == req.question_id))
    question = res.scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="question_not_found")

    await db.flush()
    return SkipQuestionResponse(skipped_question_id=answer_id, penalty=1, current_question_index=question.question_index + 1, next_question_available=True)


@router.post("/session/{session_id}/end", response_model=EndInterviewResponse)
async def end_session(session_id: str, req: EndInterviewRequest, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    result = await calculate_final_score(db, session_id)
    return EndInterviewResponse(session_id=session_id, status="COMPLETED", evaluation_id=result["evaluation_id"], final_score=result["final_score"])


@router.get("/session/{session_id}/result", response_model=InterviewResultResponse)
async def get_result(session_id: str, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(InterviewEvaluation).where(InterviewEvaluation.session_id == session_id))
    evaluation = res.scalars().first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="evaluation_not_found")

    return InterviewResultResponse(
        session_id=session_id,
        technical_score=float(evaluation.technical_score),
        communication_score=float(evaluation.communication_score),
        confidence_score=float(evaluation.confidence_score),
        problem_solving_score=float(evaluation.problem_solving_score),
        penalty_points=int(evaluation.penalty_points),
        final_score=float(evaluation.final_score),
        summary=evaluation.summary,
    )


@router.get("/session/{session_id}/report")
async def interview_report(session_id: str, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    eval_res = await db.execute(select(InterviewEvaluation).where(InterviewEvaluation.session_id == session_id))
    evaluation = eval_res.scalars().first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="evaluation_not_found")

    answers_res = await db.execute(
        select(InterviewQuestion.question_text, InterviewAnswer.answer_text, InterviewAnswer.response_time)
        .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.question_index.asc())
    )

    turn_reviews = []
    for index, (question_text, answer_text, response_time) in enumerate(answers_res.all(), start=1):
        turn_reviews.append(
            {
                "turn_number": index,
                "question_text": question_text,
                "candidate_response": answer_text,
                "content_score": float(evaluation.technical_score) / 100.0,
                "behavior_score": float(evaluation.communication_score) / 100.0,
                "final_score": float(evaluation.final_score) / 100.0,
                "intent": "answer",
                "response_time_sec": int((response_time or 0) / 1000),
                "followups": [],
            }
        )

    return {
        "overall_score": float(evaluation.final_score) / 100.0,
        "content_score": float(evaluation.technical_score) / 100.0,
        "behavior_score": float(evaluation.communication_score) / 100.0,
        "total_turns": len(turn_reviews),
        "feedback_summary": evaluation.summary or "",
        "turn_reviews": turn_reviews,
        "recommendation": "hire" if evaluation.final_score >= 70 else ("maybe" if evaluation.final_score >= 50 else "reject"),
    }


@router.post("/session/{session_id}/proctoring-event", response_model=ProctoringEventResponse, status_code=201)
async def proctoring_event(session_id: str, req: ProctoringEventRequest, user_id: str = Depends(verify_access), db: AsyncSession = Depends(get_db)):
    if req.event_type not in ("tab_switch", "webcam_missing", "multiple_faces", "copy_paste", "webcam_unavailable"):
        raise HTTPException(status_code=422, detail="invalid_event_type")

    current = await db.execute(select(func.count(ProctoringViolation.id)).where(ProctoringViolation.session_id == session_id))
    warning_number = int(current.scalar() or 0) + 1
    violation_id = __import__("uuid").uuid4().hex
    db.add(
        ProctoringViolation(
            id=violation_id,
            session_id=session_id,
            event_type=req.event_type,
            screenshot_url=req.screenshot_url,
            warning_number=warning_number,
        )
    )

    session_res = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    session = session_res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="session_not_found")

    session.warning_count = warning_number
    await db.flush()
    if warning_number >= settings.PROCTORING_MAX_WARNINGS:
        session.status = "TERMINATED"
        await calculate_final_score(db, session_id)
        return ProctoringEventResponse(violation_id=violation_id, warning_number=warning_number, session_status="TERMINATED")

    return ProctoringEventResponse(violation_id=violation_id, warning_number=warning_number, session_status=session.status)


@router.post("/tts", response_model=TTSResponse)
async def tts(req: TTSRequest, user_id: str = Depends(verify_access)):
    try:
        await tts_service.synthesise_speech(req.text, voice=req.voice, sample_rate=req.sample_rate)
        return TTSResponse(audio_url="https://storage.example/tts/placeholder.wav", duration_ms=0)
    except Exception:
        raise HTTPException(status_code=503, detail="tts_failed")


@router.post("/stt", response_model=STTResponse)
async def stt(req: STTRequest, user_id: str = Depends(verify_access)):
    return STTResponse(transcript="", confidence=0.0, duration_ms=0)


@router.post("/session/{session_id}/ai/evaluate")
async def ai_evaluate(session_id: str, payload: dict, user_id: str = Depends(verify_access)):
    """Evaluate an answer using AI without persisting (useful for preview/testing)."""
    try:
        question = payload.get("question_text", "")
        answer = payload.get("answer_text", "")
        time_taken = int(payload.get("time_taken_ms", 0))
    except Exception:
        raise HTTPException(status_code=422, detail="invalid_payload")
    try:
        res = await ai_service.evaluate_answer(question=question, answer=answer, difficulty="medium", role="", time_taken_ms=time_taken)
        return res
    except Exception:
        raise HTTPException(status_code=503, detail="ai_evaluation_failed")