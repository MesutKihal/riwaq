from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from django.utils import timezone
import os

def generate_certificate(student_name, course_title, certificate_number, issued_date):
    """Generate PDF certificate"""
    
    # Create certificate directory if not exists
    cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    
    filename = f"certificate_{certificate_number}.pdf"
    filepath = os.path.join(cert_dir, filename)
    
    # Create PDF
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Add border
    c.setStrokeColorRGB(0.64, 0.12, 0.20)  # MIT Red
    c.setLineWidth(5)
    c.rect(20, 20, width-40, height-40)
    
    # Add inner border
    c.setLineWidth(2)
    c.rect(25, 25, width-50, height-50)
    
    # Add title
    c.setFont("Helvetica-Bold", 40)
    c.setFillColorRGB(0.64, 0.12, 0.20)
    c.drawCentredString(width/2, height-100, "شهادة إتمام")
    
    # Add subtitle
    c.setFont("Helvetica", 20)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width/2, height-150, "يتقدم رواق بهذه الشهادة إلى")
    
    # Add student name
    c.setFont("Helvetica-Bold", 36)
    c.setFillColorRGB(0.64, 0.12, 0.20)
    c.drawCentredString(width/2, height-220, student_name)
    
    # Add course completion text
    c.setFont("Helvetica", 16)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width/2, height-280, "لإتمامه بنجاح دورة")
    
    # Add course title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.64, 0.12, 0.20)
    c.drawCentredString(width/2, height-330, course_title)
    
    # Add date
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)
    date_str = issued_date.strftime("%Y/%m/%d")
    c.drawCentredString(width/2, height-400, f"التاريخ: {date_str}")
    
    # Add certificate number
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width/2, height-450, f"رقم الشهادة: {certificate_number}")
    
    # Add signature
    c.setFont("Helvetica", 10)
    c.drawString(width-200, 60, "توقيع المدرب")
    c.line(width-250, 50, width-50, 50)
    
    c.save()
    
    return filepath