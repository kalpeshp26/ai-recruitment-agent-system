import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import engine
from app.database.base import Base
# Import the user model directly and only create the tables required for
# authentication when running locally with SQLite. Many tables use
# PostgreSQL-specific types (JSONB) which SQLite cannot compile.
from app.models.user import User
from app.models.assessment import AssessmentSession, AssessmentRound
# Aptitude models (exclude RLSession which uses JSONB)
from app.models.aptitude import AptitudeTopic, AptitudeQuestion, AptitudeAttempt


def init_db():
    print("Initializing minimal database tables for auth (users)...")
    # Create a minimal set of tables usable with SQLite for local testing:
    # - users: authentication
    # - assessment_sessions, assessment_rounds: session lifecycle
    # - aptitude_topics, aptitude_questions, aptitude_attempts: basic aptitude
    tables = [
        User.__table__,
        AssessmentSession.__table__,
        AssessmentRound.__table__,
        AptitudeTopic.__table__,
        AptitudeQuestion.__table__,
        AptitudeAttempt.__table__,
    ]

    Base.metadata.create_all(bind=engine, tables=tables)
    print("Users table created successfully!")

if __name__ == "__main__":
    init_db()
