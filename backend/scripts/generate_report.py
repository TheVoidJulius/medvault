"""Build docs/MedVault_AI_Project_Report.pdf: what the project is, how it flows, and how to demo it.

Numbers in the report are read from the seeded database at build time, so they always
match what the app shows. Screenshots come from docs/screenshots/.

    cd backend
    pip install reportlab
    python scripts/generate_report.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func

from app.ai.engine import generate_patient_summary
from app.db.seed_data import seed_database_if_empty
from app.db.session import Base, SessionLocal, engine
from app.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    Doctor,
    Medication,
    Patient,
    Prescription,
    Symptom,
    TestResult,
    Visit,
)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "MedVault_AI_Project_Report.pdf"
SHOTS = ROOT / "docs" / "screenshots"

# Design tokens (see DESIGN.md)
INK = colors.HexColor("#141A1F")
INK2 = colors.HexColor("#47515A")
INK3 = colors.HexColor("#68727B")
PEN = colors.HexColor("#2340C8")
PEN_WASH = colors.HexColor("#E8ECFB")
TRACE = colors.HexColor("#C42032")
TRACE_WASH = colors.HexColor("#FBE9EA")
OK = colors.HexColor("#17704C")
OK_WASH = colors.HexColor("#E4F2EB")
RULE = colors.HexColor("#DCE0DB")
WELL = colors.HexColor("#EEF0ED")
GRID = colors.HexColor("#F4D3CF")
GRID_MAJOR = colors.HexColor("#EBB3AD")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# --------------------------------------------------------------------------- styles

S = {
    "display": ParagraphStyle("display", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=INK),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=INK, spaceBefore=12, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5, textColor=INK, spaceAfter=6, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=12, textColor=INK2),
    "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=INK3, spaceBefore=3, spaceAfter=10),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=10, leading=14.5, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.8, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.8, leading=12, textColor=INK),
    "q": ParagraphStyle("q", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8.8, leading=12, textColor=INK),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(i, S[style], bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=False):
    data = [[c if not isinstance(c, str) else Paragraph(c, S["cellb" if header and r == 0 else "cell"]) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
    ]
    if header:
        style += [("LINEBELOW", (0, 0), (-1, 0), 1, INK), ("BACKGROUND", (0, 0), (-1, 0), WELL)]
    if zebra:
        for r in range(1 + header, len(rows), 2):
            style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F7F8F6")))
    t.setStyle(TableStyle(style))
    return t


def screenshot(name, caption, width=CONTENT_W):
    path = SHOTS / name
    if not path.exists():
        return [P(f"<i>Screenshot {name} missing; run the app and capture it.</i>", "caption")]
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width, width * ratio
    frame = Table([[img]], colWidths=[width])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return [KeepTogether([frame, P(caption, "caption")])]


def callout(text, tone="pen"):
    bg, edge = {"pen": (PEN_WASH, PEN), "ok": (OK_WASH, OK), "trace": (TRACE_WASH, TRACE)}[tone]
    t = Table([[P(text, "cell")]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 2.5, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


# --------------------------------------------------------------------------- diagrams


def _wrap(text, max_chars):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def box(d, x, y, w, h, title, sub="", fill=colors.white, edge=INK, title_color=INK, bold=True):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=edge, strokeWidth=0.9))
    lines = _wrap(title, int(w / 5.2))
    sub_lines = _wrap(sub, int(w / 4.4)) if sub else []
    total = len(lines) * 10.5 + len(sub_lines) * 9
    ty = y + h / 2 + total / 2 - 8.5
    for ln in lines:
        d.add(String(x + w / 2, ty, ln, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=8.6, fillColor=title_color, textAnchor="middle"))
        ty -= 10.5
    for ln in sub_lines:
        d.add(String(x + w / 2, ty, ln, fontName="Helvetica", fontSize=7.2, fillColor=INK2, textAnchor="middle"))
        ty -= 9


def arrow(d, x1, y1, x2, y2, color=INK2, label="", label_dx=0, label_dy=4):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1))
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    s = 5
    p1 = (x2 - s * math.cos(ang - 0.42), y2 - s * math.sin(ang - 0.42))
    p2 = (x2 - s * math.cos(ang + 0.42), y2 - s * math.sin(ang + 0.42))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color, strokeWidth=0.5))
    if label:
        d.add(String((x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy, label, fontName="Helvetica", fontSize=7, fillColor=INK3, textAnchor="middle"))


def architecture_diagram():
    w, h = CONTENT_W, 300
    d = Drawing(w, h)
    for name, y, lh in [("Browser", 238, 62), ("Vercel", 148, 82), ("Data", 8, 132)]:
        d.add(Rect(0, y, w, lh, fillColor=colors.HexColor("#F7F8F6"), strokeColor=RULE, strokeWidth=0.6))
        d.add(String(8, y + lh - 13, name, fontName="Helvetica-Bold", fontSize=8, fillColor=INK3))
    x0, gap = 58, 14
    bw3 = (w - x0 - 8 - 2 * gap) / 3
    box(d, x0, 248, bw3, 40, "React 18 + TypeScript SPA", "Vite build, Tailwind, hash routes", fill=PEN_WASH, edge=PEN)
    box(d, x0 + bw3 + gap, 248, bw3, 40, "sessionStorage", "JWT token and signed-in user")
    box(d, x0 + 2 * (bw3 + gap), 248, bw3, 40, "Charts and vitals strip", "drawn in the browser as SVG")
    arrow(d, x0 + bw3, 268, x0 + bw3 + gap, 268)
    sw = 130
    box(d, x0, 160, sw, 52, "Static frontend", "frontend/dist on the Vercel CDN")
    ax = x0 + sw + gap
    box(d, ax, 160, w - 8 - ax, 52, "FastAPI as a Python serverless function",
        "api/index.py loads backend/app/main.py: auth, dashboard, patients and ai routers")
    arrow(d, x0 + sw / 2, 248, x0 + sw / 2, 212, label="HTML, JS, CSS", label_dx=30)
    arrow(d, x0 + bw3 - 10, 248, ax + 50, 212, label="fetch /api/* with Bearer JWT", label_dx=58, label_dy=2)
    bw4 = (w - 16 - 3 * gap) / 4
    xs = [8 + i * (bw4 + gap) for i in range(4)]
    box(d, xs[0], 50, bw4, 62, "SQLAlchemy ORM", "models, relationships, CHECK constraints")
    box(d, xs[1], 50, bw4, 62, "SQLite database", "16 tables; PostgreSQL-ready; seeded on cold start")
    box(d, xs[2], 50, bw4, 62, "Grounded AI engine", "summary, retrieval and note extraction")
    box(d, xs[3], 50, bw4, 62, "Gemini (optional)", "may reword the overview; off without an API key")
    arrow(d, ax + 60, 160, xs[0] + bw4 / 2, 112)
    arrow(d, ax + 160, 160, xs[2] + bw4 / 2, 112)
    arrow(d, xs[0] + bw4, 81, xs[1], 81)
    arrow(d, xs[2], 81, xs[1] + bw4, 81)
    arrow(d, xs[2] + bw4, 81, xs[3], 81, color=INK3)
    d.add(String(w / 2, 22, "Every write and every AI call is also recorded in audit_logs.", fontName="Helvetica", fontSize=7.5, fillColor=INK3, textAnchor="middle"))
    return d


def user_flow_diagram():
    w, h = CONTENT_W, 238
    d = Drawing(w, h)
    gap = 16
    bw = (w - 3 * gap) / 4
    xs = [i * (bw + gap) for i in range(4)]

    def label(y, text):
        d.add(String(0, y, text, fontName="Helvetica-Bold", fontSize=7.5, fillColor=INK3))

    label(228, "Main path")
    main = [("Sign in", "demo presets; bcrypt and JWT"), ("Overview", "counts, recent visits, out-of-range labs"),
            ("Patients", "search, filter and sort all records"), ("Patient chart", "allergies, vitals strip, history, contact")]
    for i, (t, sub) in enumerate(main):
        box(d, xs[i], 178, bw, 44, t, sub, fill=PEN_WASH if i == 3 else (WELL if i == 0 else colors.white), edge=PEN if i == 3 else INK)
        if i < 3:
            arrow(d, xs[i] + bw, 200, xs[i + 1], 200)
    label(150, "Inside the patient chart (tabs)")
    tabs = [("Timeline", "every visit, searchable"), ("AI summary", "cited statements, flag for review"),
            ("Ask this chart", "plain-English question"), ("New visit", "form plus AI note extraction")]
    for i, (t, sub) in enumerate(tabs):
        box(d, xs[i], 100, bw, 44, t, sub)
    d.add(Line(xs[3] + bw / 2, 178, xs[3] + bw / 2, 162, strokeColor=INK2, strokeWidth=1))
    d.add(Line(xs[0] + bw / 2, 162, xs[3] + bw / 2, 162, strokeColor=INK2, strokeWidth=1))
    for i in range(4):
        arrow(d, xs[i] + bw / 2, 162, xs[i] + bw / 2, 144)
    label(72, "From any screen")
    side = [("Ask the records", "question across all patients"), ("Citation inspector", "opens the exact stored row"),
            ("Ctrl K palette", "jump to any patient or screen"), ("Audit trail", "who did what, and when")]
    for i, (t, sub) in enumerate(side):
        box(d, xs[i], 22, bw, 44, t, sub, fill=colors.HexColor("#F7F8F6"))
    arrow(d, xs[1] + bw / 2, 100, xs[1] + bw / 2, 66, label="click a citation tag", label_dx=40, label_dy=2)
    d.add(String(w / 2, 4, "Every screen has its own URL, e.g. #/patients/1/summary, so back and forward work.",
                 fontName="Helvetica", fontSize=7.2, fillColor=INK3, textAnchor="middle"))
    return d


def summary_flow_diagram():
    w, h = CONTENT_W, 205
    d = Drawing(w, h)
    steps = [
        ("1  Request", "GET /api/ai/patients/{id}/summary", WELL, INK),
        ("2  Cache check", "SHA-256 of the patient's rows; hit = reuse", colors.white, INK),
        ("3  Load rows", "visits, symptoms, Dx, Rx, labs, notes, allergies, history", colors.white, INK),
        ("4  Aggregate", "recurrence, status changes, lab trends, gaps", colors.white, INK),
        ("5  Cite", "tag every fact: V-, SYM-, DX-, RX-, LAB-, ALG-, HX-", PEN_WASH, PEN),
        ("6  Validate", "drop any statement whose tag is not a stored row", OK_WASH, OK),
        ("7  Store + log", "ai_summaries cache, audit_logs entry", colors.white, INK),
        ("8  Show", "grounding receipt, citation drawer, flag for review", PEN_WASH, PEN),
    ]
    cols, bw, bh, gx = 4, (w - 3 * 14) / 4, 62, 14
    for i, (t, sub, fill, edge) in enumerate(steps):
        row, col = divmod(i, cols)
        x = col * (bw + gx)
        y = 125 - row * 95
        box(d, x, y, bw, bh, t, sub, fill=fill, edge=edge)
        if col < cols - 1:
            arrow(d, x + bw, y + bh / 2, x + bw + gx, y + bh / 2)
    ret_y = 110
    d.add(Line(w - bw / 2, 125, w - bw / 2, ret_y, strokeColor=INK2, strokeWidth=1))
    d.add(Line(w - bw / 2, ret_y, bw / 2, ret_y, strokeColor=INK2, strokeWidth=1))
    arrow(d, bw / 2, ret_y, bw / 2, 30 + bh)
    return d


def retrieval_flow_diagram():
    w, h = CONTENT_W, 150
    d = Drawing(w, h)
    bw = (w - 4 * 12) / 5
    steps = [
        ("Question", "“Which patients had dengue with falling platelets?”"),
        ("Parse", "date window, record types, keywords; drop filler words"),
        ("Expand", "synonyms: dengue → NS1, platelet, retro-orbital"),
        ("Scan + score", "each stored row: +4.5 per matched term, type bonus"),
        ("Answer", "top 25 rows with citations, or an explicit ‘nothing matches’"),
    ]
    for i, (t, sub) in enumerate(steps):
        x = i * (bw + 12)
        fill = PEN_WASH if i == 4 else colors.white
        box(d, x, 62, bw, 70, t, sub, fill=fill, edge=PEN if i == 4 else INK)
        if i < 4:
            arrow(d, x + bw, 97, x + bw + 12, 97)
    box(d, (w - 260) / 2, 0, 260, 40, "Zero matches → refusal", "returns total_matches 0 and says the record is silent; it never guesses", fill=TRACE_WASH, edge=TRACE, title_color=TRACE)
    arrow(d, 4 * (bw + 12) + bw / 2, 62, (w + 260) / 2, 30)
    return d


def er_diagram():
    w, h = CONTENT_W, 300
    d = Drawing(w, h)
    bw, bh = 82, 28
    c = [i * (w - bw) / 4 for i in range(5)]
    pos = {
        "roles": (c[0], 262), "users": (c[1], 262), "doctors": (c[2], 262), "patient_doctor": (c[3], 262),
        "audit_logs": (c[0], 197), "patients": (c[3], 197),
        "allergies": (c[4], 232), "medical_history": (c[4], 182), "ai_summaries": (c[4], 132),
        "visits": (c[2], 132),
        "symptoms": (c[0], 62), "diagnoses": (c[1], 62), "prescriptions": (c[2], 62), "clinical_notes": (c[3], 62),
        "test_results": (c[4], 62), "medications": (c[2], 2),
    }
    core = {"patients", "visits"}
    for name, (x, y) in pos.items():
        box(d, x, y, bw, bh, name, fill=PEN_WASH if name in core else colors.white, edge=PEN if name in core else INK)

    def link(a, b, label=""):
        ax, ay = pos[a]
        bx, by = pos[b]
        x1, y1 = ax + bw / 2, ay + bh / 2
        x2, y2 = bx + bw / 2, by + bh / 2
        # clip to box edges roughly
        import math

        ang = math.atan2(y2 - y1, x2 - x1)
        dx, dy = math.cos(ang), math.sin(ang)
        tx = (bw / 2) / abs(dx) if dx else 1e9
        ty = (bh / 2) / abs(dy) if dy else 1e9
        t = min(tx, ty)
        arrow(d, x1 + dx * t, y1 + dy * t, x2 - dx * t, y2 - dy * t, label=label)

    for a, b in [("roles", "users"), ("users", "doctors"), ("users", "audit_logs"), ("doctors", "patient_doctor"),
                 ("patients", "patient_doctor"), ("patients", "allergies"), ("patients", "medical_history"),
                 ("patients", "ai_summaries"), ("patients", "visits"), ("doctors", "visits"), ("visits", "symptoms"),
                 ("visits", "diagnoses"), ("visits", "prescriptions"), ("medications", "prescriptions"),
                 ("visits", "clinical_notes"), ("visits", "test_results")]:
        link(a, b)
    return d


def ecg_cover_band():
    w, h = CONTENT_W, 120
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=GRID_MAJOR, strokeWidth=0.6))
    step = 4
    x = 0
    while x <= w:
        d.add(Line(x, 0, x, h, strokeColor=GRID_MAJOR if (x / step) % 5 == 0 else GRID, strokeWidth=0.45))
        x += step
    y = 0
    while y <= h:
        d.add(Line(0, y, w, y, strokeColor=GRID_MAJOR if (y / step) % 5 == 0 else GRID, strokeWidth=0.45))
        y += step
    base, pts, x = 60, [], 0
    while x < w:
        pts += [(x, base), (x + 16, base), (x + 21, base + 6), (x + 26, base), (x + 33, base), (x + 36, base - 6),
                (x + 40, base + 44), (x + 44, base - 16), (x + 48, base), (x + 60, base), (x + 70, base + 11), (x + 80, base), (x + 100, base)]
        x += 100
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x2 <= w:
            d.add(Line(x1, y1, x2, y2, strokeColor=TRACE, strokeWidth=1.6))
    return d


def logo_mark(size=26):
    d = Drawing(size, size)
    k = size / 32
    d.add(Rect(0, 0, size, size, rx=8 * k, ry=8 * k, fillColor=INK, strokeColor=None))

    def seg(x1, y1, x2, y2, col, wdt=2.2):
        d.add(Line(x1 * k, size - y1 * k, x2 * k, size - y2 * k, strokeColor=col, strokeWidth=wdt * k, strokeLineCap=1))

    for a in [(10.5, 8.5, 8, 8.5), (8, 8.5, 8, 23.5), (8, 23.5, 10.5, 23.5), (21.5, 8.5, 24, 8.5), (24, 8.5, 24, 23.5), (24, 23.5, 21.5, 23.5)]:
        seg(*a, colors.white)
    seg(12.5, 11.5, 19.5, 11.5, colors.HexColor("#8C9094"))
    seg(12.5, 20.5, 19.5, 20.5, colors.HexColor("#8C9094"))
    seg(12.5, 16, 19.5, 16, colors.HexColor("#8EA2FF"), 2.6)
    return d


# --------------------------------------------------------------------------- data


def gather_stats():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
        top_dx = (
            db.query(Diagnosis.condition_name, func.count(Diagnosis.id))
            .filter(Diagnosis.status != "Ruled-out")
            .group_by(Diagnosis.condition_name)
            .order_by(func.count(Diagnosis.id).desc())
            .limit(8)
            .all()
        )
        visit_types = db.query(Visit.visit_type, func.count(Visit.id)).group_by(Visit.visit_type).all()
        first, last = db.query(func.min(Visit.visit_date), func.max(Visit.visit_date)).one()
        cities = {}
        for (addr,) in db.query(Patient.address).all():
            if addr:
                city = addr.rsplit(",", 1)[-1].strip().rsplit(" ", 1)[0]
                cities[city] = cities.get(city, 0) + 1
        aarav = db.query(Patient).filter(Patient.mrn == "MRN-2026-00001").one()
        vs = generate_patient_summary(db, aarav.id, force_refresh=True).validation_stats
        return {
            "aarav_cites": f"{vs['verified_citations']} of {vs['total_citations_emitted']}",
            "patients": db.query(Patient).count(),
            "visits": db.query(Visit).count(),
            "doctors": db.query(Doctor).count(),
            "symptoms": db.query(Symptom).count(),
            "diagnoses": db.query(Diagnosis).count(),
            "prescriptions": db.query(Prescription).count(),
            "notes": db.query(ClinicalNote).count(),
            "labs": db.query(TestResult).count(),
            "abnormal_labs": db.query(TestResult).filter(TestResult.flag != "Normal").count(),
            "allergies": db.query(Allergy).count(),
            "medications": db.query(Medication).count(),
            "no_blood_group": db.query(Patient).filter(Patient.blood_group.is_(None)).count(),
            "cities": len(cities),
            "top_dx": top_dx,
            "visit_types": sorted(visit_types, key=lambda r: -r[1]),
            "span": (first.date(), last.date()),
        }
    finally:
        db.close()


# --------------------------------------------------------------------------- page furniture


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, PAGE_H - 13 * mm, PAGE_W - MARGIN, PAGE_H - 13 * mm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(INK)
        canvas.drawString(MARGIN, PAGE_H - 11 * mm, "MedVault AI")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK3)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, "Project report and flow")
        canvas.drawString(MARGIN, 11 * mm, "Pushkar Panwar (2501730022) and Saksham Singh (2501730270)")
        canvas.drawRightString(PAGE_W - MARGIN, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


# --------------------------------------------------------------------------- content


def build():
    st = gather_stats()
    span = f"{st['span'][0]:%b %Y} to {st['span'][1]:%b %Y}"
    story = []

    # Cover
    cover_logo = Table([[logo_mark(30), P("<font size=15><b>MedVault AI</b></font>", "body")]], colWidths=[40, CONTENT_W - 40])
    cover_logo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [Spacer(1, 18 * mm), cover_logo, Spacer(1, 14 * mm),
              P("Every patient’s history, read back with its sources.", "display"),
              Spacer(1, 16), ecg_cover_band(), Spacer(1, 14),
              P("Project report and flow for an AI-assisted medical record database: what it does, how a request moves "
                "through it, how the AI stays tied to stored data, and how to demo it.", "body"),
              Spacer(1, 22 * mm)]
    story.append(table([
        ["Team", "Pushkar Panwar (2501730022), Saksham Singh (2501730270)"],
        ["Live app", "https://ai-medical-records.vercel.app (and medvault-ai-thevoidjulius.vercel.app)"],
        ["Source", "github.com/saxamsingh/ai-medical-records"],
        ["Report date", f"{date.today():%d %B %Y}"],
    ], [32 * mm, CONTENT_W - 32 * mm], header=False))
    story.append(PageBreak())

    # 1. Overview
    story += [P("1. What the project is", "h1"),
              P("Doctors lose time hunting through separate visit notes, prescriptions and lab sheets to answer simple questions: "
                "has this patient had this symptom before, what were they prescribed, is this lab value getting better? MedVault AI "
                "keeps a patient’s whole history in one normalised relational database and puts two AI features on top of it:"),
              *bullets([
                  "<b>AI summary of a patient.</b> One click turns every stored visit, diagnosis, prescription and lab into a structured "
                  "summary. Every sentence carries a citation tag such as <font name=Courier>[DX-12]</font> that points at the exact database row it came from.",
                  "<b>Ask the records.</b> A doctor types a question in plain English, for one patient or the whole hospital, and gets "
                  "an answer next to the source rows. If nothing in the database matches, it says so instead of guessing.",
              ]),
              P("A third, smaller feature extracts symptoms, diagnoses and drugs from a typed consultation note into the new-visit form."),
              callout("<b>The core idea:</b> the AI never states a medical fact that it cannot point to in the database. A validator checks "
                      "every citation before the answer is returned, and the screen shows how many citations were verified.", "pen"),
              P("What is in the database right now", "h2"),
              table([
                  ["Patients", "Visits", "Doctors", "Diagnoses", "Prescriptions", "Lab results", "Clinical notes"],
                  [str(st["patients"]), str(st["visits"]), str(st["doctors"]), str(st["diagnoses"]), str(st["prescriptions"]),
                   str(st["labs"]), str(st["notes"])],
              ], [CONTENT_W / 7] * 7),
              Spacer(1, 4),
              P(f"Visits span {span}. {st['abnormal_labs']} lab results are flagged outside their reference range, "
                f"{st['allergies']} allergies are recorded, and {st['medications']} drugs are in the medication catalogue. "
                "All patients are synthetic; none is a real person.", "small")]
    story.append(PageBreak())

    # 2. Project flow
    story += [P("2. Project flow", "h1"),
              P("2.1 System architecture", "h2"),
              P("The app is a single repository deployed to Vercel. The React frontend is built into static files; the FastAPI backend runs "
                "as one Python serverless function behind <font name=Courier>/api/*</font>. On a cold start the backend creates the tables and "
                "seeds the synthetic patients into SQLite."),
              architecture_diagram(),
              P("Figure 1. Where each part runs and how a request travels.", "caption"),
              P("2.2 How a user moves through the app", "h2"),
              P("Every screen has its own URL (for example <font name=Courier>#/patients/1/summary</font>), so the browser back button works and "
                "links can be shared. The command palette (Ctrl K) jumps straight to any patient."),
              KeepTogether([user_flow_diagram(),
                            P("Figure 2. Screens and the paths between them. The patient chart is the hub.", "caption")])]
    story += [CondPageBreak(90 * mm),
              P("2.3 How an AI summary is built", "h2"),
              P("The summary is <b>extractive</b>: the engine computes facts from SQL rows, then writes them as sentences with citation tags. "
                "It does not invent text, so there is nothing for it to hallucinate."),
              summary_flow_diagram(),
              P("Figure 3. The eight steps behind one AI summary. Any write to a patient deletes that patient's cached summary, "
                "so step 2 never serves stale text.", "caption"),
              KeepTogether([P("2.4 How a plain-English question is answered", "h2"),
                            retrieval_flow_diagram(),
                            P("Figure 4. Retrieval turns a question into filters over stored rows, then ranks them.", "caption")])]
    story.append(PageBreak())

    # 3. Database
    story += [P("3. Database design", "h1"),
              P("Sixteen tables: thirteen core clinical and identity tables, plus a doctor–patient link table, an AI summary cache and an audit log. "
                "Every child record hangs off a visit, and every visit hangs off a patient, so nothing can be orphaned."),
              er_diagram(),
              P("Figure 5. Entity relationships. Arrows point from parent to child (one-to-many).", "caption"),
              table([
                  ["Group", "Tables", "Purpose"],
                  ["Identity", "roles, users, doctors", "Login, role (doctor or admin), specialisation and registration number"],
                  ["Patient", "patients, allergies, medical_history, patient_doctor", "Demographics with a unique MRN, long-term conditions, assigned doctors"],
                  ["Encounter", "visits, symptoms, diagnoses, prescriptions, clinical_notes, test_results",
                   "One visit with vitals, and its child rows: ICD-10 diagnoses, drugs, SOAP notes, labs"],
                  ["Catalogue", "medications", "Generic name, class, form and strength stored once, referenced by prescriptions"],
                  ["System", "ai_summaries, audit_logs", "Cached summaries keyed by a hash of the patient's rows; record of every action"],
              ], [24 * mm, 62 * mm, CONTENT_W - 86 * mm], zebra=True),
              P("Normalisation (3NF)", "h2"),
              *bullets([
                  "<b>1NF:</b> no lists in a column. Five symptoms are five rows in <font name=Courier>symptoms</font>, not one comma-separated field.",
                  "<b>2NF:</b> in the link table <font name=Courier>patient_doctor</font>, every column depends on the whole key (patient_id, doctor_id).",
                  "<b>3NF:</b> drug details live in <font name=Courier>medications</font>; a prescription stores only medication_id, dose and frequency. "
                  "Doctor details live in <font name=Courier>doctors</font>, not repeated on every visit.",
              ]),
              P("Rules the database itself enforces", "h2"),
              table([
                  ["Column", "Constraint"],
                  ["patients.sex", "Male, Female or Other"],
                  ["visits.visit_type", "OPD, Follow-up, Emergency or Telehealth"],
                  ["visits.vitals_hr / vitals_spo2", "Heart rate 20–300; SpO2 50–100"],
                  ["diagnoses.status", "Provisional, Confirmed, Controlled, Ruled-out or Resolved"],
                  ["symptoms.severity", "Mild, Moderate or Severe"],
                  ["test_results.flag", "Normal, High, Low, Critical or Abnormal"],
                  ["allergies.severity / status", "Mild to Life-Threatening; Active or Resolved"],
              ], [62 * mm, CONTENT_W - 62 * mm], zebra=True),
              Spacer(1, 4),
              P("Foreign keys are indexed, with composite indexes on (patient_id, visit_date) for timelines and (patient_id, records_hash) for the summary cache.", "small")]
    story.append(PageBreak())

    # 4. Features with screenshots
    story += [P("4. The application, screen by screen", "h1"),
              P("Sign in and overview", "h2"),
              P("Four demo accounts sit on the sign-in screen. After sign-in, the overview shows record counts, recent visits, "
                "labs outside their range, visits per month, how patients were seen and the most common diagnoses and symptoms. "
                "All of these numbers come from SQL <font name=Courier>COUNT</font> and <font name=Courier>GROUP BY</font> queries."),
              *screenshot("02-overview.jpg", "Figure 6. Overview for Dr. Ananya Sharma."),
              P("Patient chart", "h2"),
              P("The chart opens with allergies (always visible), then the vitals strip: heart rate and blood pressure from every visit, "
                "drawn on ECG chart paper with the normal range shaded and out-of-range readings in red. The timeline lists each visit with its "
                "diagnoses (ruled-out ones struck through), symptoms, prescriptions, results, plan and SOAP note."),
              *screenshot("04-chart-timeline.jpg", "Figure 7. Aarav Mehta’s chart: migraine storyline over four visits."),
              P("AI summary with citations", "h2"),
              P("The top line is a receipt: how many citations matched a stored record and the grounding score. Each tag opens "
                "the stored row in a side drawer. Any statement can be flagged for a doctor to review."),
              *screenshot("05-ai-summary.jpg", f"Figure 8. AI summary: {st['aarav_cites']} citations matched stored rows."),
              *screenshot("06-citation-inspector.jpg", "Figure 9. Clicking a tag opens the exact database row the AI used."),
              P("Missing data is reported, not guessed", "h2"),
              *screenshot("07-data-gaps.jpg", "Figure 10. Zoya Farooqui has no blood group or emergency number on file, and the summary says so."),
              P("Ask the records", "h2"),
              *screenshot("08-ask-the-records.jpg", "Figure 11. A cohort-wide question: the answer on the left, ranked source rows on the right."),
              *screenshot("09-refusal.jpg", "Figure 12. Asked about something never recorded, it returns zero matches and says so."),
              P("Recording a visit", "h2"),
              *screenshot("10-new-visit-extract.jpg", "Figure 13. Typing a note and pressing ‘Extract from note’ fills the symptom, diagnosis and drug rows for review."),
              P("Navigation and accountability", "h2"),
              *screenshot("11-command-palette.jpg", "Figure 14. Ctrl K finds any patient by name, MRN or condition."),
              *screenshot("12-audit-trail.jpg", "Figure 15. The audit trail lists every sign-in, change, summary and question."),
              *screenshot("13-chart-dark.jpg", "Figure 16. Full dark theme.")]
    story.append(PageBreak())

    # 5. Data
    dx_rows = [["Diagnosis", "Times recorded"]] + [[n, str(c)] for n, c in st["top_dx"]]
    vt_rows = [["Visit type", "Visits"]] + [[t, str(c)] for t, c in st["visit_types"]]
    story += [P("5. The synthetic patient data", "h1"),
              P(f"The database holds {st['patients']} fictional patients from {st['cities']} towns and cities. Six were written by hand "
                "as detailed storylines (for example Aarav Mehta’s migraine and Zoya Farooqui’s rheumatoid arthritis with missing fields). "
                "The rest come from a generator in <font name=Courier>backend/app/db/cohort.py</font> with a fixed random seed, so every "
                "deployment gets exactly the same people."),
              *bullets([
                  "<b>Names fit their region.</b> A Telugu first name gets a Telugu surname and a Hyderabad or Vijayawada address with a real PIN code. "
                  "Fourteen groups are covered, from Punjabi and Bengali to Malayali, Assamese and Sikkimese.",
                  "<b>Conditions fit Indian OPDs.</b> 23 storylines: diabetes with hypertension, CKD, heart attack, fatty liver, TB on HRZE, dengue in the "
                  "monsoon, typhoid, malaria, chikungunya, child diarrhoea, tonsillitis, UTI, thyroid, PCOS, anaemia, gestational diabetes, "
                  "vitamin deficiency, asthma, COPD from cooking smoke, knee arthritis, acidity with H. pylori and depression.",
                  "<b>Built to exercise the AI.</b> Symptoms recur across visits, diagnoses move from provisional to confirmed or ruled out, "
                  "lab values trend (HbA1c falling, platelets dipping then recovering), and about 6% of patients have no blood group so the "
                  f"gap detector has something to find ({st['no_blood_group']} right now).",
              ])]
    two = Table([[table(dx_rows, [72 * mm, 22 * mm], zebra=True), table(vt_rows, [42 * mm, 22 * mm], zebra=True)]],
                colWidths=[100 * mm, CONTENT_W - 100 * mm])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [Spacer(1, 6), two, P("Most recorded diagnoses (excluding ruled-out) and visit types, read from the database when this report was built.", "caption")]

    # 6. Stack, security, testing
    story += [P("6. Technology, security and testing", "h1"),
              table([
                  ["Layer", "Choice", "Why"],
                  ["Frontend", "React 18, TypeScript, Vite, Tailwind CSS", "Typed components, fast builds, design tokens for light and dark themes"],
                  ["Backend", "Python, FastAPI, Pydantic", "Request validation, automatic API docs at /docs, fast to write"],
                  ["Database", "SQLAlchemy ORM on SQLite", "Zero setup for evaluation; switching to PostgreSQL is a DATABASE_URL change"],
                  ["AI", "Own grounded engine; optional Gemini", "Facts come from SQL; an LLM may only reword the overview, and only for synthetic records"],
                  ["Hosting", "Vercel", "Static frontend on CDN, backend as a serverless function"],
              ], [24 * mm, 56 * mm, CONTENT_W - 80 * mm], zebra=True),
              P("Security and privacy", "h2"),
              *bullets([
                  "Passwords are hashed with bcrypt. Login returns a signed JWT that every API call must carry.",
                  "The token lives in sessionStorage, so it is cleared when the tab closes.",
                  "Role checks on write endpoints (doctor or admin).",
                  "Every sign-in, record change, AI summary and question is written to <font name=Courier>audit_logs</font>.",
                  "All records are flagged <font name=Courier>is_synthetic</font>; external AI is only allowed for synthetic data unless explicitly enabled.",
              ]),
              P("Tests and checks", "h2"),
              table([
                  ["Suite", "What it proves"],
                  ["Backend, pytest (7 tests)", "401 on missing or forged tokens; 422 on bad input; 404 on unknown IDs; dashboard counts update after a new visit; "
                   "summaries have a 1.0 grounding score, flag missing blood group and diagnostic revisions, and refresh after a new allergy; "
                   "retrieval finds headaches and refuses ‘Ebola’; note extraction finds symptom, diagnosis and drug"],
                  ["Frontend, vitest (7 tests)", "Token stored only in sessionStorage; overview counts and theme toggle; patient search, filters and empty state; "
                   "editing a profile and adding an allergy; citation drawer and flagging; record search with refusal; command palette navigation"],
                  ["Build", "TypeScript compiles with no errors; production bundle about 77 kB gzipped"],
                  ["Whole cohort", f"All {st['patients']} AI summaries generated with every citation verified"],
              ], [42 * mm, CONTENT_W - 42 * mm], zebra=True),
              Spacer(1, 4),
              P("Performance fix: questions across all patients loaded every child table in one joined query, which multiplied rows. Switching to "
                "<font name=Courier>selectinload</font> (one query per table) cut a cohort question from 1.2 s to 0.2 s.", "small")]
    story.append(PageBreak())

    # 7. Demo script
    story += [P("7. Five-minute demo script", "h1"),
              table([
                  ["Step", "Do this", "Say this"],
                  ["1", "Sign in as Dr. Ananya Sharma.", "Passwords are bcrypt-hashed; the session is a JWT kept in sessionStorage."],
                  ["2", "Point at the overview counts and charts.", "Every number here is a SQL COUNT or GROUP BY over the live tables."],
                  ["3", "Patients → search ‘dengue’.", f"{st['patients']} synthetic Indian patients; search covers name, MRN, mobile, condition and allergy."],
                  ["4", "Open Aarav Mehta (MRN-2026-00001).", "Allergy always on top. The vitals strip is drawn from his four visits. Tension headache was ruled out, then migraine confirmed."],
                  ["5", "AI summary tab → click [SYM-1] → close → flag a line.", f"{st['aarav_cites']} citations verified. The drawer shows the exact row. Doctors can flag anything doubtful."],
                  ["6", "Open Zoya Farooqui (MRN-2026-00006) → AI summary.", "Her blood group and emergency number are missing, and the AI reports that instead of guessing."],
                  ["7", "Ask the records → a dengue question, then ‘Ebola’ for Aarav.", "Answers come with source rows. For Ebola it returns zero matches: no hallucination."],
                  ["8", "Aarav → New visit → type a note → Extract from note.", "The note is parsed into symptom, diagnosis and drug rows for the doctor to check before saving."],
                  ["9", "Press Ctrl K; open Audit trail.", "Fast navigation; and every action is logged with who and when."],
              ], [11 * mm, 62 * mm, CONTENT_W - 73 * mm], zebra=True),
              Spacer(1, 6),
              callout("Demo logins: every doctor uses password <b>Doctor@123</b> (for example dr.sharma@medvault.edu); "
                      "the admin is admin@medvault.edu with <b>Admin@123</b>.", "ok")]

    # 8. Questions
    qa = [
        ("Why a relational database and not MongoDB?",
         "Medical records are strongly linked: a prescription belongs to a visit, which belongs to a patient. Foreign keys stop orphan rows, "
         "transactions save a visit and all its children together or not at all, and SQL GROUP BY gives the dashboard numbers directly."),
        ("How does the AI avoid hallucinating?",
         "It is extractive. It computes facts from rows (counts, status changes, lab trends), writes each as a sentence with the row's tag, and a "
         "validator drops any sentence whose tag is not a real row. The UI shows the verified count. When data is missing it says ‘not recorded’."),
        ("What if a new visit is added? Is the summary stale?",
         "No. Any write to a patient deletes that patient's cached summary, and the cache key is a SHA-256 hash of the patient's rows, so a "
         "changed record can never match an old cache entry. The pytest suite checks this."),
        ("How does the plain-English search work?",
         "It reads date words (‘last two years’, ‘2026’), the kind of record asked about (diagnosis, drug, lab), removes filler words, expands "
         "medical synonyms (dengue → NS1, platelet), scores every stored row, and returns the top 25 with citations, or an explicit refusal."),
        ("Where is the data from?",
         "It is synthetic. A seeded generator builds region-consistent Indian names and addresses and 23 clinical courses. No real patient data is used."),
        ("What is ICD-10 and a SOAP note?",
         "ICD-10 is the WHO's code list for diseases (I10 is hypertension, A97.1 is dengue with warning signs). SOAP is the standard note format: "
         "Subjective (what the patient says), Objective (exam and vitals), Assessment (diagnosis), Plan (treatment)."),
        ("How would it scale to a real hospital?",
         "Point DATABASE_URL at PostgreSQL, keep the existing indexes, add server-side pagination to the patient list, and move retrieval to "
         "full-text search or vector search. The API and UI would not need to change."),
        ("What are the limits?",
         "Retrieval is keyword and synonym based, so it can miss unusual phrasing. Data is synthetic. There is no FHIR/HL7 export or imaging yet; "
         "those, plus vector search, are the next steps."),
    ]
    story += [P("8. Questions the examiner may ask", "h1")]
    for q, a in qa:
        story.append(KeepTogether([P(q, "q"), P(a)]))

    # 9. Repository map
    story += [CondPageBreak(70 * mm), P("9. Where things live in the code", "h1"),
              table([
                  ["Path", "Contents"],
                  ["backend/app/models/__init__.py", "All 16 tables, relationships and CHECK constraints"],
                  ["backend/app/routers/", "auth, dashboard, patients and ai endpoints"],
                  ["backend/app/ai/engine.py", "Summary builder, citation validator, retrieval, note extraction"],
                  ["backend/app/db/seed_data.py, cohort*.py", "Six hand-written storylines and the generated Indian cohort"],
                  ["frontend/src/features/", "Screens: sign-in, overview, patients, chart tabs, record search, audit"],
                  ["frontend/src/components/", "Design system, vitals strip, charts, citation drawer, command palette, logo"],
                  ["backend/tests, frontend/src/__tests__", "pytest and vitest suites"],
                  ["docs/", "This report, screenshots, SQL schema"],
              ], [70 * mm, CONTENT_W - 70 * mm], zebra=True)]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=18 * mm, bottomMargin=17 * mm,
                            title="MedVault AI: project report and flow", author="Pushkar Panwar and Saksham Singh")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")
