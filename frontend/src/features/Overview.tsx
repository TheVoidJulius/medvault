import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, UserPlus } from 'lucide-react';
import { BarList, MonthColumns } from '../components/charts';
import { Button, Notice, PageHeader, Panel, Skeleton, Tag, statusTone } from '../components/ui';
import { cx, formatDate } from '../lib/format';
import { errorText } from '../lib/http';
import type { AuditEntry, DashboardData } from '../lib/types';
import { useWorkspace } from '../workspace';
import { humanise } from './AuditLog';

function useDashboard() {
  const { api, revision } = useWorkspace();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<DashboardData>('/api/dashboard/stats')
      .then((d) => live && setData(d))
      .catch((e) => live && setError(errorText(e)));
    return () => {
      live = false;
    };
  }, [api, revision]);
  return { data, error };
}

function Counts({ data }: { data: DashboardData }) {
  const c = data.counts;
  const items = [
    { label: 'Patients', value: c.total_patients },
    { label: 'Visits', value: c.total_visits },
    { label: 'Diagnoses', value: c.total_diagnoses },
    { label: 'Prescriptions', value: c.total_prescriptions },
    { label: 'Lab results', value: c.total_lab_results },
  ];
  return (
    <dl className="nums grid grid-cols-2 gap-px border border-ink bg-ink sm:grid-cols-5">
      {items.map((k) => (
        <div key={k.label} className="bg-paper px-4 py-3">
          <dt className="font-mono text-[0.75rem] text-ink-2">{k.label}</dt>
          <dd className="display text-[2.25rem] leading-none">{k.value.toLocaleString('en-IN')}</dd>
        </div>
      ))}
    </dl>
  );
}

function Loading() {
  return (
    <div className="space-y-6" aria-label="Loading overview">
      <Skeleton className="h-12 w-80" />
      <Skeleton className="h-20" />
      <Skeleton className="h-80" />
    </div>
  );
}

