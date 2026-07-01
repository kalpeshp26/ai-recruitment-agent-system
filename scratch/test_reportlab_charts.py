import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib import colors

def test_chart_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("Testing Charts", styles['Heading1']))
    
    # 1. SpiderChart
    d1 = Drawing(400, 200)
    sp = SpiderChart()
    sp.x = 125
    sp.y = 25
    sp.width = 150
    sp.height = 150
    sp.data = [[80.0, 70.0, 60.0, 90.0, 50.0]]
    sp.labels = ['Skills', 'Experience', 'Education', 'Location', 'Title']
    sp.strands[0].strokeColor = colors.HexColor('#6366f1')
    sp.strands[0].fillColor = colors.HexColor('#a5b4fc')
    d1.add(sp)
    story.append(d1)
    
    story.append(Spacer(1, 20))
    
    # 2. Bar Chart
    d2 = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = [[1, 2, 4, 8, 3, 2]]
    bc.categoryAxis.categoryNames = ['<50', '50-60', '60-70', '70-80', '80-90', '90+']
    bc.bars[0].fillColor = colors.HexColor('#6366f1')
    d2.add(bc)
    story.append(d2)
    
    doc.build(story)
    print("PDF size:", len(buffer.getvalue()))

if __name__ == '__main__':
    test_chart_pdf()
