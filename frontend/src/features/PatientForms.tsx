import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { Button, Input, Modal, Notice, Select, Textarea } from '../components/ui';
import { errorText } from '../lib/http';
import type { PatientDetail, Visit } from '../lib/types';
import { useWorkspace } from '../workspace';

export const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const VISIT_TYPES = ['OPD', 'Follow-up', 'Emergency', 'Telehealth'];

const nullIfBlank = (v: string) => (v.trim() ? v.trim() : null);

function Actions({ onCancel, busy, submitLabel }: { onCancel: () => void; busy: boolean; submitLabel: string }) {
  return (
    <div className="mt-6 flex justify-end gap-2 border-t border-rule pt-4">
      <Button onClick={onCancel}>Cancel</Button>
      <Button type="submit" tone="ink" loading={busy}>
        {submitLabel}
      </Button>
    </div>
  );
}

function Grid({ cols = 2, children }: { cols?: 2 | 3; children: ReactNode }) {
  return <div className={cols === 3 ? 'grid gap-3 sm:grid-cols-3' : 'grid gap-3 sm:grid-cols-2'}>{children}</div>;
}

function useSubmit(action: () => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, submit };
}

/* ------------------------------------------------------- Register patient */

const EMPTY_PATIENT = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  sex: 'Female',
  blood_group: '',
  phone: '+91-',
  email: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  allergy: '',
  condition: '',
};

