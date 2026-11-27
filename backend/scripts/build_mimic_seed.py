"""Convert the MIMIC-IV Clinical Database Demo into MedVault's seed file.

Source data (real, de-identified patients of Beth Israel Deaconess Medical Center, Boston),
published on PhysioNet under the Open Database License (ODbL):
  - MIMIC-IV Clinical Database Demo v2.2  https://physionet.org/content/mimic-iv-demo/2.2/
  - MIMIC-IV-ED Demo v2.2                 https://physionet.org/content/mimic-iv-ed-demo/2.2/

Download the tables listed in RAW_TABLES into <raw>/hosp and <raw>/ed, then run:

    python scripts/build_mimic_seed.py <raw>

Writes backend/app/db/data/mimic_iv_demo.json.gz. Nothing here invents clinical facts: every
symptom, diagnosis, drug, lab and vital comes from a source row. MIMIC has no names, addresses,
allergies or free-text notes in the demo, so those stay empty, and the per-visit note is labelled
as compiled from coded data. Dates are moved from MIMIC's shifted years back into each
patient's real year group (anchor_year_group), so they are approximate to within about 3 years.
"""

import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "db" / "data" / "mimic_iv_demo.json.gz"

RAW_TABLES = {
    "hosp": ["patients", "admissions", "diagnoses_icd", "d_icd_diagnoses", "prescriptions", "labevents", "d_labitems",
             "omr", "procedures_icd", "d_icd_procedures", "services"],
    "ed": ["edstays", "triage", "vitalsign", "diagnosis"],
}

MAX_DX, MAX_RX, MAX_LABS = 8, 12, 14

# Lab panels a clinician scans first; their first value each admission is always kept.
KEY_LABS = [
    "Hemoglobin", "White Blood Cells", "Platelet Count", "Sodium", "Potassium", "Creatinine", "Urea Nitrogen",
    "Glucose", "Bicarbonate", "Lactate", "Troponin T", "NTproBNP", "INR(PT)", "Alanine Aminotransferase (ALT)",
    "Asparate Aminotransferase (AST)", "Bilirubin, Total", "Albumin", "% Hemoglobin A1c", "pH",
]

# Hospital service code -> MedVault demo doctor (the app's sign-in accounts, not source data).
SERVICE_TO_DOCTOR = {
    "MED": "internal", "OMED": "internal", "ENT": "internal", "EYE": "internal", "DENT": "internal",
    "CMED": "cardio", "CSURG": "cardio", "NMED": "neuro", "NSURG": "neuro",
    "SURG": "ortho", "TSURG": "ortho", "VSURG": "ortho", "ORTHO": "ortho", "TRAUM": "ortho", "PSURG": "ortho",
    "GU": "nephro", "GYN": "obgyn", "OBS": "obgyn", "PSYCH": "psych", "NB": "paeds", "NBB": "paeds",
}

# ED triage chief complaints are free-text abbreviations; expand the common ones for readability.
COMPLAINT_TERMS = {
    "SOB": "Shortness of breath", "DYSPNEA": "Shortness of breath", "CP": "Chest pain", "CHEST PAIN": "Chest pain",
    "AMS": "Altered mental status", "ABD PAIN": "Abdominal pain", "ABDOMINAL PAIN": "Abdominal pain", "HA": "Headache",
    "N/V": "Nausea and vomiting", "N/V/D": "Nausea, vomiting and diarrhoea", "DOE": "Breathlessness on exertion",
    "LE EDEMA": "Leg swelling", "S/P FALL": "Fall", "FALL": "Fall", "FEVER": "Fever", "COUGH": "Cough",
    "WEAKNESS": "Weakness", "DIZZINESS": "Dizziness", "SYNCOPE": "Fainting (syncope)", "HYPOTENSION": "Low blood pressure",
    "HYPERGLYCEMIA": "High blood sugar", "BRBPR": "Rectal bleeding", "HEMATEMESIS": "Vomiting blood",
    "ETOH": "Alcohol intoxication", "SI": "Suicidal thoughts", "UTI": "Urinary infection symptoms", "DYSURIA": "Painful urination",
    "BACK PAIN": "Back pain", "FACIAL DROOP": "Facial droop", "SEIZURE": "Seizure", "PALPITATIONS": "Palpitations",
    "HYPOXIA": "Low oxygen", "FATIGUE": "Fatigue", "LETHARGY": "Lethargy", "CONFUSION": "Confusion",
}


