"""Light end-to-end test for the Interview API.
Runs against http://127.0.0.1:8000 by default and exercises /health, /start, /next-question, /submit-answer, /end.
"""
import time
import json
import os
from pathlib import Path
import httpx
from jose import jwt

API_BASE = "http://127.0.0.1:8000"


def load_secret() -> str:
    """Load JWT secret from the environment or the local .env file."""
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "JWT_SECRET":
                return value.split("#", 1)[0].strip()

    return "changeme"

def make_token(user_id: str):
    return jwt.encode({"sub": user_id}, load_secret(), algorithm="HS256")

def wait_for_health(timeout=10):
    url = f"{API_BASE}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run():
    print("Waiting for server health...")
    ok = wait_for_health(15)
    if not ok:
        print("Server did not become healthy")
        return 1

    # Start interview (public)
    start_url = f"{API_BASE}/api/v1/interview/start"
    payload = {"role": "engineer", "answer_mode": "text", "preferred_language": "en"}
    r = httpx.post(start_url, json=payload, timeout=5.0)
    print("/start ->", r.status_code, r.text)
    if r.status_code != 201:
        return 2
    data = r.json()
    session_id = data.get("session_id")
    token = data.get("session_token")
    # Also create a JWT for auth endpoints
    jwt_token = make_token(f"user-engineer")

    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Fetch next question
    next_url = f"{API_BASE}/api/v1/interview/session/{session_id}/next-question"
    r = httpx.get(next_url, headers=headers, timeout=5.0)
    print("/next-question ->", r.status_code, r.text)
    if r.status_code != 200:
        return 3
    q = r.json()
    question_id = q.get("question_id")

    # Submit an answer
    submit_url = f"{API_BASE}/api/v1/interview/session/{session_id}/submit-answer"
    submit_payload = {"question_id": question_id, "answer_text": "This is a test answer.", "response_time_ms": 1200, "client_request_id": "test-1"}
    r = httpx.post(submit_url, json=submit_payload, headers=headers, timeout=5.0)
    print("/submit-answer ->", r.status_code, r.text)
    if r.status_code != 200:
        return 4

    # End session
    end_url = f"{API_BASE}/api/v1/interview/session/{session_id}/end"
    r = httpx.post(end_url, json={"reason": "test_complete"}, headers=headers, timeout=5.0)
    print("/end ->", r.status_code, r.text)
    if r.status_code != 200:
        return 5

    # Get result
    res_url = f"{API_BASE}/api/v1/interview/session/{session_id}/result"
    r = httpx.get(res_url, headers=headers, timeout=5.0)
    print("/result ->", r.status_code, r.text)
    return 0

if __name__ == '__main__':
    raise SystemExit(run())
