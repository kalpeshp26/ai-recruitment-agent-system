import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

# Paths
JD_PATH = "scratch/python_developer_jd.txt"
RESUME_PATH = "scratch/john_developer_resume.pdf"

# 1. Generate Job Description Text File
jd_content = """Job Title: Python Developer
Location: San Francisco, CA (Hybrid)
Role: Full-time

Job Description:
We are looking for a Python Developer to join our core engineering team. You will be responsible for building robust APIs and backend services using FastAPI and SQLAlchemy.

Key Requirements:
- 3+ years of professional software development experience.
- Strong proficiency in Python 3.x and backend frameworks like FastAPI.
- Solid experience with relational databases, database modeling, and SQLAlchemy.
- Familiarity with version control using Git.
- Experience with testing, SQLite, and deployment.

If you have a passion for writing clean, efficient code and building scalable systems, we want to hear from you!
"""

os.makedirs("scratch", exist_ok=True)
with open(JD_PATH, "w", encoding="utf-8") as f:
    f.write(jd_content)
print(f"[SUCCESS] Generated Job Description text file at: {JD_PATH}")


# 2. Generate Matching PDF Resume using ReportLab
def generate_resume_pdf(output_path):
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ResumeTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=HexColor('#1A365D'),
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'ResumeSection',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=HexColor('#2B6CB0'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'ResumeBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=HexColor('#2D3748'),
        spaceAfter=8
    )
    
    story = []
    
    # Contact Info
    story.append(Paragraph("John Developer", title_style))
    story.append(Paragraph("Email: john.developer@example.com | Phone: +1-555-0144 | Location: San Francisco, CA", body_style))
    story.append(Spacer(1, 10))
    
    # Professional Summary
    story.append(Paragraph("Professional Summary", section_style))
    story.append(Paragraph("Highly skilled Software Engineer with over 4 years of experience specializing in Python backend development. Proven expertise in building clean, high-performance REST APIs with FastAPI, managing complex database migrations with SQLAlchemy, and maintaining source control through Git.", body_style))
    
    # Skills
    story.append(Paragraph("Technical Skills", section_style))
    story.append(Paragraph("<b>Languages & Frameworks:</b> Python, FastAPI, SQL, HTML, CSS, JavaScript<br/>"
                           "<b>Databases & Tools:</b> SQLite, PostgreSQL, SQLAlchemy, Git, Docker, REST APIs", body_style))
    
    # Experience
    story.append(Paragraph("Professional Experience", section_style))
    story.append(Paragraph("<b>Senior Backend Engineer</b> | TechCorp Solutions (2024 - Present)", body_style))
    story.append(Paragraph("- Lead the design and implementation of microservices using FastAPI, reducing response latency by 25%.<br/>"
                           "- Designed relational schemas and managed data models with SQLAlchemy for high-traffic applications.<br/>"
                           "- Maintained clean CI/CD pipelines and version controls using Git.", body_style))
    
    story.append(Paragraph("<b>Python Developer</b> | WebStart Inc (2022 - 2024)", body_style))
    story.append(Paragraph("- Built and maintained scalable APIs for client-facing web applications using Python and FastAPI.<br/>"
                           "- Used SQLite for light local transactional database configurations and fast prototyping.<br/>"
                           "- Collaborated with frontend developers to integrate APIs cleanly.", body_style))
    
    # Education
    story.append(Paragraph("Education", section_style))
    story.append(Paragraph("<b>Bachelor of Science in Computer Science</b> | University of California, Berkeley", body_style))
    
    doc.build(story)
    print(f"[SUCCESS] Generated matching PDF resume at: {output_path}")

generate_resume_pdf(RESUME_PATH)
