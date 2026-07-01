# Interview Workflow Implementation Status

## ✅ Completed Changes

### Change 3: Separate EmailJS Configurations
**Status**: ✅ COMPLETE

**Files Modified:**
1. `.env` - Added 9 new EmailJS configuration variables:
   - `EMAILJS_OUTREACH_SERVICE_ID`, `EMAILJS_OUTREACH_TEMPLATE_ID`, `EMAILJS_OUTREACH_PUBLIC_KEY`
   - `EMAILJS_INTERVIEW_SERVICE_ID`, `EMAILJS_INTERVIEW_TEMPLATE_ID`, `EMAILJS_INTERVIEW_PUBLIC_KEY`
   - `EMAILJS_ONBOARDING_SERVICE_ID`, `EMAILJS_ONBOARDING_TEMPLATE_ID`, `EMAILJS_ONBOARDING_PUBLIC_KEY`
   - `INTERVIEW_BASE_URL=http://localhost:5173`
   - `INTERVIEW_EXPIRY_DAYS=7`

**Files Created:**
1. `interview/interview_email_sender.py` - Sends interview invitation emails
   - Function: `send_interview_invitation_email()`
   - Function: `send_interview_reminder_email()`
   - Includes EmailJS template documentation

### Change 2: Auto Interview Session Creation
**Status**: ✅ COMPLETE (Backend)

**Files Created:**
1. `interview/session_manager.py` - Manages interview sessions
   - Function: `create_interview_session()` - Creates session, generates URL
   - Function: `get_interview_session()` - Retrieves session details
   - Function: `update_interview_status()` - Updates status (PENDING/IN_PROGRESS/COMPLETED/EXPIRED)
   - Function: `list_pending_interviews()` - Lists pending interviews

**Files Modified:**
1. `prescreening/answer_evaluator.py` - Auto-creates interview on PASS verdict:
   - Creates interview session automatically
   - Sends interview invitation email
   - Updates application status to INTERVIEW_PENDING
   - Adds session_id and interview_url to event payload

**Flow:**
```
Prescreening PASS
  ↓
create_interview_session()
  ↓
Generate session ID (sess_abc123)
  ↓
Generate URL (http://localhost:5173/interview/session/sess_abc123)
  ↓
Store in interview_sessions table
  ↓
send_interview_invitation_email()
  ↓
Update application status → INTERVIEW_PENDING
  ↓
Publish SCREENING_PASSED event (includes interview_url)
```

---

## 🚧 Remaining Changes

### Change 1: Direct Interview Launch
**Status**: 🚧 PENDING

**Required Implementation:**
1. **Frontend Dashboard** (`frontend/app.js`):
   - Modify `loadInterviewResults()` to fetch interview sessions from backend
   - Add `launchInterview(sessionId)` function
   - Button: Opens `http://localhost:5173/interview/session/{sessionId}`

2. **Frontend HTML** (`frontend/index.html`):
   - Update Stage 6 UI to show interview sessions
   - Add "Launch Interview" button per session
   - Display: Candidate Name, Status, Session ID, Created Date

3. **Interview React App** (`Multi-Round-Assesment (3)/Multi-Round-Assesment/frontend/src/App.jsx`):
   - Add route: `/interview/session/:sessionId`
   - Auto-load session on mount
   - Skip landing page, go to Question 1
   - Keep resume upload for candidate identification

4. **Interview Backend** (`Multi-Round-Assesment (3)/Multi-Round-Assesment/app/api/interview_routes.py`):
   - Add endpoint: `GET /session/:sessionId/load`
   - Returns session data and first question
   - Validates session exists and not expired

### Change 4: Interview Status Tracking
**Status**: 🚧 PENDING

**Required Implementation:**
1. **Database Migration**:
   - Add `interview_status` column to `interview_sessions` table
   - Add `invited_at`, `started_at` timestamps
   - Run migration script

2. **Frontend Display** (`frontend/app.js`, `frontend/index.html`):
   - Display interview status badges (color-coded)
   - Show: PENDING (blue), IN_PROGRESS (orange), COMPLETED (green), EXPIRED (red)
   - Display timestamps: Created, Started, Completed
   - Add buttons: Launch Interview, Copy Link, Resend Email

3. **Status Updates**:
   - PENDING → Set when session created
   - IN_PROGRESS → Set when candidate starts first question
   - COMPLETED → Set when all questions answered
   - EXPIRED → Set by background job when deadline passes

