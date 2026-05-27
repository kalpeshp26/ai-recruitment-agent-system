"""
--- FILE: backend/models/rl.py ---

RL-related ORM models: rl_q_table and rl_attempt_log.
Includes `epsilon` column on rl_q_table to persist per-user epsilon.
"""
from datetime import datetime

from sqlalchemy import Column, Float, Integer, String, func, Text
from sqlalchemy.orm import relationship

from backend.database.base import Base


class RLQTable(Base):
    """Tabular Q-table storing Q-values per user/state/action.

    Primary key: (user_id, state, action)
    An `epsilon` column persists exploration parameter per user/state.
    """

    __tablename__ = "rl_q_table"

    user_id = Column(String(36), primary_key=True)
    state = Column(String(128), primary_key=True)
    action = Column(String(16), primary_key=True)
    q_value = Column(Float, nullable=False, default=0.1)
    visit_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(String, nullable=False, server_default=func.now())
    epsilon = Column(Float, nullable=False, default=0.3)

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<RLQTable user={self.user_id} state={self.state} action={self.action} q={self.q_value}>"


class RLAttemptLog(Base):
    """Per-question RL attempt history for analytics and replay."""

    __tablename__ = "rl_attempt_log"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    session_id = Column(String(36), nullable=False)
    question_id = Column(String(36), nullable=True)
    difficulty = Column(String(8), nullable=False)
    state_before = Column(String(128), nullable=False)
    action_taken = Column(String(16), nullable=False)
    reward = Column(Float, nullable=False)
    state_after = Column(String(128), nullable=False)
    response_time = Column(Integer, nullable=False)
    is_correct = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False, server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<RLAttemptLog id={self.id} user={self.user_id} action={self.action_taken} reward={self.reward}>"
