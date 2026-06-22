"""
grok_task_generator.py - AI-powered onboarding task generation
Uses Grok AI to generate personalized onboarding tasks based on job details
"""
import os
import json
import logging
from typing import List, Dict
import requests

logger = logging.getLogger(__name__)

# Grok API configuration
GROK_API_KEY = os.getenv("GROQ_API_KEY", "")
GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def generate_onboarding_tasks(job_title: str, job_description: str, department: str, 
                            skills: List[str] = None) -> Dict[str, List[str]]:
    """
    Generate personalized onboarding tasks using Grok AI based on job details.
    
    Args:
        job_title: The job title (e.g., "Software Engineer")
        job_description: Full job description
        department: Department name (e.g., "Engineering", "Marketing")
        skills: List of required skills for the role
    
    Returns:
        Dictionary with task phases: {"day_1": [...], "week_1": [...], "month_1": [...]}
    """
    if not GROK_API_KEY:
        logger.warning("GROK_API_KEY not set, falling back to default tasks")
        return get_default_tasks(department)
    
    skills_str = ", ".join(skills) if skills else "various technical skills"
    
    prompt = f"""Generate a personalized onboarding task checklist for a new employee.

Job Details:
- Title: {job_title}
- Department: {department}
- Required Skills: {skills_str}
- Job Description: {job_description[:500] if job_description else "Not provided"}

Please generate tasks for three phases:
1. Day 1 (first day tasks)
2. Week 1 (first week tasks)  
3. Month 1 (first month tasks)

For each phase, provide 4-6 specific, actionable tasks that are relevant to this role.
Tasks should be practical and role-specific.

Return the response in this exact JSON format:
{{
    "day_1": ["task 1", "task 2", ...],
    "week_1": ["task 1", "task 2", ...],
    "month_1": ["task 1", "task 2", ...]
}}"""

    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert HR onboarding specialist. Generate practical, role-specific onboarding tasks."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        # Handle cases where AI might wrap JSON in markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        
        tasks = json.loads(content)
        
        # Validate structure
        required_phases = ["day_1", "week_1", "month_1"]
        for phase in required_phases:
            if phase not in tasks or not isinstance(tasks[phase], list):
                logger.warning(f"Invalid task structure for phase {phase}, using defaults")
                tasks = get_default_tasks(department)
                break
        
        logger.info(f"Generated AI tasks for {job_title} in {department}")
        return tasks
        
    except requests.RequestException as e:
        logger.error(f"Grok API request failed: {e}")
        return get_default_tasks(department)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Grok response: {e}")
        return get_default_tasks(department)
    except Exception as e:
        logger.error(f"Error generating AI tasks: {e}")
        return get_default_tasks(department)


def get_default_tasks(department: str) -> Dict[str, List[str]]:
    """
    Fallback default tasks based on department when AI generation fails.
    """
    department_lower = department.lower() if department else ""
    
    if "engineering" in department_lower or "developer" in department_lower or "software" in department_lower:
        return {
            "day_1": [
                "Collect laptop and development tools from IT",
                "Set up company email and GitHub account",
                "Join Slack engineering channels and introduce yourself",
                "Meet your manager and development team",
                "Set up development environment and access code repositories",
                "Complete HR paperwork and security training"
            ],
            "week_1": [
                "Complete mandatory compliance and security training",
                "Set up all required development tools (IDE, Docker, etc.)",
                "Schedule 1:1 meetings with key team members",
                "Review project documentation and codebase structure",
                "Submit bank details for payroll",
                "Complete first code review or bug fix task"
            ],
            "month_1": [
                "Complete role-specific technical onboarding training",
                "Submit first progress report to manager",
                "Complete 30-day check-in with HR",
                "Provide onboarding feedback survey",
                "Contribute to a production feature or fix",
                "Present first project update to team"
            ]
        }
    elif "marketing" in department_lower:
        return {
            "day_1": [
                "Collect laptop and marketing tools from IT",
                "Set up company email and marketing software accounts",
                "Join Slack marketing channels and introduce yourself",
                "Meet your manager and marketing team",
                "Review brand guidelines and marketing assets",
                "Complete HR paperwork and policy acknowledgements"
            ],
            "week_1": [
                "Complete mandatory compliance training",
                "Set up all required marketing tools (CRM, analytics, etc.)",
                "Schedule 1:1 meetings with key team members",
                "Review current marketing campaigns and strategies",
                "Submit bank details for payroll",
                "Create first piece of content or campaign draft"
            ],
            "month_1": [
                "Complete role-specific marketing onboarding training",
                "Submit first progress report to manager",
                "Complete 30-day check-in with HR",
                "Provide onboarding feedback survey",
                "Launch or contribute to a marketing campaign",
                "Present campaign performance report to team"
            ]
        }
    elif "hr" in department_lower or "human resources" in department_lower:
        return {
            "day_1": [
                "Collect laptop and HR systems access from IT",
                "Set up company email and HR software accounts",
                "Join Slack HR channels and introduce yourself",
                "Meet your manager and HR team",
                "Review HR policies and procedures handbook",
                "Complete HR paperwork and compliance training"
            ],
            "week_1": [
                "Complete mandatory compliance and ethics training",
                "Set up all required HR systems (Workday, ATS, etc.)",
                "Schedule 1:1 meetings with key team members",
                "Review current HR processes and employee handbook",
                "Submit bank details for payroll",
                "Handle first employee inquiry or request"
            ],
            "month_1": [
                "Complete role-specific HR onboarding training",
                "Submit first progress report to manager",
                "Complete 30-day check-in with HR",
                "Provide onboarding feedback survey",
                "Conduct first employee onboarding session",
                "Review and update HR processes documentation"
            ]
        }
    else:
        # Default generic tasks
        return {
            "day_1": [
                "Collect laptop and access card from IT",
                "Set up company email and change password",
                "Join Slack workspace and introduce yourself",
                "Meet your manager and team",
                "Complete HR paperwork and policy acknowledgements"
            ],
            "week_1": [
                "Complete mandatory compliance training",
                "Set up all required software tools",
                "Schedule 1:1 meetings with key team members",
                "Review your 30-60-90 day goals with manager",
                "Submit bank details for payroll"
            ],
            "month_1": [
                "Complete role-specific onboarding training",
                "Submit first progress report to manager",
                "Complete 30-day check-in with HR",
                "Provide onboarding feedback survey"
            ]
        }


def get_job_details_from_db(job_id: str) -> Dict:
    """
    Fetch job details from database for AI task generation.
    """
    from shared.db.database import db_session
    from shared.db.models import Job
    from sqlalchemy import select
    
    try:
        with db_session() as db:
            result = db.execute(select(Job).where(Job.id == job_id).limit(1))
            job = result.scalar_one_or_none()
            
            if job:
                return {
                    "title": job.title,
                    "description": job.description,
                    "department": job.department,
                    "skills": json.loads(job.skills) if job.skills else []
                }
            return None
    except Exception as e:
        logger.error(f"Error fetching job details: {e}")
        return None