### Change 5: Demo-Friendly Admin Shortcut
**Status**: 🚧 PENDING

**Required Implementation:**
- Same as Change 1 - "Launch Interview" button uses actual session ID
- No separate demo sessions needed
- HR and candidate use same session URL

---

## Quick Implementation Guide

### Step 1: Add Frontend Interview Display

File: `frontend/app.js`

```javascript
// Add at end of file
async function launchInterview(sessionId) {
    const url = `http://localhost:5173/interview/session/${sessionId}`;
    window.open(url, '_blank');
    setStatus('Interview launched', 'info');
}

async function copyInterviewLink(sessionId) {
    const url = `http://localhost:5173/interview/session/${sessionId}`;
    try {
        await navigator.clipboard.writeText(url);
        setStatus('Interview link copied!', 'success');
    } catch (e) {
        prompt('Copy this link:', url);
    }
}

async function resendInterviewEmail(candidateId, sessionId) {
    try {
        setStatus('Resending interview email...', 'info');
        // Call backend endpoint to resend
        const response = await apiRequest(`/interview/resend/${sessionId}`, { 
            method: 'POST' 
        }, API_BASE);
        setStatus('Interview email resent!', 'success');
    } catch (error) {
        setStatus(`Failed to resend: ${error.message}`, 'error');
    }
}

// Make functions available globally
window.launchInterview = launchInterview;
window.copyInterviewLink = copyInterviewLink;
window.resendInterviewEmail = resendInterviewEmail;
```

### Step 2: Update loadInterviewResults()

Replace existing `loadInterviewResults()` in `frontend/app.js`:

```javascript
async function loadInterviewResults() {
    try {
        // Fetch interview sessions from backend
        const response = await apiRequest('/interview/sessions', { 
            method: 'GET' 
        }, API_BASE);
        
        const sessions = Array.isArray(response.sessions) ? response.sessions : [];
        
        // Update stats
        setText('stat-total-interviews', sessions.length);
        setText('stat-completed-interviews', sessions.filter(s => s.status === 'COMPLETED').length);
        setText('stat-in-progress', sessions.filter(s => s.status === 'IN_PROGRESS').length);
        
        // Calculate average score
        const completed = sessions.filter(s => s.final_score != null);
        const avgScore = completed.length > 0 
            ? (completed.reduce((sum, s) => sum + s.final_score, 0) / completed.length).toFixed(1)
            : '0.0';
        setText('stat-avg-score', avgScore);
        
        // Render interview cards
        renderInterviewCards(sessions);
        
        setStatus('Interview data loaded', 'success');
        return sessions;
    } catch (error) {
        setStatus(`Load interviews failed: ${error.message}`, 'error');
        return [];
    }
}

