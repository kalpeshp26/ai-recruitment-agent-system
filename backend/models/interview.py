"""
--- FILE: backend/models/interview.py ---

ORM models for interview-related tables based on docs/INTERVIEW_DATABASE_SCHEMA.md.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.database.base import Base
from backend.config import settings

# Choose JSON type: prefer JSONB for Postgres, fallback to generic JSON
try:
    from sqlalchemy import JSON

    JSON_TYPE = JSON
except Exception:  # pragma: no cover - defensive
    JSON_TYPE = Text


def _json_type():
    """Return the appropriate JSON column type for the configured DB."""
    if settings.DATABASE_URL.startswith("postgresql"):
        return JSONB
    return JSON_TYPE


class InterviewSession(Base):
    """Represents a candidate interview session."""

    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    role = Column(String(64), nullable=False)
    start_time = Column(String, nullable=False, server_default=func.now())
    end_time = Column(String, nullable=True)
    status = Column(String(32), nullable=False)
    answer_mode = Column(String(16), nullable=False)
    current_question_index = Column(Integer, nullable=False, default=0)
    total_score = Column(Integer, nullable=True)
    warning_count = Column(Integer, nullable=False, default=0)
    session_token = Column(Text, unique=True, nullable=False)
    last_activity_at = Column(String, nullable=False, server_default=func.now())

    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete")
    evaluation = relationship("InterviewEvaluation", uselist=False, back_populates="session")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<InterviewSession id={self.id} user_id={self.user_id} status={self.status}>"


class InterviewQuestion(Base):
    """Stores generated questions for a session."""

    __tablename__ = "interview_questions"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    difficulty = Column(String(8), nullable=False)
    category = Column(String(64), nullable=True)
    time_limit = Column(Integer, nullable=False, default=120)
    question_index = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("difficulty IN ('easy','medium','hard')", name="ck_question_difficulty"),
    )

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("InterviewAnswer", uselist=False, back_populates="question", cascade="all, delete")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<InterviewQuestion id={self.id} idx={self.question_index} diff={self.difficulty}>"


class InterviewAnswer(Base):
    """Stores candidate answers and LLM scores."""

    __tablename__ = "interview_answers"

    id = Column(String(36), primary_key=True)
    question_id = Column(String(36), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=True)
    answer_audio_url = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    scores = Column(_json_type(), nullable=False)
    response_time = Column(Integer, nullable=False)
    is_skipped = Column(Boolean, nullable=False, default=False)
    submitted_at = Column(String, nullable=False, server_default=func.now())

    question = relationship("InterviewQuestion", back_populates="answer")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<InterviewAnswer id={self.id} question_id={self.question_id} skipped={self.is_skipped}>"


class InterviewEvaluation(Base):
    """Aggregated session evaluation and final scores."""

    __tablename__ = "interview_evaluation"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    technical_score = Column(Integer, nullable=False)
    communication_score = Column(Integer, nullable=False)
    confidence_score = Column(Integer, nullable=False)
    problem_solving_score = Column(Integer, nullable=False)
    total_score = Column(Integer, nullable=False)
    penalty_points = Column(Integer, nullable=False, default=0)
    final_score = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, server_default=func.now())

    session = relationship("InterviewSession", back_populates="evaluation")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<InterviewEvaluation id={self.id} session_id={self.session_id} final={self.final_score}>"


class ProctoringViolation(Base):
    """Records proctoring events tied to sessions."""

    __tablename__ = "proctoring_violations"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    timestamp = Column(String, nullable=False, server_default=func.now())
    screenshot_url = Column(Text, nullable=True)
    warning_number = Column(Integer, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<ProctoringViolation id={self.id} session={self.session_id} warning={self.warning_number}>"
