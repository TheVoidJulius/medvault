import { FormEvent, ReactNode, useState } from 'react';
import { Plus, Sparkles, Trash2 } from 'lucide-react';
import { Button, Input, Notice, Select, Textarea } from '../../components/ui';
import { errorText } from '../../lib/http';
import type { PatientDetail } from '../../lib/types';
import { useWorkspace } from '../../workspace';
import { VISIT_TYPES } from '../PatientForms';

const today = () => new Date().toISOString().slice(0, 10);
const blankSymptom = () => ({ name: '', severity: 'Moderate', duration_days: 3, notes: '' });
const blankDiagnosis = () => ({ condition_name: '', icd10_code: '', status: 'Provisional', notes: '' });
const blankRx = () => ({ medication_name: '', strength: '', dosage: '1 tablet', frequency: 'Twice daily', duration_days: 7, instructions: '' });
const blankLab = () => ({ test_name: '', value: '', unit: '', reference_range: '', flag: 'Normal', result_date: today() });

const initialForm = () => ({
  visit_type: 'OPD',
  chief_complaint: '',
  vitals_bp: '',
  vitals_hr: '',
  vitals_temp_c: '',
  vitals_spo2: '',
  vitals_weight_kg: '',
  treatment_plan: '',
  note_type: 'SOAP',
  note: '',
  symptoms: [blankSymptom()],
  diagnoses: [blankDiagnosis()],
  prescriptions: [blankRx()],
  labs: [blankLab()],
});

type Form = ReturnType<typeof initialForm>;
type ListKey = 'symptoms' | 'diagnoses' | 'prescriptions' | 'labs';

function Rows<K extends ListKey>({
  title,
  form,
  k,
  blank,
  setForm,
  render,
}: {
  title: string;
  form: Form;
  k: K;
  blank: () => Form[K][number];
  setForm: (f: (prev: Form) => Form) => void;
  render: (row: Form[K][number], update: (patch: Partial<Form[K][number]>) => void, i: number) => ReactNode;
}) {
  const rows = form[k] as Form[K][number][];
  return (
    <fieldset className="border border-ink bg-sheet">
      <legend className="sr-only">{title}</legend>
      <div className="flex items-center justify-between border-b border-rule px-4 py-2.5">
        <h3 className="text-[0.875rem] font-bold">{title}</h3>
        <Button size="sm" tone="quiet" onClick={() => setForm((f) => ({ ...f, [k]: [...(f[k] as unknown[]), blank()] }))} icon={<Plus className="h-4 w-4" />}>
          Add row
        </Button>
      </div>
      <div className="divide-y divide-rule">
        {rows.map((row, i) => (
          <div key={i} className="flex items-end gap-2 px-4 py-3">
            <div className="grid flex-1 gap-2 sm:grid-cols-12">
              {render(
                row,
                (patch) => setForm((f) => ({ ...f, [k]: (f[k] as Form[K][number][]).map((r, j) => (j === i ? { ...r, ...patch } : r)) })),
                i,
              )}
            </div>
            <Button
              size="sm"
              tone="quiet"
              aria-label={`Remove ${title.toLowerCase()} row ${i + 1}`}
              disabled={rows.length === 1}
              onClick={() => setForm((f) => ({ ...f, [k]: (f[k] as unknown[]).filter((_, j) => j !== i) }))}
              icon={<Trash2 className="h-4 w-4" />}
            />
          </div>
        ))}
      </div>
    </fieldset>
  );
}