function renderInterviewCards(sessions) {
    const container = $('interview-sessions-list');
    if (!container) return;
    
    if (sessions.length === 0) {
        container.innerHTML = '<div class="empty-state">No interview sessions yet</div>';
        return;
    }
    
    const cards = sessions.map(session => {
        const statusClass = {
            'PENDING': 'info',
            'IN_PROGRESS': 'warning',
            'COMPLETED': 'success',
            'EXPIRED': 'error'
        }[session.status] || 'info';
        
        return `
        <div class="job-card">
            <div class="job-card-header">
                <div class="job-card-title-block">
                    <h3>${escapeHTML(session.candidate_name || 'Unknown Candidate')}</h3>
                    <div class="job-card-subtitle">${escapeHTML(session.job_title || 'Position TBD')}</div>
                </div>
                <span class="status-tag ${statusClass}">${escapeHTML(session.status)}</span>
            </div>
            <div class="job-card-sections">
                <div class="job-card-section">
                    <span>SESSION ID</span>
                    <strong>${escapeHTML(session.session_id.substring(5, 13))}</strong>
                </div>
                <div class="job-card-section">
                    <span>CREATED</span>
                    <strong>${session.invited_at ? new Date(session.invited_at).toLocaleDateString() : 'N/A'}</strong>
                </div>
                <div class="job-card-section">
                    <span>SCORE</span>
                    <strong>${session.final_score != null ? session.final_score.toFixed(2) : 'Not completed'}</strong>
                </div>
            </div>
            <div class="job-card-footer">
                <span><strong>Candidate:</strong> ${escapeHTML(session.candidate_email || 'N/A')}</span>
                <div class="job-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="launchInterview('${escapeHTML(session.session_id)}')">
                        Launch Interview
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="copyInterviewLink('${escapeHTML(session.session_id)}')">
                        Copy Link
                    </button>
                    ${session.status === 'PENDING' || session.status === 'EXPIRED' ? 
                        `<button class="btn btn-ghost btn-sm" onclick="resendInterviewEmail('${escapeHTML(session.candidate_id)}', '${escapeHTML(session.session_id)}')">
                            Resend Email
                        </button>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');
    
    container.innerHTML = cards;
}
```

### Step 3: Add Backend Endpoint

File: Create `interview/interview_api.py`:

```python
"""
interview/interview_api.py
Interview session management API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/interview", tags=["interview"])

@router.get("/sessions")
async def list_interview_sessions(job_id: Optional[str] = None):
    """List all interview sessions with candidate details."""
    from interview.session_manager import list_pending_interviews
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job
    from sqlalchemy import text
    
    try:
        with db_session() as db:
            # Query interview sessions
            query = text("""
                SELECT i.id, i.candidate_id, i.job_id, i.interview_status,
                       i.invited_at, i.started_at, i.completed_at, i.expires_at,
                       c.name as candidate_name, c.email as candidate_email,
                       j.title as job_title
                FROM interview_sessions i
                LEFT JOIN candidates c ON c.id = i.candidate_id
                LEFT JOIN jobs j ON j.id = i.job_id
                ORDER BY i.invited_at DESC
            """)
            
            results = db.execute(query).fetchall()
            
            sessions = []
            for row in results:
                sessions.append({
                    "session_id": row[0],
                    "candidate_id": row[1],
                    "job_id": row[2],
                    "status": row[3] or "PENDING",
                    "invited_at": row[4],
                    "started_at": row[5],
                    "completed_at": row[6],
                    "expires_at": row[7],
                    "candidate_name": row[8],
                    "candidate_email": row[9],
                    "job_title": row[10],
                    "final_score": None  # TODO: Fetch from interview results
                })
            
            return {"success": True, "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resend/{session_id}")
async def resend_interview_email(session_id: str):
    """Resend interview invitation email."""
    from interview.session_manager import get_interview_session
    from interview.interview_email_sender import send_interview_invitation_email
    from shared.db.database import db_session
    from shared.db.models import Candidate, Job
    from datetime import datetime, timedelta
    
    try:
        session = get_interview_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        with db_session() as db:
            candidate = db.query(Candidate).filter_by(id=session['candidate_id']).first()
            job = db.query(Job).filter_by(id=session['job_id']).first()
            
            if not candidate or not job:
                raise HTTPException(status_code=404, detail="Candidate or job not found")
            
            interview_url = f"http://localhost:5173/interview/session/{session_id}"
            deadline = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
            
            email_sent = send_interview_invitation_email(
                candidate_email=candidate.email,
                candidate_name=candidate.name,
                job_title=job.title,
                interview_url=interview_url,
                completion_deadline=deadline,
                session_id=session_id
            )
            
            if email_sent:
                return {"success": True, "message": "Interview email resent successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to send email")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Register Interview Router

File: `backend/main.py`

Add to imports:
```python
from interview.interview_api import router as interview_api_router
```

Add to router registration:
```python
app.include_router(interview_api_router, prefix="/api")
```

---

## User Action Required

1. **Configure EmailJS Templates**:
   - Create 3 separate EmailJS templates (Outreach, Interview, Onboarding)
   - Update `.env` with actual service IDs, template IDs, and public keys

2. **Test Prescreening Flow**:
   - Complete a prescreening session with passing score
   - Verify interview session created automatically
   - Verify email sent
   - Check Stage 6 for interview session

3. **Implement Frontend Changes**:
   - Add the functions from Step 1 to `frontend/app.js`
   - Replace `loadInterviewResults()` from Step 2
   - Test "Launch Interview" button

4. **Register Backend Endpoint**:
   - Create `interview/interview_api.py` from Step 3
   - Add router to `backend/main.py` from Step 4
   - Restart backend

---

**Current Progress**: 40% Complete
**Next Priority**: Frontend interview display and launch functionality
**Blockers**: None - EmailJS credentials needed for email testing
