"""
interview/interview_api.py
Interview session management API endpoints for Stage 6
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["Stage 6: Interview"])


@router.get("/sessions")
async def list_interview_sessions(job_id: Optional[str] = None):
    """List all interview sessions with candidate details - includes candidates who passed prescreening."""
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job, Application, ChatbotSession
    from sqlalchemy import text, select
    import json

    try:
        with db_session() as db:
            sessions_dict = {}  # Use dict to deduplicate by candidate_id + job_id

            # First, get interview sessions from the interview_sessions table
            try:
                if job_id:
                    query = text("""
                        SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                               i.invited_at, i.started_at, i.completed_at,
                               c.name as candidate_name, c.email as candidate_email,
                               j.title as job_title,
                               e.final_score, e.content_score, e.behavior_score, e.recommendation, e.evaluator_notes
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        LEFT JOIN interview_evaluations e ON e.session_id = i.session_id
                        WHERE i.job_id = :job_id
                        ORDER BY i.invited_at DESC
                    """)
                    results = db.execute(query, {"job_id": job_id}).fetchall()
                else:
                    query = text("""
                        SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                               i.invited_at, i.started_at, i.completed_at,
                               c.name as candidate_name, c.email as candidate_email,
                               j.title as job_title,
                               e.final_score, e.content_score, e.behavior_score, e.recommendation, e.evaluator_notes
                        FROM interview_sessions i
                        LEFT JOIN candidates c ON c.id = i.candidate_id
                        LEFT JOIN jobs j ON j.id = i.job_id
                        LEFT JOIN interview_evaluations e ON e.session_id = i.session_id
                        ORDER BY i.invited_at DESC
                    """)
                    results = db.execute(query).fetchall()

                for row in results:
                    key = f"{row[1]}_{row[2]}"  # candidate_id_job_id
                    sessions_dict[key] = {
                        "session_id": row[0],
                        "candidate_id": row[1],
                        "job_id": row[2],
                        "status": row[3] or "PENDING",
                        "invited_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
                        "started_at": row[5].isoformat() if hasattr(row[5], "isoformat") else row[5],
                        "completed_at": row[6].isoformat() if hasattr(row[6], "isoformat") else row[6],
                        "candidate_name": row[7],
                        "candidate_email": row[8],
                        "job_title": row[9],
                        "final_score": row[10],
                        "technical_score": row[11],
                        "communication_score": row[12],
                        "recommendation": row[13],
                        "summary": row[14]
                    }

                logger.info(f"Retrieved {len(sessions_dict)} interview sessions from interview_sessions table")
            except Exception as table_error:
                logger.warning(f"interview_sessions table query failed: {table_error}")

            # Second, get candidates who completed prescreening from Application table
            # This ensures all candidates with status DONE, PRESCREENED, or INTERVIEW_PENDING are included
            query = select(Application).where(
                Application.status.in_(["DONE", "PRESCREENED", "INTERVIEW_PENDING"])
            ).order_by(Application.updated_at.desc())

            if job_id:
                query = query.where(Application.job_id == job_id)

            result = db.execute(query)
            applications = result.scalars().all()

            for app in applications:
                key = f"{app.candidate_id}_{app.job_id}"
                
                # Only add if not already in sessions_dict (interview_sessions takes precedence)
                if key not in sessions_dict:
                    # Get candidate details
                    candidate = db.execute(
                        select(Candidate).where(Candidate.id == app.candidate_id).limit(1)
                    )
                    cand = candidate.scalar_one_or_none()

                    # Get job details
                    job = db.execute(
                        select(Job).where(Job.id == app.job_id).limit(1)
                    )
                    job_obj = job.scalar_one_or_none()

                    # Generate a session ID based on application
                    session_id = f"prescreen_{app.candidate_id[:8]}_{app.job_id[:8]}"

                    sessions_dict[key] = {
                        "session_id": session_id,
                        "candidate_id": app.candidate_id,
                        "job_id": app.job_id,
                        "status": "PENDING",
                        "invited_at": app.updated_at.isoformat() if app.updated_at else None,
                        "started_at": None,
                        "completed_at": None,
                        "candidate_name": cand.name if cand else "Unknown",
                        "candidate_email": cand.email if cand else None,
                        "job_title": job_obj.title if job_obj else "Unknown",
                        "final_score": None
                    }

            # Third, get candidates from chatbot_sessions with PASS/BORDERLINE verdicts
            # This is a fallback for candidates whose application status might not be updated
            query = select(ChatbotSession).where(
                ChatbotSession.status == "COMPLETED"
            ).order_by(ChatbotSession.created_at.desc())

            if job_id:
                query = query.where(ChatbotSession.job_id == job_id)

            result = db.execute(query)
            chatbot_sessions = result.scalars().all()

            for session in chatbot_sessions:
                key = f"{session.candidate_id}_{session.job_id}"
                
                # Only add if not already in sessions_dict
                if key not in sessions_dict:
                    # Check if the session has a PASS or BORDERLINE verdict in summary
                    try:
                        if session.summary:
                            summary_data = json.loads(session.summary) if isinstance(session.summary, str) else session.summary
                            verdict = summary_data.get("verdict") if isinstance(summary_data, dict) else None
                            
                            # Only include if verdict is PASS or BORDERLINE
                            if verdict in ["PASS", "BORDERLINE"]:
                                # Get candidate details
                                candidate = db.execute(
                                    select(Candidate).where(Candidate.id == session.candidate_id).limit(1)
                                )
                                cand = candidate.scalar_one_or_none()

                                # Get job details
                                job = db.execute(
                                    select(Job).where(Job.id == session.job_id).limit(1)
                                )
                                job_obj = job.scalar_one_or_none()

                                sessions_dict[key] = {
                                    "session_id": session.session_id,
                                    "candidate_id": session.candidate_id,
                                    "job_id": session.job_id,
                                    "status": "PENDING",
                                    "invited_at": session.created_at.isoformat() if session.created_at else None,
                                    "started_at": None,
                                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                                    "candidate_name": cand.name if cand else "Unknown",
                                    "candidate_email": cand.email if cand else None,
                                    "job_title": job_obj.title if job_obj else "Unknown",
                                    "final_score": None
                                }
                    except Exception as json_error:
                        logger.warning(f"Failed to parse summary for session {session.session_id}: {json_error}")

            logger.info(f"Total sessions (including prescreening): {len(sessions_dict)}")
            return {"success": True, "sessions": list(sessions_dict.values())}

    except Exception as e:
        logger.error(f"Failed to list interview sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resend/{session_id}")
async def resend_interview_email(session_id: str):
    """Resend interview invitation email to candidate."""
    from interview.session_manager import get_interview_session
    from interview.interview_email_sender import send_interview_invitation_email
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job
    from datetime import datetime, timedelta
    import os
    
    try:
        # Get session details
        session = get_interview_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Get candidate and job details
        with db_session() as db:
            candidate = db.query(Candidate).filter_by(id=session['candidate_id']).first()
            job = db.query(Job).filter_by(id=session['job_id']).first()
            
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Generate interview URL
            interview_base_url = os.getenv("INTERVIEW_BASE_URL", "http://localhost:5173")
            interview_url = f"{interview_base_url}/interview/session/{session_id}"
            
            # Calculate new deadline
            deadline = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
            
            # Send email
            email_sent = send_interview_invitation_email(
                candidate_email=candidate.email,
                candidate_name=candidate.name,
                job_title=job.title,
                interview_url=interview_url,
                completion_deadline=deadline,
                session_id=session_id
            )
            
            if email_sent:
                logger.info(f"Interview email resent successfully for session {session_id}")
                return {
                    "success": True,
                    "message": f"Interview email resent to {candidate.email}",
                    "session_id": session_id
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to send email")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend interview email for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_interview_stats(job_id: Optional[str] = None):
    """Get interview statistics."""
    from shared.db.database import db_session
    from sqlalchemy import text
    
    try:
        with db_session() as db:
            if job_id:
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN interview_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN interview_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN interview_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN interview_status = 'EXPIRED' THEN 1 ELSE 0 END) as expired
                    FROM interview_sessions
                    WHERE job_id = :job_id
                """)
                result = db.execute(query, {"job_id": job_id}).fetchone()
            else:
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN interview_status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN interview_status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN interview_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN interview_status = 'EXPIRED' THEN 1 ELSE 0 END) as expired
                    FROM interview_sessions
                """)
                result = db.execute(query).fetchone()
            
            return {
                "success": True,
                "stats": {
                    "total": result[0] or 0,
                    "pending": result[1] or 0,
                    "in_progress": result[2] or 0,
                    "completed": result[3] or 0,
                    "expired": result[4] or 0
                }
            }
    except Exception as e:
        logger.error(f"Failed to get interview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/session/{interview_id}/terminate")
async def terminate_interview(interview_id: int, request: dict):
    """Terminate interview session early and save partial results."""
    from shared.db.database import db_session
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        session_id = request.get('session_id')
        
        with db_session() as db:
            # Update interview session status
            query = text("""
                UPDATE interview_sessions
                SET interview_status = 'TERMINATED',
                    completed_at = :completed_at
                WHERE session_id = :session_id
            """)
            db.execute(query, {
                "session_id": session_id,
                "completed_at": datetime.now().isoformat()
            })
            db.commit()
            
            logger.info(f"Interview {interview_id} (session {session_id}) terminated by candidate")
            
            return {
                "success": True,
                "message": "Interview terminated. Progress saved.",
                "interview_id": interview_id,
                "session_id": session_id
            }
            
    except Exception as e:
        logger.error(f"Failed to terminate interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/validate/{session_id}")
async def validate_interview_session(session_id: str):
    """Validate that an interview session is active and return associated candidate/job details."""
    from interview.session_manager import get_interview_session
    try:
        session = get_interview_session(session_id)
        if session:
            status = session.get("status") or "PENDING"
            
            # Check if completed/expired/terminated
            if status in ["COMPLETED", "TERMINATED", "EXPIRED", "completed", "terminated", "expired"]:
                return {
                    "success": True,
                    "valid": False,
                    "message": f"Interview session is already {status.lower()}"
                }
                
            return {
                "success": True,
                "valid": True,
                "session_id": session["session_id"],
                "candidate_id": session["candidate_id"],
                "job_id": session["job_id"],
                "status": status,
                "message": "Session is valid"
            }
        else:
            return {
                "success": True,
                "valid": False,
                "message": "Invalid or expired session ID"
            }
    except Exception as e:
        logger.error(f"Failed to validate interview session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/completed-candidates")
async def get_completed_candidates():
    """Get candidates who completed interviews or have HIRE/STRONG_HIRE evaluations."""
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job, InterviewEvaluation, Application
    from sqlalchemy import text, select

    try:
        with db_session() as db:
            candidates_dict = {}  # deduplicate by candidate_id + job_id

            # ── 1. interview_sessions table (raw SQL – no ORM model needed) ──
            try:
                query = text("""
                    SELECT i.session_id, i.candidate_id, i.job_id, i.interview_status,
                           i.completed_at,
                           c.name  AS candidate_name,
                           c.email AS candidate_email,
                           j.title AS job_title
                    FROM   interview_sessions i
                    LEFT JOIN candidates c ON c.id = i.candidate_id
                    LEFT JOIN jobs       j ON j.id = i.job_id
                    WHERE  UPPER(COALESCE(i.interview_status,'')) = 'COMPLETED'
                    ORDER  BY i.completed_at DESC
                """)
                for row in db.execute(query).fetchall():
                    key = f"{row[1]}_{row[2]}"
                    candidates_dict[key] = {
                        "session_id":      row[0],
                        "candidate_id":    row[1],
                        "job_id":          row[2],
                        "status":          row[3],
                        "completed_at":    row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
                        "candidate_name":  row[5],
                        "candidate_email": row[6],
                        "job_title":       row[7],
                    }
                logger.info(f"interview_sessions: {len(candidates_dict)} candidates")
            except Exception as e:
                logger.warning(f"interview_sessions query failed: {e}")

            # ── 2. InterviewEvaluation with HIRE / STRONG_HIRE ────────────────
            try:
                evals = db.execute(
                    select(InterviewEvaluation)
                    .where(InterviewEvaluation.recommendation.in_(["HIRE", "STRONG_HIRE"]))
                    .order_by(InterviewEvaluation.created_at.desc())
                ).scalars().all()

                for ev in evals:
                    key = f"{ev.candidate_id}_{ev.job_id}"
                    if key in candidates_dict:
                        continue
                    cand = db.execute(
                        select(Candidate).where(Candidate.id == ev.candidate_id).limit(1)
                    ).scalar_one_or_none()
                    job_obj = db.execute(
                        select(Job).where(Job.id == ev.job_id).limit(1)
                    ).scalar_one_or_none() if ev.job_id else None
                    # also try candidate.job_id
                    if not job_obj and cand and cand.job_id:
                        job_obj = db.execute(
                            select(Job).where(Job.id == cand.job_id).limit(1)
                        ).scalar_one_or_none()
                    if cand:
                        candidates_dict[key] = {
                            "session_id":      f"eval_{ev.id}",
                            "candidate_id":    ev.candidate_id,
                            "job_id":          ev.job_id or (cand.job_id if cand else None),
                            "status":          "COMPLETED",
                            "completed_at":    ev.created_at.isoformat() if ev.created_at else None,
                            "candidate_name":  cand.name,
                            "candidate_email": cand.email,
                            "job_title":       job_obj.title if job_obj else "Unknown Position",
                        }
                logger.info(f"After evaluations: {len(candidates_dict)} candidates")
            except Exception as e:
                logger.warning(f"Evaluations query failed: {e}")

            # ── 3. Applications with HIRED / OFFER_ACCEPTED / OFFER_SENT ─────
            try:
                apps = db.execute(
                    select(Application)
                    .where(Application.status.in_(["HIRED", "OFFER_ACCEPTED", "OFFER_SENT"]))
                    .order_by(Application.updated_at.desc())
                ).scalars().all()

                for app in apps:
                    key = f"{app.candidate_id}_{app.job_id}"
                    if key in candidates_dict:
                        continue
                    cand = db.execute(
                        select(Candidate).where(Candidate.id == app.candidate_id).limit(1)
                    ).scalar_one_or_none()
                    job_obj = db.execute(
                        select(Job).where(Job.id == app.job_id).limit(1)
                    ).scalar_one_or_none()
                    if cand and job_obj:
                        candidates_dict[key] = {
                            "session_id":      f"app_{app.id}",
                            "candidate_id":    app.candidate_id,
                            "job_id":          app.job_id,
                            "status":          "COMPLETED",
                            "completed_at":    app.updated_at.isoformat() if app.updated_at else None,
                            "candidate_name":  cand.name,
                            "candidate_email": cand.email,
                            "job_title":       job_obj.title,
                        }
                logger.info(f"After applications: {len(candidates_dict)} candidates")
            except Exception as e:
                logger.warning(f"Applications query failed: {e}")

            # ── 4. All InterviewEvaluations (any recommendation) as last resort ──
            # Ensures candidates with any completed evaluation appear, not just HIRE ones,
            # but only if no other source already captured them.
            try:
                all_evals = db.execute(
                    select(InterviewEvaluation)
                    .order_by(InterviewEvaluation.created_at.desc())
                ).scalars().all()

                for ev in all_evals:
                    job_id_eff = ev.job_id
                    cand = None
                    if not job_id_eff:
                        cand = db.execute(
                            select(Candidate).where(Candidate.id == ev.candidate_id).limit(1)
                        ).scalar_one_or_none()
                        if cand:
                            job_id_eff = cand.job_id
                    key = f"{ev.candidate_id}_{job_id_eff}"
                    if key in candidates_dict:
                        continue
                    if not cand:
                        cand = db.execute(
                            select(Candidate).where(Candidate.id == ev.candidate_id).limit(1)
                        ).scalar_one_or_none()
                    job_obj = db.execute(
                        select(Job).where(Job.id == job_id_eff).limit(1)
                    ).scalar_one_or_none() if job_id_eff else None
                    if cand:
                        candidates_dict[key] = {
                            "session_id":      f"eval_{ev.id}",
                            "candidate_id":    ev.candidate_id,
                            "job_id":          job_id_eff,
                            "status":          "COMPLETED",
                            "completed_at":    ev.created_at.isoformat() if ev.created_at else None,
                            "candidate_name":  cand.name,
                            "candidate_email": cand.email,
                            "job_title":       job_obj.title if job_obj else "Unknown Position",
                        }
                logger.info(f"Final total completed candidates: {len(candidates_dict)}")
            except Exception as e:
                logger.warning(f"All-evaluations fallback query failed: {e}")

            return {"success": True, "candidates": list(candidates_dict.values())}

    except Exception as e:
        logger.error(f"Failed to get completed candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/export/pdf")
async def export_interview_session_pdf(session_id: str):
    """Generate and return a PDF report of the candidate's interview details."""
    from shared.db.database import db_session
    from sqlalchemy import text
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    # ReportLab imports
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    try:
        with db_session() as db:
            # Query session details
            query_session = text("""
                SELECT i.id, i.candidate_id, i.job_id, i.completed_at,
                       c.name as candidate_name, c.email as candidate_email,
                       j.title as job_title,
                       e.final_score, e.content_score, e.behavior_score, e.recommendation, e.evaluator_notes
                FROM interview_sessions i
                LEFT JOIN candidates c ON c.id = i.candidate_id
                LEFT JOIN jobs j ON j.id = i.job_id
                LEFT JOIN interview_evaluations e ON e.session_id = i.session_id
                WHERE i.session_id = :session_id
            """)
            row = db.execute(query_session, {"session_id": session_id}).fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Interview session not found")
                
            db_id, cand_id, job_id, completed_at, name, email, job_title, final_score, content_score, behavior_score, recommendation, notes = row
            
            # Query turns details
            query_turns = text("""
                SELECT turn_number, question_text, candidate_response, content_score, behavior_score, final_score
                FROM interview_turns
                WHERE interview_id = :interview_id
                ORDER BY turn_number ASC
            """)
            turns = db.execute(query_turns, {"interview_id": db_id}).fetchall()
            
            # Generate PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Title'],
                textColor=colors.HexColor('#1e293b'),
                fontSize=22,
                spaceAfter=12
            )
            h2_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                textColor=colors.HexColor('#0f172a'),
                fontSize=14,
                spaceBefore=12,
                spaceAfter=6
            )
            body_style = ParagraphStyle(
                'BodyTextCustom',
                parent=styles['Normal'],
                textColor=colors.HexColor('#334155'),
                fontSize=10,
                leading=14
            )
            bold_style = ParagraphStyle(
                'BodyBold',
                parent=body_style,
                fontName='Helvetica-Bold'
            )
            
            story = []
            
            # Document Title
            story.append(Paragraph("AI Interview Scorecard", title_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Metadata Table
            meta_data = [
                [Paragraph("<b>Candidate Name:</b>", body_style), Paragraph(str(name or "N/A"), body_style),
                 Paragraph("<b>Job Title:</b>", body_style), Paragraph(str(job_title or "N/A"), body_style)],
                [Paragraph("<b>Email:</b>", body_style), Paragraph(str(email or "N/A"), body_style),
                 Paragraph("<b>Completed At:</b>", body_style), Paragraph(str(completed_at or "N/A"), body_style)],
                [Paragraph("<b>Final Score:</b>", body_style), Paragraph(f"{round((final_score or 0) * 100, 1)}%" if final_score is not None else "N/A", body_style),
                 Paragraph("<b>Recommendation:</b>", body_style), Paragraph(str(recommendation or "N/A"), bold_style)],
                [Paragraph("<b>Technical Score:</b>", body_style), Paragraph(f"{round((content_score or 0) * 100, 1)}%" if content_score is not None else "N/A", body_style),
                 Paragraph("<b>Communication Score:</b>", body_style), Paragraph(f"{round((behavior_score or 0) * 100, 1)}%" if behavior_score is not None else "N/A", body_style)]
            ]
            meta_table = Table(meta_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Summary / Evaluator Notes
            if notes:
                story.append(Paragraph("Evaluator Summary", h2_style))
                story.append(Paragraph(str(notes), body_style))
                story.append(Spacer(1, 0.2*inch))
                
            # Questions and Answers
            if turns:
                story.append(Paragraph("Detailed Q&A Transcript", h2_style))
                for t in turns:
                    t_num, q_text, ans_text, c_scr, b_scr, f_scr = t
                    turn_title = f"<b>Question {t_num}</b>"
                    if f_scr is not None:
                        turn_title += f" (Score: {round(f_scr * 100, 1)}%)"
                    
                    story.append(Paragraph(turn_title, bold_style))
                    story.append(Spacer(1, 0.05*inch))
                    story.append(Paragraph(f"<b>Q:</b> {q_text}", body_style))
                    story.append(Spacer(1, 0.03*inch))
                    story.append(Paragraph(f"<b>A:</b> {ans_text or 'No response'}", body_style))
                    story.append(Spacer(1, 0.15*inch))
                    
            doc.build(story)
            buffer.seek(0)
            
            filename = f"scorecard_{name.replace(' ', '_')}_{session_id[:8]}.pdf" if name else f"scorecard_{session_id}.pdf"
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
            
    except Exception as e:
        logger.error(f"Failed to export interview session PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
