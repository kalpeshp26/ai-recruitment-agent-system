"""
it_provisioner.py — Netra | Stage 9
Free implementation — no Google Workspace, JIRA, or Slack APIs.
Generates provisioning report as a local text file.
In production: swap each section with real API calls.
"""

import sqlite3
import json
import os
from datetime import datetime
from config import DATABASE_URL, PROVISIONING_DIR

# Extract DB path from DATABASE_URL
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")

ROLE_SOFTWARE_MAP = {
    "engineering": ["GitHub", "VSCode", "Postman", "AWS Console", "Jira", "Confluence"],
    "design": ["Figma", "Adobe XD", "Zeplin", "Jira"],
    "marketing": ["HubSpot", "Google Analytics", "Canva", "Slack"],
    "hr": ["Workday", "LinkedIn Recruiter", "Slack", "Google Workspace"],
    "default": ["Office365", "Slack", "Zoom", "Google Workspace"]
}


def get_candidate_and_role(candidate_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, c.email, j.title, j.department, j.location
        FROM candidates c
        JOIN applications a ON a.candidate_id = c.id
        JOIN offers o ON o.application_id = a.id
        JOIN jobs j ON j.id = a.job_id
        WHERE c.id=? AND o.status='accepted'
        LIMIT 1
    """, (candidate_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {
            "name": f"Candidate {candidate_id}",
            "personal_email": "",
            "job_title": "Software Engineer",
            "department": "engineering",
            "location": "Remote"
        }
    return {"name": row[0], "personal_email": row[1],
            "job_title": row[2], "department": (row[3] or "engineering").lower(), "location": row[4]}


def generate_company_email(name: str, domain: str = "company.com") -> str:
    parts = name.lower().split()
    return f"{parts[0]}.{parts[-1]}@{domain}"


def assign_software_licenses(department: str) -> list:
    return ROLE_SOFTWARE_MAP.get(department, ROLE_SOFTWARE_MAP['default'])


def generate_provisioning_report(candidate_id: str, onboarding_id: str,
                                  company_email: str, licenses: list,
                                  ticket_id: str) -> str:
    """Save provisioning details to a local text file (replaces JIRA/Google API)."""
    os.makedirs(PROVISIONING_DIR, exist_ok=True)
    path = os.path.join(PROVISIONING_DIR, f"it_provision_{candidate_id}.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"IT PROVISIONING REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*40}\n")
        f.write(f"Candidate ID   : {candidate_id}\n")
        f.write(f"Onboarding ID  : {onboarding_id}\n")
        f.write(f"Company Email  : {company_email}\n")
        f.write(f"Ticket ID      : {ticket_id}\n")
        f.write(f"Slack Invited  : Yes\n")
        f.write(f"Licenses       : {', '.join(licenses)}\n")
        f.write(f"\n[IN PRODUCTION]\n")
        f.write(f"- Google Workspace API → create {company_email}\n")
        f.write(f"- JIRA API → raise laptop ticket {ticket_id}\n")
        f.write(f"- Slack API → invite {company_email}\n")
    return path


def save_it_provisioning(onboarding_id: str, company_email: str,
                          ticket: str, licenses: list):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Update status only. Additional provisioning fields not present in onboarding schema.
    cur.execute("""
        UPDATE onboarding
        SET status='it_provisioned'
        WHERE id=?
    """, (onboarding_id,))
    conn.commit()
    conn.close()


def _provision(onboarding_id: str, candidate_id: str) -> dict:
    info = get_candidate_and_role(candidate_id)
    company_email = generate_company_email(info['name'])
    licenses = assign_software_licenses(info['department'])
    ticket_id = f"IT-{candidate_id}"

    report_path = generate_provisioning_report(
        candidate_id, onboarding_id, company_email, licenses, ticket_id)
    save_it_provisioning(onboarding_id, company_email, ticket_id, licenses)

    print(f"[it_provisioner] ✅ Provisioning complete")
    print(f"  Company Email : {company_email}")
    print(f"  Ticket        : {ticket_id}")
    print(f"  Licenses      : {', '.join(licenses)}")
    print(f"  Report saved  : {report_path}")

    return {"company_email": company_email, "ticket": ticket_id,
            "licenses": licenses, "report": report_path}


def provision_it_resources(onboarding_id: str, candidate_id: str | None = None) -> dict:
    if candidate_id is None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT candidate_id FROM onboarding WHERE id=?", (onboarding_id,))
        row = cur.fetchone()
        conn.close()
        candidate_id = row[0] if row and row[0] else None

    if candidate_id is None:
        raise ValueError(f"Could not resolve candidate_id for onboarding {onboarding_id}")

    return _provision(onboarding_id, candidate_id)


def provision(onboarding_id: str, candidate_id: str) -> dict:
    return _provision(onboarding_id, candidate_id)
