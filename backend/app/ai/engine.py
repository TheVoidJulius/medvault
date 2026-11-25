from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
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
    Visit,
)
from app.schemas import (
    AIQueryResponse,
    AISummaryResponse,
    ChronologicalEvent,
    CitationRef,
    NoteExtractionResponse,
    RetrievedRecordCard,
    SummaryStatement,
)

CLINICAL_DISCLAIMER = (
    "CLINICAL DECISION SUPPORT NOTICE: This AI-assisted output is synthesized strictly from "
    "stored relational records. It is not an independent medical diagnosis or prescription order. "
    "Clinicians must verify every cited claim against the linked original source record."
)

STOPWORDS = {
    "what", "were", "this", "patient", "patients", "patient's", "previous", "show", "find",
    "has", "have", "had", "reported", "before", "during", "from", "the", "last", "all",
    "related", "to", "a", "an", "in", "of", "for", "and", "or", "with", "on", "at", "by",
    "is", "are", "was", "been", "any", "give", "me", "list", "summarise", "summarize",
    "tell", "about", "history", "record", "records", "visit", "visits", "mentioning",
    "consultations", "consultation", "particular", "condition", "similar",
}

SYNONYM_MAP = {
    "headache": ["headache", "migraine", "cephalalgia", "throbbing", "photophobia", "aura"],
    "headaches": ["headache", "migraine", "cephalalgia", "throbbing", "photophobia", "aura"],
    "migraine": ["migraine", "headache", "photophobia", "aura", "sumatriptan"],
    "sugar": ["diabetes", "glucose", "hba1c", "hyperglycemia", "metformin", "glycemic"],
    "diabetes": ["diabetes", "glucose", "hba1c", "metformin", "glimepiride", "neuropathy"],
    "diabetic": ["diabetes", "glucose", "hba1c", "metformin", "glimepiride"],
    "bp": ["hypertension", "blood pressure", "amlodipine", "telmisartan", "losartan", "systolic"],
    "hypertension": ["hypertension", "blood pressure", "amlodipine", "telmisartan", "losartan"],
    "breathing": ["asthma", "dyspnea", "wheezing", "shortness of breath", "salbutamol", "budesonide", "spo2"],
    "asthma": ["asthma", "wheezing", "dyspnea", "bronchospasm", "salbutamol", "budesonide", "fev1"],
    "breath": ["dyspnea", "wheezing", "shortness of breath", "asthma"],
    "cough": ["cough", "bronchitis", "asthma", "wheezing", "sputum"],
    "chest": ["chest pain", "angina", "palpitations", "dyspnea", "ecg", "troponin"],
    "heart": ["cardiac", "angina", "hypertension", "palpitations", "ecg", "lipid", "atorvastatin"],
    "joint": ["arthralgia", "arthritis", "rheumatoid", "swelling", "stiffness", "methotrexate", "crp", "esr"],
    "stomach": ["epigastric", "gastritis", "gerd", "nausea", "acid", "pantoprazole", "abdominal"],
    "thyroid": ["hypothyroidism", "tsh", "levothyroxine", "fatigue", "weight"],
    "anemia": ["anemia", "hemoglobin", "ferritin", "iron", "fatigue", "pallor"],
    "kidney": ["renal", "creatinine", "egfr", "urea", "proteinuria"],
    "fever": ["fever", "pyrexia", "chills", "infection"],
}


