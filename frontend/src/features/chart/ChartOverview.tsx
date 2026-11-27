import { ArrowRight, Plus } from 'lucide-react';
import { Button, Tag } from '../../components/ui';
import { VitalsStrip } from '../../components/vitals';
import { cx, formatDate } from '../../lib/format';
import type { PatientDetail } from '../../lib/types';
import { byNewest, conditionGroups, labGroups, latestVitals } from './records';

function Card({ title, action, children, className }: { title: string; action?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cx('rounded-panel border border-rule bg-sheet', className)}>
      <header className="flex items-center justify-between gap-2 border-b border-rule px-5 py-3">
        <h2 className="text-[1rem] font-bold">{title}</h2>
        {action}
      </header>
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

export function ChartOverview({
  patient,
  onOpenVisit,
  onShowTab,
  onAddHistory,
}: {
  patient: PatientDetail;
  onOpenVisit: (visitId: number) => void;
  onShowTab: (tab: 'visits' | 'labs' | 'medicines') => void;
  onAddHistory: () => void;
}) {
  const visits = byNewest(patient.visits);
  const latest = visits[0];
  const vitals = latestVitals(patient);
  const conditions = conditionGroups(patient).slice(0, 6);
  const flagged = labGroups(patient)
    .filter((g) => g.latest.flag !== 'Normal')
    .slice(0, 8);
  const emergencies = visits.filter((v) => v.visit_type === 'Emergency').length;

  return (
    <div className="space-y-6">
      {/* Vitals at a glance */}
      <section aria-label="Latest vitals" className="grid grid-cols-2 gap-px overflow-hidden rounded-panel border border-rule bg-rule lg:grid-cols-4">
        {vitals.map((v) => (
          <div key={v.label} className="bg-sheet px-5 py-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[0.875rem] text-ink-2">{v.label}</span>
              {v.state !== 'unknown' && (
                <Tag tone={v.state === 'normal' ? 'ok' : 'danger'}>{v.state === 'normal' ? 'Normal' : 'Out of range'}</Tag>
              )}
            </div>
            <p className={cx('mt-1 text-[2rem] font-bold leading-none tracking-[-0.02em]', v.state === 'abnormal' && 'text-trace')}>
              {v.value}
              {v.value !== '—' && <span className="ml-1 text-[0.95rem] font-medium text-ink-3">{v.unit}</span>}
            </p>
            <p className="mt-1.5 text-[0.8125rem] text-ink-3">{v.date ? `Recorded ${formatDate(v.date)}` : 'Not recorded'}. {v.hint}.</p>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Main conditions"
          action={
            <Button size="sm" tone="quiet" onClick={() => onShowTab('visits')}>
              All visits <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          }
        >
          {conditions.length === 0 ? (
            <p className="text-[0.9375rem] text-ink-3">No diagnoses recorded yet.</p>
          ) : (
            <ul className="divide-y divide-rule">
              {conditions.map((c) => (
                <li key={c.name} className="flex items-start justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="text-[0.9375rem] font-semibold leading-snug">{c.name}</p>
                    <p className="text-[0.8125rem] text-ink-3">
                      {c.visits === 1 ? `Recorded once, ${formatDate(c.last)}` : `${c.visits} visits, ${formatDate(c.first, { day: undefined })} to ${formatDate(c.last, { day: undefined })}`}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-tag bg-well px-2 py-0.5 text-[0.8125rem] font-semibold text-ink-2">{c.visits}×</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title="Latest visit"
          action={
            latest && (
              <Button size="sm" tone="quiet" onClick={() => onOpenVisit(latest.id)}>
                Open visit <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )
          }
        >
          {!latest ? (
            <p className="text-[0.9375rem] text-ink-3">No visits recorded yet.</p>
          ) : (
            <dl className="space-y-3 text-[0.9375rem]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{formatDate(latest.visit_date)}</span>
                <Tag tone={latest.visit_type === 'Emergency' ? 'danger' : 'outline'}>{latest.visit_type}</Tag>
                <span className="text-ink-3">{latest.doctor_name}</span>
              </div>
              <div>
                <dt className="text-[0.8125rem] text-ink-3">Reason for visit</dt>
                <dd className="font-semibold">{latest.chief_complaint}</dd>
              </div>
              {latest.diagnoses.length > 0 && (
                <div>
                  <dt className="text-[0.8125rem] text-ink-3">Diagnosed with</dt>
                  <dd>
                    <ul className="list-disc pl-5">
                      {latest.diagnoses.slice(0, 3).map((d) => (
                        <li key={d.id}>{d.condition_name}</li>
                      ))}
                    </ul>
                    {latest.diagnoses.length > 3 && <span className="text-[0.8125rem] text-ink-3">and {latest.diagnoses.length - 3} more</span>}
                  </dd>
                </div>
              )}
              {latest.treatment_plan && (
                <div>
                  <dt className="text-[0.8125rem] text-ink-3">Outcome</dt>
                  <dd className="text-ink-2">{latest.treatment_plan}</dd>
                </div>
              )}
            </dl>
          )}
        </Card>
      </div>

      <Card
        title={`Results to review${flagged.length ? ` (${flagged.length})` : ''}`}
        action={
          <Button size="sm" tone="quiet" onClick={() => onShowTab('labs')}>
            All lab results <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        }
      >
        {flagged.length === 0 ? (
          <p className="text-[0.9375rem] text-ink-3">Every test's most recent result is within its normal range.</p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="nums w-full text-left text-[0.9375rem]">
              <thead className="text-[0.8125rem] text-ink-3">
                <tr>
                  <th className="px-5 pb-2 font-medium">Test</th>
                  <th className="px-3 pb-2 font-medium">Latest result</th>
                  <th className="hidden px-3 pb-2 font-medium sm:table-cell">Normal range</th>
                  <th className="px-5 pb-2 text-right font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {flagged.map((g) => (
                  <tr key={g.name} className="border-t border-rule">
                    <td className="px-5 py-2.5 font-semibold">{g.name}</td>
                    <td className="px-3 py-2.5">
                      <span className="font-semibold text-trace">
                        {g.latest.value} {g.latest.unit}
                      </span>{' '}
                      <Tag tone="danger">{g.latest.flag}</Tag>
                    </td>
                    <td className="hidden px-3 py-2.5 text-ink-2 sm:table-cell">{g.latest.range ?? '—'}</td>
                    <td className="whitespace-nowrap px-5 py-2.5 text-right text-ink-2">{formatDate(g.latest.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {patient.visits.length > 0 && (
        <section aria-label="Vitals across visits">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-[1rem] font-bold">
              Vitals over {patient.visits.length} visits{emergencies ? `, ${emergencies} in emergency` : ''}
            </h2>
            <span className="text-[0.8125rem] text-ink-3">Green band is normal. Red marks are out of range. Click a point to open that visit.</span>
          </div>
          <VitalsStrip visits={patient.visits} onSelectVisit={onOpenVisit} />
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Medical history"
          action={
            <Button size="sm" tone="quiet" onClick={onAddHistory} icon={<Plus className="h-4 w-4" />}>
              Add
            </Button>
          }
        >
          {patient.medical_history.length === 0 ? (
            <p className="text-[0.9375rem] text-ink-3">No long-term history recorded.</p>
          ) : (
            <ul className="divide-y divide-rule">
              {patient.medical_history.map((h) => (
                <li key={h.id} className="py-2.5 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-[0.9375rem] font-semibold">{h.condition_name}</span>
                    <Tag tone={h.status === 'Active' ? 'warn' : 'neutral'}>{h.status}</Tag>
                  </div>
                  {h.notes && <p className="text-[0.8125rem] text-ink-2">{h.notes}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Contact">
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-[0.9375rem]">
            <dt className="text-ink-3">Mobile</dt>
            <dd>{patient.phone || <span className="text-ink-3">Not recorded</span>}</dd>
            <dt className="text-ink-3">Email</dt>
            <dd className="break-all">{patient.email || <span className="text-ink-3">Not recorded</span>}</dd>
            <dt className="text-ink-3">Address</dt>
            <dd>{patient.address || <span className="text-ink-3">Not recorded</span>}</dd>
            <dt className="text-ink-3">Emergency contact</dt>
            <dd>
              {patient.emergency_contact_name || <span className="text-ink-3">Not recorded</span>}
              {patient.emergency_contact_phone && <span className="block">{patient.emergency_contact_phone}</span>}
            </dd>
          </dl>
        </Card>
      </div>
    </div>
  );
}
