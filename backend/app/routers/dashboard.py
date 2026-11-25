from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    Doctor,
    Patient,
    Prescription,
    Symptom,
    TestResult,
    User,
    Visit,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard & Analytics"])


@router.get("/stats")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_patients = db.query(Patient).filter(Patient.is_active == True).count()
    total_visits = db.query(Visit).count()
    total_diagnoses = db.query(Diagnosis).count()
    total_prescriptions = db.query(Prescription).count()
    total_notes = db.query(ClinicalNote).count()
    total_labs = db.query(TestResult).count()
    total_symptoms = db.query(Symptom).count()
    total_allergies = db.query(Allergy).count()

    total_medical_records = (
        total_visits + total_diagnoses + total_prescriptions + total_notes + total_labs + total_symptoms
    )

    recent_visits_q = (
        db.query(Visit)
        .options(
            joinedload(Visit.patient),
            joinedload(Visit.doctor).joinedload(Doctor.user),
            joinedload(Visit.diagnoses),
            joinedload(Visit.test_results),
        )
        .order_by(Visit.visit_date.desc())
        .limit(8)
        .all()
    )

    recent_visits = [
        {
            "visit_id": v.id,
            "visit_tag": f"V-{v.id}",
            "patient_id": v.patient_id,
            "patient_name": f"{v.patient.first_name} {v.patient.last_name}" if v.patient else "Unknown",
            "patient_mrn": v.patient.mrn if v.patient else "",
            "doctor_name": v.doctor.user.full_name if v.doctor and v.doctor.user else "Attending",
            "visit_date": v.visit_date.isoformat(),
            "visit_type": v.visit_type,
            "chief_complaint": v.chief_complaint,
            "primary_diagnosis": v.diagnoses[0].condition_name if v.diagnoses else "Pending evaluation",
            "abnormal_lab_count": sum(1 for t in v.test_results if t.flag != "Normal"),
        }
        for v in recent_visits_q
    ]

    recently_updated_patients_q = (
        db.query(Patient)
        .options(joinedload(Patient.visits), joinedload(Patient.allergies))
        .filter(Patient.is_active == True)
        .order_by(Patient.updated_at.desc())
        .limit(6)
        .all()
    )

    recently_updated_records = [
        {
            "patient_id": p.id,
            "mrn": p.mrn,
            "full_name": f"{p.first_name} {p.last_name}",
            "sex": p.sex,
            "blood_group": p.blood_group,
            "visit_count": len(p.visits),
            "allergy_count": len(p.allergies),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in recently_updated_patients_q
    ]

    dx_rows = (
        db.query(Diagnosis.condition_name, func.count(Diagnosis.id).label("cnt"))
        .filter(Diagnosis.status != "Ruled-out")
        .group_by(Diagnosis.condition_name)
        .order_by(func.count(Diagnosis.id).desc())
        .limit(6)
        .all()
    )
    top_conditions = [{"condition": row.condition_name, "count": row.cnt} for row in dx_rows]

    sym_rows = (
        db.query(Symptom.name, func.count(Symptom.id).label("cnt"))
        .group_by(Symptom.name)
        .order_by(func.count(Symptom.id).desc())
        .limit(6)
        .all()
    )
    top_symptoms = [{"symptom": row.name, "count": row.cnt} for row in sym_rows]

    return {
        "counts": {
            "total_patients": total_patients,
            "total_visits": total_visits,
            "total_medical_records": total_medical_records,
            "total_diagnoses": total_diagnoses,
            "total_prescriptions": total_prescriptions,
            "total_clinical_notes": total_notes,
            "total_lab_results": total_labs,
            "total_allergies": total_allergies,
        },
        "recent_visits": recent_visits,
        "recently_updated_records": recently_updated_records,
        "top_conditions": top_conditions,
        "top_symptoms": top_symptoms,
    }
