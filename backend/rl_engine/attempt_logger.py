"""
--- FILE: backend/rl_engine/attempt_logger.py ---

Non-blocking logger for RL attempts. Never raises; logs warnings on failure.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.rl import RLAttemptLog

logger = logging.getLogger(__name__)


async def log_attempt(db: AsyncSession,
                      user_id: str,
                      session_id: str,
                      question_id: str | None,
                      difficulty: str,
                      state_before: str,
                      action_taken: str,
                      reward: float,
                      state_after: str,
                      response_time: int,
                      is_correct: bool) -> None:
    """Persist an RL attempt record. This function must not raise.

    Any exception is caught and logged; callers should continue.
    """
    try:
        entry = RLAttemptLog(
            id="",
            user_id=user_id,
            session_id=session_id,
            question_id=question_id,
            difficulty=difficulty,
            state_before=state_before,
            action_taken=action_taken,
            reward=reward,
            state_after=state_after,
            response_time=response_time,
            is_correct=1 if is_correct else 0,
        )
        db.add(entry)
    except Exception:  # pragma: no cover - must swallow errors
        logger.exception("Failed to log RL attempt; continuing")
        return
