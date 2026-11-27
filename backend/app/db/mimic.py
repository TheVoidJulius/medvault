"""Seed MedVault with real, de-identified hospital patients from the MIMIC-IV demo.

The seed file is produced by scripts/build_mimic_seed.py from PhysioNet's MIMIC-IV Clinical
Database Demo and MIMIC-IV-ED Demo (ODbL). See app/db/data/README.md for attribution.
"""

import gzip
import json
from datetime import date, datetime, timezone
from pathlib import Path
from random import Random
from typing import Dict

from sqlalchemy.orm import Session

from app.db.cohort import add_specialist_doctors
from app.models import ClinicalNote, Diagnosis, Doctor, Medication, Patient, Prescription, Symptom, TestResult, Visit

SEED_FILE = Path(__file__).resolve().parent / "data" / "mimic_iv_demo.json.gz"

# MIMIC hospital service code -> MedVault demo doctor account (app users, not source data)
SERVICE_TO_DOCTOR = {
    "CMED": "cardio", "CSURG": "cardio", "NMED": "neuro", "NSURG": "neuro", "OMED": "internal",
    "SURG": "ortho", "TSURG": "ortho", "VSURG": "ortho", "ORTHO": "ortho", "TRAUM": "ortho",
    "GU": "nephro", "GYN": "obgyn", "OBS": "obgyn", "PSYCH": "psych",
}


def load_source() -> dict:
    with gzip.open(SEED_FILE, "rt", encoding="utf-8") as f:
        return json.load(f)


def seed_mimic(db: Session, doctors: Dict[str, Doctor]) -> int:
    data = load_source()
    add_specialist_doctors(db, doctors, Random(2026))

    meds: Dict[str, Medication] = {}
    for m in data["medications"]:
        med = Medication(name=m["name"], generic_name=m["name"], drug_class=None, form=m["form"][:50], strength=m["strength"][:50])
        db.add(med)
        meds[m["name"]] = med

    for p in data["patients"]:
        patient = Patient(
            mrn=f"MIMIC-{p['subject_id']}",
            first_name="Patient",
            last_name=p["subject_id"],
            date_of_birth=date(p["birth_year"], 7, 1),
            sex=p["sex"],
            blood_group=None,
            phone="",
            email=None,
            address=None,
            emergency_contact_name=None,
            emergency_contact_phone=None,
            is_synthetic=False,
            is_active=True,
        )
        db.add(patient)
        assigned = set()
        for v in p["visits"]:
            doctor = doctors[SERVICE_TO_DOCTOR.get(v["service"], "internal")]
            if doctor.id not in assigned:
                patient.assigned_doctors.append(doctor)
                assigned.add(doctor.id)
            when = datetime.fromisoformat(v["date"]).replace(tzinfo=timezone.utc)
            vit = v["vitals"]
            visit = Visit(
                patient=patient,
                doctor=doctor,
                visit_date=when,
                visit_type=v["type"],
                chief_complaint=v["complaint"],
                vitals_bp=vit["bp"],
                vitals_hr=vit["hr"],
                vitals_temp_c=vit["temp"],
                vitals_spo2=vit["spo2"],
                vitals_weight_kg=vit["weight"],
                treatment_plan=v["plan"],
                created_at=when,
                updated_at=when,
            )
            visit.symptoms = [Symptom(name=s["name"][:120], severity=s["severity"], duration_days=None, notes=s["notes"][:255]) for s in v["symptoms"]]
            visit.diagnoses = [Diagnosis(condition_name=d["name"][:160], icd10_code=d["code"], status="Confirmed", notes=d["notes"]) for d in v["diagnoses"]]
            visit.prescriptions = [
                Prescription(medication=meds[r["drug"][:138]], dosage=r["dosage"], frequency=r["frequency"][:80],
                             duration_days=r["days"], instructions=r["instructions"])
                for r in v["rx"]
            ]
            visit.clinical_notes = [ClinicalNote(author_id=doctor.user_id, note_type="Discharge" if v["type"] == "Inpatient" else "Consultation",
                                                 content=v["note"], created_at=when)]
            visit.test_results = [
                TestResult(test_name=l["name"][:140], value=l["value"], unit=l["unit"], reference_range=l["ref"], flag=l["flag"],
                           result_date=when.date(), remarks=l["remarks"])
                for l in v["labs"]
            ]
            db.add(visit)
    db.flush()
    return len(data["patients"])
