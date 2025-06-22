# utils.py
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import os
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def generate_pdf_from_template(template_name, context):
    template = get_template(template_name)
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def generate_confidential_info_pdf(data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logo (if exists)
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 40, height - 80, width=120, height=50, mask='auto')

    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, height - 50, "Confidential Info Verification")

    p.setFont("Helvetica", 12)
    y = height - 120
    p.drawString(40, y, f"Assigned To (Heir ID): {data.get('assigned_to_id')}")
    y -= 20
    p.drawString(40, y, f"Testator: {testator_name}")
    y -= 20
    p.drawString(40, y, f"Instructions:")
    y -= 40
    p.drawString(60, y, data.get('instructions', '')[:400])  # truncate if long

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE SPECIAL ACCOUNT PDF
def generate_special_account_pdf(data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # — Logo and header branding —
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 40, height - 80, width=120, height=50, mask='auto')
    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, height - 50, "Special Account Verification")

    # — Account details —
    p.setFont("Helvetica", 12)
    y = height - 120
    for key in ['account_type', 'account_name', 'account_number']:
        p.drawString(40, y, f"{key.replace('_',' ').title()}: {data.get(key)}")
        y -= 20
    p.drawString(40, y, f"Assigned To (Heir ID): {data.get('assigned_to_id')}")
    y -= 20
    p.drawString(40, y, f"Testator: {testator_name}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE ASSET PDF
def generate_asset_pdf(data, testator_name, image_file=None):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "Asset Verification Details")

    p.setFont("Helvetica", 12)
    y = height - 100
    line_height = 20

    p.drawString(100, y, f"Testator: {testator_name}")
    y -= line_height
    p.drawString(100, y, f"Asset Type: {data['asset_type']}")
    y -= line_height
    p.drawString(100, y, f"Location: {data['location']}")
    y -= line_height
    p.drawString(100, y, f"Estimated Value: {data['estimated_value']}")
    y -= line_height
    p.drawString(100, y, f"Instruction: {data['instruction']}")
    y -= line_height
    p.drawString(100, y, f"Assigned To (Heir IDs): {', '.join(data['assigned_to'])}")

    if image_file:
        try:
            y -= 50
            image = ImageReader(image_file)
            p.drawImage(image, 100, y - 150, width=200, height=150, preserveAspectRatio=True)
        except Exception as e:
            p.drawString(100, y, "Image could not be displayed.")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE HEIR PDF
def generate_heir_pdf(data, testator):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "Heir Verification Details")

    p.setFont("Helvetica", 12)
    y = height - 100
    line_height = 20

    p.drawString(100, y, f"Testator: {testator.full_name}")
    y -= line_height
    p.drawString(100, y, f"Full Name: {data['full_name']}")
    y -= line_height
    p.drawString(100, y, f"Relationship: {data['relationship']}")
    y -= line_height
    p.drawString(100, y, f"Date of Birth: {data['date_of_birth']}")
    y -= line_height
    p.drawString(100, y, f"Phone Number: {data['phone_number']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE CONFIDENTIAL INFO PDF
def generate_confidential_pdf(data, testator_name):
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Branding
    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, height - 50, "Confidential Info Verification")

    # Content
    p.setFont("Helvetica", 12)
    y = height - 100
    p.drawString(40, y, f"Testator: {testator_name}")
    y -= 20
    p.drawString(40, y, f"Assigned Heir ID: {data.get('assigned_to_id')}")
    y -= 20
    p.drawString(40, y, "Instructions:")
    y -= 20
    p.drawString(60, y, data.get("instructions")[:200] + "...")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_executor_pdf(executor_data, testator_name):
    """
    Generate a PDF summary of the executor submission.
    Returns a BytesIO buffer with the PDF content.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    elements = []

    title = f"Executor Assignment Summary for {testator_name}"
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>Full Name:</b> {executor_data.get('full_name')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Relationship:</b> {executor_data.get('relationship')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Phone Number:</b> {executor_data.get('phone_number')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Testator ID:</b> {executor_data.get('testator_id')}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_post_death_pdf(instruction_data, testator_name):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Post-Death Instructions for {testator_name}", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Instructions:</b>", styles["Heading3"]))
    elements.append(Paragraph(instruction_data.get("instructions", ""), styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer