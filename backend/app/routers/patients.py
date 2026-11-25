from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, log_audit, require_roles
from app.db.session import get_db
from app.models import (
    AISummaryCache,
    Allergy,
    ClinicalNote,
    Diagnosis,
    Doctor,
    MedicalHistoryItem,
    Medication,
    Patient,
    Prescription,
    Symptom,
    TestResult,
    User,
    Visit,
)
from app.schemas import (
    AllergyCreate,
    AllergyOut,
    ClinicalNoteOut,
    MedicalHistoryCreate,
    MedicalHistoryOut,
    MedicationOut,
    PatientCreate,
    PatientDetailOut,
    PatientListItem,
    PatientUpdate,
    VisitCreate,
    VisitOut,
    VisitUpdate,
)

router = APIRouter(prefix="/api/patients", tags=["Patients & Medical Records"])


def _generate_next_mrn(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Patient).count() + 1
    while True:
        candidate = f"MRN-{year}-{count:05d}"
        exists = db.query(Patient).filter(Patient.mrn == candidate).first()
        if not exists:
            return candidate
        count += 1


def _serialize_visit(v: Visit) -> VisitOut:
    doc_name = v.doctor.user.full_name if v.doctor and v.doctor.user else "Attending Physician"
    doc_spec = v.doctor.specialization if v.doctor else "General Medicine"
    notes_out = [
        ClinicalNoteOut(
            id=n.id,
            visit_id=n.visit_id,
            author_id=n.author_id,
            author_name=n.author.full_name if n.author else doc_name,
            note_type=n.note_type,
            content=n.content,
            created_at=n.created_at,
        )
        for n in v.clinical_notes
    ]
    return VisitOut(
        id=v.id,
        patient_id=v.patient_id,
        doctor_id=v.doctor_id,
        doctor_name=doc_name,
        doctor_specialization=doc_spec,
        visit_date=v.visit_date,
        visit_type=v.visit_type,
        chief_complaint=v.chief_complaint,
        vitals_bp=v.vitals_bp,
        vitals_hr=v.vitals_hr,
        vitals_temp_c=v.vitals_temp_c,
        vitals_spo2=v.vitals_spo2,
        vitals_weight_kg=v.vitals_weight_kg,
        treatment_plan=v.treatment_plan,
        follow_up_date=v.follow_up_date,
        created_at=v.created_at,
        updated_at=v.updated_at,
        symptoms=v.symptoms,
        diagnoses=v.diagnoses,
        prescriptions=v.prescriptions,
        clinical_notes=notes_out,
        test_results=v.test_results,
    )


@router.get("", response_model=List[PatientListItem])
def list_patients(
    q: Optional[str] = Query(None, description="Search by name, MRN, phone, email, or condition"),
    sex: Optional[str] = Query(None),
    blood_group: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Patient).options(
        joinedload(Patient.visits).joinedload(Visit.diagnoses),
        joinedload(Patient.allergies),
        joinedload(Patient.medical_history),
    )

    if active_only:
        query = query.filter(Patient.is_active == True)
    if sex:
        query = query.filter(Patient.sex == sex)
    if blood_group:
        query = query.filter(Patient.blood_group == blood_group)

    patients = query.order_by(Patient.updated_at.desc()).all()

    results: List[PatientListItem] = []
    q_clean = q.strip().lower() if q else None

    for p in patients:
        sorted_visits = sorted(p.visits, key=lambda v: v.visit_date, reverse=True)
        last_v = sorted_visits[0].visit_date if sorted_visits else None

        conditions = []
        for h in p.medical_history:
            if h.condition_name not in conditions:
                conditions.append(h.condition_name)
        for v in sorted_visits:
            for d in v.diagnoses:
                if d.status != "Ruled-out" and d.condition_name not in conditions:
                    conditions.append(d.condition_name)

        allergies = [a.allergen for a in p.allergies if a.status == "Active"]

        if q_clean:
            searchable = " ".join(
                [
                    p.mrn,
                    p.first_name,
                    p.last_name,
                    f"{p.first_name} {p.last_name}",
                    p.phone or "",
                    p.email or "",
                    p.blood_group or "",
                    " ".join(conditions),
                    " ".join(allergies),
                ]
            ).lower()
            if q_clean not in searchable:
                continue

        results.append(
            PatientListItem(
                id=p.id,
                mrn=p.mrn,
                first_name=p.first_name,
                last_name=p.last_name,
                date_of_birth=p.date_of_birth,
                sex=p.sex,
                blood_group=p.blood_group,
                phone=p.phone,
                email=p.email,
                is_synthetic=p.is_synthetic,
                is_active=p.is_active,
                visit_count=len(p.visits),
                last_visit_date=last_v,
                primary_conditions=conditions[:4],
                active_allergies=allergies,
            )
        )

    return results


