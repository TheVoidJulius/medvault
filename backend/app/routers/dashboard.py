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

    visit_dates = [row[0] for row in db.query(Visit.visit_date).all()]
    visits_by_month = []
    if visit_dates:
        latest = max(visit_dates)
        year, month = latest.year, latest.month
        months = []
        for _ in range(12):
            months.append((year, month))
            month -= 1
            if month == 0:
                year, month = year - 1, 12
        counts_by_month = {}
        for d in visit_dates:
            counts_by_month[(d.year, d.month)] = counts_by_month.get((d.year, d.month), 0) + 1
        visits_by_month = [
            {"month": f"{y}-{m:02d}", "count": counts_by_month.get((y, m), 0)} for y, m in reversed(months)
        ]

    type_rows = db.query(Visit.visit_type, func.count(Visit.id)).group_by(Visit.visit_type).all()
    visit_type_mix = [{"visit_type": t, "count": n} for t, n in type_rows]

    flagged_q = (
        db.query(TestResult)
        .options(joinedload(TestResult.visit).joinedload(Visit.patient))
        .filter(TestResult.flag.in_(["Critical", "High", "Low", "Abnormal"]))
        .order_by(TestResult.result_date.desc(), TestResult.id.desc())
        .limit(8)
        .all()
    )
    flagged_labs = [
        {
            "lab_id": t.id,
            "lab_tag": f"LAB-{t.id}",
            "visit_id": t.visit_id,
            "patient_id": t.visit.patient_id,
            "patient_name": f"{t.visit.patient.first_name} {t.visit.patient.last_name}",
            "patient_mrn": t.visit.patient.mrn,
            "test_name": t.test_name,
            "value": t.value,
            "unit": t.unit,
            "reference_range": t.reference_range,
            "flag": t.flag,
            "result_date": t.result_date.isoformat(),
        }
        for t in flagged_q
    ]

    return {
        "visits_by_month": visits_by_month,
        "visit_type_mix": visit_type_mix,
        "flagged_labs": flagged_labs,
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


@router.get("/public")
def public_overview(db: Session = Depends(get_db)):
    """Aggregate counts for the public landing page. Totals only; no patient rows leave without sign-in."""
    first, last = db.query(func.min(Visit.visit_date), func.max(Visit.visit_date)).one()
    real = db.query(Patient).filter(Patient.is_synthetic == False).count()  # noqa: E712
    return {
        "patients": db.query(Patient).filter(Patient.is_active == True).count(),  # noqa: E712
        "real_patients": real,
        "visits": db.query(Visit).count(),
        "emergency_visits": db.query(Visit).filter(Visit.visit_type == "Emergency").count(),
        "diagnoses": db.query(Diagnosis).count(),
        "distinct_conditions": db.query(func.count(func.distinct(Diagnosis.condition_name))).scalar(),
        "prescriptions": db.query(Prescription).count(),
        "lab_results": db.query(TestResult).count(),
        "abnormal_labs": db.query(TestResult).filter(TestResult.flag != "Normal").count(),
        "symptoms": db.query(Symptom).count(),
        "notes": db.query(ClinicalNote).count(),
        "first_year": first.year if first else None,
        "last_year": last.year if last else None,
        "source": (
            {
                "name": "MIMIC-IV Clinical Database Demo v2.2 and MIMIC-IV-ED Demo v2.2",
                "institution": "Beth Israel Deaconess Medical Center, Boston",
                "license": "Open Database License (ODbL)",
                "url": "https://physionet.org/content/mimic-iv-demo/2.2/",
            }
            if real
            else {"name": "Synthetic demonstration records", "institution": None, "license": None, "url": None}
        ),
    }