export function RegisterPatientModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (p: PatientDetail) => void }) {
  const { api } = useWorkspace();
  const [form, setForm] = useState(EMPTY_PATIENT);
  const set = (k: keyof typeof EMPTY_PATIENT) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  useEffect(() => {
    if (open) setForm(EMPTY_PATIENT);
  }, [open]);

  const { busy, error, submit } = useSubmit(async () => {
    const created = await api<PatientDetail>('/api/patients', {
      method: 'POST',
      body: JSON.stringify({
        first_name: form.first_name,
        last_name: form.last_name,
        date_of_birth: form.date_of_birth,
        sex: form.sex,
        blood_group: nullIfBlank(form.blood_group),
        phone: form.phone,
        email: nullIfBlank(form.email),
        address: nullIfBlank(form.address),
        emergency_contact_name: nullIfBlank(form.emergency_contact_name),
        emergency_contact_phone: nullIfBlank(form.emergency_contact_phone),
        allergies: form.allergy.trim()
          ? [{ allergen: form.allergy.trim(), reaction: 'Reported by patient at registration', severity: 'Moderate', status: 'Active' }]
          : [],
        medical_history: form.condition.trim() ? [{ condition_name: form.condition.trim(), category: 'Chronic', status: 'Active' }] : [],
      }),
    });
    onCreated(created);
  });

  return (
    <Modal open={open} onClose={onClose} title="Register a patient" description="The MRN is assigned when you save.">
      <form onSubmit={submit} className="space-y-3">
        <Grid>
          <Input label="First name" required value={form.first_name} onChange={set('first_name')} />
          <Input label="Last name" required value={form.last_name} onChange={set('last_name')} />
        </Grid>
        <Grid cols={3}>
          <Input label="Date of birth" type="date" required value={form.date_of_birth} onChange={set('date_of_birth')} />
          <Select label="Sex" value={form.sex} onChange={set('sex')}>
            <option>Female</option>
            <option>Male</option>
            <option>Other</option>
          </Select>
          <Select label="Blood group" value={form.blood_group} onChange={set('blood_group')}>
            <option value="">Not known</option>
            {BLOOD_GROUPS.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </Select>
        </Grid>
        <Grid>
          <Input label="Mobile" required value={form.phone} onChange={set('phone')} placeholder="+91-98XXX-XXXXX" />
          <Input label="Email" type="email" value={form.email} onChange={set('email')} />
        </Grid>
        <Input label="Address" value={form.address} onChange={set('address')} placeholder="House, locality, city, PIN" />
        <Grid>
          <Input label="Emergency contact" value={form.emergency_contact_name} onChange={set('emergency_contact_name')} placeholder="Name (relation)" />
          <Input label="Emergency contact mobile" value={form.emergency_contact_phone} onChange={set('emergency_contact_phone')} />
        </Grid>
        <Grid>
          <Input label="Known allergy" value={form.allergy} onChange={set('allergy')} placeholder="e.g. Penicillin" />
          <Input label="Long-term condition" value={form.condition} onChange={set('condition')} placeholder="e.g. Hypertension" />
        </Grid>
        {error && <Notice tone="error">{error}</Notice>}
        <Actions onCancel={onClose} busy={busy} submitLabel="Register patient" />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------- Edit patient */

export function EditPatientModal({
  patient,
  open,
  onClose,
  onSaved,
}: {
  patient: PatientDetail;
  open: boolean;
  onClose: () => void;
  onSaved: (p: PatientDetail) => void;
}) {
  const { api } = useWorkspace();
  const initial = () => ({
    first_name: patient.first_name,
    last_name: patient.last_name,
    date_of_birth: patient.date_of_birth,
    sex: patient.sex,
    blood_group: patient.blood_group ?? '',
    phone: patient.phone,
    email: patient.email ?? '',
    address: patient.address ?? '',
    emergency_contact_name: patient.emergency_contact_name ?? '',
    emergency_contact_phone: patient.emergency_contact_phone ?? '',
  });
  const [form, setForm] = useState(initial);
  useEffect(() => {
    if (open) setForm(initial());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, patient.id]);
  const set = (k: keyof ReturnType<typeof initial>) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const { busy, error, submit } = useSubmit(async () => {
    const saved = await api<PatientDetail>(`/api/patients/${patient.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        ...form,
        blood_group: nullIfBlank(form.blood_group),
        email: nullIfBlank(form.email),
        address: nullIfBlank(form.address),
        emergency_contact_name: nullIfBlank(form.emergency_contact_name),
        emergency_contact_phone: nullIfBlank(form.emergency_contact_phone),
      }),
    });
    onSaved(saved);
  });

  return (
    <Modal open={open} onClose={onClose} title="Edit demographics" description={patient.mrn}>
      <form onSubmit={submit} className="space-y-3">
        <Grid>
          <Input label="First name" required value={form.first_name} onChange={set('first_name')} />
          <Input label="Last name" required value={form.last_name} onChange={set('last_name')} />
        </Grid>
        <Grid cols={3}>
          <Input label="Date of birth" type="date" required value={form.date_of_birth} onChange={set('date_of_birth')} />
          <Select label="Sex" value={form.sex} onChange={set('sex')}>
            <option>Female</option>
            <option>Male</option>
            <option>Other</option>
          </Select>
          <Select label="Blood group" value={form.blood_group} onChange={set('blood_group')}>
            <option value="">Not known</option>
            {BLOOD_GROUPS.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </Select>
        </Grid>
        <Grid>
          <Input label="Mobile" required value={form.phone} onChange={set('phone')} />
          <Input label="Email" type="email" value={form.email} onChange={set('email')} />
        </Grid>
        <Input label="Address" value={form.address} onChange={set('address')} />
        <Grid>
          <Input label="Emergency contact" value={form.emergency_contact_name} onChange={set('emergency_contact_name')} />
          <Input label="Emergency contact mobile" value={form.emergency_contact_phone} onChange={set('emergency_contact_phone')} />
        </Grid>
        {error && <Notice tone="error">{error}</Notice>}
        <Actions onCancel={onClose} busy={busy} submitLabel="Save changes" />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------- Allergy */

export function AllergyModal({ patient, open, onClose, onSaved }: { patient: PatientDetail; open: boolean; onClose: () => void; onSaved: (allergen: string) => void }) {
  const { api } = useWorkspace();
  const [form, setForm] = useState({ allergen: '', reaction: '', severity: 'Moderate', status: 'Active' });
  useEffect(() => {
    if (open) setForm({ allergen: '', reaction: '', severity: 'Moderate', status: 'Active' });
  }, [open]);
  const { busy, error, submit } = useSubmit(async () => {
    await api(`/api/patients/${patient.id}/allergies`, { method: 'POST', body: JSON.stringify(form) });
    onSaved(form.allergen);
  });
  return (
    <Modal open={open} onClose={onClose} title="Record an allergy" description="Active allergies show on every screen of this chart." width="max-w-lg">
      <form onSubmit={submit} className="space-y-3">
        <Input label="Allergen" required value={form.allergen} onChange={(e) => setForm({ ...form, allergen: e.target.value })} placeholder="e.g. Sulfonamides" />
        <Input label="Reaction" required value={form.reaction} onChange={(e) => setForm({ ...form, reaction: e.target.value })} placeholder="What happened" />
        <Grid>
          <Select label="Severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
            <option>Mild</option>
            <option>Moderate</option>
            <option>Severe</option>
            <option>Life-Threatening</option>
          </Select>
          <Select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option>Active</option>
            <option>Resolved</option>
          </Select>
        </Grid>
        {error && <Notice tone="error">{error}</Notice>}
        <Actions onCancel={onClose} busy={busy} submitLabel="Record allergy" />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------- History */

export function HistoryModal({ patient, open, onClose, onSaved }: { patient: PatientDetail; open: boolean; onClose: () => void; onSaved: (name: string) => void }) {
  const { api } = useWorkspace();
  const blank = { condition_name: '', category: 'Chronic', onset_date: '', status: 'Active', notes: '' };
  const [form, setForm] = useState(blank);
  useEffect(() => {
    if (open) setForm(blank);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const { busy, error, submit } = useSubmit(async () => {
    await api(`/api/patients/${patient.id}/history`, {
      method: 'POST',
      body: JSON.stringify({ ...form, onset_date: nullIfBlank(form.onset_date), notes: nullIfBlank(form.notes) }),
    });
    onSaved(form.condition_name);
  });
  return (
    <Modal open={open} onClose={onClose} title="Add to medical history" width="max-w-lg">
      <form onSubmit={submit} className="space-y-3">
        <Input label="Condition" required value={form.condition_name} onChange={(e) => setForm({ ...form, condition_name: e.target.value })} />
        <Grid cols={3}>
          <Select label="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            <option>Chronic</option>
            <option>Past Illness</option>
            <option>Surgical</option>
            <option>Family</option>
          </Select>
          <Select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option>Active</option>
            <option>Controlled</option>
            <option>Resolved</option>
            <option>Historical</option>
          </Select>
          <Input label="Onset" type="date" value={form.onset_date} onChange={(e) => setForm({ ...form, onset_date: e.target.value })} />
        </Grid>
        <Textarea label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        {error && <Notice tone="error">{error}</Notice>}
        <Actions onCancel={onClose} busy={busy} submitLabel="Add to history" />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------- Edit visit */

export function EditVisitModal({ visit, onClose, onSaved }: { visit: Visit | null; onClose: () => void; onSaved: (v: Visit) => void }) {
  const { api } = useWorkspace();
  const [form, setForm] = useState({ visit_type: 'OPD', chief_complaint: '', vitals_bp: '', vitals_hr: '', vitals_spo2: '', vitals_weight_kg: '', treatment_plan: '' });
  useEffect(() => {
    if (visit)
      setForm({
        visit_type: visit.visit_type,
        chief_complaint: visit.chief_complaint,
        vitals_bp: visit.vitals_bp ?? '',
        vitals_hr: visit.vitals_hr?.toString() ?? '',
        vitals_spo2: visit.vitals_spo2?.toString() ?? '',
        vitals_weight_kg: visit.vitals_weight_kg ?? '',
        treatment_plan: visit.treatment_plan ?? '',
      });
  }, [visit]);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const { busy, error, submit } = useSubmit(async () => {
    if (!visit) return;
    const saved = await api<Visit>(`/api/patients/visits/${visit.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        visit_type: form.visit_type,
        chief_complaint: form.chief_complaint,
        vitals_bp: nullIfBlank(form.vitals_bp),
        vitals_hr: form.vitals_hr ? Number(form.vitals_hr) : null,
        vitals_spo2: form.vitals_spo2 ? Number(form.vitals_spo2) : null,
        vitals_weight_kg: nullIfBlank(form.vitals_weight_kg),
        treatment_plan: nullIfBlank(form.treatment_plan),
      }),
    });
    onSaved(saved);
  });
  return (
    <Modal open={!!visit} onClose={onClose} title={visit ? `Edit visit V-${visit.id}` : 'Edit visit'} width="max-w-xl">
      <form onSubmit={submit} className="space-y-3">
        <Grid>
          <Select label="Visit type" value={form.visit_type} onChange={set('visit_type')}>
            {VISIT_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Input label="Blood pressure" value={form.vitals_bp} onChange={set('vitals_bp')} placeholder="120/80 mmHg" />
        </Grid>
        <Input label="Chief complaint" required value={form.chief_complaint} onChange={set('chief_complaint')} />
        <Grid cols={3}>
          <Input label="Heart rate" type="number" min={20} max={300} value={form.vitals_hr} onChange={set('vitals_hr')} />
          <Input label="SpO₂ %" type="number" min={50} max={100} value={form.vitals_spo2} onChange={set('vitals_spo2')} />
          <Input label="Weight kg" value={form.vitals_weight_kg} onChange={set('vitals_weight_kg')} />
        </Grid>
        <Textarea label="Plan" value={form.treatment_plan} onChange={set('treatment_plan')} />
        {error && <Notice tone="error">{error}</Notice>}
        <Actions onCancel={onClose} busy={busy} submitLabel="Save visit" />
      </form>
    </Modal>
  );
}

export { VISIT_TYPES };
