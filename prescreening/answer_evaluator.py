"""
prescreening/answer_evaluator.py
════════════════════════════════════════════════════════════════════
Stage 5 — AI Answer Evaluation ⭐ Core AI File
Fetches all Q&A pairs for a completed chatbot session, sends each to
Groq LLM for scoring, computes an overall verdict (PASS/BORDERLINE/FAIL),
stores the evaluation report in the scores table, and fires the appropriate
RabbitMQ event to trigger the interview module.

Uses Groq (llama-3.3-70b-versatile) for AI evaluation.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import pika
from dotenv import load_dotenv
from groq import Groq

from shared.db.database import db_session
from shared.db.models import Application, ChatbotAnswer, ChatbotSession, Score
from shared.queue.event_topics import EventTopics

# ─── Env ────────────────────────────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
RABBITMQ_URL      = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
GROQ_MODEL        = "llama-3.3-70b-versatile"

MAX_RETRIES       = 3
BASE_BACKOFF      = 2        # seconds

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("answer_evaluator")

# ─── Groq client (lazy — created on first use) ─────────────────────────────
_groq = None

def _get_groq():
    """Return a cached Groq client, creating it on first call."""
    global _groq
    if _groq is None:
        _groq = Groq(api_key=GROQ_API_KEY)
    return _groq

# Score mapping
SCORE_MAP = {"Excellent": 4, "Good": 3, "Average": 2, "Poor": 1}


# ─────────────────────────────────────────────────────────────────────────────
# GROQ LLM EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_single_answer(question: str, answer: str) -> dict:
    """
    Send one Q&A pair to Groq LLM for evaluation.
    Returns dict: {score, disqualified, reason}
    Implements exponential-backoff retry on rate-limit errors.
    """
    system_prompt = (
        "You are an expert HR evaluator reviewing candidate pre-screening answers. "
        "Score the answer on a scale: Excellent, Good, Average, or Poor. "
        "Also flag if the answer contains a knockout disqualifier, for example: "
        "notice period more than 90 days, salary expectation more than 30% above budget, "
        "or explicit lack of required experience. "
        "Return ONLY a valid JSON object with exactly these keys: "
        "{\"score\": \"Excellent|Good|Average|Poor\", \"disqualified\": true|false, \"reason\": \"brief explanation\"}"
    )
    user_message = f"Question: {question}\nCandidate Answer: {answer}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _get_groq().chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=256,
            )
            text = response.choices[0].message.content.strip()
            
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            result = json.loads(text.strip())
            
            # Normalize field names
            return {
                "score":        result.get("score", "Average"),
                "disqualified": bool(result.get("disqualified", False)),
                "reason":       result.get("reason", ""),
            }
        except Exception as exc:
            # Check if it's a rate limit error
            if "rate_limit" in str(exc).lower() or "429" in str(exc):
                wait = BASE_BACKOFF ** attempt
                log.warning("Groq rate limit hit (attempt %d/%d). Waiting %ds.", attempt, MAX_RETRIES, wait)
                time.sleep(wait)
            elif "json" in str(exc).lower():
                log.error("JSON parse error from Groq response: %s", exc)
                return {"score": "Average", "disqualified": False, "reason": "Parse error"}
            else:
                log.error("Groq API error on attempt %d: %s", attempt, exc)
                time.sleep(BASE_BACKOFF ** attempt)

    # All retries exhausted — default to Average/not disqualified
    log.error("All %d retries exhausted for question: %s", MAX_RETRIES, question[:80])
    return {"score": "Average", "disqualified": False, "reason": "Evaluation unavailable"}


# ─────────────────────────────────────────────────────────────────────────────
# RABBITMQ PUBLISHER
# ─────────────────────────────────────────────────────────────────────────────

def _publish_event(topic: str, payload: dict):
    """Publish a single RabbitMQ event on the given topic."""
    try:
        params     = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel    = connection.channel()
        channel.queue_declare(queue=topic, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=topic,
            body=json.dumps(payload).encode(),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        connection.close()
        log.info("Published event '%s': %s", topic, payload)
    except Exception as exc:
        log.error("RabbitMQ publish error for topic '%s': %s", topic, exc)


# ─────────────────────────────────────────────────────────────────────────────
# CORE EVALUATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_session(session_id: str) -> dict:
    """
    Main entry point — called after chatbot session COMPLETED.
    1. Fetch all Q&A pairs
    2. Score each with Groq LLM
    3. Determine verdict (PASS / BORDERLINE / FAIL)
    4. Store in scores table
    5. Publish RabbitMQ event
    Returns the evaluation summary dict.
    """
    log.info("Starting evaluation for session %s", session_id)

    with db_session() as db:
        session = db.query(ChatbotSession).filter_by(session_id=session_id).first()
        if not session:
            log.error("Session %s not found", session_id)
            return {}

        answers = (
            db.query(ChatbotAnswer)
            .filter_by(session_id=session_id)
            .order_by(ChatbotAnswer.question_index)
            .all()
        )

        if not answers:
            log.warning("No answers found for session %s", session_id)
            return {}

        # ── Evaluate each answer ─────────────────────────────────────────────
        eval_results   = []
        disqualified   = False
        disq_reason    = ""

        for ans in answers:
            result = _evaluate_single_answer(ans.question, ans.answer)
            eval_results.append({
                "question_index": ans.question_index,
                "question":       ans.question,
                "answer":         ans.answer,
                "score":          result["score"],
                "disqualified":   result["disqualified"],
                "reason":         result["reason"],
            })

            # Update the answer record with AI score
            ans.ai_score    = result["score"]
            ans.disqualified= result["disqualified"]
            ans.reason      = result["reason"]

            if result["disqualified"]:
                disqualified = True
                disq_reason  = result["reason"]

        # ── Compute verdict ──────────────────────────────────────────────────
        numeric_scores = [SCORE_MAP.get(r["score"], 2) for r in eval_results]
        avg_score      = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0

        if disqualified:
            verdict = "FAIL"
            rejection_reason = disq_reason
        elif avg_score >= 2.5:
            verdict = "PASS"
            rejection_reason = None
        elif avg_score >= 2.0:
            verdict = "BORDERLINE"
            rejection_reason = f"Average score {avg_score:.2f} — borderline case"
        else:
            verdict = "FAIL"
            rejection_reason = f"Average score {avg_score:.2f} — below threshold"

        log.info(
            "Session %s → verdict=%s, avg_score=%.2f, disqualified=%s",
            session_id, verdict, avg_score, disqualified,
        )

        # ── Get application ──────────────────────────────────────────────────
        app = (
            db.query(Application)
            .filter_by(candidate_id=session.candidate_id, job_id=session.job_id)
            .first()
        )

        # ── Store in scores table ────────────────────────────────────────────
        score_record = Score(
            job_id           = session.job_id,
            candidate_id     = session.candidate_id,
            overall_score    = avg_score,
            skill_match      = avg_score,
            scoring_algorithm= "prescreening_ai",
        )
        db.add(score_record)

        # ── Update application stage ─────────────────────────────────────────
        if app:
            app.stage  = 5
            app.status = "DONE"

        # Fetch candidate name, email and job title before committing/closing
        from shared.db.models import Candidate, Job
        candidate = db.query(Candidate).filter_by(id=session.candidate_id).first()
        job = db.query(Job).filter_by(id=session.job_id).first()
        
        candidate_id = session.candidate_id
        job_id = session.job_id
        candidate_name = candidate.name if candidate else None
        candidate_email = candidate.email if candidate else None
        job_title = job.title if job else None
        app_id = app.id if app else None

        db.commit()

    # ── Publish RabbitMQ event and Auto-Create Interview Session ─────────────
    event_payload = {
        "candidate_id": str(candidate_id),
        "job_id":       str(job_id),
        "application_id": app_id,
        "session_id":   session_id,
        "verdict":      verdict,
        "avg_score":    round(avg_score, 2),
    }

    if verdict in ["PASS", "BORDERLINE"]:
        # ═══════════════════════════════════════════════════════════════
        # AUTO-CREATE INTERVIEW SESSION AND SEND INVITATION EMAIL
        # ═══════════════════════════════════════════════════════════════
        try:
            from interview.session_manager import create_interview_session
            from interview.interview_email_sender import send_interview_invitation_email
            from datetime import datetime, timedelta

            if candidate_name and candidate_email and job_title:
                # Create interview session
                interview_session = create_interview_session(
                    candidate_id=str(candidate_id),
                    job_id=str(job_id),
                    candidate_name=candidate_name,
                    candidate_email=candidate_email,
                    job_title=job_title
                )

                if interview_session:
                    log.info(f"✅ Interview session created for {verdict} candidate: {interview_session['session_id']}")

                    event_payload['interview_session_id'] = interview_session['session_id']
                    event_payload['interview_url'] = interview_session['interview_url']

                    # Send interview invitation email
                    deadline = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
                    email_sent = send_interview_invitation_email(
                        candidate_email=candidate_email,
                        candidate_name=candidate_name,
                        job_title=job_title,
                        interview_url=interview_session['interview_url'],
                        completion_deadline=deadline,
                        session_id=interview_session['session_id']
                    )

                    if email_sent:
                        log.info(f"✅ Interview invitation email sent to {candidate_email}")
                    else:
                        log.warning(f"⚠️ Failed to send interview email to {candidate_email}")
                else:
                    log.warning(f"⚠️ Failed to create interview session for candidate {candidate_id}")
            else:
                log.warning(f"⚠️ Candidate or Job details missing for session {session_id}")

        except Exception as e:
            log.error(f"❌ Error in auto-interview creation: {e}")
            import traceback
            traceback.print_exc()

        _publish_event(EventTopics.SCREENING_PASSED, event_payload)
    else:
        _publish_event(EventTopics.SCREENING_FAILED, {**event_payload, "rejection_reason": rejection_reason})

    summary = {
        "session_id":    session_id,
        "verdict":       verdict,
        "avg_score":     round(avg_score, 2),
        "disqualified":  disqualified,
        "total_answers": len(eval_results),
        "interview_session_id": event_payload.get("interview_session_id"),
        "interview_url": event_payload.get("interview_url"),
    }
    log.info("Evaluation complete: %s", summary)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python answer_evaluator.py <session_id>")
        sys.exit(1)
    result = evaluate_session(sys.argv[1])
    print(json.dumps(result, indent=2))
