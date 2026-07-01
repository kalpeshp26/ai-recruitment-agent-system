# Prescreening Flow - Complete Guide

## 🎯 Actual Production Flow

### For Candidates:

```
1. Candidate receives outreach email
     ↓
2. Clicks prescreening link
     ↓
3. Opens: http://localhost:8000/candidate/prescreening
     ↓
4. Chatbot interface loads
     ↓
5. Answer 6 questions one by one
     ↓
6. Submit final answer
     ↓
7. Groq AI evaluates ALL answers (automatic)
     ↓
8a. IF PASS (score ≥ 2.5):
    - Interview session created
    - Invitation email sent with Session ID
    - Appears in Stage 6 dashboard
     ↓
8b. IF FAIL (score < 2.5):
    - Rejection recorded
    - No interview session created
```

---

## 🤖 AI Evaluation System

### Scoring Engine:
- **AI Model:** Groq (llama-3.3-70b-versatile)
- **Evaluation:** Automatic on submission
- **Speed:** 2-5 seconds per answer
- **Total Time:** ~15-30 seconds for all 6 answers

### Score Scale:
```
Excellent = 4 points
Good      = 3 points
Average   = 2 points
Poor      = 1 point
```

### Pass Threshold:
```
PASS        = Average ≥ 2.5 (auto-creates interview)
BORDERLINE  = Average ≥ 2.0 and < 2.5 (manual review)
FAIL        = Average < 2.0 (rejected)
```

### Knockout Disqualifiers (Instant FAIL):
- ❌ Notice period > 90 days
- ❌ Salary expectation 30%+ above budget
- ❌ Explicit lack of required experience

---

## 📊 Backend API Endpoints

### 1. Create Session
```
POST /api/prescreening/chatbot/session
Body: {
  "candidate_id": "cand_123",
  "job_id": "job_456"
}

Response: {
  "token": "unique-session-token",
  "session_id": "sess_789",
  "message": "Session created"
}
```

### 2. Start Chatbot
```
GET /api/prescreening/chatbot/start?token={token}

Response: {
  "session_id": "sess_789",
  "candidate_name": "John Doe",
  "job_title": "Software Engineer",
  "questions": [
    "What motivated you to apply...",
    "Describe your most relevant...",
    ...
  ],
  "total_questions": 6
}
```

### 3. Submit Answer
```
POST /api/prescreening/chatbot/answer
Body: {
  "token": "unique-session-token",
  "question_index": 0,
  "answer_text": "I'm excited about this role..."
}

Response (if more questions):
{
  "status": "next_question",
  "next_question_index": 1,
  "next_question": "Describe your most relevant..."
}

Response (if last question):
{
  "status": "complete",
  "message": "Thank you! Your responses have been submitted. We'll be in touch soon. 🎉"
}
```

**Note:** When last answer is submitted, automatic AI evaluation triggers!

---

## 🔄 Evaluation Process (Behind the Scenes)

### Step 1: Trigger (Automatic)
```python
# In screening_chatbot.py
if next_idx >= total:
    session.status = "COMPLETED"
    
    # Launch evaluation in background thread
    threading.Thread(
        target=evaluate_session,
        args=(str(session.session_id),),
        daemon=True
    ).start()
```

### Step 2: AI Scoring (15-30 seconds)
```python
# In answer_evaluator.py
for each answer:
    1. Send to Groq LLM
    2. Get score (Excellent/Good/Average/Poor)
    3. Check for disqualifiers
    4. Store result
```

### Step 3: Calculate Verdict
```python
avg_score = sum(all_scores) / 6

if disqualified:
    verdict = "FAIL"
elif avg_score >= 2.5:
    verdict = "PASS"
elif avg_score >= 2.0:
    verdict = "BORDERLINE"
else:
    verdict = "FAIL"
```

### Step 4: Actions Based on Verdict

#### If PASS:
1. Create interview session
2. Generate unique Session ID
3. Send invitation email with Session ID
4. Update application status to "INTERVIEW_PENDING"
5. Publish RabbitMQ event: `screening.passed`

