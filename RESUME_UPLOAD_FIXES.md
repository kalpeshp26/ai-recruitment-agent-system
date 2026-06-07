# Resume Upload Fixes

## Issues Fixed

### 1. **Job Dropdown Not Populated**
**Problem:** The "Link to Job" dropdown in the resume upload section was empty even when jobs existed.

**Root Cause:** Jobs were not loaded on page initialization, only when switching to specific tabs.

**Fix Applied:**
- Added `loadJobs()` call in `DOMContentLoaded` event handler to load jobs immediately on page load
- Added `'resume-job-select'` to the list of dropdowns populated by `loadJobsForSelect()` function
- Now all job dropdowns across the app are populated consistently

**Files Changed:**
- `frontend/app.js` (lines ~1558-1565, ~502)

---

### 2. **Resume Upload API Endpoint Mismatch**
**Problem:** Frontend was calling wrong API endpoint for resume upload.

**Root Cause:** Frontend called `/api/sourcing/resume/upload` but backend endpoint is `/api/sourcing/upload-resume`

**Fix Applied:**
- Updated fetch URL from `/api/sourcing/resume/upload` to `/api/sourcing/upload-resume`

**Files Changed:**
- `frontend/app.js` (line ~1448)

---

### 3. **Resume Parsing Display Issues**
**Problem:** After upload, frontend showed "failed to parse resume" even when upload succeeded.

**Root Cause:** 
- Resume parsing happens **asynchronously** after upload (triggered by event)
- Frontend expected immediate parsed data in upload response
- Upload API only returns basic info (candidate_id, filename)
- Parsing takes 1-3 seconds to complete

**Fix Applied:**
- Implemented **polling mechanism** to wait for parsing completion
- Frontend now:
  1. Uploads file successfully
  2. Shows "Parsing resume..." status
  3. Polls candidate endpoint every 1 second (max 10 attempts)
  4. Displays parsed data once `status === 'parsed'`
  5. Shows appropriate message if parsing takes longer
- Better error handling and status messages

**Files Changed:**
- `frontend/app.js` (lines ~1461-1540)

---

## How It Works Now

### Upload Flow:
1. User selects job from dropdown (now populated)
2. User uploads resume file (PDF/DOCX/TXT)
3. Backend validates file and saves it
4. Backend creates candidate record with `status='uploaded'`
5. Backend publishes `resume.uploaded` event
6. Auto-parsing function triggers (background)
7. Resume text extracted (PyMuPDF/python-docx)
8. LlamaIndex + Groq AI parses structured data
9. Candidate record updated with:
   - name, email, phone
   - skills, education, experience
   - work_history
   - `status='parsed'`
10. Frontend polls and displays parsed data

### Polling Logic:
- Starts 1.5 seconds after upload
- Checks candidate status every 1 second
- Max 10 attempts (10 seconds total)
- Displays parsed data when ready
- Shows warning if parsing takes longer

---

## Testing

### Before Starting:
```bash
# Terminal 1: Main backend
python backend/main.py

# OR with explicit module
python main.py
```

### Test Steps:
1. Open http://127.0.0.1:8000/
2. Go to **Stage 1: Job Intake** tab
3. Create a test job (any title, e.g., "Test Engineer")
4. Go to **Stage 2: Candidate Intake** tab
5. Check "Link to Job" dropdown - should show "Test Engineer"
6. Upload a resume (PDF or DOCX)
7. Watch progress:
   - "Uploading..." (20%)
   - "Processing..." (60%)
   - "Parsing resume..." (100%)
8. After 2-3 seconds, parsed data appears
9. Verify extracted: name, email, phone, skills, experience

### Expected Results:
- ✅ Job dropdown populated
- ✅ File uploads successfully
- ✅ Parsing completes within 3-5 seconds
- ✅ Parsed data displayed correctly
- ✅ Candidate appears in list below

### If Parsing Fails:
Check backend logs for:
- Groq API key issues (`GROQ_API_KEY` in `.env`)
- File read permissions
- PyMuPDF/python-docx installation
- Event bus connection

---

## API Endpoints Used

### Upload Resume:
```
POST /api/sourcing/upload-resume
Content-Type: multipart/form-data

Body:
- file: (PDF/DOCX/TXT file)
- job_id: (optional) UUID of job

Response:
{
  "success": true,
  "candidate_id": "uuid",
  "filename": "resume.pdf",
  "file_path": "uploads/resumes/uuid_resume.pdf",
  "job_id": "job-uuid",
  "message": "Resume uploaded successfully. Queued for parsing."
}
```

### Get Candidate (for polling):
```
GET /api/sourcing/candidates/{candidate_id}

Response:
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "skills": ["Python", "FastAPI", "React"],
  "education": ["B.Tech Computer Science"],
  "experience_years": 5,
  "status": "parsed",  // or "uploaded"
  ...
}
```

---

## Architecture Notes

### Why Async Parsing?
- Resume parsing is **CPU/AI intensive** (1-3 seconds)
- Blocking upload for parsing creates poor UX
- Event-driven architecture allows:
  - Fast upload response
  - Background processing
  - Scalable with queue systems (RabbitMQ)
  - Retry logic for failures

### Event Flow:
```
upload_resume()
  ↓
[saves file + creates candidate]
  ↓
publishes → "resume.uploaded" event
  ↓
auto_parse_uploaded_resume() listens
  ↓
_parse_uploaded_resume_internal()
  ↓
extract_text() → _parse_with_llamaindex()
  ↓
updates candidate.status = 'parsed'
  ↓
publishes → "profile.parsed" event
```

---

## Dependencies Required

### Python Packages:
```bash
pip install PyMuPDF        # PDF text extraction
pip install python-docx    # DOCX text extraction
pip install llama-index-core
pip install llama-index-llms-groq
```

### Environment Variables:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

Get Groq API key: https://console.groq.com/

---

## Future Enhancements

1. **Websocket Updates**: Push parsing completion to frontend instead of polling
2. **Progress Updates**: Show parsing stages (extracting → analyzing → saving)
3. **Batch Upload**: Allow multiple resume uploads at once
4. **Error Recovery**: Retry failed parsing automatically
5. **Preview Mode**: Show extracted text before final parsing
6. **Manual Correction**: Allow editing parsed data before saving

---

## Troubleshooting

### "No jobs in dropdown"
- Run backend first: `python backend/main.py` or `python main.py`
- Create a job in Stage 1
- Refresh browser (jobs load on page load now)

### "Failed to parse resume"
- Check if file is valid PDF/DOCX
- Check file size < 10MB
- Verify Groq API key in `.env`
- Check backend logs for parsing errors
- Try uploading again (parsing is idempotent)

### "Parsing takes too long"
- Normal: 2-5 seconds for typical resume
- Long resumes (>10 pages) may take 5-10 seconds
- Check Groq API rate limits
- Check network connection to Groq
- Falls back to regex parsing if Groq fails

### "Candidate status stuck on 'uploaded'"
- Parsing failed silently
- Check backend logs for errors
- Check if PyMuPDF/python-docx installed
- Verify file is readable
- Try manual parsing endpoint (if available)

---

**Last Updated:** June 3, 2026
