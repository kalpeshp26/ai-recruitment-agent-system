"""
offer_letter_generator.py — Netra | Stage 8
Consumes decision.made events. Pulls candidate + job data.
Generates PDF via ReportLab. Uses Groq (free) for personalization.
Storage: local filesystem (no AWS needed).
"""

import json
import sqlite3
import os
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from config import DATABASE_URL, OFFERS_DIR

# Extract DB path from DATABASE_URL
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")


def get_candidate_and_job(candidate_id: int, job_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, c.email, c.phone, c.experience_years,
               j.title, j.department, j.salary_min, j.salary_max,
               j.location, j.employment_type
        FROM candidates c, jobs j
        WHERE c.id=? AND j.id=?
    """, (candidate_id, job_id))
    row = cur.fetchone()
    conn.close()
    return {
        "candidate_name": row[0], "candidate_email": row[1],
        "candidate_phone": row[2], "experience_years": row[3],
        "job_title": row[4], "department": row[5],
        "salary_min": row[6], "salary_max": row[7],
        "location": row[8], "employment_type": row[9],
    }


def generate_letter_text(data: dict) -> str:
    """Generate offer letter text locally — no external API needed."""
    return f"""Dear {data['candidate_name']},

We are delighted to offer you the position of {data['job_title']} in our {data['department']} team.

Offer Details:
  - Annual Salary  : ${data['offered_salary']:,.0f}
  - Joining Date   : {data['joining_date']}
  - Location       : {data['location']}
  - Employment Type: {data['employment_type']}

Please sign and return this letter within 7 days to confirm your acceptance.

We look forward to welcoming you to the team!

Best regards,
HR Team"""


def generate_offer_pdf(data: dict, letter_text: str) -> str:
    os.makedirs(OFFERS_DIR, exist_ok=True)
    filename = os.path.join(OFFERS_DIR, f"offer_{data['candidate_id']}_{data['job_id']}.pdf")
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("OFFER LETTER", styles['Title']), Spacer(1, 0.3 * inch),
             Paragraph(f"Dear {data['candidate_name']},", styles['Normal']),
             Spacer(1, 0.2 * inch)]
    for line in letter_text.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
    doc.build(story)
    return filename


def save_offer_to_db(candidate_id: int, job_id: int,
                     offered_salary: float, pdf_path: str, joining_date: str,
                     interview_id: int = None) -> str:
    """Create or find an application for (candidate_id, job_id), then insert an offer.

    Uses `applications.id` as `application_id` for offers. If no application exists,
    creates one with id `app_{candidate_id}` to remain compatible with other code.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find existing application
    cur.execute("SELECT id FROM applications WHERE job_id=? AND candidate_id=? LIMIT 1", (job_id, candidate_id))
    row = cur.fetchone()
    if row:
        application_id = row[0]
    else:
        # Create application with predictable id for compatibility
        application_id = f"app_{candidate_id}"
        try:
            cur.execute("INSERT INTO applications (id, job_id, candidate_id, status) VALUES (?,?,?,'applied')",
                        (application_id, job_id, candidate_id))
        except Exception:
            # If applications table missing or insert fails, continue
            pass

    # Prepare offer id and insert into offers using application_id
    offer_id = str(uuid.uuid4())[:12]
    try:
        if interview_id is not None:
            cur.execute("""
                INSERT INTO offers (id, application_id, salary_offered, offer_letter_url, start_date, interview_id, status)
                VALUES (?,?,?,?,?,?, 'generated')
            """, (offer_id, application_id, offered_salary, pdf_path, joining_date, interview_id))
        else:
            cur.execute("""
                INSERT INTO offers (id, application_id, salary_offered, offer_letter_url, start_date, status)
                VALUES (?,?,?,?, 'generated')
            """, (offer_id, application_id, offered_salary, pdf_path, joining_date))
    except Exception:
        # If insert fails, raise to be handled by caller
        conn.rollback()
        conn.close()
        raise

    conn.commit()
    conn.close()
    return offer_id
