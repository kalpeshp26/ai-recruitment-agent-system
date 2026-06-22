"""
recruitment_dashboard.py — Netra | Stage 10
SQLite-based. PDF/CSV export via ReportLab + pandas. No paid APIs.
"""

import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from config import DATABASE_URL

# Extract DB path from DATABASE_URL
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")


def get_funnel_metrics() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        def q(sql, params=()):
            cur.execute(sql, params)
            result = cur.fetchone()
            return result[0] if result else 0

        open_roles = q("SELECT COUNT(*) FROM jobs WHERE status='active'")
        total_applicants = q("SELECT COUNT(DISTINCT id) FROM candidates")
        
        shortlisted = q("""
            SELECT COUNT(DISTINCT id) FROM candidates
            WHERE id IN (SELECT candidate_id FROM applications WHERE UPPER(status) NOT IN ('SOURCED', 'REJECTED'))
               OR id IN (SELECT candidate_id FROM communications)
               OR id IN (SELECT candidate_id FROM chatbot_sessions)
               OR id IN (SELECT candidate_id FROM interview_sessions)
               OR id IN (SELECT candidate_id FROM interview_evaluations)
               OR id IN (SELECT candidate_id FROM onboarding)
               OR id IN (SELECT candidate_id FROM applications WHERE id IN (SELECT application_id FROM offers))
        """)
        
        outreach_sent = q("""
            SELECT COUNT(DISTINCT id) FROM candidates
            WHERE id IN (SELECT candidate_id FROM communications)
               OR id IN (SELECT candidate_id FROM chatbot_sessions)
               OR id IN (SELECT candidate_id FROM interview_sessions)
               OR id IN (SELECT candidate_id FROM interview_evaluations)
               OR id IN (SELECT candidate_id FROM onboarding)
               OR id IN (SELECT candidate_id FROM applications WHERE id IN (SELECT application_id FROM offers))
               OR id IN (SELECT candidate_id FROM applications WHERE UPPER(status) NOT IN ('SOURCED', 'REJECTED', 'SHORTLISTED'))
        """)
        
        prescreening_passed = q("""
            SELECT COUNT(DISTINCT id) FROM candidates
            WHERE id IN (SELECT candidate_id FROM chatbot_sessions WHERE LOWER(status) IN ('completed', 'done', 'pass', 'completed_eval'))
               OR id IN (SELECT candidate_id FROM interview_sessions)
               OR id IN (SELECT candidate_id FROM interview_evaluations)
               OR id IN (SELECT candidate_id FROM onboarding)
               OR id IN (SELECT candidate_id FROM applications WHERE id IN (SELECT application_id FROM offers))
        """)
        
        interviewed = q("""
            SELECT COUNT(DISTINCT id) FROM candidates
            WHERE id IN (SELECT candidate_id FROM interview_sessions)
               OR id IN (SELECT candidate_id FROM interview_evaluations)
               OR id IN (SELECT candidate_id FROM onboarding)
               OR id IN (SELECT candidate_id FROM applications WHERE id IN (SELECT application_id FROM offers))
        """)
        
        selected = q("""
            SELECT COUNT(DISTINCT id) FROM candidates
            WHERE id IN (SELECT candidate_id FROM interview_sessions WHERE LOWER(status) IN ('complete', 'completed'))
               OR id IN (SELECT candidate_id FROM interview_evaluations WHERE UPPER(recommendation) IN ('STRONG_HIRE', 'HIRE'))
               OR id IN (SELECT candidate_id FROM onboarding)
               OR id IN (SELECT candidate_id FROM applications WHERE id IN (SELECT application_id FROM offers))
        """)
        
        offered = q("""
            SELECT COUNT(DISTINCT c.id)
            FROM offers o
            JOIN candidates c ON (
                o.application_id = c.id 
                OR o.application_id = 'app_' || c.id 
                OR o.application_id IN (SELECT id FROM applications WHERE candidate_id = c.id)
            )
        """)
        
        accepted = q("""
            SELECT COUNT(DISTINCT c.id)
            FROM offers o
            JOIN candidates c ON (
                o.application_id = c.id 
                OR o.application_id = 'app_' || c.id 
                OR o.application_id IN (SELECT id FROM applications WHERE candidate_id = c.id)
            )
            WHERE LOWER(o.status) = 'accepted'
        """)
        
        joined = q("""
            SELECT COUNT(DISTINCT o.candidate_id)
            FROM onboarding o
            JOIN candidates c ON o.candidate_id = c.id
        """)
        
        conn.close()
        
        metrics = {
            "open_roles":           open_roles,
            "total_applicants":     total_applicants,
            "shortlisted":          shortlisted,
            "outreach_sent":        outreach_sent,
            "prescreening_passed":  prescreening_passed,
            "interviewed":          interviewed,
            "selected":             selected,
            "offered":              offered,
            "accepted":             accepted,
            "joined":               joined,
        }
    except sqlite3.OperationalError:
        metrics = {
            "open_roles": 0,
            "total_applicants": 0,
            "shortlisted": 0,
            "outreach_sent": 0,
            "prescreening_passed": 0,
            "interviewed": 0,
            "selected": 0,
            "offered": 0,
            "accepted": 0,
            "joined": 0,
        }
    return metrics