@router.post("", response_model=PatientDetailOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    mrn = _generate_next_mrn(db)
    patient = Patient(
        mrn=mrn,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
        blood_group=payload.blood_group,
        phone=payload.phone.strip(),
        email=payload.email.strip() if payload.email else None,
        address=payload.address,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        is_synthetic=True,
        is_active=True,
    )
    db.add(patient)
    db.flush()

    for alg in payload.allergies:
        db.add(
            Allergy(
                patient_id=patient.id,
                allergen=alg.allergen.strip(),
                reaction=alg.reaction.strip(),
                severity=alg.severity,
                status=alg.status,
                recorded_date=alg.recorded_date,
            )
        )

    for hx in payload.medical_history:
        db.add(
            MedicalHistoryItem(
                patient_id=patient.id,
                condition_name=hx.condition_name.strip(),
                category=hx.category,
                onset_date=hx.onset_date,
                status=hx.status,
                notes=hx.notes,
            )
        )

    if current_user.doctor_profile:
        patient.assigned_doctors.append(current_user.doctor_profile)

    db.commit()
    log_audit(
        db,
        current_user.id,
        "CREATE_PATIENT",
        patient_id=patient.id,
        detail=f"Registered patient {patient.first_name} {patient.last_name} ({patient.mrn})",
    )
    return get_patient_detail(patient.id, db, current_user)


@router.get("/medications/catalog", response_model=List[MedicationOut])
def get_medications_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Medication).order_by(Medication.name.asc()).all()


