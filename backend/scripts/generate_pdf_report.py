"""Generate the editorial technical report PDF for MedVault AI.

Applies the Burgundy Clinical Design System (#380F17, #8F0B13, #EFDFC5, #252B2B)
with strict ReportLab 2D coordinate geometry and Stripe Press / O'Reilly table spacing.
"""

from pathlib import Path
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_PDF = ROOT_DIR / "docs" / "MedVault_AI_Technical_Report.pdf"

BURGUNDY = colors.HexColor("#380F17")
CRIMSON = colors.HexColor("#8F0B13")
CRITICAL = colors.HexColor("#DC2011")
IVORY = colors.HexColor("#EFDFC5")
IVORY_TINT = colors.HexColor("#FBF4E9")
ALABASTER = colors.HexColor("#FAF8F5")
CHARCOAL = colors.HexColor("#252B2B")
SLATE_GREY = colors.HexColor("#4C4F54")
LIGHT_BORDER = colors.HexColor("#E7E1DA")


class NumberedReportCanvas(canvas.Canvas):
    """Canvas subclass that renders exactly one clean footer line per page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_single_footer(total_pages)
            super().showPage()
        super().save()

    def _draw_single_footer(self, page_count: int) -> None:
        self.saveState()
        self.setStrokeColor(LIGHT_BORDER)
        self.setLineWidth(0.7)
        self.line(54, 42, A4[0] - 54, 42)
        self.setFont("Helvetica", 8.5)
        self.setFillColor(SLATE_GREY)
        self.drawString(54, 28, "MedVault AI: Burgundy Clinical EHR & Grounded Retrieval | Pushkar Panwar & Saksham Singh")
        self.drawRightString(A4[0] - 54, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def draw_arrow_head(drawing: Drawing, x: float, y: float, direction: str, color=CHARCOAL) -> None:
    size = 4.5
    if direction == "right":
        pts = [x, y, x - size * 1.4, y + size, x - size * 1.4, y - size]
    elif direction == "left":
        pts = [x, y, x + size * 1.4, y + size, x + size * 1.4, y - size]
    elif direction == "down":
        pts = [x, y, x - size, y + size * 1.4, x + size, y + size * 1.4]
    else:
        pts = [x, y, x - size, y - size * 1.4, x + size, y - size * 1.4]
    drawing.add(Polygon(pts, fillColor=color, strokeColor=color))


def add_labeled_box(
    drawing: Drawing,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    subtitle: str,
    fill=ALABASTER,
    stroke=CHARCOAL,
    title_color=BURGUNDY,
) -> None:
    drawing.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1.1))
    cx = x + w / 2.0
    drawing.add(String(cx, y + h - 16, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8.5, fillColor=title_color))
    drawing.add(String(cx, y + 8, subtitle, textAnchor="middle", fontName="Helvetica", fontSize=7.0, fillColor=SLATE_GREY))


def build_architecture_diagram() -> Drawing:
    """Create a 460x246 vector system and AI grounding pipeline diagram."""
    d = Drawing(460, 246)

    # Top row: y=194..234 (h=40)
    add_labeled_box(d, 10, 194, 95, 40, "Burgundy UI", "React + ui.tsx", fill=IVORY_TINT, stroke=CRIMSON, title_color=CRIMSON)
    add_labeled_box(d, 129, 194, 115, 40, "FastAPI + JWT", "RBAC & Validation", fill=ALABASTER, stroke=BURGUNDY)
    add_labeled_box(d, 268, 194, 170, 40, "SQL Fact Engine", "GROUP BY & Recurrence", fill=ALABASTER, stroke=BURGUNDY)

    # Horizontal arrows in top row (24pt gap)
    d.add(Line(105, 214, 129, 214, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 129, 214, "right")
    d.add(Line(244, 214, 268, 214, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 268, 214, "right")

    # Middle row: y=116..156 (h=40, vertical gap 38pt below top row)
    add_labeled_box(d, 10, 116, 95, 40, "Source Drawer", "Inspect [TAG] Row", fill=IVORY_TINT, stroke=CRIMSON, title_color=CRIMSON)
    add_labeled_box(d, 129, 116, 115, 40, "Citation Gate", "100% Tag Check", fill=IVORY, stroke=BURGUNDY, title_color=BURGUNDY)
    add_labeled_box(d, 268, 116, 170, 40, "Relational DB", "13 Tables (3NF)", fill=ALABASTER, stroke=BURGUNDY)

    d.add(Line(353, 194, 353, 156, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 353, 156, "down")

    d.add(Line(268, 136, 244, 136, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 244, 136, "left")
    d.add(Line(129, 136, 105, 136, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 105, 136, "left")

    # Bottom row: y=46..86 (h=40, vertical gap 30pt below middle row)
    add_labeled_box(d, 129, 46, 115, 40, "Audit Logger", "Immutable Trail", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 268, 46, 170, 40, "Summary Cache", "SHA-256 Invalidation", fill=ALABASTER, stroke=SLATE_GREY)

    d.add(Line(186, 116, 186, 86, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 186, 86, "down")
    d.add(Line(353, 116, 353, 86, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 353, 86, "down")

    # Summary strip at y=8..30
    d.add(Rect(10, 8, 428, 22, rx=4, ry=4, fillColor=BURGUNDY, strokeColor=BURGUNDY))
    d.add(
        String(
            224,
            15.5,
            "Invariant: Database computes facts; Citation Gate strips unverified tags before render.",
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=8.0,
            fillColor=IVORY,
        )
    )
    return d


def build_schema_diagram() -> Drawing:
    """Create a 460x240 vector ER topology diagram for the 13-table 3NF schema."""
    d = Drawing(460, 240)

    # Row 1: y=186..226 (h=40)
    add_labeled_box(d, 10, 186, 90, 40, "USERS", "email, role_id FK", fill=ALABASTER, stroke=BURGUNDY)
    add_labeled_box(d, 122, 186, 94, 40, "DOCTORS", "user_id UK, license", fill=ALABASTER, stroke=BURGUNDY)
    add_labeled_box(d, 238, 186, 98, 40, "PATIENTS", "mrn UK, dob, sex", fill=IVORY_TINT, stroke=CRIMSON, title_color=CRIMSON)
    add_labeled_box(d, 358, 186, 84, 40, "ALLERGIES/HX", "patient_id FK", fill=IVORY, stroke=BURGUNDY, title_color=BURGUNDY)

    d.add(Line(100, 206, 122, 206, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 122, 206, "right")
    d.add(Line(216, 206, 238, 206, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 238, 206, "right")
    d.add(Line(336, 206, 358, 206, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 358, 206, "right")

    # Row 2: y=114..154 (h=40, vertical gap 32pt)
    add_labeled_box(d, 10, 114, 90, 40, "ROLES & AUDIT", "admin | doctor", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 122, 114, 94, 40, "PATIENT_DOC", "M:N Assignment", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 238, 114, 98, 40, "VISITS (Core)", "patient_id, vitals", fill=IVORY_TINT, stroke=CRIMSON, title_color=CRIMSON)
    add_labeled_box(d, 358, 114, 84, 40, "AI_SUMMARIES", "json + SHA-256", fill=ALABASTER, stroke=SLATE_GREY)

    d.add(Line(55, 186, 55, 154, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 55, 154, "down")
    d.add(Line(169, 186, 169, 154, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 169, 154, "down")
    d.add(Line(287, 186, 287, 154, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 287, 154, "down")
    d.add(Line(216, 134, 238, 134, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 238, 134, "right")
    d.add(Line(336, 134, 358, 134, strokeColor=CHARCOAL, strokeWidth=1.1))
    draw_arrow_head(d, 358, 134, "right")

    # Row 3: y=44..84 (h=40, vertical gap 30pt)
    add_labeled_box(d, 10, 44, 96, 40, "SYMPTOMS", "severity, duration", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 120, 44, 96, 40, "DIAGNOSES", "icd10, status", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 230, 44, 102, 40, "NOTES & LABS", "SOAP + test flags", fill=ALABASTER, stroke=SLATE_GREY)
    add_labeled_box(d, 346, 44, 96, 40, "RX -> MEDS", "dosage, strength", fill=ALABASTER, stroke=SLATE_GREY)

    # Orthogonal distribution bus from VISITS bottom (287, 114) at y=99 down to y=84
    d.add(Line(287, 114, 287, 99, strokeColor=CRIMSON, strokeWidth=1.1))
    d.add(Line(58, 99, 394, 99, strokeColor=CRIMSON, strokeWidth=1.1))
    for target_x in (58, 168, 281, 394):
        d.add(Line(target_x, 99, target_x, 84, strokeColor=CRIMSON, strokeWidth=1.1))
        draw_arrow_head(d, target_x, 84, "down", color=CRIMSON)

    # Summary strip at y=8..30
    d.add(Rect(10, 8, 432, 22, rx=4, ry=4, fillColor=BURGUNDY, strokeColor=BURGUNDY))
    d.add(
        String(
            226,
            15.5,
            "3NF Enforcement: Zero repeating symptom groups; every FK column carries a dedicated B-tree index.",
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=8.0,
            fillColor=IVORY,
        )
    )
    return d


def make_section_banner(title: str, styles) -> Table:
    tbl = Table([[Paragraph(title, styles["BannerText"])]], colWidths=[487])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BURGUNDY),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return tbl


def make_callout(label: str, body: str, styles, bg=IVORY_TINT, bar=CRIMSON) -> KeepTogether:
    html = f"<b>[{label}]</b> {body}"
    tbl = Table([[Paragraph(html, styles["CalloutText"])]], colWidths=[487])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, bar),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    return KeepTogether([tbl, Spacer(1, 8)])


def make_data_table(headers: list[str], rows: list[list[str]], col_widths: list[float], styles) -> Table:
    table_data = [[Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in headers]]
    for row in rows:
        table_data.append([Paragraph(cell, styles["TableCell"]) for cell in row])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BURGUNDY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALABASTER]),
                ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return tbl


def generate_pdf() -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=52,
        bottomMargin=56,
        title="MedVault AI Technical Report",
        author="Pushkar Panwar & Saksham Singh",
    )

    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle("ReportTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=BURGUNDY, spaceAfter=4),
        "Subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=SLATE_GREY, spaceAfter=12),
        "BannerText": ParagraphStyle("BannerText", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=IVORY),
        "Heading": ParagraphStyle("SubHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=BURGUNDY, spaceBefore=8, spaceAfter=4, keepWithNext=True),
        "Body": ParagraphStyle("BodyText", parent=base["Normal"], fontName="Helvetica", fontSize=9.8, leading=14.5, textColor=CHARCOAL, spaceAfter=6),
        "CalloutText": ParagraphStyle("CalloutText", parent=base["Normal"], fontName="Helvetica", fontSize=9.2, leading=13.5, textColor=CHARCOAL),
        "TableHeader": ParagraphStyle("TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.8, leading=12, textColor=IVORY),
        "TableCell": ParagraphStyle("TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=8.6, leading=12.5, textColor=CHARCOAL),
        "Caption": ParagraphStyle("Caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.5, leading=12, textColor=SLATE_GREY, alignment=1, spaceBefore=4, spaceAfter=10),
    }

    story = []

    story.append(Paragraph("MedVault AI: AI-Assisted Medical Record Database", styles["Title"]))
    story.append(
        Paragraph(
            "Production Engineering &amp; Burgundy Clinical Design Report | Pushkar Panwar (2501730022) &amp; Saksham Singh (2501730270)",
            styles["Subtitle"],
        )
    )
    story.append(
        make_callout(
            "CORE INVARIANT",
            "Relational SQL computes every clinical count, recurrence interval, medication history, and lab trend deterministically. The AI layer formats those facts and cites primary-key tags that the validator checks before rendering.",
            styles,
        )
    )

    story.append(make_section_banner("1. SYSTEM ARCHITECTURE &amp; CITATION PIPELINE", styles))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "MedVault AI separates HTTP routing, Pydantic input validation, relational persistence, and grounded AI synthesis into distinct layers. Clinicians authenticate with bcrypt-verified passwords and HS256 JWT tokens before accessing patient timelines or executing natural-language queries.",
            styles["Body"],
        )
    )
    story.append(
        KeepTogether(
            [
                build_architecture_diagram(),
                Paragraph("Figure 1: Request flow from the Burgundy Clinical React workspace through FastAPI RBAC, SQL fact aggregation, and citation validation.", styles["Caption"]),
            ]
        )
    )

    story.append(make_section_banner("2. NORMALISED 3NF DATABASE DESIGN", styles))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "The relational schema separates patient identity, clinician profiles, encounter visits, and five clinical child tables into Third Normal Form (3NF). Separating medications from prescriptions removes transitive drug-class dependencies, and isolating allergies and baseline history prevents duplicate entries across repeat visits.",
            styles["Body"],
        )
    )
    story.append(
        KeepTogether(
            [
                build_schema_diagram(),
                Paragraph("Figure 2: Thirteen-table 3NF entity topology with cascade rules, CHECK constraints, and indexed foreign keys.", styles["Caption"]),
            ]
        )
    )
    story.append(
        make_callout(
            "⚡ 30-SECOND VIVA &amp; EXAM CHEAT-CODE",
            "How to justify 3NF in one sentence: 1NF splits multi-valued symptoms and diagnoses out of visits; 2NF ensures junction attributes like dosage depend on the full prescription key; 3NF isolates medication catalog fields and doctor credentials into their own tables.",
            styles,
            bg=IVORY,
            bar=BURGUNDY,
        )
    )

    story.append(make_section_banner("3. PRODUCTION DESIGN &amp; ENGINEERING HARDENING", styles))
    story.append(Spacer(1, 8))
    audit_rows = [
        ["Design System", "Single-file styling lacked reusable tokens, dark theme, and cohesive identity.", "Implemented Burgundy Clinical Design System (DESIGN.md, ui.tsx, Light &amp; Dark themes)."],
        ["Clinical CRUD", "Missing UI flows to edit patient profiles, add allergies/history, or edit visits.", "Added Edit Patient, Add Allergy, Add History, Edit Visit modals + multi-row Visit form."],
        ["Database Indexes", "Missing FK indexes on users.role_id, visits.patient_id, visits.doctor_id, and clinical_notes.author_id.", "Added explicit B-tree indexes across all FK columns and a partial active-patient index."],
        ["Query Efficiency", "Dashboard top-symptom and top-condition queries scanned full tables in Python.", "Replaced full-table scans with SQL GROUP BY + func.count() + ORDER BY LIMIT 6 queries."],
        ["Cache &amp; Security", "Stale ai_summaries persisted after writes; JWT lived in persistent storage.", "Invalidated AISummaryCache on writes and moved active session tokens to sessionStorage."],
        ["Automated TDD", "Frontend lacked component interaction tests; backend had single smoke test.", "Built Vitest + Testing Library frontend suite alongside 7 backend Pytest invariant tests."],
    ]
    story.append(make_data_table(["Audit Area", "Defect Found", "Verified Fix"], audit_rows, [95, 195, 197], styles))
    story.append(Spacer(1, 10))

    story.append(make_section_banner("4. TWO-MEMBER WORK ALLOCATION", styles))
    story.append(Spacer(1, 8))
    team_rows = [
        ["Pushkar Panwar\n(2501730022)", "3NF Schema, Auth/RBAC, Patient &amp; Visit CRUD, Synthetic Storylines", "backend/app/models/__init__.py, routers/auth.py, routers/patients.py, db/seed_data.py, docs/DATABASE_SCHEMA.sql"],
        ["Saksham Singh\n(2501730270)", "Citation-Grounded AI Engine, NL Retrieval, Burgundy Clinical UI, Vitest &amp; Slide Deck", "backend/app/ai/engine.py, routers/ai.py, frontend/src/components/ui.tsx, frontend/src/App.tsx, docs/presentation.html"],
    ]
    story.append(make_data_table(["Member", "Owned Responsibilities", "Primary Source Files"], team_rows, [110, 175, 202], styles))

    doc.build(story, canvasmaker=NumberedReportCanvas)
    print(f"Generated PDF report: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()