def get_funnel_dropoff(metrics: dict) -> list:
    stages = [
        ("Applicants",           metrics['total_applicants']),
        ("Shortlisted",          metrics['shortlisted']),
        ("Outreach Sent",        metrics['outreach_sent']),
        ("Pre-screening Passed", metrics['prescreening_passed']),
        ("Interviewed",          metrics['interviewed']),
        ("Selected",             metrics['selected']),
        ("Offered",              metrics['offered']),
        ("Accepted",             metrics['accepted']),
        ("Joined",               metrics['joined']),
    ]
    result = []
    prev_count = None
    for i, (stage, count) in enumerate(stages):
        if prev_count is not None:
            count = min(count, prev_count)
            
        prev = prev_count if prev_count is not None else count
        dropoff = round((1 - count / prev) * 100, 1) if prev > 0 and i > 0 else 0
        
        result.append({"stage": stage, "count": count, "dropoff_pct": dropoff})
        prev_count = count
    return result


def get_jobs_summary() -> list:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT j.title, j.department,
                   COUNT(DISTINCT a.candidate_id) AS applicants,
                   COUNT(DISTINCT CASE WHEN a.status='selected' THEN a.candidate_id END) AS shortlisted,
                   COUNT(DISTINCT o.id) AS offered,
                   COUNT(DISTINCT CASE WHEN ob.status='it_provisioned' THEN ob.id END) AS joined
            FROM jobs j
            LEFT JOIN applications a ON a.job_id=j.id
            LEFT JOIN offers o ON o.application_id=a.id
            LEFT JOIN onboarding ob ON ob.offer_id=o.id
            GROUP BY j.id
        """)
        rows = cur.fetchall()
        conn.close()
    except sqlite3.OperationalError:
        return []
    return [{"title": r[0], "department": r[1], "applicants": r[2],
             "shortlisted": r[3], "offered": r[4], "joined": r[5]} for r in rows]


def export_to_csv(output_path: str = "/tmp/recruitment_dashboard.csv"):
    metrics = get_funnel_metrics()
    funnel = get_funnel_dropoff(metrics)
    jobs = get_jobs_summary()
    with open(output_path, 'w') as f:
        f.write("=== FUNNEL METRICS ===\n")
        pd.DataFrame(funnel).to_csv(f, index=False)
        f.write("\n=== PER JOB BREAKDOWN ===\n")
        pd.DataFrame(jobs).to_csv(f, index=False)
    print(f"[recruitment_dashboard] CSV → {output_path}")
    return output_path


def export_to_pdf(output_path: str = "/tmp/recruitment_dashboard.pdf"):
    metrics = get_funnel_metrics()
    funnel = get_funnel_dropoff(metrics)
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("Recruitment Dashboard", styles['Title']), Spacer(1, 0.2*inch)]
    data = [["Stage", "Count", "Drop-off %"]] + [
        [f['stage'], str(f['count']), f"{f['dropoff_pct']}%"] for f in funnel]
    t = Table(data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')])
    ]))
    story.append(t)
    doc.build(story)
    print(f"[recruitment_dashboard] PDF → {output_path}")
    return output_path


def get_interview_offer_insights() -> dict:
    """Return analytics joining interview_sessions and offers for insights.

    Metrics returned:
    - avg_interview_score_offered: average final_score for candidates who were offered
    - avg_interview_score_accepted: average final_score for offers that were accepted
    - avg_interview_score_rejected: average final_score for offers that were rejected
    - offers_with_high_score_pct: percent of offers where interview final_score >= 0.7
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # avg final_score for candidates who have an offer (join via interview_id if available, else candidate_id)
        cur.execute("""
            SELECT AVG(t.final_score) FROM interview_turns t
            JOIN offers o ON o.interview_id = t.interview_id
            WHERE t.is_followup=0 AND t.final_score IS NOT NULL
        """)
        avg_offered = cur.fetchone()[0] or 0

        # accepted offers
        cur.execute("""
            SELECT AVG(t.final_score) FROM interview_turns t
            JOIN offers o ON o.interview_id = t.interview_id
            WHERE o.status='accepted' AND t.is_followup=0 AND t.final_score IS NOT NULL
        """)
        avg_accepted = cur.fetchone()[0] or 0

        # rejected offers
        cur.execute("""
            SELECT AVG(t.final_score) FROM interview_turns t
            JOIN offers o ON o.interview_id = t.interview_id
            WHERE o.status='rejected' AND t.is_followup=0 AND t.final_score IS NOT NULL
        """)
        avg_rejected = cur.fetchone()[0] or 0

        # offers with high score
        cur.execute("""
            SELECT COUNT(DISTINCT o.id) FROM offers o
            JOIN interview_turns t ON o.interview_id = t.interview_id
            WHERE t.is_followup=0 AND t.final_score >= 0.7
        """)
        high_count = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM offers")
        total_offers = cur.fetchone()[0] or 0

        conn.close()
    except sqlite3.OperationalError:
        return {
            "avg_interview_score_offered": 0,
            "avg_interview_score_accepted": 0,
            "avg_interview_score_rejected": 0,
            "offers_with_high_score_pct": 0,
            "total_offers": 0,
        }

    return {
        "avg_interview_score_offered": round(avg_offered, 3),
        "avg_interview_score_accepted": round(avg_accepted, 3),
        "avg_interview_score_rejected": round(avg_rejected, 3),
        "offers_with_high_score_pct": round((high_count / total_offers * 100), 1) if total_offers > 0 else 0,
        "total_offers": total_offers,
    }