export function NewVisit({ patient, onSaved }: { patient: PatientDetail; onSaved: (visitId: number) => void }) {
  const { api, medications } = useWorkspace();
  const [form, setForm] = useState<Form>(initialForm);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extracted, setExtracted] = useState<string | null>(null);
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const extract = async () => {
    if (!form.note.trim()) {
      setError('Write or paste the consultation note first, then extract.');
      return;
    }
    setExtracting(true);
    setError(null);
    try {
      type Extracted = {
        chief_complaint: string;
        recommended_follow_up: string;
        concise_summary: string;
        extracted_symptoms: { name: string; severity?: string }[];
        suspected_diagnoses: { condition_name: string; icd10_code?: string; status?: string }[];
        mentioned_medications: { medication: string; dosage_notes?: string }[];
      };
      const x = await api<Extracted>('/api/ai/extract-note', { method: 'POST', body: JSON.stringify({ note_text: form.note }) });
      setForm((f) => ({
        ...f,
        chief_complaint: f.chief_complaint || x.chief_complaint,
        treatment_plan: f.treatment_plan || x.recommended_follow_up,
        symptoms: x.extracted_symptoms.length ? x.extracted_symptoms.map((s) => ({ ...blankSymptom(), name: s.name, severity: s.severity || 'Moderate' })) : f.symptoms,
        diagnoses: x.suspected_diagnoses.length
          ? x.suspected_diagnoses.map((d) => ({ ...blankDiagnosis(), condition_name: d.condition_name, icd10_code: d.icd10_code ?? '', status: d.status || 'Provisional' }))
          : f.diagnoses,
        prescriptions: x.mentioned_medications.length
          ? x.mentioned_medications.map((m) => {
              const [name, strength = ''] = m.medication.split(' ');
              return { ...blankRx(), medication_name: name, strength, frequency: m.dosage_notes || 'As directed' };
            })
          : f.prescriptions,
      }));
      setExtracted(x.concise_summary);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setExtracting(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await api<{ id: number }>(`/api/patients/${patient.id}/visits`, {
        method: 'POST',
        body: JSON.stringify({
          visit_type: form.visit_type,
          chief_complaint: form.chief_complaint,
          vitals_bp: form.vitals_bp || null,
          vitals_hr: form.vitals_hr ? Number(form.vitals_hr) : null,
          vitals_temp_c: form.vitals_temp_c || null,
          vitals_spo2: form.vitals_spo2 ? Number(form.vitals_spo2) : null,
          vitals_weight_kg: form.vitals_weight_kg || null,
          treatment_plan: form.treatment_plan || null,
          symptoms: form.symptoms.filter((s) => s.name.trim()),
          diagnoses: form.diagnoses.filter((d) => d.condition_name.trim()),
          prescriptions: form.prescriptions.filter((p) => p.medication_name.trim()).map((p) => ({ ...p, strength: p.strength || 'Standard' })),
          clinical_notes: form.note.trim() ? [{ note_type: form.note_type, content: form.note }] : [],
          test_results: form.labs.filter((t) => t.test_name.trim() && t.value.trim()),
        }),
      });
      setForm(initialForm());
      setExtracted(null);
      onSaved(saved.id);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <section className="border border-ink bg-sheet p-4">
        <div className="grid gap-3 sm:grid-cols-[180px_1fr]">
          <Select label="Visit type" value={form.visit_type} onChange={set('visit_type')}>
            {VISIT_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Input label="Chief complaint" required value={form.chief_complaint} onChange={set('chief_complaint')} placeholder="In the patient’s words" />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Input label="BP" value={form.vitals_bp} onChange={set('vitals_bp')} placeholder="120/80 mmHg" />
          <Input label="Heart rate" type="number" min={20} max={300} value={form.vitals_hr} onChange={set('vitals_hr')} placeholder="bpm" />
          <Input label="Temp °C" value={form.vitals_temp_c} onChange={set('vitals_temp_c')} placeholder="36.8" />
          <Input label="SpO₂ %" type="number" min={50} max={100} value={form.vitals_spo2} onChange={set('vitals_spo2')} />
          <Input label="Weight kg" value={form.vitals_weight_kg} onChange={set('vitals_weight_kg')} />
        </div>
      </section>

      <section className="border border-ink bg-sheet p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-[0.875rem] font-bold">Consultation note</h3>
            <p className="text-2xs text-ink-3">Write the note, then let AI pull out symptoms, diagnoses and drugs into the rows below for you to check.</p>
          </div>
          <div className="flex gap-2">
            <Select aria-label="Note type" value={form.note_type} onChange={set('note_type')} className="h-8 text-[0.8125rem]">
              <option>SOAP</option>
              <option>Progress</option>
              <option>Consultation</option>
              <option>Discharge</option>
            </Select>
            <Button size="sm" tone="ink" loading={extracting} onClick={extract} icon={<Sparkles className="h-4 w-4" />}>
              Extract from note
            </Button>
          </div>
        </div>
        <Textarea
          aria-label="Consultation note"
          value={form.note}
          onChange={set('note')}
          className="mt-3 min-h-[140px]"
          placeholder="S: 34yo with throbbing right-sided headache and photophobia for 3 days. O: Neuro exam normal. A: Migraine without aura. P: Sumatriptan 50mg at onset."
        />
        {extracted && (
          <p className="mt-2 rounded-ctl bg-pen-wash px-3 py-2 text-[0.8125rem] text-pen">
            <span className="font-semibold">Extracted. </span>
            {extracted} Check each row before saving.
          </p>
        )}
      </section>

      <Rows
        title="Symptoms"
        form={form}
        k="symptoms"
        blank={blankSymptom}
        setForm={setForm}
        render={(r, up, i) => (
          <>
            <div className="sm:col-span-5">
              <Input aria-label={`Symptom ${i + 1}`} placeholder="Symptom" value={r.name} onChange={(e) => up({ name: e.target.value })} />
            </div>
            <div className="sm:col-span-3">
              <Select aria-label={`Severity ${i + 1}`} value={r.severity} onChange={(e) => up({ severity: e.target.value })}>
                <option>Mild</option>
                <option>Moderate</option>
                <option>Severe</option>
              </Select>
            </div>
            <div className="sm:col-span-4">
              <Input aria-label={`Duration in days ${i + 1}`} type="number" min={0} value={r.duration_days} onChange={(e) => up({ duration_days: Number(e.target.value) })} placeholder="Days" />
            </div>
          </>
        )}
      />

      <Rows
        title="Diagnoses"
        form={form}
        k="diagnoses"
        blank={blankDiagnosis}
        setForm={setForm}
        render={(r, up, i) => (
          <>
            <div className="sm:col-span-6">
              <Input aria-label={`Diagnosis ${i + 1}`} placeholder="Condition" value={r.condition_name} onChange={(e) => up({ condition_name: e.target.value })} />
            </div>
            <div className="sm:col-span-3">
              <Input aria-label={`ICD-10 code ${i + 1}`} placeholder="ICD-10" className="font-mono" value={r.icd10_code} onChange={(e) => up({ icd10_code: e.target.value })} />
            </div>
            <div className="sm:col-span-3">
              <Select aria-label={`Diagnosis status ${i + 1}`} value={r.status} onChange={(e) => up({ status: e.target.value })}>
                <option>Provisional</option>
                <option>Confirmed</option>
                <option>Controlled</option>
                <option>Ruled-out</option>
                <option>Resolved</option>
              </Select>
            </div>
          </>
        )}
      />

      <datalist id="medication-catalog">
        {medications.map((m) => (
          <option key={m.id} value={m.name}>
            {m.generic_name} {m.strength}
          </option>
        ))}
      </datalist>
      <Rows
        title="Prescriptions"
        form={form}
        k="prescriptions"
        blank={blankRx}
        setForm={setForm}
        render={(r, up, i) => (
          <>
            <div className="sm:col-span-4">
              <Input
                aria-label={`Medication ${i + 1}`}
                list="medication-catalog"
                placeholder="Medication"
                value={r.medication_name}
                onChange={(e) => {
                  const med = medications.find((m) => m.name === e.target.value);
                  up({ medication_name: e.target.value, ...(med && !r.strength ? { strength: med.strength } : {}) });
                }}
              />
            </div>
            <div className="sm:col-span-2">
              <Input aria-label={`Strength ${i + 1}`} placeholder="Strength" value={r.strength} onChange={(e) => up({ strength: e.target.value })} />
            </div>
            <div className="sm:col-span-4">
              <Input aria-label={`Frequency ${i + 1}`} placeholder="How often" value={r.frequency} onChange={(e) => up({ frequency: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Input aria-label={`Days ${i + 1}`} type="number" min={0} value={r.duration_days} onChange={(e) => up({ duration_days: Number(e.target.value) })} />
            </div>
          </>
        )}
      />

      <Rows
        title="Lab results"
        form={form}
        k="labs"
        blank={blankLab}
        setForm={setForm}
        render={(r, up, i) => (
          <>
            <div className="sm:col-span-4">
              <Input aria-label={`Test ${i + 1}`} placeholder="Test" value={r.test_name} onChange={(e) => up({ test_name: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Input aria-label={`Value ${i + 1}`} placeholder="Value" value={r.value} onChange={(e) => up({ value: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Input aria-label={`Unit ${i + 1}`} placeholder="Unit" value={r.unit} onChange={(e) => up({ unit: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Input aria-label={`Reference range ${i + 1}`} placeholder="Range" value={r.reference_range} onChange={(e) => up({ reference_range: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Select aria-label={`Flag ${i + 1}`} value={r.flag} onChange={(e) => up({ flag: e.target.value })}>
                <option>Normal</option>
                <option>High</option>
                <option>Low</option>
                <option>Abnormal</option>
                <option>Critical</option>
              </Select>
            </div>
          </>
        )}
      />

      <section className="border border-ink bg-sheet p-4">
        <Textarea label="Plan" value={form.treatment_plan} onChange={set('treatment_plan')} placeholder="Treatment, advice and follow-up" />
      </section>

      {error && <Notice tone="error">{error}</Notice>}
      <div className="flex justify-end gap-2">
        <Button onClick={() => setForm(initialForm())}>Clear form</Button>
        <Button type="submit" tone="pen" loading={busy}>
          Save visit
        </Button>
      </div>
    </form>
  );
}