def read(raw: Path, mod: str, table: str):
    with gzip.open(raw / mod / f"{table}.csv.gz", "rt", newline="") as f:
        yield from csv.DictReader(f)


def ts(value: str):
    return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S") if value else None


def shift_year(d, years: int):
    if d is None:
        return None
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 Feb in a non-leap target year
        return d.replace(year=d.year - years, day=28)


def icd_display(code: str, version: str) -> str:
    code = code.strip()
    if version == "10":
        return code if len(code) <= 3 else f"{code[:3]}.{code[3:]}"
    if code.startswith("E"):
        return code if len(code) <= 4 else f"{code[:4]}.{code[4:]}"
    return code if len(code) <= 3 else f"{code[:3]}.{code[3:]}"


def tidy(text: str) -> str:
    """MIMIC titles are often ALL CAPS; make them readable without changing words."""
    t = text.strip()
    if t.isupper() and len(t) > 4:
        t = t.capitalize()
    return t


def complaint_symptoms(cc: str):
    out = []
    for part in [p.strip() for p in cc.replace(";", ",").split(",") if p.strip()]:
        key = part.upper()
        out.append(COMPLAINT_TERMS.get(key, tidy(part)))
    return out[:4]


def pain_severity(pain: str) -> str:
    try:
        p = float(pain)
    except (TypeError, ValueError):
        return "Moderate"
    return "Severe" if p >= 7 else "Moderate" if p >= 4 else "Mild"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v: float) -> str:
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:g}"