def load_full_patient(db: Session, patient_id: int) -> Optional[Patient]:
    return (
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


def compute_records_hash(patient: Patient) -> str:
    parts = [
        f"P:{patient.id}:{patient.updated_at}",
        f"A:{len(patient.allergies)}:" + ",".join(f"{a.id}-{a.status}" for a in sorted(patient.allergies, key=lambda x: x.id)),
        f"H:{len(patient.medical_history)}:" + ",".join(f"{h.id}-{h.status}" for h in sorted(patient.medical_history, key=lambda x: x.id)),
    ]
    for v in sorted(patient.visits, key=lambda x: x.id):
        parts.append(
            f"V:{v.id}:{v.visit_date.isoformat()}:{len(v.symptoms)}:{len(v.diagnoses)}:"
            f"{len(v.prescriptions)}:{len(v.clinical_notes)}:{len(v.test_results)}"
        )
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def build_citation_index(patient: Patient) -> Dict[str, CitationRef]:
    index: Dict[str, CitationRef] = {}

    for a in patient.allergies:
        tag = f"ALG-{a.id}"
        index[tag] = CitationRef(
            tag=tag,
            record_type="Allergy",
            record_id=a.id,
            visit_id=None,
            visit_date=a.recorded_date.isoformat() if a.recorded_date else None,
            label=f"Allergy: {a.allergen} ({a.severity})",
            snippet=f"{a.allergen} -> {a.reaction} [Severity: {a.severity}, Status: {a.status}]",
        )

    for h in patient.medical_history:
        tag = f"HX-{h.id}"
        index[tag] = CitationRef(
            tag=tag,
            record_type="MedicalHistory",
            record_id=h.id,
            visit_id=None,
            visit_date=h.onset_date.isoformat() if h.onset_date else None,
            label=f"{h.category}: {h.condition_name}",
            snippet=f"{h.condition_name} ({h.category}, Status: {h.status}) {h.notes or ''}".strip(),
        )

    for v in patient.visits:
        vdate = v.visit_date.strftime("%Y-%m-%d")
        doc_name = v.doctor.user.full_name if v.doctor and v.doctor.user else "Attending Physician"
        vtag = f"V-{v.id}"
        index[vtag] = CitationRef(
            tag=vtag,
            record_type="Visit",
            record_id=v.id,
            visit_id=v.id,
            visit_date=vdate,
            label=f"Visit ({vdate}) — {v.visit_type}",
            snippet=f"{v.chief_complaint} | Plan: {v.treatment_plan or 'N/A'} ({doc_name})",
        )

        for s in v.symptoms:
            stag = f"SYM-{s.id}"
            index[stag] = CitationRef(
                tag=stag,
                record_type="Symptom",
                record_id=s.id,
                visit_id=v.id,
                visit_date=vdate,
                label=f"Symptom: {s.name} ({vdate})",
                snippet=f"{s.name} — Severity: {s.severity}, Duration: {s.duration_days or '?'} days. {s.notes or ''}".strip(),
            )

        for d in v.diagnoses:
            dtag = f"DX-{d.id}"
            code_str = f" [{d.icd10_code}]" if d.icd10_code else ""
            index[dtag] = CitationRef(
                tag=dtag,
                record_type="Diagnosis",
                record_id=d.id,
                visit_id=v.id,
                visit_date=vdate,
                label=f"Diagnosis: {d.condition_name}{code_str} ({vdate})",
                snippet=f"{d.condition_name}{code_str} — Status: {d.status}. {d.notes or ''}".strip(),
            )

        for p in v.prescriptions:
            ptag = f"RX-{p.id}"
            med_name = p.medication.name if p.medication else "Medication"
            strength = p.medication.strength if p.medication else ""
            index[ptag] = CitationRef(
                tag=ptag,
                record_type="Prescription",
                record_id=p.id,
                visit_id=v.id,
                visit_date=vdate,
                label=f"Rx: {med_name} {strength} ({vdate})",
                snippet=f"{med_name} {strength} — {p.dosage}, {p.frequency} for {p.duration_days or '?'} days. {p.instructions or ''}".strip(),
            )

        for n in v.clinical_notes:
            ntag = f"NOTE-{n.id}"
            index[ntag] = CitationRef(
                tag=ntag,
                record_type="ClinicalNote",
                record_id=n.id,
                visit_id=v.id,
                visit_date=vdate,
                label=f"{n.note_type} Note ({vdate})",
                snippet=n.content[:260] + ("..." if len(n.content) > 260 else ""),
            )

        for t in v.test_results:
            ttag = f"LAB-{t.id}"
            index[ttag] = CitationRef(
                tag=ttag,
                record_type="TestResult",
                record_id=t.id,
                visit_id=v.id,
                visit_date=vdate,
                label=f"Lab: {t.test_name} ({vdate})",
                snippet=f"{t.test_name}: {t.value} {t.unit or ''} (Ref: {t.reference_range or 'N/A'}) — Flag: {t.flag}",
            )

    return index


def validate_statements(
    statements: List[SummaryStatement], citation_index: Dict[str, CitationRef]
) -> Tuple[List[SummaryStatement], int, int]:
    validated: List[SummaryStatement] = []
    total_citations = 0
    verified_citations = 0
    for stmt in statements:
        valid_cits = [c for c in stmt.citations if c in citation_index]
        total_citations += len(stmt.citations)
        verified_citations += len(valid_cits)
        validated.append(
            SummaryStatement(
                text=stmt.text,
                citations=valid_cits,
                severity_or_status=stmt.severity_or_status,
            )
        )
    return validated, total_citations, verified_citations


def generate_patient_summary(
    db: Session, patient_id: int, force_refresh: bool = False
) -> AISummaryResponse:
    patient = load_full_patient(db, patient_id)
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")

    rec_hash = compute_records_hash(patient)
    if not force_refresh:
        cached = (
            db.query(AISummaryCache)
            .filter(
                AISummaryCache.patient_id == patient_id,
                AISummaryCache.records_hash == rec_hash,
            )
            .order_by(AISummaryCache.created_at.desc())
            .first()
        )
        if cached:
            data = json.loads(cached.summary_json)
            data["cached"] = True
            return AISummaryResponse(**data)

    citation_index = build_citation_index(patient)
    today = date.today()
    age = today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )

    sorted_visits = sorted(patient.visits, key=lambda v: v.visit_date, reverse=True)
    chronological_visits = sorted(patient.visits, key=lambda v: v.visit_date)

    # 1. Executive Overview
    executive_overview: List[SummaryStatement] = []
    if not sorted_visits:
        executive_overview.append(
            SummaryStatement(
                text=(
                    f"{patient.first_name} {patient.last_name} ({age}y, {patient.sex}, Blood Group: "
                    f"{patient.blood_group or 'Not recorded'}) is registered in the database, "
                    "but has no clinical visits recorded yet."
                ),
                citations=[],
                severity_or_status="No Clinical Visits",
            )
        )
    else:
        first_v = chronological_visits[0]
        latest_v = sorted_visits[0]
        executive_overview.append(
            SummaryStatement(
                text=(
                    f"{age}-year-old {patient.sex.lower()} patient with {len(sorted_visits)} documented clinical "
                    f"encounters spanning from {first_v.visit_date.strftime('%b %d, %Y')} to "
                    f"{latest_v.visit_date.strftime('%b %d, %Y')}."
                ),
                citations=[f"V-{first_v.id}", f"V-{latest_v.id}"] if first_v.id != latest_v.id else [f"V-{latest_v.id}"],
                severity_or_status="Active Longitudinal Record",
            )
        )
        executive_overview.append(
            SummaryStatement(
                text=(
                    f"Most recent encounter ({latest_v.visit_type} on {latest_v.visit_date.strftime('%b %d, %Y')}) "
                    f"presented with '{latest_v.chief_complaint}'. Plan: {latest_v.treatment_plan or 'Standard follow-up'}."
                ),
                citations=[f"V-{latest_v.id}"] + [f"NOTE-{n.id}" for n in latest_v.clinical_notes[:1]],
                severity_or_status=latest_v.visit_type,
            )
        )

    if patient.medical_history:
        hx_cits = [f"HX-{h.id}" for h in patient.medical_history]
        hx_names = [f"{h.condition_name} ({h.category}: {h.status})" for h in patient.medical_history]
        executive_overview.append(
            SummaryStatement(
                text=f"Baseline Medical History: {'; '.join(hx_names)}.",
                citations=hx_cits,
                severity_or_status="Baseline History",
            )
        )

    # 2. Recurring Symptoms Analysis
    symptom_groups: Dict[str, List[Tuple[Symptom, Visit]]] = defaultdict(list)
    for v in chronological_visits:
        for s in v.symptoms:
            norm = s.name.strip().lower()
            symptom_groups[norm].append((s, v))

    recurring_symptoms: List[SummaryStatement] = []
    sorted_sym_groups = sorted(symptom_groups.items(), key=lambda item: len(item[1]), reverse=True)
    for norm_name, occurrences in sorted_sym_groups:
        display_name = occurrences[0][0].name
        cits = [f"SYM-{s.id}" for s, _ in occurrences]
        dates = [v.visit_date.strftime("%b %Y") for _, v in occurrences]
        severities = [s.severity for s, _ in occurrences]
        if len(occurrences) >= 2:
            recurring_symptoms.append(
                SummaryStatement(
                    text=(
                        f"Recurring '{display_name}' reported across {len(occurrences)} visits "
                        f"({', '.join(dates)}); severity pattern: {' -> '.join(severities)}."
                    ),
                    citations=cits,
                    severity_or_status="Recurring Pattern",
                )
            )
        else:
            s_obj, v_obj = occurrences[0]
            dur_str = f" for {s_obj.duration_days} days" if s_obj.duration_days else ""
            recurring_symptoms.append(
                SummaryStatement(
                    text=(
                        f"Single episode of '{display_name}' ({s_obj.severity} severity{dur_str}) "
                        f"recorded on {v_obj.visit_date.strftime('%b %d, %Y')}."
                    ),
                    citations=cits,
                    severity_or_status=s_obj.severity,
                )
            )

    if not recurring_symptoms:
        recurring_symptoms.append(
            SummaryStatement(
                text="No structured symptoms have been recorded for this patient.",
                citations=[],
                severity_or_status="Unavailable",
            )
        )

    # 3. Diagnoses (Active, Confirmed, Provisional, Ruled-out)
    dx_groups: Dict[str, List[Tuple[Diagnosis, Visit]]] = defaultdict(list)
    for v in chronological_visits:
        for d in v.diagnoses:
            dx_groups[d.condition_name.strip().lower()].append((d, v))

    active_and_past_diagnoses: List[SummaryStatement] = []
    for _, dx_list in dx_groups.items():
        latest_dx, latest_v = dx_list[-1]
        first_dx, first_v = dx_list[0]
        cits = [f"DX-{d.id}" for d, _ in dx_list]
        code_txt = f" (ICD-10: {latest_dx.icd10_code})" if latest_dx.icd10_code else ""
        statuses = [d.status for d, _ in dx_list]
        if len(dx_list) > 1:
            active_and_past_diagnoses.append(
                SummaryStatement(
                    text=(
                        f"{latest_dx.condition_name}{code_txt} — Current status: {latest_dx.status}. "
                        f"Documented in {len(dx_list)} encounters from {first_v.visit_date.strftime('%b %Y')} "
                        f"to {latest_v.visit_date.strftime('%b %Y')} (status progression: {' -> '.join(statuses)})."
                    ),
                    citations=cits,
                    severity_or_status=latest_dx.status,
                )
            )
        else:
            active_and_past_diagnoses.append(
                SummaryStatement(
                    text=(
                        f"{latest_dx.condition_name}{code_txt} — {latest_dx.status} on "
                        f"{latest_v.visit_date.strftime('%b %d, %Y')}. {latest_dx.notes or ''}".strip()
                    ),
                    citations=cits,
                    severity_or_status=latest_dx.status,
                )
            )

    if not active_and_past_diagnoses:
        active_and_past_diagnoses.append(
            SummaryStatement(
                text="No clinical diagnoses recorded in visit history.",
                citations=[],
                severity_or_status="Unavailable",
            )
        )

    # 4. Medication & Prescription History
    med_groups: Dict[str, List[Tuple[Prescription, Visit]]] = defaultdict(list)
    for v in chronological_visits:
        for p in v.prescriptions:
            med_label = f"{p.medication.name} {p.medication.strength}" if p.medication else f"Med#{p.medication_id}"
            med_groups[med_label].append((p, v))

    medication_history: List[SummaryStatement] = []
    for med_label, rx_list in med_groups.items():
        latest_rx, latest_v = rx_list[-1]
        cits = [f"RX-{p.id}" for p, _ in rx_list]
        generic = f" ({latest_rx.medication.generic_name})" if latest_rx.medication else ""
        if len(rx_list) > 1:
            dosages = [f"{p.dosage} {p.frequency} ({v.visit_date.strftime('%b %Y')})" for p, v in rx_list]
            medication_history.append(
                SummaryStatement(
                    text=(
                        f"{med_label}{generic} — Prescribed across {len(rx_list)} visits: "
                        f"{'; '.join(dosages)}. Latest instructions: {latest_rx.instructions or 'Take as directed'}."
                    ),
                    citations=cits,
                    severity_or_status="Repeat Prescription",
                )
            )
        else:
            medication_history.append(
                SummaryStatement(
                    text=(
                        f"{med_label}{generic} — {latest_rx.dosage}, {latest_rx.frequency} "
                        f"for {latest_rx.duration_days or 'ongoing'} days (Prescribed {latest_v.visit_date.strftime('%b %d, %Y')}). "
                        f"{latest_rx.instructions or ''}".strip()
                    ),
                    citations=cits,
                    severity_or_status="Prescribed",
                )
            )

    if not medication_history:
        medication_history.append(
            SummaryStatement(
                text="No medications or prescriptions are recorded for this patient.",
                citations=[],
                severity_or_status="Unavailable",
            )
        )

    # 5. Allergies & Safety Alerts
    allergies_and_alerts: List[SummaryStatement] = []
    if patient.allergies:
        for a in patient.allergies:
            allergies_and_alerts.append(
                SummaryStatement(
                    text=f"ALLERGY ALERT: {a.allergen} causes {a.reaction} (Severity: {a.severity}, Status: {a.status}).",
                    citations=[f"ALG-{a.id}"],
                    severity_or_status=a.severity,
                )
            )
    else:
        allergies_and_alerts.append(
            SummaryStatement(
                text="No known drug or environmental allergies documented in patient profile.",
                citations=[],
                severity_or_status="None Recorded",
            )
        )

    # 6. Abnormal Test Results & Longitudinal Lab Trends
    lab_groups: Dict[str, List[Tuple[TestResult, Visit]]] = defaultdict(list)
    for v in chronological_visits:
        for t in v.test_results:
            lab_groups[t.test_name.strip()].append((t, v))

    abnormal_test_trends: List[SummaryStatement] = []
    for test_name, t_list in lab_groups.items():
        cits = [f"LAB-{t.id}" for t, _ in t_list]
        abnormal_any = any(t.flag != "Normal" for t, _ in t_list)
        if len(t_list) > 1:
            trend_vals = [f"{t.value} {t.unit or ''} [{t.flag}, {t.result_date.strftime('%b %Y')}]" for t, _ in t_list]
            latest_t = t_list[-1][0]
            abnormal_test_trends.append(
                SummaryStatement(
                    text=(
                        f"{test_name} longitudinal trend ({len(t_list)} measurements): "
                        f"{' -> '.join(trend_vals)}. Reference range: {latest_t.reference_range or 'Standard'}."
                    ),
                    citations=cits,
                    severity_or_status=latest_t.flag,
                )
            )
        elif abnormal_any:
            t_obj, _ = t_list[0]
            abnormal_test_trends.append(
                SummaryStatement(
                    text=(
                        f"Abnormal {test_name}: {t_obj.value} {t_obj.unit or ''} "
                        f"(Flag: {t_obj.flag}, Ref: {t_obj.reference_range or 'N/A'}) on {t_obj.result_date.isoformat()}. "
                        f"{t_obj.remarks or ''}".strip()
                    ),
                    citations=cits,
                    severity_or_status=t_obj.flag,
                )
            )

    if not abnormal_test_trends:
        abnormal_test_trends.append(
            SummaryStatement(
                text="No abnormal laboratory or diagnostic test trends flagged.",
                citations=[],
                severity_or_status="Normal / Unavailable",
            )
        )

    # 7. Data Gaps, Diagnostic Revisions & Outdated Record Checks
    data_gaps_and_conflicts: List[SummaryStatement] = []
    if not patient.blood_group:
        data_gaps_and_conflicts.append(
            SummaryStatement(
                text="Missing Data: Patient blood group is not recorded in demographic profile.",
                citations=[],
                severity_or_status="Missing Data",
            )
        )
    if not patient.emergency_contact_phone:
        data_gaps_and_conflicts.append(
            SummaryStatement(
                text="Missing Data: Emergency contact telephone number is unavailable.",
                citations=[],
                severity_or_status="Missing Data",
            )
        )

    # Check diagnostic revisions (e.g., Provisional later Ruled-out or changed)
    for _, dx_list in dx_groups.items():
        statuses = [d.status for d, _ in dx_list]
        if "Ruled-out" in statuses or ("Provisional" in statuses and "Confirmed" in statuses):
            cits = [f"DX-{d.id}" for d, _ in dx_list]
            cond = dx_list[-1][0].condition_name
            data_gaps_and_conflicts.append(
                SummaryStatement(
                    text=(
                        f"Diagnostic Status Evolution for '{cond}': status changed across visits "
                        f"({' -> '.join(statuses)}). Verify current clinical working diagnosis."
                    ),
                    citations=cits,
                    severity_or_status="Diagnostic Revision",
                )
            )

    # Check if latest visit is older than 180 days
    if sorted_visits:
        latest_v = sorted_visits[0]
        days_since = (datetime.now(timezone.utc) - latest_v.visit_date.replace(tzinfo=timezone.utc)).days
        if days_since > 180:
            data_gaps_and_conflicts.append(
                SummaryStatement(
                    text=(
                        f"Outdated Record Notice: Most recent clinical visit was {days_since} days ago "
                        f"({latest_v.visit_date.strftime('%Y-%m-%d')}). Current medications and vitals may require re-verification."
                    ),
                    citations=[f"V-{latest_v.id}"],
                    severity_or_status="Outdated Notice",
                )
            )

    if not data_gaps_and_conflicts:
        data_gaps_and_conflicts.append(
            SummaryStatement(
                text="All core demographic fields, allergy checks, and recent encounter records are complete with no conflicting diagnostic statuses detected.",
                citations=[],
                severity_or_status="Complete",
            )
        )

    # 8. Chronological Timeline
    chronological_timeline: List[ChronologicalEvent] = []
    for v in sorted_visits:
        doc_name = v.doctor.user.full_name if v.doctor and v.doctor.user else "Attending Doctor"
        note_snippet = v.clinical_notes[0].content if v.clinical_notes else (v.treatment_plan or "No clinical note text.")
        if len(note_snippet) > 220:
            note_snippet = note_snippet[:217] + "..."
        chronological_timeline.append(
            ChronologicalEvent(
                visit_id=v.id,
                visit_tag=f"V-{v.id}",
                visit_date=v.visit_date.strftime("%Y-%m-%d"),
                visit_type=v.visit_type,
                doctor_name=doc_name,
                chief_complaint=v.chief_complaint,
                key_findings=note_snippet,
                diagnoses=[f"{d.condition_name} ({d.status}) [DX-{d.id}]" for d in v.diagnoses],
                prescriptions=[
                    f"{p.medication.name} {p.medication.strength} ({p.dosage} {p.frequency}) [RX-{p.id}]"
                    for p in v.prescriptions
                    if p.medication
                ],
                abnormal_labs=[
                    f"{t.test_name}: {t.value} {t.unit or ''} ({t.flag}) [LAB-{t.id}]"
                    for t in v.test_results
                    if t.flag != "Normal"
                ],
            )
        )

    # Validate every statement against the citation index
    total_cits = 0
    verified_cits = 0
    for section_list in [
        executive_overview,
        recurring_symptoms,
        active_and_past_diagnoses,
        medication_history,
        allergies_and_alerts,
        abnormal_test_trends,
        data_gaps_and_conflicts,
    ]:
        _, t_c, v_c = validate_statements(section_list, citation_index)
        total_cits += t_c
        verified_cits += v_c

    provider_label = "Grounded Relational Synthesis Engine (SQL + Citation Validator)"
    if settings.GEMINI_API_KEY and (patient.is_synthetic or settings.ALLOW_EXTERNAL_PHI):
        llm_overview = _try_gemini_executive_enhancement(patient, executive_overview, citation_index)
        if llm_overview:
            executive_overview = llm_overview
            provider_label = f"Google Gemini ({settings.GEMINI_MODEL}) + SQL Citation Validator"

    response = AISummaryResponse(
        patient_id=patient.id,
        patient_mrn=patient.mrn,
        patient_name=f"{patient.first_name} {patient.last_name}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        provider_used=provider_label,
        cached=False,
        disclaimer=CLINICAL_DISCLAIMER,
        executive_overview=executive_overview,
        recurring_symptoms=recurring_symptoms,
        active_and_past_diagnoses=active_and_past_diagnoses,
        medication_history=medication_history,
        allergies_and_alerts=allergies_and_alerts,
        abnormal_test_trends=abnormal_test_trends,
        data_gaps_and_conflicts=data_gaps_and_conflicts,
        chronological_timeline=chronological_timeline,
        citation_index=citation_index,
        validation_stats={
            "total_citations_emitted": total_cits,
            "verified_citations": verified_cits,
            "unverified_citations_dropped": total_cits - verified_cits,
            "grounding_score": 1.0 if total_cits == verified_cits else round(verified_cits / max(total_cits, 1), 2),
            "source_records_indexed": len(citation_index),
        },
    )

    cache_row = AISummaryCache(
        patient_id=patient.id,
        summary_json=response.model_dump_json(),
        records_hash=rec_hash,
        provider_used=provider_label,
    )
    db.add(cache_row)
    db.commit()

    return response


