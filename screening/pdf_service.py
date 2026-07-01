"""
pdf_service.py — Service to generate styled candidate screening report PDFs in-memory.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_screening_pdf(stats: dict) -> io.BytesIO:
    """
    Generate an in-memory PDF report summarizing candidate screening statistics.
    """
    buffer = io.BytesIO()
    
    # Page setup - A4 Portrait with 0.5-inch margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom premium styles
    primary_color = colors.HexColor('#6366f1')  # Indigo
    dark_neutral = colors.HexColor('#1f2937')   # Charcoal
    light_neutral = colors.HexColor('#f3f4f6')  # Soft Gray
    accent_green = colors.HexColor('#10b981')   # Emerald
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=15
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=dark_neutral,
        spaceBefore=12,
        spaceAfter=6
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=dark_neutral
    )
    
    cell_header_style = ParagraphStyle(
        'TableHeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )

    story = []
    
    # 1. Header Section
    story.append(Paragraph("Candidate Screening Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Multi-Agent Recruitment Pipeline", subtitle_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Empty State Handling
    if stats["screened_count"] == 0:
        story.append(Paragraph("No Statistics Available", section_title_style))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("There are currently no candidates in the database who have completed the screening process. Run candidate resume screening on the dashboard to generate metrics and charts.", cell_style))
        doc.build(story)
        buffer.seek(0)
        return buffer

    # 2. Key Performance Indicators (KPIs)
    story.append(Paragraph("Key Metrics Summary", section_title_style))
    kpi_headers = ["Metric", "Value", "Description"]
    kpi_data = [
        [Paragraph(h, cell_header_style) for h in kpi_headers],
        [Paragraph("Total Candidates", cell_style), Paragraph(str(stats["total_candidates"]), cell_style), Paragraph("Total resumes imported in candidate intake.", cell_style)],
        [Paragraph("Screened Candidates", cell_style), Paragraph(str(stats["screened_count"]), cell_style), Paragraph("Candidates fully scored and processed.", cell_style)],
        [Paragraph("Qualified Candidates (Score >= 70)", cell_style), Paragraph(str(stats["qualified_count"]), cell_style), Paragraph("Candidates shortlisted for direct interview invitation.", cell_style)],
        [Paragraph("Average Match Score", cell_style), Paragraph(f"{stats['avg_score']}%", cell_style), Paragraph("Mean composite percentage match across all criteria.", cell_style)],
        [Paragraph("Highest Match Score", cell_style), Paragraph(f"{stats['highest_score']}%", cell_style), Paragraph("Top-scoring candidate match percentage.", cell_style)]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[2.2 * inch, 1.3 * inch, 3.5 * inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_neutral]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.25 * inch))
    
    # 3. Parameter Performance Match
    story.append(Paragraph("Average Match by Screening Parameter", section_title_style))
    param_headers = ["Screening Metric", "Average Fit %", "Interpretation"]
    
    averages = stats["parameter_averages"]
    param_data = [
        [Paragraph(h, cell_header_style) for h in param_headers],
        [Paragraph("Skills & Aliases Fit", cell_style), Paragraph(f"{averages.get('skills', 0.0)}%", cell_style), Paragraph("Normalized overlap and tenure matching of job skills.", cell_style)],
        [Paragraph("Work History / Tenure", cell_style), Paragraph(f"{averages.get('experience', 0.0)}%", cell_style), Paragraph("Experience levels evaluated against job requirement ranges.", cell_style)],
        [Paragraph("Education Level & Major", cell_style), Paragraph(f"{averages.get('education', 0.0)}%", cell_style), Paragraph("Tiered relevance check of degree levels and majors.", cell_style)],
        [Paragraph("Location Alignment", cell_style), Paragraph(f"{averages.get('location', 0.0)}%", cell_style), Paragraph("Geographic alignment and proximity score.", cell_style)],
        [Paragraph("Job Title Relevance", cell_style), Paragraph(f"{averages.get('title_relevance', 0.0)}%", cell_style), Paragraph("Semantic matching of previous job titles to candidate.", cell_style)]
    ]
    
    param_table = Table(param_data, colWidths=[2.2 * inch, 1.3 * inch, 3.5 * inch])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), dark_neutral),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_neutral]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(param_table)
    story.append(Spacer(1, 0.25 * inch))
    
    # 4. Candidate Score Range Distribution
    story.append(Paragraph("Score Range Distribution", section_title_style))
    buckets = stats["buckets"]
    dist_headers = ["Score Range", "Candidate Count", "Percent Share"]
    
    dist_data = [
        [Paragraph(h, cell_header_style) for h in dist_headers]
    ]
    
    ranges = [
        ("< 50 (Unqualified)", buckets.get("under_50", 0)),
        ("50 - 60 (Borderline Fail)", buckets.get("50_60", 0)),
        ("60 - 70 (Borderline Pass)", buckets.get("60_70", 0)),
        ("70 - 80 (Qualified / Hirable)", buckets.get("70_80", 0)),
        ("80 - 90 (Strong Competency)", buckets.get("80_90", 0)),
        ("90+ (Highly Recommended)", buckets.get("90_plus", 0))
    ]
    
    for label, val in ranges:
        pct = (val / stats["screened_count"] * 100) if stats["screened_count"] > 0 else 0
        dist_data.append([
            Paragraph(label, cell_style),
            Paragraph(str(val), cell_style),
            Paragraph(f"{pct:.1f}%", cell_style)
        ])
        
    dist_table = Table(dist_data, colWidths=[2.5 * inch, 1.8 * inch, 2.7 * inch])
    dist_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4b5563')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_neutral]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(dist_table)
    story.append(Spacer(1, 0.25 * inch))
    
    # 5. Visual Charts & Explanations (Radar & Bar charts)
    story.append(Paragraph("Visual Analytics & Charts", section_title_style))
    story.append(Spacer(1, 0.1 * inch))
    
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.spider import SpiderChart
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    
    # Average Parameter Match Radar Chart
    story.append(Paragraph("<b>Parameter Average Match (%) Radar representation:</b>", cell_style))
    story.append(Spacer(1, 0.05 * inch))
    
    radar_drawing = Drawing(400, 200)
    sp = SpiderChart()
    sp.x = 125
    sp.y = 20
    sp.width = 150
    sp.height = 150
    sp.data = [[
        averages.get('skills', 0.0),
        averages.get('experience', 0.0),
        averages.get('education', 0.0),
        averages.get('location', 0.0),
        averages.get('title_relevance', 0.0)
    ]]
    sp.labels = ['Skills', 'Experience', 'Education', 'Location', 'Title Match']
    sp.strands[0].strokeColor = colors.HexColor('#6366f1')
    sp.strands[0].fillColor = colors.HexColor('#e0e7ff')
    radar_drawing.add(sp)
    story.append(radar_drawing)
    
    story.append(Paragraph("<i>Signification:</i> The radar chart displays the candidate pool's average alignment across five core criteria. A wide polygon shows strong, balanced capability, while sharp indentations highlight skill or location gaps.", cell_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Candidate Score Distribution Bar Chart
    story.append(Paragraph("<b>Candidate Score Range Distribution representation:</b>", cell_style))
    story.append(Spacer(1, 0.05 * inch))
    
    bar_drawing = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 40
    bc.y = 30
    bc.height = 140
    bc.width = 320
    bc.data = [[
        buckets.get("under_50", 0),
        buckets.get("50_60", 0),
        buckets.get("60_70", 0),
        buckets.get("70_80", 0),
        buckets.get("80_90", 0),
        buckets.get("90_plus", 0)
    ]]
    bc.categoryAxis.categoryNames = ['< 50', '50-60', '60-70', '70-80', '80-90', '90+']
    bc.bars[0].fillColor = colors.HexColor('#6366f1')
    bar_drawing.add(bc)
    story.append(bar_drawing)
    
    story.append(Paragraph("<i>Signification:</i> The bar chart segments final candidate scores into bands. A higher volume of candidates clustered in the 70+ brackets represents a high-potential applicant pool ready for shortlist consideration.", cell_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Build Document
    doc.build(story)
    buffer.seek(0)
    return buffer
