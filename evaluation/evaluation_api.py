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
    content_score: Optional[float] = Field(default=None, ge=0, le=1)
    behavior_score: Optional[float] = Field(default=None, ge=0, le=1)
    final_score: float = Field(ge=0, le=1)
    interview_date: Optional[date] = None
    recommendation: Optional[str] = None

    @field_validator("phase", "recommendation", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        if value is None:
            return value
        return str(value).strip().upper()


def _score_percent(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value) * 100, 1)


def _recommendation(final_score: float, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit.upper()
    if final_score >= 0.75:
        return "STRONG_HIRE"
    if final_score >= 0.6:
        return "HIRE"
    if final_score >= 0.45:
        return "HOLD"
    return "REJECT"


def _serialize_evaluation(
    evaluation: InterviewEvaluation,
    candidate: Optional[Candidate] = None,
    job: Optional[Job] = None,
) -> dict:
    final_score = float(evaluation.final_score or 0)
    return {
        "id": evaluation.id,
        "candidate_id": evaluation.candidate_id,
        "candidate_name": candidate.name if candidate else "Unknown",
        "candidate_email": candidate.email if candidate else None,
        "job_id": evaluation.job_id or (candidate.job_id if candidate else None),
        "job_title": job.title if job else "Unknown Position",
        "session_id": evaluation.session_id,
        "phase": evaluation.phase,
        "content_score": evaluation.content_score,
        "content_score_percent": _score_percent(evaluation.content_score),
        "behavior_score": evaluation.behavior_score,
        "behavior_score_percent": _score_percent(evaluation.behavior_score),
        "final_score": final_score,
        "final_score_percent": _score_percent(final_score),
        "interview_date": evaluation.interview_date.isoformat() if evaluation.interview_date else None,
        "recommendation": evaluation.recommendation,
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
