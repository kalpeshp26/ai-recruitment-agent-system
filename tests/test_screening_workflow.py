"""
Tests for Candidate Pipeline Stage and Workflow Management.
Run with: .venv/Scripts/python.exe -m pytest tests/test_screening_workflow.py -v
"""
import pytest
import asyncio
from shared.db.database import async_session
from shared.db.models import Candidate, Application, Job
from screening.workflow_service import update_candidate_stage, CandidateStage
from fastapi import HTTPException

async def run_workflow_transitions_async():
    """Verify that allowed stage transitions succeed and invalid ones fail."""
    async with async_session() as db:
        # Create a sample job
        job = Job(title="Workflow test", status="active")
        db.add(job)
        await db.flush()
        
        # Create a candidate
        candidate = Candidate(
            name="Workflow Candidate",
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
        
        try:
            # 1. Transition: new -> prescreening (Should succeed)
            cand = await update_candidate_stage(db, candidate_id, CandidateStage.PRESCREENING)
            assert cand.status == "prescreening"
            
            # Verify application mapping
            await db.refresh(application)
            assert application.status == "SHORTLISTED"
            
            # 2. Transition: prescreening -> new (Should fail)
            with pytest.raises(HTTPException) as exc_info:
                await update_candidate_stage(db, candidate_id, CandidateStage.NEW)
            assert exc_info.value.status_code == 400
            assert "Transition from 'prescreening' to 'new' is not allowed" in exc_info.value.detail
            
            # 3. Transition: prescreening -> interview (Should succeed)
            cand = await update_candidate_stage(db, candidate_id, CandidateStage.INTERVIEW)
            assert cand.status == "interview"
            await db.refresh(application)
            assert application.status == "INTERVIEW_PENDING"
            
            # 4. Transition: interview -> rejected (Should succeed)
            cand = await update_candidate_stage(db, candidate_id, CandidateStage.REJECTED)
            assert cand.status == "rejected"
            await db.refresh(application)
            assert application.status == "REJECTED"
            
            # 5. Transition: rejected -> interview (Re-opening - should succeed)
            cand = await update_candidate_stage(db, candidate_id, CandidateStage.INTERVIEW)
            assert cand.status == "interview"
            await db.refresh(application)
            assert application.status == "INTERVIEW_PENDING"

        finally:
            # Cleanup
            await db.delete(application)
            await db.delete(cand)
            await db.delete(job)
            await db.commit()

def test_workflow_transitions():
    """Sync wrapper to execute async test using asyncio.run."""
    asyncio.run(run_workflow_transitions_async())
