# AI Recruitment Multi-Agent System

A complete 10-stage autonomous recruitment pipeline with AI-powered agents for job posting, candidate sourcing, screening, interviews, offers, and onboarding.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for interview frontend)

### 1. Start Infrastructure Services (Docker)

```bash
# Start infrastructure containers only (development):
docker compose up -d postgres rabbitmq redis

# Start full stack including the API app (uses the 'full-stack' profile):
docker compose --profile full-stack up -d --build

# Development override (hot-reload):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Verify services are running
docker ps
```

**Service Status (default mappings in this repo):**
- PostgreSQL (host port): 5433 -> container 5432 (user: recruitment_user, db: recruitment)
- RabbitMQ Management UI: http://localhost:15672 (AMQP: 5672)
- Redis: http://localhost:6379

### 2. Setup Python Environment

```bash
# Create and activate a virtualenv (Windows)
python -m venv .venv
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
# If a .env.example exists, copy it; otherwise create a minimal .env.
if exist .env.example (
	copy .env.example .env
) else (
	echo "# Minimal .env for local development" > .env
)

# Edit .env to add keys like GROQ_API_KEY, JWT_SECRET, etc.
```

Minimal `.env` example (add API keys as needed):

```env
# Use SQLite by default (no change required)
# DATABASE_URL=sqlite+aiosqlite:///./data/recruitment.db

# Toggle production behaviour
PRODUCTION_MODE=false

# Local secrets
JWT_SECRET=dev-secret-key-change-in-production

# Optional AI / third-party keys (leave blank to disable features)
GROQ_API_KEY=
GITHUB_API_TOKEN=
STACKOVERFLOW_API_KEY=
LINKEDIN_ACCESS_TOKEN=
```

### 3. Start Backend Services

```bash
# Run the API locally (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or (Windows) with the bundled script
python main.py
```

Wait for startup messages:
```
✅ Stages 8, 9, 10 autonomous agents started
🚀 AI Recruitment System started
📊 Dashboard: http://localhost:8000
```

### 4. Start Stage 6 Multi-Round Assessment

The Stage 6 interview flow is a separate React + FastAPI app in:

`Multi-Round-Assesment (3)/Multi-Round-Assesment`

Start it with two terminals:

Backend terminal:
```bash
# IMPORTANT: run this from the Multi-Round-Assesment project root, not the main repo root
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Frontend terminal:
```bash
cd "Multi-Round-Assesment (3)\Multi-Round-Assesment\frontend"
npm install
npm run dev
```

Default dev ports:
- Backend API: `http://localhost:8001`
- Frontend: `http://localhost:5173`

The Vite frontend proxies `/api` requests to `http://localhost:8001` by default, so keep the backend on port 8001 unless you also update `frontend/vite.config.js`.

If you see `ModuleNotFoundError: No module named 'app'`, it means the backend was launched from the wrong folder. Go into `Multi-Round-Assesment (3)\Multi-Round-Assesment` first, then run `uvicorn app.main:app ...`.

If you want the main recruitment dashboard to open the interview flow, use Stage 6 in the main app and it will redirect to `http://localhost:5173/interview`.

### 5. Create Sample Data

```bash
# In a new terminal, create test data
python create_simple_sample_data.py
```

## � Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Main Dashboard** | http://localhost:8000 | Complete recruitment pipeline (10 stages) |
| **Stage 6 Multi-Round Assessment** | http://localhost:5173/interview | Candidate-facing AI interview interface |
| **Stage 6 API** | http://localhost:8001 | FastAPI backend for aptitude / coding / interview rounds |
| **API Documentation** | http://localhost:8000/docs | FastAPI interactive docs |
| **PostgreSQL** | localhost:5433 | Database (recruitment/recruitment_user) |
| **RabbitMQ Management** | http://localhost:15672 | Event bus monitoring (recruitment/recruitment_queue) |
| **Redis** | localhost:6379 | Cache service |

## 🎯 System Status

**✅ Working Stages (76.9%):**
- Stage 1: Job Requisition & Posting
- Stage 2: Candidate Sourcing  
- Stage 3: Screening & Shortlisting
- Stage 4: Outreach
- Stage 5: Prescreening
- Stage 7: Evaluation
- Stage 8: Offer Management

**⚠️ Known Issues:**
- Stage 6: Interview (SQL compatibility)
- Stage 9: Onboarding (SQL compatibility) 
- Stage 10: Analytics (SQL compatibility)

## 🔧 Health Check

```bash
# Test all system components
python system_health_check.py
```

## 📁 Project Structure

```
├── main.py                 # Main FastAPI application
├── config.py              # Configuration settings
├── .env                   # Environment variables
├── docker-compose.yml     # Infrastructure services
├── data/                  # SQLite database
├── frontend/              # Admin dashboard
├── interview-frontend/    # React interview app
├── intake/               # Stage 1: Job requisition
├── sourcing/             # Stage 2: Candidate sourcing
├── screening/            # Stage 3: Screening
├── outreach/             # Stage 4: Outreach
├── prescreening/         # Stage 5: Prescreening
├── interview/            # Stage 6: AI Interview
├── evaluation/           # Stage 7: Evaluation
├── offer/                # Stage 8: Offer management
├── onboarding/           # Stage 9: Onboarding
├── analytics/            # Stage 10: Analytics
└── shared/               # Common utilities
```

## 🛠️ Troubleshooting

**Container Issues:**
```bash
# If you get network conflicts or container name conflicts:
docker-compose down
docker network prune -f
docker rm -f recruitment-rabbitmq recruitment-postgres recruitment-redis

# Then restart services
docker-compose up -d postgres rabbitmq redis

# Check service logs
docker-compose logs postgres
docker-compose logs rabbitmq
docker-compose logs redis

# Reset all data
docker-compose down -v
docker-compose up -d
```

**Database Issues:**
```bash
# SQLite (default)
rm data/recruitment.db
python main.py  # Will recreate tables

# PostgreSQL 
docker-compose restart postgres
```

**Port Conflicts:**
- PostgreSQL: 5432
- RabbitMQ: 5672, 15672  
- Redis: 6379
- Main app: 8000
- Interview app: 5173

## 📧 Email Configuration

For production email sending, add to `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=hr@yourcompany.com
FROM_NAME=HR Team
```

## 🎉 Demo Workflow

1. **View Dashboard**: http://localhost:8000
2. **Check Sample Data**: Navigate through Stage 1-8 tabs
3. **Test Offers**: Click "Accept Offer" in Stage 8
4. **Monitor Events**: Check RabbitMQ management UI
5. **Try Interview**: Visit http://localhost:5173 (if running)

---

**Status**: 76.9% Complete | **Last Updated**: April 2026