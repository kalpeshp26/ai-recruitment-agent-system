"""
--- FILE: backend/services/interview_service.py ---

Interview service layer: session lifecycle, state transitions, and final scoring.
All DB operations are async and use SQLAlchemy AsyncSession.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    InterviewEvaluation,
    ProctoringViolation,
)

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


ACTIVE_STATES = {"INITIALIZING", "PERMISSION_CHECK", "READY", "QUESTION_ASKED", "RECORDING", "PROCESSING", "EVALUATING", "NEXT_QUESTION"}

VALID_TRANSITIONS = {
    "IDLE": ["INITIALIZING"],
    "INITIALIZING": ["PERMISSION_CHECK"],
    "PERMISSION_CHECK": ["READY"],
    "READY": ["QUESTION_ASKED"],
    "QUESTION_ASKED": ["RECORDING", "PROCESSING"],
    "RECORDING": ["PROCESSING"],
    "PROCESSING": ["EVALUATING"],
    "EVALUATING": ["NEXT_QUESTION"],
    "NEXT_QUESTION": ["QUESTION_ASKED"],
    # Terminal transitions handled separately
}


async def start_or_resume_session(db: AsyncSession, user_id: str, role: str, answer_mode: str = "voice") -> InterviewSession:
    """Idempotent start: return existing active session or create a new one.

    - If an active session exists for the user, return it.
    - Otherwise create a new InterviewSession with status INITIALIZING,
      set start_time and session_token, then transition to READY.
    """
    q = select(InterviewSession).where(InterviewSession.user_id == user_id, InterviewSession.status.in_(list(ACTIVE_STATES)))
    res = await db.execute(q)
    existing = res.scalars().first()
    if existing:
        return existing

    now_iso = datetime.now(timezone.utc).isoformat()
    session_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    session = InterviewSession(
        id=session_id,
        user_id=user_id,
        role=role,
        start_time=now_iso,
        status="INITIALIZING",
        answer_mode=answer_mode,
        current_question_index=0,
        session_token=token,
        last_activity_at=now_iso,
    )
    db.add(session)
    await db.flush()

    # Transition to PERMISSION_CHECK then READY per state machine
    session.status = "PERMISSION_CHECK"
    session.last_activity_at = datetime.now(timezone.utc).isoformat()
    await db.flush()

    session.status = "READY"
    session.last_activity_at = datetime.now(timezone.utc).isoformat()
    await db.flush()

    return session


async def get_session_status(db: AsyncSession, session_id: str) -> Dict[str, Any]:
    """Return live session metadata for the frontend.

    Response includes: status, current_question_index, warning_count,
    time_remaining_seconds, answer_mode
    """
    q = select(InterviewSession).where(InterviewSession.id == session_id)
    res = await db.execute(q)
    session = res.scalars().first()
    if not session:
        raise KeyError("session_not_found")

    # compute time elapsed for the API contract
    try:
        start = datetime.fromisoformat(session.start_time)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        elapsed_seconds = max(0, int(elapsed))
    except Exception:
        elapsed_seconds = 0

    return {
        "session_id": session.id,
        "status": session.status,
        "current_question_index": session.current_question_index,
        "answer_mode": session.answer_mode,
        "warning_count": session.warning_count,
        "time_elapsed_seconds": elapsed_seconds,
    }


async def transition_state(db: AsyncSession, session: InterviewSession, new_state: str) -> None:
    """Validate and perform a state transition for a session.

    Raises InvalidTransitionError on invalid transitions.
    """
    cur = session.status
    if cur == new_state:
        # idempotent
        return

    # Terminal transitions allowed from any state
    if new_state in ("TERMINATED", "COMPLETED"):
        session.status = new_state
        session.last_activity_at = datetime.now(timezone.utc).isoformat()
        await db.flush()
        return

    allowed = VALID_TRANSITIONS.get(cur) or []
    if new_state not in allowed:
        raise InvalidTransitionError(f"Invalid transition: {cur} -> {new_state}")

    session.status = new_state
    session.last_activity_at = datetime.now(timezone.utc).isoformat()
    await db.flush()


async def calculate_final_score(db: AsyncSession, session_id: str) -> Dict[str, Any]:
    """Compute final aggregated scores, apply penalties, persist InterviewEvaluation, and return the scorecard."""
    # Fetch answers for the session by joining questions
    q = (
        select(InterviewAnswer)
        .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.session_id == session_id)
    )
    res = await db.execute(q)
    answers = res.scalars().all()

    # If no answers, default averages to 0
    if not answers:
        avg_tech = avg_comm = avg_conf = avg_ps = 0.0
        answered_count = 0
    else:
        answered_count = len(answers)
        techs = [a.scores.get("technical", 0.0) for a in answers]
        comms = [a.scores.get("communication", 0.0) for a in answers]
        confs = [a.scores.get("confidence", 0.0) for a in answers]
        pss = [a.scores.get("problem_solving", 0.0) for a in answers]
        avg_tech = sum(techs) / answered_count
        avg_comm = sum(comms) / answered_count
        avg_conf = sum(confs) / answered_count
        avg_ps = sum(pss) / answered_count

    # aggregate total 0-10
    aggregate_total = (
        avg_tech * settings.SCORE_WEIGHT_TECHNICAL
        + avg_comm * settings.SCORE_WEIGHT_COMMUNICATION
        + avg_conf * settings.SCORE_WEIGHT_CONFIDENCE
        + avg_ps * settings.SCORE_WEIGHT_PROBLEM_SOLVING
    )
    final_raw_score = aggregate_total * 10.0

    # penalties: warnings and skips
    # count warnings
    wq = select(func.count(ProctoringViolation.id)).where(ProctoringViolation.session_id == session_id)
    warn_res = await db.execute(wq)
    warnings = int(warn_res.scalar() or 0)

    # count skips
    # join answers where is_skipped true and their questions point to session
    skipped_q = (
        select(func.count(InterviewAnswer.id))
        .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.session_id == session_id, InterviewAnswer.is_skipped == True)
    )
    skip_res = await db.execute(skipped_q)
    skips = int(skip_res.scalar() or 0)

    penalty_points = warnings * settings.PENALTY_PER_WARNING + skips * 1

    final_score = final_raw_score - penalty_points
    final_score = max(0.0, min(100.0, final_score))

    # grade mapping
    if final_score >= 90:
        grade = "A"
    elif final_score >= 80:
        grade = "B"
    elif final_score >= 70:
        grade = "C"
    elif final_score >= 60:
        grade = "D"
    else:
        grade = "F"

    # persist evaluation
    existing_eval_q = select(InterviewEvaluation).where(InterviewEvaluation.session_id == session_id)
    existing_eval_res = await db.execute(existing_eval_q)
    evaluation = existing_eval_res.scalar_one_or_none()
    if evaluation is None:
        eval_id = str(uuid.uuid4())
        evaluation = InterviewEvaluation(
            id=eval_id,
            session_id=session_id,
            technical_score=round(avg_tech * 10, 2),
            communication_score=round(avg_comm * 10, 2),
            confidence_score=round(avg_conf * 10, 2),
            problem_solving_score=round(avg_ps * 10, 2),
            total_score=round(final_raw_score, 2),
            penalty_points=penalty_points,
            final_score=round(final_score, 2),
            summary="",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(evaluation)
    else:
        eval_id = evaluation.id
        evaluation.technical_score = round(avg_tech * 10, 2)
        evaluation.communication_score = round(avg_comm * 10, 2)
        evaluation.confidence_score = round(avg_conf * 10, 2)
        evaluation.problem_solving_score = round(avg_ps * 10, 2)
        evaluation.total_score = round(final_raw_score, 2)
        evaluation.penalty_points = penalty_points
        evaluation.final_score = round(final_score, 2)
        evaluation.summary = evaluation.summary or ""
    await db.flush()
    # Ensure evaluation is committed so other DB sessions can read it
    try:
        await db.commit()
    except Exception:
        # If commit fails, rollback to keep session clean and re-raise
        await db.rollback()
        raise

    return {
        "evaluation_id": eval_id,
        "technical_score": evaluation.technical_score,
        "communication_score": evaluation.communication_score,
        "confidence_score": evaluation.confidence_score,
        "problem_solving_score": evaluation.problem_solving_score,
        "penalty_points": penalty_points,
        "final_score": evaluation.final_score,
        "grade": grade,
        "answered_count": answered_count,
    }


__all__ = ["start_or_resume_session", "get_session_status", "transition_state", "calculate_final_score", "InvalidTransitionError"]