#### If FAIL:
1. Store rejection reason
2. Update application status to "REJECTED"
3. Publish RabbitMQ event: `screening.failed`

---

## 🧪 Testing the Full Flow

### Option 1: Use Candidate Interface
1. Start backend: `python main.py`
2. Open: http://localhost:8000/candidate/prescreening
3. Use sample answers from PRESCREENING_ANSWERS.md
4. Submit all 6 answers
5. Wait 30 seconds
6. Check Stage 6 dashboard for interview session

### Option 2: Direct API Testing
```bash
# 1. Create session
curl -X POST http://localhost:8000/api/prescreening/chatbot/session \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "cand_test", "job_id": "job_test"}'

# 2. Start chatbot (use token from step 1)
curl http://localhost:8000/api/prescreening/chatbot/start?token=YOUR_TOKEN

# 3. Submit answers (repeat for each question)
curl -X POST http://localhost:8000/api/prescreening/chatbot/answer \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN",
    "question_index": 0,
    "answer_text": "Sample excellent answer here..."
  }'

# 4. Check logs for evaluation results
tail -f logs/prescreening.log
```

---

## 📝 Database Tables

### chatbot_sessions
```sql
- session_id (UUID)
- candidate_id
- job_id
- status (IN_PROGRESS, COMPLETED)
- questions (JSON array)
- created_at
- completed_at
```

### chatbot_answers
```sql
- session_id
- question_index
- question
- answer
- ai_score (Excellent/Good/Average/Poor)
- disqualified (boolean)
- reason
- answered_at
```

### scores
```sql
- application_id
- skill_score (average numeric score)
- total_score
- tag (PASS/BORDERLINE/FAIL)
- rejection_reason
- evaluation_detail (JSON with all answers)
```

### interview_sessions (created on PASS)
```sql
- id (Session ID shown to candidate)
- candidate_id
- job_id
- interview_status (PENDING)
- invited_at
- expires_at
```

---

## 🎯 Key Points

1. **Automatic Evaluation:** No manual trigger needed, happens on completion
2. **Background Processing:** Uses threading to avoid blocking API response
3. **Real-time:** Takes 15-30 seconds total
4. **Groq LLM:** Free tier has generous limits (14,400 requests/day)
5. **Pass Threshold:** Need average ≥ 2.5 (mix of Good/Excellent)
6. **Session Creation:** Automatic for PASS verdicts
7. **Email Sending:** Automatic with Session ID included

---

## 🚫 Common Issues

### Issue 1: "Demo submission" message in dashboard
**Cause:** You're using the demo form in main dashboard  
**Solution:** Use actual candidate interface at `/candidate/prescreening`

### Issue 2: No evaluation happening
**Cause:** GROQ_API_KEY not set in .env  
**Solution:** Add your Groq API key to .env file

### Issue 3: All answers score "Average"
**Cause:** Groq API error or rate limit  
**Solution:** Check logs, wait a minute, retry

### Issue 4: Not passing even with good answers
**Cause:** Answers too short or generic  
**Solution:** Use sample answers from guide, aim for 75-150 words per answer

---

## 📊 Success Metrics

**Good Answer Indicators:**
- Length: 75-150 words
- Specificity: Numbers, metrics, examples
- Relevance: Matches job requirements
- Professionalism: Proper grammar, structure
- Enthusiasm: Shows genuine interest

**Typical Score Distribution:**
- Excellent: Detailed, specific, professional
- Good: Clear, relevant, adequate detail
- Average: Generic, short, minimal detail
- Poor: Irrelevant, unprofessional, very short

---

## 🎉 Expected Results

After submitting good answers:
1. ✅ Evaluation completes in ~30 seconds
2. ✅ Interview session appears in Stage 6
3. ✅ Session ID is visible (e.g., "INT-2026-000123")
4. ✅ Email invitation sent (if EmailJS configured)
5. ✅ Status shows "INTERVIEW_PENDING"
6. ✅ Launch Interview button works

You're ready to test! Use the sample answers and follow the candidate flow.
