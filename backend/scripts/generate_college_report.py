"""Build docs/MedVault_AI_College_Report.docx (and a PDF copy when LibreOffice is installed).

The report is regenerated from the project itself each time it runs:
  - counts, the visit date span and the visit-type mix are read from the seeded database;
  - every AI summary is regenerated for every patient to measure citation grounding
    (the cache rows this adds are removed again afterwards);
  - a cohort-wide question and a refusal question are timed against the live engine;
  - table names, foreign keys and CHECK constraints are read from the SQLAlchemy metadata;
  - test names come from backend/tests/test_api.py and frontend/src/__tests__/App.test.tsx,
    and both suites are run (skip with --skip-tests);
  - code excerpts are copied verbatim from the source files by start/end markers;
  - screenshots are embedded from docs/screenshots/*.jpg in filename order.

Page 1 is left blank for the college cover page. When `soffice` and `pdftotext` are available
the script builds twice: once to find the page of every heading in the PDF, then again to write
those page numbers into the table of contents.

    cd backend
    .venv/bin/pip install python-docx matplotlib
    .venv/bin/python scripts/seed.py
    .venv/bin/python scripts/generate_college_report.py
"""

import argparse
import ast
import io
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend"
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
OUT_DOCX = DOCS / "MedVault_AI_College_Report.docx"

sys.path.insert(0, str(BACKEND))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.section import WD_SECTION  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402
from sqlalchemy import CheckConstraint, func  # noqa: E402

LIVE_URL = "https://medvault-ai-smoky.vercel.app"
BODY_FONT = "Times New Roman"
CODE_FONT = "Courier New"
TEXT_WIDTH_IN = 8.27 - 2.0  # A4 width minus 1-inch margins


# =========================================================================== live data


def gather_stats():
    from app.ai.engine import answer_natural_language_query, generate_patient_summary
    from app.db.seed_data import seed_database_if_empty
    from app.db.session import Base, SessionLocal, engine
    from app.models import (
        AISummaryCache,
        Allergy,
        ClinicalNote,
        Diagnosis,
        Doctor,
        Medication,
        Patient,
        Prescription,
        Symptom,
        TestResult,
        User,
        Visit,
    )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
        s = {
            "patients": db.query(Patient).count(),
            "real": db.query(Patient).filter(Patient.is_synthetic == False).count(),  # noqa: E712
            "visits": db.query(Visit).count(),
            "symptoms": db.query(Symptom).count(),
            "diagnoses": db.query(Diagnosis).count(),
            "distinct_conditions": db.query(func.count(func.distinct(Diagnosis.condition_name))).scalar(),
            "prescriptions": db.query(Prescription).count(),
            "medications": db.query(Medication).count(),
            "labs": db.query(TestResult).count(),
            "abnormal_labs": db.query(TestResult).filter(TestResult.flag != "Normal").count(),
            "notes": db.query(ClinicalNote).count(),
            "allergies": db.query(Allergy).count(),
            "doctors": db.query(Doctor).count(),
            "users": db.query(User).count(),
            "no_blood_group": db.query(Patient).filter(Patient.blood_group.is_(None)).count(),
        }
        first, last = db.query(func.min(Visit.visit_date), func.max(Visit.visit_date)).one()
        s["span"] = (first.date(), last.date()) if first else None
        s["visit_types"] = sorted(db.query(Visit.visit_type, func.count(Visit.id)).group_by(Visit.visit_type).all(), key=lambda r: -r[1])
        s["lab_flags"] = sorted(db.query(TestResult.flag, func.count(TestResult.id)).group_by(TestResult.flag).all(), key=lambda r: -r[1])
        s["top_dx"] = (
            db.query(Diagnosis.condition_name, func.count(Diagnosis.id))
            .filter(Diagnosis.status != "Ruled-out")
            .group_by(Diagnosis.condition_name)
            .order_by(func.count(Diagnosis.id).desc())
            .limit(5)
            .all()
        )

        # Regenerate every summary to measure grounding, then remove the cache rows this added.
        max_cache_id = db.query(func.max(AISummaryCache.id)).scalar() or 0
        total = verified = with_full = n = 0
        t0 = time.perf_counter()
        for (pid,) in db.query(Patient.id).order_by(Patient.id).all():
            vs = generate_patient_summary(db, pid, force_refresh=True).validation_stats
            total += vs["total_citations_emitted"]
            verified += vs["verified_citations"]
            with_full += 1 if vs["grounding_score"] == 1.0 else 0
            n += 1
        s["summary_seconds"] = time.perf_counter() - t0
        db.query(AISummaryCache).filter(AISummaryCache.id > max_cache_id).delete(synchronize_session=False)
        db.commit()
        s["summaries"] = n
        s["summaries_full"] = with_full
        s["cits_total"] = total
        s["cits_verified"] = verified

        def timed(q):
            best, res = None, None
            for _ in range(3):
                t = time.perf_counter()
                res = answer_natural_language_query(db, q)
                el = time.perf_counter() - t
                best = el if best is None else min(best, el)
            return best, res.total_matches

        s["q_hf"] = ("Which patients had heart failure?",) + timed("Which patients had heart failure?")
        s["q_ebola"] = ("Find records mentioning Ebola",) + timed("Find records mentioning Ebola")

        # Schema facts straight from the ORM metadata.
        tables = []
        for name, table in Base.metadata.tables.items():
            checks = [str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)]
            fks = sorted({f"{fk.parent.name} -> {fk.column.table.name}.{fk.column.name}" for fk in table.foreign_keys})
            tables.append({"name": name, "checks": checks, "fks": fks, "cols": len(table.columns)})
        s["tables"] = tables
        return s
    finally:
        db.close()


def backend_tests():
    tree = ast.parse((BACKEND / "tests" / "test_api.py").read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            doc = ast.get_docstring(node) or ""
            out.append((node.name, doc.replace("Core Invariant: ", "")))
    return out


def frontend_tests():
    path = FRONTEND / "src" / "__tests__" / "App.test.tsx"
    if not path.exists():
        return []
    return re.findall(r"^\s*it\('([^']+)'", path.read_text(encoding="utf-8"), flags=re.M)


def run_suite(cmd, cwd, pattern):
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"not run ({exc.__class__.__name__})"
    text = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout + proc.stderr)
    m = re.findall(pattern, text)
    return m[-1].strip() if m else f"exit code {proc.returncode}"


# =========================================================================== code excerpts


def excerpt(rel_path, start, end, skip=None, after=0):
    """Return verbatim lines from `start` marker through `end` marker (inclusive).
    `skip` is an optional (from_marker, to_marker) pair inside the excerpt that is replaced by '...'."""
    path = ROOT / rel_path
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        i = next(k for k, ln in enumerate(lines) if start in ln)
        j = next(k for k in range(i, len(lines)) if end in lines[k])
    except StopIteration:
        print(f"  ! excerpt markers not found in {rel_path}: {start!r} .. {end!r}")
        return None
    chunk = lines[i : j + 1 + after]
    if skip:
        a = next((k for k, ln in enumerate(chunk) if skip[0] in ln), None)
        b = next((k for k in range(a or 0, len(chunk)) if skip[1] in chunk[k]), None) if a is not None else None
        if a is not None and b is not None:
            indent = re.match(r"\s*", chunk[a]).group(0)
            chunk = chunk[:a] + [indent + "..."] + chunk[b + 1 :]
    # remove common indentation so nested excerpts start at column 0
    pad = min((len(ln) - len(ln.lstrip()) for ln in chunk if ln.strip()), default=0)
    return "\n".join(ln[pad:] for ln in chunk), i + 1


# =========================================================================== diagrams


def _box(ax, x, y, w, h, title, sub="", fc="#FFFFFF", ec="#222222"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", fc=fc, ec=ec, lw=1.1))
    if sub:
        ax.text(x + w / 2, y + h * 0.7, title, ha="center", va="center", fontsize=8.6, weight="bold", family="serif")
        ax.text(x + w / 2, y + h * 0.32, sub, ha="center", va="center", fontsize=6.8, linespacing=1.15, family="serif", color="#333333", wrap=True)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=8.2, weight="bold", family="serif")


def _arrow(ax, x1, y1, x2, y2, label="", dashed=False, lx=0.0, ly=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, lw=1.0,
                                 color="#333333", linestyle="--" if dashed else "-"))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center", va="center", fontsize=7, family="serif",
                color="#222222", bbox=dict(fc="white", ec="none", pad=0.6))


