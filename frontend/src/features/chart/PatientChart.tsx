import { useCallback, useEffect, useState } from 'react';
import { ClipboardPlus, FileText, MessageSquareText, Pencil, Plus, ShieldAlert, Sparkles } from 'lucide-react';
import { Button, Notice, Skeleton, Tabs, Tag } from '../../components/ui';
import { VitalsStrip } from '../../components/vitals';
import { ageFrom, formatDate, fullName } from '../../lib/format';
import { errorText } from '../../lib/http';
import type { PatientDetail } from '../../lib/types';
import { ChartTab, useWorkspace } from '../../workspace';
import { AllergyModal, EditPatientModal, HistoryModal } from '../PatientForms';
import { QueryPanel } from '../RecordSearch';
import { NewVisit } from './NewVisit';
import { Summary } from './Summary';
import { Timeline } from './Timeline';

export function PatientChart({ patientId, tab, focusVisit }: { patientId: number; tab: ChartTab; focusVisit?: number }) {
  const { api, navigate, notify, reloadPatients, bumpRevision } = useWorkspace();
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<'edit' | 'allergy' | 'history' | null>(null);
  const [summaryStale, setSummaryStale] = useState(0);

  const load = useCallback(async () => {
    try {
      setPatient(await api<PatientDetail>(`/api/patients/${patientId}`));
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  }, [api, patientId]);

  useEffect(() => {
    load();
  }, [load]);

  const afterWrite = async (message: string) => {
    setModal(null);
    notify(message);
    setSummaryStale((n) => n + 1);
    bumpRevision();
    await Promise.all([load(), reloadPatients()]);
  };

  const setTab = (t: ChartTab) => navigate({ view: 'chart', patientId, tab: t });

  if (error) return <Notice tone="error">{error}</Notice>;
  if (!patient) {
    return (
      <div className="space-y-4" aria-label="Loading chart">
        <Skeleton className="h-24" />
        <Skeleton className="h-56" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const activeAllergies = patient.allergies.filter((a) => a.status === 'Active');
  const lastVisit = patient.visits[0];

  return (
    <div className="space-y-6">
      {/* Identity */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="code text-ink-3">{patient.mrn}</p>
          <h1 className="display mt-1 text-[2.75rem] leading-[0.95]">{fullName(patient)}</h1>
          <p className="mt-1 text-ink-2">
            {lastVisit
              ? `${ageFrom(patient.date_of_birth, new Date(lastVisit.visit_date))} years at last visit (${formatDate(lastVisit.visit_date, { day: undefined })})`
              : `${ageFrom(patient.date_of_birth)} years`}
            , {patient.sex.toLowerCase()}. Blood group{' '}
            {patient.blood_group ? <span className="code text-ink">{patient.blood_group}</span> : <span className="text-warn">not recorded</span>}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setModal('edit')} icon={<Pencil className="h-4 w-4" />}>
            Edit profile
          </Button>
          <Button tone="pen" onClick={() => setTab('new-visit')} icon={<ClipboardPlus className="h-4 w-4" />}>
            New visit
          </Button>
        </div>
      </header>

      {/* Alerts strip: allergies always visible */}
      <section aria-label="Allergies" className="flex flex-wrap items-center gap-2 rounded-panel border border-rule bg-sheet px-4 py-3">
        <ShieldAlert className={activeAllergies.length ? 'h-4 w-4 text-trace' : 'h-4 w-4 text-ink-3'} aria-hidden />
        {activeAllergies.length === 0 ? (
          <span className="text-[0.8125rem] text-ink-2">No known allergies recorded.</span>
        ) : (
          activeAllergies.map((a) => (
            <span key={a.id} className="inline-flex items-center gap-1.5 rounded-ctl bg-trace-wash px-2.5 py-1 text-[0.8125rem] font-semibold text-trace" title={a.reaction}>
              Allergy: {a.allergen}
              <span className="font-normal opacity-80">({a.severity.toLowerCase()})</span>
            </span>
          ))
        )}
        <Button size="sm" tone="quiet" className="ml-auto" onClick={() => setModal('allergy')} icon={<Plus className="h-4 w-4" />}>
          Add allergy
        </Button>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-6">
          {patient.visits.length > 0 && (
            <section aria-label="Vitals across visits">
              <div className="mb-2 flex items-baseline justify-between">
                <h2 className="text-[0.9375rem] font-bold">Vitals across {patient.visits.length} visits</h2>
                <span className="text-2xs text-ink-3">Shaded band is the normal range. Red marks are outside it.</span>
              </div>
              <VitalsStrip visits={patient.visits} onSelectVisit={(id) => navigate({ view: 'chart', patientId, tab: 'timeline', focusVisit: id })} />
            </section>
          )}

          <div>
            <Tabs
              label="Chart sections"
              value={tab}
              onChange={setTab}
              items={[
                { value: 'timeline', label: 'Timeline', icon: <FileText className="h-4 w-4" />, count: patient.visits.length },
                { value: 'summary', label: 'AI summary', icon: <Sparkles className="h-4 w-4" /> },
                { value: 'ask', label: 'Ask this chart', icon: <MessageSquareText className="h-4 w-4" /> },
                { value: 'new-visit', label: 'New visit', icon: <ClipboardPlus className="h-4 w-4" /> },
              ]}
            />
            <div className="pt-5">
              {tab === 'timeline' && <Timeline patient={patient} focusVisit={focusVisit} onChanged={afterWrite} onNewVisit={() => setTab('new-visit')} />}
              {tab === 'summary' && <Summary patient={patient} stale={summaryStale} />}
              {tab === 'ask' && <QueryPanel scopePatient={patient} />}
              {tab === 'new-visit' && (
                <NewVisit
                  patient={patient}
                  onSaved={async (visitId) => {
                    await afterWrite(`Saved visit V-${visitId} for ${fullName(patient)}.`);
                    navigate({ view: 'chart', patientId, tab: 'timeline', focusVisit: visitId });
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Chart spine */}
        <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <section className="rounded-panel border border-rule bg-sheet">
            <header className="flex items-center justify-between border-b border-rule px-4 py-2.5">
              <h2 className="text-[0.875rem] font-bold">Medical history</h2>
              <Button size="sm" tone="quiet" onClick={() => setModal('history')} icon={<Plus className="h-4 w-4" />}>
                Add
              </Button>
            </header>
            {patient.medical_history.length === 0 ? (
              <p className="px-4 py-4 text-[0.8125rem] text-ink-3">No baseline history recorded.</p>
            ) : (
              <ul className="divide-y divide-rule">
                {patient.medical_history.map((h) => (
                  <li key={h.id} className="px-4 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[0.8125rem] font-semibold leading-snug">{h.condition_name}</span>
                      <Tag tone={h.status === 'Active' ? 'warn' : 'neutral'}>{h.status}</Tag>
                    </div>
                    <p className="text-2xs text-ink-3">
                      {h.category}
                      {h.onset_date ? `, since ${formatDate(h.onset_date, { day: undefined })}` : ''}
                    </p>
                    {h.notes && <p className="mt-0.5 text-2xs text-ink-2">{h.notes}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-panel border border-rule bg-sheet px-4 py-3">
            <h2 className="text-[0.875rem] font-bold">Contact</h2>
            <dl className="mt-2 space-y-2 text-[0.8125rem]">
              <div>
                <dt className="text-2xs text-ink-3">Mobile</dt>
                <dd className="code text-[0.8125rem]">{patient.phone || <span className="font-sans text-ink-3">Not recorded</span>}</dd>
              </div>
              {patient.email && (
                <div>
                  <dt className="text-2xs text-ink-3">Email</dt>
                  <dd className="break-all">{patient.email}</dd>
                </div>
              )}
              <div>
                <dt className="text-2xs text-ink-3">Address</dt>
                <dd>{patient.address || <span className="text-ink-3">Not recorded</span>}</dd>
              </div>
              <div>
                <dt className="text-2xs text-ink-3">Emergency contact</dt>
                <dd>
                  {patient.emergency_contact_name || <span className="text-ink-3">Not recorded</span>}
                  {patient.emergency_contact_phone ? (
                    <span className="code block text-[0.8125rem]">{patient.emergency_contact_phone}</span>
                  ) : (
                    patient.emergency_contact_name && <span className="block text-warn">Number missing</span>
                  )}
                </dd>
              </div>
              {lastVisit && (
                <div>
                  <dt className="text-2xs text-ink-3">Attending</dt>
                  <dd>{lastVisit.doctor_name}</dd>
                </div>
              )}
            </dl>
          </section>
        </aside>
      </div>

      <EditPatientModal
        patient={patient}
        open={modal === 'edit'}
        onClose={() => setModal(null)}
        onSaved={(p) => afterWrite(`Saved profile changes for ${p.mrn}.`)}
      />
      <AllergyModal patient={patient} open={modal === 'allergy'} onClose={() => setModal(null)} onSaved={(a) => afterWrite(`Recorded allergy to ${a}.`)} />
      <HistoryModal patient={patient} open={modal === 'history'} onClose={() => setModal(null)} onSaved={(n) => afterWrite(`Added ${n} to medical history.`)} />
    </div>
  );
}
