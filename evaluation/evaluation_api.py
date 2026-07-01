"""
Evaluation API - manual interview-round output capture and reports.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.database import get_db
from shared.db.models import Candidate, InterviewEvaluation, Job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class InterviewDataSubmit(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    session_id: str
    phase: str = "HR"
    content_score: Optional[float] = Field(default=None, ge=0, le=100)
    behavior_score: Optional[float] = Field(default=None, ge=0, le=100)
    final_score: float = Field(ge=0, le=100)
    interview_date: Optional[date] = None
    recommendation: Optional[str] = None
    recorded_interview_url: Optional[str] = None

    @field_validator("phase", "recommendation", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return value
        return str(value).strip().upper()


def _recommendation(final_score: float, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit.upper()
    val = final_score * 100.0 if final_score <= 1.0 else final_score
    if val >= 75:
        return "STRONG_HIRE"
    if val >= 60:
        return "HIRE"
    if val >= 45:
        return "HOLD"
    return "REJECT"


def _serialize_evaluation(
    evaluation: InterviewEvaluation,
    candidate: Optional[Candidate] = None,
    job: Optional[Job] = None,
) -> dict:
    raw_final = float(evaluation.final_score or 0)
    raw_content = evaluation.content_score
    raw_behavior = evaluation.behavior_score
    
    is_legacy = raw_final <= 1.0
    
    if is_legacy:
        final_score = round(raw_final * 100.0, 1)
        content_score = round(raw_content * 100.0, 1) if raw_content is not None else None
        behavior_score = round(raw_behavior * 100.0, 1) if raw_behavior is not None else None
    else:
        final_score = round(raw_final, 1)
        content_score = round(raw_content, 1) if raw_content is not None else None
        behavior_score = round(raw_behavior, 1) if raw_behavior is not None else None

    return {
        "id": evaluation.id,
        "candidate_id": evaluation.candidate_id,
        "candidate_name": candidate.name if candidate else "Unknown",
        "candidate_email": candidate.email if candidate else None,
        "job_id": evaluation.job_id or (candidate.job_id if candidate else None),
        "job_title": job.title if job else "Unknown Position",
        "session_id": evaluation.session_id,
        "phase": evaluation.phase,
        "content_score": content_score,
        "content_score_percent": content_score,
        "behavior_score": behavior_score,
        "behavior_score_percent": behavior_score,
        "final_score": final_score,
        "final_score_percent": final_score,
        "interview_date": evaluation.interview_date.isoformat() if evaluation.interview_date else None,
        "recommendation": evaluation.recommendation,
        "recorded_interview_url": evaluation.recorded_interview_url,
        "communication_score": evaluation.communication_score,
        "confidence_score": evaluation.confidence_score,
        "ai_recommendation": evaluation.ai_recommendation or evaluation.recommendation,
        "recruiter_decision": evaluation.recruiter_decision,
        "recruiter_notes": evaluation.recruiter_notes,
        "strengths": evaluation.strengths,
        "weaknesses": evaluation.weaknesses,
        "ai_generated_at": evaluation.ai_generated_at.isoformat() if evaluation.ai_generated_at else None,
        "recruiter_reviewed_at": evaluation.recruiter_reviewed_at.isoformat() if evaluation.recruiter_reviewed_at else None,
        "decision_finalized_at": evaluation.decision_finalized_at.isoformat() if evaluation.decision_finalized_at else None,
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        "updated_at": evaluation.updated_at.isoformat() if evaluation.updated_at else None,
    }


async def _candidate_and_job(
    db: AsyncSession,
    candidate_id: str,
    job_id: Optional[str] = None,
) -> tuple[Candidate, Optional[Job]]:
    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    effective_job_id = job_id or candidate.job_id
    job = None
    if effective_job_id:
        job_result = await db.execute(select(Job).where(Job.id == effective_job_id))
        job = job_result.scalar_one_or_none()
    return candidate, job


@router.post("/submit-interview")
async def submit_interview_evaluation(
    data: InterviewDataSubmit,
    db: AsyncSession = Depends(get_db),
):
    """Store one manually provided set of interview-round outputs."""
    candidate, job = await _candidate_and_job(db, data.candidate_id, data.job_id)

    evaluation = InterviewEvaluation(
        candidate_id=data.candidate_id,
        job_id=data.job_id or candidate.job_id,
        session_id=data.session_id,
        phase=data.phase,
        content_score=data.content_score,
        behavior_score=data.behavior_score,
        final_score=data.final_score,
        interview_date=data.interview_date,
        recommendation=_recommendation(data.final_score, data.recommendation),
        recorded_interview_url=data.recorded_interview_url,
    )

    db.add(evaluation)
    await db.flush()
    await db.refresh(evaluation)

    return {
        "success": True,
        "evaluation_id": evaluation.id,
        "evaluation": _serialize_evaluation(evaluation, candidate, job),
        "message": "Interview evaluation submitted successfully",
    }


@router.get("/results")
async def get_evaluation_results(
    candidate_id: Optional[str] = None,
    phase: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return evaluation records with candidate and job context."""
    query = select(InterviewEvaluation).order_by(desc(InterviewEvaluation.created_at)).limit(limit)
    if candidate_id:
        query = query.where(InterviewEvaluation.candidate_id == candidate_id)
    if phase:
        query = query.where(InterviewEvaluation.phase == phase.upper())

    result = await db.execute(query)
    evaluations = result.scalars().all()

    rows = []
    for evaluation in evaluations:
        candidate = None
        job = None
        try:
            candidate, job = await _candidate_and_job(db, evaluation.candidate_id, evaluation.job_id)
        except HTTPException:
            logger.warning("Evaluation %s references missing candidate %s", evaluation.id, evaluation.candidate_id)
        rows.append(_serialize_evaluation(evaluation, candidate, job))
    return rows


@router.get("/report/{evaluation_id}")
async def get_evaluation_report(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a JSON evaluation report for one submitted interview output set."""
    result = await db.execute(
        select(InterviewEvaluation).where(InterviewEvaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    candidate, job = await _candidate_and_job(db, evaluation.candidate_id, evaluation.job_id)
    payload = _serialize_evaluation(evaluation, candidate, job)
    return {
        "evaluation_id": evaluation.id,
        "candidate": {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
        },
        "job": {
            "id": job.id if job else payload["job_id"],
            "title": job.title if job else "Unknown Position",
            "description": job.description if job else None,
        },
        "interview_output": payload,
        "report": {
            "recommendation": evaluation.recommendation,
            "score_percent": payload["final_score_percent"],
            "risk_flags": [
                flag for flag in [
                    "Low final score" if (evaluation.final_score or 0) < 0.45 else None,
                ] if flag
            ],
        },
    }


class RecruiterOverrideSubmit(BaseModel):
    recruiter_decision: str
    recruiter_notes: str


@router.post("/override/{evaluation_id}")
async def submit_recruiter_override(
    evaluation_id: str,
    data: RecruiterOverrideSubmit,
    db: AsyncSession = Depends(get_db),
):
    """Store recruiter override decision and notes for a completed evaluation."""
    result = await db.execute(
        select(InterviewEvaluation).where(InterviewEvaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    import datetime
    evaluation.recruiter_decision = data.recruiter_decision.upper()
    evaluation.recruiter_notes = data.recruiter_notes
    evaluation.recruiter_reviewed_at = datetime.datetime.utcnow()
    evaluation.decision_finalized_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(evaluation)

    return {
        "success": True,
        "message": "Recruiter override recorded successfully",
        "evaluation_id": evaluation.id,
    }