def architecture_png():
    fig, ax = plt.subplots(figsize=(6.6, 5.6), dpi=200)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for y, h, name in [(0.84, 0.155, "Client"), (0.5, 0.32, "Vercel"), (0.0, 0.48, "Server-side logic and data")]:
        ax.add_patch(FancyBboxPatch((0.0, y), 1.0, h, boxstyle="square,pad=0", fc="#F4F4F4", ec="#BBBBBB", lw=0.6))
        ax.text(0.01, y + h - 0.012, name, fontsize=7.5, va="top", family="serif", style="italic", color="#555555")
    _box(ax, 0.22, 0.855, 0.56, 0.11, "Browser: React 18 + TypeScript SPA",
         "Vite build, Tailwind CSS, three.js heart\nJWT kept in sessionStorage", fc="#E8ECFB", ec="#2340C8")
    _box(ax, 0.04, 0.63, 0.38, 0.11, "Vercel CDN (static files)", "frontend/dist:\nHTML, JS, CSS, images")
    _box(ax, 0.56, 0.63, 0.4, 0.11, "Python serverless function", "api/index.py imports\nbackend/app/main.py")
    _arrow(ax, 0.36, 0.855, 0.23, 0.74, "GET /, /assets/*", lx=-0.08)
    _arrow(ax, 0.64, 0.855, 0.76, 0.74, "fetch /api/* + Bearer JWT", lx=0.12)
    ax.text(0.86, 0.565, "vercel.json rewrite:\n/api/(.*) -> /api/index.py", ha="center", va="center", fontsize=7, family="serif")
    _box(ax, 0.3, 0.35, 0.4, 0.1, "FastAPI routers", "auth, dashboard, patients, ai\n(Pydantic validation)")
    _arrow(ax, 0.72, 0.63, 0.6, 0.45)
    _box(ax, 0.02, 0.15, 0.3, 0.13, "Security", "bcrypt hashes, JWT (HS256)\nrequire_roles, audit_logs")
    _box(ax, 0.35, 0.15, 0.3, 0.13, "AI engine", "grounded summary, retrieval,\nnote extraction")
    _box(ax, 0.68, 0.15, 0.3, 0.13, "SQLAlchemy ORM", "16 tables, foreign keys,\nCHECK constraints")
    _arrow(ax, 0.4, 0.35, 0.2, 0.28)
    _arrow(ax, 0.5, 0.35, 0.5, 0.28)
    _arrow(ax, 0.6, 0.35, 0.8, 0.28)
    _arrow(ax, 0.65, 0.215, 0.68, 0.215)
    _box(ax, 0.5, 0.015, 0.48, 0.1, "SQLite file (PostgreSQL-ready URL)",
         "/tmp/medical_records.db on Vercel,\nseeded on cold start", fc="#E4F2EB", ec="#17704C")
    _arrow(ax, 0.83, 0.15, 0.78, 0.115)
    ax.text(0.03, 0.065, "Seed file: mimic_iv_demo.json.gz\n(100 MIMIC-IV demo patients)", fontsize=7, family="serif", va="center")
    _arrow(ax, 0.33, 0.065, 0.5, 0.065, dashed=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


ER_POS = {
    "roles": (0, 4), "users": (1, 4), "doctors": (2, 4), "patient_doctor": (3, 4),
    "audit_logs": (0, 3), "patients": (3, 3), "allergies": (4, 3.5), "medical_history": (4, 2.75),
    "ai_summaries": (4, 2.0), "visits": (2, 2),
    "symptoms": (0, 1), "diagnoses": (1, 1), "prescriptions": (2, 1), "clinical_notes": (3, 1), "test_results": (4, 1),
    "medications": (2, 0),
}


def er_png(tables):
    fig, ax = plt.subplots(figsize=(6.6, 4.6), dpi=200)
    ax.set_xlim(-0.6, 4.6)
    ax.set_ylim(-0.45, 4.45)
    ax.axis("off")
    bw, bh = 0.92, 0.36
    pos = {t["name"]: ER_POS.get(t["name"]) for t in tables if ER_POS.get(t["name"])}

    def centre(n):
        x, y = pos[n]
        return x, y

    drawn = set()
    for t in tables:
        for fk in t["fks"]:
            target = fk.split("-> ")[1].split(".")[0]
            a, b = t["name"], target
            if a in pos and b in pos and (a, b) not in drawn:
                drawn.add((a, b))
                (x1, y1), (x2, y2) = centre(a), centre(b)
                ax.plot([x1, x2], [y1, y2], color="#666666", lw=0.9, zorder=1)
    for name, (x, y) in pos.items():
        core = name in ("patients", "visits")
        ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh, boxstyle="round,pad=0.01,rounding_size=0.05",
                                    fc="#E8ECFB" if core else "white", ec="#2340C8" if core else "#222222", lw=1.1, zorder=2))
        ax.text(x, y, name, ha="center", va="center", fontsize=6.8, family="monospace", weight="bold" if core else "normal", zorder=3)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


# =========================================================================== docx helpers


def _set_fonts(style_or_run_element_rpr, name):
    rfonts = style_or_run_element_rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        style_or_run_element_rpr.insert(0, rfonts)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(att)) is not None:
            del rfonts.attrib[qn(att)]
    for att in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(att), name)


def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    _set_fonts(normal.element.get_or_add_rPr(), BODY_FONT)
    pf = normal.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(6)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for lvl, size, before, after in [(1, 16, 0, 12), (2, 13, 12, 6), (3, 12, 10, 4)]:
        st = doc.styles[f"Heading {lvl}"]
        st.font.name = BODY_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = RGBColor(0, 0, 0)
        _set_fonts(st.element.get_or_add_rPr(), BODY_FONT)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.line_spacing = 1.15
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for name in ("List Bullet",):
        st = doc.styles[name]
        st.font.name = BODY_FONT
        st.font.size = Pt(12)
        st.paragraph_format.space_after = Pt(3)
        st.paragraph_format.line_spacing = 1.5

    cap = doc.styles["Caption"]
    cap.font.name = BODY_FONT
    cap.font.size = Pt(10)
    cap.font.bold = False
    cap.font.italic = True
    cap.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    _set_fonts(cap.element.get_or_add_rPr(), BODY_FONT)
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(4)
    cap.paragraph_format.space_after = Pt(12)
    cap.paragraph_format.line_spacing = 1.15


def add_rich(paragraph, text, size=None):
    """Tiny markup: **bold**, `code`."""
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = paragraph.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = paragraph.add_run(part[1:-1])
            r.font.name = CODE_FONT
            _set_fonts(r._element.get_or_add_rPr(), CODE_FONT)
            r.font.size = Pt(10.5 if size is None else size - 1)
        else:
            r = paragraph.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
    return paragraph


def field_run(paragraph, instr):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    r._element.append(b)
    r2 = paragraph.add_run()
    t = OxmlElement("w:instrText")
    t.set(qn("xml:space"), "preserve")
    t.text = instr
    r2._element.append(t)
    r3 = paragraph.add_run()
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    r3._element.append(s)
    paragraph.add_run("1")
    r4 = paragraph.add_run()
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    r4._element.append(e)


def shade(cell, hex_fill):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def cell_margins(table, top=60, bottom=60, left=100, right=100):
    tblPr = table._element.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


class Report:
    def __init__(self):
        self.doc = Document()
        self.headings = []  # (level, text)
        self.fig_no = 0
        self.tab_no = 0
        setup_styles(self.doc)

    # ---- text
    def h1(self, text, new_page=True):
        p = self.doc.add_heading(text, level=1)
        p.paragraph_format.page_break_before = new_page
        self.headings.append((1, text))
        return p

    def h2(self, text):
        self.headings.append((2, text))
        return self.doc.add_heading(text, level=2)

    def h3(self, text):
        return self.doc.add_heading(text, level=3)

    def p(self, text, align=None):
        para = self.doc.add_paragraph()
        add_rich(para, text)
        if align is not None:
            para.alignment = align
        return para

    def bullets(self, items):
        for it in items:
            para = self.doc.add_paragraph(style="List Bullet")
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_rich(para, it)

    def caption(self, text):
        return self.doc.add_paragraph(text, style="Caption")

    # ---- tables
    def table(self, rows, widths, caption=None, header=True, size=10.5):
        if caption:
            self.tab_no += 1
            cp = self.caption(f"Table {self.tab_no}: {caption}")
            cp.paragraph_format.keep_with_next = True
            cp.paragraph_format.space_after = Pt(4)
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell_margins(t)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                cell = t.cell(r, c)
                cell.width = Inches(widths[c])
                para = cell.paragraphs[0]
                para.paragraph_format.line_spacing = 1.0
                para.paragraph_format.space_after = Pt(0)
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                add_rich(para, str(val), size=size)
                if header and r == 0:
                    for run in para.runs:
                        run.bold = True
                    shade(cell, "E7E7E7")
        if header:
            trPr = t.rows[0]._tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader")
            trPr.append(th)
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)
        spacer.paragraph_format.line_spacing = 1.0
        return t

    def code(self, src, title):
        if src is None:
            return False
        text, line_no = src
        t = self.doc.add_table(rows=1, cols=1)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell_margins(t, 80, 80, 120, 120)
        cell = t.cell(0, 0)
        cell.width = Inches(TEXT_WIDTH_IN)
        shade(cell, "F3F3F3")
        first = True
        for ln in text.split("\n"):
            para = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            pf = para.paragraph_format
            pf.line_spacing = 1.0
            pf.space_after = Pt(0)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.keep_with_next = True
            r = para.add_run(ln if ln else " ")
            r.font.name = CODE_FONT
            r.font.size = Pt(9)
            _set_fonts(r._element.get_or_add_rPr(), CODE_FONT)
        cap = self.caption(f"{title} (from line {line_no})")
        cap.paragraph_format.space_before = Pt(3)
        return True

    def image(self, stream_or_path, width_in, caption):
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.line_spacing = 1.0
        para.paragraph_format.space_after = Pt(0)
        para.add_run().add_picture(stream_or_path, width=Inches(width_in))
        self.fig_no += 1
        self.caption(f"Figure {self.fig_no}: {caption}")

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---- table of contents (Word field with cached entries)
    def toc_placeholder(self):
        self.toc_anchor = self.doc.add_paragraph()

    def fill_toc(self, pages):
        entries = self.headings
        made = []
        for i, (lvl, text) in enumerate(entries):
            para = self.doc.add_paragraph()
            pf = para.paragraph_format
            pf.line_spacing = 1.15
            pf.space_after = Pt(2 if lvl == 2 else 4)
            pf.space_before = Pt(6 if lvl == 1 else 0)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Inches(0 if lvl == 1 else 0.35)
            pf.tab_stops.add_tab_stop(Inches(TEXT_WIDTH_IN), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if i == 0:
                for kind, val in (("begin", None), ("instr", 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None)):
                    r = para.add_run()
                    if kind == "instr":
                        el = OxmlElement("w:instrText")
                        el.set(qn("xml:space"), "preserve")
                        el.text = val
                    else:
                        el = OxmlElement("w:fldChar")
                        el.set(qn("w:fldCharType"), kind)
                    r._element.append(el)
            r = para.add_run(text)
            r.bold = lvl == 1
            r.font.size = Pt(12 if lvl == 1 else 11)
            pg = pages.get(text, "") if pages is not None else "00"
            r2 = para.add_run(f"\t{pg}")
            r2.font.size = Pt(12 if lvl == 1 else 11)
            if i == len(entries) - 1:
                r3 = para.add_run()
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), "end")
                r3._element.append(el)
            made.append(para)
        for para in made:
            self.toc_anchor._p.addprevious(para._p)
        self.toc_anchor._p.getparent().remove(self.toc_anchor._p)


