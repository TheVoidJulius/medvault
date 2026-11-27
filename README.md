# MedVault AI: AI-Assisted Medical Record Database

**Team Members:**
- **Pushkar Panwar** (`2501730022`)
- **Saksham Singh** (`2501730270`)

MedVault AI stores longitudinal patient histories in a 13-table Third Normal Form (3NF) relational database and pairs them with a citation-grounded AI synthesis and natural-language retrieval engine.

- **Live Production URL:** https://medvault-ai-smoky.vercel.app (Pushkar's deployment; https://ai-medical-records.vercel.app is Saksham's)
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

Visitors first see the public landing page; **Open the records** leads to sign-in, which offers four of these accounts as one-click presets.

## Patient Data: real, de-identified hospital records

MedVault seeds **100 real patients** of Beth Israel Deaconess Medical Center (Boston) from the **MIMIC-IV Clinical Database Demo** and **MIMIC-IV-ED Demo** (v2.2), published on PhysioNet under the Open Database License. This gives 325 visits, 2,253 ICD-9/ICD-10 diagnoses, 2,934 drug orders and about 3,400 lab results.

- The publishers de-identified the data: no names, addresses or exact dates. Patients appear as `Patient 10040025` with MRN `MIMIC-10040025`.
- Allergies, blood group and free-text notes are not in the demo. The AI reports them as gaps instead of guessing.
- Source, licence, citation and exact field mapping: [`backend/app/db/data/README.md`](backend/app/db/data/README.md).
- Using a real hospital's live records would need ethics approval and patient consent (India's DPDP Act 2023), so a published research dataset is used instead.

`DATA_SOURCE=synthetic` switches back to the hand-written storylines and the generated Indian cohort (`backend/app/db/seed_data.py`, `cohort*.py`). The pytest suite always runs on that synthetic data in a temporary database (`backend/tests/conftest.py`).

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
3. Restart Uvicorn to create tables and seed the 100 MIMIC-IV patients.

---

## Project Documentation
- [SQL DDL Schema (`docs/DATABASE_SCHEMA.sql`)](docs/DATABASE_SCHEMA.sql)
- [Project report and flow, PDF (`docs/MedVault_AI_Project_Report.pdf`)](docs/MedVault_AI_Project_Report.pdf): architecture, user flow, AI pipelines, database, screenshots, demo script and viva questions
- [Screenshots of every screen (`docs/screenshots/`)](docs/screenshots/)
- [16:9 HTML Presentation Deck (`docs/presentation.html`)](docs/presentation.html)
