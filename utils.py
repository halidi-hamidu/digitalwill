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

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.template.loader import render_to_string
from weasyprint import HTML
from reportlab.lib.units import inch
import uuid

# Register Montserrat fonts (if not already registered)
pdfmetrics.registerFont(TTFont("Montserrat-Bold", "Montserrat-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Montserrat-Thin", "Montserrat-VariableFont_wght.ttf"))

def generate_confidential_info_pdf(data, testator_name, settings):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = date.today().strftime("%d %B %Y")

    # --- Logo ---
    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            p.drawImage(logo, margin, height - 90, width=100, height=40, mask="auto")
        except Exception:
            pass  # silently continue if logo fails

    # --- Header ---
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    header_x = margin + 110 if os.path.exists(logo_path) else margin
    p.drawString(header_x, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # --- Subtitle ---
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, "Confidential Info Verification")

    # --- Declaration Paragraphs ---
    declaration_paragraphs = [
        "I hereby affirm that the confidential information enclosed herein is accurate and complete to the best of my knowledge.",
        "This declaration serves as an official statement to facilitate secure handling and rightful access to sensitive details.",
        "All efforts have been made to verify the authenticity and correctness of this information as part of the testator’s digital will.",
        "I acknowledge that any false or misleading information may have serious legal consequences and is subject to scrutiny."
    ]
    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)

    y_declaration = height - 115
    line_height = 16
    max_width = width - 2 * margin

    for paragraph in declaration_paragraphs:
        wrapped_lines = simpleSplit(paragraph, "Montserrat-Bold", 11, max_width)
        for line in wrapped_lines:
            p.drawString(margin, y_declaration, line)
            y_declaration -= line_height
        y_declaration -= line_height  # extra space between paragraphs

    # --- Summary Table ---
    table_data = [
        ["Assigned To (Heir ID)", data.get("assigned_to_id", "N/A")],
        ["Testator", testator_name],
        ["Date", current_date],
    ]
    table_width = width - 2 * margin
    col_widths = [table_width * 0.36, table_width * 0.64]
    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = y_declaration - 20
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # --- Instructions Section ---
    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawString(margin, table_top - table_height - 30, "Instructions:")

    p.setFont("Montserrat-Thin", 11)
    instruction_text = data.get("instructions", "No instructions provided.")
    max_width = width - 2 * margin
    wrapped_lines = simpleSplit(instruction_text, "Montserrat-Thin", 11, max_width)

    y_position = table_top - table_height - 50
    line_height = 16

    for line in wrapped_lines:
        if y_position < 60:
            p.showPage()
            p.setFont("Montserrat-Thin", 11)
            y_position = height - margin
        p.drawString(margin, y_position, line)
        y_position -= line_height

    # --- Footer ---
    footer_y = 40
    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + 12, f"Confidential Info for: {testator_name}")
    p.drawCentredString(width / 2, footer_y, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y - 12, "ISO 1496177")

    # --- Finalize ---
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_special_account_pdf(data, testator_name, settings):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = date.today().strftime("%d %B %Y")

    # ----------- HEADER with Logo and Branding -----------
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            p.drawImage(logo, margin, height - 90, width=100, height=40, mask='auto')
        except Exception:
            # If logo can't load, silently continue
            pass

    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    # Adjust header text position if logo present, else start at margin
    header_x = margin + 110 if os.path.exists(logo_path) else margin
    p.drawString(header_x, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ----------- SUBTITLE -----------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, "Special Account Verification")

    # ----------- DECLARATION -----------
    declaration_paragraphs = [
        "I hereby confirm that all details related to this special account have been provided truthfully and to the best of my knowledge.",
        "This declaration aims to facilitate accurate verification and rightful assignment of the account within the testator's estate.",
        "The account information including account type, number, and ownership has been thoroughly validated.",
        "I understand that any misinformation can have legal repercussions, and this statement serves as an official record of this verification."
    ]
    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)

    y_declaration = height - 115
    line_height = 16
    max_width = width - 2 * margin

    for paragraph in declaration_paragraphs:
        wrapped_lines = simpleSplit(paragraph, "Montserrat-Bold", 11, max_width)
        for line in wrapped_lines:
            p.drawString(margin, y_declaration, line)
            y_declaration -= line_height
        y_declaration -= line_height  # extra space between paragraphs

    # ----------- ACCOUNT DETAILS TABLE -----------
    table_data = [
        ["Account Type", data.get("account_type", "N/A")],
        ["Account Name", data.get("account_name", "N/A")],
        ["Account Number", data.get("account_number", "N/A")],
        ["Assigned To (Heir ID)", data.get("assigned_to_id", "N/A")],
        ["Testator", testator_name],
        ["Date", current_date],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.36, table_width * 0.64]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = y_declaration - 20
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ----------- FOOTER -----------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Account Record for: {testator_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # ----------- FINALIZE PDF -----------
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE ASSET PDF
def generate_asset_pdf(data, testator_name, image_file=None):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, "Asset Verification Details")

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I hereby declare that the information provided about the asset is accurate and complete to the best of my knowledge.",
        "This declaration is made to ensure the rightful identification and verification of the asset as part of the testator's estate.",
        "All details regarding ownership, location, and valuation have been thoroughly checked and confirmed.",
        "Any false or misleading information may have legal consequences, and this declaration serves as a formal record of the asset verification."
    ]
    
    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)

    y_declaration = height - 115
    line_height = 16
    max_width = width - 2 * margin

    for paragraph in declaration_paragraphs:
        wrapped_lines = simpleSplit(paragraph, "Montserrat-Bold", 11, max_width)
        for line in wrapped_lines:
            p.drawString(margin, y_declaration, line)
            y_declaration -= line_height
        y_declaration -= line_height  # extra space between paragraphs

    # ------------------- ASSET DATA TABLE -------------------
    instruction_text = data.get("instruction", "N/A")
    instruction_display = (instruction_text[:97] + "...") if len(instruction_text) > 100 else instruction_text

    assigned_to_list = data.get("assigned_to", [])
    assigned_to_str = ", ".join(assigned_to_list) if assigned_to_list else "N/A"

    table_data = [
        ["Testator", testator_name],
        ["Asset Type", data.get("asset_type", "N/A")],
        ["Location", data.get("location", "N/A")],
        ["Estimated Value", data.get("estimated_value", "N/A")],
        ["Instruction", instruction_display],
        ["Assigned To (Heir IDs)", assigned_to_str],
        ["Date", str(date.today())],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.36, table_width * 0.64]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = y_declaration - 20
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- IMAGE (optional) -------------------
    if image_file:
        try:
            image_y = table_top - table_height - 180  # leave some gap under the table
            image = ImageReader(image_file)
            img_width = 200
            img_height = 150
            p.drawImage(image, margin, image_y, width=img_width, height=img_height, preserveAspectRatio=True)
        except Exception:
            p.setFont("Montserrat-Thin", 10)
            p.setFillColor(colors.red)
            p.drawString(margin, table_top - table_height - 30, "⚠️ Image could not be displayed.")

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Asset Record for: {testator_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# Ensure these are registered once globally
def generate_heir_pdf(data, testator):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, "Heir Verification Details")

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I hereby declare that the information provided herein regarding the heir is true and accurate to the best of my knowledge.",
        "This declaration is made to ensure rightful verification and identification of the heir within the testator's estate.",
        "All details concerning relationship, identity, and contact information have been thoroughly checked and confirmed.",
        "Any false or misleading information may result in legal consequences, and this document serves as a formal record of the heir verification."
    ]

    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)

    y_declaration = height - 115
    line_height = 16
    max_width = width - 2 * margin

    for paragraph in declaration_paragraphs:
        wrapped_lines = simpleSplit(paragraph, "Montserrat-Bold", 11, max_width)
        for line in wrapped_lines:
            p.drawString(margin, y_declaration, line)
            y_declaration -= line_height
        y_declaration -= line_height  # extra space between paragraphs

    # ------------------- HEIR DATA TABLE -------------------
    table_data = [
        ["Testator", getattr(testator, "full_name", "N/A")],
        ["Full Name", data.get("full_name", "N/A")],
        ["Relationship", data.get("relationship", "N/A")],
        ["Date of Birth", data.get("date_of_birth", "N/A")],
        ["Phone Number", data.get("phone_number", "N/A")],
        ["Date", str(date.today())],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = y_declaration - 20
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Heir Record for: {getattr(testator, 'full_name', 'N/A')}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# GENERATE CONFIDENTIAL INFO PDF
def generate_confidential_pdf(data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, "Confidential Info Verification")

    # ------------------- DECLARATION -------------------
    declaration_text = (
        "I hereby declare that the information contained in this document is true and accurate "
        "to the best of my knowledge and that it will be used only for the purposes of verification "
        "and lawful inheritance proceedings."
    )
    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)

    # Wrap declaration text
    wrapped_declaration = simpleSplit(declaration_text, "Montserrat-Bold", 11, width - 2 * margin)
    y_declaration = height - 115
    line_height = 16
    for line in wrapped_declaration:
        p.drawString(margin, y_declaration, line)
        y_declaration -= line_height

    # ------------------- TABLE -------------------
    table_data = [
        ["Testator", testator_name],
        ["Assigned Heir ID", data.get("assigned_to_id", "N/A")],
        ["Date", str(date.today())]
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = y_declaration - 20
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- INSTRUCTIONS SECTION -------------------
    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawString(margin, table_top - table_height - 40, "Instructions:")

    p.setFont("Montserrat-Bold", 11)
    p.setFillColor(colors.black)
    instruction_text = data.get("instructions", "No instructions provided.")
    wrapped_lines = simpleSplit(instruction_text, "Montserrat-Bold", 11, width - 2 * margin)

    y_position = table_top - table_height - 60
    for line in wrapped_lines:
        if y_position < 60:  # avoid footer overlap and create new page if needed
            p.showPage()
            y_position = height - margin
            p.setFont("Montserrat-Bold", 11)
            p.setFillColor(colors.black)
        p.drawString(margin, y_position, line)
        y_position -= line_height

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Confidential Record for: {testator_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# Register fonts if not done already
def generate_executor_pdf(executor_data, testator_name):
    """
    Generate a branded PDF summary of the executor submission.
    Returns a BytesIO buffer with the PDF content.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, f"Executor Assignment Summary for {testator_name}")

    # ------------------- EXECUTOR DATA TABLE -------------------
    table_data = [
        ["Full Name", executor_data.get("full_name", "N/A")],
        ["Relationship", executor_data.get("relationship", "N/A")],
        ["Phone Number", executor_data.get("phone_number", "N/A")],
        ["Testator ID", executor_data.get("testator_id", "N/A")],
        ["Date", str(date.today())],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = height - 110
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I confirm that the information provided about the executor is accurate and complete.",
        "This document serves as an official record of executor assignment within Seduta Will.",
        "I understand that Seduta Will reserves the right to verify any information submitted.",
        "Seduta Will complies with all applicable Tanzanian laws and data protection regulations.",
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name="Justified",
        parent=styles["Normal"],
        fontName="Montserrat-Bold",
        fontSize=11,
        leading=14,
        alignment=4,  # Justified alignment
    )

    decl_start_y = table_top - table_height - 40
    for paragraph in declaration_paragraphs:
        para = Paragraph(paragraph, para_style)
        para_width, para_height = para.wrap(width - 2 * margin, height)
        para.drawOn(p, margin, decl_start_y - para_height)
        decl_start_y -= para_height + 10

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Executor Record for: {testator_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# Register fonts (if not already done)
def generate_post_death_pdf(instruction_data, testator_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, f"Post-Death Instructions for {testator_name}")

    # ------------------- INSTRUCTION TEXT -------------------
    instruction_text = instruction_data.get("instructions", "No instructions provided.")

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name="Justified",
        parent=styles["Normal"],
        fontName="Montserrat-Bold",
        fontSize=12,
        leading=16,
        alignment=4,  # Justified alignment
    )

    para = Paragraph(instruction_text, para_style)

    available_width = width - 2 * margin
    available_height = height - 150  # space below title, above footer

    # Wrap and draw paragraph
    para_width, para_height = para.wrap(available_width, available_height)
    para.drawOn(p, margin, height - 110 - para_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I confirm that the instructions provided above reflect my true wishes post-mortem.",
        "This document forms part of my official digital will managed by Seduta Will.",
        "I acknowledge Seduta Will's right to verify these instructions if necessary.",
        "Seduta Will complies with all relevant Tanzanian laws and data protection standards.",
    ]

    para_y = height - 110 - para_height - 40
    for paragraph in declaration_paragraphs:
        decl_para = Paragraph(paragraph, para_style)
        w, h = decl_para.wrap(available_width, available_height)
        decl_para.drawOn(p, margin, para_y - h)
        para_y -= h + 10

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Post-Death Record for: {testator_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# Register fonts
def generate_asset_update_pdf(data, full_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, f"Asset Update Summary for {full_name}")

    # ------------------- ASSET DATA TABLE -------------------
    table_data = [
        ["Asset Type", data.get("asset_type", "N/A")],
        ["Location", data.get("location", "N/A")],
        ["Estimated Value", data.get("estimated_value", "N/A")],
        ["Instruction", data.get("instruction", "N/A")[:100] + "..."],
        ["Image", data.get("asset_image_name", "N/A")],
        ["Updated By", full_name],
        ["Date", str(date.today())],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = height - 110
    table_height = len(table_data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I confirm that the asset update information provided above is accurate to the best of my knowledge.",
        "This document serves as an official update to my digital asset record within Seduta Will.",
        "I understand that falsifying data may result in legal consequences and that Seduta Will reserves the right to verify any updates.",
        "Seduta Will complies with data protection laws and the legal standards of the jurisdiction of Tanzania and other relevant authorities.",
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name='Justified',
        parent=styles['Normal'],
        fontName="Montserrat-Bold",
        fontSize=11,
        leading=14,
        alignment=4,  # Justified
    )

    decl_start_y = table_top - table_height - 40
    for paragraph in declaration_paragraphs:
        para = Paragraph(paragraph, para_style)
        para_width, para_height = para.wrap(width - 2 * margin, height)
        para.drawOn(p, margin, decl_start_y - para_height)
        decl_start_y -= para_height + 10

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Update Record for: {full_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# Register Montserrat fonts
def generate_asset_delete_pdf(asset_data, full_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - margin, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(margin, height - 90, f"Asset Deletion Summary for {full_name}")

    # ------------------- ASSET DATA TABLE -------------------
    data = [
        ["Asset Type", asset_data.get("asset_type", "N/A")],
        ["Location", asset_data.get("location", "N/A")],
        ["Estimated Value", asset_data.get("estimated_value", "N/A")],
        ["Instruction", asset_data.get("instruction", "N/A")[:100] + "..."],
        ["Deletion Requested By", full_name],
        ["Date", str(date.today())],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = height - 110
    table_height = len(data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I confirm that the asset deletion information provided above is true and complete to the best of my knowledge.",
        "This document represents an official request for asset removal from my digital will record, authorized and submitted voluntarily.",
        "I acknowledge that any inaccurate or misleading data may have legal consequences, and Seduta Will reserves the right to audit or verify the submission.",
        "Seduta Will adheres to data protection and legal compliance standards as set by the jurisdiction of Tanzania and relevant regulatory bodies.",
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name='Justified',
        parent=styles['Normal'],
        fontName="Montserrat-Bold",
        fontSize=11,
        leading=14,
        alignment=4,  # Justified
    )

    decl_start_y = table_top - table_height - 40
    for paragraph in declaration_paragraphs:
        para = Paragraph(paragraph, para_style)
        para_width, para_height = para.wrap(width - 2 * margin, height)
        para.drawOn(p, margin, decl_start_y - para_height)
        decl_start_y -= para_height + 10

    # ------------------- FOOTER -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"Deletion Record for: {full_name}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_updated_user_pdf(user, profile):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")
    full_name = profile.full_name

    # ------------------- TOP CONTENT (HEADER) -------------------
    c.setFont("Montserrat-Bold", 20)
    c.setFillColor(colors.orange)
    c.drawString(margin, height - 50, "🧾 Seduta Will")

    c.setFont("Montserrat-Bold", 12)
    c.setFillColor(colors.black)
    c.drawRightString(width - margin, height - 45, current_date)

    c.setStrokeColor(colors.orange)
    c.setLineWidth(1.5)
    c.line(margin, height - 60, width - margin, height - 60)

    # ------------------- MAIN CONTENT -------------------
    y_start = height - 90
    c.setFont("Montserrat-Bold", 16)
    c.setFillColor(colors.orange)
    c.drawString(margin, y_start, "Updated Profile Details")

    # Profile table data
    data = [
        ["Full Name", profile.full_name],
        ["Username", user.username],
        ["Email", user.email],
        ["Phone Number", profile.phone_number],
        ["NIDA Number", profile.nida_number],
        ["Date of Birth", profile.date_of_birth.strftime("%d %B %Y") if profile.date_of_birth else "N/A"],
        ["Gender", profile.gender],
        # ["Region", profile.region],
        # ["District", profile.district],
        # ["Ward", profile.ward],
        # ["Street", profile.street],
        # ["Roles", profile.roles],
    ]

    table_width = width - 2 * margin
    col_widths = [table_width * 0.35, table_width * 0.65]
    table = Table(data, colWidths=col_widths)

    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table_height = len(data) * 18
    table_top = y_start - 30
    table.drawOn(c, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I hereby declare that the above updated information is true and accurate to the best of my knowledge.",
        "This document serves as an official update to my personal profile for Seduta Will system records.",
        "Any discrepancies found may result in account review or limitations as per company policy.",
        "I understand that this information will be used for identification and verification purposes."
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name="Justified",
        parent=styles["Normal"],
        fontName="Montserrat-Bold",
        fontSize=10.5,
        leading=14,
        alignment=4  # Justified
    )

    y_decl = table_top - table_height - 40
    for para in declaration_paragraphs:
        p = Paragraph(para, para_style)
        w, h = p.wrap(width - 2 * margin, height)
        p.drawOn(c, margin, y_decl - h)
        y_decl -= (h + 10)

    # ------------------- FOOTER CONTENT -------------------
    footer_y = 60
    line_spacing = 16

    c.setStrokeColor(colors.orange)
    c.setLineWidth(0.7)
    c.line(margin, footer_y + 36, width - margin, footer_y + 36)

    c.setFont("Montserrat-Bold", 10)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, footer_y + (line_spacing * 2),
                        f"PDF ID: {profile.user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    c.drawCentredString(width / 2, footer_y + line_spacing,
                        "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    c.setFillColor(colors.orange)
    c.drawCentredString(width / 2, footer_y, "ISO 1496177")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_heir_verification_pdf(heir):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- HEADER -------------------
    c.setFont("Montserrat-Bold", 20)
    c.setFillColor(colors.orange)
    c.drawString(margin, height - 50, "🧾 Seduta Will")

    c.setFont("Montserrat-Bold", 12)
    c.setFillColor(colors.black)
    c.drawRightString(width - margin, height - 45, current_date)

    c.setStrokeColor(colors.orange)
    c.setLineWidth(1.5)
    c.line(margin, height - 60, width - margin, height - 60)

    # ------------------- TITLE -------------------
    c.setFont("Montserrat-Bold", 16)
    c.setFillColor(colors.orange)
    c.drawString(margin, height - 90, f"Heir Verification Summary")

    # ------------------- HEIR DATA TABLE -------------------
    table_data = [
        ["Full Name", heir.full_name],
        ["Relationship", heir.relationship],
        ["Date of Birth", heir.date_of_birth.strftime("%d %B %Y") if heir.date_of_birth else "N/A"],
        ["Phone Number", heir.phone_number],
        ["Associated Testator", heir.testator.get_full_name()],
        ["Testator Email", heir.testator.email],
    ]

    col_widths = [width * 0.35, width * 0.55]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))

    table_top = height - 110
    table_height = len(table_data) * 20
    table.wrapOn(c, width, height)
    table.drawOn(c, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declarations = [
        "I hereby confirm that the heir information listed above has been officially verified under the Seduta Will system.",
        "This document serves as a formal record of heir registration and digital acknowledgment.",
        "All data provided herein has been submitted truthfully and is now part of the testator's will.",
        "Seduta Will reserves the right to audit or validate any heir information for legal and compliance purposes.",
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name="Justified",
        parent=styles["Normal"],
        fontName="Montserrat-Bold",
        fontSize=11,
        leading=14,
        alignment=4,  # Justified
    )

    decl_start_y = table_top - table_height - 40
    for paragraph in declarations:
        p = Paragraph(paragraph, para_style)
        w, h = p.wrap(width - 2 * margin, height)
        p.drawOn(c, margin, decl_start_y - h)
        decl_start_y -= h + 10

    # ------------------- FOOTER (RELOCATED BELOW TABLE+DECLARATION) -------------------
    footer_y = decl_start_y - 40  # leave some space after last paragraph
    line_spacing = 16

    c.setStrokeColor(colors.orange)
    c.setLineWidth(0.5)
    c.line(margin, footer_y + 26, width - margin, footer_y + 26)

    c.setFont("Montserrat-Bold", 10)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"PDF ID: HEIR-{heir.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    c.drawCentredString(width / 2, footer_y + line_spacing, "Seduta, P.O. Box 1577, Kawe, Dar es Salaam")

    c.setFillColor(colors.orange)
    c.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # ------------------- SAVE -------------------
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_heir_verification_token(testator_id):
    signer = TimestampSigner()
    return signer.sign(str(testator_id))

def generate_pdf_from_template(template_name, context=None):
    """
    Generate a PDF from a Django template and context data.
    
    Args:
        template_name (str): The relative path to the HTML template (e.g. "app/template.html").
        context (dict): Context data to render the template with.
        
    Returns:
        BytesIO: A BytesIO stream containing the PDF data.
    """
    context = context or {}

    # Render the HTML template with context
    html_string = render_to_string(template_name, context)

    # Create a BytesIO buffer for the PDF output
    pdf_buffer = BytesIO()

    # Base URL needed to resolve static files (CSS, images)
    base_url = settings.STATIC_ROOT or settings.BASE_DIR

    # Generate the PDF
    HTML(string=html_string, base_url=base_url).write_pdf(target=pdf_buffer)

    pdf_buffer.seek(0)  # rewind buffer before returning
    return pdf_buffer

# PDF Generator for Asyncronization tasks using celery librarys
def generate_model_pdf(user, models_data):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Top Content
    pdf.setFont("Montserrat-Bold", 16)
    pdf.drawString(40, height - 50, "Seduta Will")  # Logo placeholder
    pdf.setFont("Montserrat-Bold", 10)
    pdf.drawRightString(width - 40, height - 40, datetime.now().strftime("%Y-%m-%d %H:%M"))

    y_position = height - 100

    # Middle Content
    for title, entries in models_data.items():
        pdf.setFont("Montserrat-Bold", 14)
        pdf.drawString(40, y_position, title)
        y_position -= 20

        for entry in entries:
            pdf.setFont("Montserrat-Bold", 10)
            for key, value in entry.items():
                pdf.drawString(50, y_position, f"{key}: {value}")
                y_position -= 15
                if y_position < 100:
                    pdf.showPage()
                    y_position = height - 100

    # Footer Content
    pdf.setFont("Montserrat-Bold", 8)
    pdf.drawString(40, 40, f"PDF ID: {uuid.uuid4()}")
    pdf.drawString(40, 25, "Company Address: Seduta HQ, Dar es Salaam, Tanzania")
    pdf.drawRightString(width - 40, 25, "ISO 27001:2023 Certified")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
