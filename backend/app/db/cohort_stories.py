"""Clinical storylines for the synthetic cohort.

Each storyline is a function that receives a random generator and a patient
context and returns the patient's baseline history plus a dated list of visits.
The courses follow conditions that dominate Indian outpatient practice, and each
one is written so the AI summariser has something real to work with: symptoms
that recur, diagnoses that move from provisional to confirmed (or get ruled out),
and lab values that trend across visits.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from random import Random
from typing import Callable, Dict, List, Optional, Tuple

# Extra drugs added to the catalogue on top of the original sixteen.
EXTRA_MEDICATIONS = [
    ("Paracetamol", "Paracetamol (Acetaminophen)", "Analgesic / Antipyretic", "Tablet", "650mg"),
    ("Azithromycin", "Azithromycin Dihydrate", "Macrolide Antibiotic", "Tablet", "500mg"),
    ("Amoxicillin-Clavulanate", "Amoxicillin 500mg + Clavulanic Acid 125mg", "Penicillin Antibiotic", "Tablet", "625mg"),
    ("Cefixime", "Cefixime Trihydrate", "Third-Generation Cephalosporin", "Tablet", "200mg"),
    ("Ceftriaxone", "Ceftriaxone Sodium", "Third-Generation Cephalosporin", "Injection", "1g"),
    ("Ondansetron", "Ondansetron Hydrochloride", "5-HT3 Antiemetic", "Tablet", "4mg"),
    ("ORS", "Oral Rehydration Salts (WHO low-osmolarity)", "Electrolyte Replacement", "Sachet", "20.5g"),
    ("Zinc Sulfate", "Elemental Zinc", "Mineral Supplement", "Dispersible Tablet", "20mg"),
    ("Insulin Glargine", "Insulin Glargine (Basal Analogue)", "Long-Acting Insulin", "Pen Injection", "100 IU/mL"),
    ("Sitagliptin", "Sitagliptin Phosphate", "DPP-4 Inhibitor", "Tablet", "100mg"),
    ("Empagliflozin", "Empagliflozin", "SGLT2 Inhibitor", "Tablet", "10mg"),
    ("Losartan", "Losartan Potassium", "ARB Antihypertensive", "Tablet", "50mg"),
    ("Chlorthalidone", "Chlorthalidone", "Thiazide-like Diuretic", "Tablet", "12.5mg"),
    ("Aspirin", "Acetylsalicylic Acid (Low Dose)", "Antiplatelet", "Tablet", "75mg"),
    ("Clopidogrel", "Clopidogrel Bisulfate", "P2Y12 Antiplatelet", "Tablet", "75mg"),
    ("Rosuvastatin", "Rosuvastatin Calcium", "HMG-CoA Reductase Inhibitor (Statin)", "Tablet", "20mg"),
    ("Metoprolol", "Metoprolol Succinate (ER)", "Beta-Blocker", "Tablet", "50mg"),
    ("Furosemide", "Furosemide", "Loop Diuretic", "Tablet", "40mg"),
    ("HRZE FDC", "Isoniazid 75 + Rifampicin 150 + Pyrazinamide 400 + Ethambutol 275", "Anti-Tubercular (Intensive Phase)", "Tablet", "4-drug FDC"),
    ("HRE FDC", "Isoniazid 75 + Rifampicin 150 + Ethambutol 275", "Anti-Tubercular (Continuation Phase)", "Tablet", "3-drug FDC"),
    ("Pyridoxine", "Pyridoxine (Vitamin B6)", "Vitamin Supplement", "Tablet", "10mg"),
    ("Artemether-Lumefantrine", "Artemether 80mg + Lumefantrine 480mg", "Antimalarial (ACT)", "Tablet", "80/480mg"),
    ("Chloroquine", "Chloroquine Phosphate", "Antimalarial", "Tablet", "250mg"),
    ("Primaquine", "Primaquine Phosphate", "Antimalarial (Radical Cure)", "Tablet", "7.5mg"),
    ("Escitalopram", "Escitalopram Oxalate", "SSRI Antidepressant", "Tablet", "10mg"),
    ("Clonazepam", "Clonazepam", "Benzodiazepine", "Tablet", "0.25mg"),
    ("Levocetirizine", "Levocetirizine Dihydrochloride", "H1 Antihistamine", "Tablet", "5mg"),
    ("Fluticasone Nasal", "Fluticasone Propionate Nasal Spray", "Intranasal Corticosteroid", "Nasal Spray", "50mcg"),
    ("Cholecalciferol", "Vitamin D3 (Cholecalciferol)", "Vitamin D Supplement", "Sachet", "60,000 IU"),
    ("Calcium + D3", "Calcium Carbonate 500mg + Vitamin D3 250 IU", "Mineral Supplement", "Tablet", "500mg"),
    ("Methylcobalamin", "Methylcobalamin (Vitamin B12)", "Vitamin Supplement", "Tablet", "1500mcg"),
    ("Etoricoxib", "Etoricoxib", "COX-2 Selective NSAID", "Tablet", "60mg"),
    ("Diclofenac Gel", "Diclofenac Diethylamine 1.16%", "Topical NSAID", "Gel", "1.16%"),
    ("Rabeprazole", "Rabeprazole Sodium", "Proton Pump Inhibitor (PPI)", "Tablet", "20mg"),
    ("H. pylori Kit", "Lansoprazole + Amoxicillin + Clarithromycin", "H. pylori Eradication Kit", "Kit", "14-day"),
    ("Domperidone", "Domperidone", "Prokinetic", "Tablet", "10mg"),
    ("Myo-Inositol", "Myo-Inositol 1000mg + Folic Acid 200mcg", "Insulin Sensitiser Supplement", "Sachet", "1g"),
    ("Folic Acid", "Folic Acid", "Vitamin Supplement", "Tablet", "5mg"),
    ("Iron Sucrose", "Iron Sucrose (IV)", "Parenteral Iron", "Injection", "200mg"),
    ("Tiotropium", "Tiotropium Bromide", "LAMA Inhaler", "Rotacap", "18mcg"),
    ("Prednisolone", "Prednisolone", "Systemic Corticosteroid", "Tablet", "20mg"),
    ("Nitrofurantoin", "Nitrofurantoin Monohydrate", "Urinary Antibacterial", "Capsule", "100mg"),
    ("Hydroxychloroquine", "Hydroxychloroquine Sulfate", "DMARD / Antimalarial", "Tablet", "200mg"),
    ("Ursodeoxycholic Acid", "Ursodeoxycholic Acid", "Hepatoprotective Bile Acid", "Tablet", "300mg"),
    ("Sodium Bicarbonate", "Sodium Bicarbonate", "Alkalinising Agent", "Tablet", "500mg"),
    ("Nitroglycerin", "Glyceryl Trinitrate (Sublingual)", "Nitrate Vasodilator", "Tablet", "0.5mg"),
]


@dataclass
class Ctx:
    first_name: str
    sex: str
    age: int
    weight: float
    start: date


@dataclass
class VisitSpec:
    day: int
    vtype: str
    complaint: str
    vitals: Tuple[str, int, str, int, float]  # bp, hr, temp, spo2, weight
    plan: str
    symptoms: List[Tuple[str, str, int, str]]
    diagnoses: List[Tuple[str, str, str, str]]
    rx: List[Tuple[str, str, str, int, str]]
    note: str
    labs: List[Tuple[str, str, str, str, str, str]] = field(default_factory=list)
    note_type: str = "SOAP"


@dataclass
class Story:
    specialty: str
    history: List[Tuple[str, str, Optional[date], str, str]]
    visits: List[VisitSpec]
    allergy: Optional[Tuple[str, str, str]] = None


StoryFn = Callable[[Random, Ctx], Story]


def _who(c: Ctx) -> str:
    noun = "male" if c.sex == "Male" else "female"
    if c.age < 13:
        noun = "boy" if c.sex == "Male" else "girl"
    return f"{c.age}yo {noun}"


def _bp(rng: Random, sys_lo: int, sys_hi: int, dia_lo: int, dia_hi: int) -> str:
    return f"{rng.randint(sys_lo, sys_hi)}/{rng.randint(dia_lo, dia_hi)} mmHg"


def _t(rng: Random, lo: float, hi: float) -> str:
    return f"{rng.uniform(lo, hi):.1f}"


def _w(c: Ctx, delta: float = 0.0) -> float:
    return round(c.weight + delta, 1)


def _r(rng: Random, lo: float, hi: float, nd: int = 1) -> str:
    return f"{rng.uniform(lo, hi):.{nd}f}"


# ---------------------------------------------------------------------------
# Metabolic & cardiovascular
# ---------------------------------------------------------------------------

def diabetes_hypertension(rng: Random, c: Ctx) -> Story:
    a1c = [rng.uniform(8.6, 10.4)]
    a1c.append(a1c[0] - rng.uniform(1.0, 1.8))
    a1c.append(a1c[1] - rng.uniform(0.3, 0.9))
    fbs = [rng.randint(168, 232), rng.randint(128, 150), rng.randint(104, 126)]
    gap1, gap2 = rng.randint(80, 120), rng.randint(170, 260)
    return Story(
        specialty="internal",
        history=[
            ("Type 2 Diabetes Mellitus", "Chronic", c.start - timedelta(days=rng.randint(200, 2400)), "Active",
             "Diagnosed on routine screening; strong family history of diabetes."),
            ("Essential Hypertension", "Chronic", c.start - timedelta(days=rng.randint(100, 1500)), "Active",
             "High-salt diet; works long desk hours."),
            ("Father with Type 2 Diabetes and Coronary Artery Disease", "Family", None, "Historical",
             "Father had a myocardial infarction at 58."),
        ],
        visits=[
            VisitSpec(
                0, "OPD", "Increased thirst, frequent urination at night and tiredness for two months",
                (_bp(rng, 146, 162, 90, 98), rng.randint(82, 92), _t(rng, 36.6, 37.0), 98, _w(c)),
                "Start Metformin and Telmisartan; diabetic diet counselling with dietician; review with HbA1c in 3 months.",
                [("Polyuria", "Moderate", 60, "Wakes 3-4 times a night to pass urine"),
                 ("Polydipsia", "Moderate", 60, "Drinks 4-5 litres of water a day"),
                 ("Fatigue", "Moderate", 45, "Unable to finish workday without rest")],
                [("Type 2 Diabetes Mellitus without complications", "E11.9", "Confirmed", "HbA1c well above target."),
                 ("Essential Hypertension", "I10", "Confirmed", "Stage 2 on two separate readings.")],
                [("Metformin", "500mg", "1 tablet twice daily after meals", 90, "Increase to 1g BID after 2 weeks if tolerated"),
                 ("Telmisartan", "40mg", "1 tablet once daily in the morning", 90, "Check BP at home twice weekly")],
                f"S: {_who(c)} with two months of polyuria, polydipsia and fatigue. Eats rice-heavy meals and sweets daily. "
                f"O: BP elevated, BMI raised, no foot ulcers, monofilament sensation intact. "
                f"A: Type 2 DM (E11.9) with Stage 2 essential hypertension (I10). "
                f"P: Metformin 500mg BID, Telmisartan 40mg OD, diet and walking 30 minutes daily.",
                [("HbA1c", f"{a1c[0]:.1f}", "%", "4.0 - 5.6", "High", "Poor glycaemic control"),
                 ("Fasting Blood Sugar", str(fbs[0]), "mg/dL", "70 - 100", "High", "Hyperglycaemia"),
                 ("Serum Creatinine", _r(rng, 0.8, 1.1, 2), "mg/dL", "0.6 - 1.2", "Normal", "Baseline renal function"),
                 ("LDL Cholesterol", str(rng.randint(132, 168)), "mg/dL", "< 100", "High", "Needs statin consideration")],
            ),
            VisitSpec(
                gap1, "Follow-up", "Diabetes and blood pressure review; tingling in both feet",
                (_bp(rng, 134, 142, 84, 88), rng.randint(76, 84), _t(rng, 36.5, 36.9), 98, _w(c, -2.0)),
                "Increase Metformin to 1g BID; add Atorvastatin; foot care education; add B12 cover.",
                [("Tingling in Feet", "Mild", 20, "Pins and needles in both soles at night"),
                 ("Fatigue", "Mild", 20, "Energy improved since diet change")],
                [("Type 2 Diabetes Mellitus without complications", "E11.9", "Controlled", "HbA1c falling but above target."),
                 ("Essential Hypertension", "I10", "Controlled", "Improving on ARB.")],
                [("Metformin", "500mg", "2 tablets twice daily after meals", 90, "Dose increased"),
                 ("Telmisartan", "40mg", "1 tablet once daily", 90, "Continue"),
                 ("Atorvastatin", "20mg", "1 tablet at bedtime", 90, "For LDL reduction"),
                 ("Methylcobalamin", "1500mcg", "1 tablet once daily", 60, "Long-term Metformin can lower B12")],
                f"S: Improved thirst; lost 2 kg. New night-time tingling in both feet. "
                f"O: BP better; vibration sense mildly reduced at great toes. "
                f"A: T2DM improving; early sensory symptoms, neuropathy not yet confirmed. "
                f"P: Metformin up-titrated, statin started, B12 supplement.",
                [("HbA1c", f"{a1c[1]:.1f}", "%", "4.0 - 5.6", "High", "Improving trend"),
                 ("Fasting Blood Sugar", str(fbs[1]), "mg/dL", "70 - 100", "High", "Improving"),
                 ("Serum Vitamin B12", str(rng.randint(160, 210)), "pg/mL", "200 - 900", "Low", "Borderline low on Metformin")],
            ),
            VisitSpec(
                gap1 + gap2, "Follow-up", "Six-month diabetes review",
                (_bp(rng, 124, 132, 78, 84), rng.randint(70, 78), _t(rng, 36.5, 36.8), 99, _w(c, -3.5)),
                "Continue current regimen; annual eye and kidney screening; review in 6 months.",
                [("Tingling in Feet", "Mild", 5, "Much less frequent")],
                [("Type 2 Diabetes Mellitus without complications", "E11.9", "Controlled", "Near target HbA1c."),
                 ("Essential Hypertension", "I10", "Controlled", "At target.")],
                [("Metformin", "500mg", "2 tablets twice daily", 180, "Continue"),
                 ("Telmisartan", "40mg", "1 tablet once daily", 180, "Continue"),
                 ("Atorvastatin", "20mg", "1 tablet at bedtime", 180, "Continue")],
                f"S: Walking daily, diet adherence good. Tingling much less. "
                f"O: BP at target. Fundus examination by ophthalmology: no diabetic retinopathy. "
                f"A: T2DM and hypertension controlled. "
                f"P: Continue regimen; urine microalbumin and lipids next visit.",
                [("HbA1c", f"{a1c[2]:.1f}", "%", "4.0 - 5.6", "High" if a1c[2] > 6.5 else "Normal", "Close to individual target"),
                 ("Fasting Blood Sugar", str(fbs[2]), "mg/dL", "70 - 100", "High" if fbs[2] > 110 else "Normal", ""),
                 ("LDL Cholesterol", str(rng.randint(78, 98)), "mg/dL", "< 100", "Normal", "At target on statin"),
                 ("Urine Albumin-Creatinine Ratio", str(rng.randint(12, 26)), "mg/g", "< 30", "Normal", "No nephropathy")],
            ),
        ],
    )


def hypertension_only(rng: Random, c: Ctx) -> Story:
    gap = rng.randint(30, 60)
    return Story(
        specialty="cardio",
        history=[("Essential Hypertension", "Chronic", c.start - timedelta(days=rng.randint(30, 900)), "Active",
                  "Home readings consistently above 140/90.")],
        visits=[
            VisitSpec(
                0, "OPD", "Morning headache and high BP readings on home machine",
                (_bp(rng, 150, 168, 94, 104), rng.randint(80, 90), _t(rng, 36.6, 37.0), 98, _w(c)),
                "Start Amlodipine; reduce salt to under 5 g/day; recheck in 4-6 weeks.",
                [("Headache", "Mild", 14, "Occipital, worse on waking"),
                 ("Dizziness", "Mild", 7, "On standing quickly")],
                [("Essential Hypertension", "I10", "Confirmed", "Stage 2 on repeat readings.")],
                [("Amlodipine", "5mg", "1 tablet once daily", 30, "May cause ankle swelling")],
                f"S: {_who(c)}, home BP 150s/90s for two weeks, morning occipital headache. Adds extra salt and pickle to meals. "
                f"O: BP elevated in both arms; fundus shows mild arteriolar narrowing. "
                f"A: Stage 2 essential hypertension (I10). P: Amlodipine 5mg OD, DASH diet, sodium restriction.",
                [("Serum Sodium", str(rng.randint(136, 142)), "mEq/L", "135 - 145", "Normal", ""),
                 ("Serum Potassium", _r(rng, 3.8, 4.6), "mEq/L", "3.5 - 5.1", "Normal", ""),
                 ("Resting ECG (12-Lead)", "Sinus rhythm, LVH voltage criteria borderline", "", "Normal", "Abnormal", "Echo advised")],
            ),
            VisitSpec(
                gap, "Follow-up", "Blood pressure review; mild ankle swelling",
                (_bp(rng, 132, 140, 82, 88), rng.randint(72, 80), _t(rng, 36.5, 36.8), 99, _w(c, -1.0)),
                "Add Telmisartan; continue Amlodipine; review in 3 months.",
                [("Ankle Swelling", "Mild", 10, "Pitting, evening only"),
                 ("Headache", "Mild", 2, "Rare now")],
                [("Essential Hypertension", "I10", "Controlled", "Improving; not yet at target.")],
                [("Amlodipine", "5mg", "1 tablet once daily", 90, "Continue"),
                 ("Telmisartan", "40mg", "1 tablet once daily", 90, "Added for target BP")],
                "S: Headaches settled. Evening ankle swelling. O: BP improved but above 130/80. "
                "A: Hypertension improving; amlodipine-related pedal oedema. P: Add ARB.",
                [("2D Echocardiography", "Mild concentric LVH, EF 60%", "", "EF 55-70%", "Abnormal", "Hypertensive heart changes")],
            ),
        ],
    )


def coronary_artery_disease(rng: Random, c: Ctx) -> Story:
    ef1, ef2 = rng.randint(38, 44), rng.randint(46, 52)
    return Story(
        specialty="cardio",
        history=[("Tobacco Use (Bidi / Cigarettes)", "Past Illness", c.start - timedelta(days=9000), "Historical",
                  "Smoked 15 a day for 20 years; quit after the heart attack."),
                 ("Dyslipidaemia", "Chronic", c.start - timedelta(days=600), "Active", "Never treated before the event.")],
        visits=[
            VisitSpec(
                0, "Emergency", "Crushing central chest pain radiating to left arm for 2 hours with sweating",
                (_bp(rng, 92, 104, 60, 68), rng.randint(104, 118), _t(rng, 36.6, 37.0), rng.randint(92, 95), _w(c)),
                "Primary PCI to LAD done in cath lab; dual antiplatelet therapy, high-intensity statin, beta-blocker; cardiac rehab.",
                [("Chest Pain", "Severe", 1, "Retrosternal pressure, 9/10, radiating to left arm"),
                 ("Sweating (Diaphoresis)", "Severe", 1, "Profuse cold sweat"),
                 ("Breathlessness", "Moderate", 1, "Unable to lie flat")],
                [("Acute Anterior Wall ST-Elevation Myocardial Infarction", "I21.09", "Confirmed", "ST elevation V1-V4; LAD culprit.")],
                [("Aspirin", "75mg", "1 tablet once daily after lunch", 365, "Lifelong unless told otherwise"),
                 ("Clopidogrel", "75mg", "1 tablet once daily", 365, "Do not stop without cardiologist advice"),
                 ("Rosuvastatin", "20mg", "1 tablet at bedtime", 365, "High-intensity statin"),
                 ("Metoprolol", "50mg", "1 tablet once daily", 365, "Hold if pulse below 55"),
                 ("Nitroglycerin", "0.5mg", "1 tablet under the tongue for chest pain, may repeat after 5 min", 90, "Call ambulance if pain persists")],
                f"S: {_who(c)}, smoker, brought by family to emergency with 2 hours of crushing chest pain. "
                f"O: Diaphoretic, BP low-normal, tachycardic. ECG: ST elevation V1-V4. Troponin I markedly raised. "
                f"A: Acute anterior STEMI (I21.09). P: Loaded with aspirin and clopidogrel, primary PCI with drug-eluting stent to proximal LAD.",
                [("Troponin I (High Sensitivity)", str(rng.randint(4800, 12500)), "ng/L", "< 26", "Critical", "Acute myocardial injury"),
                 ("2D Echocardiography", f"Anterior wall hypokinesia, EF {ef1}%", "", "EF 55-70%", "Abnormal", "Reduced LV function"),
                 ("LDL Cholesterol", str(rng.randint(150, 190)), "mg/dL", "< 55 (post-MI)", "High", "")],
            ),
            VisitSpec(
                rng.randint(28, 40), "Follow-up", "Post-angioplasty review; breathless on climbing two floors",
                (_bp(rng, 112, 122, 70, 78), rng.randint(62, 70), _t(rng, 36.5, 36.8), 97, _w(c, -2.5)),
                "Continue all cardiac medicines; enrol in cardiac rehabilitation; strict tobacco abstinence.",
                [("Breathlessness", "Mild", 20, "On climbing two floors"),
                 ("Chest Pain", "Mild", 3, "Brief twinges at rest, not exertional")],
                [("Old Myocardial Infarction", "I25.2", "Confirmed", "Post-PCI, stable."),
                 ("Unstable Angina", "I20.0", "Ruled-out", "Twinges are atypical; ECG unchanged, troponin normal.")],
                [("Aspirin", "75mg", "1 tablet once daily", 365, ""),
                 ("Clopidogrel", "75mg", "1 tablet once daily", 335, ""),
                 ("Rosuvastatin", "20mg", "1 tablet at bedtime", 365, ""),
                 ("Metoprolol", "50mg", "1 tablet once daily", 365, "")],
                "S: Mild exertional breathlessness, short non-exertional twinges. Not smoking. O: Heart rate controlled, chest clear. "
                "A: Stable post-MI; recurrent ischaemia ruled out. P: Cardiac rehab, continue DAPT.",
                [("Troponin I (High Sensitivity)", str(rng.randint(6, 18)), "ng/L", "< 26", "Normal", "No new injury")],
            ),
            VisitSpec(
                rng.randint(200, 260), "Follow-up", "Six-month cardiology review; walking 4 km daily",
                (_bp(rng, 116, 124, 72, 78), rng.randint(58, 66), _t(rng, 36.4, 36.7), 98, _w(c, -5.0)),
                "Continue secondary prevention; repeat lipid profile in 3 months.",
                [("Breathlessness", "Mild", 2, "Only on brisk uphill walking")],
                [("Old Myocardial Infarction", "I25.2", "Confirmed", "LV function recovering.")],
                [("Aspirin", "75mg", "1 tablet once daily", 365, ""),
                 ("Rosuvastatin", "20mg", "1 tablet at bedtime", 365, ""),
                 ("Metoprolol", "50mg", "1 tablet once daily", 365, "")],
                "S: Completed cardiac rehab. Walks 4 km daily, no angina. O: Euvolaemic. "
                "A: Recovering LV function post-STEMI. P: Continue; clopidogrel course nearing completion.",
                [("2D Echocardiography", f"Improved anterior wall motion, EF {ef2}%", "", "EF 55-70%", "Abnormal", "Improving"),
                 ("LDL Cholesterol", str(rng.randint(48, 66)), "mg/dL", "< 55 (post-MI)", "Normal", "Near target")],
            ),
        ],
    )


def ckd_diabetic(rng: Random, c: Ctx) -> Story:
    cr = [rng.uniform(1.7, 2.0), rng.uniform(2.0, 2.3), rng.uniform(2.0, 2.2)]
    egfr = [rng.randint(36, 42), rng.randint(30, 35), rng.randint(31, 35)]
    return Story(
        specialty="nephro",
        history=[("Type 2 Diabetes Mellitus", "Chronic", c.start - timedelta(days=rng.randint(3600, 6500)), "Active",
                  "Long-standing diabetes with irregular follow-up."),
                 ("Chronic Kidney Disease", "Chronic", c.start - timedelta(days=rng.randint(90, 400)), "Active",
                  "Diabetic nephropathy suspected on proteinuria.")],
        visits=[
            VisitSpec(
                0, "OPD", "Swelling of feet and puffy face in the mornings",
                (_bp(rng, 148, 160, 88, 96), rng.randint(78, 86), _t(rng, 36.5, 36.9), 97, _w(c, 2.0)),
                "Start Losartan and Empagliflozin; low-salt, moderate-protein diet; avoid painkillers (NSAIDs).",
                [("Pedal Oedema", "Moderate", 30, "Pitting up to mid-shin"),
                 ("Facial Puffiness", "Mild", 20, "Worse on waking"),
                 ("Foamy Urine", "Mild", 60, "Noticed by patient")],
                [("Chronic Kidney Disease, Stage 3b", "N18.32", "Confirmed", "eGFR in 30-44 range."),
                 ("Type 2 Diabetes Mellitus with Diabetic Nephropathy", "E11.21", "Confirmed", "Albuminuria present.")],
                [("Losartan", "50mg", "1 tablet once daily", 90, "Kidney protection; recheck potassium in 2 weeks"),
                 ("Empagliflozin", "10mg", "1 tablet once daily in the morning", 90, "Drink adequate water; watch for genital infection"),
                 ("Furosemide", "40mg", "1 tablet in the morning", 14, "For swelling; stop if dizzy")],
                f"S: {_who(c)} with 1 month of leg swelling and morning facial puffiness. Takes over-the-counter painkillers for knee pain. "
                f"O: Bilateral pitting oedema. BP raised. USG kidneys: bilaterally echogenic, normal size. "
                f"A: CKD stage 3b (N18.32) from diabetic nephropathy (E11.21). P: ARB plus SGLT2 inhibitor, stop NSAIDs.",
                [("Serum Creatinine", f"{cr[0]:.2f}", "mg/dL", "0.6 - 1.2", "High", "Reduced clearance"),
                 ("eGFR (CKD-EPI)", str(egfr[0]), "mL/min/1.73m2", "> 90", "Low", "Stage 3b"),
                 ("Urine Albumin-Creatinine Ratio", str(rng.randint(420, 880)), "mg/g", "< 30", "High", "Severely increased albuminuria"),
                 ("Haemoglobin", _r(rng, 9.8, 10.8), "g/dL", "12.0 - 16.0", "Low", "Anaemia of CKD")],
            ),
            VisitSpec(
                rng.randint(14, 21), "Follow-up", "Two-week safety check after starting Losartan",
                (_bp(rng, 132, 140, 80, 86), rng.randint(74, 80), _t(rng, 36.5, 36.8), 98, _w(c, -0.5)),
                "Expected small creatinine rise after ARB; continue; stop Furosemide.",
                [("Pedal Oedema", "Mild", 7, "Reduced to ankles")],
                [("Chronic Kidney Disease, Stage 3b", "N18.32", "Confirmed", "Acceptable post-ARB creatinine rise (<30%).")],
                [("Losartan", "50mg", "1 tablet once daily", 90, "Continue"),
                 ("Empagliflozin", "10mg", "1 tablet once daily", 90, "Continue")],
                "S: Swelling better. O: Oedema at ankles only. A: Haemodynamic creatinine rise within expected range. "
                "P: Continue ARB and SGLT2i; potassium acceptable.",
                [("Serum Creatinine", f"{cr[1]:.2f}", "mg/dL", "0.6 - 1.2", "High", "Expected rise after ARB"),
                 ("eGFR (CKD-EPI)", str(egfr[1]), "mL/min/1.73m2", "> 90", "Low", ""),
                 ("Serum Potassium", _r(rng, 4.9, 5.3), "mEq/L", "3.5 - 5.1", "High", "Mild hyperkalaemia; low-potassium diet")],
            ),
            VisitSpec(
                rng.randint(150, 200), "Follow-up", "Kidney clinic review",
                (_bp(rng, 126, 134, 76, 82), rng.randint(70, 78), _t(rng, 36.4, 36.8), 98, _w(c, -1.5)),
                "Stable kidney function; continue; IV iron for anaemia; review in 3 months.",
                [("Fatigue", "Moderate", 30, "Tired in afternoons")],
                [("Chronic Kidney Disease, Stage 3b", "N18.32", "Controlled", "Stable eGFR, proteinuria halved."),
                 ("Anaemia in Chronic Kidney Disease", "D63.1", "Confirmed", "Iron deficient.")],
                [("Losartan", "50mg", "1 tablet once daily", 90, ""),
                 ("Empagliflozin", "10mg", "1 tablet once daily", 90, ""),
                 ("Iron Sucrose", "200mg", "IV infusion weekly x 5 doses", 35, "Given in day-care")],
                "S: Fatigue in afternoons. O: Pallor. A: Stable CKD 3b; iron-deficient anaemia of CKD. P: IV iron sucrose course.",
                [("Serum Creatinine", f"{cr[2]:.2f}", "mg/dL", "0.6 - 1.2", "High", "Stable"),
                 ("eGFR (CKD-EPI)", str(egfr[2]), "mL/min/1.73m2", "> 90", "Low", "Stable"),
                 ("Urine Albumin-Creatinine Ratio", str(rng.randint(180, 320)), "mg/g", "< 30", "High", "Reduced on ARB + SGLT2i"),
                 ("Serum Ferritin", str(rng.randint(38, 70)), "ng/mL", "100 - 500 (CKD target)", "Low", "Iron deficiency")],
            ),
        ],
    )


def nafld(rng: Random, c: Ctx) -> Story:
    alt = [rng.randint(84, 120), rng.randint(42, 58)]
    return Story(
        specialty="gastro",
        history=[("Obesity (BMI over 30)", "Chronic", c.start - timedelta(days=2000), "Active", "Sedentary job, frequent outside food.")],
        visits=[
            VisitSpec(
                0, "OPD", "Heaviness in right upper abdomen and raised liver enzymes on office health check",
                (_bp(rng, 128, 138, 82, 88), rng.randint(76, 84), _t(rng, 36.5, 36.9), 98, _w(c, 8.0)),
                "Weight loss of 7-10% over 6 months; avoid alcohol; Ursodeoxycholic acid; repeat LFT in 3 months.",
                [("Abdominal Discomfort", "Mild", 60, "Dull heaviness, right upper quadrant, after meals")],
                [("Non-Alcoholic Fatty Liver Disease", "K76.0", "Confirmed", "Grade II fatty liver on ultrasound."),
                 ("Viral Hepatitis B", "B18.1", "Ruled-out", "HBsAg negative.")],
                [("Ursodeoxycholic Acid", "300mg", "1 tablet twice daily", 90, ""),
                 ("Cholecalciferol", "60,000 IU", "1 sachet once a week with milk", 56, "8 weeks")],
                f"S: {_who(c)}, IT professional, right upper abdominal heaviness. Drinks socially once a month. "
                f"O: Central obesity, liver span mildly increased. USG: Grade II fatty liver. "
                f"A: NAFLD (K76.0); hepatitis B ruled out. P: Lifestyle change, UDCA, vitamin D.",
                [("ALT (SGPT)", str(alt[0]), "U/L", "7 - 56", "High", "Hepatocellular pattern"),
                 ("HBsAg", "Non-reactive", "", "Non-reactive", "Normal", ""),
                 ("Serum Vitamin D (25-OH)", _r(rng, 11, 19), "ng/mL", "30.0 - 100.0", "Low", "Deficient"),
                 ("Triglycerides", str(rng.randint(210, 290)), "mg/dL", "< 150", "High", "")],
            ),
            VisitSpec(
                rng.randint(100, 140), "Follow-up", "Fatty liver review after weight loss",
                (_bp(rng, 118, 126, 76, 82), rng.randint(70, 78), _t(rng, 36.5, 36.8), 99, _w(c, 2.5)),
                "Continue lifestyle changes; stop UDCA; annual liver ultrasound.",
                [("Abdominal Discomfort", "Mild", 3, "Rare")],
                [("Non-Alcoholic Fatty Liver Disease", "K76.0", "Controlled", "Enzymes improving with 6% weight loss.")],
                [("Cholecalciferol", "60,000 IU", "1 sachet once a month", 90, "Maintenance")],
                "S: Lost 5.5 kg with home-cooked meals and evening walks. O: Weight down. A: NAFLD improving. P: Continue.",
                [("ALT (SGPT)", str(alt[1]), "U/L", "7 - 56", "Normal" if alt[1] <= 56 else "High", "Improved"),
                 ("Triglycerides", str(rng.randint(140, 170)), "mg/dL", "< 150", "High", "Improving")],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Infectious disease (tropical & seasonal)
# ---------------------------------------------------------------------------

def tuberculosis(rng: Random, c: Ctx) -> Story:
    w0 = _w(c, -6.0)
    return Story(
        specialty="pulmo",
        history=[("Household Contact with Pulmonary TB", "Family", None, "Historical", "Uncle treated for TB two years ago.")],
        visits=[
            VisitSpec(
                0, "OPD", "Cough for more than 3 weeks with evening fever, night sweats and weight loss",
                (_bp(rng, 104, 116, 66, 74), rng.randint(96, 108), _t(rng, 37.8, 38.4), rng.randint(94, 96), w0),
                "Notify on Ni-kshay; start daily HRZE fixed-dose combination for 8 weeks (intensive phase); Pyridoxine; nutrition support under Ni-kshay Poshan Yojana.",
                [("Productive Cough", "Severe", 28, "Yellowish sputum, occasionally blood-streaked"),
                 ("Evening Fever", "Moderate", 21, "Low-grade rise every evening"),
                 ("Night Sweats", "Moderate", 21, "Drenching sweats"),
                 ("Weight Loss", "Moderate", 60, "Lost about 6 kg in 2 months")],
                [("Pulmonary Tuberculosis, Microbiologically Confirmed", "A15.0", "Confirmed", "CBNAAT MTB detected, rifampicin sensitive."),
                 ("Community-Acquired Pneumonia", "J18.9", "Ruled-out", "Chronic course and CBNAAT result favour TB.")],
                [("HRZE FDC", "4 tablets", "4 tablets once daily on empty stomach", 56, "Weight-band dosing; urine may turn orange"),
                 ("Pyridoxine", "10mg", "1 tablet once daily", 180, "Prevents isoniazid neuropathy")],
                f"S: {_who(c)} with productive cough for 4 weeks, evening fevers, night sweats and 6 kg weight loss. "
                f"O: Febrile, thin build, crepitations right upper zone. CXR: right upper lobe infiltrates with cavitation. "
                f"A: Microbiologically confirmed pulmonary TB, drug sensitive (A15.0). "
                f"P: HRZE daily x 8 weeks, notified on Ni-kshay, family contact screening.",
                [("Sputum CBNAAT (GeneXpert)", "MTB Detected, Rifampicin Resistance Not Detected", "", "Not detected", "Abnormal", "Drug-sensitive TB"),
                 ("Chest X-Ray PA View", "Right upper lobe infiltrates with 2 cm cavity", "", "Clear lung fields", "Abnormal", ""),
                 ("ESR", str(rng.randint(62, 96)), "mm/hr", "0 - 20", "High", ""),
                 ("HIV 1 & 2 Antibody", "Non-reactive", "", "Non-reactive", "Normal", "Routine screening for TB patients"),
                 ("ALT (SGPT)", str(rng.randint(20, 34)), "U/L", "7 - 56", "Normal", "Baseline before ATT")],
            ),
            VisitSpec(
                rng.randint(56, 62), "Follow-up", "End of intensive phase review",
                (_bp(rng, 110, 118, 70, 76), rng.randint(80, 88), _t(rng, 36.6, 37.0), 97, _w(c, -3.0)),
                "Sputum converted; switch to HRE continuation phase for 16 weeks.",
                [("Productive Cough", "Mild", 7, "Occasional morning cough"),
                 ("Nausea", "Mild", 10, "After morning doses")],
                [("Pulmonary Tuberculosis, Microbiologically Confirmed", "A15.0", "Confirmed", "Sputum smear converted to negative.")],
                [("HRE FDC", "4 tablets", "4 tablets once daily", 112, "Continuation phase"),
                 ("Pyridoxine", "10mg", "1 tablet once daily", 112, ""),
                 ("Ondansetron", "4mg", "1 tablet 30 min before ATT if nauseous", 10, "")],
                "S: Fever and sweats gone, gained 3 kg. Mild nausea after medicines. O: Afebrile, fewer crepitations. "
                "A: Good response; sputum converted. P: Continuation phase HRE.",
                [("Sputum Smear for AFB", "Negative", "", "Negative", "Normal", "Sputum conversion"),
                 ("ALT (SGPT)", str(rng.randint(38, 52)), "U/L", "7 - 56", "Normal", "No drug-induced hepatitis")],
            ),
            VisitSpec(
                rng.randint(170, 185), "Follow-up", "Treatment completion visit",
                (_bp(rng, 112, 120, 72, 78), rng.randint(72, 80), _t(rng, 36.5, 36.8), 98, _w(c, 1.0)),
                "Declared cured; follow-up at 6, 12 and 24 months for relapse.",
                [],
                [("Pulmonary Tuberculosis", "A15.0", "Resolved", "Cured: smear negative at end of treatment.")],
                [],
                "S: Asymptomatic, weight regained. O: Chest clear. CXR: fibrotic strands right upper zone, no cavity. "
                "A: Pulmonary TB, treatment outcome cured. P: Post-treatment follow-up schedule.",
                [("Sputum Smear for AFB", "Negative", "", "Negative", "Normal", "End-of-treatment"),
                 ("Chest X-Ray PA View", "Healed fibrotic strands, no cavity", "", "Clear lung fields", "Abnormal", "Residual scarring")],
                note_type="Discharge",
            ),
        ],
    )


def dengue(rng: Random, c: Ctx) -> Story:
    plt = [rng.randint(68, 92), rng.randint(24, 42), rng.randint(110, 165)]
    return Story(
        specialty="internal",
        history=[],
        visits=[
            VisitSpec(
                0, "Emergency", "High fever for 3 days with severe body ache and pain behind the eyes",
                (_bp(rng, 102, 112, 64, 70), rng.randint(102, 112), _t(rng, 38.9, 39.8), 98, _w(c)),
                "Admit for monitoring; oral and IV fluids; Paracetamol only; avoid NSAIDs; platelet count every 12 hours.",
                [("High Fever", "Severe", 3, "Up to 103 F, with chills"),
                 ("Retro-orbital Pain", "Moderate", 2, "Pain on moving eyes"),
                 ("Myalgia", "Severe", 3, "Severe body ache, 'break-bone' pain"),
                 ("Rash", "Mild", 1, "Blanching erythema on forearms")],
                [("Dengue Fever with Warning Signs", "A97.1", "Confirmed", "NS1 antigen positive, falling platelets."),
                 ("Malaria", "B54", "Ruled-out", "Rapid malaria antigen test negative.")],
                [("Paracetamol", "650mg", "1 tablet every 6 hours if fever (max 4 g/day)", 5, "Do not take Ibuprofen or Aspirin"),
                 ("ORS", "1 sachet in 1 L water", "Sip through the day, target 2.5-3 L fluids", 5, "")],
                f"S: {_who(c)} with 3 days of high fever, severe myalgia and retro-orbital pain during monsoon; neighbour also had dengue. "
                f"O: Febrile, tachycardic, tourniquet test positive, mild hepatomegaly. "
                f"A: Dengue with warning signs (A97.1); malaria ruled out. P: Admit, fluids, strict NSAID avoidance, serial platelets and haematocrit.",
                [("Dengue NS1 Antigen", "Positive", "", "Negative", "Abnormal", "Acute dengue infection"),
                 ("Platelet Count", f"{plt[0]},000", "/uL", "150,000 - 450,000", "Low", "Thrombocytopenia"),
                 ("Haematocrit", str(rng.randint(44, 48)), "%", "36 - 46", "High", "Haemoconcentration"),
                 ("Malaria Rapid Antigen (Pf/Pv)", "Negative", "", "Negative", "Normal", "")],
            ),
            VisitSpec(
                2, "Follow-up", "Inpatient day 3: fever settled, gum bleeding while brushing",
                (_bp(rng, 98, 106, 62, 68), rng.randint(88, 96), _t(rng, 36.8, 37.3), 98, _w(c, -0.8)),
                "Critical phase: continue IV fluids; watch for bleeding and abdominal pain; no platelet transfusion unless active bleeding.",
                [("Gum Bleeding", "Mild", 1, "Minor bleeding while brushing"),
                 ("Fatigue", "Severe", 5, "Bed-bound")],
                [("Dengue Fever with Warning Signs", "A97.1", "Confirmed", "Critical phase; platelet nadir.")],
                [("Paracetamol", "650mg", "1 tablet SOS for fever", 3, "")],
                "S: Defervescence, gum bleeding on brushing. O: Haemodynamically stable, no ascites. "
                "A: Dengue critical phase with platelet nadir. P: Fluids, monitor, transfusion not indicated.",
                [("Platelet Count", f"{plt[1]},000", "/uL", "150,000 - 450,000", "Critical", "Nadir; monitor every 12 hours"),
                 ("Haematocrit", str(rng.randint(42, 45)), "%", "36 - 46", "Normal", "")],
                note_type="Progress",
            ),
            VisitSpec(
                9, "Follow-up", "Post-discharge review after dengue",
                (_bp(rng, 110, 118, 70, 76), rng.randint(74, 82), _t(rng, 36.5, 36.8), 99, _w(c, -1.5)),
                "Recovered; gradual return to work; balanced diet.",
                [("Fatigue", "Mild", 7, "Improving daily")],
                [("Dengue Fever with Warning Signs", "A97.1", "Resolved", "Platelets recovered.")],
                [],
                "S: Weak but eating well. O: No bleeding, no rash. A: Recovered dengue. P: No further tests needed.",
                [("Platelet Count", f"{plt[2]},000", "/uL", "150,000 - 450,000", "Low" if plt[2] < 150 else "Normal", "Recovered")],
            ),
        ],
    )


def typhoid(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="internal",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Fever for 7 days rising step-by-step with headache and loss of appetite",
                (_bp(rng, 104, 114, 64, 72), rng.randint(84, 92), _t(rng, 38.8, 39.4), 98, _w(c, -1.0)),
                "Oral Cefixime for 14 days; boiled or filtered water only; review after blood culture report.",
                [("Fever", "Severe", 7, "Step-ladder pattern, highest in evening"),
                 ("Headache", "Moderate", 6, "Frontal, dull"),
                 ("Loss of Appetite", "Moderate", 6, ""),
                 ("Abdominal Discomfort", "Mild", 4, "Vague, periumbilical")],
                [("Enteric Fever (Typhoid)", "A01.00", "Provisional", "Relative bradycardia, coated tongue; culture awaited."),
                 ("Dengue Fever", "A97.9", "Ruled-out", "NS1 and IgM negative.")],
                [("Cefixime", "200mg", "1 tablet twice daily after food", 14, "Complete full course even after fever settles"),
                 ("Paracetamol", "650mg", "1 tablet SOS for fever over 100 F", 7, "")],
                f"S: {_who(c)} with 7 days of step-ladder fever, headache and anorexia. Ate street food (pani puri) the week before. "
                f"O: Febrile with relative bradycardia, coated tongue, soft splenomegaly. "
                f"A: Provisional enteric fever (A01.00); dengue excluded. P: Empirical Cefixime, blood culture sent.",
                [("Blood Culture", "Salmonella Typhi isolated, sensitive to Ceftriaxone and Cefixime, resistant to Ciprofloxacin", "", "No growth", "Abnormal", "Confirms enteric fever"),
                 ("Dengue NS1 Antigen", "Negative", "", "Negative", "Normal", ""),
                 ("Total Leucocyte Count", str(rng.randint(3400, 4200)), "/uL", "4000 - 11000", "Low", "Leucopenia")],
            ),
            VisitSpec(
                rng.randint(9, 12), "Follow-up", "Typhoid follow-up; fever settled on day 5 of antibiotics",
                (_bp(rng, 110, 118, 70, 76), rng.randint(72, 80), _t(rng, 36.6, 36.9), 99, _w(c, -2.0)),
                "Complete Cefixime course; light diet; return if fever recurs.",
                [("Fatigue", "Mild", 10, "Recovering")],
                [("Enteric Fever (Typhoid)", "A01.00", "Confirmed", "Culture-proven, responding to Cefixime.")],
                [("Cefixime", "200mg", "1 tablet twice daily", 4, "Finish remaining course")],
                "S: Afebrile since day 5. Appetite returning. O: Spleen no longer palpable. "
                "A: Culture-confirmed typhoid, ciprofloxacin-resistant strain, good response. P: Complete 14 days.",
                [],
            ),
        ],
    )


def malaria_vivax(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="internal",
        history=[],
        visits=[
            VisitSpec(
                0, "Emergency", "Fever with shaking chills every alternate day for 6 days",
                (_bp(rng, 100, 110, 62, 70), rng.randint(100, 110), _t(rng, 39.2, 40.0), 97, _w(c)),
                "Chloroquine for 3 days followed by Primaquine for 14 days after G6PD test; mosquito net and repellent.",
                [("Fever with Chills", "Severe", 6, "Rigors followed by sweating, alternate days"),
                 ("Headache", "Moderate", 5, ""),
                 ("Myalgia", "Moderate", 5, "")],
                [("Plasmodium vivax Malaria", "B51.9", "Confirmed", "Ring forms and trophozoites on peripheral smear.")],
                [("Chloroquine", "250mg", "4 tablets day 1-2, 2 tablets day 3", 3, "Take after food"),
                 ("Paracetamol", "650mg", "1 tablet SOS for fever", 5, "")],
                f"S: {_who(c)} with tertian fever with rigors for 6 days; construction site near stagnant water. "
                f"O: Febrile, pallor, mild splenomegaly. "
                f"A: P. vivax malaria (B51.9). P: Chloroquine, then Primaquine radical cure after G6PD screen.",
                [("Peripheral Smear for Malaria Parasite", "P. vivax trophozoites seen", "", "No parasites seen", "Abnormal", ""),
                 ("G6PD Screening", "Normal activity", "", "Normal", "Normal", "Safe to give Primaquine"),
                 ("Platelet Count", f"{rng.randint(96, 128)},000", "/uL", "150,000 - 450,000", "Low", "")],
            ),
            VisitSpec(
                rng.randint(4, 6), "Follow-up", "Malaria follow-up; no fever for 2 days",
                (_bp(rng, 110, 116, 70, 74), rng.randint(76, 84), _t(rng, 36.6, 37.0), 98, _w(c, -1.0)),
                "Start Primaquine for 14 days to prevent relapse.",
                [("Fatigue", "Mild", 5, "")],
                [("Plasmodium vivax Malaria", "B51.9", "Resolved", "Smear negative after chloroquine.")],
                [("Primaquine", "7.5mg", "2 tablets once daily", 14, "Radical cure; report dark urine immediately")],
                "S: Afebrile. O: Smear negative. A: Clinical and parasitological cure. P: Primaquine 0.25 mg/kg x 14 days.",
                [("Peripheral Smear for Malaria Parasite", "No parasites seen", "", "No parasites seen", "Normal", "")],
            ),
        ],
    )


def chikungunya(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="rheum",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Sudden high fever with severe pain in wrists, ankles and fingers",
                (_bp(rng, 112, 124, 72, 80), rng.randint(96, 104), _t(rng, 38.8, 39.4), 98, _w(c)),
                "Paracetamol and rest; NSAIDs only after dengue excluded; cold compresses for joints.",
                [("High Fever", "Severe", 2, ""),
                 ("Joint Pain (Arthralgia)", "Severe", 2, "Symmetric wrists, ankles, small joints of hands; can't hold a cup"),
                 ("Rash", "Mild", 1, "Maculopapular rash over trunk")],
                [("Chikungunya Virus Disease", "A92.0", "Confirmed", "Chikungunya IgM positive."),
                 ("Dengue Fever", "A97.9", "Ruled-out", "NS1 negative.")],
                [("Paracetamol", "650mg", "1 tablet every 6-8 hours", 7, "")],
                f"S: {_who(c)} with abrupt fever and incapacitating small-joint pain; local outbreak in colony. "
                f"O: Febrile, swelling of both wrists and ankles. A: Chikungunya (A92.0), dengue excluded. P: Symptomatic care.",
                [("Chikungunya IgM (ELISA)", "Positive", "", "Negative", "Abnormal", ""),
                 ("Dengue NS1 Antigen", "Negative", "", "Negative", "Normal", "")],
            ),
            VisitSpec(
                rng.randint(40, 70), "Follow-up", "Persistent joint pain and morning stiffness 2 months after chikungunya",
                (_bp(rng, 116, 124, 74, 80), rng.randint(72, 80), _t(rng, 36.5, 36.9), 99, _w(c, -1.0)),
                "Short NSAID course then Hydroxychloroquine for post-chikungunya arthritis; physiotherapy.",
                [("Joint Pain (Arthralgia)", "Moderate", 60, "Fingers and ankles"),
                 ("Morning Stiffness", "Moderate", 45, "Lasts about 45 minutes")],
                [("Post-Chikungunya Chronic Inflammatory Arthritis", "M02.80", "Confirmed", "Rheumatoid factor and anti-CCP negative."),
                 ("Seropositive Rheumatoid Arthritis", "M05.79", "Ruled-out", "Serology negative.")],
                [("Etoricoxib", "60mg", "1 tablet once daily after food", 14, ""),
                 ("Hydroxychloroquine", "200mg", "1 tablet twice daily", 90, "Annual eye check if continued long term")],
                "S: Persistent small-joint pain and stiffness after chikungunya. O: Mild wrist synovitis. "
                "A: Post-chikungunya arthritis; RA excluded on serology. P: HCQ, NSAID bridge, physiotherapy.",
                [("Rheumatoid Factor", "Negative", "", "Negative", "Normal", ""),
                 ("Anti-CCP Antibody", str(rng.randint(2, 8)), "U/mL", "< 17", "Normal", ""),
                 ("C-Reactive Protein (CRP)", _r(rng, 9, 16), "mg/L", "< 5.0", "High", "")],
            ),
        ],
    )


def gastroenteritis_child(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="paeds",
        history=[("Immunisation Up to Date (UIP Schedule)", "Past Illness", None, "Historical", "Includes rotavirus vaccine.")],
        visits=[
            VisitSpec(
                0, "Emergency", "Loose watery stools 8-10 times since yesterday with vomiting",
                (_bp(rng, 90, 98, 56, 62), rng.randint(118, 132), _t(rng, 37.8, 38.4), 98, _w(c, -0.6)),
                "Some dehydration: ORS 75 mL/kg over 4 hours under observation, then Zinc for 14 days; continue feeding.",
                [("Diarrhoea", "Severe", 1, "Watery, no blood, 8-10 episodes"),
                 ("Vomiting", "Moderate", 1, "4 episodes"),
                 ("Low-Grade Fever", "Mild", 1, "")],
                [("Acute Gastroenteritis with Some Dehydration", "A09", "Confirmed", "Sunken eyes, drinks eagerly."),
                 ("Cholera", "A00.9", "Ruled-out", "No rice-water stools; stool culture negative.")],
                [("ORS", "1 sachet in 1 L water", "75 mL/kg over 4 hours, then after each loose stool", 5, "Mother taught preparation"),
                 ("Zinc Sulfate", "20mg", "1 tablet dissolved in water once daily", 14, ""),
                 ("Ondansetron", "4mg", "Half tablet once if vomiting", 1, "")],
                f"S: {_who(c)} brought by mother with watery diarrhoea and vomiting since yesterday; family attended a wedding feast. "
                f"O: Irritable, sunken eyes, skin pinch goes back slowly. A: Acute gastroenteritis with some dehydration (A09). "
                f"P: ORS plan B, Zinc, continue breastfeeding/feeding.",
                [("Serum Sodium", str(rng.randint(132, 136)), "mEq/L", "135 - 145", "Low", "Mild hyponatraemia"),
                 ("Stool Routine", "Watery, no RBC, few pus cells", "", "No pus cells", "Abnormal", "")],
            ),
            VisitSpec(
                3, "Follow-up", "Diarrhoea follow-up; stools reducing",
                (_bp(rng, 94, 100, 58, 64), rng.randint(96, 108), _t(rng, 36.6, 37.0), 99, _w(c)),
                "Complete Zinc course; hand hygiene; boiled water.",
                [("Diarrhoea", "Mild", 3, "Down to 2 soft stools a day")],
                [("Acute Gastroenteritis", "A09", "Resolved", "Rehydrated.")],
                [("Zinc Sulfate", "20mg", "1 tablet once daily", 11, "Complete 14 days")],
                "S: Playing, eating. O: Well hydrated. A: Resolved AGE. P: Finish zinc.",
                [],
            ),
        ],
    )


def recurrent_tonsillitis_child(rng: Random, c: Ctx) -> Story:
    gap = rng.randint(70, 140)
    return Story(
        specialty="paeds",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Sore throat, fever and difficulty swallowing for 2 days",
                (_bp(rng, 92, 100, 58, 64), rng.randint(104, 116), _t(rng, 38.4, 39.0), 98, _w(c)),
                "Amoxicillin-Clavulanate for 7 days; warm saline gargles; Paracetamol for fever.",
                [("Sore Throat", "Severe", 2, "Pain on swallowing"),
                 ("Fever", "Moderate", 2, "")],
                [("Acute Tonsillitis", "J03.90", "Confirmed", "Exudative tonsils, tender neck nodes.")],
                [("Amoxicillin-Clavulanate", "625mg", "Weight-based syrup equivalent twice daily", 7, "Complete course"),
                 ("Paracetamol", "650mg", "Weight-based syrup SOS", 3, "")],
                f"S: {_who(c)} with sore throat and fever for 2 days. O: Enlarged exudative tonsils, tender jugulodigastric nodes. "
                f"A: Acute bacterial tonsillitis (J03.90). P: Co-amoxiclav x 7 days.",
                [],
            ),
            VisitSpec(
                gap, "OPD", "Third episode of throat infection this year",
                (_bp(rng, 92, 100, 58, 64), rng.randint(100, 112), _t(rng, 38.2, 38.8), 98, _w(c, 0.5)),
                "Antibiotics; refer to ENT for opinion on tonsillectomy if episodes continue (Paradise criteria).",
                [("Sore Throat", "Severe", 3, "Recurring"),
                 ("Fever", "Moderate", 2, "")],
                [("Recurrent Acute Tonsillitis", "J03.91", "Confirmed", "3 episodes in 12 months.")],
                [("Azithromycin", "500mg", "Weight-based syrup once daily", 5, ""),
                 ("Paracetamol", "650mg", "Weight-based syrup SOS", 3, "")],
                "S: Recurrent sore throat, third episode in a year; missed school. O: Hypertrophied tonsils with exudate. "
                "A: Recurrent tonsillitis (J03.91). P: Azithromycin, ENT referral.",
                [("Antistreptolysin O (ASO) Titre", str(rng.randint(260, 420)), "IU/mL", "< 200", "High", "Recent streptococcal infection")],
            ),
        ],
    )


def uti_female(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="internal",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Burning while passing urine and frequent urge for 3 days",
                (_bp(rng, 110, 122, 70, 78), rng.randint(84, 92), _t(rng, 37.4, 37.9), 99, _w(c)),
                "Nitrofurantoin for 5 days; drink 2.5-3 litres water; urine culture.",
                [("Dysuria", "Moderate", 3, "Burning sensation"),
                 ("Urinary Frequency", "Moderate", 3, "Every hour"),
                 ("Lower Abdominal Pain", "Mild", 2, "Suprapubic")],
                [("Acute Cystitis", "N30.00", "Confirmed", "Uncomplicated lower UTI."),
                 ("Acute Pyelonephritis", "N10", "Ruled-out", "No flank pain or high fever.")],
                [("Nitrofurantoin", "100mg", "1 capsule twice daily with food", 5, "")],
                f"S: {_who(c)} with dysuria and frequency for 3 days; reduced water intake during summer travel. "
                f"O: Suprapubic tenderness, no renal angle tenderness. A: Uncomplicated cystitis (N30.00). P: Nitrofurantoin.",
                [("Urine Routine", "Pus cells 25-30/hpf, nitrite positive", "", "0-5 pus cells/hpf", "Abnormal", ""),
                 ("Urine Culture", "E. coli >10^5 CFU/mL, sensitive to Nitrofurantoin", "", "No growth", "Abnormal", "")],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Endocrine, women's health, nutrition
# ---------------------------------------------------------------------------

def hypothyroidism(rng: Random, c: Ctx) -> Story:
    tsh = [rng.uniform(11.5, 18.0), rng.uniform(5.2, 7.0), rng.uniform(1.6, 3.4)]
    return Story(
        specialty="endo",
        history=[("Mother with Hypothyroidism", "Family", None, "Historical", "On levothyroxine for 15 years.")],
        visits=[
            VisitSpec(
                0, "OPD", "Weight gain, hair fall, feeling cold and constipation for 4 months",
                (_bp(rng, 118, 128, 78, 84), rng.randint(58, 64), _t(rng, 36.2, 36.5), 99, _w(c, 4.0)),
                "Start Levothyroxine 50 mcg on empty stomach; recheck TSH in 6 weeks.",
                [("Weight Gain", "Moderate", 120, "Gained 5 kg without diet change"),
                 ("Hair Fall", "Moderate", 90, ""),
                 ("Cold Intolerance", "Mild", 90, ""),
                 ("Fatigue", "Moderate", 120, "Sleeps 10 hours, still tired")],
                [("Primary Hypothyroidism (Hashimoto Thyroiditis)", "E06.3", "Confirmed", "High TSH, positive anti-TPO.")],
                [("Levothyroxine", "50mcg", "1 tablet at 6 AM on empty stomach, 30 min before tea", 45, "Do not take with calcium or iron")],
                f"S: {_who(c)} with 4 months of weight gain, hair fall, cold intolerance, constipation. "
                f"O: Dry skin, delayed ankle reflexes, mild diffuse goitre. A: Hashimoto hypothyroidism (E06.3). P: Levothyroxine 50 mcg.",
                [("TSH", f"{tsh[0]:.2f}", "uIU/mL", "0.4 - 4.5", "High", "Overt hypothyroidism"),
                 ("Free T4", _r(rng, 0.5, 0.7, 2), "ng/dL", "0.8 - 1.8", "Low", ""),
                 ("Anti-TPO Antibody", str(rng.randint(180, 620)), "IU/mL", "< 35", "High", "Autoimmune thyroiditis"),
                 ("Total Cholesterol", str(rng.randint(222, 256)), "mg/dL", "< 200", "High", "Secondary to hypothyroidism")],
            ),
            VisitSpec(
                rng.randint(42, 50), "Follow-up", "Thyroid review at 6 weeks",
                (_bp(rng, 116, 124, 76, 80), rng.randint(64, 70), _t(rng, 36.4, 36.7), 99, _w(c, 2.5)),
                "Increase Levothyroxine to 75 mcg; recheck in 6 weeks.",
                [("Fatigue", "Mild", 40, "Better")],
                [("Primary Hypothyroidism (Hashimoto Thyroiditis)", "E06.3", "Confirmed", "TSH still above range.")],
                [("Levothyroxine", "75mcg", "1 tablet at 6 AM on empty stomach", 90, "Dose increased")],
                "S: More energy, less hair fall. O: Reflexes normalising. A: Under-replaced. P: Increase to 75 mcg.",
                [("TSH", f"{tsh[1]:.2f}", "uIU/mL", "0.4 - 4.5", "High", "Improving")],
            ),
            VisitSpec(
                rng.randint(130, 160), "Follow-up", "Thyroid review on 75 mcg",
                (_bp(rng, 112, 120, 72, 78), rng.randint(68, 74), _t(rng, 36.5, 36.8), 99, _w(c, 0.5)),
                "Euthyroid; continue 75 mcg; TSH every 6-12 months.",
                [],
                [("Primary Hypothyroidism (Hashimoto Thyroiditis)", "E06.3", "Controlled", "Euthyroid on replacement.")],
                [("Levothyroxine", "75mcg", "1 tablet at 6 AM on empty stomach", 180, "")],
                "S: Asymptomatic. O: Weight back to baseline. A: Controlled hypothyroidism. P: Continue.",
                [("TSH", f"{tsh[2]:.2f}", "uIU/mL", "0.4 - 4.5", "Normal", "At target"),
                 ("Total Cholesterol", str(rng.randint(172, 194)), "mg/dL", "< 200", "Normal", "Normalised")],
            ),
        ],
    )


def pcos(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="obgyn",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Irregular periods every 45-60 days, acne and weight gain",
                (_bp(rng, 112, 122, 72, 80), rng.randint(76, 84), _t(rng, 36.5, 36.8), 99, _w(c, 6.0)),
                "Lifestyle modification; Metformin; Myo-inositol; review cycles in 3 months.",
                [("Irregular Menstrual Cycles", "Moderate", 365, "Cycles every 45-60 days"),
                 ("Acne", "Moderate", 180, "Jawline and chin"),
                 ("Excess Facial Hair (Hirsutism)", "Mild", 365, "Upper lip and chin"),
                 ("Weight Gain", "Moderate", 365, "Gained 7 kg in a year")],
                [("Polycystic Ovary Syndrome", "E28.2", "Confirmed", "Rotterdam criteria: oligo-ovulation + polycystic ovaries on USG."),
                 ("Primary Hypothyroidism", "E03.9", "Ruled-out", "TSH normal.")],
                [("Metformin", "500mg", "1 tablet twice daily after meals", 90, ""),
                 ("Myo-Inositol", "1g", "1 sachet twice daily", 90, "")],
                f"S: {_who(c)}, student, with oligomenorrhoea, acne and weight gain over a year. "
                f"O: BMI 27, acanthosis nigricans on neck, mild hirsutism (mFG 10). USG: bilateral polycystic ovarian morphology. "
                f"A: PCOS (E28.2); thyroid cause excluded. P: Diet and exercise, Metformin, Myo-inositol.",
                [("TSH", _r(rng, 1.4, 3.2, 2), "uIU/mL", "0.4 - 4.5", "Normal", ""),
                 ("LH:FSH Ratio", _r(rng, 2.3, 3.1), "", "< 2", "High", "Suggestive of PCOS"),
                 ("Fasting Insulin", str(rng.randint(18, 28)), "uIU/mL", "2 - 12", "High", "Insulin resistance"),
                 ("USG Pelvis", "Bilateral ovaries with >20 peripheral follicles each", "", "Normal ovaries", "Abnormal", "")],
            ),
            VisitSpec(
                rng.randint(100, 130), "Follow-up", "PCOS review after 3 months of lifestyle change",
                (_bp(rng, 110, 118, 70, 76), rng.randint(72, 78), _t(rng, 36.5, 36.8), 99, _w(c, 3.0)),
                "Continue Metformin; periods regularising; continue exercise.",
                [("Irregular Menstrual Cycles", "Mild", 90, "Last two cycles at 34 and 36 days"),
                 ("Acne", "Mild", 60, "Improving")],
                [("Polycystic Ovary Syndrome", "E28.2", "Controlled", "Cycles improving with 4% weight loss.")],
                [("Metformin", "500mg", "1 tablet twice daily", 90, "")],
                "S: Joined yoga classes, lost 3 kg, cycles more regular. O: Acne reduced. A: PCOS improving. P: Continue.",
                [],
            ),
        ],
    )


def anaemia_women(rng: Random, c: Ctx) -> Story:
    hb = [rng.uniform(7.8, 9.0), rng.uniform(10.2, 11.0), rng.uniform(11.8, 12.8)]
    return Story(
        specialty="internal",
        history=[("Heavy Menstrual Bleeding", "Chronic", c.start - timedelta(days=700), "Active", "Uses 6-7 pads a day for first 3 days.")],
        visits=[
            VisitSpec(
                0, "OPD", "Breathless on climbing stairs, extreme tiredness and dizziness",
                (_bp(rng, 100, 110, 62, 70), rng.randint(96, 106), _t(rng, 36.5, 36.8), 98, _w(c)),
                "Oral iron with Vitamin C; deworming; iron-rich diet (jaggery, green leafy vegetables, rajma); gynaecology review for heavy periods.",
                [("Fatigue", "Severe", 90, "Cannot complete household work"),
                 ("Breathlessness", "Moderate", 30, "On climbing one floor"),
                 ("Dizziness", "Mild", 30, "On standing")],
                [("Iron Deficiency Anaemia", "D50.0", "Confirmed", "Microcytic hypochromic, low ferritin; secondary to menorrhagia.")],
                [("Ferrous Ascorbate", "100mg", "1 tablet once daily, 1 hour before lunch", 90, "Stools may turn black"),
                 ("Folic Acid", "5mg", "1 tablet once daily", 90, "")],
                f"S: {_who(c)} with 3 months of fatigue and exertional breathlessness; vegetarian diet; heavy periods. "
                f"O: Marked pallor, koilonychia, tachycardia, soft flow murmur. "
                f"A: Iron deficiency anaemia (D50.0) due to menorrhagia and low dietary iron. P: Oral iron, folate, Albendazole single dose.",
                [("Haemoglobin", f"{hb[0]:.1f}", "g/dL", "12.0 - 15.5", "Low", "Moderate anaemia"),
                 ("MCV", str(rng.randint(64, 72)), "fL", "80 - 100", "Low", "Microcytosis"),
                 ("Serum Ferritin", str(rng.randint(4, 9)), "ng/mL", "15 - 150", "Low", "Depleted iron stores"),
                 ("Peripheral Smear", "Microcytic hypochromic RBCs with pencil cells", "", "Normocytic normochromic", "Abnormal", "")],
            ),
            VisitSpec(
                rng.randint(40, 50), "Follow-up", "Anaemia review after 6 weeks of iron",
                (_bp(rng, 106, 114, 68, 74), rng.randint(84, 90), _t(rng, 36.5, 36.8), 99, _w(c, 0.5)),
                "Good response; continue iron for 3 more months to refill stores.",
                [("Fatigue", "Mild", 40, "Much better")],
                [("Iron Deficiency Anaemia", "D50.0", "Confirmed", "Responding to oral iron.")],
                [("Ferrous Ascorbate", "100mg", "1 tablet once daily", 90, "")],
                "S: Energy improved. O: Less pallor. A: Good haematological response. P: Continue iron.",
                [("Haemoglobin", f"{hb[1]:.1f}", "g/dL", "12.0 - 15.5", "Low", "Rising ~2 g/dL"),
                 ("Reticulocyte Count", _r(rng, 2.4, 3.6), "%", "0.5 - 2.5", "High", "Marrow response to iron")],
            ),
            VisitSpec(
                rng.randint(130, 160), "Follow-up", "Anaemia review at 4 months",
                (_bp(rng, 110, 118, 70, 76), rng.randint(74, 80), _t(rng, 36.5, 36.8), 99, _w(c, 1.0)),
                "Haemoglobin normal; stop iron after one more month; gynaecology managing menorrhagia.",
                [],
                [("Iron Deficiency Anaemia", "D50.0", "Resolved", "Haemoglobin and ferritin normalised.")],
                [],
                "S: No symptoms. O: No pallor. A: Corrected IDA. P: Stop iron next month.",
                [("Haemoglobin", f"{hb[2]:.1f}", "g/dL", "12.0 - 15.5", "Normal", "Normalised"),
                 ("Serum Ferritin", str(rng.randint(32, 48)), "ng/mL", "15 - 150", "Normal", "Stores refilled")],
            ),
        ],
    )


def gestational_diabetes(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="obgyn",
        history=[("First Pregnancy (Primigravida)", "Past Illness", c.start - timedelta(days=150), "Active", "Singleton pregnancy, regular antenatal care.")],
        visits=[
            VisitSpec(
                0, "OPD", "Routine antenatal visit at 24 weeks; glucose tolerance test",
                (_bp(rng, 110, 118, 70, 76), rng.randint(84, 92), _t(rng, 36.6, 36.9), 99, _w(c, 7.0)),
                "Medical nutrition therapy; home glucose monitoring 4 times a day; review in 2 weeks.",
                [("Fatigue", "Mild", 30, "Normal for pregnancy")],
                [("Gestational Diabetes Mellitus", "O24.410", "Confirmed", "DIPSI 75 g OGTT 2-hour value above 140 mg/dL.")],
                [("Calcium + D3", "500mg", "1 tablet twice daily", 90, "Antenatal supplement"),
                 ("Ferrous Ascorbate", "100mg", "1 tablet once daily", 90, "Antenatal iron")],
                f"S: {_who(c)}, primigravida at 24 weeks, routine antenatal visit. "
                f"O: Fundal height matches dates, fetal heart 144/min. "
                f"A: Gestational diabetes (O24.410) on DIPSI screening. P: Diet therapy, SMBG, dietician referral.",
                [("OGTT 2-hour (DIPSI, 75 g)", str(rng.randint(152, 178)), "mg/dL", "< 140", "High", "Diagnostic of GDM"),
                 ("Haemoglobin", _r(rng, 10.6, 11.4), "g/dL", "11.0 - 14.0", "Normal", "")],
            ),
            VisitSpec(
                rng.randint(14, 18), "Follow-up", "GDM review; post-meal sugars still high on diet alone",
                (_bp(rng, 112, 120, 72, 78), rng.randint(86, 92), _t(rng, 36.6, 36.9), 99, _w(c, 7.5)),
                "Start Metformin (safe in pregnancy); continue diet; growth scan at 32 weeks.",
                [],
                [("Gestational Diabetes Mellitus", "O24.410", "Confirmed", "Post-prandial values above 120 mg/dL on diet.")],
                [("Metformin", "500mg", "1 tablet twice daily after meals", 90, "Continue until delivery")],
                "S: Following diet, walks after dinner. O: Home log shows PPBS 130-150. A: GDM not controlled on MNT. P: Metformin.",
                [("Post-Prandial Blood Sugar", str(rng.randint(134, 152)), "mg/dL", "< 120 (pregnancy)", "High", "")],
            ),
            VisitSpec(
                rng.randint(60, 70), "Follow-up", "Antenatal visit at 34 weeks",
                (_bp(rng, 114, 122, 74, 80), rng.randint(86, 94), _t(rng, 36.6, 36.9), 99, _w(c, 10.0)),
                "Sugars controlled; plan delivery at 38-39 weeks; postpartum OGTT at 6-12 weeks.",
                [],
                [("Gestational Diabetes Mellitus", "O24.410", "Controlled", "Controlled on Metformin.")],
                [("Metformin", "500mg", "1 tablet twice daily", 35, "")],
                "S: Good fetal movements. O: Growth scan: fetal weight 50th centile, liquor normal. A: Controlled GDM. P: Delivery planning.",
                [("Post-Prandial Blood Sugar", str(rng.randint(104, 118)), "mg/dL", "< 120 (pregnancy)", "Normal", "")],
            ),
        ],
    )


def vitamin_deficiency(rng: Random, c: Ctx) -> Story:
    vd = [rng.uniform(8.0, 14.0), rng.uniform(32.0, 44.0)]
    return Story(
        specialty="internal",
        history=[("Lacto-Vegetarian Diet", "Chronic", None, "Active", "No eggs, fish or meat.")],
        visits=[
            VisitSpec(
                0, "OPD", "Body ache, leg cramps and numbness in hands and feet",
                (_bp(rng, 116, 124, 74, 80), rng.randint(72, 80), _t(rng, 36.5, 36.8), 99, _w(c)),
                "Weekly Vitamin D3 60,000 IU for 8 weeks; Methylcobalamin; morning sunlight 20 minutes.",
                [("Body Ache (Generalised)", "Moderate", 90, "Diffuse, worse in legs"),
                 ("Leg Cramps", "Moderate", 60, "At night"),
                 ("Numbness in Hands and Feet", "Mild", 45, "Glove-and-stocking")],
                [("Vitamin D Deficiency", "E55.9", "Confirmed", ""),
                 ("Vitamin B12 Deficiency", "E53.8", "Confirmed", "Dietary, vegetarian.")],
                [("Cholecalciferol", "60,000 IU", "1 sachet weekly with milk", 56, ""),
                 ("Methylcobalamin", "1500mcg", "1 tablet once daily", 90, ""),
                 ("Calcium + D3", "500mg", "1 tablet once daily after dinner", 90, "")],
                f"S: {_who(c)}, office worker, mostly indoors, vegetarian, with diffuse body ache and paraesthesia. "
                f"O: Proximal muscle tenderness, reduced vibration sense at toes. "
                f"A: Vitamin D (E55.9) and B12 (E53.8) deficiency. P: Supplementation, sun exposure.",
                [("Serum Vitamin D (25-OH)", f"{vd[0]:.1f}", "ng/mL", "30.0 - 100.0", "Low", "Deficient"),
                 ("Serum Vitamin B12", str(rng.randint(110, 170)), "pg/mL", "200 - 900", "Low", "Deficient"),
                 ("Serum Calcium", _r(rng, 8.4, 8.9), "mg/dL", "8.5 - 10.5", "Normal", "")],
            ),
            VisitSpec(
                rng.randint(80, 110), "Follow-up", "Vitamin levels review",
                (_bp(rng, 114, 122, 72, 78), rng.randint(70, 76), _t(rng, 36.5, 36.8), 99, _w(c)),
                "Levels corrected; monthly maintenance Vitamin D; continue B12 for 3 months.",
                [("Body Ache (Generalised)", "Mild", 10, "Mostly resolved")],
                [("Vitamin D Deficiency", "E55.9", "Resolved", "Repleted."),
                 ("Vitamin B12 Deficiency", "E53.8", "Controlled", "")],
                [("Cholecalciferol", "60,000 IU", "1 sachet monthly", 180, "Maintenance"),
                 ("Methylcobalamin", "1500mcg", "1 tablet once daily", 90, "")],
                "S: Cramps and aches settled. O: Vibration sense improved. A: Deficiencies corrected. P: Maintenance.",
                [("Serum Vitamin D (25-OH)", f"{vd[1]:.1f}", "ng/mL", "30.0 - 100.0", "Normal", "Repleted"),
                 ("Serum Vitamin B12", str(rng.randint(380, 560)), "pg/mL", "200 - 900", "Normal", "")],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Respiratory, musculoskeletal, GI, mental health
# ---------------------------------------------------------------------------

def asthma_rhinitis(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="pulmo",
        history=[("Allergic Rhinitis", "Chronic", c.start - timedelta(days=rng.randint(1500, 4000)), "Active",
                  "Worse in October-November during crop-stubble smoke season.")],
        visits=[
            VisitSpec(
                0, "OPD", "Wheezing and night-time cough during winter smog",
                (_bp(rng, 112, 122, 72, 78), rng.randint(90, 100), _t(rng, 36.6, 37.0), rng.randint(93, 95), _w(c)),
                "Start Budesonide-Formoterol inhaler; Salbutamol rescue; spacer technique taught; N95 mask on high AQI days.",
                [("Wheezing", "Moderate", 14, "Night and early morning"),
                 ("Dry Cough", "Moderate", 21, "Wakes from sleep"),
                 ("Sneezing", "Mild", 30, "Morning bouts")],
                [("Moderate Persistent Asthma", "J45.40", "Confirmed", "Reversible obstruction on spirometry."),
                 ("Allergic Rhinitis", "J30.9", "Confirmed", "")],
                [("Budesonide+Formoterol", "200/6mcg", "2 puffs twice daily", 90, "Rinse mouth after use"),
                 ("Salbutamol", "100mcg", "2 puffs SOS for wheeze", 90, "Tell doctor if needed more than twice a week"),
                 ("Levocetirizine", "5mg", "1 tablet at bedtime", 30, "")],
                f"S: {_who(c)} with night cough and wheeze since Diwali; city AQI above 400. "
                f"O: Bilateral polyphonic wheeze, SpO2 mildly reduced. "
                f"A: Moderate persistent asthma (J45.40) with allergic rhinitis. P: ICS-LABA maintenance, SABA rescue.",
                [("Spirometry (FEV1, % predicted)", str(rng.randint(64, 72)), "%", "> 80", "Low", "Post-bronchodilator improvement 16%"),
                 ("Absolute Eosinophil Count", str(rng.randint(520, 760)), "/uL", "40 - 440", "High", "Allergic phenotype")],
            ),
            VisitSpec(
                rng.randint(60, 90), "Follow-up", "Asthma control review",
                (_bp(rng, 112, 120, 72, 76), rng.randint(76, 84), _t(rng, 36.5, 36.8), 98, _w(c)),
                "Well controlled; continue; nasal steroid for rhinitis.",
                [("Sneezing", "Mild", 14, "Occasional")],
                [("Moderate Persistent Asthma", "J45.40", "Controlled", "No night symptoms in 4 weeks.")],
                [("Budesonide+Formoterol", "200/6mcg", "2 puffs twice daily", 90, ""),
                 ("Fluticasone Nasal", "50mcg", "2 sprays each nostril once daily", 60, "")],
                "S: No night waking, rescue inhaler used once in a month. O: Chest clear. A: Asthma controlled. P: Continue.",
                [("Spirometry (FEV1, % predicted)", str(rng.randint(84, 92)), "%", "> 80", "Normal", "")],
            ),
        ],
    )


def copd_biomass(rng: Random, c: Ctx) -> Story:
    smoke = "cooking on a chulha with wood and dung cakes for 30 years" if c.sex == "Female" else "smoking bidis for 35 years"
    return Story(
        specialty="pulmo",
        history=[("Chronic Smoke Exposure", "Past Illness", None, "Historical", f"History of {smoke}.")],
        visits=[
            VisitSpec(
                0, "OPD", "Breathlessness on walking and cough with sputum every winter for 4 years",
                (_bp(rng, 128, 138, 80, 86), rng.randint(90, 100), _t(rng, 36.6, 37.0), rng.randint(90, 93), _w(c, -3.0)),
                "Start Tiotropium; pulmonary rehabilitation; influenza and pneumococcal vaccination; switch to LPG (Ujjwala) / quit smoking.",
                [("Breathlessness", "Moderate", 1400, "mMRC grade 2"),
                 ("Productive Cough", "Moderate", 120, "White sputum, worse in mornings")],
                [("Chronic Obstructive Pulmonary Disease", "J44.9", "Confirmed", "Post-bronchodilator FEV1/FVC < 0.70."),
                 ("Bronchial Asthma", "J45.909", "Ruled-out", "No significant reversibility.")],
                [("Tiotropium", "18mcg", "1 rotacap inhaled once daily", 90, "Use rotahaler, do not swallow"),
                 ("Salbutamol", "100mcg", "2 puffs SOS", 90, "")],
                f"S: {_who(c)} with progressive exertional breathlessness and winter cough; {smoke}. "
                f"O: Barrel chest, prolonged expiration, scattered rhonchi. "
                f"A: COPD (J44.9), GOLD group B; asthma ruled out. P: LAMA, rehab, vaccines, smoke cessation.",
                [("Spirometry FEV1/FVC (post-bronchodilator)", _r(rng, 0.52, 0.62, 2), "", "> 0.70", "Low", "Fixed obstruction"),
                 ("Chest X-Ray PA View", "Hyperinflated lungs, flattened diaphragm", "", "Normal", "Abnormal", "")],
            ),
            VisitSpec(
                rng.randint(90, 160), "Emergency", "Increased breathlessness and yellow-green sputum for 3 days",
                (_bp(rng, 132, 142, 82, 88), rng.randint(104, 114), _t(rng, 37.8, 38.4), rng.randint(86, 89), _w(c, -4.0)),
                "Nebulised bronchodilators, oral Prednisolone 5 days, Amoxicillin-Clavulanate, controlled oxygen to SpO2 88-92%.",
                [("Breathlessness", "Severe", 3, "Breathless while talking"),
                 ("Productive Cough", "Severe", 3, "Purulent sputum"),
                 ("Fever", "Mild", 2, "")],
                [("COPD with Acute Exacerbation", "J44.1", "Confirmed", "Infective trigger.")],
                [("Prednisolone", "20mg", "2 tablets once daily after breakfast", 5, ""),
                 ("Amoxicillin-Clavulanate", "625mg", "1 tablet three times daily", 5, ""),
                 ("Tiotropium", "18mcg", "1 rotacap once daily", 90, "")],
                "S: 3 days of worsening dyspnoea and purulent sputum after a cold. O: Tachypnoeic, SpO2 87% on room air, wheeze. "
                "A: Infective acute exacerbation of COPD (J44.1). P: Steroids, antibiotics, controlled O2.",
                [("Arterial Blood Gas pCO2", str(rng.randint(46, 52)), "mmHg", "35 - 45", "High", "Mild hypercapnia, compensated"),
                 ("Total Leucocyte Count", str(rng.randint(12800, 15600)), "/uL", "4000 - 11000", "High", "")],
            ),
        ],
    )


def knee_osteoarthritis(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="ortho",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Pain in both knees on climbing stairs and sitting cross-legged",
                (_bp(rng, 128, 140, 80, 86), rng.randint(72, 80), _t(rng, 36.5, 36.8), 98, _w(c, 5.0)),
                "Quadriceps strengthening; weight reduction; topical Diclofenac; avoid squatting and floor sitting.",
                [("Knee Pain", "Moderate", 365, "Bilateral, worse on stairs and after sitting"),
                 ("Morning Stiffness", "Mild", 180, "Less than 20 minutes"),
                 ("Crepitus", "Mild", 180, "Grating sound on bending")],
                [("Bilateral Primary Osteoarthritis of Knee", "M17.0", "Confirmed", "Kellgren-Lawrence grade II-III.")],
                [("Diclofenac Gel", "1.16%", "Apply to both knees three times daily", 30, ""),
                 ("Calcium + D3", "500mg", "1 tablet once daily", 90, ""),
                 ("Paracetamol", "650mg", "1 tablet SOS for pain (max 3/day)", 30, "")],
                f"S: {_who(c)} with bilateral knee pain for a year; difficulty in Indian-style toilet and sitting for prayers. "
                f"O: Crepitus, medial joint-line tenderness, no effusion. X-ray: medial joint-space narrowing, osteophytes. "
                f"A: Bilateral knee OA (M17.0). P: Physiotherapy, topical NSAID, weight loss.",
                [("X-Ray Both Knees (Standing AP)", "Medial joint space narrowing with marginal osteophytes, KL grade II-III", "", "Normal", "Abnormal", ""),
                 ("Serum Uric Acid", _r(rng, 5.0, 6.6), "mg/dL", "3.5 - 7.2", "Normal", "Gout unlikely")],
            ),
            VisitSpec(
                rng.randint(80, 130), "Follow-up", "Knee pain flare after a pilgrimage trip with long walks",
                (_bp(rng, 130, 138, 80, 84), rng.randint(74, 80), _t(rng, 36.5, 36.8), 98, _w(c, 3.5)),
                "Short Etoricoxib course; continue physiotherapy; consider intra-articular steroid if no relief.",
                [("Knee Pain", "Severe", 10, "Right more than left after long walking"),
                 ("Knee Swelling", "Mild", 7, "Right knee")],
                [("Bilateral Primary Osteoarthritis of Knee", "M17.0", "Confirmed", "Flare with mild effusion.")],
                [("Etoricoxib", "60mg", "1 tablet once daily after food", 10, "Not to be taken long term"),
                 ("Pantoprazole", "40mg", "1 tablet before breakfast", 10, "")],
                "S: Pain flare after walking several km at pilgrimage. O: Small right knee effusion. A: OA flare. P: COX-2 short course.",
                [],
            ),
        ],
    )


def gerd_hpylori(rng: Random, c: Ctx) -> Story:
    return Story(
        specialty="gastro",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Burning in the upper stomach and sour belching after spicy food",
                (_bp(rng, 118, 128, 76, 82), rng.randint(72, 80), _t(rng, 36.5, 36.8), 99, _w(c)),
                "Pantoprazole for 4 weeks; small frequent meals; avoid late dinners, tea on empty stomach and spicy food.",
                [("Heartburn", "Moderate", 60, "Retrosternal burning after meals"),
                 ("Epigastric Pain", "Moderate", 45, "Gnawing, before meals"),
                 ("Bloating", "Mild", 30, "")],
                [("Gastro-Oesophageal Reflux Disease", "K21.9", "Provisional", ""),
                 ("Dyspepsia", "K30", "Provisional", "Rule out H. pylori.")],
                [("Pantoprazole", "40mg", "1 tablet 30 minutes before breakfast", 28, ""),
                 ("Domperidone", "10mg", "1 tablet before meals SOS for bloating", 10, "")],
                f"S: {_who(c)} with 2 months of heartburn and epigastric pain; skips breakfast, many cups of tea. "
                f"O: Mild epigastric tenderness, no alarm features. A: GERD with dyspepsia. P: PPI trial, H. pylori stool antigen.",
                [("H. pylori Stool Antigen", "Positive", "", "Negative", "Abnormal", "")],
            ),
            VisitSpec(
                rng.randint(14, 24), "Follow-up", "Follow-up with H. pylori positive report",
                (_bp(rng, 118, 126, 76, 80), rng.randint(70, 78), _t(rng, 36.5, 36.8), 99, _w(c)),
                "14-day triple therapy eradication; test of cure 4 weeks after completion.",
                [("Epigastric Pain", "Mild", 20, "Better on PPI")],
                [("Helicobacter pylori Gastritis", "K29.70", "Confirmed", "Stool antigen positive."),
                 ("Gastro-Oesophageal Reflux Disease", "K21.9", "Confirmed", "")],
                [("H. pylori Kit", "14-day", "As per kit, twice daily", 14, "Complete all 14 days")],
                "S: Partial relief on PPI. O: Benign abdomen. A: H. pylori gastritis. P: Triple therapy, test of cure.",
                [],
            ),
            VisitSpec(
                rng.randint(55, 75), "Telehealth", "Video consult: test of cure result",
                (_bp(rng, 116, 124, 74, 80), rng.randint(70, 76), _t(rng, 36.5, 36.8), 99, _w(c)),
                "Eradication confirmed; PPI on demand only.",
                [],
                [("Helicobacter pylori Gastritis", "K29.70", "Resolved", "Eradicated.")],
                [("Pantoprazole", "40mg", "1 tablet SOS for heartburn", 30, "")],
                "S: Symptom-free. O: Video consult. A: H. pylori eradicated. P: Lifestyle measures.",
                [("H. pylori Stool Antigen", "Negative", "", "Negative", "Normal", "Test of cure")],
                note_type="Consultation",
            ),
        ],
    )


def depression_anxiety(rng: Random, c: Ctx) -> Story:
    phq = [rng.randint(16, 20), rng.randint(9, 12), rng.randint(3, 6)]
    return Story(
        specialty="psych",
        history=[],
        visits=[
            VisitSpec(
                0, "OPD", "Low mood, poor sleep and loss of interest for 2 months after job loss",
                (_bp(rng, 116, 124, 74, 80), rng.randint(82, 90), _t(rng, 36.5, 36.8), 99, _w(c, -3.0)),
                "Start Escitalopram; weekly CBT sessions; sleep hygiene; Tele-MANAS helpline 14416 shared; review in 4 weeks.",
                [("Low Mood", "Severe", 60, "Most of the day, nearly every day"),
                 ("Insomnia", "Moderate", 45, "Early morning awakening at 4 AM"),
                 ("Loss of Interest", "Moderate", 60, "Stopped playing cricket with friends"),
                 ("Palpitations", "Mild", 20, "With worry")],
                [("Moderate Depressive Episode", "F32.1", "Confirmed", "No suicidal intent on assessment."),
                 ("Generalised Anxiety Disorder", "F41.1", "Provisional", "Overlapping worry symptoms."),
                 ("Hyperthyroidism", "E05.90", "Ruled-out", "TSH normal.")],
                [("Escitalopram", "10mg", "1 tablet once daily after breakfast", 30, "Takes 2-4 weeks to work; don't stop suddenly"),
                 ("Clonazepam", "0.25mg", "1 tablet at bedtime", 14, "Short term only")],
                f"S: {_who(c)} with 2 months of low mood, anhedonia, early-morning awakening after losing job. Denies self-harm thoughts. "
                f"O: Psychomotor slowing, reactive affect. A: Moderate depressive episode (F32.1) with anxiety. "
                f"P: SSRI, CBT, short-term clonazepam, family support.",
                [("PHQ-9 Score", str(phq[0]), "points", "0 - 4", "High", "Moderately severe"),
                 ("TSH", _r(rng, 1.2, 3.0, 2), "uIU/mL", "0.4 - 4.5", "Normal", "")],
                note_type="Consultation",
            ),
            VisitSpec(
                rng.randint(28, 35), "Telehealth", "Video review 4 weeks after starting Escitalopram",
                (_bp(rng, 114, 122, 72, 78), rng.randint(74, 80), _t(rng, 36.5, 36.8), 99, _w(c, -2.0)),
                "Continue Escitalopram; stop Clonazepam; continue CBT.",
                [("Low Mood", "Moderate", 30, "Better on most days"),
                 ("Insomnia", "Mild", 14, "Sleeping 6 hours")],
                [("Moderate Depressive Episode", "F32.1", "Confirmed", "Partial response.")],
                [("Escitalopram", "10mg", "1 tablet once daily", 60, "")],
                "S: Mood improving, sleeping better, attending interviews. O: Brighter affect on video. "
                "A: Partial response. P: Continue SSRI, taper clonazepam.",
                [("PHQ-9 Score", str(phq[1]), "points", "0 - 4", "High", "Mild-moderate")],
            ),
            VisitSpec(
                rng.randint(110, 140), "Follow-up", "Three-month mental health review",
                (_bp(rng, 112, 120, 72, 76), rng.randint(70, 76), _t(rng, 36.5, 36.8), 99, _w(c)),
                "In remission; continue Escitalopram for at least 6-9 months.",
                [],
                [("Moderate Depressive Episode", "F32.1", "Controlled", "In remission."),
                 ("Generalised Anxiety Disorder", "F41.1", "Ruled-out", "Anxiety resolved with mood; no separate disorder.")],
                [("Escitalopram", "10mg", "1 tablet once daily", 180, "")],
                "S: Started new job, enjoying cricket again. O: Euthymic. A: Remission. P: Continue SSRI 6-9 months.",
                [("PHQ-9 Score", str(phq[2]), "points", "0 - 4", "Normal" if phq[2] <= 4 else "High", "Minimal")],
            ),
        ],
    )


# Weighted catalogue: (storyline, weight, sex filter, (min age, max age), seasonal months)
STORYLINES: List[Tuple[StoryFn, int, Optional[str], Tuple[int, int], Optional[Tuple[int, ...]]]] = [
    (diabetes_hypertension, 14, None, (38, 72), None),
    (hypertension_only, 7, None, (35, 70), None),
    (coronary_artery_disease, 5, "Male", (42, 68), None),
    (ckd_diabetic, 4, None, (52, 76), None),
    (nafld, 4, None, (28, 55), None),
    (tuberculosis, 7, None, (18, 60), None),
    (dengue, 7, None, (10, 55), (7, 8, 9, 10)),
    (typhoid, 5, None, (8, 45), (4, 5, 6, 7, 8)),
    (malaria_vivax, 3, None, (14, 55), (7, 8, 9, 10, 11)),
    (chikungunya, 3, None, (20, 60), (8, 9, 10)),
    (gastroenteritis_child, 4, None, (2, 9), (5, 6, 7, 8)),
    (recurrent_tonsillitis_child, 3, None, (5, 12), None),
    (uti_female, 4, "Female", (20, 55), (4, 5, 6)),
    (hypothyroidism, 6, "Female", (25, 58), None),
    (pcos, 5, "Female", (18, 30), None),
    (anaemia_women, 6, "Female", (18, 45), None),
    (gestational_diabetes, 3, "Female", (23, 34), None),
    (vitamin_deficiency, 4, None, (24, 50), None),
    (asthma_rhinitis, 5, None, (14, 45), (10, 11, 12)),
    (copd_biomass, 4, None, (55, 78), (11, 12, 1)),
    (knee_osteoarthritis, 5, None, (50, 75), None),
    (gerd_hpylori, 5, None, (24, 60), None),
    (depression_anxiety, 4, None, (20, 45), None),
]

SPECIALTY_TO_DOCTOR_KEY: Dict[str, str] = {
    "internal": "internal",
    "cardio": "cardio",
    "nephro": "nephro",
    "gastro": "gastro",
    "pulmo": "pulmo",
    "rheum": "internal",
    "paeds": "paeds",
    "endo": "endo",
    "obgyn": "obgyn",
    "ortho": "ortho",
    "psych": "psych",
}
