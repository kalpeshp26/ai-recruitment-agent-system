"""
Tests for the Stage 3 Screening Service.

Uses the existing database setup — no separate test database needed.
Run:  python -m pytest tests/test_screening.py -v
"""
import json
import sys
import os
import uuid

import pytest
from shared.db.database import get_db_sync as get_db
from shared.db.models import Candidate, Job


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    """Get a database session for testing."""
    db_gen = get_db()
    session = next(db_gen)
    yield session
    try:
        next(db_gen)
    except StopIteration:
        pass


@pytest.fixture
def sample_job(db_session):
    """Insert a sample job and return it."""
    job = Job(
        title="Python Developer",
        skills=json.dumps(["python", "sql", "fastapi", "docker"]),
        experience_min=3,
        experience_max=5,
        qualification="bachelor's",
        location="Pune",
    )
    db_session.add(job)
    db_session.commit()
    return job


def _make_candidate(job_id, **overrides):
    """Helper to build a Candidate with sane defaults."""
    defaults = {
        "name": "Test Candidate",
        "email": "test@example.com",
        "phone": "1234567890",
        "skills": json.dumps(["python", "sql"]),
        "experience_years": 4.0,
        "education": "bachelor's in computer science",
        "location": "Pune",
        "source": "resume",
        "job_id": job_id,
        "work_history": json.dumps([
            {"company": "TechCorp", "role": "Python Developer", "duration": "4 years", "skills": ["python", "sql"]}
        ]),
    }
    defaults.update(overrides)
    return Candidate(**defaults)


# ── Duplicate Detector Tests ─────────────────────────────────────────────────

class TestDuplicateDetector:

    def test_no_duplicate(self, db_session, sample_job):
        from screening.duplicate_detector import check_duplicate

        c = _make_candidate(sample_job.id, email="unique@example.com")
        db_session.add(c)
        db_session.commit()

        is_dup, original = check_duplicate(c, db_session)
        assert is_dup is False
        assert original is None

    def test_duplicate_by_email(self, db_session, sample_job):
        from screening.duplicate_detector import check_duplicate

        c1 = _make_candidate(sample_job.id, email="alice@example.com", name="Alice A")
        c2 = _make_candidate(sample_job.id, email="alice@example.com", name="Bob B")
        db_session.add_all([c1, c2])
        db_session.commit()

        is_dup, original = check_duplicate(c2, db_session)
        assert is_dup is True
        assert original == c1.id

    def test_duplicate_by_phone(self, db_session, sample_job):
        from screening.duplicate_detector import check_duplicate

        c1 = _make_candidate(sample_job.id, email="a@a.com", phone="9876543210", name="One")
        c2 = _make_candidate(sample_job.id, email="b@b.com", phone="9876543210", name="Two")
        db_session.add_all([c1, c2])
        db_session.commit()

        is_dup, original = check_duplicate(c2, db_session)
        assert is_dup is True
        assert original == c1.id

    def test_duplicate_by_fuzzy_name(self, db_session, sample_job):
        from screening.duplicate_detector import check_duplicate

        c1 = _make_candidate(sample_job.id, email="a@a.com", phone="111", name="Alice Johnson")
        c2 = _make_candidate(sample_job.id, email="b@b.com", phone="222", name="Alice Jhonson")  # typo
        db_session.add_all([c1, c2])
        db_session.commit()

        is_dup, original = check_duplicate(c2, db_session)
        assert is_dup is True
        assert original == c1.id


# ── Scoring Engine Tests ─────────────────────────────────────────────────────

