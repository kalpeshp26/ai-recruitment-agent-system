# 🏗️ AI Recruitment System - Architecture & Workflow

## System Overview

Multi-agent AI recruitment system with 10 automated stages covering the complete hiring pipeline from job posting to onboarding.

**Tech Stack:**
- **Backend**: Python FastAPI (async)
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI**: OpenAI GPT / Groq LLaMA
- **Email**: EmailJS
- **Event System**: In-memory (dev) / RabbitMQ (prod)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (SPA)                          │
│  HTML/CSS/JS - Dashboard with 10 Stage Tabs                 │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/REST API
┌──────────────────▼──────────────────────────────────────────┐
│                  FASTAPI BACKEND                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Main Application (main.py)              │   │
│  │  - CORS middleware                                   │   │
│  │  - Route registration                                │   │
│  │  - Lifespan management                               │   │
│  └──────────┬───────────────────────────────────────────┘   │
│             │                                                │
│  ┌──────────▼──────────────────────────────────────────┐   │
│  │           10 STAGE ROUTERS                           │   │
│  │  Stage 1: Job Intake (intake/)                       │   │
│  │  Stage 2: Candidate Intake (sourcing/)               │   │
│  │  Stage 3: Screening (screening/)                     │   │
│  │  Stage 4: Outreach (outreach/)                       │   │
│  │  Stage 5: Prescreening (prescreening/)               │   │
│  │  Stage 6-7: Interview (interview/)                   │   │
│  │  Stage 8: Offer Management (offer/)                  │   │
│  │  Stage 9: Onboarding (onboarding/)                   │   │
│  │  Stage 10: Analytics (analytics/)                    │   │
│  └──────────┬───────────────────────────────────────────┘   │
│             │                                                │
│  ┌──────────▼──────────────────────────────────────────┐   │
│  │         SHARED INFRASTRUCTURE                        │   │
│  │  - Database ORM (SQLAlchemy)                         │   │
│  │  - Event Bus (RabbitMQ/In-memory)                    │   │
│  │  - Storage (Local/S3)                                │   │
│  │  - Auth (JWT)                                        │   │
│  └──────────┬───────────────────────────────────────────┘   │
└─────────────┼───────────────────────────────────────────────┘
              │
