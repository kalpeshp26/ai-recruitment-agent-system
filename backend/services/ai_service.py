"""
--- FILE: backend/services/ai_service.py ---

AI service wrapping Groq model calls for question generation, answer
evaluation, and session summarization. Falls back to local prompts when
provider calls fail or return invalid responses.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings
from backend.prompts import (
    P1_SYSTEM_MESSAGE,
    P1_USER_TEMPLATE,
    P1_OUTPUT_SCHEMA,
    P2_SYSTEM_MESSAGE,
    P2_USER_TEMPLATE,
    P2_OUTPUT_SCHEMA,
    P5_SYSTEM_MESSAGE,
    P5_USER_TEMPLATE,
    P5_OUTPUT_SCHEMA,
    P7_SYSTEM_MESSAGE,
    P7_USER_TEMPLATE,
    P7_OUTPUT_SCHEMA,
    P9_SYSTEM_MESSAGE,
    P9_USER_TEMPLATE,
    P9_OUTPUT_SCHEMA,
    FALLBACK_QUESTIONS,
)

logger = logging.getLogger(__name__)

GROQ_ENDPOINT = "https://api.groq.com/v1/generate"


def _strip_md_fences(text: str) -> str:
    """Remove Markdown code fences from a model response before JSON parse."""
    if text is None:
        return ""
    return text.replace("```json", "").replace("```", "").strip()


async def _call_groq(payload: Dict[str, Any], timeout: float = 10.0) -> Optional[str]:
    """Call Groq generation/eval endpoint and return raw text response or None on failure."""
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"} if settings.GROQ_API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(GROQ_ENDPOINT, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Provider shape may vary; attempt common keys
            text = data.get("text") or data.get("choices", [{}])[0].get("text") or json.dumps(data)
            return text
    except Exception as e:
        logger.exception("Groq call failed: %s", e)
        return None


async def generate_question(role: str,
                            difficulty: str,
                            category: Optional[str],
                            conversation_history: List[Dict[str, str]],
                            session_id: str) -> Dict[str, Any]:
    """Generate a question using Groq or fallback.

    Returns a dict with keys: question_text, difficulty, category, time_limit, metadata
    """
    # Prepare history (last 3)
    history = conversation_history[-3:] if conversation_history else []

    # Choose prompt template based on category
    if category == "hr":
        system = P1_SYSTEM_MESSAGE
        user_template = P1_USER_TEMPLATE
        temp = settings.GROQ_TEMP_GEN
        max_tokens = 256
    else:
        system = P2_SYSTEM_MESSAGE
        user_template = P2_USER_TEMPLATE
        temp = settings.GROQ_TEMP_GEN
        max_tokens = 512

    user_payload = user_template.format(role=role, difficulty_hint=difficulty, category=category or "", last_q=(history[-1]["q"] if history else ""), last_a_summary=(history[-1].get("a_summary") if history else ""))

    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": temp,
        "max_tokens": max_tokens,
        "system": system,
        "user": user_payload,
    }

    resp_text = await _call_groq(payload, timeout=15.0)
    if resp_text:
        try:
            clean = _strip_md_fences(resp_text)
            parsed = json.loads(clean)
            # ensure minimal keys
            question_text = parsed.get("question_text")
            if question_text:
                return {"question_text": question_text.strip(),
                        "difficulty": parsed.get("difficulty") or difficulty,
                        "category": parsed.get("category") or category,
                        "time_limit": parsed.get("time_limit") or 120,
                        "metadata": parsed.get("metadata") or {"source": "groq"}}
        except Exception:
            logger.exception("Failed to parse Groq generation response; falling back")

    # Fallback: pick from local bank
    fallback_list = FALLBACK_QUESTIONS.get(difficulty, FALLBACK_QUESTIONS.get("medium"))
    idx = hash(session_id) % len(fallback_list)
    return {"question_text": fallback_list[idx], "difficulty": difficulty, "category": category or "general", "time_limit": 120, "metadata": {"source": "fallback"}}


async def evaluate_answer(question: str, answer: str, difficulty: str, role: str, time_taken_ms: int) -> Dict[str, Any]:
    """Evaluate an answer using Groq; return structured dict.

    Returns: {technical, communication, confidence, problem_solving, feedback, is_correct}
    """
    if not answer or answer.strip() == "":
        return {"technical": 0.0, "communication": 0.0, "confidence": 0.0, "problem_solving": 0.0, "total": 0.0, "is_correct": False, "feedback": {"technical":"","communication":"","confidence":"","problem_solving":""}, "summary": ""}

    # Build a JSON payload dict rather than using string.format on a template
    user_payload_obj = {
        "question_text": question,
        "expected_keywords": ["", ""],
        "answer_text": answer,
        "transcript": answer,
        "time_taken_ms": time_taken_ms,
        "role": role,
    }
    user_payload = json.dumps(user_payload_obj)
    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": settings.GROQ_TEMP_EVAL,
        "max_tokens": settings.GROQ_MAX_TOKENS_EVAL,
        "system": P5_SYSTEM_MESSAGE,
        "user": user_payload,
    }

    resp_text = await _call_groq(payload, timeout=20.0)
    if resp_text:
        try:
            clean = _strip_md_fences(resp_text)
            parsed = json.loads(clean)
            # validate numeric fields
            technical = float(parsed.get("technical", 5.0))
            communication = float(parsed.get("communication", 5.0))
            confidence = float(parsed.get("confidence", 5.0))
            problem_solving = float(parsed.get("problem_solving", 5.0))
            total = float(parsed.get("total", (technical * 0.4 + communication * 0.2 + confidence * 0.2 + problem_solving * 0.2)))
            is_correct = bool(parsed.get("is_correct", technical >= 6.0))
            feedback = parsed.get("feedback", {})
            summary = parsed.get("summary", "")
            return {"technical": technical, "communication": communication, "confidence": confidence, "problem_solving": problem_solving, "total": total, "is_correct": is_correct, "feedback": feedback, "summary": summary}
        except Exception:
            logger.exception("Failed to parse Groq evaluation response; using default rubric")
            return {"technical": 5.0, "communication": 5.0, "confidence": 5.0, "problem_solving": 5.0, "total": 5.0, "is_correct": False, "feedback": {"technical":"","communication":"","confidence":"","problem_solving":""}, "summary": ""}

    # On AI failure
    return {"technical": 5.0, "communication": 5.0, "confidence": 5.0, "problem_solving": 5.0, "total": 5.0, "is_correct": False, "feedback": {"technical":"","communication":"","confidence":"","problem_solving":""}, "summary": ""}


async def generate_session_summary(qa_summaries: List[Dict[str, Any]], final_score: float, role: str) -> str:
    """Generate a 2-3 sentence candidate-facing session summary via Groq (P7).

    Returns a short string summary; on failure returns a simple templated summary.
    """
    user_payload = P7_USER_TEMPLATE.format(session_id="session", qa_summaries=json.dumps(qa_summaries))
    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": 0.3,
        "max_tokens": 512,
        "system": P7_SYSTEM_MESSAGE,
        "user": user_payload,
    }

    resp_text = await _call_groq(payload, timeout=10.0)
    if resp_text:
        try:
            clean = _strip_md_fences(resp_text)
            parsed = json.loads(clean)
            summary = parsed.get("summary") or parsed.get("short_feedback") or ""
            if summary:
                # Return a concise 2-3 sentence summary
                return " ".join(summary.splitlines())
        except Exception:
            logger.exception("Failed to parse Groq session summary; falling back")

    return f"Final score: {final_score:.1f}. Thank you for completing the interview. Expect feedback shortly."