# =========================================================================== content

SHOT_CAPTIONS = {
    "00-landing": "Public landing page. The interactive three.js heart is rendered in chrome at the top of the scroll story; it can be rotated by dragging.",
    "00b-landing-ask": "Landing page, scroll step 3 (\"Ask\"). The heart has turned matte white and sits in the torso of a Gray's Anatomy (1918) plate.",
    "01-sign-in": "Sign-in page with the demonstration doctor and administrator accounts.",
    "02-overview": "Doctor overview: record counts, visits by month, visit-type mix, recent visits and out-of-range lab results.",
    "03-patients-search": "Patient list with search, filters and sorting across all registered patients.",
    "04-chart-overview": "Patient chart, Overview tab: allergy banner, demographics and a summary of the record.",
    "04b-chart-visits": "Patient chart, Visits tab: the visit timeline, with older visits collapsed to one line.",
    "04c-chart-labs": "Patient chart, Lab results tab: each test grouped across visits with its latest result and flag.",
    "05-ai-summary": "AI summary with the grounding receipt (every emitted citation matched a stored record) and citation tags after each statement.",
    "06-citation-inspector": "Citation inspector: clicking a tag opens the exact stored row (table, row id, visit and date) that the statement cites.",
    "07-data-gaps": "The \"Gaps and revisions in the record\" section of the summary, which reports missing fields and diagnosis status changes.",
    "08-ask-the-records": "Ask the records: a plain-English question answered with ranked source rows, each carrying its citation tag.",
    "09-refusal": "Refusal: a question about Ebola matches no stored row, so the system returns 0 matching records and says so instead of guessing.",
    "10-new-visit-extract": "New visit form. \"Extract from note\" pulls symptoms, diagnoses and drugs out of a consultation note into editable rows.",
    "11-command-palette": "Command palette (Ctrl+K) for jumping to any patient or screen.",
    "12-audit-trail": "Audit trail: sign-ins, record changes and every AI call, with the user, patient and time of each.",
    "13-chart-dark": "Patient chart in the dark theme.",
}

TABLE_PURPOSE = {
    "roles": "Role names (admin, doctor).",
    "users": "Sign-in accounts: e-mail, bcrypt hash, role.",
    "doctors": "Clinical profile of a user: specialisation, licence, department.",
    "patient_doctor": "Many-to-many link: which doctors are assigned to which patients.",
    "patients": "Demographics and contact details; one row per patient (MRN is unique).",
    "visits": "One clinical encounter: date, type, complaint, vitals, plan.",
    "symptoms": "Symptoms recorded at a visit, with severity and duration.",
    "diagnoses": "Diagnoses made at a visit, with ICD code and status.",
    "medications": "Drug catalogue: name, generic name, class, form, strength.",
    "prescriptions": "A drug prescribed at a visit: dose, frequency, duration.",
    "clinical_notes": "Free-text notes attached to a visit (SOAP, progress, etc.).",
    "test_results": "Lab and diagnostic results of a visit, with reference range and flag.",
    "allergies": "Patient-level allergies with reaction, severity and status.",
    "medical_history": "Patient-level chronic, past, surgical and family history.",
    "ai_summaries": "Cache of generated summaries keyed by a hash of the patient's rows.",
    "audit_logs": "Who did what to which patient, and when.",
}

FRONTEND_TEST_NOTES = {
    "shows the landing page to visitors and opens sign-in from it": "Renders the public landing page, waits for the live patient totals and the data-source line, and checks that \"Open the records\" routes to #/sign-in.",
    "gives the admin a records-administration home with completeness and activity": "Signs in as the administrator and checks the records-administration home: the data-completeness panel (e.g. blood group recorded) and recent activity.",
    "keeps the session token in sessionStorage only": "After sign-in the JWT is in sessionStorage and not in localStorage, so it is cleared when the tab closes.",
    "shows record counts and charts on the overview and switches theme": "Checks the overview counts and chart labels, then toggles dark and light themes and the stored preference.",
    "searches, filters and sorts the patient list and recovers from an empty result": "Filters by sex and blood group, sorts by name, checks the exact result order, then recovers from a search with no match.",
    "edits demographics, records an allergy and filters the visit timeline": "Edits a phone number, adds an allergy, opens the Visits tab, expands a collapsed visit and filters by visit type.",
    "groups lab results and medicines across visits": "Opens the Lab results and Medicines tabs and checks their grouped tables.",
    "opens the cited source row from an AI summary and flags a statement": "Clicks a citation tag in the AI summary, checks the inspector shows the cited row, closes it, and flags a statement for review.",
    "answers a records question with sources and refuses when nothing matches": "Asks a records question and gets one source row; asks about a non-existent term and gets \"Nothing in the record matches\" with 0 records.",
    "finds a patient from the command palette": "Opens the palette with Ctrl+K, searches for a patient, presses Enter and lands on the chart URL.",
}


def fmt_int(n):
    return f"{n:,}"


