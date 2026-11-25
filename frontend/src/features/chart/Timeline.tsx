import { ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, FlaskConical, Pencil, Pill, Search, Stethoscope } from 'lucide-react';
import { Button, Empty, Input, Select, Tag, statusTone } from '../../components/ui';
import { cx, formatDate } from '../../lib/format';
import type { PatientDetail, Visit } from '../../lib/types';
import { EditVisitModal, VISIT_TYPES } from '../PatientForms';

function visitText(v: Visit) {
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

function Section({ icon, title, children }: { icon: JSX.Element; title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="mb-1.5 flex items-center gap-1.5 text-2xs font-semibold text-ink-3">
        {icon}
        {title}
      </h4>
      {children}
    </div>
  );
}

function VisitEntry({ visit, highlighted, onEdit }: { visit: Visit; highlighted: boolean; onEdit: () => void }) {
  const ref = useRef<HTMLElement>(null);
  const [notesOpen, setNotesOpen] = useState(false);
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
  }, [highlighted]);

  return (
    <article
      ref={ref}
      className={cx(
        'relative rounded-panel border bg-sheet transition-shadow',
        highlighted ? 'border-pen shadow-[0_0_0_3px_rgb(var(--pen)/0.15)]' : 'border-rule',
      )}
    >
      <header className="flex items-start justify-between gap-3 border-b border-rule px-5 py-3.5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="code text-pen">V-{visit.id}</span>
            <Tag tone={visit.visit_type === 'Emergency' ? 'danger' : 'outline'}>{visit.visit_type}</Tag>
            <span className="text-[0.8125rem] text-ink-3">{visit.doctor_name}</span>
          </div>
          <h3 className="mt-1 text-[0.9375rem] font-bold leading-snug">{visit.chief_complaint}</h3>
        </div>
        <Button size="sm" tone="quiet" className="shrink-0" onClick={onEdit} icon={<Pencil className="h-3.5 w-3.5" />}>
          Edit
        </Button>
      </header>

      <div className="grid gap-x-6 gap-y-4 px-5 py-4 md:grid-cols-2">
        {visit.diagnoses.length > 0 && (
          <Section icon={<Stethoscope className="h-3.5 w-3.5" />} title="Diagnoses">
            <ul className="space-y-1.5">
              {visit.diagnoses.map((d) => (
                <li key={d.id} className="text-[0.8125rem]">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className={cx('font-semibold', d.status === 'Ruled-out' && 'text-ink-3 line-through decoration-ink-3/60')}>{d.condition_name}</span>
                    {d.icd10_code && <span className="code text-ink-3">{d.icd10_code}</span>}
                    <Tag tone={d.status === 'Ruled-out' ? 'neutral' : statusTone(d.status)}>{d.status}</Tag>
                  </div>
                  {d.notes && <p className="text-2xs text-ink-2">{d.notes}</p>}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {visit.symptoms.length > 0 && (
          <Section icon={<Activity className="h-3.5 w-3.5" />} title="Symptoms">
            <ul className="space-y-1">
              {visit.symptoms.map((s) => (
                <li key={s.id} className="flex items-baseline justify-between gap-3 text-[0.8125rem]">
                  <span>
                    <span className="font-semibold">{s.name}</span>
                    {s.notes && <span className="text-ink-2">, {s.notes.charAt(0).toLowerCase() + s.notes.slice(1)}</span>}
                  </span>
                  <span className="shrink-0 text-2xs text-ink-3">
                    {s.severity}
                    {s.duration_days ? `, ${s.duration_days}d` : ''}
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {visit.prescriptions.length > 0 && (
          <Section icon={<Pill className="h-3.5 w-3.5" />} title="Prescribed">
            <ul className="space-y-1.5">
              {visit.prescriptions.map((rx) => (
                <li key={rx.id} className="text-[0.8125rem]">
                  <span className="font-semibold">
                    {rx.medication?.name} <span className="font-normal text-ink-2">{rx.medication?.strength}</span>
                  </span>
                  <p className="text-2xs text-ink-2">
                    {rx.frequency}
                    {rx.duration_days ? ` for ${rx.duration_days} days` : ''}
                    {rx.instructions ? `. ${rx.instructions}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {visit.test_results.length > 0 && (
          <Section icon={<FlaskConical className="h-3.5 w-3.5" />} title="Results">
            <table className="w-full text-[0.8125rem]">
              <tbody>
                {visit.test_results.map((t) => (
                  <tr key={t.id} className="align-top">
                    <td className="py-0.5 pr-3">{t.test_name}</td>
                    <td className={cx('code py-0.5 pr-2 text-right', t.flag !== 'Normal' && 'text-trace')}>
                      {t.value} {t.unit}
                    </td>
                    <td className="py-0.5 text-right">{t.flag !== 'Normal' && <Tag tone="danger">{t.flag}</Tag>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}
      </div>

      {(visit.treatment_plan || visit.clinical_notes.length > 0) && (
        <footer className="border-t border-rule px-5 py-3 text-[0.8125rem]">
          {visit.treatment_plan && (
            <p>
              <span className="font-semibold">Plan. </span>
              <span className="text-ink-2">{visit.treatment_plan}</span>
            </p>
          )}
          {visit.clinical_notes.length > 0 && (
            <>
              <button type="button" onClick={() => setNotesOpen((o) => !o)} className="mt-2 text-2xs font-semibold text-pen hover:underline" aria-expanded={notesOpen}>
                {notesOpen ? 'Hide' : 'Show'} {visit.clinical_notes[0].note_type} note
              </button>
              {notesOpen &&
                visit.clinical_notes.map((n) => (
                  <p key={n.id} className="mt-2 whitespace-pre-line rounded-ctl bg-well p-3 leading-relaxed text-ink">
                    {n.content.replace(/ (?=[SOAP]: )/g, '\n')}
                  </p>
                ))}
            </>
          )}
        </footer>
      )}
    </article>
  );
}

export function Timeline({
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

  const visits = useMemo(() => {
    const term = q.trim().toLowerCase();
    return patient.visits.filter((v) => (!type || v.visit_type === type) && (!term || visitText(v).includes(term)));
  }, [patient.visits, q, type]);

  if (patient.visits.length === 0) {
    return <Empty title="No visits yet" body="Record the first visit with symptoms, diagnoses, prescriptions and notes." action={<Button tone="pen" onClick={onNewVisit}>Record first visit</Button>} />;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-[1fr_200px]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
          <Input aria-label="Search this timeline" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search symptoms, diagnoses, drugs, notes" className="pl-9" />
        </div>
        <Select aria-label="Filter by visit type" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All visit types</option>
          {VISIT_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </Select>
      </div>

      {visits.length === 0 ? (
        <Empty
          title="No visit matches"
          body="Nothing in this patient’s visits fits that search."
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
        <ol className="relative space-y-5 border-l border-rule-strong pl-6 sm:ml-[5.5rem] sm:pl-8">
          {visits.map((v) => (
            <li key={v.id} className="relative">
              <span className="absolute -left-[1.85rem] top-5 h-3 w-3 rounded-full border-2 border-paper bg-ink sm:-left-[2.35rem]" aria-hidden />
              <time dateTime={v.visit_date} className="mb-1 block text-[0.8125rem] font-semibold text-ink-2 sm:absolute sm:-left-[8.5rem] sm:top-4 sm:mb-0 sm:w-24 sm:text-right">
                {formatDate(v.visit_date)}
              </time>
              <VisitEntry visit={v} highlighted={focusVisit === v.id} onEdit={() => setEditing(v)} />
            </li>
          ))}
        </ol>
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
