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
from django.core.signing import TimestampSigner
from datetime import datetime, date

from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import simpleSplit

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
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo (optional)
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 50, height - 90, width=100, height=40, mask='auto')

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(160, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Confidential Info Verification")

    # Summary Table
    table_data = [
        ["Assigned To (Heir ID)", data.get("assigned_to_id", "N/A")],
        ["Testator", testator_name],
        ["Date", str(date.today())]
    ]
    table = Table(table_data, colWidths=[180, 320])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 220)

    # Instructions Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 260, "Instructions:")

    p.setFont("Helvetica", 12)
    instruction_text = data.get("instructions", "No instructions provided.")
    wrapped_lines = simpleSplit(instruction_text, "Helvetica", 12, width - 100)

    y_position = height - 280
    for line in wrapped_lines:
        if y_position < 60:
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 60
        p.drawString(50, y_position, line)
        y_position -= 18

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE SPECIAL ACCOUNT PDF
def generate_special_account_pdf(data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Branding: Logo (if exists) + "Digital Will" Header
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 50, height - 90, width=100, height=40, mask='auto')

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(160, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Special Account Verification")

    # Account Details Table
    table_data = [
        ["Account Type", data.get("account_type", "N/A")],
        ["Account Name", data.get("account_name", "N/A")],
        ["Account Number", data.get("account_number", "N/A")],
        ["Assigned To (Heir ID)", data.get("assigned_to_id", "N/A")],
        ["Testator", testator_name],
        ["Date", str(date.today())],
    ]

    table = Table(table_data, colWidths=[180, 320])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw the table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 280)

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE ASSET PDF
def generate_asset_pdf(data, testator_name, image_file=None):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Asset Verification Details")

    # Asset Data Table
    table_data = [
        ["Testator", testator_name],
        ["Asset Type", data.get("asset_type", "N/A")],
        ["Location", data.get("location", "N/A")],
        ["Estimated Value", data.get("estimated_value", "N/A")],
        ["Instruction", data.get("instruction", "N/A")[:100] + "..."],
        ["Assigned To (Heir IDs)", ", ".join(data.get("assigned_to", []))],
        ["Date", str(date.today())],
    ]

    table = Table(table_data, colWidths=[180, 320])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 340)

    # Image (if provided)
    if image_file:
        try:
            image_y = height - 520  # Adjust vertical position as needed
            image = ImageReader(image_file)
            p.drawImage(image, 50, image_y - 150, width=200, height=150, preserveAspectRatio=True)
        except Exception as e:
            p.setFont("Helvetica-Oblique", 10)
            p.setFillColor(colors.red)
            p.drawString(50, height - 520, "⚠️ Image could not be displayed.")

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE HEIR PDF
def generate_heir_pdf(data, testator):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Heir Verification Details")

    # Heir Data Table
    table_data = [
        ["Testator", getattr(testator, "full_name", "N/A")],
        ["Full Name", data.get("full_name", "N/A")],
        ["Relationship", data.get("relationship", "N/A")],
        ["Date of Birth", data.get("date_of_birth", "N/A")],
        ["Phone Number", data.get("phone_number", "N/A")],
        ["Date", str(date.today())],
    ]

    table = Table(table_data, colWidths=[150, 350])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw the table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 300)

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE CONFIDENTIAL INFO PDF
def generate_confidential_pdf(data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Confidential Info Verification")

    # Table with Summary Info
    table_data = [
        ["Testator", testator_name],
        ["Assigned Heir ID", data.get("assigned_to_id", "N/A")],
        ["Date", str(date.today())]
    ]

    table = Table(table_data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 200)

    # Instructions Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 240, "Instructions:")

    p.setFont("Helvetica", 12)
    instruction_text = data.get("instructions", "No instructions provided.")
    wrapped_lines = simpleSplit(instruction_text, "Helvetica", 12, width - 100)

    y_position = height - 260
    for line in wrapped_lines:
        if y_position < 60:
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 60
        p.drawString(50, y_position, line)
        y_position -= 18

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_executor_pdf(executor_data, testator_name):
    """
    Generate a branded PDF summary of the executor submission.
    Returns a BytesIO buffer with the PDF content.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, f"Executor Assignment Summary for {testator_name}")

    # Executor Info Table
    table_data = [
        ["Full Name", executor_data.get("full_name", "N/A")],
        ["Relationship", executor_data.get("relationship", "N/A")],
        ["Phone Number", executor_data.get("phone_number", "N/A")],
        ["Testator ID", executor_data.get("testator_id", "N/A")],
        ["Date", str(date.today())],
    ]

    table = Table(table_data, colWidths=[150, 350])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw the table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 300)

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_post_death_pdf(instruction_data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, f"Post-Death Instructions for {testator_name}")

    # Instruction Text (wrapped manually)
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    instruction_text = instruction_data.get("instructions", "No instructions provided.")
    
    # Wrap text within page width
    from reportlab.lib.utils import simpleSplit
    wrapped_lines = simpleSplit(instruction_text, "Helvetica", 12, width - 100)
    
    y_position = height - 140
    for line in wrapped_lines:
        if y_position < 60:  # avoid overlapping footer
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 60
        p.drawString(50, y_position, line)
        y_position -= 18  # line spacing

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_asset_update_pdf(data, full_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, f"Asset Update Summary for {full_name}")

    # Asset Data Table
    table_data = [
        ["Asset Type", data.get("asset_type", "N/A")],
        ["Location", data.get("location", "N/A")],
        ["Estimated Value", data.get("estimated_value", "N/A")],
        ["Instruction", data.get("instruction", "N/A")[:100] + "..."],
        ["Image", data.get("asset_image_name", "N/A")],
        ["Updated By", full_name],
        ["Date", str(date.today())],
    ]

    table = Table(table_data, colWidths=[150, 350])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw the table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 350)

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_asset_delete_pdf(asset_data, full_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title & Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, f"Asset Deletion Summary for {full_name}")

    # Asset Data Table
    data = [
        ["Asset Type", asset_data.get("asset_type", "N/A")],
        ["Location", asset_data.get("location", "N/A")],
        ["Estimated Value", asset_data.get("estimated_value", "N/A")],
        ["Instruction", asset_data.get("instruction", "N/A")[:100] + "..."],
        ["Deletion Requested By", full_name],
        ["Date", str(date.today())],
    ]

    table = Table(data, colWidths=[150, 350])
    style = TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)

    # Draw the table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 320)

    # Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_heir_verification_token(testator_id):
    signer = TimestampSigner()
    return signer.sign(str(testator_id))