def _try_gemini_executive_enhancement(
    patient: Patient,
    fallback_overview: List[SummaryStatement],
    citation_index: Dict[str, CitationRef],
) -> Optional[List[SummaryStatement]]:
    try:
        context_lines = [
            f"[{tag}] {ref.label}: {ref.snippet}" for tag, ref in list(citation_index.items())[:40]
        ]
        prompt = (
            "You are a clinical medical record summarizer. Use ONLY the tagged records below. "
            "Never invent facts. Return JSON: {\"statements\": [{\"text\": \"...\", \"citations\": [\"V-1\"]}]}.\n\n"
            + "\n".join(context_lines)
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            body = resp.json()
            raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            stmts = [
                SummaryStatement(
                    text=item["text"],
                    citations=[c for c in item.get("citations", []) if c in citation_index],
                    severity_or_status="AI Synthesized",
                )
                for item in parsed.get("statements", [])
                if item.get("text")
            ]
            return stmts if stmts else None
    except Exception:
        return None


def parse_natural_language_query(query: str) -> Dict[str, Any]:
    q_lower = query.lower().strip()
    now = datetime.now(timezone.utc)
    date_from: Optional[datetime] = None

    # Parse relative timeframes
    years_match = re.search(r"last\s+(\d+|one|two|three|five)\s+years?", q_lower)
    months_match = re.search(r"last\s+(\d+|three|six|twelve)\s+months?", q_lower)
    word_to_num = {"one": 1, "two": 2, "three": 3, "five": 5, "six": 6, "twelve": 12}

    if years_match:
        val = years_match.group(1)
        num_years = word_to_num.get(val, int(val) if val.isdigit() else 2)
        date_from = now - timedelta(days=365 * num_years)
    elif "last year" in q_lower or "past year" in q_lower:
        date_from = now - timedelta(days=365)
    elif months_match:
        val = months_match.group(1)
        num_months = word_to_num.get(val, int(val) if val.isdigit() else 6)
        date_from = now - timedelta(days=30 * num_months)
    elif "2024" in q_lower:
        date_from = datetime(2024, 1, 1, tzinfo=timezone.utc)
    elif "2025" in q_lower:
        date_from = datetime(2025, 1, 1, tzinfo=timezone.utc)
    elif "2026" in q_lower:
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Detect target record types
    target_types: List[str] = []
    if any(w in q_lower for w in ["diagnos", "condition", "disease", "illness"]):
        target_types.append("Diagnosis")
    if any(w in q_lower for w in ["medicat", "prescri", "drug", "pill", "tablet", "dose", "rx", "treatment"]):
        target_types.append("Prescription")
    if any(w in q_lower for w in ["symptom", "complain", "pain", "ache", "headache", "fever", "cough", "wheez", "recurring"]):
        target_types.append("Symptom")
    if any(w in q_lower for w in ["test", "lab", "result", "blood", "hba1c", "bp", "glucose", "level", "panel", "xray", "ecg"]):
        target_types.append("TestResult")
    if any(w in q_lower for w in ["allerg", "reaction"]):
        target_types.append("Allergy")
    if any(w in q_lower for w in ["note", "consultation", "visit", "encounter", "summary", "history"]):
        target_types.extend(["Visit", "ClinicalNote"])

    # Tokenize keywords & expand clinical synonyms
    raw_tokens = re.findall(r"[a-z0-9]+", q_lower)
    keywords = [t for t in raw_tokens if t not in STOPWORDS and len(t) > 2]
    expanded_terms = set(keywords)
    for kw in list(keywords):
        if kw in SYNONYM_MAP:
            expanded_terms.update(SYNONYM_MAP[kw])
        for key, syns in SYNONYM_MAP.items():
            if kw in syns:
                expanded_terms.add(key)
                expanded_terms.update(syns)

    # Remove generic schema intent words from content search terms if specific medical terms exist
    intent_words = {
        "diagnoses", "diagnosis", "medications", "medication", "prescribed", "prescriptions",
        "prescription", "symptoms", "symptom", "tests", "results", "labs", "allergies",
        "allergy", "years", "year", "months", "month", "medical", "clinical", "notes",
    }
    clinical_terms = [t for t in expanded_terms if t not in intent_words]

    is_recurring_query = any(w in q_lower for w in ["recurring", "repeated", "similar", "again", "before", "multiple", "frequent"])

    return {
        "date_from": date_from.strftime("%Y-%m-%d") if date_from else None,
        "target_record_types": list(dict.fromkeys(target_types)) or ["All"],
        "extracted_keywords": keywords,
        "expanded_clinical_terms": sorted(clinical_terms),
        "is_recurring_check": is_recurring_query,
    }


def answer_natural_language_query(
    db: Session, query: str, patient_id: Optional[int] = None
) -> AIQueryResponse:
    parsed = parse_natural_language_query(query)
    date_from_str = parsed["date_from"]
    date_from_dt = (
        datetime.strptime(date_from_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if date_from_str
        else None
    )
    target_types = parsed["target_record_types"]
    clinical_terms = parsed["expanded_clinical_terms"]
    is_recurring_check = parsed["is_recurring_check"]

    if patient_id is not None:
        p = load_full_patient(db, patient_id)
        patients = [p] if p else []
    else:
        patients = (
            db.query(Patient)
            .options(
                joinedload(Patient.allergies),
                joinedload(Patient.medical_history),
                joinedload(Patient.visits).joinedload(Visit.doctor).joinedload(Doctor.user),
                joinedload(Patient.visits).joinedload(Visit.symptoms),
                joinedload(Patient.visits).joinedload(Visit.diagnoses),
                joinedload(Patient.visits).joinedload(Visit.prescriptions).joinedload(Prescription.medication),
                joinedload(Patient.visits).joinedload(Visit.clinical_notes),
                joinedload(Patient.visits).joinedload(Visit.test_results),
            )
            .filter(Patient.is_active == True)
            .all()
        )

    citation_index: Dict[str, CitationRef] = {}
    candidate_cards: List[RetrievedRecordCard] = []

    def score_text(text_blob: str, record_type: str) -> Tuple[float, List[str]]:
        blob_lower = text_blob.lower()
        matched: List[str] = []
        score = 0.0

        if "All" in target_types or record_type in target_types:
            score += 2.0

        if clinical_terms:
            for term in clinical_terms:
                if term in blob_lower:
                    matched.append(term)
                    score += 4.5
            if not matched:
                return 0.0, []
        else:
            # No specific clinical condition mentioned (e.g., "What were this patient's previous diagnoses?")
            if "All" not in target_types and record_type not in target_types:
                return 0.0, []
            score += 3.0

        return score, list(dict.fromkeys(matched))

    for pat in patients:
        pat_name = f"{pat.first_name} {pat.last_name}"
        pat_cits = build_citation_index(pat)
        citation_index.update(pat_cits)

        for a in pat.allergies:
            tag = f"ALG-{a.id}"
            blob = f"{a.allergen} {a.reaction} {a.severity} {a.status}"
            sc, matched = score_text(blob, "Allergy")
            if sc > 0:
                candidate_cards.append(
                    RetrievedRecordCard(
                        citation_tag=tag,
                        record_type="Allergy",
                        record_id=a.id,
                        visit_id=None,
                        patient_id=pat.id,
                        patient_name=pat_name,
                        patient_mrn=pat.mrn,
                        visit_date=a.recorded_date.isoformat() if a.recorded_date else None,
                        doctor_name=None,
                        title=f"Allergy: {a.allergen} ({a.severity})",
                        details=f"Reaction: {a.reaction} | Status: {a.status}",
                        relevance_score=round(sc, 2),
                        matched_terms=matched,
                    )
                )

        for v in pat.visits:
            v_dt = v.visit_date if v.visit_date.tzinfo else v.visit_date.replace(tzinfo=timezone.utc)
            if date_from_dt and v_dt < date_from_dt:
                continue

            vdate = v.visit_date.strftime("%Y-%m-%d")
            doc_name = v.doctor.user.full_name if v.doctor and v.doctor.user else "Attending Physician"

            # Check Symptoms
            for s in v.symptoms:
                tag = f"SYM-{s.id}"
                blob = f"{s.name} {s.severity} {s.notes or ''} {v.chief_complaint}"
                sc, matched = score_text(blob, "Symptom")
                if sc > 0:
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="Symptom",
                            record_id=s.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"Symptom: {s.name} ({s.severity})",
                            details=f"Duration: {s.duration_days or 'N/A'} days | Visit Complaint: {v.chief_complaint}. {s.notes or ''}".strip(),
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

            # Check Diagnoses
            for d in v.diagnoses:
                tag = f"DX-{d.id}"
                blob = f"{d.condition_name} {d.icd10_code or ''} {d.status} {d.notes or ''}"
                sc, matched = score_text(blob, "Diagnosis")
                if sc > 0:
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="Diagnosis",
                            record_id=d.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"Diagnosis: {d.condition_name} [{d.icd10_code or 'No ICD'}]",
                            details=f"Status: {d.status} | Notes: {d.notes or 'Standard clinical diagnosis'}",
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

            # Check Prescriptions
            for p in v.prescriptions:
                tag = f"RX-{p.id}"
                med_str = f"{p.medication.name} {p.medication.generic_name} {p.medication.strength} {p.medication.drug_class or ''}" if p.medication else ""
                blob = f"{med_str} {p.dosage} {p.frequency} {p.instructions or ''} {v.chief_complaint}"
                sc, matched = score_text(blob, "Prescription")
                if sc > 0:
                    med_title = f"{p.medication.name} {p.medication.strength}" if p.medication else "Medication"
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="Prescription",
                            record_id=p.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"Prescription: {med_title}",
                            details=f"Sig: {p.dosage}, {p.frequency} for {p.duration_days or 'ongoing'} days. {p.instructions or ''}".strip(),
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

            # Check Lab Results
            for t in v.test_results:
                tag = f"LAB-{t.id}"
                blob = f"{t.test_name} {t.value} {t.unit or ''} {t.flag} {t.remarks or ''}"
                sc, matched = score_text(blob, "TestResult")
                if sc > 0:
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="TestResult",
                            record_id=t.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"Lab Result: {t.test_name} = {t.value} {t.unit or ''} ({t.flag})",
                            details=f"Ref Range: {t.reference_range or 'N/A'} | Date: {t.result_date.isoformat()}. {t.remarks or ''}".strip(),
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

            # Check Clinical Notes & Visits
            for n in v.clinical_notes:
                tag = f"NOTE-{n.id}"
                blob = f"{n.note_type} {n.content} {v.chief_complaint} {v.treatment_plan or ''}"
                sc, matched = score_text(blob, "ClinicalNote")
                if sc > 0:
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="ClinicalNote",
                            record_id=n.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"{n.note_type} Note — {v.chief_complaint}",
                            details=n.content,
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

            if "Visit" in target_types or (not clinical_terms and "All" in target_types):
                tag = f"V-{v.id}"
                blob = f"{v.visit_type} {v.chief_complaint} {v.treatment_plan or ''}"
                sc, matched = score_text(blob, "Visit")
                if sc > 0:
                    candidate_cards.append(
                        RetrievedRecordCard(
                            citation_tag=tag,
                            record_type="Visit",
                            record_id=v.id,
                            visit_id=v.id,
                            patient_id=pat.id,
                            patient_name=pat_name,
                            patient_mrn=pat.mrn,
                            visit_date=vdate,
                            doctor_name=doc_name,
                            title=f"{v.visit_type} Visit — {v.chief_complaint}",
                            details=f"Plan: {v.treatment_plan or 'Routine care'} | Vitals BP: {v.vitals_bp or 'N/A'}, HR: {v.vitals_hr or 'N/A'}",
                            relevance_score=round(sc, 2),
                            matched_terms=matched,
                        )
                    )

    # Sort by relevance score desc, then visit_date desc
    candidate_cards.sort(
        key=lambda c: (c.relevance_score, c.visit_date or "0000-00-00"),
        reverse=True,
    )

    top_cards = candidate_cards[:25]
    answer_statements: List[SummaryStatement] = []

    if not top_cards:
        direct_summary = (
            "No matching clinical records were found in the database for this query. "
            "The AI module does not extrapolate or invent clinical facts when source records are unavailable."
        )
        answer_statements.append(
            SummaryStatement(
                text=direct_summary,
                citations=[],
                severity_or_status="No Source Records Found",
            )
        )
    else:
        by_type: Dict[str, List[RetrievedRecordCard]] = defaultdict(list)
        for c in top_cards:
            by_type[c.record_type].append(c)

        direct_summary = (
            f"Retrieved {len(candidate_cards)} grounded relational record(s) matching your query "
            f"(displaying top {len(top_cards)} ranked by clinical relevance and date)."
        )

        if is_recurring_check:
            sym_counts = Counter(c.title for c in top_cards if c.record_type in ("Symptom", "Diagnosis", "ClinicalNote"))
            repeated = [(title, cnt) for title, cnt in sym_counts.items() if cnt >= 2]
            if repeated:
                rep_cits = [c.citation_tag for c in top_cards[:6]]
                answer_statements.append(
                    SummaryStatement(
                        text=(
                            f"Recurring Pattern Confirmed: Found {len(top_cards)} matching records across multiple encounters. "
                            f"Repeated entries include: {', '.join(f'{t} ({cnt}x)' for t, cnt in repeated[:4])}."
                        ),
                        citations=rep_cits,
                        severity_or_status="Recurring Pattern Confirmed",
                    )
                )

        for rtype, cards in by_type.items():
            cits = [c.citation_tag for c in cards[:8]]
            items_preview = [
                f"{c.title.replace(rtype + ': ', '')} ({c.visit_date or 'Recorded'}) [{c.citation_tag}]"
                for c in cards[:6]
            ]
            answer_statements.append(
                SummaryStatement(
                    text=f"{rtype} Records ({len(cards)} matched): " + "; ".join(items_preview) + ".",
                    citations=cits,
                    severity_or_status=f"{len(cards)} {rtype}(s)",
                )
            )

    used_citation_index = {
        c.citation_tag: citation_index[c.citation_tag]
        for c in top_cards
        if c.citation_tag in citation_index
    }

    return AIQueryResponse(
        query=query,
        patient_id=patient_id,
        interpreted_filters=parsed,
        answer_statements=answer_statements,
        direct_summary=direct_summary,
        retrieved_records=top_cards,
        citation_index=used_citation_index,
        provider_used="Hybrid Relational SQL + Clinical Synonym Retriever",
        disclaimer=CLINICAL_DISCLAIMER,
        total_matches=len(candidate_cards),
    )


def extract_structured_clinical_note(note_text: str) -> NoteExtractionResponse:
    text_lower = note_text.lower()

    # Extract symptoms mentioned
    symptom_catalog = [
        ("Throbbing Headache", ["throbbing headache", "migraine", "severe headache", "headache"]),
        ("Photophobia", ["photophobia", "light sensitivity", "sensitive to light"]),
        ("Nausea / Vomiting", ["nausea", "vomiting", "emesis"]),
        ("Shortness of Breath (Dyspnea)", ["shortness of breath", "dyspnea", "breathlessness", "difficulty breathing"]),
        ("Wheezing", ["wheezing", "wheeze", "bronchospasm"]),
        ("Nocturnal Cough", ["nocturnal cough", "night cough", "dry cough", "cough"]),
        ("Chest Pain / Tightness", ["chest pain", "chest tightness", "angina", "substernal"]),
        ("Fatigue / Lethargy", ["fatigue", "lethargy", "tiredness", "exhaustion"]),
        ("Polyuria / Polydipsia", ["polyuria", "polydipsia", "excessive thirst", "frequent urination"]),
        ("Peripheral Tingling (Neuropathy)", ["tingling", "numbness", "paresthesia", "burning feet"]),
        ("Joint Pain (Arthralgia)", ["joint pain", "arthralgia", "morning stiffness", "swollen joints"]),
        ("Fever", ["fever", "pyrexia", "febrile", "chills"]),
        ("Dizziness / Vertigo", ["dizziness", "vertigo", "lightheaded"]),
        ("Epigastric Burning", ["epigastric", "heartburn", "acid reflux", "dyspepsia"]),
    ]

    extracted_symptoms = []
    for label, triggers in symptom_catalog:
        if any(t in text_lower for t in triggers):
            sev = "Severe" if any(w in text_lower for w in ["severe", "intense", "acute", "unbearable"]) else "Moderate"
            extracted_symptoms.append({"name": label, "severity": sev})

    dx_catalog = [
        ("Migraine with Aura", "G43.109", ["migraine", "photophobia", "aura", "sumatriptan"]),
        ("Type 2 Diabetes Mellitus", "E11.9", ["type 2 diabetes", "t2dm", "hba1c", "hyperglycemia", "metformin"]),
        ("Essential Hypertension", "I10", ["hypertension", "elevated bp", "high blood pressure", "amlodipine", "telmisartan"]),
        ("Bronchial Asthma", "J45.40", ["asthma", "wheezing", "bronchospasm", "salbutamol", "budesonide"]),
        ("Iron Deficiency Anemia", "D50.9", ["anemia", "low hemoglobin", "low ferritin", "iron deficiency"]),
        ("Hypothyroidism", "E03.9", ["hypothyroidism", "elevated tsh", "levothyroxine"]),
        ("Gastroesophageal Reflux Disease (GERD)", "K21.9", ["gerd", "acid reflux", "gastritis", "pantoprazole"]),
        ("Rheumatoid Arthritis", "M06.9", ["rheumatoid", "synovitis", "methotrexate"]),
    ]

    suspected_diagnoses = []
    for cond, icd, triggers in dx_catalog:
        if any(t in text_lower for t in triggers):
            suspected_diagnoses.append({"condition_name": cond, "icd10_code": icd, "status": "Provisional"})

    med_catalog = [
        ("Sumatriptan 50mg", "50mg PRN at headache onset"),
        ("Propranolol 40mg", "40mg BID prophylaxis"),
        ("Metformin 500mg", "500mg BID with meals"),
        ("Glimepiride 2mg", "2mg OD before breakfast"),
        ("Amlodipine 5mg", "5mg OD"),
        ("Telmisartan 40mg", "40mg OD"),
        ("Budesonide/Formoterol Inhaler", "2 puffs BID"),
        ("Salbutamol 100mcg Inhaler", "2 puffs PRN for acute relief"),
        ("Atorvastatin 20mg", "20mg HS"),
        ("Levothyroxine 50mcg", "50mcg OD empty stomach"),
        ("Pantoprazole 40mg", "40mg OD before breakfast"),
        ("Ferrous Sulfate 325mg", "325mg OD"),
    ]

    mentioned_medications = []
    for med_name, default_sig in med_catalog:
        base_word = med_name.split()[0].lower()
        if base_word in text_lower:
            mentioned_medications.append({"medication": med_name, "dosage_notes": default_sig})

    sentences = [s.strip() for s in re.split(r"[.\n]+", note_text.strip()) if s.strip()]
    chief_complaint = sentences[0][:140] if sentences else "Clinical consultation note"
    follow_up = "Review in 4 weeks with repeat laboratory panel."
    for s in sentences:
        if any(w in s.lower() for w in ["follow", "review", "return", "recheck", "week", "month"]):
            follow_up = s
            break

    concise_summary = (
        f"Extracted {len(extracted_symptoms)} symptom(s), {len(suspected_diagnoses)} condition(s), "
        f"and {len(mentioned_medications)} medication reference(s) from clinical note."
    )

    return NoteExtractionResponse(
        chief_complaint=chief_complaint,
        extracted_symptoms=extracted_symptoms,
        suspected_diagnoses=suspected_diagnoses,
        mentioned_medications=mentioned_medications,
        recommended_follow_up=follow_up,
        concise_summary=concise_summary,
    )
