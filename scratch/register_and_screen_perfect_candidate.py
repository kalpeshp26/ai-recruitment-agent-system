import json
import sqlite3
import os
import sys

# Add root folder to sys.path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.db.database import get_db_sync
from shared.db.models import Candidate, Job, Application
from screening.processor import process_candidate

db_gen = get_db_sync()
db_session = next(db_gen)

try:
    # 1. Fetch any Python Developer job
    job = db_session.query(Job).filter(Job.title == "Python Developer").first()
    if not job:
        print("Error: No Python Developer job found in database.")
        sys.exit(1)
        
    print(f"Targeting Job ID: {job.id} | Title: {job.title}")
    
    # 2. Perfect Resume Content
    raw_resume = """JOHN DOE
Email: johndoe.perfect@gmail.com
Phone: +91 98765 43210
Location: Pune, India

SUMMARY:
Accomplished Senior Python Developer with 6 years of experience designing and deploying high-performance microservices, REST APIs, and containerized cloud applications. Proven track record in FastAPI backend orchestration, relational SQL databases, and automated containerization with Docker.

EDUCATION:
Bachelor of Technology (B.Tech) in Computer Science and Engineering (CSE)

TECHNICAL SKILLS:
Python, SQL, FastAPI, Docker, REST APIs, PostgreSQL, Git

EXPERIENCE:
Senior Python Developer | TopTech Solutions, Pune (June 2020 - Present)
- Architected and built production-grade REST APIs using Python and FastAPI framework.
- Designed and optimized relational databases with PostgreSQL and complex SQL queries.
- Deployed microservices into production using Docker containers and Kubernetes.
- Led a team of software developers to successfully deliver next-generation systems.

PROJECTS:
1. Python API Portal:
   Designed and developed a developer portal backend using Python and FastAPI, querying SQL databases and containerized with Docker.
2. Database Sync Utility:
   Built a high-performance Python utility utilizing SQL for data synchronization between disparate enterprise databases.
"""

    # 3. Create Candidate ORM Object
    candidate = Candidate(
        name="John Doe",
        email="johndoe.perfect@gmail.com",
        phone="+919876543210",
        location="Pune",
        current_role="Senior Python Developer",
        experience_years=6.0,
        skills=json.dumps(["python", "sql", "fastapi", "docker"]),
        education="Bachelor of Technology in Computer Science and Engineering",
        work_history=json.dumps([
            {
                "company": "TopTech Solutions",
                "role": "Senior Python Developer",
                "duration": "2020 - 2026",
                "skills": ["python", "sql", "fastapi", "docker"],
                "description": "Led backend Python microservices using FastAPI, SQL, and Docker."
            }
        ]),
        parsed_data=json.dumps({
            "projects": [
                {"name": "Python API Portal", "description": "Python, FastAPI, SQL, Docker project."},
                {"name": "Database Sync Utility", "description": "Python database utility with SQL."}
            ]
        }),
        raw_resume_text=raw_resume,
        job_id=job.id,
        status="new"
    )
    
    db_session.add(candidate)
    db_session.commit()
    print(f"Created Candidate: {candidate.name} | ID: {candidate.id}")
    
    # 4. Create an Application row
    app = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        status="applied"
    )
    db_session.add(app)
    db_session.commit()
    
    # 5. Screen candidate using processor
    result = process_candidate(candidate.id, db_session)
    print("Screening completed:", result)
    
    db_session.refresh(candidate)
    print(f"Candidate Final Score: {candidate.score}")
    print(f"Candidate Status: {candidate.status}")
    print(f"Candidate Breakdown: {candidate.score_breakdown}")
    
except Exception as e:
    db_session.rollback()
    print("Error:", e)
finally:
    try:
        next(db_gen)
    except StopIteration:
        pass