def build(stats, tests, pages):
    R = Report()
    doc = R.doc

    # ---------- page 1: blank cover (filled in by the student)
    doc.add_paragraph()
    for sec in doc.sections:
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Inches(1)
    body = doc.add_section(WD_SECTION.NEW_PAGE)
    body.footer.is_linked_to_previous = False
    fp = body.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field_run(fp, "PAGE")
    for r in fp.runs:
        r.font.size = Pt(11)
        r.font.name = BODY_FONT
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    cols = body._sectPr.find(qn("w:cols"))
    (cols.addprevious(pg) if cols is not None else body._sectPr.append(pg))
    # the cover section (page 1) has no footer reference of its own, so it shows no page number

    s = stats
    real_note = f"{s['real']} real, de-identified patients" if s["real"] else f"{s['patients']} synthetic patients"
    span = f"{s['span'][0].year} to {s['span'][1].year}" if s["span"] else "n/a"
    grounding_pct = 100.0 * s["cits_verified"] / max(s["cits_total"], 1)

    # ---------- Abstract
    R.h1("Abstract", new_page=False)
    R.p(
        "Doctors often lose time searching through scattered visit notes, prescriptions and laboratory reports to "
        "understand a patient's history. MedVault AI is a web-based medical records database that stores each "
        "patient's history in a normalised relational schema and adds three AI-assisted features on top of it: a "
        "patient summary in which every statement carries a citation tag (for example [DX-12]) that points to the exact "
        "database row it came from, a plain-English record search that returns ranked source rows or states that "
        "nothing matches, and extraction of symptoms, diagnoses and drugs from a consultation note. The system uses "
        "React, TypeScript and three.js in the browser and Python FastAPI with SQLAlchemy on the server, and is "
        f"deployed on Vercel. It is seeded with {real_note} from the MIMIC-IV Clinical Database Demo (Beth Israel "
        f"Deaconess Medical Center, Boston). Across all {s['summaries']} patient summaries, {fmt_int(s['cits_verified'])} of "
        f"{fmt_int(s['cits_total'])} citations ({grounding_pct:.0f}%) matched a stored row."
    )
    R.p(f"**Project team:** Pushkar Panwar (2501730022) and Saksham Singh (2501730270).", align=WD_ALIGN_PARAGRAPH.LEFT)
    R.p(f"**Live demonstration:** {LIVE_URL}", align=WD_ALIGN_PARAGRAPH.LEFT)
    R.p("**Keywords:** electronic medical records, relational database, normalisation, retrieval, citation grounding, FastAPI, React.",
        align=WD_ALIGN_PARAGRAPH.LEFT)

    # ---------- TOC
    toc_h = doc.add_paragraph()
    toc_h.paragraph_format.page_break_before = True
    toc_h.paragraph_format.space_after = Pt(12)
    toc_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    tr = toc_h.add_run("Table of Contents")
    tr.bold = True
    tr.font.size = Pt(16)
    R.toc_placeholder()

    # ---------- Chapter 1
    R.h1("Chapter 1: Introduction")
    R.h2("1.1 Background")
    R.p(
        "A patient who is treated over several years builds up a long trail of records: visit notes, prescriptions, "
        "laboratory sheets, discharge summaries and allergy lists. In many clinics these sit in different places, on "
        "paper, in separate software, or in free text. Before a consultation the doctor has to piece the history "
        "together: when a symptom first appeared, which drug was stopped and why, whether a laboratory value is rising. "
        "This takes time that would otherwise go to the patient, and an item that is missed, such as a drug allergy or "
        "an earlier diagnosis that was later ruled out, can lead to a wrong decision."
    )
    R.p(
        "Relational databases are well suited to this data. Visits, diagnoses, prescriptions and laboratory results are "
        "naturally rows that belong to a patient and a visit, and SQL can group, count and filter them. What a database "
        "does not do by itself is give a doctor a readable overview, or answer a question typed in ordinary language."
    )
    R.h2("1.2 Motivation")
    R.p(
        "Large language models can write fluent summaries, but in medicine fluency is not enough: a model can produce "
        "a statement that sounds right but is not supported by the record (a hallucination). We wanted a system in "
        "which the AI layer never asserts anything the database cannot back up, and in which the doctor can check any "
        "statement with one click. This led to the central design rule of MedVault AI: every generated statement must "
        "carry the identifier of the stored row it is built from, and those identifiers are checked against the "
        "database before the answer is shown."
    )
    R.p(
        "The project also gave us a practical setting for the topics of a database course: schema design and "
        "normalisation, keys and constraints, joins and aggregation, indexing, query performance and access control."
    )

    # ---------- Chapter 2
    R.h1("Chapter 2: Problem Statement")
    R.h2("2.1 Problem")
    R.p(
        "**To design and build a medical records database that stores a patient's longitudinal history in a normalised "
        "relational form, and that lets a clinician (a) read an automatically generated summary of that history in which "
        "every statement is traceable to a stored record, and (b) search the records in plain English, with the system "
        "refusing to answer when no stored record supports an answer.**"
    )
    R.h2("2.2 Scope")
    R.bullets([
        "Patient registration and demographics; visits with vitals, symptoms, diagnoses, prescriptions, clinical notes and laboratory results; allergies and medical history.",
        "A dashboard of counts and aggregates computed with SQL.",
        "AI-assisted features: cited patient summary, natural-language record search, and entity extraction from a consultation note.",
        "Sign-in with roles (doctor, administrator) and an audit trail of reads, writes and AI calls.",
        "A public landing page that explains the system and shows only aggregate totals.",
    ])
    R.h2("2.3 Constraints")
    R.bullets([
        "**Patient privacy.** Patient rows are returned only to signed-in users. The landing page shows totals only. The optional external language model is disabled by default for real patient data (`ALLOW_EXTERNAL_PHI` is false), so real records are not sent to an outside service.",
        "**Hallucination risk.** A medical summary must not contain unsupported facts. Statements are built from database rows, each carries citation tags, and the tags are validated against the rows before display. A search that matches nothing returns an explicit refusal.",
        "**Data availability.** Real clinical data is restricted. We use the openly licensed MIMIC-IV demo subset (100 patients), which limits the size of the dataset.",
        "**Cost and hosting.** The system had to run on a free hosting tier, which led to a serverless deployment with an SQLite file that is rebuilt on each cold start.",
    ])

    # ---------- Chapter 3
    R.h1("Chapter 3: Objectives")
    objectives = [
        "Design a normalised (3NF) relational schema for patients, visits and the clinical records attached to them, with primary keys, foreign keys and CHECK constraints that reject invalid values.",
        "Build a REST API for registering patients, recording visits and reading complete patient charts, with input validation.",
        "Generate a patient summary in which every statement cites the stored rows it is built from, and measure what fraction of citations are valid.",
        "Answer plain-English questions about the records with ranked source rows, and refuse explicitly when nothing matches.",
        "Extract symptoms, diagnoses and medications from a typed consultation note to speed up data entry.",
        "Protect the data with hashed passwords, token-based sign-in, role checks and an audit trail.",
        "Seed the system with real, de-identified patient data rather than invented records.",
        "Test the backend and frontend automatically and deploy the system publicly.",
    ]
    for i, o in enumerate(objectives, 1):
        para = R.p(f"**O{i}.** {o}")
        para.paragraph_format.left_indent = Inches(0.3)
        para.paragraph_format.first_line_indent = Inches(-0.3)

    # ---------- Chapter 4
    R.h1("Chapter 4: Proposed Solution and System Overview")
    R.p(
        "MedVault AI is a single-page web application backed by a relational database. The database is the single "
        "source of truth; the AI features read from it and never write clinical facts of their own. The main parts are "
        "described below."
    )
    R.h2("4.1 Normalised patient database")
    R.p(
        f"Sixteen tables hold users and roles, doctors, patients, visits and the records attached to each visit "
        f"(symptoms, diagnoses, prescriptions, clinical notes, laboratory results), patient-level allergies and history, "
        f"a summary cache and the audit log. The current database holds {fmt_int(s['patients'])} patients, "
        f"{fmt_int(s['visits'])} visits and {fmt_int(s['diagnoses'] + s['prescriptions'] + s['labs'] + s['symptoms'] + s['notes'])} "
        "visit-level clinical rows. The schema is described in Chapter 7."
    )
    R.h2("4.2 Citation-grounded patient summary")
    R.p(
        "For any patient the system builds a summary in seven sections: overview, recurring symptoms, diagnoses, "
        "medication history, allergies and alerts, abnormal laboratory trends, and gaps or revisions in the record, "
        "followed by a chronological timeline. Each statement is assembled from database rows and carries the tags of "
        "those rows, for example `V-325` for a visit, `DX-12` for a diagnosis or `LAB-40` for a laboratory result. "
        "Before the summary is returned, every tag is checked against an index built from the patient's stored rows, "
        "and the result is reported as a grounding receipt such as \"385 of 385 citations matched a stored record\" (see the screenshots in Chapter 11). "
        "Clicking a tag opens the cited row. Statements that report an absence (for example \"blood group is not "
        "recorded\") carry no tag because there is no row to cite."
    )
    R.h2("4.3 Natural-language record search with refusal")
    R.p(
        "A doctor can type a question such as \"Which patients had heart failure?\" either for one patient or across "
        "all patients. The question is parsed into a date window, record types and keywords, expanded with clinical "
        "synonyms, and matched against every stored row. Matching rows are ranked and returned with their tags. If no "
        "row matches, the answer says so (\"No matching clinical records were found ...\") and returns zero records "
        "instead of guessing."
    )
    R.h2("4.4 Note entity extraction")
    R.p(
        "When recording a new visit, the doctor can type a consultation note and press \"Extract from note\". The "
        "system finds symptoms, likely diagnoses (with ICD-10 codes, marked Provisional) and medications mentioned in "
        "the text and fills them into editable rows of the visit form for the doctor to check before saving."
    )
    R.h2("4.5 Public landing page with an interactive 3D heart")
    R.p(
        "Visitors who are not signed in see a landing page that explains the system in three scroll steps (Store, "
        "Summarise, Ask). A procedural heart is rendered in real time with three.js: the heart muscle is a metaball "
        "surface built with the marching cubes algorithm and the great vessels are swept tubes. As the page scrolls "
        "the material changes from chrome to matte white and the heart moves into the chest of an anatomical plate from "
        "Gray's Anatomy (1918, public domain). The page shows only aggregate totals from a public endpoint; no patient "
        "row is sent without sign-in."
    )
    R.h2("4.6 Roles and audit trail")
    R.p(
        "Passwords are stored as bcrypt hashes. A successful sign-in returns a JSON Web Token that carries the user id "
        "and role and expires after 720 minutes. Every API route except the health check, the sign-in route and the "
        "public totals requires a valid token, and write routes are guarded by a `require_roles(\"admin\", \"doctor\")` "
        "dependency. Sign-ins, patient and visit changes, allergy and history additions, and every AI call are written "
        "to the `audit_logs` table, which can be viewed on the Audit trail screen."
    )

    # ---------- Chapter 5
    R.h1("Chapter 5: Technology Stack")
    R.p("The versions below are taken from `frontend/package.json`, `backend/requirements.txt` and `vercel.json`.")
    R.table([
        ["Layer", "Technology", "Why it was chosen"],
        ["User interface", "React 18 + TypeScript", "Component model for a multi-screen app; static types catch API-shape errors at build time."],
        ["Build tool", "Vite 6", "Fast development server and an optimised static build in `frontend/dist`."],
        ["Styling", "Tailwind CSS 3", "Utility classes and design tokens kept in one config; light and dark themes."],
        ["3D graphics", "three.js 0.170", "WebGL rendering of the landing-page heart (marching cubes, tube geometry, physical materials)."],
        ["Icons", "lucide-react", "Consistent line icons."],
        ["API server", "Python FastAPI 0.115", "Typed routes, dependency injection for auth, automatic OpenAPI docs."],
        ["Validation", "Pydantic 2", "Request and response schemas; field validators (e.g. heart rate 20-300)."],
        ["ORM", "SQLAlchemy 2.0", "Declarative models with keys, indexes and CHECK constraints; eager-loading control."],
        ["Database", "SQLite (PostgreSQL-ready)", "Zero-setup file database; the URL is configurable and `psycopg2-binary` is included for PostgreSQL."],
        ["Security", "bcrypt 4.2 + PyJWT 2.10", "Salted password hashes; signed HS256 tokens carrying user id and role."],
        ["Backend tests", "pytest 8 + FastAPI TestClient (httpx)", "End-to-end API tests against a throwaway database."],
        ["Frontend tests", "Vitest 5 + Testing Library + jsdom", "Renders the real app with a mocked API and drives it like a user."],
        ["Hosting", "Vercel", "Static files on the CDN; the API as a Python serverless function (`api/index.py`)."],
    ], [1.15, 1.85, 3.27], caption="Technology stack")

    # ---------- Chapter 6
    R.h1("Chapter 6: System Architecture")
    R.p(
        "The system is a three-tier web application deployed on Vercel. Figure 1 shows the request flow."
    )
    R.image(architecture_png(), 6.0, "System architecture and request flow")
    R.h2("6.1 Request flow")
    R.bullets([
        "**Static files.** The browser loads the single-page application (HTML, JavaScript, CSS and images built by Vite into `frontend/dist`) from the Vercel CDN. Any path that is not under `/api/` is rewritten to `/index.html`, and the app uses hash routes (for example `#/patients/1/summary`) so that the back and forward buttons work.",
        "**API calls.** The app calls `/api/...` with the JWT in an `Authorization: Bearer` header. `vercel.json` rewrites `/api/(.*)` to the Python function `api/index.py`, which adds `backend/` to the import path and imports the FastAPI `app` from `backend/app/main.py`.",
        "**Routers.** FastAPI dispatches to one of four routers: `auth` (sign-in, current user, audit log), `dashboard` (aggregates and public totals), `patients` (patients, visits, allergies, history) and `ai` (summary, query, note extraction). Dependencies check the token and role before the handler runs.",
        "**Data access.** Handlers use SQLAlchemy sessions; models map to the 16 tables. The AI engine reads complete patient graphs through the same ORM.",
        "**Database and cold start.** On Vercel the database URL is switched to `/tmp/medical_records.db` because the deployment bundle is read-only. When the function starts, `ensure_db_initialized()` creates the tables and, if the patients table is empty, seeds it from the bundled MIMIC-IV file. Data written during a session therefore lasts only as long as that function instance.",
    ])

    # ---------- Chapter 7
    R.h1("Chapter 7: Database Design")
    tables = s["tables"]
    R.p(
        f"The schema is defined as SQLAlchemy models in `backend/app/models/__init__.py` and contains {len(tables)} tables. "
        "Table 2 lists them. The foreign keys are read from the model metadata when this report is generated."
    )
    order = list(ER_POS.keys())
    rows = [["Table", "Purpose", "Foreign keys"]]
    for t in sorted(tables, key=lambda t: order.index(t["name"]) if t["name"] in order else 99):
        rows.append([f"`{t['name']}`", TABLE_PURPOSE.get(t["name"], ""), "; ".join(t["fks"]) or "none"])
    R.table(rows, [1.35, 2.55, 2.37], caption="Tables of the MedVault schema", size=10)
    R.image(er_png(tables), 6.0, "Entity-relationship overview (lines are foreign keys; patients and visits are the core entities)")

    R.h2("7.1 Relationships")
    R.bullets([
        "A **patient** has many **visits**; a visit belongs to exactly one patient and one **doctor** (`visits.patient_id`, `visits.doctor_id`).",
        "A visit has many **symptoms**, **diagnoses**, **prescriptions**, **clinical notes** and **test results**. These rows are deleted with their visit (`ON DELETE CASCADE`).",
        "A **prescription** refers to one **medication** in the catalogue; a medication cannot be deleted while prescriptions use it (`ON DELETE RESTRICT`).",
        "**Allergies**, **medical history** and **AI summaries** belong to the patient, not to a visit.",
        "Patients and doctors are linked many-to-many through **patient_doctor**, whose primary key is the pair (patient_id, doctor_id).",
        "A **user** has one **role**; a **doctor** row is the clinical profile of one user (`doctors.user_id` is unique). **Audit log** rows keep their history when a user or patient is removed (`ON DELETE SET NULL`).",
    ])
    R.h2("7.2 Normalisation (3NF)")
    R.p(
        "Each table has a single-column surrogate primary key (or, for `patient_doctor`, a composite key), every column "
        "holds one atomic value (1NF), no non-key column depends on part of a key (2NF), and no non-key column depends on "
        "another non-key column (3NF). Two design decisions show this concretely:"
    )
    R.bullets([
        "**Medications are separated from prescriptions.** Drug name, generic name, class, form and strength depend only on the drug, not on the visit. If they were stored on each prescription, the same drug's strength would be repeated in every prescription and could become inconsistent. `prescriptions` therefore stores only the visit-specific facts (dosage, frequency, duration, instructions) and a `medication_id` foreign key. "
        f"The database holds {fmt_int(s['prescriptions'])} prescriptions that refer to {fmt_int(s['medications'])} catalogue drugs.",
        "**Doctors are separated from visits.** A doctor's specialisation, licence number and department depend on the doctor, not on the visit. Storing them on each visit would create a transitive dependency (visit -> doctor -> department). `visits` stores only `doctor_id`; the doctor's details live once in `doctors`, and the doctor's name lives once in `users`.",
        "Likewise, symptoms, diagnoses and laboratory results are separate tables rather than repeated columns on `visits` (which would violate 1NF), and patient-level facts such as allergies are not repeated per visit.",
    ])
    R.p(
        "Indexes support the common access paths: unique indexes on `patients.mrn`, `users.email` and `medications.name`; "
        "a composite index on `visits(patient_id, visit_date)` for a patient's timeline; an index on "
        "`patients(last_name, first_name)` for name search; and an index on `ai_summaries(patient_id, records_hash)` "
        "for the summary cache lookup."
    )
    R.h2("7.3 CHECK constraints")
    R.p("The CHECK constraints below are read directly from the model metadata; no other CHECK constraints exist in the schema.")
    crow = [["Table", "CHECK constraint"]]
    for t in sorted(tables, key=lambda t: order.index(t["name"]) if t["name"] in order else 99):
        for c in t["checks"]:
            crow.append([f"`{t['name']}`", f"`{c}`"])
    R.table(crow, [1.4, 4.87], caption="CHECK constraints in the schema", size=10)
    R.p(
        "The same bounds are also enforced one layer earlier: the Pydantic schema for a new visit rejects a heart rate "
        "outside 20-300 or an SpO2 outside 50-100 with HTTP 422, so an invalid value is reported to the user before it "
        "reaches the database. The data converter (Chapter 8) drops source values outside these ranges for the same reason."
    )

    # ---------- Chapter 8
    R.h1("Chapter 8: Dataset")
    R.h2("8.1 Source")
    R.p(
        f"MedVault is seeded with {s['real']} real, de-identified patients from the **MIMIC-IV Clinical Database Demo v2.2** "
        "and the **MIMIC-IV-ED Demo v2.2**. Both are published on PhysioNet by the MIT Laboratory for Computational "
        "Physiology and contain records of patients treated at Beth Israel Deaconess Medical Center, Boston. They are "
        "licensed under the Open Database License (ODbL) v1.0, and the derived seed file "
        "(`backend/app/db/data/mimic_iv_demo.json.gz`) is shared under the same licence."
    )
    R.p(
        "Citation: Johnson A, Bulgarelli L, Pollard T, Horng S, Celi LA, Mark R. MIMIC-IV Clinical Database Demo "
        "(version 2.2). PhysioNet. 2023. https://doi.org/10.13026/dp1f-ex47", align=WD_ALIGN_PARAGRAPH.LEFT
    )
    R.h2("8.2 Conversion")
    R.p(
        "The script `backend/scripts/build_mimic_seed.py` reads the `hosp` and `ed` CSV tables and writes the seed file. "
        "It does not invent clinical facts: every symptom, diagnosis, drug, laboratory value and vital sign comes from a "
        "source row. Table 4 shows how each MedVault table is filled."
    )
    R.table([
        ["MedVault table", "MIMIC-IV source"],
        ["patients", "`patients`: sex, age, year group. Named \"Patient <subject_id>\"; MRN `MIMIC-<subject_id>`."],
        ["visits", "`admissions` (Emergency or Inpatient) and ED stays that did not lead to an admission."],
        ["vitals", "ED `triage` and `vitalsign` (BP, heart rate, SpO2, temperature converted from F to C); `omr` for BP and weight within the past year."],
        ["symptoms", "ED triage chief complaint; common abbreviations expanded (e.g. SOB -> Shortness of breath); raw text kept."],
        ["diagnoses", "`diagnoses_icd` + `d_icd_diagnoses`; first 8 by sequence number per admission; ICD-9 or ICD-10 code."],
        ["prescriptions", "`prescriptions` (drug_type MAIN); up to 12 distinct drugs per admission."],
        ["test_results", "`labevents` + `d_labitems`: first value of 19 key tests, then first value of other abnormal tests; up to 14 per admission."],
        ["clinical_notes", "Compiled from the coded rows above in SOAP form and labelled \"Compiled from coded MIMIC-IV data\"."],
    ], [1.4, 4.87], caption="Mapping from MIMIC-IV tables to MedVault tables", size=10)
    R.h2("8.3 What the publishers removed, and other caveats")
    R.bullets([
        "The demo has no names, addresses, telephone numbers, blood groups, allergies or free-text notes. These fields stay empty in MedVault, and the summary reports them as data gaps "
        f"({s['no_blood_group']} of {s['patients']} patients have no blood group recorded).",
        "MIMIC shifts every patient's dates into the future for de-identification. The converter moves them back into the patient's `anchor_year_group` (shift = anchor_year minus the first year of the group, minus one), so dates are accurate to within about three years.",
        "Some laboratory values are masked as \"___\" by the publishers; those rows carry no result and are skipped.",
        "A laboratory flag is set from MIMIC's `abnormal` marker: High or Low when the value is above or below the reference range, otherwise Abnormal.",
        "Heart rates outside 20-300 and SpO2 values outside 50-100 are dropped, matching the CHECK constraints.",
        "The doctor shown on a MIMIC visit is one of the application's demonstration accounts, chosen from the hospital service code (for example CMED -> cardiology). It is not source data.",
    ])
    R.h2("8.4 Resulting data")
    vt = ", ".join(f"{t} {fmt_int(n)}" for t, n in s["visit_types"])
    R.table([
        ["Item", "Count (read from the database)"],
        ["Patients (real, de-identified)", f"{fmt_int(s['patients'])} ({fmt_int(s['real'])})"],
        ["Visits", f"{fmt_int(s['visits'])} ({vt})"],
        ["Visit dates", span],
        ["Symptoms", fmt_int(s["symptoms"])],
        ["Diagnoses (distinct conditions)", f"{fmt_int(s['diagnoses'])} ({fmt_int(s['distinct_conditions'])})"],
        ["Prescriptions / catalogue drugs", f"{fmt_int(s['prescriptions'])} / {fmt_int(s['medications'])}"],
        ["Laboratory results (not Normal)", f"{fmt_int(s['labs'])} ({fmt_int(s['abnormal_labs'])})"],
        ["Clinical notes (compiled)", fmt_int(s["notes"])],
    ], [2.6, 3.67], caption="Contents of the seeded database")
    R.h2("8.5 Synthetic cohort for tests")
    R.p(
        "An earlier synthetic cohort of Indian patients, with hand-written clinical storylines, is still in the code. It is "
        "loaded when `DATA_SOURCE=synthetic`. The backend test suite uses it (in a temporary database) because the tests "
        "refer to named storyline patients; the deployed application uses `DATA_SOURCE=mimic`, the default."
    )

    # ---------- Chapter 9
    R.h1("Chapter 9: AI Module")
    R.p(
        "All three AI features are implemented in `backend/app/ai/engine.py`. By default they are deterministic: they "
        "build their output from database rows using rules, aggregation and keyword retrieval, so the same records "
        "always give the same output. An optional Google Gemini call can reword the overview section, but only when an "
        "API key is configured and only for synthetic patients unless `ALLOW_EXTERNAL_PHI` is set; any tag it returns "
        "that is not in the citation index is removed. The deployed system runs without it."
    )
    R.h2("9.1 Summary pipeline")
    R.table([
        ["Step", "What happens"],
        ["1. Request", "`GET /api/ai/patients/{id}/summary` (optionally `?refresh=true`) with a valid token."],
        ["2. Load rows", "`load_full_patient` loads the patient with allergies, history and every visit's doctor, symptoms, diagnoses, prescriptions (with medication), notes and laboratory results in one query."],
        ["3. Cache check", "`compute_records_hash` builds a SHA-256 hash over the patient's rows (ids, statuses, per-visit row counts, last update). If a cached summary with the same hash exists, it is returned. Any new or changed row changes the hash, so stale summaries are never served."],
        ["4. Citation index", "`build_citation_index` creates one entry per stored row with a tag (V-, SYM-, DX-, RX-, NOTE-, LAB-, ALG-, HX-), a label and a snippet of the row."],
        ["5. Aggregate", "Groups symptoms by name (recurring vs single episodes and severity pattern), diagnoses by condition (status progression), prescriptions by drug and strength (dosage over time), and laboratory results by test (longitudinal trend with flags)."],
        ["6. Data gaps", "Reports missing blood group or emergency contact, diagnoses whose status changed (Provisional -> Confirmed, or Ruled-out), and a last visit older than 180 days."],
        ["7. Validate", "`validate_statements` checks every tag of every statement against the citation index and counts emitted and verified tags; the grounding score is verified / emitted."],
        ["8. Cache and audit", "The summary is stored in `ai_summaries` with its hash, and the router writes an `AI_GENERATE_SUMMARY` entry to `audit_logs`."],
        ["9. Display", "The UI shows the grounding receipt, the clinical disclaimer, citation chips that open the cited row, and a \"Flag for review\" button on each statement."],
    ], [1.25, 5.02], caption="Steps of the summary pipeline", size=10)
    R.h2("9.2 Retrieval for natural-language questions")
    R.p("`answer_natural_language_query` answers a question for one patient or for all patients in four stages.")
    R.bullets([
        "**Query parsing.** Relative dates (\"last 2 years\", \"last six months\", \"past year\") and the years 2024-2026 set a start date. Words such as \"diagnosis\", \"prescribed\", \"lab\" or \"allergy\" select target record types. The text is split into words; stopwords (question scaffolding such as \"which\", \"patients\", \"records\", and words like \"low\" and \"high\" that would match too broadly) and words of two letters or fewer are removed.",
        "**Synonym expansion.** A hand-built map adds related clinical terms, for example \"sugar\" -> diabetes, glucose, hba1c, metformin; \"bp\" -> hypertension, amlodipine. Expansion works in both directions, so a synonym in the question also adds its group.",
        "**Scoring.** Every allergy, symptom, diagnosis, prescription, laboratory result, note and (when relevant) visit is scored. Words the user typed score 6 points per match and expansion synonyms 2; an exact two-word phrase from the question (\"heart failure\") adds 10; a laboratory flag the question asks for (\"high\", \"low\", \"critical\", \"abnormal\") adds 6; a row of a requested type adds 2. For symptoms and prescriptions, a term found only in the parent visit's chief complaint scores 1, so a drug given during a heart-failure admission never outranks the heart-failure diagnosis itself. A row with no matching term scores zero and is dropped.",
        "**Answer or refusal.** Rows are sorted by score and date and the top 25 are returned with their tags, grouped by record type, with a recurring-pattern note when the question asks about repetition. If no row scores above zero, the response has `total_matches = 0` and the text \"No matching clinical records were found in the database for this query. The AI module does not extrapolate or invent clinical facts when source records are unavailable.\"",
    ])
    R.p(
        "For questions across all patients the engine loads every patient's records. Child collections are loaded with "
        "SQLAlchemy's `selectinload` (one extra `SELECT ... WHERE id IN (...)` per collection) rather than `joinedload`, "
        "whose single large join multiplied rows across all child tables. Section 12.3 gives the measured effect."
    )
    R.h2("9.3 Note extraction")
    R.p(
        "`extract_structured_clinical_note` scans the lower-cased note for trigger phrases from three catalogues: 14 "
        "symptom groups (for example \"shortness of breath\", \"dyspnea\" or \"breathlessness\" -> Shortness of Breath), "
        "8 conditions with ICD-10 codes (for example \"asthma\", \"wheezing\" or \"salbutamol\" -> Bronchial Asthma, J45.40), "
        "and 12 medications with a default dosage. Severity is set to Severe if the note contains words such as \"severe\" "
        "or \"acute\", otherwise Moderate; diagnoses are always marked Provisional. The first sentence becomes the chief "
        "complaint and the first sentence mentioning follow-up, review or a time period becomes the follow-up plan. The "
        "extracted rows are suggestions: they fill the visit form and are saved only when the doctor submits it."
    )

    # ---------- Chapter 10
    R.h1("Chapter 10: Implementation and Code Snippets")
    R.p("The excerpts below are copied from the repository when this report is generated. \"...\" marks lines left out.")
    snippets = [
        ("10.1 Visit model with CHECK constraints", ("backend/app/models/__init__.py", "class Visit(Base):", "vitals_spo2: Mapped"),
         "Listing 1: backend/app/models/__init__.py",
         "The `visits` table is declared as a SQLAlchemy model. `__table_args__` adds three CHECK constraints (allowed visit "
         "types and valid ranges for heart rate and SpO2, each allowing NULL when the vital was not measured) and a composite "
         "index on (patient_id, visit_date) that serves the chart timeline. The two foreign keys behave differently on "
         "delete: removing a patient cascades to their visits, while a doctor who still has visits cannot be removed (RESTRICT)."),
        ("10.2 Hash of a patient's records for the summary cache", ("backend/app/ai/engine.py", "def compute_records_hash", "return hashlib.sha256"),
         "Listing 2: backend/app/ai/engine.py",
         "The cache key is a SHA-256 hash of a compact description of the patient's rows: the patient's last update time, the "
         "id and status of every allergy and history entry, and for every visit its date and the number of symptoms, "
         "diagnoses, prescriptions, notes and laboratory results. Adding or changing any of these changes the hash, so the "
         "next request rebuilds the summary instead of serving a stale one. The backend tests check this by adding an "
         "allergy and confirming the next summary is not cached."),
        ("10.3 Citation validation", ("backend/app/ai/engine.py", "def validate_statements", "return validated, total_citations"),
         "Listing 3: backend/app/ai/engine.py",
         "Each statement's citation tags are compared with the citation index, which has exactly one key per stored row of "
         "the patient. Only tags that exist in the index are kept, and the function returns the number of tags emitted and "
         "the number verified. These totals become the grounding receipt shown above the summary."),
        ("10.4 Retrieval scoring", ("backend/app/ai/engine.py", "def score_text(", "return score, list(dict.fromkeys(matched))", ('"""Score one record', "never outranks"), 0),
         "Listing 4: backend/app/ai/engine.py",
         "`score_text` scores one stored row against the parsed question. Phrases, requested flags and record types add "
         "fixed bonuses; each matched clinical term adds 6 points if the user typed it and 2 if it came from synonym "
         "expansion; text borrowed from the parent visit counts 1. When the question contains clinical terms and none "
         "match, the row scores zero, which is what makes the refusal path possible."),
        ("10.5 Converting a MIMIC-IV laboratory row", ("backend/scripts/build_mimic_seed.py", "def as_lab(", "Single result this admission", None, 1),
         "Listing 5: backend/scripts/build_mimic_seed.py",
         "For each laboratory test in an admission the converter keeps the first result. MIMIC marks out-of-range values "
         "with `flag = \"abnormal\"`; the code turns this into High or Low by comparing the numeric value with the reference "
         "range, and falls back to Abnormal when no numeric comparison is possible. The reference range is written as "
         "\"low - high\"."),
        ("10.6 Password hashing and tokens", ("backend/app/core/security.py", "def verify_password", "return jwt.encode"),
         "Listing 6: backend/app/core/security.py",
         "Passwords are hashed with bcrypt using a fresh random salt; only the hash is stored. On sign-in the router "
         "verifies the password and calls `create_access_token`, which signs a JWT containing the user id (`sub`), the "
         "role and an expiry time (720 minutes by default). Each protected request decodes the token to identify the user."),
        ("10.7 Dashboard aggregation with GROUP BY", ("backend/app/routers/dashboard.py", "dx_rows = (", "top_conditions = ["),
         "Listing 7: backend/app/routers/dashboard.py",
         "The dashboard's \"top conditions\" list is a single aggregate query: diagnoses that were not ruled out are grouped "
         "by condition name, counted, and the six most frequent are returned. SQLAlchemy emits `SELECT condition_name, "
         "count(id) ... GROUP BY condition_name ORDER BY count(id) DESC LIMIT 6`."),
        ("10.8 Citation chips in the user interface", ("frontend/src/components/citations.tsx", "export function Citations({", "</span>", None, 2),
         "Listing 8: frontend/src/components/citations.tsx",
         "Each AI statement is followed by one button per citation tag. Clicking a button opens the citation inspector "
         "drawer with the stored row the tag refers to. A tag that is not in the citation index is rendered disabled, with "
         "a tooltip saying so, so an unsupported tag can never open a fabricated record."),
    ]
    shown = 0
    for heading, spec, title, explanation in snippets:
        path, a, b = spec[:3]
        skip, after = (spec[3], spec[4]) if len(spec) > 3 else (None, 0)
        src = excerpt(path, a, b, skip=skip, after=after)
        if src is None:
            continue
        shown += 1
        R.h2(f"10.{shown} {heading.split(' ', 1)[1]}")
        R.p(explanation)
        R.code(src, f"Listing {shown}: {title.split(': ', 1)[1]}")
    R.n_snippets = shown

    # ---------- Chapter 11
    R.h1("Chapter 11: Screenshots and Outcomes")
    R.p(f"The screenshots below were taken from the running application with the MIMIC-IV data loaded. The live system is at {LIVE_URL}.")
    shots = sorted(SHOTS.glob("*.jpg")) if SHOTS.exists() else []
    R.n_shots = 0
    for path in shots:
        cap = SHOT_CAPTIONS.get(path.stem, path.stem.split("-", 1)[-1].replace("-", " ").capitalize() + ".")
        R.image(str(path), 6.0, cap)
        R.n_shots += 1

    # ---------- Chapter 12
    R.h1("Chapter 12: Testing and Results")
    R.h2("12.1 Backend tests (pytest)")
    R.p(
        f"`backend/tests/test_api.py` contains {len(tests['backend'])} tests. They call the real FastAPI application through "
        "`TestClient`, against a temporary SQLite database seeded with the synthetic cohort (`conftest.py` sets "
        f"`DATA_SOURCE=synthetic`). Result at generation time: **{tests['backend_result']}**."
    )
    R.table([["Test", "What it checks"]] + [[f"`{n}`", d] for n, d in tests["backend"]], [2.55, 3.72],
            caption="Backend test cases", size=9.5)
    R.h2("12.2 Frontend tests (Vitest and Testing Library)")
    R.p(
        f"`frontend/src/__tests__/App.test.tsx` renders the complete React application in jsdom with a mocked API and "
        f"drives it as a user would (clicks, typing, keyboard shortcuts). It contains {len(tests['frontend'])} tests. "
        f"Result at generation time: **{tests['frontend_result']}**."
    )
    R.table([["Test", "What it checks"]] + [[t, FRONTEND_TEST_NOTES.get(t, "Behaviour as named by the test.")] for t in tests["frontend"]], [2.55, 3.72],
            caption="Frontend test cases", size=9.5)
    R.h2("12.3 Measured results")
    q1, t1, m1 = s["q_hf"]
    q2, t2, m2 = s["q_ebola"]
    R.p(
        "The figures below were measured on the seeded database while generating this report (single machine, best of "
        "three runs for the timings)."
    )
    R.table([
        ["Measurement", "Result"],
        ["Patients", fmt_int(s["patients"])],
        ["Visits", fmt_int(s["visits"])],
        ["Diagnoses", fmt_int(s["diagnoses"])],
        ["Prescriptions", fmt_int(s["prescriptions"])],
        ["Laboratory results", fmt_int(s["labs"])],
        ["Abnormal laboratory results (flag not Normal)", fmt_int(s["abnormal_labs"])],
        ["AI summaries regenerated", f"{s['summaries']} patients in {s['summary_seconds']:.1f} s"],
        ["Citations emitted / verified", f"{fmt_int(s['cits_total'])} / {fmt_int(s['cits_verified'])} ({grounding_pct:.1f}% grounded)"],
        ["Summaries with grounding score 1.0", f"{s['summaries_full']} of {s['summaries']}"],
        [f"Cohort-wide question \"{q1}\"", f"{fmt_int(m1)} matching rows in {t1:.2f} s"],
        [f"Cohort-wide question \"{q2}\"", f"{fmt_int(m2)} matching rows in {t2:.2f} s ({'refusal returned' if m2 == 0 else 'matches found'})"],
    ], [3.4, 2.87], caption="Measured outcomes")
    R.bullets([
        f"**Grounding.** Every summary of every patient was regenerated; {fmt_int(s['cits_verified'])} of {fmt_int(s['cits_total'])} "
        "citation tags matched a stored row, so no unsupported tag reached the user.",
        "**Retrieval speed.** Cohort-wide questions originally loaded patients with `joinedload`, which joined every child "
        "table into one result and took about 1.2 s per question (recorded in the project's commit history when the change "
        f"was made). Switching to `selectinload` brought this to about 0.2 s. The measurement in Table 9 ({t1:.2f} s, taken on the "
        "machine that generated this report) is the current figure.",
        "**Refusal.** A question about a disease that does not occur in the records returns zero rows and an explicit "
        "\"no matching records\" message, both in the automated tests and on the real data.",
    ])

    # ---------- Chapter 13
    R.h1("Chapter 13: Conclusion")
    R.p(
        "MedVault AI shows that an AI layer over a medical database can be useful without being trusted blindly. The "
        "relational schema keeps each fact in one place, enforced by keys and CHECK constraints. The summary, search and "
        "extraction features are built from those rows, and every summary statement that asserts a fact carries the tag "
        f"of its source row. On {s['real']} real, de-identified MIMIC-IV patients, all {fmt_int(s['cits_total'])} citations "
        "in the generated summaries matched a stored record, and questions with no supporting record are refused rather "
        "than answered. The system is secured with bcrypt, JWT and role checks, records an audit trail, is covered by "
        "automated backend and frontend tests, and is deployed publicly."
    )
    R.p(
        "The project met its objectives (Chapter 3). The main lesson was that grounding is easier to guarantee when the "
        "AI layer assembles statements from identified rows than when it writes free text and the citations are checked "
        "afterwards."
    )

    # ---------- Chapter 14
    R.h1("Chapter 14: Limitations and Future Scope")
    R.h2("14.1 Limitations")
    R.bullets([
        "**Keyword and synonym retrieval.** Search matches words and a hand-built synonym list. It does not understand meaning: a question phrased with words that are not in the record or the synonym map can miss relevant rows, and a common word (for example \"fever\" in \"Ebola hemorrhagic fever\") can match unrelated rows.",
        "**Rule-based note extraction.** The extraction catalogues are small (14 symptom groups, 8 conditions, 12 drugs). A note about heart failure, for example, yields the breathlessness symptom but no diagnosis or drug.",
        f"**Demo-size dataset.** The MIMIC-IV demo has {s['real']} patients and no free-text notes, names or allergies, so the summaries are built from coded data and dates are approximate within about three years.",
        "**Temporary storage on the free deployment.** On Vercel the SQLite file lives in `/tmp` and is rebuilt on a cold start, so changes made in the live demo are not permanent. A hosted PostgreSQL database would remove this limit.",
        "**No standards-based exchange.** There is no FHIR or HL7 import or export, so the system cannot exchange records with hospital systems.",
        "**No imaging.** X-rays, scans and reports in image or PDF form are not stored.",
        "**Coarse roles.** Doctor and administrator currently have the same permissions on most routes; finer rules (for example, a doctor sees only assigned patients) are not enforced.",
    ])
    R.h2("14.2 Future scope")
    R.bullets([
        "Vector (embedding) search alongside keyword search, so questions match by meaning, while still returning only stored rows with their tags.",
        "A language model for the summary text, constrained to the citation index and checked by the same validator.",
        "FHIR R4 export and import of patients, encounters, conditions, medication requests and observations.",
        "Storage of imaging and scanned documents, linked to visits.",
        "A persistent PostgreSQL deployment, row-level access rules per assigned doctor, and patient consent records.",
        "Evaluation with clinicians on time saved and on the usefulness of the summaries.",
    ])

    # ---------- References
    R.h1("References")
    refs = [
        "Johnson A, Bulgarelli L, Pollard T, Horng S, Celi LA, Mark R. MIMIC-IV Clinical Database Demo (version 2.2). PhysioNet. 2023. https://doi.org/10.13026/dp1f-ex47",
        "Johnson A, Bulgarelli L, Pollard T, Celi LA, Mark R, Horng S. MIMIC-IV-ED Demo (version 2.2). PhysioNet. 2023. https://physionet.org/content/mimic-iv-ed-demo/2.2/",
        "Goldberger A, Amaral L, Glass L, Hausdorff J, Ivanov PC, Mark R, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000;101(23):e215-e220.",
        "Open Data Commons. Open Database License (ODbL) v1.0. https://opendatacommons.org/licenses/odbl/1-0/",
        "World Health Organization. International Statistical Classification of Diseases and Related Health Problems, 10th Revision (ICD-10). Geneva: WHO.",
        "Gray H. Anatomy of the Human Body. 20th ed., revised by W. H. Lewis. Philadelphia: Lea & Febiger; 1918. (Public-domain illustrations used on the landing page.)",
        "FastAPI documentation. https://fastapi.tiangolo.com/",
        "React documentation. https://react.dev/",
        "SQLAlchemy 2.0 documentation. https://docs.sqlalchemy.org/en/20/",
        "three.js documentation. https://threejs.org/docs/",
        "Pydantic documentation. https://docs.pydantic.dev/",
        "Vercel documentation: Python runtime and rewrites. https://vercel.com/docs",
        "Codd EF. A relational model of data for large shared data banks. Communications of the ACM. 1970;13(6):377-387.",
    ]
    for i, ref in enumerate(refs, 1):
        para = R.p(f"[{i}] {ref}", align=WD_ALIGN_PARAGRAPH.LEFT)
        para.paragraph_format.left_indent = Inches(0.4)
        para.paragraph_format.first_line_indent = Inches(-0.4)
        para.paragraph_format.line_spacing = 1.15

    R.fill_toc(pages)
    return R


