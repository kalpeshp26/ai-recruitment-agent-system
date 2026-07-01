# Interview Workflow Improvements - Implementation Plan

## Overview
5 major changes to streamline the interview workflow and improve automation.

---

## Change 1: Direct Interview Launch
**Goal**: Launch interview button opens directly to first question, bypassing all landing pages.

### Implementation:
1. **Frontend (Main Dashboard)**:
   - Modify "Launch Interview" button in Stage 6
   - Generate URL with session ID: `/interview/session/{session_id}`
   - Button should fetch active interview sessions for candidate
   
2. **Interview React App**:
   - Add route: `/interview/session/:sessionId`
   - Auto-load session data on mount
   - Skip homepage/landing, go straight to Question 1
   - Keep resume upload only (for candidate identification)

### Files to Modify:
- `frontend/app.js` - loadInterviewResults(), button handler
- `frontend/index.html` - Update button onclick
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/frontend/src/App.jsx` - Add direct route
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/app/api/interview_routes.py` - Session endpoint

---

## Change 2: Auto Interview Session on Prescreening Pass
**Goal**: When candidate passes prescreening, automatically create interview session and send email.

### Implementation:
1. **Prescreening Evaluator**:
   - When verdict == "PASS", call interview session creator
   - Generate unique session ID
   - Store in `interview_sessions` table
   - Update candidate status to "INTERVIEW_PENDING"

2. **Interview Session Creator**:
   - New function: `create_interview_session(candidate_id, job_id)`
   - Generate session ID, secure token
   - Set expiration (7 days)
   - Return interview URL

3. **Email Sender**:
   - Call `sendInterviewInvitationEmail()` after session creation
   - Include interview link, instructions, deadline

### Files to Create/Modify:
- `prescreening/answer_evaluator.py` - Add interview session creation on PASS
- `interview/session_manager.py` (NEW) - Create interview sessions
- `interview/email_sender.py` (NEW) - Send interview invitations
- `.env` - Add EMAILJS_INTERVIEW_* configs

---

## Change 3: Separate EmailJS Configurations
**Goal**: Different EmailJS templates for each workflow stage.

### Implementation:
1. **Environment Variables** (`.env`):
```env
# Outreach (Stage 4)
EMAILJS_OUTREACH_SERVICE_ID=service_xxx
EMAILJS_OUTREACH_TEMPLATE_ID=template_xxx
EMAILJS_OUTREACH_PUBLIC_KEY=key_xxx

# Interview Invitation (Stage 5->6)
EMAILJS_INTERVIEW_SERVICE_ID=service_yyy
EMAILJS_INTERVIEW_TEMPLATE_ID=template_yyy
EMAILJS_INTERVIEW_PUBLIC_KEY=key_yyy

# Onboarding (Stage 9)
EMAILJS_ONBOARDING_SERVICE_ID=service_zzz
EMAILJS_ONBOARDING_TEMPLATE_ID=template_zzz
EMAILJS_ONBOARDING_PUBLIC_KEY=key_zzz
```

2. **Email Senders**:
   - `outreach/outreach_email_sender.py` - Uses OUTREACH config
   - `interview/interview_email_sender.py` - Uses INTERVIEW config
   - `onboarding/onboarding_email_sender.py` - Uses ONBOARDING config

3. **Functions**:
   - `sendOutreachEmail(candidate, job, prescreening_link)`
   - `sendInterviewInvitationEmail(candidate, interview_link, deadline)`
   - `sendOnboardingEmail(candidate, onboarding_portal, documents)`

### Files to Create/Modify:
- `.env` - Add all 9 new variables
- `outreach/outreach_email_sender.py` (NEW)
- `interview/interview_email_sender.py` (NEW)
- `onboarding/onboarding_email_sender.py` (NEW)
- Update existing email sending code to use dedicated senders

---

## Change 4: Interview Status Tracking
**Goal**: Track interview status (PENDING, IN_PROGRESS, COMPLETED, EXPIRED).

### Implementation:
1. **Database Schema**:
   - Add `interview_status` column to `interview_sessions` table
   - Values: PENDING, IN_PROGRESS, COMPLETED, EXPIRED
   - Add `invited_at`, `started_at`, `completed_at` timestamps

2. **Status Updates**:
   - PENDING: When session created
   - IN_PROGRESS: When candidate starts first question
   - COMPLETED: When all questions answered
   - EXPIRED: When deadline passes (background job)

3. **Frontend Display (Stage 6)**:
   - Show interview status in cards
   - Display: Candidate Name, Prescreening Score, Interview Status, Created, Completion
   - Buttons: Launch Interview, Copy Link, Resend Email
   - Color-code statuses: PENDING (blue), IN_PROGRESS (orange), COMPLETED (green), EXPIRED (red)

### Files to Modify:
- Database migration: Add interview_status column
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/app/models/interview.py` - Add status field
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/app/api/interview_routes.py` - Update status endpoints
- `frontend/app.js` - loadInterviewResults() with status display
- `frontend/index.html` - Stage 6 cards with status badges

---

## Change 5: Demo-Friendly Admin Shortcut
**Goal**: Launch Interview button opens the SAME session candidate would get via email.

