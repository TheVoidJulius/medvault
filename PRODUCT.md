# Product Brief: MedVault AI

**Product:** MedVault AI: AI-Assisted Medical Record Database
**Authors:** Pushkar Panwar (`2501730022`) and Saksham Singh (`2501730270`)
**Surface Mode:** Operate (authenticated clinical workspace for structured record management, review, and synthesis)

## Purpose
Medical teams accumulate longitudinal patient records across outpatient visits, emergency encounters, diagnostic labs, and medication orders. MedVault AI stores those records in a normalised 13-table relational schema and generates citation-verified clinical summaries and natural-language retrievals grounded strictly in stored primary keys.

## Target Users
1. **Attending Physicians & Specialists:** Review patient history before consultations, log visits with vitals and SOAP notes, inspect abnormal lab trends, and verify AI summaries against primary-key citations.
2. **Clinical Records Administrators:** Register patients, generate unique Medical Record Numbers (MRNs), audit access logs, and maintain demographic integrity.

## Core Workflows
- **Authentication & Access Control:** Email/password login verified via `bcrypt`, JWT bearer tokens, role gates (`doctor`, `admin`), and action audit logging.
- **Clinical Intelligence Dashboard:** Live relational counts, SQL `GROUP BY` symptom and diagnosis frequency distributions, recent encounters, and fast patient search.
- **Patient Registry & Profile Management:** Search, filter, sort, and paginate registered patients; register new profiles; edit patient demographics; manage active allergies and baseline medical history.
- **Encounter Timeline & Structured Data Entry:** Chronological visit cards with vital signs, symptoms, ICD-10 diagnoses, prescriptions, SOAP notes, and lab results; filterable timeline; inline visit editing; multi-item visit creation with AI SOAP entity extraction.
- **Grounded AI Synthesis & Retrieval:** One-click patient summaries with 100% citation validation, explicit missing/conflicting data detection, per-claim review flagging, clickable source inspection drawer, and natural-language retrieval that refuses to extrapolate unrecorded facts.

- **Fast navigation:** Command palette (Ctrl K / ⌘K or `/`) to jump to any patient by name, MRN or condition; shareable URLs for every chart tab.
- **Public landing page:** explains the product with live database totals before sign-in; no patient rows are public.
- **Real de-identified data:** 100 patients from the MIMIC-IV demo (Beth Israel Deaconess Medical Center, ODbL). A synthetic Indian cohort remains available with `DATA_SOURCE=synthetic`.

## Privacy & Clinical Safety Principles
- The default dataset is de-identified research data (MIMIC-IV demo), flagged `is_synthetic = false`; no patient row is sent to an external AI service unless `ALLOW_EXTERNAL_PHI` is set.
- Auth session credentials live in `sessionStorage` rather than persistent storage and clear on logout.
- Every AI-generated panel carries a prominent clinical decision-support notice separating AI synthesis from stored records.
