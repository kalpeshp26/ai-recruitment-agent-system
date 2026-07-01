"""
Tests for screening statistics service and PDF generator.
Run with:  .venv/Scripts/python.exe -m pytest tests/test_screening_stats.py -v
"""
import pytest
import io
from screening.statistics_service import calculate_stats
from screening.pdf_service import generate_screening_pdf

def test_empty_candidate_list():
    """Verify that empty candidate lists do not throw division by zero errors."""
    stats = calculate_stats([])
    
    assert stats["total_candidates"] == 0
    assert stats["screened_count"] == 0
    assert stats["qualified_count"] == 0
    assert stats["avg_score"] == 0.0
    assert stats["highest_score"] == 0.0
    
    # Check buckets are zeroed
    for key, val in stats["buckets"].items():
        assert val == 0
        
    # Check averages are zeroed
    for key, val in stats["parameter_averages"].items():
        assert val == 0.0

def test_average_score_calculation():
    """Verify calculations of average, qualified counts, and highest scores."""
    candidates = [
        {"score": 85.0, "score_breakdown": None},
        {"score": 60.0, "score_breakdown": None},
        {"score": 45.0, "score_breakdown": None},
        {"score": 95.0, "score_breakdown": None},
        {"score": 75.0, "score_breakdown": None},
    ]
    
    stats = calculate_stats(candidates)
    
    assert stats["total_candidates"] == 5
    assert stats["screened_count"] == 5
    assert stats["qualified_count"] == 3  # >= 70: 85, 95, 75
    assert stats["highest_score"] == 95.0
    assert stats["avg_score"] == 72.0     # (85 + 60 + 45 + 95 + 75) / 5 = 360 / 5 = 72.0

def test_distribution_buckets():
    """Verify candidate count mapping to score ranges."""
    candidates = [
        {"score": 42.0},  # under 50
        {"score": 55.0},  # 50-60
        {"score": 68.0},  # 60-70
        {"score": 72.0},  # 70-80
        {"score": 88.0},  # 80-90
        {"score": 93.0},  # 90+
        {"score": 99.0},  # 90+
    ]
    
    stats = calculate_stats(candidates)
    
    buckets = stats["buckets"]
    assert buckets["under_50"] == 1
    assert buckets["50_60"] == 1
    assert buckets["60_70"] == 1
    assert buckets["70_80"] == 1
    assert buckets["80_90"] == 1
    assert buckets["90_plus"] == 2

def test_parameter_normalization():
    """Verify score parameter averages normalize and resolve to correct percentages."""
    candidates = [
        {
            "score": 80.0,
            "score_breakdown": {
                "skills": {"score": 30.0, "max_score": 40.0},        # 75%
                "experience": {"score": 20.0, "max_score": 25.0},    # 80%
                "education": {"score": 15.0, "max_score": 15.0},     # 100%
                "location": {"score": 10.0, "max_score": 10.0},      # 100%
                "title_relevance": {"score": 5.0, "max_score": 10.0} # 50%
            }
        },
        {
            "score": 60.0,
            "score_breakdown": {
                "skills": {"score": 10.0, "max_score": 40.0},        # 25% (avg = 50%)
                "experience": {"score": 10.0, "max_score": 25.0},    # 40% (avg = 60%)
                "education": {"score": 6.0, "max_score": 15.0},      # 40% (avg = 70%)
                "location": {"score": 0.0, "max_score": 10.0},       # 0%  (avg = 50%)
                "title_relevance": {"score": 5.0, "max_score": 10.0} # 50% (avg = 50%)
            }
        }
    ]
    
    stats = calculate_stats(candidates)
    
    averages = stats["parameter_averages"]
    assert averages["skills"] == 50.0
    assert averages["experience"] == 60.0
    assert averages["education"] == 70.0
    assert averages["location"] == 50.0
    assert averages["title_relevance"] == 50.0

def test_pdf_generation():
    """Verify that PDF generation completes successfully and outputs non-empty BytesIO stream."""
    candidates = [
        {
            "score": 85.0,
            "score_breakdown": {
                "skills": {"score": 35.0, "max_score": 40.0},
                "experience": {"score": 20.0, "max_score": 25.0},
                "education": {"score": 15.0, "max_score": 15.0},
                "location": {"score": 10.0, "max_score": 10.0},
                "title_relevance": {"score": 8.0, "max_score": 10.0}
            }
        }
    ]
    
    stats = calculate_stats(candidates)
    pdf_buffer = generate_screening_pdf(stats)
    
    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")  # PDF magic number header