┌─────────────▼──────────────┐   ┌──────────────────────────┐
│   SQLite/PostgreSQL DB     │   │  External Services       │
│  - candidates               │   │  - OpenAI/Groq API       │
│  - jobs                     │   │  - EmailJS               │
│  - applications             │   │  - Resume Storage        │
│  - interviews               │   └──────────────────────────┘
│  - communications           │
└─────────────────────────────┘
```

---

## Directory Structure

```
ai-recruitment-agent-system-w-interview/
├── backend/                    # Main backend server
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration
│   ├── database/               # Database setup
│   ├── models/                 # Pydantic models
│   ├── routers/                # API routes
│   └── services/               # Business logic
│
├── frontend/                   # Frontend application
│   ├── index.html              # Main dashboard
│   ├── app.js                  # JavaScript logic
│   ├── style.css               # Styling
│   └── services/               # Service modules
│
├── shared/                     # Shared utilities
│   ├── db/                     # Database models & session
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   └── database.py         # DB connection
│   ├── queue/                  # Event bus
│   │   ├── event_bus.py        # Pub/Sub system
│   │   └── event_topics.py     # Event definitions
│   ├── storage/                # File storage
│   └── auth/                   # Authentication
│
├── intake/                     # Stage 1: Job Intake
│   ├── job_requisition_api.py  # Job creation API
│   └── job_poster.py           # Multi-platform posting
│
├── sourcing/                   # Stage 2: Candidate Intake
│   ├── resume_collector.py     # Resume upload
│   ├── profile_parser.py       # AI parsing (Groq)
│   └── candidate_form.py       # Manual entry
│
├── screening/                  # Stage 3: Screening
│   ├── screening_api.py        # REST endpoints
│   ├── processor.py            # Screening orchestrator
│   ├── scoring_engine.py       # Candidate scoring (0-100)
│   ├── duplicate_detector.py   # Duplicate detection
│   └── shortlister.py          # Event listener
│
├── outreach/                   # Stage 4: Outreach
│   ├── outreach_api.py         # REST endpoints
│   ├── email_sender.py         # Outreach orchestrator
│   ├── emailjs_sender.py       # EmailJS integration
│   └── followup_manager.py     # Automated follow-ups
│
├── prescreening/               # Stage 5: Prescreening
│   ├── prescreening_api.py     # REST endpoints
│   ├── screening_chatbot.py    # AI chatbot
│   ├── answer_evaluator.py     # Answer scoring
│   └── background_checker.py   # BGV integration
│
├── interview/                  # Stage 6-7: Interview
│   ├── interview.py            # Interview logic
│   ├── rl_engine.py            # Adaptive Q-learning
│   └── proctoring/             # Behavioral monitoring
│
├── evaluation/                 # Stage 7: Evaluation
│   └── assessment.py           # Final scoring
│
├── offer/                      # Stage 8: Offer Management
│   ├── offer_agent.py          # Autonomous agent
│   ├── offer_letter_generator.py
│   └── negotiation_bot.py      # Negotiation handling
│
├── onboarding/                 # Stage 9: Onboarding
│   ├── onboarding_agent.py     # Autonomous agent
│   ├── task_manager.py         # Task tracking
│   └── document_collector.py   # Document management
│
├── analytics/                  # Stage 10: Analytics
│   ├── analytics_agent.py      # Autonomous agent
│   ├── recruitment_dashboard.py
│   ├── time_to_hire_reporter.py
│   └── hiring_forecast_engine.py
│
├── Multi-Round-Assesment (3)/  # AI Interview Module
│   └── Multi-Round-Assesment/
│       ├── app/                # Interview backend
│       └── frontend/           # Interview React app
│
├── data/                       # Database files
│   └── recruitment.db          # SQLite database
│
├── uploads/                    # Uploaded files
│   └── resumes/                # Resume storage
│
├── templates/                  # Email templates
│   ├── outreach_email.html
│   ├── prescreening_invitation.html
│   └── rejection_*.html
│
├── docs/                       # Documentation
├── tests/                      # Test files
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── main.py                     # Main entry point
```

---

## Database Schema

### Core Tables

**candidates**
- id (PK), name, email, phone
- skills (JSON), experience_years, education
- location, current_role
- resume_url, raw_resume_text, parsed_data (JSON)
- score, score_breakdown (JSON)
- status (new/parsed/shortlisted/rejected)
- is_duplicate, merged_into
- job_id (FK), source

**jobs**
- id (PK), title, department, location
- skills (JSON), experience_min, experience_max
- qualification, salary_min, salary_max
- employment_type, description
- status (draft/active/closed)

**applications**
- id (PK), candidate_id (FK), job_id (FK)
- status (APPLIED/SCREENING/SHORTLISTED/REJECTED/OUTREACH_SENT/PRESCREENING/INTERVIEW/SELECTED)
- stage (1-10)
- applied_at, updated_at

**communications**
- id (PK), candidate_id (FK), job_id (FK)
- type (outreach/followup/rejection)
- channel (email/sms), status (sent/delivered/opened/clicked)
- sent_at, template_used

**interview_sessions** (Multi-Round-Assesment DB)
- id (PK), session_id, candidate_id
- phase (HR/TECHNICAL/COMPLETE)
- current_turn, total_turns
- behavioral_score, confidence_score, technical_score
- transcript, rl_state (JSON)

---

## Complete Workflow

### Stage 1: Job Intake

**Endpoints:**
- `POST /api/intake/jobs` - Create job
- `GET /api/intake/jobs` - List jobs
- `POST /api/intake/post-job` - Post to platforms

**Flow:**
1. HR fills job requisition form
2. AI generates professional JD (GPT)
3. Job saved to database
4. Multi-platform posting (LinkedIn, Indeed, Adzuna)

**Events Published:**
- `job.created`
- `job.posted`

---

### Stage 2: Candidate Intake

**Endpoints:**
- `POST /api/sourcing/upload-resume` - Upload resume
- `POST /api/sourcing/candidates` - Manual entry
- `GET /api/sourcing/candidates` - List candidates

**Flow:**
1. **Resume Upload:**
   - File uploaded (PDF/DOCX/TXT)
   - Stored in uploads/resumes/
   - Candidate record created with job_id
   - Event published → Auto-parsing triggered

2. **AI Parsing:**
   - Text extraction (PyMuPDF/python-docx)
   - AI parsing (Groq LLaMA + LlamaIndex)
   - Structured data extracted: name, email, skills, education, experience
   - Candidate record updated with parsed data

3. **Manual Entry:**
   - Form-based entry with all fields
   - Direct database insert
   - Application record created

**Events Published:**
- `resume.uploaded`
- `profile.parsed`

**Key Files:**
- `sourcing/resume_collector.py`
- `sourcing/profile_parser.py`
- `sourcing/candidate_form.py`

---

### Stage 3: Screening

**Endpoints:**
- `POST /api/screening/run` - Run screening
- `GET /api/screening/stats` - Get statistics
- `GET /api/screening/candidates` - Get screening results

**Scoring System (0-100 points):**
- **Skills (40%)**: Intersection match with job requirements
  - Normalized matching (JavaScript ≈ JS, Node.js ≈ NodeJS)
  - Case-insensitive
- **Experience (30%)**: Meets minimum years requirement
  - Full marks if >= required
  - Proportional if less
- **Education (20%)**: Education level hierarchy
  - PhD (5) > Master's (4) > Bachelor's (3) > Associate (2) > High School (1)
- **Location (10%)**: Exact match bonus

**Shortlisting Threshold:** 70 points

**Flow:**
1. Fetch unscreened candidates (score IS NULL)
2. For each candidate:
   - Check duplicate (email, phone, fuzzy name match)
   - Calculate score against job requirements
   - Decide: shortlisted (≥70) or rejected (<70)
   - Update candidate.status and score
   - Update application.status
3. Publish events for next stage

**Events Published:**
- `candidate.screened`
- `candidate.shortlisted` (triggers outreach)
- `candidate.rejected`

**Key Files:**
- `screening/screening_api.py`
- `screening/processor.py`
- `screening/scoring_engine.py`

---

### Stage 4: Outreach

**Endpoints:**
- `POST /api/outreach/send` - Send outreach email
- `GET /api/outreach/candidates` - Get shortlisted candidates
- `GET /api/outreach/stats` - Get outreach statistics

**Flow:**
1. Listen for `candidate.shortlisted` event
2. Build personalized email with:
   - Job details
   - Company information
   - Prescreening chatbot link (with token)
3. Send via EmailJS
4. Create communication record
5. Update application.status → OUTREACH_SENT
6. Auto-create prescreening session

**EmailJS Integration:**
- Service ID, Template ID, Public Key, Private Key
- POST to `https://api.emailjs.com/api/v1.0/email/send`
- Template variables: candidate_name, job_title, chatbot_url

