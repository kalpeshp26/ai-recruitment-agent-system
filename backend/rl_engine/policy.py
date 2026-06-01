"""
--- FILE: backend/rl_engine/policy.py ---

Policy utilities to enforce valid difficulty transitions and policy guards.
"""
from typing import Literal

VALID_TRANSITIONS = {
    "easy": ["easy", "medium"],
    "medium": ["easy", "medium", "hard"],
    "hard": ["medium", "hard"],
}


def apply_policy(difficulty: Literal["easy", "medium", "hard"],
                 action: str,
                 correct_streak: int,
                 wrong_streak: int) -> str:
    """Apply policy guards and return the final action.

    - wrong_streak >= 4 forces 'decrease' (checked before correct_streak).
    - correct_streak >= 5 forces 'increase'.
    - Valid actions are restricted by VALID_TRANSITIONS for the current difficulty.
    - Boundary behavior: decrease at easy stays easy; increase at hard stays hard.
    """
    # Force decrease on long wrong streaks
    if wrong_streak >= 4:
        return "decrease"

    # Force increase on long correct streaks
    if correct_streak >= 5:
        return "increase"

    # Ensure action is one of increase/same/decrease
    if action not in ("increase", "same", "decrease"):
        action = "same"

    allowed = VALID_TRANSITIONS.get(difficulty, ["same"])

    # Map 'increase' at hard to 'same' and 'decrease' at easy to 'same'
    if action == "increase" and "hard" not in allowed:
        return "same"
    if action == "decrease" and "easy" not in allowed:
        return "same"

    if action in allowed:
        return action

    return "same"
