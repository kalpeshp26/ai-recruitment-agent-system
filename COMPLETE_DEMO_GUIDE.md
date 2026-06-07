# 🚀 Complete Project Demo & Testing Guide

## Overview
This guide shows you how to test and demonstrate the entire AI Recruitment System end-to-end.

---

## 🔧 Prerequisites

### 1. Install Dependencies (One-time setup)
```bash
# Main app dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite python-multipart python-dotenv openai

# Interview app dependencies
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
pip install -r requirements.txt

# Interview frontend dependencies
cd frontend
npm install
cd ../../..
```

### 2. Initialize Interview Database (One-time setup)
```bash
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python init_db.py
cd ../..
```

---

## 🎬 Step-by-Step Demo

### STEP 1: Start All Servers (3 terminals)

#### Terminal 1: Main Backend
```bash
python main.py
```
**Should see**: `Uvicorn running on http://0.0.0.0:8000`

#### Terminal 2: Interview Backend
```bash
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
**Should see**: `Uvicorn running on http://0.0.0.0:8001`

#### Terminal 3: Interview Frontend (React)
```bash
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm run dev
```
**Should see**: `Local: http://localhost:5173/`

---

### STEP 2: Open Main Dashboard
1. Open browser: **http://127.0.0.1:8000/**
2. You should see the AI Recruitment System dashboard

---

### STEP 3: Demo the Complete Recruitment Pipeline

## 📋 Stage 1: Job Intake

1. Click **"Job Intake"** tab in sidebar
2. Fill out the job form:
   - **Job Title**: "Senior Software Engineer"
   - **Department**: "Engineering"
   - **Location**: "Remote"
   - **Experience**: Min: 3, Max: 7
   - **Skills**: Python, FastAPI, React, SQL
   - **Salary**: Min: 80000, Max: 150000
   - **Employment Type**: Full-time
   - **Description**: "We are seeking an experienced software engineer..."
3. Click **"Post Job"**
4. ✅ **Verify**: Job appears in the list below

---

## 👤 Stage 2: Candidate Intake

### Option A: Upload Resume
1. Click **"Candidate Intake"** tab
2. Select job from **"Link to Job"** dropdown
3. **Click** or **drag-and-drop** a resume file (PDF/DOCX)
4. ✅ **Verify**: Progress bar shows upload
5. ✅ **Verify**: Parsed resume data appears
6. ✅ **Verify**: Candidate added to list

### Option B: Manual Entry
1. Scroll down to manual entry form
2. Fill candidate details:
   - Name, Email, Phone
   - Skills, Experience, Education
   - Select job from dropdown
3. Click **"Add Candidate"**
4. ✅ **Verify**: Candidate appears in list

---

## 🔍 Stage 3: Screening

1. Click **"Screening"** tab
2. Optional: Select a job from filter
3. Click **"Run Screening"** button
4. ✅ **Verify**: Loading spinner appears
5. ✅ **Verify**: Stats cards update (Total, Screened, Shortlisted)
6. ✅ **Verify**: Screening results appear below
7. ✅ **Verify**: Candidates have status (Shortlisted/Rejected) and scores

---

## 📧 Stage 4: Outreach

1. Click **"Outreach"** tab
2. Optional: Filter by job
3. ✅ **Verify**: Shortlisted candidates appear in table
4. Click **"Send"** button for a candidate
5. ✅ **Verify**: Email sent confirmation
6. ✅ **Verify**: Status updates to "Contacted"

---

## 📝 Stage 5: Prescreening

### Option A: Admin View
1. Click **"Prescreening"** tab
2. Click **"Admin View"** button
3. ✅ **Verify**: Session list appears
4. Optional: Filter by job
5. Click **"Refresh Prescreening Data"**

### Option B: Candidate View (Demo)
1. Click **"Candidate View (Demo)"** button
2. ✅ **Verify**: 6 demo questions appear
3. Type in any textarea
4. ✅ **Verify**: Character counter updates in real-time
5. ✅ **Verify**: Green ✓ appears when minimum characters met
6. Click **"Submit Prescreening"**

### Option C: Take Simple Interview
1. Click **"Take Interview"** button
2. ✅ **Verify**: Opens `/candidate/interview` page
3. Fill out prescreening questionnaire
4. Submit answers

---

## 🎤 Stage 6-7: Interview & Evaluation

