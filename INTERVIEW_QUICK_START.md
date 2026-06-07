# Interview Workflow - Quick Start Guide

## ✅ What's New

The interview workflow is now **fully automated**:
- ✅ Interview sessions created automatically when candidates pass prescreening
- ✅ Invitation emails sent automatically
- ✅ "Launch Interview" button opens directly to Question 1
- ✅ Status tracking (PENDING, IN_PROGRESS, COMPLETED, EXPIRED)
- ✅ Separate EmailJS configs for each workflow stage

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Run Database Migration
```bash
python run_interview_migration.py
```
Expected output:
```
✅ Added interview_status column
✅ Added invited_at column
✅ Added started_at column
✅ Migration completed successfully
```

### Step 2: Configure EmailJS (Optional - for emails)
Update `.env` with your EmailJS credentials:
```env
EMAILJS_INTERVIEW_SERVICE_ID=your_service_id
EMAILJS_INTERVIEW_TEMPLATE_ID=your_template_id
EMAILJS_INTERVIEW_PUBLIC_KEY=your_public_key
```

Create template at [EmailJS Dashboard](https://dashboard.emailjs.com):
- Template name: "Interview Invitation"
- Variables: `{{candidate_name}}`, `{{job_title}}`, `{{interview_url}}`, `{{completion_deadline}}`

### Step 3: Restart Backend
```bash
python backend/main.py
```

### Step 4: Test
1. Open dashboard: `http://localhost:8000`
2. Complete prescreening with passing score
3. Go to Stage 6
4. See interview session appear
5. Click "Launch Interview"

---

## 🎯 How to Use

### For HR/Recruiters:

**View All Interviews:**
```
Dashboard → Stage 6: AI Interview & Evaluation
```

**Launch Interview (Demo/Test):**
```
1. Find candidate's session card
2. Click "Launch Interview" button
3. Interview opens in new window → Question 1
```

**Share Interview Link:**
```
Click "Copy Link" → Paste in email/chat
```

**Resend Invitation Email:**
```
Click "Resend Email" (only for PENDING/EXPIRED status)
```

---

## 📊 Interview Statuses

| Status | Color | Meaning |
|--------|-------|---------|
| PENDING | 🔵 Blue | Session created, candidate not started |
| IN_PROGRESS | 🟠 Orange | Candidate answering questions |
| COMPLETED | 🟢 Green | All questions answered |
| EXPIRED | 🔴 Red | Deadline passed without completion |

---

## 🔄 Automatic Flow

```
Candidate passes prescreening (score ≥ 2.5)
  ↓
✅ Interview session created (sess_abc123def)
  ↓
✅ Invitation email sent automatically
  ↓
✅ Application status updated (INTERVIEW_PENDING)
  ↓
✅ Session appears in Stage 6
  ↓
Candidate clicks email link OR HR clicks "Launch Interview"
  ↓
✅ Interview opens → Question 1 immediately
```

---

## 🔧 Troubleshooting

**Q: Interview not auto-creating after prescreening?**
- Check prescreening score (must be ≥ 2.5 to pass)
- View backend logs for errors
- Verify migration ran successfully

**Q: Email not sending?**
- Update `.env` with EmailJS credentials
- Session still creates and appears in dashboard
- Use "Copy Link" to share manually

**Q: "Launch Interview" button not working?**
- Hard refresh browser (Ctrl+Shift+R)
- Verify interview app running on port 5173
- Check browser console for errors

**Q: Session not found?**
- Check database: `SELECT * FROM interview_sessions;`
- Verify session_id is correct
- Ensure migration added status column

---

## 📁 Key Files

**Backend:**
- `interview/session_manager.py` - Session CRUD
- `interview/interview_email_sender.py` - Email sending
- `interview/interview_api.py` - API endpoints
- `prescreening/answer_evaluator.py` - Auto-create logic

**Frontend:**
- `frontend/app.js` - Functions: launchInterview(), loadInterviewResults()
- `frontend/index.html` - Stage 6 UI with session cards

**Database:**
- `data/recruitment.db` - Main database
- `run_interview_migration.py` - Migration script

---

## 🎮 Test Commands

**Check if migration ran:**
```bash
python -c "import sqlite3; conn = sqlite3.connect('data/recruitment.db'); cur = conn.cursor(); cur.execute('PRAGMA table_info(interview_sessions)'); print([row[1] for row in cur.fetchall()]); conn.close()"
```

**List interview sessions:**
```bash
python -c "import sqlite3; conn = sqlite3.connect('data/recruitment.db'); cur = conn.cursor(); cur.execute('SELECT id, candidate_id, interview_status FROM interview_sessions'); print(cur.fetchall()); conn.close()"
```

**Test API endpoint:**
```bash
curl http://localhost:8000/api/interview/sessions
```

---

## 💡 Pro Tips

1. **Demo Mode**: "Launch Interview" opens actual candidate session - perfect for testing
2. **Multiple Sessions**: System handles unlimited concurrent interviews
3. **Email Optional**: Sessions work without EmailJS - use "Copy Link" instead
4. **Auto-Cleanup**: Set INTERVIEW_EXPIRY_DAYS to auto-expire old sessions
5. **Status Tracking**: Monitor interview progress in real-time

---

## 📞 Need Help?

**Check logs:**
```bash
# Backend logs show session creation
python backend/main.py

# Look for:
✅ Interview session created: sess_...
✅ Interview invitation email sent to...
```

**Check database:**
```bash
sqlite3 data/recruitment.db
SELECT * FROM interview_sessions ORDER BY invited_at DESC LIMIT 5;
```

**Verify API:**
```bash
curl http://localhost:8000/api/interview/stats
```

---

## 🎯 Success Criteria

✅ Prescreening pass creates interview automatically  
✅ Email sent (if EmailJS configured)  
✅ Session appears in Stage 6 dashboard  
✅ "Launch Interview" opens to Question 1  
✅ Status updates correctly  
✅ Timestamps recorded  

---

**Last Updated**: June 3, 2026  
**Version**: 1.0  
**Status**: Production Ready
