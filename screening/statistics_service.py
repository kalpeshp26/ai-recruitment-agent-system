"""
statistics_service.py — Core service for aggregating candidate screening statistics.
"""
from typing import List, Dict, Any

def calculate_stats(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics from candidate screening results.
    Handles empty candidate lists safely to avoid ZeroDivisionError.
    """
    total_candidates = len(candidates)
    screened_candidates = [c for c in candidates if c.get("score") is not None]
    screened_count = len(screened_candidates)
    
    # KPIs
    avg_score = 0.0
    highest_score = 0.0
    qualified_count = 0
    
    # Score distribution ranges
    buckets = {
        "under_50": 0,
        "50_60": 0,
        "60_70": 0,
        "70_80": 0,
        "80_90": 0,
        "90_plus": 0
    }
    
    # Parameter score accumulators
    param_totals = {
        "skills": {"score": 0.0, "max_score": 0.0},
        "experience": {"score": 0.0, "max_score": 0.0},
        "education": {"score": 0.0, "max_score": 0.0},
        "location": {"score": 0.0, "max_score": 0.0},
        "title_relevance": {"score": 0.0, "max_score": 0.0}
    }
    
    if screened_count > 0:
        scores = [float(c["score"]) for c in screened_candidates]
        avg_score = sum(scores) / screened_count
        highest_score = max(scores)
        qualified_count = len([c for c in screened_candidates if float(c["score"]) >= 70.0])
        
        for c in screened_candidates:
            score = float(c["score"])
            if score < 50:
                buckets["under_50"] += 1
            elif score < 60:
                buckets["50_60"] += 1
            elif score < 70:
                buckets["60_70"] += 1
            elif score < 80:
                buckets["70_80"] += 1
            elif score < 90:
                buckets["80_90"] += 1
            else:
                buckets["90_plus"] += 1
                
            breakdown = c.get("score_breakdown")
            if isinstance(breakdown, dict):
                # Normalization function
                def get_val_and_max(key: str, default_max: float) -> tuple[float, float]:
                    val = breakdown.get(key)
                    if isinstance(val, dict) and "score" in val and "max_score" in val:
                        return float(val["score"]), float(val["max_score"])
                    # Fallback to standard weights
                    if val is None:
                        val = 0.0
                    return float(val), float(default_max)
                
                skill_key = "skills" if "skills" in breakdown else "skill_match"
                s_val, s_max = get_val_and_max(skill_key, 40.0)
                e_val, e_max = get_val_and_max("experience", 25.0)
                ed_val, ed_max = get_val_and_max("education", 15.0)
                l_val, l_max = get_val_and_max("location", 10.0)
                t_val, t_max = get_val_and_max("title_relevance", 10.0)
                
                param_totals["skills"]["score"] += s_val
                param_totals["skills"]["max_score"] += s_max
                
                param_totals["experience"]["score"] += e_val
                param_totals["experience"]["max_score"] += e_max
                
                param_totals["education"]["score"] += ed_val
                param_totals["education"]["max_score"] += ed_max
                
                param_totals["location"]["score"] += l_val
                param_totals["location"]["max_score"] += l_max
                
                param_totals["title_relevance"]["score"] += t_val
                param_totals["title_relevance"]["max_score"] += t_max
                
    # Calculate parameter averages as percentages
    parameter_averages = {}
    for param, data in param_totals.items():
        if data["max_score"] > 0:
            parameter_averages[param] = round((data["score"] / data["max_score"]) * 100, 1)
        else:
            parameter_averages[param] = 0.0
            
    return {
        "total_candidates": total_candidates,
        "screened_count": screened_count,
        "qualified_count": qualified_count,
        "avg_score": round(avg_score, 1),
        "highest_score": round(highest_score, 1),
        "buckets": buckets,
        "parameter_averages": parameter_averages
    }


def calculate_skills_comparison(candidates: list, job_skills: list) -> list:
    """
    Generate comparative metrics for required job skills across candidates.
    Calculates frequency (count in raw text) and recency (current job vs past vs not found).
    """
    import re
    import json
    
    comparison_list = []
    normalized_job_skills = [s.strip().lower() for s in job_skills]
    
    for c in candidates:
        raw_text = (getattr(c, "raw_resume_text", "") or "").lower()
        work_history_raw = getattr(c, "work_history", None)
        history = []
        if work_history_raw:
            try:
                history = json.loads(work_history_raw) if isinstance(work_history_raw, str) else work_history_raw
            except Exception:
                pass
                
        skills_breakdown = []
        for skill in normalized_job_skills:
            # 1. Calculate Frequency (word occurrences in raw resume text)
            escaped = re.escape(skill)
            pattern = rf"\b{escaped}\b"
            # Fallbacks for specific symbols
            if skill in ['c++', 'cpp']:
                pattern = r"(?:^|\s|[.,;:!/-])(?:c\+\+|cpp)(?:$|\s|[.,;:!/-])"
            elif skill in ['c#', 'csharp']:
                pattern = r"(?:^|\s|[.,;:!/-])(?:c#|csharp)(?:$|\s|[.,;:!/-])"
            
            frequency = len(re.findall(pattern, raw_text))
            
            # 2. Calculate Recency
            recency = "Not Mentioned"
            try:
                cand_skills = getattr(c, "skills", None)
                parsed_c_skills = [s.lower() for s in (json.loads(cand_skills) if isinstance(cand_skills, str) else (cand_skills or []))]
            except Exception:
                parsed_c_skills = []
                
            if frequency > 0 or skill in parsed_c_skills:
                recency = "Mentioned (Profile)"
                
            if history and isinstance(history, list):
                most_recent_job = history[0]
                for idx, job in enumerate(history):
                    title = (job.get("title") or job.get("role") or "").lower()
                    desc = (job.get("description") or "").lower()
                    skills_list = [s.lower() for s in job.get("skills", [])]
                    
                    evidence = 0
                    if re.search(pattern, title):
                        evidence += 3
                    if skill in skills_list:
                        evidence += 5
                    if re.search(pattern, desc):
                        evidence += 1
                        
                    if evidence >= 3:
                        if job == most_recent_job or idx == 0:
                            recency = "Recent (Current Role)"
                            break
                        else:
                            recency = "Past Experience"
                            
            skills_breakdown.append({
                "skill": skill.upper(),
                "frequency": frequency,
                "recency": recency
            })
            
        comparison_list.append({
            "candidate_id": getattr(c, "id", None),
            "candidate_name": getattr(c, "name", "Unknown"),
            "skills_breakdown": skills_breakdown
        })
        
    return comparison_list

