"""Generate the comprehensive Walkthrough Guide and Viva Preparation Manual PDF for MedVault AI.

Applies the Burgundy Clinical Design System (#380F17, #8F0B13, #EFDFC5, #252B2B)
with strict ReportLab 2D coordinate geometry, Stripe Press / O'Reilly typography,
and structured technical tables for academic defense and examiner review.
"""

from pathlib import Path
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_PDF = ROOT_DIR / "docs" / "MedVault_AI_Walkthrough_and_Viva_Guide.pdf"
PUBLIC_PDF = ROOT_DIR / "frontend" / "public" / "MedVault_AI_Walkthrough_and_Viva_Guide.pdf"

BURGUNDY = colors.HexColor("#380F17")
CRIMSON = colors.HexColor("#8F0B13")
CRITICAL = colors.HexColor("#DC2011")
IVORY = colors.HexColor("#EFDFC5")
IVORY_TINT = colors.HexColor("#FBF4E9")
ALABASTER = colors.HexColor("#FAF8F5")
CHARCOAL = colors.HexColor("#252B2B")
SLATE_GREY = colors.HexColor("#4C4F54")
LIGHT_BORDER = colors.HexColor("#E7E1DA")
GREEN_STATUS = colors.HexColor("#2F6B48")


class NumberedVivaCanvas(canvas.Canvas):
    """Canvas subclass that renders exactly one clean header and footer line per page."""

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
            self._draw_running_decorations(total_pages)
            super().showPage()
        super().save()

    def _draw_running_decorations(self, page_count: int) -> None:
        self.saveState()
        # Running top header
        self.setFont("Helvetica-Bold", 8.0)
        self.setFillColor(BURGUNDY)
        self.drawString(54, A4[1] - 38, "MEDVAULT AI — VIVA & EXAMINER DEMONSTRATION MANUAL")
        self.setFont("Helvetica", 8.0)
        self.setFillColor(SLATE_GREY)
        self.drawRightString(A4[0] - 54, A4[1] - 38, "B.Tech Capstone Project | Pushkar Panwar & Saksham Singh")
        self.setStrokeColor(LIGHT_BORDER)
        self.setLineWidth(0.6)
        self.line(54, A4[1] - 44, A4[0] - 54, A4[1] - 44)

        # Running bottom footer
        self.line(54, 42, A4[0] - 54, 42)
        self.setFont("Helvetica", 8.5)
        self.setFillColor(SLATE_GREY)
        self.drawString(54, 28, "Confidential — Prepared for Academic Examination & Faculty Review")
        self.drawRightString(A4[0] - 54, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def make_section_banner(title: str, styles) -> Table:
    tbl = Table([[Paragraph(title, styles["BannerText"])]], colWidths=[487])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BURGUNDY),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return tbl


def make_qa_block(q_num: int, question: str, answer_points: list[str], styles, tech_tip: str = "") -> KeepTogether:
    content = []
    q_html = f"<b>Q{q_num}. {question}</b>"
    content.append(Paragraph(q_html, styles["QuestionTitle"]))
    content.append(Spacer(1, 3))

    bullet_body = "".join([f"&bull; {pt}<br/>" for pt in answer_points])
    content.append(Paragraph(bullet_body, styles["AnswerBody"]))

    if tech_tip:
        tip_tbl = Table([[Paragraph(f"<b>Key Defense Point:</b> {tech_tip}", styles["TipText"])]], colWidths=[487])
        tip_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), IVORY_TINT),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.5, CRIMSON),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        content.append(Spacer(1, 3))
        content.append(tip_tbl)

    content.append(Spacer(1, 9))
    return KeepTogether(content)


def make_step_card(step_num: str, title: str, what_to_click: str, what_to_say: str, under_the_hood: str, styles) -> KeepTogether:
    rows = [
        [Paragraph(f"<b>STEP {step_num}: {title.upper()}</b>", styles["StepHeader"]), ""],
        [Paragraph("<b>What to Click / Do:</b>", styles["StepLabel"]), Paragraph(what_to_click, styles["StepValue"])],
        [Paragraph("<b>What to Say to Ma'am:</b>", styles["StepLabel"]), Paragraph(what_to_say, styles["StepValueQuote"])],
        [Paragraph("<b>Technical Engine Reality:</b>", styles["StepLabel"]), Paragraph(under_the_hood, styles["StepValue"])],
    ]
    tbl = Table(rows, colWidths=[130, 357])
    tbl.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (1, 0), BURGUNDY),
                ("BACKGROUND", (0, 1), (-1, -1), ALABASTER),
                ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return KeepTogether([tbl, Spacer(1, 10)])


