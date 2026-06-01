"""
--- FILE: backend/rl_engine/reward_calculator.py ---

Reward calculator implementing the exact formula from docs.
"""
from typing import Literal

DEFAULT_TIME_LIMIT = 120  # seconds


def calculate_reward(is_correct: bool,
                     difficulty: Literal["easy", "medium", "hard"],
                     response_time_ms: int,
                     time_limit_seconds: int = DEFAULT_TIME_LIMIT,
                     correct_streak: int = 0,
                     wrong_streak: int = 0) -> float:
    """Calculate the RL reward for a single attempt.

    Formula:
      base = (is_correct ? 1.0 : 0.0) scaled by difficulty multiplier
      difficulty multipliers: easy×0.5, medium×1.0, hard×1.5
      time bonus: ratio = response_time / time_limit
        ratio <0.4 -> +0.5
        0.4–0.7 -> +0.2
        0.7–0.9 -> 0
        >0.9 -> -0.3
      streak modifier: correct_streak>=3 -> +0.3; wrong_streak>=3 -> -0.3
      clamp result to [-3.0, +3.0]

    Returns:
        clamped reward as float
    """
    multipliers = {"easy": 0.5, "medium": 1.0, "hard": 1.5}
    multiplier = multipliers.get(difficulty, 1.0)

    # base derived from correctness: map boolean to 1 or 0
    base_score = 1.0 if is_correct else 0.0
    reward_base = base_score * multiplier

    # time bonus
    try:
        ratio = (response_time_ms / 1000.0) / float(time_limit_seconds or DEFAULT_TIME_LIMIT)
    except Exception:
        ratio = 0.5

    if ratio < 0.4:
        time_bonus = 0.5
    elif ratio < 0.7:
        time_bonus = 0.2
    elif ratio <= 0.9:
        time_bonus = 0.0
    else:
        time_bonus = -0.3

    # streak modifier
    streak_mod = 0.0
    if correct_streak >= 3:
        streak_mod += 0.3
    if wrong_streak >= 3:
        streak_mod -= 0.3

    reward = reward_base + time_bonus + streak_mod

    # clamp
    if reward > 3.0:
        reward = 3.0
    if reward < -3.0:
        reward = -3.0
    return float(reward)