**Events Subscribed:**
- `candidate.shortlisted`

**Events Published:**
- `outreach.sent`

**Key Files:**
- `outreach/outreach_api.py`
- `outreach/email_sender.py`
- `outreach/emailjs_sender.py`

---

### Stage 5: Prescreening

**Endpoints:**
- `GET /api/prescreening/stats` - Get statistics
- `GET /api/prescreening/sessions` - Get sessions
- `GET /api/prescreening/candidates` - Get candidates

**Flow:**
1. Candidate clicks chatbot link from email
2. Session loaded with token
3. 6 prescreening questions presented
4. Answers evaluated by AI
5. Background verification (optional)
6. Session marked complete
7. Application.status → PRESCREENED

**Chatbot Questions:**
- Motivation for applying
- Relevant experience
- Salary expectations
- Availability
- Remote work preference
- Additional information

**Key Files:**
- `prescreening/prescreening_api.py`
- `prescreening/screening_chatbot.py`
- `prescreening/answer_evaluator.py`

---

### Stage 6-7: Interview & Evaluation

**Two Interview Options:**

#### Option A: Simple Prescreening (Main App)
- Served at `/candidate/interview`
- Simple HTML form with questions
- Lightweight, no complex setup

#### Option B: AI Interview (React App)
- **Requires 3 servers:**
  - Main backend: `http://localhost:8000`
  - Interview backend: `http://localhost:8001`
  - Interview frontend: `http://localhost:5173`

**AI Interview Features:**
- 10 adaptive questions (5 HR + 5 Technical)
- Reinforcement learning (Q-learning)
- Difficulty adjustment based on performance
- Speech-to-text and text-to-speech
- Behavioral proctoring
- Real-time evaluation

**Scoring Dimensions:**
- Technical score (0-1)
- Behavioral score (0-1)
- Confidence score (0-1)
- Communication score (0-1)
- Problem-solving score (0-1)

