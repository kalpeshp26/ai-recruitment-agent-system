"""
Tests for Separate Recruiter & Candidate Prescreening Experience.
Covers: Session creation, reuse, expiration, duplicate submission, and results verification.
Run with: .venv/Scripts/python.exe -m pytest tests/test_prescreening_separation.py -v
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from shared.db.database import async_session
from shared.db.models import Candidate, Application, Job, ChatbotSession, ChatbotAnswer
from screening.workflow_service import update_candidate_stage, CandidateStage
from prescreening.prescreening_api import (
    get_session_by_candidate,
    get_session_details,
    get_session_results,
    submit_prescreening_answers_custom,
    SubmitAnswersRequest,
    AnswerSubmit
)
from fastapi import HTTPException
from sqlalchemy import select, delete

async def run_prescreening_separation_tests():
    async with async_session() as db:
        # 1. Setup job, candidate, application
        job = Job(title="QA Security Engineer", description="Cyber and Quality", status="active")
        db.add(job)
        await db.flush()
        
        cand = Candidate(name="Lifecycle Tester", job_id=job.id, status="new")
        db.add(cand)
        await db.flush()
        
        app = Application(candidate_id=cand.id, job_id=job.id, status="applied")
        db.add(app)
        await db.commit()
        
        session_id = None
        try:
            # 2. Test Automated Creation on pipeline transition
            updated_cand = await update_candidate_stage(db, cand.id, CandidateStage.PRESCREENING)
            assert updated_cand.status == "prescreening"
            
            # Fetch created session
            res = await db.execute(select(ChatbotSession).where(ChatbotSession.candidate_id == cand.id))
            session = res.scalar_one_or_none()
            assert session is not None
            assert session.status == "IN_PROGRESS"
            assert len(json.loads(session.questions)) == 6
            
            # Save session details for reference
            session_id = session.session_id
            
            # 3. Test Active Session Reuse (moving stage again shouldn't create new session)
            session.invitation_sent_at = datetime.utcnow() - timedelta(hours=1)
            await db.commit()
            
            # Transition again
            updated_cand2 = await update_candidate_stage(db, cand.id, CandidateStage.PRESCREENING)
            
            res2 = await db.execute(select(ChatbotSession).where(ChatbotSession.candidate_id == cand.id))
            sessions = res2.scalars().all()
            assert len(sessions) == 1
            assert sessions[0].session_id == session_id
            
            # 4. Test Recruiter Dashboard query endpoint (RESTful)
            recruiter_info = await get_session_by_candidate(cand.id, db)
            assert recruiter_info["success"] is True
            assert recruiter_info["session_id"] == session_id
            assert recruiter_info["answered_questions"] == 0
            
            # 5. Test Expiration Flow
            session.expires_at = datetime.utcnow() - timedelta(minutes=1)
            await db.commit()
            
            # Retrieving details now should flag it as EXPIRED
            portal_details = await get_session_details(session_id, db)
            assert portal_details["status"] == "EXPIRED"
            
            # Submitting answers to expired session should raise error (HTTP 400)
            req = SubmitAnswersRequest(
                session_id=session_id,
                answers=[AnswerSubmit(question_index=0, question="Why?", answer="Because it is expired and needs 20+ chars")]
            )
            with pytest.raises(HTTPException) as exc_info:
                await submit_prescreening_answers_custom(req, db)
            assert exc_info.value.status_code == 400
            assert "expired" in exc_info.value.detail.lower()
            
            # Restore expiry for completion test
            res_session = await db.execute(select(ChatbotSession).where(ChatbotSession.session_id == session_id))
            session = res_session.scalar_one_or_none()
            session.expires_at = datetime.utcnow() + timedelta(hours=10)
            session.status = "IN_PROGRESS"
            await db.commit()
            
            # 6. Test Successful Candidate submission
            req_valid = SubmitAnswersRequest(
                session_id=session_id,
                answers=[
                    AnswerSubmit(question_index=i, question=f"Q{i}", answer="This is a long response of 20+ characters to pass validations.")
                    for i in range(6)
                ]
            )
            resp = await submit_prescreening_answers_custom(req_valid, db)
            assert resp["success"] is True
            
            # 7. Test Duplicate submission prevention
            with pytest.raises(HTTPException) as exc_info_dup:
                await submit_prescreening_answers_custom(req_valid, db)
            assert exc_info_dup.value.status_code == 400
            assert "completed" in exc_info_dup.value.detail.lower()
            
            # 8. Test Recruiter results details scorecard endpoint
            results = await get_session_results(session_id, db)
            assert results["success"] is True
            assert results["status"] == "COMPLETED"
            assert len(results["answers"]) == 6
            assert "evaluation" in results
            
        finally:
            # Cleanup
            if session_id:
                await db.execute(delete(ChatbotAnswer).where(ChatbotAnswer.session_id == session_id))
                await db.execute(delete(ChatbotSession).where(ChatbotSession.session_id == session_id))
            await db.execute(delete(Application).where(Application.candidate_id == cand.id))
            await db.execute(delete(Candidate).where(Candidate.id == cand.id))
            await db.execute(delete(Job).where(Job.id == job.id))
            await db.commit()

def test_prescreening_separation():
    """Sync wrapper to execute prescreening separation tests."""
    asyncio.run(run_prescreening_separation_tests())