### Implementation:
1. **Session Linking**:
   - When displaying interview in Stage 6, show candidate's actual session ID
   - "Launch Interview" button opens: `http://localhost:5173/interview/session/{actual_session_id}`
   - No separate demo sessions - uses production session

2. **Interview App**:
   - `/interview/session/:sessionId` route works for both:
     - Candidate clicking email link
     - HR clicking Launch Interview
   - Same session, same questions, same flow

3. **Security**:
   - Interview app validates session ID exists
   - Shows resume upload if not yet matched to user
   - Loads session data and starts interview

### Files to Modify:
- `frontend/app.js` - Update openInterviewApp() and add launchInterview(sessionId)
- `frontend/index.html` - Add Launch Interview button per interview card
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/frontend/src/App.jsx` - Route handling

---

## Database Schema Changes

### New Table: `interview_invitations`
```sql
CREATE TABLE interview_invitations (
    id VARCHAR PRIMARY KEY,
    candidate_id VARCHAR NOT NULL,
    job_id VARCHAR NOT NULL,
    session_id VARCHAR UNIQUE NOT NULL,
    interview_url TEXT NOT NULL,
    status VARCHAR DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, EXPIRED
    invited_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

### Update `interview_sessions` table:
```sql
ALTER TABLE interview_sessions ADD COLUMN interview_status VARCHAR DEFAULT 'PENDING';
ALTER TABLE interview_sessions ADD COLUMN invited_at DATETIME;
ALTER TABLE interview_sessions ADD COLUMN started_at DATETIME;
```

---

## Event Flow

### Current Flow:
```
Candidate completes prescreening
  ↓
answer_evaluator.py evaluates
  ↓
If PASS: publish SCREENING_PASSED event
  ↓
[Manual] HR creates interview session
```

### New Flow:
```
Candidate completes prescreening
  ↓
answer_evaluator.py evaluates
  ↓
If PASS:
  1. Create interview session (auto)
  2. Generate interview URL
  3. Send interview invitation email (auto)
  4. Publish SCREENING_PASSED event
  5. Update status to INTERVIEW_PENDING
  ↓
Candidate receives email with interview link
  ↓
Candidate clicks link → Interview starts at Question 1
  ↓
OR
  ↓
HR clicks "Launch Interview" → Same session, Question 1
```

---

## Implementation Order

1. ✅ **Change 3**: Set up EmailJS configurations (foundation)
2. ✅ **Change 4**: Add interview status tracking (database)
3. ✅ **Change 2**: Auto-create interview sessions on prescreening pass
4. ✅ **Change 1**: Direct interview launch (frontend + React app)
5. ✅ **Change 5**: Demo shortcut (reuses Change 1 implementation)

---

## Testing Checklist

### Change 1 - Direct Interview Launch:
- [ ] Click "Launch Interview" from Stage 6
- [ ] Verify URL contains session ID
- [ ] Verify interview app opens to Question 1 directly
- [ ] Verify no landing page shown
- [ ] Verify resume upload still works for identification

### Change 2 - Auto Interview on Prescreening Pass:
- [ ] Complete prescreening with passing score
- [ ] Verify interview session created automatically
- [ ] Verify interview invitation email sent
- [ ] Verify candidate status updated to INTERVIEW_PENDING
- [ ] Verify interview appears in Stage 6

### Change 3 - Separate EmailJS:
- [ ] Verify outreach email uses OUTREACH template
- [ ] Verify interview email uses INTERVIEW template
- [ ] Verify onboarding email uses ONBOARDING template
- [ ] Verify all emails send successfully

### Change 4 - Status Tracking:
- [ ] Verify status shows PENDING when created
- [ ] Verify status changes to IN_PROGRESS when started
- [ ] Verify status changes to COMPLETED when finished
- [ ] Verify expired interviews marked EXPIRED
- [ ] Verify Stage 6 displays correct status badges

### Change 5 - Admin Shortcut:
- [ ] Verify Launch Interview uses actual session ID
- [ ] Verify same session opened by candidate and HR
- [ ] Verify no duplicate sessions created
- [ ] Verify interview progress persists

---

## Files Overview

### New Files:
1. `interview/session_manager.py` - Create/manage interview sessions
2. `interview/interview_email_sender.py` - Send interview invitations
3. `outreach/outreach_email_sender.py` - Send outreach emails
4. `onboarding/onboarding_email_sender.py` - Send onboarding emails
5. `database/migrations/add_interview_status.sql` - Database migration

### Modified Files:
1. `.env` - EmailJS configurations
2. `prescreening/answer_evaluator.py` - Auto-create interview on PASS
3. `frontend/app.js` - Interview launch, status display
4. `frontend/index.html` - Stage 6 UI updates
5. `Multi-Round-Assesment (3)/Multi-Round-Assesment/frontend/src/App.jsx` - Direct routing
6. `Multi-Round-Assesment (3)/Multi-Round-Assesment/app/api/interview_routes.py` - Session endpoints

---

**Status**: Planning Complete - Ready for Implementation
**Estimated Time**: 2-3 hours
**Priority**: High - Critical workflow improvement