**Manual Entry Alternative:**
- Form in Stage 6 to enter results from external interviews
- Same fields as AI interview output
- Saves to same database schema

**Key Files:**
- `interview/interview.py`
- `interview/rl_engine.py`
- `backend/routers/interview_router.py`

---

### Stage 8: Offer Management

**Endpoints:**
- `POST /api/offer/generate` - Generate offer
- `POST /api/offer/send` - Send offer
- `GET /api/offer/list` - List offers

**Flow:**
1. Selected candidates from interview
2. Generate offer letter (PDF)
3. Negotiation handling (optional)
4. Send offer via email
5. Track acceptance/rejection
6. Update application.status → SELECTED

**Autonomous Agent:**
- Monitors interview completions
- Auto-generates offers for high scorers
- Sends reminders for pending decisions

**Key Files:**
- `offer/offer_agent.py`
- `offer/offer_letter_generator.py`

---

### Stage 9: Onboarding

**Endpoints:**
- `POST /api/onboarding/start` - Start onboarding
- `GET /api/onboarding/tasks` - Get tasks
- `POST /api/onboarding/complete-task` - Mark task complete

**Onboarding Tasks:**
1. Document collection (ID, address proof, education)
2. IT provisioning (laptop, accounts)
3. Background verification
4. Contract signing
5. Welcome kit dispatch

**Flow:**
1. Offer accepted
2. Auto-create onboarding checklist
3. Send document collection links
4. Track task completion
5. Trigger IT provisioning
6. Update application.status → ONBOARDING

**Key Files:**
- `onboarding/onboarding_agent.py`
- `onboarding/task_manager.py`
- `onboarding/document_collector.py`

---

### Stage 10: Analytics

**Endpoints:**
- `GET /api/analytics/dashboard` - Get dashboard metrics
- `GET /api/analytics/jobs` - Per-job analytics
- `GET /api/analytics/time-to-hire` - Time metrics
- `GET /api/analytics/forecast` - Hiring forecast

**Metrics Tracked:**
- Total candidates per stage
- Conversion rates (stage to stage)
- Average time-to-hire
- Source effectiveness
- Interviewer ratings
- Offer acceptance rate
- Dropout funnel

**Visualizations:**
- Funnel chart (stage-wise dropoff)
- Time-series graphs (candidates over time)
- Heatmaps (source × conversion)
- Forecast predictions

**Key Files:**
- `analytics/analytics_agent.py`
- `analytics/recruitment_dashboard.py`
- `analytics/time_to_hire_reporter.py`

---

## Event-Driven Architecture

### Event Bus

**In Development:**
- In-memory pub/sub
- Simple dictionary-based subscribers

**In Production:**
- RabbitMQ message broker
- Persistent queues
- Dead letter queues

### Event Flow

```
┌────────────┐       ┌──────────────┐       ┌────────────┐
│  Stage 2   │──────▶│  Event Bus   │──────▶│  Stage 3   │
│  Resume    │       │              │       │  Screening │
│  Uploaded  │       │ resume.      │       │  Processor │
└────────────┘       │ uploaded     │       └────────────┘
                     └──────────────┘
                            │
                     ┌──────▼──────┐
                     │   Parser    │
                     │  Auto-parse │
                     └─────────────┘
```

### Key Events

| Event | Published By | Subscribed By | Purpose |
|-------|-------------|---------------|---------|
| `job.created` | Job Intake | Analytics | Track job creation |
| `resume.uploaded` | Resume Collector | Profile Parser | Auto-parse resume |
| `profile.parsed` | Profile Parser | Screening | Ready for screening |
| `candidate.shortlisted` | Screening | Outreach | Send outreach email |
| `candidate.rejected` | Screening | Rejection Emailer | Send rejection |
| `outreach.sent` | Outreach | Prescreening | Create session |
| `interview.completed` | Interview | Offer | Trigger offer generation |

---

## API Architecture

### REST API Structure

**Base URL:** `http://localhost:8000/api`

**Route Prefixes:**
- `/intake/*` - Stage 1
- `/sourcing/*` - Stage 2
- `/screening/*` - Stage 3
- `/outreach/*` - Stage 4
- `/prescreening/*` - Stage 5
- `/interview/*` - Stage 6-7 (or separate port 8001)
- `/offer/*` - Stage 8
- `/onboarding/*` - Stage 9
- `/analytics/*` - Stage 10

