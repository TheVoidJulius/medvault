# MedVault AI: AI-Assisted Medical Record Database

**Team Members:**
- **Pushkar Panwar** (`2501730022`)
- **Saksham Singh** (`2501730270`)

MedVault AI stores longitudinal patient histories in a 13-table Third Normal Form (3NF) relational database and pairs them with a citation-grounded AI synthesis and natural-language retrieval engine.

- **Live Production URL:** https://ai-medical-records.vercel.app
- **Presentation Deck:** Open `/presentation.html` inside the app or `docs/presentation.html` locally.
- **Project report and flow (PDF):** `docs/MedVault_AI_Project_Report.pdf`

---

## Architecture Highlights

1. **Normalised Relational Schema (13 Tables):** Separates identity (`users`, `roles`, `doctors`), patient profiles (`patients`, `allergies`, `medical_history`), encounters (`visits`), and clinical child records (`symptoms`, `diagnoses`, `prescriptions`, `medications`, `clinical_notes`, `test_results`), plus `ai_summaries` and `audit_logs`.
2. **Database-First Grounding:** SQL computes recurrence counts, active allergies, prescription histories, lab value trajectories, and top-symptom `GROUP BY` aggregations. The AI formatter attaches primary-key tags (`[V-1]`, `[SYM-2]`, `[DX-3]`, `[RX-4]`, `[LAB-5]`, `[ALG-1]`) that the backend validator verifies before returning responses.
3. **Refusal on Missing Records:** Queries for conditions absent from a patient's history return `total_matches: 0` and refuse to extrapolate unrecorded facts.
4. **Access Control & Audit Trail:** Passwords hash with `bcrypt`, endpoints enforce HS256 JWT bearer authentication, and every login, record write, summary generation, and retrieval query logs to `audit_logs`.

---

## Quick Start (Local Development)

### Option A: One-Command Windows Launcher
Run from `c:\Users\flypi\Desktop\projects\ai-medical-records`:
```powershell
.\start-project.ps1
```

### Option B: Start Backend and Frontend Manually

**Terminal 1 (FastAPI Backend):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```
API documentation runs at `http://127.0.0.1:8000/docs`.

**Terminal 2 (React + Vite Frontend):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\frontend
npm run dev
```
Web application runs at `http://localhost:5173`.

---

## Demo Login Accounts

Every doctor account uses the password `Doctor@123`. The admin account uses `Admin@123`.

| Role | Name | Email |
|---|---|---|
| Doctor | Dr. Ananya Sharma, MD (Internal Medicine) | `dr.sharma@medvault.edu` |
| Doctor | Dr. Rajesh Verma, DM (Neurology) | `dr.verma@medvault.edu` |
| Doctor | Dr. Priya Nair, MD (Pulmonology) | `dr.nair@medvault.edu` |
| Doctor | Dr. Arjun Reddy, DM (Cardiology) | `dr.reddy@medvault.edu` |
| Doctor | Dr. Farhan Qureshi, DM (Endocrinology) | `dr.qureshi@medvault.edu` |
| Doctor | Dr. Lakshmi Subramanian, MS (Obstetrics & Gynaecology) | `dr.subramanian@medvault.edu` |
| Doctor | Dr. Harpreet Kaur, MD (Paediatrics) | `dr.kaur@medvault.edu` |
| Doctor | Dr. Sanjay Banerjee, DM (Nephrology) | `dr.banerjee@medvault.edu` |
| Doctor | Dr. Meenakshi Pillai, DM (Gastroenterology) | `dr.pillai@medvault.edu` |
| Doctor | Dr. Kunal Chatterjee, MD (Psychiatry) | `dr.chatterjee@medvault.edu` |
| Doctor | Dr. Vivek Patil, MS (Orthopaedics) | `dr.patil@medvault.edu` |
| Admin | Pushkar Panwar (System Admin) | `admin@medvault.edu` |

