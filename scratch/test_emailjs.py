import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO)

from outreach.emailjs_sender import send_email_via_emailjs

print("Testing EmailJS sending...")
result = send_email_via_emailjs(
    to_email="test@example.com",
    to_name="Test Candidate",
    subject="EmailJS Configuration Test",
    message="This is a test email to verify that your EmailJS configuration is working.",
    chatbot_url="http://localhost:8001/chatbot/session/test-token"
)

if result:
    print("\nSUCCESS: EmailJS sent/simulated successfully!")
else:
    print("\nFAILURE: Failed to send via EmailJS.")
