import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
load_dotenv()

from interview.interview_email_sender import send_interview_invitation_email

def test():
    email = "diveshlokhande72@gmail.com"
    name = "Divesh Developer"
    job = "Python Developer 2"
    url = "http://localhost:5173/interview/session/sess_test_12345"
    deadline = "July 08, 2026"
    session_id = "sess_test_12345"
    
    print("Testing send_interview_invitation_email...")
    print(f"Service ID: {os.getenv('EMAILJS_INTERVIEW_SERVICE_ID')}")
    print(f"Template ID: {os.getenv('EMAILJS_INTERVIEW_TEMPLATE_ID')}")
    print(f"Public Key: {os.getenv('EMAILJS_INTERVIEW_PUBLIC_KEY')}")
    
    success = send_interview_invitation_email(
        candidate_email=email,
        candidate_name=name,
        job_title=job,
        interview_url=url,
        completion_deadline=deadline,
        session_id=session_id
    )
    
    if success:
        print("[SUCCESS] Email sent successfully!")
    else:
        print("[FAILED] Email sending failed. Check logs/errors.")

if __name__ == "__main__":
    test()