**Authentication:**
- JWT tokens (Bearer)
- Dev mode: auto-creates test user if no token
- Production: requires valid JWT

**Response Format:**
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful"
}
```

**Error Format:**
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

---

## Frontend Architecture

### Single Page Application

**Structure:**
- 10 tab-based stages
- Vanilla JavaScript (no framework)
- Component-like functions
- State management via global `state` object

### State Management

```javascript
const state = {
    jobs: [],
    candidates: [],
    stageData: {
        screeningCandidates: [],
        outreachCandidates: [],
        prescreeningSessions: [],
        offers: [],
        onboarding: [],
        analytics: null
    }
};
```

### Key Functions

- `switchTab(tabId)` - Navigate between stages
- `loadJobs()` - Fetch and display jobs
- `loadCandidates()` - Fetch and display candidates
- `loadScreeningData()` - Load screening results
- `loadOutreachData()` - Load outreach candidates
- `runScreening()` - Trigger screening process
- `sendOutreach(candidateId, jobId)` - Send email

### UI Components

- **Job Cards** - Display job listings
- **Candidate Cards** - Display candidates
- **Screening Results** - Card-based results with status badges
- **Outreach Cards** - Show email status
- **Toast Notifications** - Success/error messages
- **Progress Indicators** - Loading states

---

## Configuration

### Environment Variables (`.env`)

```bash
# Database
DATABASE_URL=sqlite:///./data/recruitment.db

# AI Services
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# EmailJS
EMAILJS_SERVICE_ID=service_...
EMAILJS_TEMPLATE_ID=template_...
EMAILJS_PUBLIC_KEY=...
EMAILJS_PRIVATE_KEY=...

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Company Info
COMPANY_NAME=Your Company
SCREENING_BASE_URL=http://localhost:8000
```

---

## Deployment

### Development

```bash
# Backend
python main.py

# Interview Backend (optional)
cd "Multi-Round-Assesment (3)/Multi-Round-Assesment"
python -m uvicorn app.main:app --port 8001

# Interview Frontend (optional)
cd "Multi-Round-Assesment (3)/Multi-Round-Assesment/frontend"
npm run dev
```

### Production

**Backend:**
- Gunicorn + Uvicorn workers
- PostgreSQL database
- RabbitMQ message broker
- S3 for file storage
- Redis for caching

**Frontend:**
- Static file serving via Nginx
- CDN for assets
- Minified JS/CSS

**Infrastructure:**
- Docker containers
- Kubernetes orchestration
- Load balancer
- Auto-scaling

---

## Key Design Patterns

1. **Event-Driven Architecture** - Loose coupling between stages
2. **Repository Pattern** - Database access abstraction
3. **Service Layer** - Business logic separation
4. **Factory Pattern** - Object creation (candidates, applications)
5. **Strategy Pattern** - Different email sending strategies
6. **Observer Pattern** - Event subscribers
7. **State Machine** - Application status transitions

---

## Performance Optimizations

1. **Async/Await** - Non-blocking I/O operations
2. **Database Indexing** - On candidate.job_id, application.candidate_id
3. **Event Queue** - Asynchronous processing
4. **Lazy Loading** - Load stage data only when needed
5. **Pagination** - Limit API results
6. **Caching** - Job listings, candidate profiles

---

## Security Measures

1. **JWT Authentication** - Secure API access
2. **Input Validation** - Pydantic models
3. **SQL Injection Prevention** - ORM parameterized queries
4. **File Upload Validation** - Type and size checks
5. **CORS Configuration** - Controlled origin access
6. **Rate Limiting** - Prevent API abuse
7. **Environment Variables** - Sensitive data protection

---

## Testing Strategy

1. **Unit Tests** - Individual functions (`tests/`)
2. **Integration Tests** - Stage-to-stage flow
3. **API Tests** - Endpoint validation
4. **E2E Tests** - Complete workflow
5. **Load Tests** - Performance benchmarks

---

## Future Enhancements

1. **Real-time Notifications** - WebSocket for live updates
2. **Advanced Analytics** - ML-based predictions
3. **Video Interviews** - WebRTC integration
4. **Multi-tenancy** - Support multiple companies
5. **Mobile App** - Native mobile interface
6. **Candidate Portal** - Self-service application tracking
7. **ATS Integration** - Connect with existing systems
8. **Advanced Proctoring** - Eye tracking, face recognition

---

**Last Updated:** June 3, 2026