class TestScoringEngine:

    def test_perfect_match(self, db_session, sample_job):
        from screening.scoring_engine import calculate_score
        from unittest.mock import patch

        c = _make_candidate(
            sample_job.id,
            skills=json.dumps(["python", "sql", "fastapi", "docker"]),
            experience_years=5.0,
            education="bachelor's in computer science",
            location="Pune",
            current_role="Python Engineer",
            work_history=json.dumps([
                {"company": "TechCorp", "role": "Python Engineer", "duration": "2020-2025", "skills": ["python", "sql", "fastapi", "docker"]}
            ])
        )
        db_session.add(c)
        db_session.commit()

        with patch("screening.scoring_engine.evaluate_with_llm") as mock_llm:
            mock_llm.return_value = {"score": 100.0, "reason": "Perfect match"}
            total, breakdown = calculate_score(c, sample_job)
            
            assert total == 100
            assert breakdown["skill_match"] == 60
            assert breakdown["experience"] == 10
            assert breakdown["job_title_alignment"] == 10
            assert breakdown["education"] == 15
            assert breakdown["location"] == 5

    def test_partial_skills(self, db_session, sample_job):
        from screening.scoring_engine import calculate_score
        from unittest.mock import patch

        c = _make_candidate(
            sample_job.id,
            skills=json.dumps(["python"]),  # 1 of 4
            experience_years=5.0,
            education="bachelor's in commerce",  # Non-STEM
            location="Pune",
            current_role="Python Developer",
            work_history=json.dumps([
                {"company": "TechCorp", "role": "Developer", "duration": "2020-2023"}
            ])
        )
        db_session.add(c)
        db_session.commit()

        with patch("screening.scoring_engine.evaluate_with_llm") as mock_llm:
            mock_llm.return_value = {"score": 50.0, "reason": "Partial"}
            total, breakdown = calculate_score(c, sample_job)
            
            # Since education is Non-STEM (Tier 3), it should be 50% * 15 = 8 points.
            assert breakdown["education"] == 8

    def test_no_experience(self, db_session, sample_job):
        from screening.scoring_engine import calculate_score

        c = _make_candidate(sample_job.id, experience_years=0.0)
        db_session.add(c)
        db_session.commit()

        total, breakdown = calculate_score(c, sample_job)
        assert breakdown["experience"] == 0

    def test_location_mismatch(self, db_session, sample_job):
        from screening.scoring_engine import calculate_score

        c = _make_candidate(sample_job.id, location="Delhi")
        db_session.add(c)
        db_session.commit()

        total, breakdown = calculate_score(c, sample_job)
        assert breakdown["location"] == 0

    def test_modular_functions(self, sample_job):
        from screening.scoring_engine import (
            _score_skills_with_weighted_tenure,
            _score_tiered_education,
            _score_fuzzy_job_title,
            calculate_confidence_score
        )
        
        # Test tiered education relevance
        assert _score_tiered_education("bachelor's in computer science", "bachelor's") == 15 # Tier 1
        assert _score_tiered_education("b.sc in physics", "bachelor's") == 12 # Tier 2 (80% of 15)
        assert _score_tiered_education("bachelor of commerce", "bachelor's") == 8 # Tier 3 (50% of 15)
        
        # Test fuzzy job title alignment
        assert _score_fuzzy_job_title("Software Developer", None, "Python Developer") == 5
        assert _score_fuzzy_job_title("Python Developer", None, "Python Developer") == 10
        assert _score_fuzzy_job_title("QA Tester", None, "Python Developer") == 0
        
        # Test confidence scoring
        class MockCandidate:
            phone = "1234567890"
            email = "test@example.com"
            skills = json.dumps(["python"])
            work_history = json.dumps([{"company": "A", "role": "Dev", "duration": "2020-2023"}])
            
        cand = MockCandidate()
        # All completeness items present + 1 job unambiguous = 40 (completeness) + 30 (tenure clarity) + 30 (llm integrity) = 100
        assert calculate_confidence_score(cand, llm_response_valid=True) == 100
        assert calculate_confidence_score(cand, llm_response_valid=False) == 70



# ── Processor Tests ──────────────────────────────────────────────────────────

class TestProcessor:

    def test_shortlisted(self, db_session, sample_job):
        from screening.processor import process_candidate

        c = _make_candidate(
            sample_job.id,
            skills=json.dumps(["python", "sql", "fastapi", "docker"]),
            experience_years=5.0,
            education="bachelor's",
            location="Pune",
        )
        db_session.add(c)
        db_session.commit()

        from screening.scoring_engine import calculate_score
        from unittest.mock import patch
        
        with patch("screening.scoring_engine.evaluate_with_llm") as mock_llm:
            mock_llm.return_value = {"score": 90.0, "reason": "Good match"}
            score, breakdown = calculate_score(c, sample_job)
            print("DEBUG - SCORE BREAKDOWN:", breakdown)
            
            result = process_candidate(c.id, db_session)
            print("RESULT OF PROCESS_CANDIDATE:", result)
            assert result["status"] == "shortlisted"
            assert result["score"] >= 70

        # Verify DB was updated
        db_session.refresh(c)
        assert c.status == "shortlisted"
        assert c.score >= 70

    def test_rejected_low_score(self, db_session, sample_job):
        from screening.processor import process_candidate

        c = _make_candidate(
            sample_job.id,
            skills=json.dumps(["java"]),
            experience_years=0.0,
            education="high school",
            location="Delhi",
        )
        db_session.add(c)
        db_session.commit()

        result = process_candidate(c.id, db_session)
        assert result["status"] == "rejected"
        assert result["score"] < 70

    def test_duplicate_skips_scoring(self, db_session, sample_job):
        from screening.processor import process_candidate

        # Insert and process c1 first — it's the original
        c1 = _make_candidate(sample_job.id, email="dup@test.com", name="Original")
        db_session.add(c1)
        db_session.commit()

        result1 = process_candidate(c1.id, db_session)
        assert result1["is_duplicate"] is False

        # Now insert c2 with same email — should be detected as duplicate
        c2 = _make_candidate(sample_job.id, email="dup@test.com", name="Clone")
        db_session.add(c2)
        db_session.commit()

        result2 = process_candidate(c2.id, db_session)
        assert result2["is_duplicate"] is True
        assert result2["status"] == "rejected"

        db_session.refresh(c2)
        assert c2.is_duplicate is True
        assert c2.merged_into == c1.id

    def test_missing_candidate(self, db_session):
        from screening.processor import process_candidate

        result = process_candidate("nonexistent-id", db_session)
        assert result is None

    def test_missing_job(self, db_session, sample_job):
        from screening.processor import process_candidate

        c = _make_candidate(
            sample_job.id,
            email="test@nojob.com",
            name="No Job",
        )
        c.job_id = "nonexistent-job-id"
        db_session.add(c)
        db_session.commit()

        result = process_candidate(c.id, db_session)
        assert result["status"] == "rejected"
