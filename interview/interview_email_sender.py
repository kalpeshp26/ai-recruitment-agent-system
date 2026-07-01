"""
interview/interview_email_sender.py
════════════════════════════════════════════════════════════════════
Interview Invitation Email Sender
Sends interview invitation emails to candidates who passed prescreening.
Uses dedicated EmailJS configuration for interview invitations.
"""

import os
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# EmailJS Interview Configuration
EMAILJS_INTERVIEW_SERVICE_ID = os.getenv("EMAILJS_INTERVIEW_SERVICE_ID", "") or os.getenv("EMAILJS_SERVICE_ID", "")
EMAILJS_INTERVIEW_TEMPLATE_ID = os.getenv("EMAILJS_INTERVIEW_TEMPLATE_ID", "") or os.getenv("EMAILJS_TEMPLATE_ID", "")
EMAILJS_INTERVIEW_PUBLIC_KEY = os.getenv("EMAILJS_INTERVIEW_PUBLIC_KEY", "") or os.getenv("EMAILJS_PUBLIC_KEY", "")
EMAILJS_INTERVIEW_PRIVATE_KEY = os.getenv("EMAILJS_INTERVIEW_PRIVATE_KEY", "") or os.getenv("EMAILJS_PRIVATE_KEY", "")
EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"


def send_interview_invitation_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    interview_url: str,
    completion_deadline: str,
    session_id: str = None
) -> bool:
    """
    Send interview invitation email to candidate.
    
    Args:
        candidate_email: Candidate's email address
        candidate_name: Candidate's full name
        job_title: Job position title
        interview_url: Direct link to interview session
        completion_deadline: Deadline date string (e.g., "June 10, 2026")
        session_id: Interview session ID (optional, for tracking)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not all([EMAILJS_INTERVIEW_SERVICE_ID, EMAILJS_INTERVIEW_TEMPLATE_ID, EMAILJS_INTERVIEW_PUBLIC_KEY]):
        logger.error("EmailJS Interview configuration missing. Set EMAILJS_INTERVIEW_* environment variables.")
        return False
    
    try:
        # Prepare email payload
        email_data = {
            "service_id": EMAILJS_INTERVIEW_SERVICE_ID,
            "template_id": EMAILJS_INTERVIEW_TEMPLATE_ID,
            "user_id": EMAILJS_INTERVIEW_PUBLIC_KEY,
            "template_params": {
                "to_email": candidate_email,
                "to_name": candidate_name,
                "candidate_name": candidate_name,
                "job_title": job_title,
                "interview_url": interview_url,
                "interview_link": interview_url,  # Alias for templates
                "completion_deadline": completion_deadline,
                "deadline": completion_deadline,  # Alias for templates
                "session_id": session_id or "N/A",
                "company_name": os.getenv("COMPANY_NAME", "Our Company"),
                "current_year": datetime.now().year,
            }
        }
        
        # Include Private Key if configured
        if EMAILJS_INTERVIEW_PRIVATE_KEY and EMAILJS_INTERVIEW_PRIVATE_KEY.strip():
            email_data["accessToken"] = EMAILJS_INTERVIEW_PRIVATE_KEY.strip()
        
        # Send email via EmailJS
        response = requests.post(
            EMAILJS_API_URL,
            json=email_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Interview invitation email sent successfully to {candidate_email} (Session: {session_id})")
            return True
        else:
            logger.error(f"Failed to send interview email to {candidate_email}. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending interview invitation email to {candidate_email}: {e}")
        return False


def send_interview_reminder_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    interview_url: str,
    hours_remaining: int
) -> bool:
    """
    Send interview reminder email when deadline is approaching.
    
    Args:
        candidate_email: Candidate's email address
        candidate_name: Candidate's full name
        job_title: Job position title
        interview_url: Direct link to interview session
        hours_remaining: Hours left before deadline
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # For reminders, we can reuse the same template with different messaging
    return send_interview_invitation_email(
        candidate_email=candidate_email,
        candidate_name=candidate_name,
        job_title=job_title,
        interview_url=interview_url,
        completion_deadline=f"{hours_remaining} hours remaining",
        session_id=None
    )


# ════════════════════════════════════════════════════════════════════
# EmailJS Template Requirements
# ════════════════════════════════════════════════════════════════════
"""
Create an EmailJS template with these variables:

Subject: Interview Invitation - {{job_title}} at {{company_name}}

Body:
Dear {{candidate_name}},

Congratulations! You have successfully passed the prescreening stage for the 
{{job_title}} position at {{company_name}}.

We would like to invite you to the next stage: the AI-powered interview assessment.

🎯 Interview Details:
━━━━━━━━━━━━━━━━━━━━━
• Position: {{job_title}}
• Interview Link: {{interview_url}}
• Completion Deadline: {{completion_deadline}}
• Session ID: {{session_id}}

📋 Instructions:
━━━━━━━━━━━━━━━━━━━━━
1. Click the interview link above
2. Upload your resume (if not already uploaded)
3. Answer 10 AI-generated questions
4. Complete within the deadline

⚠️ Important Notes:
━━━━━━━━━━━━━━━━━━━━━
• The interview will take approximately 30-45 minutes
• Questions are adaptive based on your responses
• Your session is saved - you can pause and resume
• Ensure stable internet connection
• Use a desktop/laptop for best experience

If you have any questions or technical issues, please reply to this email.

We look forward to your interview!

Best regards,
{{company_name}} Recruitment Team

---
© {{current_year}} {{company_name}}. All rights reserved.
"""
