"""
--- FILE: backend/rl_engine/q_learning.py ---

Q-learning orchestration: select_action, update_q_table, decay_epsilon.
"""
import random
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.rl_engine.q_table_store import get_q_values, update_q_value, get_epsilon, update_epsilon

logger = logging.getLogger(__name__)

ALPHA = float(settings.RL_ALPHA)
GAMMA = float(settings.RL_GAMMA)
EPSILON_MIN = float(settings.RL_EPSILON_MIN)
EPSILON_DECAY = float(settings.RL_EPSILON_DECAY)

ACTIONS = ["increase", "same", "decrease"]


async def select_action(db: AsyncSession, user_id: str, state_key: str) -> str:
    """Select an action using epsilon-greedy policy.

    Returns the chosen action string.
    """
    eps = await get_epsilon(db, user_id)
    q_values = await get_q_values(db, user_id, state_key)

    if random.random() < eps:
        action = random.choice(ACTIONS)
        return action

    # Greedy: pick highest q-value (tie-breaker random)
    max_q = max(q_values.values())
    best = [a for a, q in q_values.items() if q == max_q]
    return random.choice(best)


async def update_q_table(db: AsyncSession, user_id: str, state_key: str, action: str, reward: float, next_state_key: str) -> float:
    """Perform Bellman update and persist new Q-value.

    Returns the updated q_value.
    """
    # Read current q
    q_values = await get_q_values(db, user_id, state_key)
    current_q = float(q_values.get(action, settings.RL_OPTIMISTIC_INIT))

    # Read max next q
    next_q_values = await get_q_values(db, user_id, next_state_key)
    max_next_q = max(next_q_values.values()) if next_q_values else settings.RL_OPTIMISTIC_INIT

    new_q = current_q + ALPHA * (reward + GAMMA * max_next_q - current_q)

    await update_q_value(db, user_id, state_key, action, new_q)
    return float(new_q)


async def decay_epsilon(db: AsyncSession, user_id: str) -> float:
    """Decay epsilon for a user and persist it to DB.

    Returns the new epsilon value.
    """
    eps = await get_epsilon(db, user_id)
    new_eps = max(EPSILON_MIN, eps * EPSILON_DECAY)
    await update_epsilon(db, user_id, new_eps)
    return float(new_eps)