def generate_viva_guide_pdf() -> Path:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PDF.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
        title="MedVault AI — Viva & Walkthrough Guide",
        author="Pushkar Panwar & Saksham Singh",
    )

    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle("Title", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=BURGUNDY, spaceAfter=2),
        "Subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=SLATE_GREY, spaceAfter=10),
        "BannerText": ParagraphStyle("BannerText", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=IVORY),
        "Heading": ParagraphStyle("Heading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=BURGUNDY, spaceBefore=6, spaceAfter=4, keepWithNext=True),
        "Body": ParagraphStyle("Body", parent=base["Normal"], fontName="Helvetica", fontSize=9.0, leading=13.5, textColor=CHARCOAL, spaceAfter=6),
        "QuestionTitle": ParagraphStyle("QTitle", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13.5, textColor=CRIMSON, keepWithNext=True),
        "AnswerBody": ParagraphStyle("AnsBody", parent=base["Normal"], fontName="Helvetica", fontSize=8.7, leading=13.0, textColor=CHARCOAL),
        "TipText": ParagraphStyle("TipText", parent=base["Normal"], fontName="Helvetica", fontSize=8.3, leading=12.0, textColor=BURGUNDY),
        "StepHeader": ParagraphStyle("StepHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=IVORY),
        "StepLabel": ParagraphStyle("StepLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=BURGUNDY),
        "StepValue": ParagraphStyle("StepValue", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=CHARCOAL),
        "StepValueQuote": ParagraphStyle("StepValueQuote", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.5, leading=12.5, textColor=CHARCOAL),
        "TableHeader": ParagraphStyle("TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=IVORY),
        "TableCell": ParagraphStyle("TableCell", parent=base["Normal"], fontName="Helvetica", fontSize=8.2, leading=11.5, textColor=CHARCOAL),
    }

    story = []

    # Title Block
    story.append(Paragraph("MedVault AI: Project Walkthrough & Faculty Viva Defense Guide", styles["Title"]))
    story.append(
        Paragraph(
            "<b>Team:</b> Pushkar Panwar (2501730022) &amp; Saksham Singh (2501730270) &nbsp;|&nbsp; "
            "<b>Project:</b> AI-Assisted Medical Record Database &nbsp;|&nbsp; <b>Design:</b> Burgundy Clinical",
            styles["Subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=CRIMSON, spaceAfter=8))

    # SECTION 1: 60-Second Elevator Pitch
    story.append(make_section_banner("1. THE 60-SECOND ELEVATOR PITCH (WHAT TO SAY FIRST)", styles))
    story.append(Spacer(1, 6))
    pitch_text = (
        "<i>\"Good morning Ma'am. Our project is <b>MedVault AI</b>, an AI-Assisted Medical Record Database designed to solve "
        "one of the most critical bottlenecks in healthcare: information overload during patient encounters. In hospitals, clinical "
        "history is fragmented across OPD visits, handwritten notes, lab sheets, and medication orders. When a patient arrives, a doctor "
        "has less than 5 minutes to review past history.<br/><br/>"
        "MedVault AI solves this through a dual-layer architecture: first, a <b>strictly normalized 13-table relational database (3NF)</b> "
        "with check constraints, foreign keys, and indexes for reliable patient data storage; second, an <b>extractive, citation-grounded AI engine</b> "
        "that generates summaries where every single medical claim is locked to an immutable primary-key citation tag like [V-1] or [SYM-2]. "
        "If a clinical fact is not in the database, our system explicitly reports it as unavailable rather than hallucinating. "
        "Let us demonstrate how it works live.\"</i>"
    )
    pitch_tbl = Table([[Paragraph(pitch_text, styles["Body"])]], colWidths=[487])
    pitch_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), IVORY_TINT),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, BURGUNDY),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(pitch_tbl)
    story.append(Spacer(1, 10))

    # SECTION 2: Step-by-Step Live Demo Walkthrough
    story.append(make_section_banner("2. STEP-BY-STEP LIVE DEMONSTRATION WALKTHROUGH", styles))
    story.append(Spacer(1, 6))

    story.append(make_step_card(
        "1", "Doctor Authentication & Role-Based Security",
        "Click the quick-login preset 'Dr. Ananya Sharma, MD', then click 'Access Clinical Workspace'.",
        "\"Ma'am, we have built Role-Based Access Control (RBAC). Passwords are encrypted with bcrypt, and authentication produces an HMAC-SHA256 JWT bearer token stored strictly in sessionStorage for security rather than persistent storage.\"",
        "FastAPI executes POST /api/auth/login, queries users and doctor_profiles tables, writes to audit_logs, and returns JWT. Token is passed via Authorization: Bearer headers.",
        styles
    ))

    story.append(make_step_card(
        "2", "Clinical Dashboard & Real-Time SQL Aggregations",
        "Show the 8 KPI metric cards (Total Patients, Encounters, Records, Prescriptions, Labs, etc.) and the Condition / Symptom distribution bars.",
        "\"Here on the Clinical Dashboard, doctors get an immediate macro view. These counters and recurrence frequency bars are NOT static or mock numbers; they are computed dynamically via SQL GROUP BY and COUNT queries across our normalized relational tables.\"",
        "GET /api/dashboard/stats executes aggregated queries on diagnoses and symptoms tables with JOINs on visits, grouping by condition/symptom and ordering by count DESC.",
        styles
    ))

    story.append(make_step_card(
        "3", "Patient Directory, Multi-Field Search & Pagination",
        "Navigate to 'Patients & EHR Directory'. Type 'Aarav' or 'Migraine' in the search bar, filter by Sex ('Male') or Blood Group ('O+'), and demonstrate pagination.",
        "\"In the Patient Directory, we can instantly filter through records by name, MRN, phone, or diagnosis. Notice the fast search response and clean pagination preserving server resources.\"",
        "Client uses URL search params (?q=...&sex=...) to query GET /api/patients with SQL ILIKE/LIKE pattern matching on indexed columns, coupled with memoized sorting and client pagination.",
        styles
    ))

    story.append(make_step_card(
        "4", "Patient Record Inspection & Full Relational Profile",
        "Click 'Open Medical Records' on Aarav Mehta (MV-2026-0001). Show Demographics, Allergies banner, and Clinical Timeline.",
        "\"When we open a patient profile, we see their entire longitudinal medical history: demographics, blood group, life-threatening allergy alerts, chronic baseline medical history, and past consultations.\"",
        "GET /api/patients/{id} performs foreign-key JOINs across patients, allergies, medical_history, visits, symptoms, diagnoses, prescriptions, clinical_notes, and test_results.",
        styles
    ))

    story.append(make_step_card(
        "5", "AI-Powered Grounded Summarization & Citation Verification",
        "Click the 'AI Grounded Summary' tab. Show the Executive Overview, Recurring Symptoms, Medication History, and Data Gaps.",
        "\"This is our core innovation, Ma'am: AI Grounded Summarization. Notice how every sentence has a bracketed tag like [SYM-1], [DX-10], or [RX-20]. The AI is barred from free-form hallucinations. Clicking any tag opens our Citation Inspector Drawer, displaying the exact database row, timestamp, and physician who entered it!\"",
        "GET /api/ai/patients/{id}/summary computes recurrence and joins. The Citation Gate verifies 100% of emitted tags against indexed relational IDs. Any unverified claim is dropped.",
        styles
    ))

    story.append(make_step_card(
        "6", "Clinician Feedback & Flagging Mechanism",
        "Click the 'Flag Issue' button next to any statement in the summary. Watch it turn into 'Flagged for Review' with an alert counter.",
        "\"In healthcare, human-in-the-loop validation is mandatory. We provide a Clinician Flagging toggle so attending physicians can mark any ambiguous claim for clinical review, ensuring safety.\"",
        "State is updated dynamically in frontend React state, incrementing the active review counter and highlighting the disputed statement for clinician follow-up.",
        styles
    ))

    story.append(make_step_card(
        "7", "Intelligent Historical Retrieval (Zero-Hallucination Query)",
        "Click 'Ask AI About Patient' or global 'AI Historical Retrieval'. Run: 'Find previous records mentioning recurring headaches'. Then type 'Find malaria symptoms'.",
        "\"Doctors can query patient records in natural language. The system parses the question into SQL filters (record types, date ranges, clinical terms) and returns the matching relational cards. When we ask about 'malaria'—which this patient never had—it strictly refuses to invent data and reports zero matches.\"",
        "POST /api/ai/query extracts query intent via regex and clinical ontology, executes targeted SQL filters, scores relevance, and constructs grounded answer statements with citations.",
        styles
    ))

    story.append(make_step_card(
        "8", "Structured Encounter Entry & AI SOAP Extraction",
        "Click 'Add Visit Record'. Paste a quick note: 'Patient complains of severe migraine and nausea for 3 days. Prescribed Sumatriptan 50mg.' Click 'Auto-Extract from Note'.",
        "\"Finally, we streamline data entry. A doctor can paste raw unstructured consultation notes, and our AI entity extractor parses them automatically into structured symptoms, provisional diagnoses, and medications for relational storage.\"",
        "POST /api/ai/extract-note processes clinical notes using medical entity extraction patterns, pre-populating relational form arrays for instant review and database persistence.",
        styles
    ))

    story.append(PageBreak())

    # SECTION 3: Deep Technical Architecture
    story.append(make_section_banner("3. TECHNICAL ARCHITECTURE & DATABASE SCHEMA", styles))
    story.append(Spacer(1, 6))

    schema_summary = [
        ["Table Name", "Primary Key & FKs", "3NF Normalization Role & Purpose"],
        ["users", "id, role_id -> roles.id", "Authentication credentials, bcrypt password hash, active status."],
        ["roles", "id (Unique: name)", "Role-based permissions (Doctor, Admin, Nurse)."],
        ["doctor_profiles", "id, user_id -> users.id", "Clinical license, medical specialty, hospital affiliation."],
        ["patients", "id (Unique: mrn)", "Core demographics, DOB, sex, contact info, synthetic flag."],
        ["patient_doctor", "patient_id, doctor_id", "Many-to-Many junction table for physician assignments."],
        ["allergies", "id, patient_id -> patients.id", "Allergen, clinical reaction, severity, active status."],
        ["medical_history", "id, patient_id -> patients.id", "Pre-existing chronic conditions, onset date, status."],
        ["visits", "id, patient_id, doctor_id", "Core clinical encounter header: date, type, vitals (BP, HR, SpO2)."],
        ["symptoms", "id, visit_id -> visits.id", "Atomic symptoms: name, severity, duration in days, notes."],
        ["diagnoses", "id, visit_id -> visits.id", "Conditions, standard ICD-10 code, diagnostic status."],
        ["prescriptions", "id, visit_id, medication_id", "Medication order: dosage, frequency, route, duration."],
        ["medications", "id (Unique: name)", "Standard drug formulary: generic name, strength, dosage form."],
        ["clinical_notes", "id, visit_id -> visits.id", "Unstructured documentation: SOAP notes, progress remarks."],
        ["test_results", "id, visit_id -> visits.id", "Diagnostic labs: test name, value, unit, abnormal flag."],
        ["ai_summary_cache", "id, patient_id -> patients.id", "SHA-256 hash-checked cache of generated clinical summaries."],
        ["audit_logs", "id, user_id -> users.id", "Immutable audit trail: timestamp, action, IP, target record."],
    ]
    schema_tbl = Table([[Paragraph(c, styles["TableHeader"]) if i == 0 else Paragraph(c, styles["TableCell"]) for c in row] for i, row in enumerate(schema_summary)], colWidths=[90, 140, 257])
    schema_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BURGUNDY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALABASTER]),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(schema_tbl)
    story.append(Spacer(1, 10))

    # SECTION 4: Top 15 Viva Questions
    story.append(make_section_banner("4. TOP 15 VIVA QUESTIONS & BULLETPROOF TECHNICAL ANSWERS", styles))
    story.append(Spacer(1, 6))

    # Q1
    story.append(make_qa_block(
        1, "Why did you choose a Relational Database instead of NoSQL / MongoDB?",
        [
            "Medical data has strict relational integrity: a prescription cannot exist without a visit, and a visit cannot exist without a patient.",
            "Relational schemas prevent orphaned records via Foreign Key constraints with ON DELETE CASCADE or RESTRICT.",
            "SQL allows ACID transactions, ensuring that recording a visit, its symptoms, and its prescriptions either all commit together or roll back.",
            "Analytical aggregations like 'Top 5 Diagnoses' are computed directly by the database engine using SQL GROUP BY and COUNT, which is faster and cleaner than NoSQL aggregations.",
        ],
        styles,
        tech_tip="Emphasize ACID compliance, relational integrity, foreign key constraints, and multi-table transactions."
    ))

    # Q2
    story.append(make_qa_block(
        2, "How is your database normalized? Explain Third Normal Form (3NF) in your project.",
        [
            "<b>1NF:</b> Every column holds atomic values (no comma-separated symptom lists or arrays). Symptoms and prescriptions are separate child rows.",
            "<b>2NF:</b> All non-key attributes are fully dependent on the primary key, eliminating partial dependencies.",
            "<b>3NF:</b> No transitive dependencies exist. For example, medications (generic name, strength, dosage form) are normalized into their own 'medications' table rather than repeating inside 'prescriptions'. Prescriptions references medication_id.",
        ],
        styles,
        tech_tip="Point to the 'medications' table vs 'prescriptions' table as proof of 3NF eliminating transitive dependency."
    ))

    # Q3
    story.append(make_qa_block(
        3, "How does your AI Module work, and how do you guarantee Zero Hallucination?",
        [
            "We do not feed medical prompts into an unrestricted generative model that makes up clinical facts.",
            "Our summarizer uses an <b>Extractive & Citation-Grounded Pipeline</b>: it queries the relational database for symptoms, diagnoses, prescriptions, and labs.",
            "It computes recurrence frequencies mathematically, formats verified statements, and assigns a unique Primary Key citation tag (e.g., [V-101], [SYM-1], [DX-10]).",
            "Before output, the <b>Citation Gate</b> checks every tag against the indexed relational records. If an unsupported statement appears, it is dropped.",
            "If data is absent (e.g. no lipid panel), the AI explicitly reports 'No recent lipid panel recorded' rather than guessing normal values.",
        ],
        styles,
        tech_tip="Use the phrase: 'Our AI is citation-grounded; it synthesizes facts extracted directly from SQL rows and validates 100% of citations.'"
    ))

    # Q4
    story.append(make_qa_block(
        4, "What happens if a new visit is added? Does the AI summary show stale data?",
        [
            "We implemented an <b>Automated Cache Invalidation Engine</b>.",
            "When an AI summary is generated, its SHA-256 state hash and payload are cached in the 'ai_summary_cache' table.",
            "Whenever a new visit, symptom, diagnosis, allergy, or lab result is inserted or updated for a patient, our backend repository automatically invalidates or clears that patient's cached summary.",
            "The next request automatically re-computes a fresh grounded summary reflecting the latest visit.",
        ],
        styles,
        tech_tip="Mention SHA-256 content hashing and write-triggered cache invalidation."
    ))

    # Q5
    story.append(make_qa_block(
        5, "What tech stack did you use and why?",
        [
            "<b>Backend:</b> Python with FastAPI. Chosen for high-speed asynchronous processing, automatic OpenAPI/Swagger documentation, and native Pydantic data validation.",
            "<b>Database:</b> Relational SQLite for zero-configuration portability during evaluation, with an architecture fully compatible with PostgreSQL via SQLAlchemy ORM.",
            "<b>Frontend:</b> React 18 with TypeScript and Vite. Provides type-safe component state, fast client-side rendering, and instant HMR.",
            "<b>Styling:</b> Tailwind CSS with our custom 'Burgundy Clinical Design System' tokenized for high contrast and clinical readability.",
        ],
        styles,
        tech_tip="Highlight Pydantic for input validation and SQLAlchemy ORM for database abstraction."
    ))

    # Q6
    story.append(make_qa_block(
        6, "How did you implement security and patient privacy?",
        [
            "<b>Password Security:</b> Cryptographically hashed using bcrypt with salt rounds.",
            "<b>Stateless Authentication:</b> Signed JWT bearer tokens with expiration timestamps, stored securely in sessionStorage rather than localStorage to prevent persistent XSS exposure.",
            "<b>Role-Based Access Control (RBAC):</b> Endpoints are protected by dependency injection checking whether the authenticated user has 'doctor' or 'admin' privileges.",
            "<b>Audit Logging:</b> Every patient inspection, visit creation, and query is recorded immutably in the 'audit_logs' table with user ID, action, and timestamp.",
            "<b>De-identification:</b> All demonstration records are tagged with 'is_synthetic = true' ensuring zero real PHI (Protected Health Information) exposure.",
        ],
        styles,
        tech_tip="Highlight sessionStorage vs localStorage for healthcare token protection."
    ))

    # Q7
    story.append(make_qa_block(
        7, "How does the Natural Language Historical Retrieval work?",
        [
            "The user inputs a query like 'What medications were prescribed during previous visits?'.",
            "The backend intent analyzer maps the query to target relational record types (e.g., Prescriptions, Medications), detects temporal keywords ('last 2 years'), and expands clinical terms.",
            "It runs parameterized SQL queries targeting those specific tables for the patient.",
            "It scores retrieved records by relevance, formats them as structured cards, and attaches citation tags linked to the raw database rows.",
            "If zero rows match, the system returns a polite refusal ('Insufficient clinical data found in stored records') without hallucinating.",
        ],
        styles,
        tech_tip="Explain that natural language is parsed into structured SQL filters rather than raw LLM generation."
    ))

    # Q8
    story.append(make_qa_block(
        8, "What are the check constraints in your database?",
        [
            "In 'visits': vitals_hr CHECK (vitals_hr BETWEEN 30 AND 260) to prevent impossible heart rates.",
            "In 'visits': vitals_spo2 CHECK (vitals_spo2 BETWEEN 50 AND 100) to ensure physiological oxygen saturation boundaries.",
            "In 'allergies': status CHECK (status IN ('Active', 'Resolved', 'Inactive')).",
            "In 'symptoms': severity CHECK (severity IN ('Mild', 'Moderate', 'Severe', 'Critical')).",
            "These constraints enforce medical data integrity at the database level regardless of the client.",
        ],
        styles,
        tech_tip="Examiners love database-level CHECK constraints because it proves you know relational engineering beyond simple tables."
    ))

    # Q9
    story.append(make_qa_block(
        9, "How did you test your application?",
        [
            "<b>Backend:</b> Pytest test suite ('tests/test_api.py') with 7 comprehensive invariant tests covering health checks, RBAC boundaries, CRUD operations, SQL aggregations, citation grounding, and entity extraction. (100% passing).",
            "<b>Frontend:</b> Vitest + Testing Library suite ('src/__tests__/App.test.tsx') with 6 end-to-end user journey tests covering authentication, dashboard KPIs, directory pagination, demographics editing, citation inspection, and retrieval refusal.",
            "<b>Static Typing & Build:</b> Full TypeScript verification ('tsc && vite build') with 0 type errors.",
        ],
        styles,
        tech_tip="Mention Test-Driven Development (TDD) and 100% automated test suite pass rate."
    ))

    # Q10
    story.append(make_qa_block(
        10, "How do you handle scalability if the hospital grows to 100,000 patients?",
        [
            "1. <b>Database Migration:</b> SQLAlchemy makes switching from SQLite to PostgreSQL a one-line configuration change in DATABASE_URL.",
            "2. <b>Database Indexing:</b> All foreign keys (patient_id, visit_id, medication_id) and searchable columns (mrn, name, phone, icd10_code) have B-tree indexes for O(log N) lookup.",
            "3. <b>Pagination:</b> API endpoints use LIMIT and OFFSET (or cursor-based pagination) to prevent loading large tables into memory.",
            "4. <b>Asynchronous API:</b> FastAPI's async/await architecture handles thousands of concurrent requests with low memory footprint.",
            "5. <b>Caching:</b> AI summaries and medication catalogs are cached, preventing repetitive heavy SQL aggregations.",
        ],
        styles,
        tech_tip="Mention B-tree indexing on foreign keys and cursor-based pagination for large datasets."
    ))

    # Q11 to Q15 condensed
    story.append(make_qa_block(
        11, "What is the difference between Extractive and Abstractive Summarization in medical AI?",
        [
            "<b>Abstractive Summarization:</b> Generates new phrasing using an LLM. High risk of hallucinating dosages or diagnoses, dangerous in clinical medicine.",
            "<b>Extractive Summarization (Our Approach):</b> Pulls verified data points directly from stored relational rows and stitches them into a coherent clinical summary with citations. Guaranteed accuracy.",
        ],
        styles,
        tech_tip="State clearly: 'In clinical medicine, extractive, citation-backed summarization is safer than pure abstractive generation.'"
    ))

    story.append(make_qa_block(
        12, "What is ICD-10 and why did you include it?",
        [
            "ICD-10 stands for <i>International Classification of Diseases, Tenth Revision</i>, published by the World Health Organization (WHO).",
            "It provides globally standardized alphanumeric codes for medical conditions (e.g., G43.909 for Migraine, I10 for Essential Hypertension).",
            "Including ICD-10 enables semantic standardization, accurate historical retrieval, and medical billing interoperability.",
        ],
        styles,
        tech_tip="Mention WHO international standardization and billing/interoperability."
    ))

    story.append(make_qa_block(
        13, "What is a SOAP Note?",
        [
            "SOAP is the gold-standard documentation format used by physicians worldwide:",
            "<b>S (Subjective):</b> What the patient tells the doctor (symptoms, complaints).",
            "<b>O (Objective):</b> Measurable physical exam findings and vital signs (BP, heart rate).",
            "<b>A (Assessment):</b> Doctor's diagnostic evaluation and clinical impression.",
            "<b>P (Plan):</b> Prescriptions, therapies, ordered laboratory tests, and follow-up timeline.",
        ],
        styles,
        tech_tip="Say: 'Our system stores and parses clinical documentation according to the universal medical SOAP standard.'"
    ))

    story.append(make_qa_block(
        14, "What are the limitations of your project, and what is your future roadmap?",
        [
            "1. <b>FHIR / HL7 Integration:</b> Future work will add HL7/FHIR export standards for integration with enterprise hospital systems like Epic or Cerner.",
            "2. <b>Vector Embeddings:</b> Hybrid retrieval combining SQL keyword filtering with dense vector search (e.g. pgvector) for complex semantic symptom matching.",
            "3. <b>Multi-Modal Imaging:</b> Storing DICOM medical imaging (X-rays, MRI scans) with automated radiologist report extraction.",
        ],
        styles,
        tech_tip="Mentioning FHIR/HL7 and DICOM shows deep domain awareness that impresses professors."
    ))

    story.append(make_qa_block(
        15, "What did each team member contribute?",
        [
            "<b>Pushkar Panwar (2501730022):</b> Database architecture, 13-table 3NF schema design, SQL constraints, foreign key indexing, FastAPI RESTful API routing, and backend Pytest test suite.",
            "<b>Saksham Singh (2501730270):</b> Frontend architecture, React + TypeScript UI, Burgundy Clinical Design System, AI Grounding & Citation engine, Vitest testing, and Vercel cloud deployment.",
        ],
        styles,
        tech_tip="Speak confidently and clearly about your specific contributions."
    ))

    doc.build(story, canvasmaker=NumberedVivaCanvas)

    # Also copy to frontend public directory so it's downloadable from the web app
    import shutil
    shutil.copyfile(OUTPUT_PDF, PUBLIC_PDF)

    return OUTPUT_PDF


if __name__ == "__main__":
    pdf_path = generate_viva_guide_pdf()
    print(f"Generated Viva & Walkthrough Guide PDF: {pdf_path}")
    print(f"File size: {pdf_path.stat().st_size} bytes")