def build(raw: Path):
    patients = {r["subject_id"]: r for r in read(raw, "hosp", "patients")}
    shift = {}
    for sid, p in patients.items():
        group_start = int(p["anchor_year_group"].split("-")[0])
        shift[sid] = int(p["anchor_year"]) - (group_start + 1)

    dx_titles = {(r["icd_version"], r["icd_code"]): r["long_title"] for r in read(raw, "hosp", "d_icd_diagnoses")}
    px_titles = {(r["icd_version"], r["icd_code"]): r["long_title"] for r in read(raw, "hosp", "d_icd_procedures")}
    lab_items = {r["itemid"]: r for r in read(raw, "hosp", "d_labitems")}

    dx_by_hadm = defaultdict(list)
    for r in read(raw, "hosp", "diagnoses_icd"):
        dx_by_hadm[r["hadm_id"]].append(r)
    px_by_hadm = defaultdict(list)
    for r in read(raw, "hosp", "procedures_icd"):
        px_by_hadm[r["hadm_id"]].append(r)
    service_by_hadm = {}
    for r in sorted(read(raw, "hosp", "services"), key=lambda r: r["transfertime"]):
        service_by_hadm.setdefault(r["hadm_id"], r["curr_service"])
    rx_by_hadm = defaultdict(list)
    for r in read(raw, "hosp", "prescriptions"):
        if r["hadm_id"] and r["drug_type"] == "MAIN":
            rx_by_hadm[r["hadm_id"]].append(r)
    labs_by_hadm = defaultdict(list)
    for r in read(raw, "hosp", "labevents"):
        if r["hadm_id"]:
            labs_by_hadm[r["hadm_id"]].append(r)
    omr_by_subject = defaultdict(list)
    for r in read(raw, "hosp", "omr"):
        omr_by_subject[r["subject_id"]].append(r)

    stays = list(read(raw, "ed", "edstays"))
    triage = {r["stay_id"]: r for r in read(raw, "ed", "triage")}
    ed_vitals = defaultdict(list)
    for r in sorted(read(raw, "ed", "vitalsign"), key=lambda r: r["charttime"]):
        ed_vitals[r["stay_id"]].append(r)
    ed_dx = defaultdict(list)
    for r in read(raw, "ed", "diagnosis"):
        ed_dx[r["stay_id"]].append(r)
    stay_by_hadm = {s["hadm_id"]: s for s in stays if s["hadm_id"]}

    drug_strengths = defaultdict(Counter)
    drug_routes = defaultdict(Counter)

    def omr_near(sid, when, name_prefix):
        best = None
        for r in omr_by_subject[sid]:
            if not r["result_name"].startswith(name_prefix):
                continue
            d = datetime.strptime(r["chartdate"], "%Y-%m-%d")
            gap = (when - d).days
            if 0 <= gap <= 365 and (best is None or gap < best[0]):
                best = (gap, r["result_value"])
        return best[1] if best else None

    def vitals_for(sid, when, stay):
        bp = hr = temp = spo2 = None
        rows = []
        if stay:
            if stay["stay_id"] in triage:
                rows.append(triage[stay["stay_id"]])
            rows += ed_vitals.get(stay["stay_id"], [])
        for r in rows:
            if bp is None and num(r.get("sbp")) and num(r.get("dbp")):
                bp = f"{fmt(num(r['sbp']))}/{fmt(num(r['dbp']))} mmHg"
            if hr is None and num(r.get("heartrate")):
                hr = int(num(r["heartrate"]))
            if temp is None and num(r.get("temperature")) and 90 < num(r["temperature"]) < 110:
                temp = f"{(num(r['temperature']) - 32) * 5 / 9:.1f}"
            if spo2 is None and num(r.get("o2sat")) and 50 <= num(r["o2sat"]) <= 100:
                spo2 = int(num(r["o2sat"]))
        if bp is None:
            raw_bp = omr_near(sid, when, "Blood Pressure")
            if raw_bp and "/" in raw_bp:
                bp = f"{raw_bp} mmHg"
        weight = omr_near(sid, when, "Weight (Lbs)")
        weight_kg = f"{float(weight) * 0.4536:.1f}" if weight and num(weight) else None
        if hr is not None and not 20 <= hr <= 300:
            hr = None
        return {"bp": bp, "hr": hr, "temp": temp, "spo2": spo2, "weight": weight_kg}

    def lab_rows(hadm, day):
        by_label = defaultdict(list)
        for r in sorted(labs_by_hadm.get(hadm, []), key=lambda r: r["charttime"]):
            item = lab_items.get(r["itemid"])
            # MIMIC masks some values as "___" during de-identification; those carry no result.
            if item and r["value"] and "___" not in r["value"]:
                by_label[item["label"]].append(r)
        chosen = []

        def as_lab(label, rows):
            r = rows[0]
            v, lo, hi = num(r["valuenum"]), num(r["ref_range_lower"]), num(r["ref_range_upper"])
            flag = "Normal"
            if r["flag"] == "abnormal":
                flag = "High" if v is not None and hi is not None and v > hi else "Low" if v is not None and lo is not None and v < lo else "Abnormal"
            ref = f"{fmt(lo)} - {fmt(hi)}" if lo is not None and hi is not None and (lo or hi) else None
            return {
                "name": label, "value": r["value"][:78], "unit": r["valueuom"] or None, "ref": ref, "flag": flag,
                "remarks": f"First result this admission ({len(rows)} measured)" if len(rows) > 1 else "Single result this admission",
            }

        for label in KEY_LABS:
            if label in by_label:
                chosen.append(as_lab(label, by_label[label]))
        for label, rows in by_label.items():
            if len(chosen) >= MAX_LABS:
                break
            if label not in KEY_LABS and rows[0]["flag"] == "abnormal":
                chosen.append(as_lab(label, rows))
        return chosen[:MAX_LABS]

    def rx_rows(hadm):
        seen, out = set(), []
        for r in sorted(rx_by_hadm.get(hadm, []), key=lambda r: r["starttime"]):
            name = r["drug"].strip()
            key = name.lower()
            if key in seen or "flush" in key or key in {"bag", "syringe"}:
                continue
            seen.add(key)
            start, stop = ts(r["starttime"]), ts(r["stoptime"])
            days = max(1, round((stop - start).total_seconds() / 86400)) if start and stop else None
            dose = " ".join(x for x in [r["dose_val_rx"], r["dose_unit_rx"]] if x) or "As charted"
            freq_bits = [r["route"]] if r["route"] else []
            if num(r["doses_per_24_hrs"]):
                freq_bits.append(f"{fmt(num(r['doses_per_24_hrs']))}x per day")
            if r["prod_strength"]:
                drug_strengths[name][r["prod_strength"][:48]] += 1
            if r["route"]:
                drug_routes[name][r["route"][:48]] += 1
            out.append({"drug": name, "dosage": dose[:48], "frequency": ", ".join(freq_bits) or "As charted", "days": days,
                        "instructions": f"Form: {r['form_rx']}" if r["form_rx"] else None})
            if len(out) >= MAX_RX:
                break
        return out

    def note_for(v):
        s = f"S: {v['complaint']}." + (f" Triage pain score {v['pain']}/10." if v.get("pain") else "")
        vit = ", ".join(x for x in [
            f"BP {v['vitals']['bp']}" if v["vitals"]["bp"] else "",
            f"HR {v['vitals']['hr']}" if v["vitals"]["hr"] else "",
            f"SpO2 {v['vitals']['spo2']}%" if v["vitals"]["spo2"] else "",
            f"Temp {v['vitals']['temp']} C" if v["vitals"]["temp"] else "",
        ] if x)
        abn = [f"{l['name']} {l['value']} {l['unit'] or ''}".strip() for l in v["labs"] if l["flag"] != "Normal"][:5]
        o = "O: " + (vit or "No vitals charted") + "." + (f" Out-of-range results: {'; '.join(abn)}." if abn else "")
        a = "A: " + ("; ".join(d["name"] for d in v["diagnoses"][:3]) or "No coded diagnosis") + "."
        p = "P: " + v["plan"]
        return "[Compiled from coded MIMIC-IV data; the demo has no free-text notes.]\n" + "\n".join([s, o, a, p])

    out_patients = []
    for sid, p in sorted(patients.items()):
        yrs = shift[sid]
        visits = []
        for a in read(raw, "hosp", "admissions"):
            if a["subject_id"] != sid:
                continue
            hadm = a["hadm_id"]
            admit, disch = ts(a["admittime"]), ts(a["dischtime"])
            stay = stay_by_hadm.get(hadm)
            tri = triage.get(stay["stay_id"]) if stay else None
            dxs = sorted(dx_by_hadm.get(hadm, []), key=lambda r: int(r["seq_num"]))[:MAX_DX]
            diagnoses = [{
                "name": tidy(dx_titles.get((d["icd_version"], d["icd_code"]), f"ICD-{d['icd_version']} {d['icd_code']}"))[:200],
                "code": icd_display(d["icd_code"], d["icd_version"]),
                "notes": f"Discharge diagnosis #{d['seq_num']} (ICD-{d['icd_version']})",
            } for d in dxs]
            cc = (tri or {}).get("chiefcomplaint", "").strip()
            complaint = ", ".join(complaint_symptoms(cc)) if cc else (f"Admitted with {diagnoses[0]['name'].lower()}" if diagnoses else "Hospital admission")
            pxs = sorted(px_by_hadm.get(hadm, []), key=lambda r: int(r["seq_num"]))[:3]
            proc = [tidy(px_titles.get((x["icd_version"], x["icd_code"]), x["icd_code"])) for x in pxs]
            los = max(0, (disch - admit).days) if admit and disch else None
            plan = f"Admitted via {a['admission_location'].lower() or 'unknown route'}"
            if a["hospital_expire_flag"] == "1":
                plan += f"; died in hospital after {los} days"
            else:
                plan += f"; discharged to {a['discharge_location'].lower() or 'unknown'} after {los} days"
            if proc:
                plan += ". Procedures: " + "; ".join(proc)
            plan += "."
            when = admit
            v = {
                "source_id": f"hadm {hadm}",
                "date": shift_year(admit, yrs).isoformat(),
                "type": "Emergency" if ("EMER" in a["admission_type"] or a["admission_type"] == "URGENT") else "Inpatient",
                "service": service_by_hadm.get(hadm, "MED"),
                "complaint": complaint[:250],
                "pain": (tri or {}).get("pain") if num((tri or {}).get("pain")) is not None else None,
                "symptoms": [{"name": s, "severity": pain_severity((tri or {}).get("pain")),
                              "notes": f"Triage chief complaint: {cc}"} for s in complaint_symptoms(cc)] if cc else [],
                "diagnoses": diagnoses,
                "rx": rx_rows(hadm),
                "labs": lab_rows(hadm, admit),
                "vitals": vitals_for(sid, when, stay),
                "plan": plan[:900],
            }
            v["note"] = note_for(v)
            visits.append(v)

        # Emergency visits that did not lead to an admission
        for s in stays:
            if s["subject_id"] != sid or s["hadm_id"]:
                continue
            tri = triage.get(s["stay_id"], {})
            cc = (tri.get("chiefcomplaint") or "").strip()
            intime = ts(s["intime"])
            dxs = sorted(ed_dx.get(s["stay_id"], []), key=lambda r: int(r["seq_num"]))[:MAX_DX]
            diagnoses = [{"name": tidy(d["icd_title"])[:200], "code": icd_display(d["icd_code"], d["icd_version"]),
                          "notes": f"ED diagnosis #{d['seq_num']} (ICD-{d['icd_version']})"} for d in dxs]
            v = {
                "source_id": f"ED stay {s['stay_id']}",
                "date": shift_year(intime, yrs).isoformat(),
                "type": "Emergency",
                "service": "MED",
                "complaint": (", ".join(complaint_symptoms(cc)) if cc else "Emergency department visit")[:250],
                "pain": tri.get("pain") if num(tri.get("pain")) is not None else None,
                "symptoms": [{"name": x, "severity": pain_severity(tri.get("pain")), "notes": f"Triage chief complaint: {cc}"}
                             for x in complaint_symptoms(cc)] if cc else [],
                "diagnoses": diagnoses,
                "rx": [],
                "labs": [],
                "vitals": vitals_for(sid, intime, s),
                "plan": f"Arrived by {s['arrival_transport'].lower() or 'unknown means'}; ED disposition: {s['disposition'].lower() or 'unknown'}.",
            }
            v["note"] = note_for(v)
            visits.append(v)

        if not visits:
            continue
        visits.sort(key=lambda v: v["date"])
        real_anchor = int(p["anchor_year"]) - yrs
        out_patients.append({
            "subject_id": sid,
            "sex": "Male" if p["gender"] == "M" else "Female",
            "birth_year": real_anchor - int(p["anchor_age"]),
            "age_capped": int(p["anchor_age"]) >= 89,
            "died": bool(p["dod"]),
            "visits": visits,
        })

    medications = []
    for name in sorted({rx["drug"] for pt in out_patients for v in pt["visits"] for rx in v["rx"]}):
        strength = drug_strengths[name].most_common(1)[0][0] if drug_strengths[name] else "As charted"
        route = drug_routes[name].most_common(1)[0][0] if drug_routes[name] else "Unspecified"
        medications.append({"name": name[:138], "strength": strength, "form": route})

    return {
        "source": {
            "dataset": "MIMIC-IV Clinical Database Demo v2.2 and MIMIC-IV-ED Demo v2.2",
            "institution": "Beth Israel Deaconess Medical Center, Boston, MA",
            "publisher": "PhysioNet (https://physionet.org/content/mimic-iv-demo/2.2/)",
            "license": "Open Database License (ODbL) v1.0",
            "citation": "Johnson A, Bulgarelli L, Pollard T, Horng S, Celi LA, Mark R. MIMIC-IV Clinical Database Demo (v2.2). PhysioNet. 2023.",
        },
        "medications": medications,
        "patients": out_patients,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = build(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    n_v = sum(len(p["visits"]) for p in data["patients"])
    print(f"Wrote {OUT}: {len(data['patients'])} patients, {n_v} visits, {len(data['medications'])} drugs, {OUT.stat().st_size // 1024} KB")
