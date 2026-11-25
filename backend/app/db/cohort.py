"""Builds the synthetic Indian patient cohort on top of the hand-written storylines.

The cohort is deterministic: the same seed always produces the same people, so
demo screenshots, viva walkthroughs and tests stay stable between deployments.
"""

from datetime import date, datetime, timedelta, timezone
from random import Random
from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.cohort_people import (
    BLOOD_GROUPS,
    BUILDINGS,
    GENERIC_ALLERGIES,
    MOBILE_LEADS,
    REGIONS,
    RELATIONS_ADULT_FEMALE,
    RELATIONS_ADULT_MALE,
    Region,
)
from app.db.cohort_stories import (
    EXTRA_MEDICATIONS,
    SPECIALTY_TO_DOCTOR_KEY,
    STORYLINES,
    Ctx,
)
from app.models import (
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

COHORT_SEED = 2026
COHORT_SIZE = 156
LATEST_VISIT = date(2026, 11, 20)
EARLIEST_START = date(2023, 1, 9)

EXTRA_DOCTORS = [
    # key, email, full name, specialization, department, registration no.
    ("cardio", "dr.reddy@medvault.edu", "Dr. Arjun Reddy, DM (Cardiology)", "Interventional Cardiology",
     "Department of Cardiology", "DMC/R/10482"),
    ("endo", "dr.qureshi@medvault.edu", "Dr. Farhan Qureshi, DM (Endocrinology)", "Endocrinology & Thyroid Disorders",
     "Department of Endocrinology", "DMC/R/11937"),
    ("obgyn", "dr.subramanian@medvault.edu", "Dr. Lakshmi Subramanian, MS (OBG)", "Obstetrics & Gynaecology",
     "Department of Obstetrics & Gynaecology", "DMC/R/09215"),
    ("paeds", "dr.kaur@medvault.edu", "Dr. Harpreet Kaur, MD (Paediatrics)", "Paediatrics & Child Health",
     "Department of Paediatrics", "DMC/R/12650"),
    ("nephro", "dr.banerjee@medvault.edu", "Dr. Sanjay Banerjee, DM (Nephrology)", "Nephrology & Dialysis",
     "Department of Nephrology", "DMC/R/08874"),
    ("gastro", "dr.pillai@medvault.edu", "Dr. Meenakshi Pillai, DM (Gastroenterology)", "Gastroenterology & Hepatology",
     "Department of Gastroenterology", "DMC/R/13308"),
    ("psych", "dr.chatterjee@medvault.edu", "Dr. Kunal Chatterjee, MD (Psychiatry)", "Psychiatry & Behavioural Sciences",
     "Department of Psychiatry", "DMC/R/14021"),
    ("ortho", "dr.patil@medvault.edu", "Dr. Vivek Patil, MS (Orthopaedics)", "Orthopaedics & Joint Replacement",
     "Department of Orthopaedics", "DMC/R/10096"),
]


def _weighted(rng: Random, items, weight_of):
    total = sum(weight_of(i) for i in items)
    pick = rng.uniform(0, total)
    upto = 0.0
    for item in items:
        upto += weight_of(item)
        if upto >= pick:
            return item
    return items[-1]


def _mobile(rng: Random) -> str:
    lead = rng.choice(MOBILE_LEADS)
    rest = f"{rng.randint(0, 999):03d}{rng.randint(0, 99999):05d}"
    full = lead + rest
    return f"+91-{full[:5]}-{full[5:]}"


def _address(rng: Random, region: Region):
    locality, city, pin = rng.choice(region.localities)
    building = rng.choice(BUILDINGS).format(n=rng.randint(2, 480), n2=rng.randint(1, 24))
    return f"{building}, {locality}, {city} {pin}", city


def _slug(text: str) -> str:
    return "".join(ch for ch in text.lower().replace(" ", ".") if ch.isalnum() or ch == ".")


def _pick_start(rng: Random, span_days: int, months) -> date:
    latest_start = LATEST_VISIT - timedelta(days=span_days)
    if latest_start <= EARLIEST_START:
        return EARLIEST_START
    for _ in range(40):
        candidate = EARLIEST_START + timedelta(days=rng.randint(0, (latest_start - EARLIEST_START).days))
        if not months or candidate.month in months:
            return candidate
    return latest_start


def _as_dt(d: date, rng: Random) -> datetime:
    return datetime(d.year, d.month, d.day, rng.randint(9, 17), rng.choice((0, 10, 15, 20, 30, 40, 45, 50)),
                    tzinfo=timezone.utc)


def seed_cohort(db: Session, meds: Dict[str, Medication], doctors: Dict[str, Doctor], next_mrn: int) -> int:
    """Insert the generated cohort. Returns the number of patients created."""
    rng = Random(COHORT_SEED)

    for spec in EXTRA_MEDICATIONS:
        name, generic, cls, form, strength = spec
        if name in meds:
            continue
        med = Medication(name=name, generic_name=generic, drug_class=cls, form=form, strength=strength)
        db.add(med)
        meds[name] = med

    doctor_role_id = doctors["internal"].user.role_id
    # One bcrypt hash shared by every demo doctor keeps cold starts fast on serverless.
    shared_hash = doctors["internal"].user.password_hash
    for key, email, full_name, specialization, department, reg_no in EXTRA_DOCTORS:
        user = User(email=email, password_hash=shared_hash, full_name=full_name, role_id=doctor_role_id, is_active=True)
        doctor = Doctor(user=user, specialization=specialization, license_no=reg_no, department=department,
                        phone=_mobile(rng))
        db.add(doctor)
        doctors[key] = doctor
    db.flush()

    created = 0
    used_names = set()
    while created < COHORT_SIZE:
        story_fn, _, sex_rule, (age_lo, age_hi), months = _weighted(rng, STORYLINES, lambda s: s[1])
        region = _weighted(rng, REGIONS, lambda r: r.weight)
        sex = sex_rule or rng.choice(("Male", "Female"))
        first = rng.choice(region.male if sex == "Male" else region.female)
        surname_pool = region.female_surnames if (sex == "Female" and region.female_surnames) else region.surnames
        last = rng.choice(surname_pool)
        if (first, last) in used_names:
            continue
        used_names.add((first, last))

        age = rng.randint(age_lo, age_hi)
        if age < 13:
            weight = round(age * 2.6 + 8 + rng.uniform(-2, 2), 1)
        elif sex == "Male":
            weight = round(rng.uniform(58, 86), 1)
        else:
            weight = round(rng.uniform(48, 74), 1)

        # Build once with a provisional start to learn the span, then rebuild with the real start date.
        story_rng_seed = rng.randint(0, 10**9)
        probe = story_fn(Random(story_rng_seed), Ctx(first, sex, age, weight, EARLIEST_START))
        offsets, day = [], 0
        for v in probe.visits:
            day = v.day if not offsets else day + v.day
            offsets.append(day)
        start = _pick_start(rng, offsets[-1], months)
        story = story_fn(Random(story_rng_seed), Ctx(first, sex, age, weight, start))

        dob = start - timedelta(days=age * 365 + rng.randint(0, 364))
        address, _city = _address(rng, region)
        if age < 13:
            guardian_sex = rng.choice(("Female", "Male"))
            guardian_first = rng.choice(region.female if guardian_sex == "Female" else region.male)
            relation = "Mother" if guardian_sex == "Female" else "Father"
            guardian_last = last if region.key != "punjabi_sikh" else ("Kaur" if guardian_sex == "Female" else "Singh")
            contact_name = f"{guardian_first} {guardian_last} ({relation})"
        else:
            relation = rng.choice(RELATIONS_ADULT_MALE if sex == "Male" else RELATIONS_ADULT_FEMALE)
            contact_is_female = relation in ("Sister", "Mother", "Daughter") or (relation == "Spouse" and sex == "Male")
            contact_first = rng.choice(region.female if contact_is_female else region.male)
            contact_last = last
            if region.key == "punjabi_sikh":
                contact_last = "Kaur" if contact_is_female else "Singh"
            contact_name = f"{contact_first} {contact_last} ({relation})"

        blood = _weighted(rng, BLOOD_GROUPS, lambda b: b[1])[0]
        patient = Patient(
            mrn=f"MRN-2026-{next_mrn:05d}",
            first_name=first,
            last_name=last,
            date_of_birth=dob,
            sex=sex,
            # A few records are left incomplete on purpose so the AI data-gap detector has real gaps to find.
            blood_group=None if rng.random() < 0.06 else blood,
            phone=_mobile(rng),
            email=None if rng.random() < 0.25 else f"{_slug(first)}.{_slug(last)}{next_mrn}.demo@synthetic-clinic.org",
            address=address,
            emergency_contact_name=contact_name,
            emergency_contact_phone=None if rng.random() < 0.05 else _mobile(rng),
            is_synthetic=True,
            is_active=True,
        )
        next_mrn += 1
        db.add(patient)

        doctor = doctors[SPECIALTY_TO_DOCTOR_KEY.get(story.specialty, "internal")]
        patient.assigned_doctors.append(doctor)
        if doctor is not doctors["internal"] and rng.random() < 0.3:
            patient.assigned_doctors.append(doctors["internal"])

        for name, category, onset, status, notes in story.history:
            patient.medical_history.append(
                MedicalHistoryItem(condition_name=name, category=category, onset_date=onset, status=status, notes=notes)
            )
        if rng.random() < 0.28:
            allergen, reaction, severity = rng.choice(GENERIC_ALLERGIES)
            patient.allergies.append(
                Allergy(allergen=allergen, reaction=reaction, severity=severity, status="Active",
                        recorded_date=start - timedelta(days=rng.randint(30, 1500)))
            )

        for spec, offset in zip(story.visits, offsets):
            visit_day = start + timedelta(days=offset)
            when = _as_dt(visit_day, rng)
            bp, hr, temp, spo2, wt = spec.vitals
            visit = Visit(
                patient=patient,
                doctor=doctor,
                visit_date=when,
                visit_type=spec.vtype,
                chief_complaint=spec.complaint,
                vitals_bp=bp,
                vitals_hr=hr,
                vitals_temp_c=temp,
                vitals_spo2=spo2,
                vitals_weight_kg=f"{wt:.1f}",
                treatment_plan=spec.plan,
                created_at=when,
                updated_at=when,
            )
            visit.symptoms = [Symptom(name=n, severity=s, duration_days=d, notes=x or None) for n, s, d, x in spec.symptoms]
            visit.diagnoses = [Diagnosis(condition_name=n, icd10_code=c, status=s, notes=x or None) for n, c, s, x in spec.diagnoses]
            visit.prescriptions = [
                Prescription(medication=meds[m], dosage=dose, frequency=freq, duration_days=dur, instructions=ins or None)
                for m, dose, freq, dur, ins in spec.rx
            ]
            visit.clinical_notes = [ClinicalNote(author_id=doctor.user_id, note_type=spec.note_type, content=spec.note, created_at=when)]
            visit.test_results = [
                TestResult(test_name=n, value=val, unit=u or None, reference_range=ref, flag=f, result_date=visit_day,
                           remarks=rem or None)
                for n, val, u, ref, f, rem in spec.labs
            ]
            db.add(visit)
        created += 1

    db.flush()
    return created