/** Doctors: what needs attention. Recent visits and labs out of range, then the two charts worth a glance. */
function DoctorOverview() {
  const { navigate, user } = useWorkspace();
  const { data, error } = useDashboard();
  if (error) return <Notice tone="error">{error}</Notice>;
  if (!data) return <Loading />;
  const firstName = user.full_name.replace(/^Dr\.?\s*/, '').split(/[ ,]/)[0];

  return (
    <div className="space-y-6">
      <PageHeader title={`Overview for ${firstName}`} />
      <Counts data={data} />

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Recent visits" bodyClassName="p-0">
          <ul>
            {data.recent_visits.map((v) => (
              <li key={v.visit_id} className="border-b border-rule last:border-0">
                <button
                  type="button"
                  onClick={() => navigate({ view: 'chart', patientId: v.patient_id, tab: 'visits', focusVisit: v.visit_id })}
                  className="grid w-full grid-cols-[1fr_auto] gap-x-4 px-5 py-3 text-left hover:bg-well/60 sm:grid-cols-[11rem_1fr_auto]"
                >
                  <span className="font-semibold">{v.patient_name}</span>
                  <span className="col-span-2 min-w-0 sm:col-span-1">
                    <span className="block truncate">{v.chief_complaint}</span>
                    <span className="block truncate text-[0.875rem] text-ink-2">{v.primary_diagnosis}</span>
                  </span>
                  <span className="row-start-1 whitespace-nowrap text-right font-mono text-[0.8125rem] sm:row-auto">
                    {formatDate(v.visit_date)}
                    <span className="block text-ink-2">{v.visit_type}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Labs outside range" bodyClassName="p-0">
          <ul>
            {(data.flagged_labs ?? []).map((l) => (
              <li key={l.lab_id} className="border-b border-rule last:border-0">
                <button
                  type="button"
                  onClick={() => navigate({ view: 'chart', patientId: l.patient_id, tab: 'labs' })}
                  className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-well/60"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{l.test_name}</span>
                    <span className="block truncate font-mono text-[0.75rem] text-ink-2">{l.patient_name}</span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="block font-semibold text-trace">
                      {l.value.length > 12 ? `${l.value.slice(0, 12)}…` : l.value} {l.unit}
                    </span>
                    <Tag tone={statusTone(l.flag)}>{l.flag}</Tag>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Most recorded diagnoses">
          <BarList
            unit="dx"
            rows={data.top_conditions.map((r) => ({ label: r.condition, value: r.count }))}
            onSelect={(label) => navigate({ view: 'search', q: `Find records of ${label}` })}
          />
        </Panel>
        <Panel title="Visits per month">
          <MonthColumns rows={data.visits_by_month ?? []} />
        </Panel>
      </div>
    </div>
  );
}

/** Admins: the health of the database itself. Totals, completeness of each field, data source, recent activity. */
function AdminOverview() {
  const { api, navigate, patients, openRegister, revision } = useWorkspace();
  const { data, error } = useDashboard();
  const [activity, setActivity] = useState<AuditEntry[] | null>(null);
  const [source, setSource] = useState<{ name: string; institution: string | null; license: string | null } | null>(null);

  useEffect(() => {
    api<AuditEntry[]>('/api/auth/audit-logs?limit=8')
      .then(setActivity)
      .catch(() => setActivity([]));
    fetch('/api/dashboard/public')
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => s && setSource(s.source))
      .catch(() => undefined);
  }, [api, revision]);

  const completeness = useMemo(() => {
    const total = Math.max(1, patients.length);
    const count = (fn: (p: (typeof patients)[number]) => boolean) => patients.filter(fn).length;
    return [
      { label: 'Has at least one visit', have: count((p) => p.visit_count > 0) },
      { label: 'Blood group recorded', have: count((p) => !!p.blood_group) },
      { label: 'Mobile number recorded', have: count((p) => !!p.phone?.trim()) },
      { label: 'Email recorded', have: count((p) => !!p.email) },
      { label: 'Allergy on file', have: count((p) => p.active_allergies.length > 0) },
    ].map((r) => ({ ...r, total, pct: Math.round((r.have / total) * 100) }));
  }, [patients]);

  if (error) return <Notice tone="error">{error}</Notice>;
  if (!data) return <Loading />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Records administration"
        actions={
          <Button tone="pen" onClick={openRegister} icon={<UserPlus className="h-4 w-4" />}>
            Register patient
          </Button>
        }
      />
      <Counts data={data} />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Data completeness">
          <ul className="space-y-3">
            {completeness.map((r) => (
              <li key={r.label}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-semibold">{r.label}</span>
                  <span className="nums font-mono text-[0.8125rem]">
                    {r.have}/{r.total}
                    <span className={cx('ml-2', r.pct < 50 ? 'text-trace' : r.pct < 90 ? 'text-warn' : 'text-ok')}>{r.pct}%</span>
                  </span>
                </div>
                <div className="mt-1 h-1.5 bg-ink/15">
                  <div className={cx('h-full', r.pct < 50 ? 'bg-trace' : r.pct < 90 ? 'bg-warn' : 'bg-ok')} style={{ width: `${r.pct}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {source && (
            <p className="mt-4 border-t border-rule pt-3 font-mono text-[0.75rem] text-ink-2">
              Source: {source.name}
              {source.institution ? `, ${source.institution}` : ''}
              {source.license ? `. ${source.license}.` : ''}
            </p>
          )}
        </Panel>

        <Panel
          title="Recent activity"
          bodyClassName="p-0"
          aside={
            <Button size="sm" tone="quiet" onClick={() => navigate({ view: 'audit' })}>
              Audit trail <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          }
        >
          {!activity ? (
            <Skeleton className="m-5 h-40" />
          ) : activity.length === 0 ? (
            <p className="px-5 py-4 text-ink-2">No activity yet.</p>
          ) : (
            <ul>
              {activity.map((l) => (
                <li key={l.id} className="grid grid-cols-[1fr_auto] gap-x-3 border-b border-rule px-5 py-2.5 last:border-0">
                  <span className="min-w-0">
                    <span className="block font-semibold">{humanise(l.action)}</span>
                    <span className="block truncate text-[0.875rem] text-ink-2">{l.user_name}</span>
                  </span>
                  <span className="nums whitespace-nowrap font-mono text-[0.75rem] text-ink-2">{l.created_at.slice(0, 16).replace('T', ' ')}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Most recorded diagnoses">
          <BarList unit="dx" rows={data.top_conditions.map((r) => ({ label: r.condition, value: r.count }))} />
        </Panel>
        <Panel title="Visits per month">
          <MonthColumns rows={data.visits_by_month ?? []} />
        </Panel>
      </div>
    </div>
  );
}

export function Overview() {
  const { user } = useWorkspace();
  return user.role_name.toLowerCase() === 'admin' ? <AdminOverview /> : <DoctorOverview />;
}