@router.get("/{patient_id}", response_model=PatientDetailOut)
def get_patient_detail(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = (
        db.query(Patient)
        .options(
            joinedload(Patient.allergies),
            joinedload(Patient.medical_history),
            joinedload(Patient.visits).joinedload(Visit.doctor).joinedload(Doctor.user),
            joinedload(Patient.visits).joinedload(Visit.symptoms),
            joinedload(Patient.visits).joinedload(Visit.diagnoses),
            joinedload(Patient.visits).joinedload(Visit.prescriptions).joinedload(Prescription.medication),
            joinedload(Patient.visits).joinedload(Visit.clinical_notes).joinedload(ClinicalNote.author),
            joinedload(Patient.visits).joinedload(Visit.test_results),
        )
        .filter(Patient.id == patient_id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    sorted_visits = sorted(patient.visits, key=lambda v: v.visit_date, reverse=True)
    return PatientDetailOut(
        id=patient.id,
        mrn=patient.mrn,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        blood_group=patient.blood_group,
        phone=patient.phone,
        email=patient.email,
        address=patient.address,
        emergency_contact_name=patient.emergency_contact_name,
        emergency_contact_phone=patient.emergency_contact_phone,
        is_synthetic=patient.is_synthetic,
        is_active=patient.is_active,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        allergies=patient.allergies,
        medical_history=patient.medical_history,
        visits=[_serialize_visit(v) for v in sorted_visits],
    )


@router.put("/{patient_id}", response_model=PatientDetailOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.query(AISummaryCache).filter(AISummaryCache.patient_id == patient_id).delete()
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(
        db,
        current_user.id,
        "UPDATE_PATIENT",
        patient_id=patient.id,
        detail=f"Updated demographic profile for {patient.mrn}",
    )
    return get_patient_detail(patient_id, db, current_user)


@router.post("/{patient_id}/allergies", response_model=AllergyOut, status_code=status.HTTP_201_CREATED)
def add_patient_allergy(
    patient_id: int,
    payload: AllergyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    allergy = Allergy(
        patient_id=patient_id,
        allergen=payload.allergen.strip(),
        reaction=payload.reaction.strip(),
        severity=payload.severity,
        status=payload.status,
        recorded_date=payload.recorded_date or datetime.now(timezone.utc).date(),
    )
    db.add(allergy)
    db.query(AISummaryCache).filter(AISummaryCache.patient_id == patient_id).delete()
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(allergy)
    log_audit(db, current_user.id, "ADD_ALLERGY", patient_id=patient_id, detail=f"Added allergy: {allergy.allergen}")
    return allergy


@router.post("/{patient_id}/history", response_model=MedicalHistoryOut, status_code=status.HTTP_201_CREATED)
def add_medical_history(
    patient_id: int,
    payload: MedicalHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    item = MedicalHistoryItem(
        patient_id=patient_id,
        condition_name=payload.condition_name.strip(),
        category=payload.category,
        onset_date=payload.onset_date,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(item)
    db.query(AISummaryCache).filter(AISummaryCache.patient_id == patient_id).delete()
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    log_audit(db, current_user.id, "ADD_MEDICAL_HISTORY", patient_id=patient_id, detail=f"Added history: {item.condition_name}")
    return item


@router.post("/{patient_id}/visits", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit_record(
    patient_id: int,
    payload: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor_id = payload.doctor_id
    if not doctor_id:
        if current_user.doctor_profile:
            doctor_id = current_user.doctor_profile.id
        else:
            first_doc = db.query(Doctor).first()
            if not first_doc:
                raise HTTPException(status_code=400, detail="No doctor profile available")
            doctor_id = first_doc.id

    visit_dt = payload.visit_date or datetime.now(timezone.utc)
    visit = Visit(
        patient_id=patient_id,
        doctor_id=doctor_id,
        visit_date=visit_dt,
        visit_type=payload.visit_type,
        chief_complaint=payload.chief_complaint.strip(),
        vitals_bp=payload.vitals_bp,
        vitals_hr=payload.vitals_hr,
        vitals_temp_c=payload.vitals_temp_c,
        vitals_spo2=payload.vitals_spo2,
        vitals_weight_kg=payload.vitals_weight_kg,
        treatment_plan=payload.treatment_plan,
        follow_up_date=payload.follow_up_date,
    )
    db.add(visit)
    db.flush()

    for s in payload.symptoms:
        db.add(
            Symptom(
                visit_id=visit.id,
                name=s.name.strip(),
                severity=s.severity,
                duration_days=s.duration_days,
                notes=s.notes,
            )
        )

    for d in payload.diagnoses:
        db.add(
            Diagnosis(
                visit_id=visit.id,
                condition_name=d.condition_name.strip(),
                icd10_code=d.icd10_code.strip() if d.icd10_code else None,
                status=d.status,
                notes=d.notes,
            )
        )

    for p in payload.prescriptions:
        med_id = p.medication_id
        if not med_id:
            if not p.medication_name:
                continue
            med = db.query(Medication).filter(Medication.name.ilike(p.medication_name.strip())).first()
            if not med:
                med = Medication(
                    name=p.medication_name.strip(),
                    generic_name=(p.generic_name or p.medication_name).strip(),
                    form=p.form or "Tablet",
                    strength=p.strength or "Standard",
                )
                db.add(med)
                db.flush()
            med_id = med.id

        db.add(
            Prescription(
                visit_id=visit.id,
                medication_id=med_id,
                dosage=p.dosage.strip(),
                frequency=p.frequency.strip(),
                duration_days=p.duration_days,
                instructions=p.instructions,
            )
        )

    for n in payload.clinical_notes:
        if n.content.strip():
            db.add(
                ClinicalNote(
                    visit_id=visit.id,
                    author_id=current_user.id,
                    note_type=n.note_type,
                    content=n.content.strip(),
                )
            )

    for t in payload.test_results:
        db.add(
            TestResult(
                visit_id=visit.id,
                test_name=t.test_name.strip(),
                value=t.value.strip(),
                unit=t.unit,
                reference_range=t.reference_range,
                flag=t.flag,
                result_date=t.result_date,
                remarks=t.remarks,
            )
        )

    db.query(AISummaryCache).filter(AISummaryCache.patient_id == patient_id).delete()
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db,
        current_user.id,
        "CREATE_VISIT_RECORD",
        patient_id=patient_id,
        detail=f"Added {visit.visit_type} visit (V-{visit.id}): {visit.chief_complaint}",
    )

    full_visit = (
        db.query(Visit)
        .options(
            joinedload(Visit.doctor).joinedload(Doctor.user),
            joinedload(Visit.symptoms),
            joinedload(Visit.diagnoses),
            joinedload(Visit.prescriptions).joinedload(Prescription.medication),
            joinedload(Visit.clinical_notes).joinedload(ClinicalNote.author),
            joinedload(Visit.test_results),
        )
        .filter(Visit.id == visit.id)
        .first()
    )
    return _serialize_visit(full_visit)


@router.put("/visits/{visit_id}", response_model=VisitOut)
def update_visit_record(
    visit_id: int,
    payload: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit record not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(visit, field, val)
    visit.updated_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db,
        current_user.id,
        "UPDATE_VISIT_RECORD",
        patient_id=visit.patient_id,
        detail=f"Updated Visit V-{visit.id}",
    )

    full_visit = (
        db.query(Visit)
        .options(
            joinedload(Visit.doctor).joinedload(Doctor.user),
            joinedload(Visit.symptoms),
            joinedload(Visit.diagnoses),
            joinedload(Visit.prescriptions).joinedload(Prescription.medication),
            joinedload(Visit.clinical_notes).joinedload(ClinicalNote.author),
            joinedload(Visit.test_results),
        )
        .filter(Visit.id == visit.id)
        .first()
    )
    return _serialize_visit(full_visit)
