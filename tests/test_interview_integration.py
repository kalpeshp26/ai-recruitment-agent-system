"""
Integration tests for the Multi-Round Assessment Interview Module.
Run with: .venv/Scripts/python.exe -m pytest tests/test_interview_integration.py -v
"""
import pytest
import asyncio
import uuid
from shared.db.database import async_session
from shared.db.models import Candidate, Application, Job, InterviewEvaluation
from screening.workflow_service import update_candidate_stage, CandidateStage
from interview.session_manager import process_interview_completed_event
from fastapi import HTTPException

async def run_interview_integration_async():
    """Verify that moving a candidate to the Interview stage creates a session, and completing syncs results."""
    async with async_session() as db:
        # Create a sample job
        job = Job(title="Integration Engineer", status="active")
        db.add(job)
        await db.flush()
        
        # Create a candidate
        candidate = Candidate(
            name="Interview Candidate",
            email="candidate.interview@example.com",
            job_id=job.id,
            status="new"
        )
        db.add(candidate)
        await db.flush()
        
        # Create application
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status="applied"
        )
        db.add(application)
        await db.commit()
        
        candidate_id = candidate.id
        job_id = job.id
        
        try:
            # 1. Transition: new -> interview (Auto-triggers session creation & mock email dispatch)
            cand = await update_candidate_stage(db, candidate_id, CandidateStage.INTERVIEW)
            assert cand.status == "interview"
            
            # Verify Application status became INTERVIEW_PENDING
            await db.refresh(application)
            assert application.status == "INTERVIEW_PENDING"
            
            # Verify interview session was added to database
            from sqlalchemy import text
            session_row = (await db.execute(text(
                "SELECT session_id, interview_status FROM interview_sessions WHERE candidate_id = :cid AND job_id = :jid"
            ), {"cid": candidate_id, "jid": job_id})).fetchone()
            
            assert session_row is not None
            session_id = session_row[0]
            assert session_row[1] in ["SENT", "FAILED", "PENDING"] # Can be any of these based on mock configs
            
            # 2. Simulate candidate completing interview and firing interview.completed event payload
            payload = {
                "interview_id": session_id,
                "candidate_id": candidate_id,
                "job_id": job_id,
                "overall_score": 0.85,
                "content_score": 0.90,
                "behavior_score": 0.80,
                "recommendation": "strong_hire",
                "completed_at": "2026-06-28T12:00:00Z"
            }
            
            # Run the process_interview_completed_event subscriber
            await process_interview_completed_event(payload)
            
            # Verify application status transitioned to INTERVIEW_COMPLETED
            await db.refresh(application)
            assert application.status == "INTERVIEW_COMPLETED"
            
            # Verify InterviewEvaluation was saved
            eval_res = (await db.execute(text(
                "SELECT final_score, recommendation, evaluator_notes FROM interview_evaluations WHERE session_id = :sid"
            ), {"sid": session_id})).fetchone()
            
            assert eval_res is not None
            assert float(eval_res[0]) == 85.0
            assert eval_res[1] == "STRONG_HIRE"
            assert "AI automated interview" in eval_res[2]
            
            # 3. Verify IDEMPOTENCY: run process_interview_completed_event again (retry)
            # Change the overall score in the retried payload to ensure it updates instead of duplicating
            payload["overall_score"] = 0.92
            payload["recommendation"] = "strong_hire"
            
            await process_interview_completed_event(payload)
            
            # Verify same application status
            await db.refresh(application)
            assert application.status == "INTERVIEW_COMPLETED"
            
            # Verify evaluation row updated score and didn't insert a duplicate row
            eval_rows = (await db.execute(text(
                "SELECT final_score, recommendation FROM interview_evaluations WHERE session_id = :sid"
            ), {"sid": session_id})).fetchall()
            
            assert len(eval_rows) == 1
            assert float(eval_rows[0][0]) == 92.0

            # 4. Verify Recruiter Override and Advisory Preservation
            eval_record_row = (await db.execute(text(
                "SELECT id, recruiter_decision, recruiter_notes, ai_recommendation, final_score FROM interview_evaluations WHERE session_id = :sid"
            ), {"sid": session_id})).fetchone()
            
            assert eval_record_row is not None
            eval_id = eval_record_row[0]
            
            # Simulate override update via DB write
            await db.execute(text("""
                UPDATE interview_evaluations
                SET recruiter_decision = 'HIRE', recruiter_notes = 'Override AI reject recommendation based on portfolio review'
                WHERE id = :eval_id
            """), {"eval_id": eval_id})
            await db.commit()
            
            # Re-fetch and check separation of AI vs Recruiter decision fields
            updated_row = (await db.execute(text(
                "SELECT recruiter_decision, recruiter_notes, ai_recommendation, final_score FROM interview_evaluations WHERE id = :eval_id"
            ), {"eval_id": eval_id})).fetchone()
            
            assert updated_row[0] == "HIRE"
            assert updated_row[1] == "Override AI reject recommendation based on portfolio review"
            assert updated_row[2] == "STRONG_HIRE" # Immutable AI recommendation preserved
            assert float(updated_row[3]) == 92.0 # Immutable AI final score preserved

        finally:
            # Cleanup
            await db.delete(application)
            await db.delete(cand)
            await db.delete(job)
            await db.execute(text("DELETE FROM interview_sessions WHERE candidate_id = :cid"), {"cid": candidate_id})
            await db.execute(text("DELETE FROM interview_evaluations WHERE candidate_id = :cid"), {"cid": candidate_id})
            await db.commit()

def test_interview_integration():
    """Sync wrapper to execute async test using asyncio.run."""
    asyncio.run(run_interview_integration_async())
