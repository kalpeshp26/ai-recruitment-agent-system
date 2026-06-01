"""
--- FILE: backend/rl_engine/q_table_store.py ---

Persistence helpers for the Q-table. Callers are responsible for committing
transactions where appropriate.
"""
import logging
from typing import Dict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.rl import RLQTable

logger = logging.getLogger(__name__)


async def get_q_values(db: AsyncSession, user_id: str, state_key: str) -> Dict[str, float]:
    """Return a dict mapping action -> q_value for the given user and state.

    If no rows exist for the state, return optimistic default for all actions.
    The caller should not commit; this is a read-only helper.
    """
    q = select(RLQTable).where(RLQTable.user_id == user_id, RLQTable.state == state_key)
    res = await db.execute(q)
    rows = res.scalars().all()
    if not rows:
        return {"increase": settings.RL_OPTIMISTIC_INIT, "same": settings.RL_OPTIMISTIC_INIT, "decrease": settings.RL_OPTIMISTIC_INIT}
    return {r.action: float(r.q_value) for r in rows}


async def update_q_value(db: AsyncSession, user_id: str, state_key: str, action: str, new_q_value: float) -> None:
    """Update or insert a q_value row for (user_id, state_key, action).

    Caller is responsible for committing the transaction.
    """
    try:
        q = select(RLQTable).where(RLQTable.user_id == user_id, RLQTable.state == state_key, RLQTable.action == action)
        res = await db.execute(q)
        row = res.scalar_one_or_none()
        if row:
            stmt = (
                update(RLQTable)
                .where(RLQTable.user_id == user_id, RLQTable.state == state_key, RLQTable.action == action)
                .values(q_value=new_q_value, visit_count=RLQTable.visit_count + 1)
            )
            await db.execute(stmt)
        else:
            new = RLQTable(user_id=user_id, state=state_key, action=action, q_value=new_q_value, visit_count=1)
            db.add(new)
    except Exception as e:  # pragma: no cover - DB failure should not crash caller
        logger.exception("Failed to update q_value: %s", e)
        raise


async def get_epsilon(db: AsyncSession, user_id: str) -> float:
    """Read epsilon for a user from the RLQTable if present; otherwise return start value."""
    q = select(RLQTable).where(RLQTable.user_id == user_id).limit(1)
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if row is None:
        return float(settings.RL_EPSILON_START)
    return float(row.epsilon or settings.RL_EPSILON_START)


async def update_epsilon(db: AsyncSession, user_id: str, new_epsilon: float) -> None:
    """Persist epsilon for a user. If rows exist, update their epsilon; otherwise insert a sentinel row.

    Caller is responsible for committing the transaction.
    """
    try:
        q = select(RLQTable).where(RLQTable.user_id == user_id).limit(1)
        res = await db.execute(q)
        row = res.scalar_one_or_none()
        if row:
            stmt = update(RLQTable).where(RLQTable.user_id == user_id).values(epsilon=new_epsilon)
            await db.execute(stmt)
        else:
            # Insert sentinel row so epsilon persists
            new = RLQTable(user_id=user_id, state="__init__", action="same", q_value=settings.RL_OPTIMISTIC_INIT, visit_count=0, epsilon=new_epsilon)
            db.add(new)
    except Exception as e:  # pragma: no cover - ensure callers handle commit
        logger.exception("Failed to update epsilon: %s", e)
        raise
