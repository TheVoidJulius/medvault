from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.cohort import seed_cohort
from app.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    Doctor,
    MedicalHistoryItem,
    Medication,
    Patient,
    Prescription,
    Role,
    Symptom,
    TestResult,
    User,
    Visit,
)


def dt(year: int, month: int, day: int, hour: int = 10, minute: int = 30) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def seed_database_if_empty(db: Session) -> dict:
    existing_patients = db.query(Patient).count()
    if existing_patients > 0:
        return {"status": "already_seeded", "patients": existing_patients}
    # Clean any partial rows if a prior run failed mid-transaction
    if db.query(Role).count() > 0:
        return {"status": "already_initialized"}

    # 1. Roles
    admin_role = Role(name="admin", description="System Administrator & Records Governance")
    doctor_role = Role(name="doctor", description="Attending Physician & Clinical Specialist")
    db.add_all([admin_role, doctor_role])
    db.flush()

    # 2. Users & Doctors
    admin_user = User(
        email="admin@medvault.edu",
        password_hash=get_password_hash("Admin@123"),
        full_name="Pushkar Panwar (Admin)",
        role_id=admin_role.id,
        is_active=True,
    )
    doc_user_1 = User(
        email="dr.sharma@medvault.edu",
        password_hash=get_password_hash("Doctor@123"),
        full_name="Dr. Ananya Sharma, MD",
        role_id=doctor_role.id,
        is_active=True,
    )
    doc_user_2 = User(
        email="dr.verma@medvault.edu",
        password_hash=get_password_hash("Doctor@123"),
        full_name="Dr. Rajesh Verma, DM (Neurology)",
        role_id=doctor_role.id,
        is_active=True,
    )
    doc_user_3 = User(
        email="dr.nair@medvault.edu",
        password_hash=get_password_hash("Doctor@123"),
        full_name="Dr. Priya Nair, MD (Pulmonology)",
        role_id=doctor_role.id,
        is_active=True,
    )
    db.add_all([admin_user, doc_user_1, doc_user_2, doc_user_3])
    db.flush()

    doc_internal = Doctor(
        user_id=doc_user_1.id,
        specialization="Internal Medicine & Diabetology",
        license_no="MCI-DL-2016-44812",
        department="Department of Internal Medicine",
        phone="+91-98110-22301",
    )
    doc_neuro = Doctor(
        user_id=doc_user_2.id,
        specialization="Neurology & Headache Disorders",
        license_no="MCI-DL-2014-31908",
        department="Department of Neurology",
        phone="+91-98110-22302",
    )
    doc_pulmo = Doctor(
        user_id=doc_user_3.id,
        specialization="Pulmonology & Critical Care",
        license_no="MCI-DL-2018-77419",
        department="Department of Respiratory Medicine",
        phone="+91-98110-22303",
    )
    db.add_all([doc_internal, doc_neuro, doc_pulmo])
    db.flush()

    # 3. Medications Catalog
    med_specs = [
        ("Sumatriptan", "Sumatriptan Succinate", "Triptan (Antimigraine)", "Tablet", "50mg"),
        ("Propranolol", "Propranolol Hydrochloride", "Beta-Blocker", "Tablet", "40mg"),
        ("Naproxen", "Naproxen Sodium", "NSAID", "Tablet", "500mg"),
        ("Metformin", "Metformin Hydrochloride", "Biguanide Antidiabetic", "Tablet", "500mg"),
        ("Glimepiride", "Glimepiride", "Sulfonylurea", "Tablet", "2mg"),
        ("Amlodipine", "Amlodipine Besylate", "Calcium Channel Blocker", "Tablet", "5mg"),
        ("Telmisartan", "Telmisartan", "ARB Antihypertensive", "Tablet", "40mg"),
        ("Atorvastatin", "Atorvastatin Calcium", "HMG-CoA Reductase Inhibitor (Statin)", "Tablet", "20mg"),
        ("Budesonide+Formoterol", "Budesonide 200mcg + Formoterol 6mcg", "ICS + LABA Inhaler", "Inhaler", "200/6mcg"),
        ("Salbutamol", "Levosalbutamol / Salbutamol", "Short-Acting Beta Agonist (SABA)", "Inhaler", "100mcg"),
        ("Montelukast", "Montelukast Sodium", "Leukotriene Receptor Antagonist", "Tablet", "10mg"),
        ("Levothyroxine", "Levothyroxine Sodium", "Thyroid Hormone Replacement", "Tablet", "75mcg"),
        ("Pantoprazole", "Pantoprazole Sodium", "Proton Pump Inhibitor (PPI)", "Tablet", "40mg"),
        ("Ferrous Ascorbate", "Elemental Iron + Folic Acid", "Hematinic / Iron Supplement", "Tablet", "100mg"),
        ("Methotrexate", "Methotrexate", "DMARD", "Tablet", "15mg"),
        ("Pregabalin", "Pregabalin + Methylcobalamin", "Neuropathic Analgesic", "Capsule", "75mg"),
    ]
    meds = {}
    for name, gen, cls, form, strength in med_specs:
        m = Medication(name=name, generic_name=gen, drug_class=cls, form=form, strength=strength)
        db.add(m)
        db.flush()
        meds[name] = m

    # Helper to create visits cleanly
    def add_visit(
        patient: Patient,
        doctor: Doctor,
        vdate: datetime,
        vtype: str,
        complaint: str,
        bp: str,
        hr: int,
        temp: str,
        spo2: int,
        weight: str,
        plan: str,
        symptoms_list: list,
        diagnoses_list: list,
        rx_list: list,
        note_text: str,
        labs_list: list,
        note_type: str = "SOAP",
    ):
        v = Visit(
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_date=vdate,
            visit_type=vtype,
            chief_complaint=complaint,
            vitals_bp=bp,
            vitals_hr=hr,
            vitals_temp_c=temp,
            vitals_spo2=spo2,
            vitals_weight_kg=weight,
            treatment_plan=plan,
            created_at=vdate,
            updated_at=vdate,
        )
        db.add(v)
        db.flush()

        for s_name, s_sev, s_dur, s_notes in symptoms_list:
            db.add(Symptom(visit_id=v.id, name=s_name, severity=s_sev, duration_days=s_dur, notes=s_notes))

        for d_name, d_icd, d_status, d_notes in diagnoses_list:
            db.add(
                Diagnosis(
                    visit_id=v.id,
                    condition_name=d_name,
                    icd10_code=d_icd,
                    status=d_status,
                    notes=d_notes,
                )
            )

        for m_key, dosage, freq, dur, instr in rx_list:
            db.add(
                Prescription(
                    visit_id=v.id,
                    medication_id=meds[m_key].id,
                    dosage=dosage,
                    frequency=freq,
                    duration_days=dur,
                    instructions=instr,
                )
            )

        db.add(
            ClinicalNote(
                visit_id=v.id,
                author_id=doctor.user_id,
                note_type=note_type,
                content=note_text,
                created_at=vdate,
            )
        )

        for t_name, t_val, t_unit, t_ref, t_flag, t_rem in labs_list:
            db.add(
                TestResult(
                    visit_id=v.id,
                    test_name=t_name,
                    value=t_val,
                    unit=t_unit,
                    reference_range=t_ref,
                    flag=t_flag,
                    result_date=vdate.date(),
                    remarks=t_rem,
                )
            )

    # =========================================================================
    # PATIENT 1: Aarav Mehta (Recurring Headaches / Migraine Storyline)
    # =========================================================================
    p1 = Patient(
        mrn="MRN-2026-00001",
        first_name="Aarav",
        last_name="Mehta",
        date_of_birth=date(1992, 4, 14),
        sex="Male",
        blood_group="O+",
        phone="+91-98101-44210",
        email="aarav.mehta.demo@synthetic-clinic.org",
        address="B-42, Hauz Khas Enclave, New Delhi",
        emergency_contact_name="Neha Mehta (Spouse)",
        emergency_contact_phone="+91-98101-44211",
        is_synthetic=True,
        is_active=True,
    )
    db.add(p1)
    db.flush()
    p1.assigned_doctors.extend([doc_neuro, doc_internal])

    db.add_all(
        [
            Allergy(
                patient_id=p1.id,
                allergen="Penicillin",
                reaction="Generalized urticaria and maculopapular rash",
                severity="Severe",
                status="Active",
                recorded_date=date(2024, 3, 12),
            ),
            MedicalHistoryItem(
                patient_id=p1.id,
                condition_name="Episodic Tension & Migraine Headaches",
                category="Chronic",
                onset_date=date(2023, 8, 1),
                status="Active",
                notes="Triggered by prolonged screen exposure, sleep deprivation, and dehydration.",
            ),
            MedicalHistoryItem(
                patient_id=p1.id,
                condition_name="Maternal Family History of Classic Migraine",
                category="Family",
                onset_date=None,
                status="Historical",
                notes="Mother diagnosed with migraine with visual aura at age 28.",
            ),
        ]
    )

    add_visit(
        p1,
        doc_neuro,
        dt(2024, 5, 18),
        "OPD",
        "Recurrent unilateral throbbing headache with light sensitivity",
        "122/78 mmHg",
        76,
        "36.8",
        99,
        "74.0",
        "Initiate acute abortive therapy; maintain headache trigger diary; rule out secondary causes.",
        [
            ("Recurring Headache", "Moderate", 4, "Right fronto-temporal throbbing pain"),
            ("Photophobia", "Moderate", 2, "Worsens with bright office monitors"),
            ("Nausea", "Mild", 1, "No emesis reported"),
        ],
        [
            ("Tension-Type Headache", "G44.209", "Ruled-out", "Initially suspected tension headache; clinical features favour migraine."),
            ("Migraine without Aura", "G43.009", "Provisional", "Unilateral pulsatile headache lasting 12-24 hours."),
        ],
        [
            ("Naproxen", "500mg", "SOS (max twice daily)", 10, "Take with food at headache onset"),
            ("Pantoprazole", "40mg", "OD before breakfast", 10, "Gastroprotection alongside NSAID"),
        ],
        "S: 32yo software architect presenting with recurrent right-sided throbbing headaches over the past 3 months. Reports photophobia and mild nausea during episodes. O: Cranial nerves II-XII intact, fundoscopy normal, no neck rigidity. A: Provisional Migraine without Aura; Tension-Type Headache ruled out due to photophobia and nausea. P: Trial of Naproxen 500mg abortive therapy + trigger diary.",
        [
            ("Serum Vitamin D (25-OH)", "16.4", "ng/mL", "30.0 - 100.0", "Low", "Insufficient Vitamin D level"),
            ("Hemoglobin", "14.6", "g/dL", "13.5 - 17.5", "Normal", "Normal baseline CBC"),
        ],
    )

    add_visit(
        p1,
        doc_neuro,
        dt(2025, 1, 22),
        "Follow-up",
        "Worsening recurring headaches preceded by shimmering visual zig-zag lines",
        "126/82 mmHg",
        80,
        "36.7",
        99,
        "74.5",
        "Upgrade to Sumatriptan abortive therapy; brain MRI normal; monitor frequency.",
        [
            ("Recurring Headache", "Severe", 3, "Bilateral to right-sided pulsating pain, 5 episodes this month"),
            ("Visual Aura (Scintillating Scotoma)", "Moderate", 1, "20-minute flickering zig-zag lines before headache"),
            ("Photophobia", "Severe", 2, "Requires dark room rest"),
        ],
        [
            ("Migraine with Aura", "G43.109", "Confirmed", "Classic visual aura followed by severe pulsatile headache."),
        ],
        [
            ("Sumatriptan", "50mg", "1 tablet at aura/headache onset (max 100mg/24h)", 30, "Abortive triptan therapy"),
        ],
        "S: Patient returns with increased frequency of recurring headaches (5 episodes/month), now preceded by 20 minutes of shimmering visual aura. NSAIDs no longer provide adequate relief. O: Neurological exam normal. MRI Brain (plain) shows no intracranial mass, hemorrhage, or demyelination. A: Confirmed Migraine with Aura (ICD-10 G43.109). P: Start Sumatriptan 50mg PRN at onset.",
        [
            ("MRI Brain (Non-Contrast)", "Unremarkable", "", "Normal parenchyma & vasculature", "Normal", "Rules out secondary structural pathology"),
        ],
    )

    add_visit(
        p1,
        doc_neuro,
        dt(2025, 9, 10),
        "Follow-up",
        "Frequent migraine attacks during high-stress project deployment (7 episodes/month)",
        "128/84 mmHg",
        82,
        "36.6",
        98,
        "75.0",
        "Initiate daily Propranolol prophylaxis alongside Sumatriptan rescue; sleep hygiene counseling.",
        [
            ("Recurring Headache", "Severe", 5, "7 migraine days in the past 30 days"),
            ("Photophobia", "Moderate", 3, "Persistent light sensitivity during attacks"),
            ("Neck Stiffness", "Mild", 3, "Prodromal cervical tightness"),
        ],
        [
            ("Migraine with Aura", "G43.109", "Confirmed", "High-frequency episodic migraine requiring prophylaxis."),
        ],
        [
            ("Propranolol", "40mg", "1 tablet twice daily (BID)", 90, "Daily migraine prophylaxis; monitor heart rate"),
            ("Sumatriptan", "50mg", "PRN at acute attack onset", 30, "Limit to <= 8 days/month to prevent medication overuse headache"),
        ],
        "S: Patient reports Sumatriptan aborts acute attacks within 90 minutes, but attack frequency escalated to 7 days/month during late-night work sprints. O: BP 128/84, HR 82 bpm regular. No focal neurological deficits. A: High-frequency Migraine with Aura. P: Commence Propranolol 40mg BID for prophylaxis; continue Sumatriptan PRN.",
        [
            ("Resting ECG (12-Lead)", "Normal Sinus Rhythm, HR 82", "bpm", "60 - 100 bpm, Normal PR interval", "Normal", "Cleared for Beta-Blocker prophylaxis"),
        ],
    )

    add_visit(
        p1,
        doc_neuro,
        dt(2026, 8, 14),
        "Follow-up",
        "Routine neurology review — significant reduction in recurring headaches",
        "118/74 mmHg",
        66,
        "36.6",
        99,
        "73.8",
        "Continue Propranolol 40mg BID prophylaxis; review in 6 months.",
        [
            ("Recurring Headache", "Mild", 1, "Reduced from 7 episodes/month down to 1 mild episode/month"),
        ],
        [
            ("Migraine with Aura", "G43.109", "Confirmed", "Well-controlled on Propranolol prophylaxis."),
        ],
        [
            ("Propranolol", "40mg", "1 tablet twice daily (BID)", 90, "Continue maintenance prophylaxis"),
            ("Sumatriptan", "50mg", "PRN for breakthrough migraine", 15, "Used only once in past 60 days"),
        ],
        "S: Patient reports >80% reduction in recurring headaches since starting Propranolol 40mg BID. Only 1 mild headache in the last two months, resolved promptly. O: BP 118/74 mmHg, HR 66 bpm. Well tolerated with no bradycardia or fatigue. A: Migraine with Aura — well controlled. P: Continue current regimen.",
        [
            ("Serum Vitamin D (25-OH)", "34.8", "ng/mL", "30.0 - 100.0", "Normal", "Normalized after supplementation"),
        ],
    )

    # =========================================================================
    # PATIENT 2: Meera Krishnan (Type 2 Diabetes + Hypertension + Neuropathy)
    # =========================================================================
    p2 = Patient(
        mrn="MRN-2026-00002",
        first_name="Meera",
        last_name="Krishnan",
        date_of_birth=date(1968, 11, 3),
        sex="Female",
        blood_group="B+",
        phone="+91-98102-55320",
        email="meera.krishnan.demo@synthetic-clinic.org",
        address="C-118, Defence Colony, New Delhi",
        emergency_contact_name="Karthik Krishnan (Son)",
        emergency_contact_phone="+91-98102-55321",
        is_synthetic=True,
        is_active=True,
    )
    db.add(p2)
    db.flush()
    p2.assigned_doctors.append(doc_internal)

    db.add_all(
        [
            Allergy(
                patient_id=p2.id,
                allergen="Sulfonamides (Sulfa Drugs)",
                reaction="Pruritic skin eruption and facial angioedema",
                severity="Severe",
                status="Active",
                recorded_date=date(2022, 6, 10),
            ),
            MedicalHistoryItem(
                patient_id=p2.id,
                condition_name="Type 2 Diabetes Mellitus",
                category="Chronic",
                onset_date=date(2019, 4, 15),
                status="Active",
                notes="Managed with oral hypoglycemics and medical nutrition therapy.",
            ),
            MedicalHistoryItem(
                patient_id=p2.id,
                condition_name="Essential Hypertension",
                category="Chronic",
                onset_date=date(2020, 9, 1),
                status="Controlled",
                notes="On ARB + CCB combination therapy.",
            ),
            MedicalHistoryItem(
                patient_id=p2.id,
                condition_name="Laparoscopic Cholecystectomy",
                category="Surgical",
                onset_date=date(2017, 2, 19),
                status="Resolved",
                notes="Uneventful surgery for symptomatic cholelithiasis.",
            ),
        ]
    )

    add_visit(
        p2,
        doc_internal,
        dt(2024, 7, 11),
        "OPD",
        "Suboptimal glycemic control with fatigue, polyuria, and elevated home blood pressure",
        "152/94 mmHg",
        84,
        "36.7",
        98,
        "71.5",
        "Intensify Metformin + Telmisartan; initiate statin; diabetic diet counseling.",
        [
            ("Fatigue", "Moderate", 21, "Persistent afternoon exhaustion"),
            ("Polyuria", "Moderate", 14, "Nocturia 3 times per night"),
            ("Polydipsia", "Mild", 14, "Increased thirst"),
        ],
        [
            ("Type 2 Diabetes Mellitus", "E11.9", "Confirmed", "Uncontrolled glycemic status (HbA1c 8.9%)."),
            ("Essential Hypertension", "I10", "Confirmed", "Stage 2 elevation on monotherapy."),
            ("Mixed Hyperlipidemia", "E78.2", "Confirmed", "Elevated LDL cholesterol."),
        ],
        [
            ("Metformin", "500mg", "2 tablets twice daily (1000mg BID)", 90, "Take after meals"),
            ("Telmisartan", "40mg", "1 tablet once daily (OD)", 90, "Morning antihypertensive"),
            ("Atorvastatin", "20mg", "1 tablet at bedtime (HS)", 90, "Cardiovascular risk reduction"),
        ],
        "S: 55yo female with 5-year history of T2DM and HTN presents with fatigue and polyuria. Admits to dietary lapses during travel. O: BP 152/94 mmHg, BMI 27.8. Foot monofilament exam intact. Labs show HbA1c 8.9% and fasting glucose 194 mg/dL. A: Uncontrolled T2DM and Essential Hypertension. P: Uptitrate Metformin to 1000mg BID, continue Telmisartan 40mg, start Atorvastatin 20mg HS.",
        [
            ("HbA1c (Glycated Hemoglobin)", "8.9", "%", "4.0 - 5.6", "High", "Poor glycemic control over prior 3 months"),
            ("Fasting Blood Glucose", "194", "mg/dL", "70 - 99", "High", "Hyperglycemia"),
            ("LDL Cholesterol", "158", "mg/dL", "< 100", "High", "Above target for diabetic patient"),
            ("Serum Creatinine", "0.92", "mg/dL", "0.6 - 1.1", "Normal", "Preserved renal function"),
        ],
    )

    add_visit(
        p2,
        doc_internal,
        dt(2025, 4, 9),
        "Follow-up",
        "Burning tingling sensation in bilateral feet and persistent morning hyperglycemia",
        "142/88 mmHg",
        78,
        "36.6",
        98,
        "70.2",
        "Add Amlodipine 5mg for BP target <130/80; start Pregabalin for diabetic neuropathy; foot care education.",
        [
            ("Peripheral Tingling (Paresthesia)", "Moderate", 30, "Burning pins-and-needles sensation in both soles at night"),
            ("Fatigue", "Mild", 14, "Improved compared to last year"),
        ],
        [
            ("Type 2 Diabetes Mellitus with Diabetic Polyneuropathy", "E11.42", "Confirmed", "Early distal symmetric sensorimotor polyneuropathy."),
            ("Essential Hypertension", "I10", "Confirmed", "Requires dual antihypertensive therapy."),
        ],
        [
            ("Metformin", "500mg", "1000mg twice daily (BID)", 90, "Continue after meals"),
            ("Telmisartan", "40mg", "1 tablet OD", 90, "Continue morning dose"),
            ("Amlodipine", "5mg", "1 tablet OD in evening", 90, "Added for dual BP control"),
            ("Pregabalin", "75mg", "1 capsule at bedtime (HS)", 60, "For neuropathic foot tingling"),
            ("Atorvastatin", "20mg", "1 tablet HS", 90, "Continue statin"),
        ],
        "S: Patient reports nocturnal burning and tingling in bilateral feet over the past month. Home fasting sugars averaging 145 mg/dL. O: BP 142/88 mmHg. Decreased vibration perception at bilateral great toes; ankle reflexes diminished. HbA1c improved from 8.9% to 7.8%. A: T2DM with early Diabetic Peripheral Neuropathy (E11.42); Hypertension. P: Add Amlodipine 5mg OD, start Pregabalin 75mg HS, reinforce daily foot inspection.",
        [
            ("HbA1c (Glycated Hemoglobin)", "7.8", "%", "4.0 - 5.6", "High", "Improved from 8.9% but still above 7.0% target"),
            ("Fasting Blood Glucose", "146", "mg/dL", "70 - 99", "High", "Moderate fasting hyperglycemia"),
            ("Urine Microalbumin-to-Creatinine Ratio", "24", "mg/g", "< 30", "Normal", "No diabetic nephropathy"),
        ],
    )

    add_visit(
        p2,
        doc_internal,
        dt(2026, 6, 20),
        "Follow-up",
        "6-month diabetes and hypertension review — improved HbA1c and controlled BP",
        "126/78 mmHg",
        74,
        "36.6",
        99,
        "68.4",
        "Continue current metabolic and neuropathic regimen; annual retinal screening normal.",
        [
            ("Peripheral Tingling (Paresthesia)", "Mild", 7, "Significantly reduced on Pregabalin"),
        ],
        [
            ("Type 2 Diabetes Mellitus with Diabetic Polyneuropathy", "E11.42", "Confirmed", "Glycemic target achieved (HbA1c 6.9%)."),
            ("Essential Hypertension", "I10", "Confirmed", "Well controlled on Telmisartan + Amlodipine."),
        ],
        [
            ("Metformin", "500mg", "1000mg BID", 90, "Continue maintenance"),
            ("Telmisartan", "40mg", "1 tablet OD", 90, "Continue maintenance"),
            ("Amlodipine", "5mg", "1 tablet OD", 90, "Continue maintenance"),
            ("Pregabalin", "75mg", "1 capsule HS", 90, "Continue for neuropathy relief"),
            ("Atorvastatin", "20mg", "1 tablet HS", 90, "Continue statin"),
        ],
        "S: Patient adherent to diet, walking 40 mins daily, and taking medications regularly. Foot tingling is now minimal. O: BP 126/78 mmHg, weight down 1.8 kg. HbA1c down to 6.9%, LDL 88 mg/dL. A: T2DM and HTN at clinical goal. P: Continue current regimen; review in 6 months.",
        [
            ("HbA1c (Glycated Hemoglobin)", "6.9", "%", "4.0 - 5.6", "High", "At ADA diabetic therapeutic target (<7.0%)"),
            ("Fasting Blood Glucose", "118", "mg/dL", "70 - 99", "High", "Near-normal fasting glucose"),
            ("LDL Cholesterol", "88", "mg/dL", "< 100", "Normal", "Controlled on Atorvastatin 20mg"),
        ],
    )

    # =========================================================================
    # PATIENT 3: Rohan Deshmukh (Bronchial Asthma & Seasonal Exacerbations)
    # =========================================================================
    p3 = Patient(
        mrn="MRN-2026-00003",
        first_name="Rohan",
        last_name="Deshmukh",
        date_of_birth=date(2001, 1, 25),
        sex="Male",
        blood_group="A+",
        phone="+91-98103-66430",
        email="rohan.deshmukh.demo@synthetic-clinic.org",
        address="Flat 402, Mayur Vihar Phase-1, Delhi",
        emergency_contact_name="Suresh Deshmukh (Father)",
        emergency_contact_phone="+91-98103-66431",
        is_synthetic=True,
        is_active=True,
    )
    db.add(p3)
    db.flush()
    p3.assigned_doctors.append(doc_pulmo)

    db.add_all(
        [
            Allergy(
                patient_id=p3.id,
                allergen="Aspirin / NSAIDs",
                reaction="Acute bronchospasm and wheezing",
                severity="Severe",
                status="Active",
                recorded_date=date(2023, 11, 5),
            ),
            Allergy(
                patient_id=p3.id,
                allergen="House Dust Mites & Winter Smog",
                reaction="Allergic rhinitis and asthma exacerbation",
                severity="Moderate",
                status="Active",
                recorded_date=date(2023, 11, 5),
            ),
            MedicalHistoryItem(
                patient_id=p3.id,
                condition_name="Childhood Allergic Rhinitis & Bronchial Asthma",
                category="Chronic",
                onset_date=date(2012, 10, 1),
                status="Active",
                notes="Seasonal exacerbations during November-January air quality deterioration.",
            ),
        ]
    )

    add_visit(
        p3,
        doc_pulmo,
        dt(2024, 11, 14),
        "Emergency",
        "Acute shortness of breath, audible wheezing, and nocturnal cough during winter smog",
        "130/82 mmHg",
        108,
        "37.1",
        93,
        "66.0",
        "Nebulization in ER; initiate Budesonide+Formoterol controller inhaler + Montelukast.",
        [
            ("Shortness of Breath (Dyspnea)", "Severe", 2, "Unable to complete full sentences without pausing"),
            ("Wheezing", "Severe", 3, "Bilateral expiratory polyphonic wheeze"),
            ("Nocturnal Cough", "Moderate", 7, "Awakening at 3 AM with chest tightness"),
        ],
        [
            ("Moderate Persistent Bronchial Asthma with Acute Exacerbation", "J45.41", "Confirmed", "Triggered by severe AQI smog exposure."),
        ],
        [
            ("Budesonide+Formoterol", "2 puffs (200/6mcg)", "Twice daily (BID) + rinse mouth", 90, "Daily maintenance controller & reliever"),
            ("Salbutamol", "2 puffs (100mcg)", "Every 6 hours PRN for acute wheeze", 30, "Rescue bronchodilator"),
            ("Montelukast", "10mg", "1 tablet at bedtime", 60, "For co-existing allergic rhinitis"),
        ],
        "S: 23yo student brought to clinic with acute dyspnea, wheezing, and nocturnal cough following 4 days of heavy winter smog. O: SpO2 93% on room air, HR 108 bpm, diffuse bilateral expiratory wheezes. Peak Expiratory Flow (PEF) 62% of predicted. Improved to SpO2 98% post-salbutamol nebulization. A: Acute Asthma Exacerbation (J45.41). P: Start Budesonide+Formoterol 200/6mcg BID, Montelukast 10mg HS, N95 mask outdoors.",
        [
            ("Spirometry FEV1 (% Predicted)", "64", "%", "> 80%", "Low", "Reversible obstructive airway pattern (+18% post-bronchodilator)"),
            ("Absolute Eosinophil Count (AEC)", "620", "cells/mcL", "40 - 440", "High", "Allergic eosinophilic airway inflammation"),
        ],
    )

    add_visit(
        p3,
        doc_pulmo,
        dt(2025, 11, 28),
        "OPD",
        "Mild seasonal wheezing and nocturnal cough after running out of controller inhaler",
        "120/76 mmHg",
        86,
        "36.8",
        97,
        "67.0",
        "Restart Budesonide+Formoterol controller immediately; verify spacer technique.",
        [
            ("Wheezing", "Moderate", 4, "Expiratory wheeze on forced exhalation"),
            ("Nocturnal Cough", "Moderate", 5, "Dry cough in early morning hours"),
        ],
        [
            ("Moderate Persistent Bronchial Asthma", "J45.40", "Confirmed", "Suboptimal adherence prior to winter season."),
        ],
        [
            ("Budesonide+Formoterol", "2 puffs", "Twice daily (BID)", 90, "Do not discontinue during winter months"),
            ("Montelukast", "10mg", "1 tablet HS", 60, "Continue throughout winter"),
        ],
        "S: Patient stopped controller inhaler 3 weeks ago feeling well, now experiencing return of nocturnal cough and mild wheezing. O: SpO2 97%, mild end-expiratory wheeze bilaterally. FEV1 76% predicted. A: Moderate Persistent Bronchial Asthma — mild flare due to non-adherence. P: Resume Budesonide+Formoterol BID with spacer.",
        [
            ("Spirometry FEV1 (% Predicted)", "76", "%", "> 80%", "Low", "Mild airflow limitation"),
        ],
    )

    add_visit(
        p3,
        doc_pulmo,
        dt(2026, 9, 5),
        "Follow-up",
        "Pre-winter asthma control check — asymptomatic with good exercise tolerance",
        "118/74 mmHg",
        72,
        "36.6",
        99,
        "67.5",
        "Maintain controller therapy through upcoming winter; influenza vaccination advised.",
        [
            ("Nocturnal Cough", "Mild", 1, "Rare occasional throat clearing only"),
        ],
        [
            ("Moderate Persistent Bronchial Asthma", "J45.40", "Confirmed", "Well controlled on ICS+LABA therapy."),
        ],
        [
            ("Budesonide+Formoterol", "1 puff", "Twice daily (BID) maintenance", 90, "Step-up to 2 puffs BID if AQI exceeds 300"),
        ],
        "S: Patient reports zero emergency visits over the past 10 months and plays badminton thrice weekly without dyspnea. O: Lungs clear to auscultation bilaterally, SpO2 99%, FEV1 91% predicted. A: Well-controlled Bronchial Asthma. P: Continue maintenance inhaler and pre-winter action plan.",
        [
            ("Spirometry FEV1 (% Predicted)", "91", "%", "> 80%", "Normal", "Normal pulmonary function achieved"),
        ],
    )

    # =========================================================================
    # PATIENT 4: Kavita Joshi (Hypothyroidism + Iron Deficiency Anemia + GERD)
    # =========================================================================
    p4 = Patient(
        mrn="MRN-2026-00004",
        first_name="Kavita",
        last_name="Joshi",
        date_of_birth=date(1985, 7, 19),
        sex="Female",
        blood_group="AB+",
        phone="+91-98104-77540",
        email="kavita.joshi.demo@synthetic-clinic.org",
        address="Sector 62, Noida, UP",
        emergency_contact_name="Rohit Joshi (Husband)",
        emergency_contact_phone="+91-98104-77541",
        is_synthetic=True,
        is_active=True,
    )
    db.add(p4)
    db.flush()
    p4.assigned_doctors.append(doc_internal)

    db.add_all(
        [
            MedicalHistoryItem(
                patient_id=p4.id,
                condition_name="Primary Hypothyroidism",
                category="Chronic",
                onset_date=date(2022, 3, 10),
                status="Active",
                notes="On daily Levothyroxine replacement.",
            ),
        ]
    )

    add_visit(
        p4,
        doc_internal,
        dt(2025, 2, 16),
        "OPD",
        "Progressive fatigue, hair thinning, cold intolerance, and epigastric burning",
        "114/72 mmHg",
        64,
        "36.4",
        99,
        "64.0",
        "Increase Levothyroxine to 75mcg OD; start oral iron supplementation and Pantoprazole.",
        [
            ("Fatigue", "Severe", 45, "Marked exhaustion and daytime somnolence"),
            ("Epigastric Burning", "Moderate", 14, "Post-prandial retrosternal heartburn"),
            ("Dizziness", "Mild", 10, "On standing rapidly"),
        ],
        [
            ("Primary Hypothyroidism", "E03.9", "Confirmed", "Subtherapeutic replacement (TSH 9.8 mIU/L)."),
            ("Iron Deficiency Anemia", "D50.9", "Confirmed", "Microcytic hypochromic anemia with low ferritin."),
            ("Gastroesophageal Reflux Disease (GERD)", "K21.9", "Confirmed", "Acid peptic symptoms."),
        ],
        [
            ("Levothyroxine", "75mcg", "1 tablet OD on empty stomach (60m before breakfast)", 90, "Separate from iron by at least 4 hours"),
            ("Ferrous Ascorbate", "100mg", "1 tablet OD after lunch", 90, "Take with Vitamin C / citrus juice"),
            ("Pantoprazole", "40mg", "1 tablet OD 30m before dinner", 28, "Short course for GERD"),
        ],
        "S: 39yo female presents with worsening fatigue, pallor, and post-meal epigastric burning. Taking Levothyroxine inconsistently alongside morning tea. O: Mild conjunctival pallor, thyroid non-tender, BP 114/72. Labs reveal TSH 9.8 mIU/L, Hb 9.6 g/dL, Ferritin 9 ng/mL. A: Undertreated Hypothyroidism + Iron Deficiency Anemia + GERD. P: Uptitrate Levothyroxine to 75mcg strict empty stomach, start Ferrous Ascorbate at lunch (4h gap from thyroid dose).",
        [
            ("Thyroid Stimulating Hormone (TSH)", "9.8", "mIU/L", "0.45 - 4.50", "High", "Hypothyroid range; requires dose adjustment"),
            ("Hemoglobin", "9.6", "g/dL", "12.0 - 15.5", "Low", "Moderate anemia"),
            ("Serum Ferritin", "9.2", "ng/mL", "15.0 - 150.0", "Low", "Depleted iron stores"),
        ],
    )

    add_visit(
        p4,
        doc_internal,
        dt(2026, 3, 21),
        "Follow-up",
        "Follow-up thyroid and anemia panel — energy levels restored",
        "116/76 mmHg",
        72,
        "36.6",
        99,
        "62.0",
        "Continue Levothyroxine 75mcg OD; stop daily iron after 1 more month of maintenance.",
        [
            ("Fatigue", "Mild", 3, "Resolved; normal daily stamina"),
        ],
        [
            ("Primary Hypothyroidism", "E03.9", "Confirmed", "Euthyroid on Levothyroxine 75mcg."),
            ("Iron Deficiency Anemia", "D50.9", "Resolved", "Hemoglobin and ferritin normalized."),
        ],
        [
            ("Levothyroxine", "75mcg", "1 tablet OD empty stomach", 90, "Continue lifelong replacement"),
            ("Ferrous Ascorbate", "100mg", "1 tablet alternate days", 30, "Final month to consolidate ferritin stores"),
        ],
        "S: Patient separated Levothyroxine from morning tea and afternoon iron tablet. Fatigue and dizziness have completely resolved. O: Conjunctivae pink, HR 72 bpm. Labs: TSH 2.4 mIU/L, Hb 12.8 g/dL, Ferritin 48 ng/mL. A: Euthyroid status and resolved Iron Deficiency Anemia. P: Continue Levothyroxine 75mcg.",
        [
            ("Thyroid Stimulating Hormone (TSH)", "2.4", "mIU/L", "0.45 - 4.50", "Normal", "Optimal euthyroid control"),
            ("Hemoglobin", "12.8", "g/dL", "12.0 - 15.5", "Normal", "Corrected from 9.6 g/dL"),
            ("Serum Ferritin", "48.0", "ng/mL", "15.0 - 150.0", "Normal", "Repleted iron stores"),
        ],
    )

    # =========================================================================
    # PATIENT 5: Vikramjit Gill (Coronary Risk / Hypertension / Chest Pain Workup)
    # =========================================================================
    p5 = Patient(
        mrn="MRN-2026-00005",
        first_name="Vikramjit",
        last_name="Gill",
        date_of_birth=date(1971, 9, 8),
        sex="Male",
        blood_group="O-",
        phone="+91-98105-88650",
        email="vikramjit.gill.demo@synthetic-clinic.org",
        address="DLF Phase 3, Gurugram, Haryana",
        emergency_contact_name="Simran Gill (Wife)",
        emergency_contact_phone="+91-98105-88651",
        is_synthetic=True,
        is_active=True,
    )
    db.add(p5)
    db.flush()
    p5.assigned_doctors.append(doc_internal)

    db.add_all(
        [
            Allergy(
                patient_id=p5.id,
                allergen="Shellfish / Iodinated Contrast",
                reaction="Generalized flushing and urticaria",
                severity="Moderate",
                status="Active",
                recorded_date=date(2024, 1, 15),
            ),
            MedicalHistoryItem(
                patient_id=p5.id,
                condition_name="Essential Hypertension & Dyslipidemia",
                category="Chronic",
                onset_date=date(2021, 5, 1),
                status="Active",
                notes="Family history of premature CAD in father at age 58.",
            ),
        ]
    )

    add_visit(
        p5,
        doc_internal,
        dt(2025, 6, 12),
        "Emergency",
        "Exertional substernal chest tightness and palpitations while climbing stairs",
        "158/96 mmHg",
        96,
        "36.8",
        98,
        "84.0",
        "Serial Troponin-I negative; initiate Propranolol, Telmisartan, and high-intensity Atorvastatin.",
        [
            ("Chest Pain / Tightness", "Moderate", 1, "20-minute retrosternal heaviness on exertion, relieved by rest"),
            ("Palpitations", "Moderate", 2, "Awareness of rapid heartbeat"),
        ],
        [
            ("Acute Myocardial Infarction", "I21.9", "Ruled-out", "Serial high-sensitivity Troponin-I negative; no ST elevation."),
            ("Stable Angina Pectoris", "I20.8", "Provisional", "Exertional chest tightness; scheduled for stress echo."),
            ("Essential Hypertension", "I10", "Confirmed", "Uncontrolled BP 158/96 mmHg."),
        ],
        [
            ("Telmisartan", "40mg", "1 tablet OD", 90, "Antihypertensive"),
            ("Propranolol", "40mg", "1 tablet BID", 90, "Rate control & anti-anginal"),
            ("Atorvastatin", "20mg", "2 tablets (40mg) HS", 90, "High-intensity lipid lowering"),
        ],
        "S: 53yo male presented with 20 minutes of exertional chest heaviness climbing 3 flights of stairs. O: BP 158/96 mmHg, HR 96 bpm. ECG shows sinus tachycardia with non-specific lateral T-wave flattening; 0-hr and 3-hr hs-Troponin-I negative. A: Acute MI ruled out; Provisional Stable Angina + Uncontrolled Hypertension. P: Start Telmisartan 40mg, Propranolol 40mg BID, Atorvastatin 40mg HS.",
        [
            ("High-Sensitivity Troponin-I", "0.012", "ng/mL", "< 0.040", "Normal", "Negative for acute myocardial necrosis"),
            ("Total Cholesterol", "248", "mg/dL", "< 200", "High", "Dyslipidemia"),
            ("LDL Cholesterol", "164", "mg/dL", "< 100", "High", "Elevated atherogenic lipid fraction"),
        ],
    )

    add_visit(
        p5,
        doc_internal,
        dt(2026, 4, 18),
        "Follow-up",
        "Cardiology & internal medicine follow-up — no recurrent chest pain",
        "124/78 mmHg",
        68,
        "36.6",
        99,
        "80.5",
        "Continue Telmisartan, Propranolol, and Atorvastatin; 3.5 kg weight reduction achieved.",
        [
            ("Fatigue", "Mild", 2, "Occasional mild evening tiredness only"),
        ],
        [
            ("Stable Angina Pectoris", "I20.8", "Controlled", "Asymptomatic on beta-blocker and statin therapy."),
            ("Essential Hypertension", "I10", "Confirmed", "Controlled at 124/78 mmHg."),
        ],
        [
            ("Telmisartan", "40mg", "1 tablet OD", 90, "Continue maintenance"),
            ("Propranolol", "40mg", "1 tablet BID", 90, "Resting HR well controlled at 68 bpm"),
            ("Atorvastatin", "20mg", "2 tablets (40mg) HS", 90, "LDL down to 82 mg/dL"),
        ],
        "S: Patient denies any recurrent chest pain, dyspnea, or palpitations over the past 10 months. Walks 4 km daily. O: BP 124/78, HR 68 bpm. LDL improved from 164 to 82 mg/dL. A: Controlled Hypertension and Stable Angina. P: Continue current cardioprotective regimen.",
        [
            ("LDL Cholesterol", "82", "mg/dL", "< 100", "Normal", "50% LDL reduction achieved on statin"),
            ("Total Cholesterol", "156", "mg/dL", "< 200", "Normal", "Within target range"),
        ],
    )

    # =========================================================================
    # PATIENT 6: Zoya Farooqui (Rheumatoid Arthritis + Methotrexate Monitoring)
    # =========================================================================
    p6 = Patient(
        mrn="MRN-2026-00006",
        first_name="Zoya",
        last_name="Farooqui",
        date_of_birth=date(1990, 12, 11),
        sex="Female",
        blood_group=None,  # Deliberate missing field so AI Data Gaps detector highlights it!
        phone="+91-98106-99760",
        email="zoya.farooqui.demo@synthetic-clinic.org",
        address="Jamia Nagar, Okhla, New Delhi",
        emergency_contact_name="Tariq Farooqui",
        emergency_contact_phone=None,  # Deliberate missing field for AI Data Gaps!
        is_synthetic=True,
        is_active=True,
    )
    db.add(p6)
    db.flush()
    p6.assigned_doctors.append(doc_internal)

    db.add_all(
        [
            MedicalHistoryItem(
                patient_id=p6.id,
                condition_name="Seropositive Rheumatoid Arthritis",
                category="Chronic",
                onset_date=date(2024, 2, 1),
                status="Active",
                notes="Symmetric small-joint polyarthritis of hands and wrists.",
            ),
        ]
    )

    add_visit(
        p6,
        doc_internal,
        dt(2025, 3, 5),
        "OPD",
        "Symmetric morning stiffness >90 minutes and swelling of bilateral wrist and MCP joints",
        "118/76 mmHg",
        80,
        "37.0",
        99,
        "59.0",
        "Initiate weekly Methotrexate 15mg + short-term Naproxen; baseline LFTs normal.",
        [
            ("Joint Pain (Arthralgia)", "Severe", 40, "Bilateral MCP, PIP, and wrist tenderness"),
            ("Morning Stiffness", "Severe", 40, "Lasts nearly 2 hours every morning"),
            ("Fatigue", "Moderate", 30, "Systemic inflammatory fatigue"),
        ],
        [
            ("Seropositive Rheumatoid Arthritis", "M05.79", "Confirmed", "Anti-CCP and Rheumatoid Factor positive."),
        ],
        [
            ("Methotrexate", "15mg", "Once weekly every Sunday morning", 90, "Take Folic Acid 5mg on Wednesday & Friday; avoid alcohol"),
            ("Naproxen", "500mg", "1 tablet BID with meals", 14, "Bridge anti-inflammatory relief"),
            ("Pantoprazole", "40mg", "1 tablet OD", 14, "Gastric protection during NSAID bridge"),
        ],
        "S: 34yo female with 6 weeks of symmetric hand and wrist swelling and prolonged morning stiffness (>90 mins). O: Boggy synovitis of bilateral 2nd/3rd MCP and wrists. Labs: CRP 28 mg/L, ESR 54 mm/hr, Anti-CCP strongly positive. A: Active Seropositive Rheumatoid Arthritis (M05.79). P: Start Methotrexate 15mg once weekly + Naproxen bridge.",
        [
            ("C-Reactive Protein (CRP)", "28.4", "mg/L", "< 5.0", "High", "Marked systemic inflammation"),
            ("Erythrocyte Sedimentation Rate (ESR)", "54", "mm/hr", "0 - 20", "High", "Elevated acute phase reactant"),
            ("ALT (SGPT)", "22", "U/L", "7 - 56", "Normal", "Baseline hepatic transaminase normal"),
        ],
    )

    add_visit(
        p6,
        doc_internal,
        dt(2026, 7, 10),
        "Follow-up",
        "Rheumatology follow-up — joint swelling resolved, morning stiffness <10 minutes",
        "116/74 mmHg",
        74,
        "36.6",
        99,
        "60.0",
        "Continue weekly Methotrexate 15mg; CRP normalized; liver enzymes stable.",
        [
            ("Joint Pain (Arthralgia)", "Mild", 2, "Minimal stiffness only on rainy mornings"),
        ],
        [
            ("Seropositive Rheumatoid Arthritis", "M05.79", "Confirmed", "Low disease activity / clinical remission on Methotrexate."),
        ],
        [
            ("Methotrexate", "15mg", "Once weekly on Sundays", 90, "Continue DMARD maintenance"),
        ],
        "S: Patient reports dramatic improvement in hand grip strength; morning stiffness is under 10 minutes. O: No active synovitis or joint effusion. CRP normalized to 3.1 mg/L, ESR 16 mm/hr, ALT 26 U/L. A: Rheumatoid Arthritis in clinical remission. P: Continue Methotrexate 15mg weekly.",
        [
            ("C-Reactive Protein (CRP)", "3.1", "mg/L", "< 5.0", "Normal", "Normalized from 28.4 mg/L"),
            ("Erythrocyte Sedimentation Rate (ESR)", "16", "mm/hr", "0 - 20", "Normal", "Normalized from 54 mm/hr"),
            ("ALT (SGPT)", "26", "U/L", "7 - 56", "Normal", "No hepatotoxicity on Methotrexate"),
        ],
    )

    # Generated cohort: ~150 more patients across Indian regions and common OPD conditions.
    seed_cohort(
        db,
        meds,
        {"internal": doc_internal, "neuro": doc_neuro, "pulmo": doc_pulmo},
        next_mrn=7,
    )

    db.commit()
    return {
        "status": "seeded",
        "patients": db.query(Patient).count(),
        "visits": db.query(Visit).count(),
    }
