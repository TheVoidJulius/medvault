import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Pencil, Search } from 'lucide-react';
import { Button, Empty, Input, Select, Tag, statusTone } from '../../components/ui';
import { cx, formatDate } from '../../lib/format';
import type { PatientDetail, Visit } from '../../lib/types';
import { EditVisitModal, VISIT_TYPES } from '../PatientForms';
import { byNewest } from './records';

function searchText(v: Visit) {
  return [
    `v-${v.id}`,
    v.chief_complaint,
    v.doctor_name ?? '',
    v.treatment_plan ?? '',
    ...v.symptoms.map((s) => s.name),
    ...v.diagnoses.map((d) => `${d.condition_name} ${d.icd10_code ?? ''}`),
    ...v.prescriptions.map((p) => p.medication?.name ?? ''),
    ...v.test_results.map((t) => t.test_name),
    ...v.clinical_notes.map((n) => n.content),
  ]
    .join(' ')
    .toLowerCase();
}

type Section = 'diagnoses' | 'medicines' | 'results' | 'vitals' | 'note';

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return <th className={cx('px-4 pb-2 text-[0.8125rem] font-medium text-ink-3', right && 'text-right')}>{children}</th>;
}

function VisitDetail({ visit, onEdit }: { visit: Visit; onEdit: () => void }) {
  const abnormal = visit.test_results.filter((t) => t.flag !== 'Normal').length;
  const sections: { key: Section; label: string; count?: number }[] = [
    { key: 'diagnoses', label: 'Diagnoses', count: visit.diagnoses.length },
    { key: 'medicines', label: 'Medicines', count: visit.prescriptions.length },
    { key: 'results', label: 'Results', count: visit.test_results.length },
    { key: 'vitals', label: 'Vitals and symptoms' },
    { key: 'note', label: 'Note and outcome' },
  ];
  const first: Section = visit.diagnoses.length ? 'diagnoses' : visit.test_results.length ? 'results' : 'vitals';
  const [section, setSection] = useState<Section>(first);

  return (
    <div className="border-t border-rule bg-paper/40">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 pt-3">
        <div role="tablist" aria-label="Visit details" className="flex flex-wrap gap-1">
          {sections.map((s) => (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={section === s.key}
              onClick={() => setSection(s.key)}
              className={cx(
                'rounded-ctl px-3 py-1.5 text-[0.875rem] font-semibold transition-colors',
                section === s.key ? 'bg-ink text-sheet' : 'text-ink-2 hover:bg-well',
              )}
            >
              {s.label}
              {s.count !== undefined && <span className="ml-1.5 opacity-70">{s.count}</span>}
              {s.key === 'results' && abnormal > 0 && <span className="ml-1.5 rounded-full bg-trace px-1.5 text-[0.75rem] text-white">{abnormal}</span>}
            </button>
          ))}
        </div>
        <Button size="sm" tone="quiet" onClick={onEdit} icon={<Pencil className="h-3.5 w-3.5" />}>
          Edit visit
        </Button>
      </div>

      <div className="overflow-x-auto px-0 pb-4 pt-3">
        {section === 'diagnoses' &&
          (visit.diagnoses.length === 0 ? (
            <p className="px-4 text-[0.9375rem] text-ink-3">No diagnoses recorded for this visit.</p>
          ) : (
            <table className="w-full text-left text-[0.9375rem]">
              <thead>
                <tr>
                  <Th>Condition</Th>
                  <Th>Code</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {visit.diagnoses.map((d) => (
                  <tr key={d.id} className="border-t border-rule align-top">
                    <td className={cx('px-4 py-2.5 font-semibold', d.status === 'Ruled-out' && 'text-ink-3 line-through')}>{d.condition_name}</td>
                    <td className="code whitespace-nowrap px-4 py-2.5 text-ink-2">{d.icd10_code ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <Tag tone={d.status === 'Ruled-out' ? 'neutral' : statusTone(d.status)}>{d.status}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

        {section === 'medicines' &&
          (visit.prescriptions.length === 0 ? (
            <p className="px-4 text-[0.9375rem] text-ink-3">No medicines ordered at this visit.</p>
          ) : (
            <table className="w-full text-left text-[0.9375rem]">
              <thead>
                <tr>
                  <Th>Medicine</Th>
                  <Th>Dose</Th>
                  <Th>How often</Th>
                  <Th right>Days</Th>
                </tr>
              </thead>
              <tbody>
                {visit.prescriptions.map((rx) => (
                  <tr key={rx.id} className="border-t border-rule align-top">
                    <td className="px-4 py-2.5 font-semibold">{rx.medication?.name}</td>
                    <td className="whitespace-nowrap px-4 py-2.5">{rx.dosage}</td>
                    <td className="px-4 py-2.5 text-ink-2">{rx.frequency}</td>
                    <td className="nums px-4 py-2.5 text-right">{rx.duration_days ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

        {section === 'results' &&
          (visit.test_results.length === 0 ? (
            <p className="px-4 text-[0.9375rem] text-ink-3">No lab results for this visit.</p>
          ) : (
            <table className="nums w-full text-left text-[0.9375rem]">
              <thead>
                <tr>
                  <Th>Test</Th>
                  <Th>Result</Th>
                  <Th>Normal range</Th>
                  <Th right>Status</Th>
                </tr>
              </thead>
              <tbody>
                {[...visit.test_results]
                  .sort((a, b) => Number(b.flag !== 'Normal') - Number(a.flag !== 'Normal'))
                  .map((t) => (
                    <tr key={t.id} className="border-t border-rule align-top">
                      <td className="px-4 py-2.5 font-semibold">{t.test_name}</td>
                      <td className={cx('whitespace-nowrap px-4 py-2.5', t.flag !== 'Normal' && 'font-semibold text-trace')}>
                        {t.value} {t.unit}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-ink-2">{t.reference_range ?? '—'}</td>
                      <td className="px-4 py-2.5 text-right">
                        <Tag tone={t.flag === 'Normal' ? 'ok' : 'danger'}>{t.flag}</Tag>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ))}

        {section === 'vitals' && (
          <div className="grid gap-4 px-4 sm:grid-cols-2">
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-[0.9375rem]">
              <dt className="text-ink-3">Blood pressure</dt>
              <dd>{visit.vitals_bp ?? '—'}</dd>
              <dt className="text-ink-3">Heart rate</dt>
              <dd>{visit.vitals_hr ? `${visit.vitals_hr} bpm` : '—'}</dd>
              <dt className="text-ink-3">Oxygen</dt>
              <dd>{visit.vitals_spo2 ? `${visit.vitals_spo2}%` : '—'}</dd>
              <dt className="text-ink-3">Temperature</dt>
              <dd>{visit.vitals_temp_c ? `${visit.vitals_temp_c} °C` : '—'}</dd>
              <dt className="text-ink-3">Weight</dt>
              <dd>{visit.vitals_weight_kg ? `${visit.vitals_weight_kg} kg` : '—'}</dd>
            </dl>
            <div>
              <p className="text-[0.8125rem] text-ink-3">Symptoms reported</p>
              {visit.symptoms.length === 0 ? (
                <p className="text-[0.9375rem] text-ink-3">None recorded.</p>
              ) : (
                <ul className="mt-1 space-y-1 text-[0.9375rem]">
                  {visit.symptoms.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-3">
                      <span className="font-semibold">{s.name}</span>
                      <Tag tone={statusTone(s.severity)}>{s.severity}</Tag>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {section === 'note' && (
          <div className="space-y-3 px-4 text-[0.9375rem]">
            {visit.treatment_plan && (
              <p>
                <span className="font-semibold">Outcome. </span>
                <span className="text-ink-2">{visit.treatment_plan}</span>
              </p>
            )}
            {visit.clinical_notes.map((n) => (
              <div key={n.id}>
                <p className="text-[0.8125rem] text-ink-3">{n.note_type} note</p>
                <p className="mt-1 whitespace-pre-line rounded-ctl bg-sheet p-3 leading-relaxed">{n.content.replace(/ (?=[SOAP]: )/g, '\n')}</p>
              </div>
            ))}
            {!visit.treatment_plan && visit.clinical_notes.length === 0 && <p className="text-ink-3">No note recorded.</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function VisitRow({
  visit,
  open,
  highlighted,
  onToggle,
  onEdit,
}: {
  visit: Visit;
  open: boolean;
  highlighted: boolean;
  onToggle: () => void;
  onEdit: () => void;
}) {
  const ref = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }, [highlighted]);
  const lead = visit.diagnoses.find((d) => d.status !== 'Ruled-out');
  const abnormal = visit.test_results.filter((t) => t.flag !== 'Normal').length;

  return (
    <li ref={ref} className={cx('overflow-hidden rounded-panel border bg-sheet', highlighted ? 'border-pen shadow-[0_0_0_3px_rgb(var(--pen)/0.15)]' : 'border-rule')}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-label={`${open ? 'Collapse' : 'Expand'} visit V-${visit.id}: ${visit.chief_complaint}`}
        className="grid w-full grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 px-4 py-3.5 text-left hover:bg-well/60 sm:grid-cols-[8.5rem_1fr_auto_auto]"
      >
        <div className="flex items-center gap-2 sm:block">
          <p className="text-[0.9375rem] font-bold">{formatDate(visit.visit_date)}</p>
          <Tag tone={visit.visit_type === 'Emergency' ? 'danger' : 'outline'} className="sm:mt-1">
            {visit.visit_type}
          </Tag>
        </div>
        <div className="col-span-2 min-w-0 sm:col-span-1">
          <p className="text-[1rem] font-semibold leading-snug">{visit.chief_complaint}</p>
          <p className="truncate text-[0.875rem] text-ink-2">{lead ? lead.condition_name : 'No diagnosis recorded'}</p>
        </div>
        <div className="hidden text-right text-[0.8125rem] text-ink-3 sm:block">
          <p>
            {visit.diagnoses.length} diagnoses, {visit.prescriptions.length} medicines
          </p>
          <p>
            {visit.test_results.length} results
            {abnormal > 0 && <span className="font-semibold text-trace">, {abnormal} out of range</span>}
          </p>
        </div>
        <ChevronDown className={cx('col-start-2 row-start-1 h-5 w-5 justify-self-end text-ink-3 transition-transform sm:col-start-auto sm:row-start-auto', open && 'rotate-180')} aria-hidden />
      </button>
      {open && <VisitDetail visit={visit} onEdit={onEdit} />}
    </li>
  );
}

export function Visits({
  patient,
  focusVisit,
  onChanged,
  onNewVisit,
}: {
  patient: PatientDetail;
  focusVisit?: number;
  onChanged: (message: string) => Promise<void>;
  onNewVisit: () => void;
}) {
  const [q, setQ] = useState('');
  const [type, setType] = useState('');
  const [editing, setEditing] = useState<Visit | null>(null);
  const ordered = useMemo(() => byNewest(patient.visits), [patient.visits]);
  const [openIds, setOpenIds] = useState<Set<number>>(() => new Set(focusVisit ? [focusVisit] : ordered[0] ? [ordered[0].id] : []));
  useEffect(() => {
    if (focusVisit) setOpenIds((s) => new Set(s).add(focusVisit));
  }, [focusVisit]);

  const visits = useMemo(() => {
    const term = q.trim().toLowerCase();
    return ordered.filter((v) => (!type || v.visit_type === type) && (!term || searchText(v).includes(term)));
  }, [ordered, q, type]);

  if (patient.visits.length === 0) {
    return (
      <Empty
        title="No visits yet"
        body="Record the first visit with symptoms, diagnoses, medicines and notes."
        action={
          <Button tone="pen" onClick={onNewVisit}>
            Record first visit
          </Button>
        }
      />
    );
  }

  const toggle = (id: number) =>
    setOpenIds((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-[1fr_200px_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
          <Input aria-label="Search this patient's visits" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a symptom, diagnosis, medicine or test" className="pl-9" />
        </div>
        <Select aria-label="Filter by visit type" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All visit types</option>
          {VISIT_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </Select>
        <Button tone="quiet" onClick={() => setOpenIds(openIds.size ? new Set() : new Set(visits.map((v) => v.id)))}>
          {openIds.size ? 'Collapse all' : 'Expand all'}
        </Button>
      </div>

      <p className="text-[0.875rem] text-ink-3">
        {visits.length === patient.visits.length ? `${visits.length} visits, newest first.` : `${visits.length} of ${patient.visits.length} visits match.`} Click a visit to see its details.
      </p>

      {visits.length === 0 ? (
        <Empty
          title="No visit matches"
          body="Nothing in this patient's visits fits that search."
          action={
            <Button
              onClick={() => {
                setQ('');
                setType('');
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <ul className="space-y-2">
          {visits.map((v) => (
            <VisitRow key={v.id} visit={v} open={openIds.has(v.id)} highlighted={focusVisit === v.id} onToggle={() => toggle(v.id)} onEdit={() => setEditing(v)} />
          ))}
        </ul>
      )}

      <EditVisitModal
        visit={editing}
        onClose={() => setEditing(null)}
        onSaved={(v) => {
          setEditing(null);
          onChanged(`Saved changes to visit V-${v.id}.`);
        }}
      />
    </div>
  );
}
