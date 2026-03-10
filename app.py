"""
DocGen - web service for automatic document generation from templates.
Backend: Python / Flask
Supported formats: PDF, DOCX
Document types: Service Contract, Completion Act, GDPR Request
"""

import os
import io
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

app = Flask(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------------
# DOCUMENT TEMPLATES
# ----------------------------------------------------------------------------

def get_contract_data(fields):
    return {
        "title": "SERVICE AGREEMENT",
        "number": fields.get("doc_number", "001"),
        "city": fields.get("city", "Kyiv"),
        "date": fields.get("date", datetime.today().strftime("%Y-%m-%d")),
        "sections": [
            {
                "heading": "1. SUBJECT OF AGREEMENT",
                "body": (
                    "1.1. The Service Provider (" + fields.get("provider_name", "___") + ", hereinafter the \"Provider\") "
                    "agrees to provide the Client (" + fields.get("client_name", "___") + ", hereinafter the \"Client\") "
                    "with the following services: " + fields.get("service_description", "___") + ".\n"
                    "1.2. The Client agrees to accept and pay for the services provided in accordance with the terms of this Agreement."
                ),
            },
            {
                "heading": "2. PRICE AND PAYMENT",
                "body": (
                    "2.1. The total cost of services is " + fields.get("amount", "0") + " UAH (VAT included).\n"
                    "2.2. The Client shall make payment within " + fields.get("payment_days", "5") + " business days "
                    "after signing the Completion Act."
                ),
            },
            {
                "heading": "3. TIMELINE",
                "body": (
                    "3.1. The Provider agrees to complete the services by " + fields.get("deadline", "___") + ".\n"
                    "3.2. Early completion is permitted upon mutual agreement of the parties."
                ),
            },
            {
                "heading": "4. LIABILITY",
                "body": (
                    "4.1. For late payment, the Client shall pay a penalty of 0.1% of the outstanding amount "
                    "for each day of delay.\n"
                    "4.2. For failure to perform or improper performance of services, the Provider shall bear "
                    "liability in accordance with applicable law."
                ),
            },
            {
                "heading": "5. PARTY DETAILS",
                "body": (
                    "PROVIDER: " + fields.get("provider_name", "___") + "\n"
                    "Tax ID: " + fields.get("provider_code", "___") + "\n"
                    "Address: " + fields.get("provider_address", "___") + "\n\n"
                    "CLIENT: " + fields.get("client_name", "___") + "\n"
                    "Tax ID: " + fields.get("client_code", "___") + "\n"
                    "Address: " + fields.get("client_address", "___")
                ),
            },
        ],
    }


def get_act_data(fields):
    return {
        "title": "COMPLETION ACT",
        "subtitle": "(Services Rendered)",
        "number": fields.get("doc_number", "001"),
        "city": fields.get("city", "Kyiv"),
        "date": fields.get("date", datetime.today().strftime("%Y-%m-%d")),
        "sections": [
            {
                "heading": "GENERAL INFORMATION",
                "body": (
                    "Provider: " + fields.get("provider_name", "___") + "\n"
                    "Client: " + fields.get("client_name", "___") + "\n"
                    "Reference: Agreement No. " + fields.get("contract_number", "___") +
                    " dated " + fields.get("contract_date", "___")
                ),
            },
            {
                "heading": "LIST OF SERVICES RENDERED",
                "table": {
                    "headers": ["#", "Service Description", "Unit", "Qty", "Unit Price", "Total"],
                    "rows": [[
                        "1",
                        fields.get("service_description", "___"),
                        fields.get("unit", "service"),
                        fields.get("quantity", "1"),
                        fields.get("unit_price", fields.get("amount", "0")),
                        fields.get("amount", "0"),
                    ]],
                    "total": fields.get("amount", "0"),
                },
            },
            {
                "heading": "SUMMARY",
                "body": (
                    "Total services rendered: " + fields.get("amount", "0") + " UAH.\n"
                    "Amount in words: " + fields.get("amount_words", "___") + ".\n"
                    "All services have been completed in full and within the agreed timeline. "
                    "The Client has no claims regarding quality or delivery."
                ),
            },
        ],
    }


def get_gdpr_data(fields):
    return {
        "title": "DATA SUBJECT REQUEST",
        "subtitle": "(pursuant to Regulation EU 2016/679 - GDPR)",
        "number": fields.get("doc_number", "001"),
        "city": fields.get("city", "Kyiv"),
        "date": fields.get("date", datetime.today().strftime("%Y-%m-%d")),
        "sections": [
            {
                "heading": "1. IDENTIFICATION OF THE DATA SUBJECT",
                "body": (
                    "Full Name: " + fields.get("client_name", "___") + "\n"
                    "Date of Birth: " + fields.get("birth_date", "___") + "\n"
                    "Contact Email: " + fields.get("email", "___") + "\n"
                    "Phone: " + fields.get("phone", "___")
                ),
            },
            {
                "heading": "2. DATA CONTROLLER",
                "body": (
                    "Organisation: " + fields.get("provider_name", "___") + "\n"
                    "Address: " + fields.get("provider_address", "___") + "\n"
                    "DPO Email: " + fields.get("dpo_email", "___")
                ),
            },
            {
                "heading": "3. TYPE OF REQUEST",
                "body": (
                    "The data subject requests to exercise the following right: " +
                    fields.get("request_type", "right of access") + ".\n\n"
                    "Details: " + fields.get("request_details", "___")
                ),
            },
            {
                "heading": "4. LEGAL BASIS",
                "body": (
                    "This request is submitted pursuant to:\n"
                    "- Articles 15-22 of Regulation EU 2016/679 (GDPR);\n"
                    "- Applicable national data protection legislation.\n\n"
                    "Pursuant to Article 12 GDPR, please provide a response within 30 calendar days."
                ),
            },
            {
                "heading": "5. DECLARATION",
                "body": (
                    "I, " + fields.get("client_name", "___") + ", confirm the accuracy of the information provided "
                    "and knowingly exercise my rights as a data subject.\n\n"
                    "Date: " + fields.get("date", datetime.today().strftime("%Y-%m-%d"))
                ),
            },
        ],
    }


DOCUMENT_BUILDERS = {
    "contract": get_contract_data,
    "act":      get_act_data,
    "gdpr":     get_gdpr_data,
}

# ----------------------------------------------------------------------------
# PDF GENERATION
# ----------------------------------------------------------------------------

def generate_pdf(doc_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", parent=styles["Normal"],
        fontSize=14, leading=18, alignment=TA_CENTER,
        spaceAfter=4, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("DocSubtitle", parent=styles["Normal"],
        fontSize=9, leading=12, alignment=TA_CENTER, spaceAfter=2,
        fontName="Helvetica-Oblique", textColor=colors.HexColor("#555555"))
    meta_style = ParagraphStyle("DocMeta", parent=styles["Normal"],
        fontSize=10, leading=14, alignment=TA_CENTER,
        spaceAfter=6, fontName="Helvetica")
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Normal"],
        fontSize=11, leading=14, spaceBefore=14, spaceAfter=4,
        fontName="Helvetica-Bold", textColor=colors.HexColor("#1a3a5c"))
    body_style = ParagraphStyle("BodyText", parent=styles["Normal"],
        fontSize=10, leading=15, alignment=TA_JUSTIFY,
        spaceAfter=4, fontName="Helvetica")
    sign_style = ParagraphStyle("SignLine", parent=styles["Normal"],
        fontSize=10, leading=20, fontName="Helvetica")

    story = []
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(doc_data["title"], title_style))
    if doc_data.get("subtitle"):
        story.append(Paragraph(doc_data["subtitle"], subtitle_style))
    story.append(Paragraph(
        "No. %s  |  %s  |  %s" % (doc_data["number"], doc_data["city"], doc_data["date"]),
        meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 0.4*cm))

    for section in doc_data["sections"]:
        story.append(Paragraph(section["heading"], heading_style))
        if "body" in section:
            for line in section["body"].split("\n"):
                story.append(Paragraph(line or "&nbsp;", body_style))
        if "table" in section:
            t = section["table"]
            table_data = [t["headers"]] + t["rows"] + [["", "", "", "", "TOTAL:", t["total"]]]
            col_widths = [1*cm, 7*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm]
            tbl = Table(table_data, colWidths=col_widths)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),  (-1,0),  colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR",     (0,0),  (-1,0),  colors.white),
                ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0),  (-1,-1), 9),
                ("ALIGN",         (0,0),  (-1,-1), "CENTER"),
                ("ALIGN",         (1,1),  (1,-2),  "LEFT"),
                ("GRID",          (0,0),  (-1,-2), 0.5, colors.HexColor("#cccccc")),
                ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#e8f0fe")),
                ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
                ("LINEABOVE",     (0,-1), (-1,-1), 1, colors.HexColor("#1a3a5c")),
                ("ROWBACKGROUNDS",(0,1),  (-1,-2), [colors.white, colors.HexColor("#f5f8ff")]),
                ("TOPPADDING",    (0,0),  (-1,-1), 5),
                ("BOTTOMPADDING", (0,0),  (-1,-1), 5),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.3*cm))

    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#aaaaaa")))
    story.append(Spacer(1, 0.4*cm))
    sign_data = [
        [Paragraph("PROVIDER / APPLICANT", sign_style), Paragraph("CLIENT / RECIPIENT", sign_style)],
        [Paragraph("________________  /_____________/", sign_style), Paragraph("________________  /_____________/", sign_style)],
    ]
    sign_table = Table(sign_data, colWidths=[9*cm, 9*cm])
    sign_table.setStyle(TableStyle([
        ("ALIGN",      (0,0), (-1,-1), "LEFT"),
        ("FONTSIZE",   (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(sign_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ----------------------------------------------------------------------------
# DOCX GENERATION
# ----------------------------------------------------------------------------

def generate_docx(doc_data):
    document = Document()
    for section in document.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2)

    DARK_BLUE = RGBColor(0x1a, 0x3a, 0x5c)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(doc_data["title"])
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = DARK_BLUE

    if doc_data.get("subtitle"):
        p2 = document.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(doc_data["subtitle"])
        r2.italic = True
        r2.font.size = Pt(9)
        r2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    p3 = document.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run("No. %s  |  %s  |  %s" % (doc_data["number"], doc_data["city"], doc_data["date"]))
    r3.font.size = Pt(10)

    document.add_paragraph()

    for section in doc_data["sections"]:
        ph = document.add_paragraph()
        rh = ph.add_run(section["heading"])
        rh.bold = True
        rh.font.size = Pt(11)
        rh.font.color.rgb = DARK_BLUE
        ph.space_before = Pt(12)

        if "body" in section:
            for line in section["body"].split("\n"):
                pb = document.add_paragraph(line)
                pb.style.font.size = Pt(10)
                pb.paragraph_format.space_after = Pt(2)

        if "table" in section:
            t = section["table"]
            rows = [t["headers"]] + t["rows"] + [["", "", "", "", "TOTAL:", t["total"]]]
            tbl = document.add_table(rows=len(rows), cols=len(t["headers"]))
            tbl.style = "Table Grid"
            for r_idx, row_data in enumerate(rows):
                row = tbl.rows[r_idx]
                for c_idx, cell_text in enumerate(row_data):
                    cell = row.cells[c_idx]
                    cell.text = str(cell_text)
                    run_cell = (cell.paragraphs[0].runs[0]
                                if cell.paragraphs[0].runs
                                else cell.paragraphs[0].add_run(str(cell_text)))
                    run_cell.font.size = Pt(9)
                    if r_idx == 0:
                        run_cell.bold = True

    document.add_paragraph()
    sig_table = document.add_table(rows=2, cols=2)
    for i, label in enumerate(["PROVIDER / APPLICANT", "CLIENT / RECIPIENT"]):
        cell = sig_table.rows[0].cells[i]
        cell.text = label
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(10)
    for i in range(2):
        cell = sig_table.rows[1].cells[i]
        cell.text = "________________  /_____________/"
        cell.paragraphs[0].runs[0].font.size = Pt(10)

    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.read()


# ----------------------------------------------------------------------------
# FLASK ROUTES
# ----------------------------------------------------------------------------

@app.route("/")
def index():
    with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), encoding="utf-8") as f:
        return render_template_string(f.read())


@app.route("/api/generate", methods=["POST"])
def generate():
    data     = request.get_json(force=True)
    doc_type = data.get("doc_type", "contract")
    fmt      = data.get("format", "pdf").lower()
    fields   = data.get("fields", {})

    if doc_type not in DOCUMENT_BUILDERS:
        return jsonify({"error": "Unknown document type: " + doc_type}), 400
    if fmt not in ("pdf", "docx"):
        return jsonify({"error": "Format must be 'pdf' or 'docx'"}), 400

    doc_data = DOCUMENT_BUILDERS[doc_type](fields)

    if fmt == "pdf":
        file_bytes = generate_pdf(doc_data)
        mimetype   = "application/pdf"
        ext        = "pdf"
    else:
        file_bytes = generate_docx(doc_data)
        mimetype   = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext        = "docx"

    filename = "%s_%s.%s" % (doc_type, fields.get("doc_number", uuid.uuid4().hex[:6]), ext)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