### Option A: Full AI Interview (React App)
1. Click **"Interview & Evaluation"** tab
2. Click **"Open Candidate Interview"** button
3. ✅ **Verify**: React app opens in new tab (http://localhost:5173)
4. **Register/Login**:
   - Email: test@example.com
   - Password: password123
   - Click "Register" or "Login"
5. ✅ **Verify**: Dashboard loads
6. **Upload Resume**:
   - Click "Upload Resume"
   - Select a PDF file
   - Wait for processing
7. ✅ **Verify**: Resume parsed successfully
8. **Start Interview**:
   - Click "Start Interview"
   - Answer 10 questions (5 HR + 5 Technical)
   - Type or speak answers
9. ✅ **Verify**: Questions appear one by one
10. ✅ **Verify**: AI adapts difficulty based on answers
11. **Complete Interview**:
    - Finish all 10 questions
    - View final report
12. ✅ **Verify**: Scores displayed (Behavioral, Technical, Confidence)

### Option B: Manual Entry (Alternative)
1. In main dashboard, **"Interview & Evaluation"** tab
2. Scroll to **"Manual Interview Results Entry"**
3. Fill form:
   - **Assessment Session ID**: 1 (or any existing session)
   - **Candidate Name**: John Doe (reference only)
   - **Phase**: Complete
   - **Current Turn**: 10
   - **Total Turns**: 10
   - **Behavioral Score**: 0.85
   - **Confidence Score**: 0.90
   - **Technical Score**: 0.88
   - **Transcript**: "Candidate performed well..."
4. Click **"Preview Data"** to see JSON
5. Click **"Save Interview Results"**
6. ✅ **Verify**: Success message appears
7. ✅ **Verify**: Data saved to database

---

## 💼 Stage 8: Offer Management

1. Click **"Offer Management"** tab
2. ✅ **Verify**: Stats show total offers
3. Click **"Generate Offer"** for a candidate
4. Fill offer details:
   - Position, Salary, Start Date
   - Benefits, Terms
5. Click **"Send Offer"**
6. ✅ **Verify**: Offer appears in list
7. ✅ **Verify**: Status shows "Sent"

---

## 📚 Stage 9: Onboarding

1. Click **"Onboarding"** tab
2. ✅ **Verify**: New hires appear in list
3. Click **"Start Onboarding"** for a candidate
4. ✅ **Verify**: Task checklist appears
5. Document collection:
   - ID proof
   - Address proof
   - Education certificates
6. Mark tasks as complete
7. ✅ **Verify**: Progress bar updates

---

## 📊 Stage 10: Analytics

1. Click **"Analytics"** tab
2. ✅ **Verify**: Dashboard metrics appear:
   - Total candidates
   - Conversion rates
   - Average time-to-hire
   - Pipeline funnel
3. ✅ **Verify**: Charts and graphs render
4. Click **"Export Analytics"**
5. ✅ **Verify**: CSV/PDF downloads

---

## 🎯 Quick Test Scenarios

### Scenario 1: Complete Pipeline (15 minutes)
1. Create job → Add candidate → Run screening
2. Send outreach → Complete prescreening
3. Take interview → Generate offer
4. Start onboarding → View analytics

### Scenario 2: Interview Focus (10 minutes)
1. Open React interview app
2. Register → Upload resume → Take interview
3. Complete 10 questions → View scores
4. Return to main dashboard
5. Verify interview results

### Scenario 3: Manual Entry (5 minutes)
1. Go to Interview stage
2. Fill manual entry form
3. Preview and save
4. Verify data flows to Offer stage

---

## ✅ Verification Checklist

### Main Dashboard
- [ ] Dashboard loads at http://127.0.0.1:8000/
- [ ] All 10 stages visible in sidebar
- [ ] Can switch between tabs

### Stage 1: Job Intake
- [ ] Can create new job
- [ ] Job appears in list
- [ ] Can delete job

### Stage 2: Candidate Intake
- [ ] Upload zone clickable
- [ ] Drag-and-drop works
- [ ] Job dropdown populated
- [ ] Resume parsing works
- [ ] Manual entry works

### Stage 3: Screening
- [ ] Run Screening button works
- [ ] Loading spinner appears
- [ ] Stats update correctly
- [ ] Results display with scores

### Stage 4: Outreach
- [ ] Shortlisted candidates appear
- [ ] Send button works
- [ ] Status updates

### Stage 5: Prescreening
- [ ] Admin view shows sessions
- [ ] Candidate view shows 6 questions
- [ ] Character counter works
- [ ] Submit works
- [ ] UI stable on scroll

### Stage 6-7: Interview
- [ ] React app opens at localhost:5173
- [ ] Can register/login
- [ ] Can upload resume
- [ ] Interview starts
- [ ] 10 questions appear
- [ ] Scores calculated
- [ ] Manual entry form works
- [ ] Preview works
- [ ] Save works

### Stage 8: Offer
- [ ] Can generate offers
- [ ] Offers display
- [ ] Status tracking works

### Stage 9: Onboarding
- [ ] Tasks appear
- [ ] Can mark complete
- [ ] Progress updates

### Stage 10: Analytics
- [ ] Metrics display
- [ ] Charts render
- [ ] Export works

---

## 🐛 Troubleshooting

### Problem: Backend not starting
```bash
# Check if port is in use
netstat -ano | findstr :8000
netstat -ano | findstr :8001

# Kill process if needed
taskkill /PID <PID> /F

# Restart backend
python backend/main.py
```

### Problem: React app not loading
```bash
# Check Node.js is installed
node --version
npm --version

# Reinstall dependencies
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Problem: Database errors
```bash
# Reinitialize interview database
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python init_db.py
```

### Problem: "No such table: users"
```bash
# Run database initialization
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python init_db.py
```

### Problem: Upload not working
- Check file size < 10MB
- Check file type is PDF/DOCX/TXT
- Check backend is running
- Check browser console for errors (F12)

---

## 📹 Demo Script (For Presentation)

### Introduction (1 minute)
"This is an AI-powered recruitment system with 10 automated stages from job posting to onboarding."

### Stage Overview (1 minute)
"Let me show you the 10 stages: Job Intake, Candidate Intake, Screening, Outreach, Prescreening, Interview, Evaluation, Offer, Onboarding, and Analytics."

### Live Demo (8 minutes)
1. **Job Creation** (1 min): "First, I'll create a job posting..."
2. **Candidate Upload** (1 min): "Now I'll upload a resume... AI parses it automatically..."
3. **Screening** (1 min): "Click Run Screening... AI evaluates all candidates..."
4. **Interview** (3 min): "Let me open the AI interview... It asks 10 adaptive questions..."
5. **Manual Entry** (1 min): "For external interviews, we have manual entry..."
6. **Analytics** (1 min): "Finally, here's the analytics dashboard..."

### Conclusion (1 minute)
"The system automates the entire recruitment pipeline with AI evaluation at every stage."

**Total Time: 12 minutes**

---

## 🎓 Key Features to Highlight

### AI-Powered Features
1. **Resume Parsing** - Automatic extraction of skills, experience, education
2. **Smart Screening** - AI evaluates candidates based on job requirements
3. **Adaptive Interview** - Difficulty adjusts based on candidate performance
4. **Behavioral Analysis** - Monitors confidence, communication, engagement
5. **Automated Scoring** - Multiple dimensions (technical, behavioral, confidence)

### User Experience
1. **Simple Interface** - Clean, modern dashboard
2. **Real-time Updates** - Live feedback and progress
3. **Toast Notifications** - User-friendly messages
4. **Data Flow** - Seamless stage-to-stage progression
5. **Manual Override** - Alternative entry for flexibility

### Technical Highlights
1. **Full Stack** - FastAPI backend + React frontend
2. **Database** - SQLite (dev) / PostgreSQL (prod)
3. **Real-time AI** - OpenAI GPT integration
4. **Speech-to-Text** - Voice interview support
5. **Proctoring** - Behavioral monitoring during interviews

---

## 📊 Expected Results

After completing the demo, you should have:
- ✅ 1+ jobs created
- ✅ 1+ candidates added
- ✅ Screening results with scores
- ✅ Outreach emails sent
- ✅ Prescreening sessions completed
- ✅ Interview results (real or manual)
- ✅ Offers generated
- ✅ Onboarding tasks tracked
- ✅ Analytics dashboard populated

---

## 🚀 Quick Start Commands

**Copy-paste these in 3 terminals:**

```bash
# Terminal 1
python backend/main.py
```

```bash
# Terminal 2
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

```bash
# Terminal 3
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm run dev
```

**Then open:** http://127.0.0.1:8000/

---

## 📝 Notes

- Interview app login: Any email/password works in dev mode
- Manual Session ID: Use 1 or any positive integer
- Scores: Must be between 0 and 1
- All stages work independently (can test in any order)
- Data persists in SQLite database

---

**Ready to demo! 🎉**

*Last Updated: June 3, 2026*
