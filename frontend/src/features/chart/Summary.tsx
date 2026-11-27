import { ReactNode, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Flag, RefreshCw, ShieldCheck } from 'lucide-react';
import { Citations } from '../../components/citations';
import { Button, Notice, Skeleton } from '../../components/ui';
import { cx, formatDate } from '../../lib/format';
import { errorText } from '../../lib/http';
import type { AISummaryResponse, PatientDetail, SummaryStatement } from '../../lib/types';
import { useWorkspace } from '../../workspace';

function Statements({
  items,
  sectionKey,
  summary,
  patientId,
  flagged,
  onFlag,
  tone = 'plain',
}: {
  items: SummaryStatement[];
  sectionKey: string;
  summary: AISummaryResponse;
  patientId: number;
  flagged: Record<string, boolean>;
  onFlag: (key: string) => void;
  tone?: 'plain' | 'alert' | 'gap';
}) {
  if (!items.length) return <p className="text-[0.8125rem] text-ink-3">Nothing recorded for this section.</p>;
  return (
    <ul className="space-y-2">
      {items.map((s, i) => {
        const key = `${sectionKey}:${i}`;
        const isFlagged = !!flagged[key];
        return (
          <li
            key={key}
            className={cx(
              'group rounded-ctl border px-3 py-2.5 text-[0.8125rem] leading-relaxed',
              isFlagged ? 'border-warn/50 bg-warn-wash' : tone === 'alert' && s.citations.length ? 'border-trace/25 bg-trace-wash' : tone === 'gap' ? 'border-dashed border-rule-strong' : 'border-transparent hover:border-rule',
            )}
          >
            {/* An alert with no cited row is an all-clear ("no known allergies"), not a danger. */}
            <span className={tone === 'alert' && s.citations.length ? 'font-medium text-trace' : ''}>{s.text}</span>
            <Citations tags={s.citations} index={summary.citation_index} patientId={patientId} />
            <div className="mt-1.5">
              <button
                type="button"
                aria-pressed={isFlagged}
                onClick={() => onFlag(key)}
                className={cx(
                  'inline-flex items-center gap-1 text-2xs font-semibold transition-colors',
                  isFlagged ? 'text-warn' : 'text-ink-3 opacity-80 hover:text-ink group-hover:opacity-100',
                )}
              >
                <Flag className="h-3 w-3" aria-hidden />
                {isFlagged ? 'Flagged for review' : 'Flag for review'}
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Block({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cx('border border-ink bg-sheet p-4', className)}>
      <h3 className="mb-2 text-[0.875rem] font-bold">{title}</h3>
      {children}
    </section>
  );
}

export function Summary({ patient, stale }: { patient: PatientDetail; stale: number }) {
  const { api, navigate } = useWorkspace();
  const [summary, setSummary] = useState<AISummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});

  const load = async (refresh: boolean) => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await api<AISummaryResponse>(`/api/ai/patients/${patient.id}/summary?refresh=${refresh}`));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient.id, stale]);

  const flaggedCount = useMemo(() => Object.values(flagged).filter(Boolean).length, [flagged]);
  const toggle = (key: string) => setFlagged((f) => ({ ...f, [key]: !f[key] }));

  if (error) return <Notice tone="error">{error}</Notice>;
  if (loading || !summary) {
    return (
      <div className="space-y-3" aria-label="Generating summary">
        <Skeleton className="h-20" />
        <Skeleton className="h-28" />
        <div className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    );
  }

  const v = summary.validation_stats;
  const pct = Math.round(v.grounding_score * 100);
  const common = { summary, patientId: patient.id, flagged, onFlag: toggle };

  return (
    <div className="space-y-4">
      {/* Grounding receipt */}
      <section className="border border-ink bg-sheet p-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <ShieldCheck className={cx('mt-0.5 h-5 w-5 shrink-0', pct === 100 ? 'text-ok' : 'text-warn')} aria-hidden />
            <div>
              <p className="font-bold">
                {v.verified_citations} of {v.total_citations_emitted} citations matched a stored record
              </p>
              <p className="text-[0.8125rem] text-ink-2">
                Built from {v.source_records_indexed} rows in this chart{v.unverified_citations_dropped ? `; ${v.unverified_citations_dropped} unmatched claims were removed` : ''}.{' '}
                {summary.cached ? 'Served from cache' : 'Generated just now'} by <span className="code">{summary.provider_used}</span>.
              </p>
              {flaggedCount > 0 && <p className="mt-1 text-[0.8125rem] font-semibold text-warn">Flagged for review: {flaggedCount}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-32" aria-label={`Grounding ${pct}%`}>
              <div className="flex justify-between text-2xs text-ink-3">
                <span>Grounding</span>
                <span className="code text-ink">{pct}%</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-well">
                <div className={cx('h-full rounded-full', pct === 100 ? 'bg-ok' : 'bg-warn')} style={{ width: `${pct}%` }} />
              </div>
            </div>
            <Button size="sm" onClick={() => load(true)} icon={<RefreshCw className="h-3.5 w-3.5" />}>
              Regenerate
            </Button>
          </div>
        </div>
      </section>

      <p className="flex gap-2 text-2xs leading-relaxed text-ink-3">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden />
        {summary.disclaimer}
      </p>

      <Block title="Overview">
        <Statements items={summary.executive_overview} sectionKey="overview" {...common} />
      </Block>

      {(summary.allergies_and_alerts.length > 0 || summary.data_gaps_and_conflicts.length > 0) && (
        <div className="grid gap-4 md:grid-cols-2">
          <Block title="Allergies and alerts">
            <Statements items={summary.allergies_and_alerts} sectionKey="alerts" tone="alert" {...common} />
          </Block>
          <Block title="Gaps and revisions in the record">
            <Statements items={summary.data_gaps_and_conflicts} sectionKey="gaps" tone="gap" {...common} />
          </Block>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Block title="Recurring symptoms">
          <Statements items={summary.recurring_symptoms} sectionKey="symptoms" {...common} />
        </Block>
        <Block title="Diagnoses over time">
          <Statements items={summary.active_and_past_diagnoses} sectionKey="diagnoses" {...common} />
        </Block>
        <Block title="Medication history">
          <Statements items={summary.medication_history} sectionKey="meds" {...common} />
        </Block>
        <Block title="Lab trends">
          <Statements items={summary.abnormal_test_trends} sectionKey="labs" {...common} />
        </Block>
      </div>

      <section className="overflow-hidden border border-ink bg-sheet">
        <h3 className="border-b border-rule px-4 py-2.5 text-[0.875rem] font-bold">Visit by visit</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[0.8125rem]">
            <thead className="text-ink-3">
              <tr className="border-b border-rule">
                <th className="px-4 py-2 font-medium">Visit</th>
                <th className="px-3 py-2 font-medium">Complaint</th>
                <th className="px-3 py-2 font-medium">Diagnoses</th>
                <th className="px-4 py-2 font-medium">Out-of-range labs</th>
              </tr>
            </thead>
            <tbody>
              {summary.chronological_timeline.map((e) => (
                <tr key={e.visit_id} className="border-b border-rule align-top last:border-0">
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <button
                      type="button"
                      onClick={() => navigate({ view: 'chart', patientId: patient.id, tab: 'visits', focusVisit: e.visit_id })}
                      className="code text-pen hover:underline"
                    >
                      {e.visit_tag}
                    </button>
                    <span className="block text-ink-3">{formatDate(e.visit_date)}</span>
                  </td>
                  <td className="px-3 py-2.5">{e.chief_complaint}</td>
                  <td className="px-3 py-2.5 text-ink-2">{e.diagnoses.join('; ') || '—'}</td>
                  <td className={cx('px-4 py-2.5', e.abnormal_labs.length ? 'text-trace' : 'text-ink-3')}>{e.abnormal_labs.join('; ') || 'None'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