The sign-in screen offers four of these as one-click presets.

## Synthetic Patient Data

The database seeds 162 synthetic patients and about 400 visits on first start:

- **6 hand-written storylines** (`backend/app/db/seed_data.py`): Aarav Mehta's migraine, Meera Krishnan's diabetes, and four others. The tests rely on these.
- **156 generated patients** (`backend/app/db/cohort*.py`): deterministic (fixed seed), so every deployment gets the same people. Names, surnames, localities and PIN codes come from matching regions: North Indian, Punjabi, Bengali, Tamil, Telugu, Kannada, Malayali, Marathi, Gujarati, Urdu-speaking, Bihari, Odia, Assamese and Sikkimese.
- **23 clinical storylines** drawn from common Indian OPD practice: diabetes with hypertension, CKD, coronary artery disease, NAFLD, drug-sensitive TB on HRZE, dengue with falling platelets, typhoid, *P. vivax* malaria, chikungunya, childhood gastroenteritis, recurrent tonsillitis, UTI, hypothyroidism, PCOS, iron-deficiency anaemia, gestational diabetes, vitamin D/B12 deficiency, asthma, COPD from biomass smoke, knee osteoarthritis, GERD with *H. pylori*, and depression.

Each storyline spans 1 to 3 visits with symptoms that recur, diagnoses that change status (provisional, confirmed, ruled out, resolved) and lab values that trend, so the AI summary has real material to cite. About 6% of patients have no blood group recorded and a few have no emergency contact number, so the data-gap detector has real gaps to find.

To reseed locally, delete `backend/medical_records.db` and restart the API.

---|---|---|---|
| **Doctor** | Dr. Ananya Sharma, MD (Internal Medicine) | `dr.sharma@medvault.edu` | `Doctor@123` |
| **Doctor** | Dr. Rajesh Verma, DM (Neurology) | `dr.verma@medvault.edu` | `Doctor@123` |
| **Doctor** | Dr. Priya Nair, MD (Pulmonology) | `dr.nair@medvault.edu` | `Doctor@123` |
| **Admin** | Pushkar Panwar (System Admin) | `admin@medvault.edu` | `Admin@123` |

Click any account preset on the sign-in screen to populate credentials in one click.

---

## Verification & Build Commands

**Run the 7-invariant backend test suite (`pytest`):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\backend
.\.venv\Scripts\python.exe -m pytest -v
```

**Run the frontend test suite (`vitest`):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\frontend
npm test
```

**Build the frontend bundle (`tsc` + `vite`):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\frontend
npm run build
```

**Regenerate the project report PDF** (needs `pip install reportlab`; reads live numbers from the seeded database and screenshots from `docs/screenshots/`):
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\backend
.\.venv\Scripts\python.exe scripts\generate_report.py
```

---

## Switching to Docker PostgreSQL 16

The backend defaults to local SQLite (`medical_records.db`, or `/tmp/medical_records.db` on Vercel serverless functions) so it starts with zero manual configuration. To run against PostgreSQL 16:

1. Start Docker Desktop and launch PostgreSQL:
   ```powershell
   docker compose up -d
   ```
2. Update `backend/.env`:
   ```env
   DATABASE_URL=postgresql://medadmin:medpassword123@localhost:5432/medical_records_db
   ```
3. Restart Uvicorn to create tables and seed the 162 synthetic patients.

---

## Project Documentation
- [SQL DDL Schema (`docs/DATABASE_SCHEMA.sql`)](docs/DATABASE_SCHEMA.sql)
- [Project report and flow, PDF (`docs/MedVault_AI_Project_Report.pdf`)](docs/MedVault_AI_Project_Report.pdf): architecture, user flow, AI pipelines, database, screenshots, demo script and viva questions
- [Screenshots of every screen (`docs/screenshots/`)](docs/screenshots/)
- [16:9 HTML Presentation Deck (`docs/presentation.html`)](docs/presentation.html)
