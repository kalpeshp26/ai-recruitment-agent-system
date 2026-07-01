# Interview App Setup Guide

## Overview
The interview round is a separate React application located in `Multi-Round-Assesment (3)/Multi-Round-Assesment/`

## Quick Setup

### Step 1: Start the Main App Backend
```bash
# Terminal 1
cd D:\AbHyAs\SY\SEM2\Industry Project\w-interview-old\ai-recruitment-agent-system-w-interview
python backend/main.py
```
**Runs on:** http://127.0.0.1:8000

### Step 2: Start the Interview App Backend
```bash
# Terminal 2
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
**Runs on:** http://127.0.0.1:8001

### Step 3: Start the Interview App Frontend (React)
```bash
# Terminal 3
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm run dev
```
**Runs on:** http://localhost:5173

## How to Use

### For Admins:
1. Open main dashboard: http://127.0.0.1:8000/
2. Go to "Interview & Evaluation" tab
3. Click **"Open Candidate Interview"** button
4. New tab opens with the React interview interface

### For Candidates:
1. Direct link: http://localhost:5173/login
2. Login with any credentials (auth bypass active in dev mode)
3. Upload resume (PDF)
4. Click "Start Interview"
5. Complete interview questions
6. View results

## Architecture

```
┌─────────────────────────────────────┐
│  Main Admin Dashboard               │
│  Port: 8000                         │
│  Tech: FastAPI + Vanilla JS        │
│  ├─ Job Intake                      │
│  ├─ Candidate Intake                │
│  ├─ Screening                       │
│  ├─ Outreach                        │
│  └─ Interview & Evaluation          │
│     └─ [Open Interview App Button]  │
└────────────┬────────────────────────┘
             │
             │ Opens in new tab
             ↓
┌─────────────────────────────────────┐
│  Multi-Round Assessment App         │
│  Port: 5173 (Frontend)              │
│  Port: 8001 (Backend)               │
│  Tech: React + FastAPI              │
│  ├─ Login                           │
│  ├─ Resume Upload                   │
│  ├─ Interview Questions             │
│  ├─ AI Evaluation                   │
│  └─ Results Report                  │
└─────────────────────────────────────┘
```

## Ports Summary
- **8000** - Main app backend + frontend
- **8001** - Interview app backend
- **5173** - Interview app frontend (React/Vite)

## Troubleshooting

### Issue: "Module not found: psycopg"
**Solution:** Already fixed! `.env` changed to use SQLite instead of PostgreSQL.

### Issue: Interview button doesn't open
**Solution:** Make sure all 3 servers are running (main backend, interview backend, interview frontend)

### Issue: Port already in use
```bash
# Find and kill process
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

### Issue: React app not loading
```bash
# Install dependencies if needed
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm install
npm run dev
```

## Testing Flow

1. ✅ Start all 3 servers
2. ✅ Open main dashboard (http://127.0.0.1:8000)
3. ✅ Navigate to "Interview & Evaluation" tab
4. ✅ Click "Open Candidate Interview" button
5. ✅ New tab opens with React app (http://localhost:5173)
6. ✅ Login and complete interview
7. ✅ Results appear in main dashboard

## Files Modified
- `frontend/index.html` - Added "Open Candidate Interview" button
- `frontend/app.js` - Added `openInterviewApp()` function
- `Multi-Round-Assesment (3)/Multi-Round-Assesment/.env` - Changed to SQLite

## Success!
When you click "Open Candidate Interview" in the main dashboard, it should open the React app in a new tab where candidates can complete their interviews.
