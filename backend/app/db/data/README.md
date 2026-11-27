# Patient data: MIMIC-IV demo (real, de-identified)

`mimic_iv_demo.json.gz` holds the 100 patients MedVault seeds on first start. It is derived from:

- **MIMIC-IV Clinical Database Demo v2.2**: https://physionet.org/content/mimic-iv-demo/2.2/
- **MIMIC-IV-ED Demo v2.2**: https://physionet.org/content/mimic-iv-ed-demo/2.2/

Both are published on PhysioNet by the MIT Laboratory for Computational Physiology and contain real, de-identified records of patients at Beth Israel Deaconess Medical Center, Boston. They are licensed under the **Open Database License (ODbL) v1.0** (full text in `LICENSE-ODbL.txt`). This derived file is shared under the same licence.

Please cite:

> Johnson, A., Bulgarelli, L., Pollard, T., Horng, S., Celi, L. A., & Mark, R. (2023). MIMIC-IV Clinical Database Demo (version 2.2). PhysioNet. https://doi.org/10.13026/dp1f-ex47
>
> Johnson, A., Bulgarelli, L., Pollard, T., Celi, L. A., Mark, R., & Horng, S. (2023). MIMIC-IV-ED Demo (version 2.2). PhysioNet.
>
> Goldberger, A., et al. (2000). PhysioBank, PhysioToolkit, and PhysioNet. Circulation 101(23), e215–e220.

## What the file contains

Built by `backend/scripts/build_mimic_seed.py` from the `hosp` and `ed` tables:

| MedVault table | Source |
|---|---|
| patients | `patients`: sex, age, year group. Named "Patient <subject_id>"; MRN `MIMIC-<subject_id>` |
| visits | `admissions` (Emergency or Inpatient) and ED stays that did not lead to admission |
| vitals | ED `triage` and `vitalsign` (BP, heart rate, SpO2, temperature); `omr` for BP and weight |
| symptoms | ED triage chief complaint, common abbreviations expanded (raw text kept in the note) |
| diagnoses | `diagnoses_icd` + `d_icd_diagnoses`, top 8 by sequence per admission |
| prescriptions | `prescriptions` (MAIN drugs), up to 12 distinct per admission |
| test_results | `labevents` + `d_labitems`: first result of key tests and of abnormal tests, up to 14 per admission |
| clinical_notes | Compiled from the coded rows above and labelled as such; the demo has no free-text notes |

Not present in the demo: names, addresses, contact numbers, blood group, allergies. MIMIC shifts dates into the future; they are moved back into each patient's `anchor_year_group`, so they are accurate to within about three years.

To rebuild, download the tables listed in `RAW_TABLES` in the script into `<raw>/hosp` and `<raw>/ed`, then run `python scripts/build_mimic_seed.py <raw>` from `backend/`.
