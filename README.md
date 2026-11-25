# MedVault AI: AI-Assisted Medical Record Database

**Team Members:**
- **Pushkar Panwar** (`2501730022`)
- **Saksham Singh** (`2501730270`)

MedVault AI stores longitudinal patient histories in a 13-table Third Normal Form (3NF) relational database and pairs them with a citation-grounded AI synthesis and natural-language retrieval engine.

- **Live Production URL:** https://ai-medical-records.vercel.app
- **Presentation Deck:** Open `/presentation.html` inside the app or `docs/presentation.html` locally.
- **Technical PDF Report:** `docs/MedVault_AI_Technical_Report.pdf`

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

| Role | Name | Email | Password |
|---|---|---|---|
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

**Build the frontend bundle (`tsc` + `vite`):**
```powershell
cd c:\Users\flypi\Desktop\projects\ai-medical-records\frontend
npm run build
```

**Regenerate the editorial PDF report:**
```powershell
python c:\Users\flypi\Desktop\projects\ai-medical-records\backend\scripts\generate_pdf_report.py
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
3. Restart Uvicorn to create tables and seed the 6 synthetic clinical storylines.

---

## Project Documentation
- [SQL DDL Schema (`docs/DATABASE_SCHEMA.sql`)](docs/DATABASE_SCHEMA.sql)
- [Engineering Audit & Viva Guide (`docs/PROJECT_REPORT_AND_VIVA_GUIDE.md`)](docs/PROJECT_REPORT_AND_VIVA_GUIDE.md)
- [Editorial PDF Technical Report (`docs/MedVault_AI_Technical_Report.pdf`)](docs/MedVault_AI_Technical_Report.pdf)
- [16:9 HTML Presentation Deck (`docs/presentation.html`)](docs/presentation.html)
