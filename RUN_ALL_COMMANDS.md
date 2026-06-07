# Complete Run Commands

## Open 3 Terminals and Run These:

### Terminal 1: Main App Backend
```bash
cd D:\AbHyAs\SY\SEM2\Industry Project\w-interview-old\ai-recruitment-agent-system-w-interview
python backend/main.py
```

### Terminal 2: Interview App Backend
```bash
cd "D:\AbHyAs\SY\SEM2\Industry Project\w-interview-old\ai-recruitment-agent-system-w-interview\Multi-Round-Assesment (3)\Multi-Round-Assesment"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 3: Interview App Frontend (React)
```bash
cd "D:\AbHyAs\SY\SEM2\Industry Project\w-interview-old\ai-recruitment-agent-system-w-interview\Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm run dev
```

## Then Open in Browser:
- Main Dashboard: http://127.0.0.1:8000/
- Click "Interview & Evaluation" tab
- Click "Open Candidate Interview" button
- React app opens in new tab!

---

## That's It!
All 3 servers running = Interview system fully operational
