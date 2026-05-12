from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

def protect_pdf(input_pdf, output_pdf, username, email):
    """Add watermark and disable printing/copying"""
    
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    
    # Add watermark to each page
    for page in reader.pages:
        # Create watermark overlay
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5, 0.3)
        c.drawString(10, 10, f"© رواق - {username} | {email}")
        c.save()
        
        # Merge watermark
        packet.seek(0)
        watermark = PdfReader(packet)
        page.merge_page(watermark.pages[0])
        writer.add_page(page)
    
    # Disable printing and copying
    writer.add_metadata({
        '/Author': 'Riwaq Platform',
        '/Title': 'Course Material'
    })
    
    # Set encryption (disable printing, copying)
    writer.encrypt(
        user_password="",
        owner_password=settings.PDF_OWNER_PASSWORD,
        permissions_flag=-44  # Disable printing and copying
    )
    
    with open(output_pdf, 'wb') as f:
        writer.write(f)