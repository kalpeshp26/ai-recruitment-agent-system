"""
Onboarding API Router - Stage 9
Handles task management, document collection, BGV, and IT provisioning.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime

router = APIRouter(tags=["Stage 9: Onboarding"])


class OnboardingCreateRequest(BaseModel):
    candidate_id: str
    offer_id: str
    joining_date: str
    job_id: Optional[str] = None


class OnboardingFromInterviewRequest(BaseModel):
    candidate_id: str
    job_id: str
    joining_date: str


class TaskCompleteRequest(BaseModel):
    task_id: str


class DocumentSubmitRequest(BaseModel):
    onboarding_id: str
    doc_type: str
    file_path: str


@router.post("/onboarding/create")
async def create_onboarding(req: OnboardingCreateRequest):
    """Create onboarding record and AI-generated task checklist."""
    from onboarding.document_collector import create_onboarding_record
    from onboarding.onboarding_task_manager import create_task_checklist
    
    try:
        onboarding_id = create_onboarding_record(req.candidate_id, req.offer_id)
        task_count = create_task_checklist(
            onboarding_id, req.candidate_id, req.joining_date, req.offer_id, req.job_id
        )
        
        return {
            "success": True,
            "onboarding_id": onboarding_id,
            "tasks_created": task_count,
            "message": "Onboarding created successfully with AI-generated tasks"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding/list")
async def list_onboarding():
    """List all onboarding records."""
    from config import DATABASE_URL
    
    try:
        db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT ob.id, ob.candidate_id, ob.offer_id, ob.status,
                   ob.created_at, c.name as candidate_name,
                   j.title as job_title
            FROM onboarding ob
            LEFT JOIN candidates c ON c.id = ob.candidate_id
            LEFT JOIN offers o ON o.id = ob.offer_id
            LEFT JOIN applications a ON a.id = o.application_id
            LEFT JOIN jobs j ON j.id = a.job_id
            ORDER BY ob.created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append({
                "id": row[0],
                "candidate_id": row[1],
                "offer_id": row[2],
                "status": row[3],
                "created_at": row[4],
                "candidate_name": row[5],
                "job_title": row[6]
            })
        
        return {"success": True, "onboarding": records}
    except sqlite3.OperationalError:
        return {"success": True, "onboarding": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding/{onboarding_id}/tasks")
async def get_tasks(onboarding_id: str):
    """Get tasks for an onboarding record."""
    from onboarding.onboarding_task_manager import get_pending_tasks
    
    try:
        tasks = get_pending_tasks(onboarding_id)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/task/complete")
async def complete_task(req: TaskCompleteRequest):
    """Mark a task as complete."""
    from onboarding.onboarding_task_manager import mark_task_complete
    
    try:
        mark_task_complete(req.task_id)
        return {
            "success": True,
            "message": f"Task {req.task_id} marked as complete"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/document/submit")
async def submit_document(req: DocumentSubmitRequest):
    """Mark a document as submitted."""
    from onboarding.document_collector import mark_document_submitted
    
    try:
        mark_document_submitted(req.onboarding_id, req.doc_type, req.file_path)
        return {
            "success": True,
            "message": f"Document {req.doc_type} submitted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/{onboarding_id}/bgv")
async def trigger_bgv(onboarding_id: str):
    """Trigger background verification."""
    from onboarding.bgv_trigger import trigger_bgv as start_bgv
    
    try:
        result = start_bgv(onboarding_id)
        return {
            "success": True,
            "message": "BGV triggered successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/{onboarding_id}/provision")
async def provision_it(onboarding_id: str):
    """Provision IT resources."""
    from onboarding.it_provisioner import provision_it_resources
    
    try:
        result = provision_it_resources(onboarding_id)
        return {
            "success": True,
            "message": "IT resources provisioned",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/from-interview")
async def create_onboarding_from_interview(req: OnboardingFromInterviewRequest):
    """Create onboarding for a candidate who passed their interview with AI-generated tasks."""
    candidate_id = req.candidate_id
    job_id = req.job_id
    joining_date = req.joining_date
    from onboarding.document_collector import create_onboarding_record
    from onboarding.onboarding_task_manager import create_task_checklist
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job, Application, Offer
    from sqlalchemy import select
    import uuid
    
    try:
        with db_session() as db:
            # Get candidate details
            candidate = db.execute(
                select(Candidate).where(Candidate.id == candidate_id).limit(1)
            ).scalar_one_or_none()
            
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            
            # Get job details
            job = db.execute(
                select(Job).where(Job.id == job_id).limit(1)
            ).scalar_one_or_none()
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Get or create application
            application = db.execute(
                select(Application).where(
                    Application.candidate_id == candidate_id,
                    Application.job_id == job_id
                ).limit(1)
            ).scalar_one_or_none()
            
            if not application:
                # Create application if it doesn't exist
                application = Application(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    status="HIRED",
                    applied_at=datetime.now()
                )
                db.add(application)
                db.flush()
            
            candidate_name = candidate.name
            job_title = job.title
            
            # Create offer record
            offer_id = f"offer_{uuid.uuid4().hex[:8]}"
            offer = Offer(
                id=offer_id,
                application_id=application.id,
                salary_offered=job.salary_min if job.salary_min else 0,
                currency=job.currency if job.currency else "INR",
                status="accepted",
                offered_at=datetime.now(),
                accepted_at=datetime.now()
            )
            db.add(offer)
            db.flush()
            db.commit()
        
        # Create onboarding record with AI-generated tasks
        onboarding_id = create_onboarding_record(candidate_id, offer_id)
        task_count = create_task_checklist(
            onboarding_id, candidate_id, joining_date, offer_id, job_id
        )
        
        return {
            "success": True,
            "onboarding_id": onboarding_id,
            "offer_id": offer_id,
            "tasks_created": task_count,
            "candidate_name": candidate_name,
            "job_title": job_title,
            "message": "Onboarding created successfully with AI-generated tasks from interview"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/onboarding/clear-mock")
async def clear_mock_onboardings():
    """Clear all mock onboarding records and their associated tasks."""
    from config import DATABASE_URL
    
    try:
        db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Delete all onboarding tasks first (foreign key dependency)
        cur.execute("DELETE FROM onboarding_tasks")
        tasks_deleted = cur.rowcount
        
        # Delete all onboarding records
        cur.execute("DELETE FROM onboarding")
        onboarding_deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "onboarding_deleted": onboarding_deleted,
            "tasks_deleted": tasks_deleted,
            "message": f"Cleared {onboarding_deleted} onboarding records and {tasks_deleted} tasks"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
