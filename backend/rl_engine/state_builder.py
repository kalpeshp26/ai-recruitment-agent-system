"""
--- FILE: backend/rl_engine/state_builder.py ---

Build RL state keys from recent attempts and current difficulty.
"""
from typing import Dict, List, Tuple, Any


def build_state(attempts: List[Dict[str, Any]], current_difficulty: str) -> Tuple[str, Dict[str, Any]]:
    """Build a state key and structured state from recent attempts.

    The state key format is: "difficulty|correct_streak|wrong_streak|response_time_bin|topic_accuracy_bin".

    - Fixes the None==None topic bug by handling current_topic is None.
    - Streaks are capped at 5.
    - Response time bins: ratio <0.4 -> fast, 0.4-0.7 -> medium, 0.7-0.9 -> slow, >0.9 -> very_slow

    Args:
        attempts: list of recent attempt dicts. Each attempt may contain
                  keys: "is_correct" (bool), "response_time" (ms), "time_limit" (s), "topic" (str).
        current_difficulty: current difficulty string ('easy'|'medium'|'hard').

    Returns:
        Tuple[state_key, state_dict]
    """
    # default counters
    correct_streak = 0
    wrong_streak = 0

    for a in reversed(attempts):
        if a.get("is_correct"):
            correct_streak += 1
            wrong_streak = 0
        else:
            wrong_streak += 1
            correct_streak = 0
        if correct_streak >= 5 or wrong_streak >= 5:
            break

    # cap streaks
    correct_streak = min(correct_streak, 5)
    wrong_streak = min(wrong_streak, 5)

    # response time ratio from last attempt if available
    if attempts:
        last = attempts[-1]
        rt_ms = last.get("response_time") or 0
        time_limit = last.get("time_limit") or 120
        # convert to seconds for ratio
        try:
            ratio = (rt_ms / 1000.0) / float(time_limit)
        except Exception:
            ratio = 0.5
    else:
        ratio = 0.5

    if ratio < 0.4:
        response_time_bin = "fast"
    elif ratio < 0.7:
        response_time_bin = "medium"
    elif ratio <= 0.9:
        response_time_bin = "slow"
    else:
        response_time_bin = "very_slow"

    # Topic accuracy: compute accuracy across attempts filtered by topic
    if attempts:
        current_topic = attempts[-1].get("topic")
        if current_topic is None:
            topic_attempts = attempts
        else:
            topic_attempts = [a for a in attempts if a.get("topic") == current_topic]
        if topic_attempts:
            correct = sum(1 for a in topic_attempts if a.get("is_correct"))
            acc = correct / len(topic_attempts)
        else:
            acc = 1.0
    else:
        acc = 1.0

    if acc >= 0.8:
        topic_accuracy_bin = "high"
    elif acc >= 0.5:
        topic_accuracy_bin = "medium"
    else:
        topic_accuracy_bin = "low"

    state = {
        "difficulty": current_difficulty,
        "correct_streak": correct_streak,
        "wrong_streak": wrong_streak,
        "response_time_bin": response_time_bin,
        "topic_accuracy_bin": topic_accuracy_bin,
    }

    state_key = f"{current_difficulty}|{correct_streak}|{wrong_streak}|{response_time_bin}|{topic_accuracy_bin}"
    return state_key, state
