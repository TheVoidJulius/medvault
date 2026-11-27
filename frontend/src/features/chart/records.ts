import type { PatientDetail, Visit } from '../../lib/types';
import { parseBp } from '../../lib/format';

/** Visits newest first (the API already sends them this way; sorting keeps it explicit). */
export const byNewest = (visits: Visit[]) => [...visits].sort((a, b) => b.visit_date.localeCompare(a.visit_date));

export interface LabPoint {
  date: string;
  value: string;
  num: number | null;
  unit?: string | null;
  flag: string;
  range?: string | null;
  visitId: number;
  tag: string;
}

export interface LabGroup {
  name: string;
  points: LabPoint[]; // oldest first
  latest: LabPoint;
  outOfRange: number;
}

export function labGroups(patient: PatientDetail): LabGroup[] {
  const map = new Map<string, LabPoint[]>();
  for (const v of patient.visits) {
    for (const t of v.test_results) {
      const num = Number.parseFloat(t.value);
      const point: LabPoint = {
        date: t.result_date || v.visit_date,
        value: t.value,
        num: Number.isFinite(num) && /^[<>]?\s*-?\d/.test(t.value) ? num : null,
        unit: t.unit,
        flag: t.flag,
        range: t.reference_range,
        visitId: v.id,
        tag: `LAB-${t.id}`,
      };
      map.set(t.test_name, [...(map.get(t.test_name) ?? []), point]);
    }
  }
  return [...map.entries()]
    .map(([name, pts]) => {
      const points = pts.sort((a, b) => a.date.localeCompare(b.date));
      return { name, points, latest: points[points.length - 1], outOfRange: points.filter((p) => p.flag !== 'Normal').length };
    })
    .sort((a, b) => Number(b.latest.flag !== 'Normal') - Number(a.latest.flag !== 'Normal') || b.latest.date.localeCompare(a.latest.date) || a.name.localeCompare(b.name));
}

export interface MedGroup {
  name: string;
  strength?: string;
  orders: { date: string; dosage: string; frequency: string; days?: number | null; visitId: number }[]; // newest first
}

export function medGroups(patient: PatientDetail): MedGroup[] {
  const map = new Map<string, MedGroup>();
  for (const v of byNewest(patient.visits)) {
    for (const rx of v.prescriptions) {
      const name = rx.medication?.name ?? 'Medication';
      const g = map.get(name) ?? { name, strength: rx.medication?.strength, orders: [] };
      g.orders.push({ date: v.visit_date, dosage: rx.dosage, frequency: rx.frequency, days: rx.duration_days, visitId: v.id });
      map.set(name, g);
    }
  }
  return [...map.values()].sort((a, b) => b.orders[0].date.localeCompare(a.orders[0].date) || b.orders.length - a.orders.length);
}

export interface ConditionGroup {
  name: string;
  code?: string | null;
  visits: number;
  first: string;
  last: string;
  status: string;
}

export function conditionGroups(patient: PatientDetail): ConditionGroup[] {
  const map = new Map<string, ConditionGroup>();
  for (const v of [...patient.visits].sort((a, b) => a.visit_date.localeCompare(b.visit_date))) {
    const seen = new Set<string>();
    for (const d of v.diagnoses) {
      if (d.status === 'Ruled-out' || seen.has(d.condition_name)) continue;
      seen.add(d.condition_name);
      const g = map.get(d.condition_name);
      if (g) {
        g.visits += 1;
        g.last = v.visit_date;
        g.status = d.status;
      } else {
        map.set(d.condition_name, { name: d.condition_name, code: d.icd10_code, visits: 1, first: v.visit_date, last: v.visit_date, status: d.status });
      }
    }
  }
  return [...map.values()].sort((a, b) => b.visits - a.visits || b.last.localeCompare(a.last));
}

export type VitalState = 'normal' | 'abnormal' | 'unknown';

export interface VitalReading {
  label: string;
  value: string;
  unit: string;
  state: VitalState;
  date?: string;
  hint: string;
}

/** The most recent recorded value of each vital, judged against simple adult normal ranges. */
export function latestVitals(patient: PatientDetail): VitalReading[] {
  const visits = byNewest(patient.visits);
  const find = <T,>(get: (v: Visit) => T | null | undefined) => {
    for (const v of visits) {
      const val = get(v);
      if (val !== null && val !== undefined && val !== '') return { val, date: v.visit_date };
    }
    return null;
  };
  const bp = find((v) => v.vitals_bp);
  const hr = find((v) => v.vitals_hr);
  const spo2 = find((v) => v.vitals_spo2);
  const temp = find((v) => v.vitals_temp_c);
  const bpN = parseBp(bp?.val);
  const tempN = temp ? Number.parseFloat(String(temp.val)) : NaN;
  return [
    {
      label: 'Blood pressure',
      value: bpN ? `${bpN.sys}/${bpN.dia}` : '—',
      unit: 'mmHg',
      state: !bpN ? 'unknown' : bpN.sys >= 140 || bpN.dia >= 90 || bpN.sys < 90 || bpN.dia < 60 ? 'abnormal' : 'normal',
      date: bp?.date,
      hint: 'Normal 90–139 over 60–89',
    },
    {
      label: 'Heart rate',
      value: hr ? String(hr.val) : '—',
      unit: 'bpm',
      state: !hr ? 'unknown' : Number(hr.val) < 60 || Number(hr.val) > 100 ? 'abnormal' : 'normal',
      date: hr?.date,
      hint: 'Normal 60–100',
    },
    {
      label: 'Oxygen (SpO₂)',
      value: spo2 ? String(spo2.val) : '—',
      unit: '%',
      state: !spo2 ? 'unknown' : Number(spo2.val) < 94 ? 'abnormal' : 'normal',
      date: spo2?.date,
      hint: 'Normal 94% or more',
    },
    {
      label: 'Temperature',
      value: temp ? String(temp.val) : '—',
      unit: '°C',
      state: !temp || Number.isNaN(tempN) ? 'unknown' : tempN >= 38 || tempN < 35.5 ? 'abnormal' : 'normal',
      date: temp?.date,
      hint: 'Normal 35.5–37.9',
    },
  ];
}
