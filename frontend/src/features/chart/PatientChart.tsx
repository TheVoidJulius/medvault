import { useCallback, useEffect, useState } from 'react';
import { ClipboardPlus, FileText, FlaskConical, LayoutGrid, MessageSquareText, Pencil, Pill, Plus, ShieldAlert, Sparkles } from 'lucide-react';
import { Button, Notice, Skeleton, Tabs, Tag } from '../../components/ui';
import { ageFrom, formatDate, fullName } from '../../lib/format';
import { errorText } from '../../lib/http';
import type { PatientDetail } from '../../lib/types';
import { ChartTab, useWorkspace } from '../../workspace';
import { AllergyModal, EditPatientModal, HistoryModal } from '../PatientForms';
import { QueryPanel } from '../RecordSearch';
import { NewVisit } from './NewVisit';
import { Summary } from './Summary';
import { ChartOverview } from './ChartOverview';
import { Labs } from './Labs';
import { Medicines } from './Medicines';
import { Visits } from './Visits';

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
  const openVisit = (visitId: number) => navigate({ view: 'chart', patientId, tab: 'visits', focusVisit: visitId });

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
          <p className="font-mono text-[0.75rem] text-ink-2">{patient.mrn}</p>
          <h1 className="display mt-1 text-[3rem] uppercase leading-[0.9] sm:text-[3.5rem]">{fullName(patient)}</h1>
          <p className="mt-1.5 text-[1rem] text-ink-2">
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
      <section aria-label="Allergies" className="flex flex-wrap items-center gap-2 border border-ink bg-sheet px-4 py-2.5">
        <ShieldAlert className={activeAllergies.length ? 'h-4 w-4 text-trace' : 'h-4 w-4 text-ink-3'} aria-hidden />
        {activeAllergies.length === 0 ? (
          <span className="text-[0.9375rem] text-ink-2">No known allergies recorded.</span>
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

      <div>
        <Tabs
          label="Chart sections"
          value={tab}
          onChange={setTab}
          items={[
            { value: 'overview', label: 'Overview', icon: <LayoutGrid className="h-4 w-4" /> },
            { value: 'visits', label: 'Visits', icon: <FileText className="h-4 w-4" />, count: patient.visits.length },
            { value: 'labs', label: 'Lab results', icon: <FlaskConical className="h-4 w-4" /> },
            { value: 'medicines', label: 'Medicines', icon: <Pill className="h-4 w-4" /> },
            { value: 'summary', label: 'AI summary', icon: <Sparkles className="h-4 w-4" /> },
            { value: 'ask', label: 'Ask', icon: <MessageSquareText className="h-4 w-4" /> },
          ]}
        />
        <div className="pt-5">
          {tab === 'overview' && (
            <ChartOverview patient={patient} onOpenVisit={openVisit} onShowTab={setTab} onAddHistory={() => setModal('history')} />
          )}
          {tab === 'visits' && <Visits patient={patient} focusVisit={focusVisit} onChanged={afterWrite} onNewVisit={() => setTab('new-visit')} />}
          {tab === 'labs' && <Labs patient={patient} onOpenVisit={openVisit} />}
          {tab === 'medicines' && <Medicines patient={patient} onOpenVisit={openVisit} />}
          {tab === 'summary' && <Summary patient={patient} stale={summaryStale} />}
          {tab === 'ask' && <QueryPanel scopePatient={patient} />}
          {tab === 'new-visit' && (
            <NewVisit
              patient={patient}
              onSaved={async (visitId) => {
                await afterWrite(`Saved visit V-${visitId} for ${fullName(patient)}.`);
                openVisit(visitId);
              }}
            />
          )}
        </div>
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