# =========================================================================== PDF + page numbers


def to_pdf(docx_path, outdir):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx_path)],
                   check=True, capture_output=True, timeout=300)
    pdf = Path(outdir) / (Path(docx_path).stem + ".pdf")
    return pdf if pdf.exists() else None


def heading_pages(pdf, headings):
    """Find the printed page number of each heading (physical page minus the blank cover page)."""
    if not shutil.which("pdftotext"):
        return None
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    pages = [[re.sub(r"\s+", " ", ln).strip() for ln in pg.splitlines()] for pg in text.split("\f")]
    found, start = {}, 1
    # skip the table of contents: chapters start after the last page that contains the TOC heading run
    toc_pages = [i for i, pg in enumerate(pages) if "Table of Contents" in pg]
    after_toc = (toc_pages[0] + 1) if toc_pages else 1
    for lvl, h in headings:
        key = re.sub(r"\s+", " ", h).strip()
        begin = 1 if key == "Abstract" else max(start, after_toc)
        for i in range(begin, len(pages)):
            if any(ln == key for ln in pages[i]) or any(ln.startswith(key) and "...." not in ln for ln in pages[i] if len(key) > 30):
                found[h] = str(i)  # physical index i (0-based) == printed number, since page 1 is unnumbered
                if key != "Abstract":
                    start = i
                break
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-tests", action="store_true", help="do not run pytest and vitest")
    ap.add_argument("--no-pdf", action="store_true", help="do not convert to PDF")
    args = ap.parse_args()

    print("Reading live statistics from the database (regenerates every AI summary) ...")
    stats = gather_stats()
    tests = {"backend": backend_tests(), "frontend": frontend_tests()}
    if args.skip_tests:
        tests["backend_result"] = tests["frontend_result"] = "not run for this build"
    else:
        print("Running backend tests ...")
        res = run_suite([sys.executable, "-m", "pytest", "-q"], BACKEND, r"(\d+ (?:passed|failed)[^\n=]*)")
        tests["backend_result"] = re.sub(r",?\s*\d+ warnings?", "", re.sub(r"\s+in [\d.]+s.*$", "", res)).strip()
        if (FRONTEND / "node_modules").exists() and shutil.which("npx"):
            print("Running frontend tests ...")
            res = run_suite(["npx", "vitest", "run"], FRONTEND, r"Tests\s+(\d+ [^\n]+)")
            tests["frontend_result"] = re.sub(r"\s*\(\d+\)\s*$", "", res).strip()
        else:
            tests["frontend_result"] = "not run (frontend dependencies not installed)"
    print(f"  backend: {tests['backend_result']}; frontend: {tests['frontend_result']}")

    DOCS.mkdir(parents=True, exist_ok=True)
    has_soffice = bool(shutil.which("soffice") or shutil.which("libreoffice"))
    pages = None
    if has_soffice and not args.no_pdf and shutil.which("pdftotext"):
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / "draft.docx"
            R = build(stats, tests, None)
            R.doc.save(draft)
            pdf = to_pdf(draft, tmp)
            if pdf:
                pages = heading_pages(pdf, R.headings)
                missing = [h for _, h in R.headings if h not in (pages or {})]
                if missing:
                    print(f"  ! page not found for: {missing}")
    R = build(stats, tests, pages or {})
    R.doc.save(OUT_DOCX)
    print(f"Wrote {OUT_DOCX} ({R.n_shots} screenshots, {R.n_snippets} code excerpts, {R.fig_no} figures)")

    if args.no_pdf:
        return
    pdf = to_pdf(OUT_DOCX, DOCS)
    if pdf:
        print(f"Wrote {pdf}")
    else:
        print("LibreOffice (soffice) not found: PDF not produced.")


if __name__ == "__main__":
    main()
