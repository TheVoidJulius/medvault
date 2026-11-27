import { useEffect, useState } from 'react';
import { BarList, MonthColumns, VisitMix } from '../components/charts';
import { Notice, PageHeader, Panel, Skeleton, Tag, statusTone } from '../components/ui';
import { formatDate } from '../lib/format';
import { errorText } from '../lib/http';
import type { DashboardData } from '../lib/types';
import { useWorkspace } from '../workspace';

export function Overview() {
  const { api, navigate, revision, user } = useWorkspace();
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

  if (error) return <Notice tone="error">{error}</Notice>;
  if (!data) {
    return (
      <div className="space-y-6" aria-label="Loading overview">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-16" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  const c = data.counts;
  const latest = data.recent_visits[0]?.visit_date;
  const firstName = user.full_name.replace(/^Dr\.?\s*/, '').split(/[ ,]/)[0];
  const counts = [
    { label: 'Patients', value: c.total_patients },
    { label: 'Visits', value: c.total_visits },
    { label: 'Diagnoses', value: c.total_diagnoses },
    { label: 'Prescriptions', value: c.total_prescriptions },
    { label: 'Lab results', value: c.total_lab_results },
    { label: 'Allergies', value: c.total_allergies },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Overview for ${firstName}`}
        lede={`${c.total_patients} patients and ${c.total_visits} visits on record${latest ? `, the latest on ${formatDate(latest)}` : ''}. Pick a visit or a flagged lab to open the chart.`}
      />

      <dl className="nums grid grid-cols-2 gap-px overflow-hidden rounded-panel border border-rule bg-rule sm:grid-cols-3 lg:grid-cols-6">
        {counts.map((k) => (
          <div key={k.label} className="bg-sheet px-5 py-4">
            <dt className="text-[0.8125rem] text-ink-3">{k.label}</dt>
            <dd className="mt-0.5 text-2xl font-extrabold tracking-[-0.03em]">{k.value.toLocaleString('en-IN')}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <Panel title="Recent visits" bodyClassName="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[0.8125rem]">
              <thead className="text-ink-3">
                <tr className="border-b border-rule">
                  <th className="px-5 py-2.5 font-medium">Patient</th>
                  <th className="px-3 py-2.5 font-medium">Seen for</th>
                  <th className="hidden px-3 py-2.5 font-medium md:table-cell">Doctor</th>
                  <th className="px-5 py-2.5 text-right font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_visits.map((v) => (
                  <tr
                    key={v.visit_id}
                    onClick={() => navigate({ view: 'chart', patientId: v.patient_id, tab: 'visits', focusVisit: v.visit_id })}
                    className="cursor-pointer border-b border-rule last:border-0 hover:bg-well"
                  >
                    <td className="px-5 py-3 align-top">
                      <span className="block font-semibold">{v.patient_name}</span>
                      {/* De-identified patients are named by their record number; do not print it twice. */}
                      {!v.patient_mrn.endsWith(v.patient_name.split(' ').pop() ?? '') && (
                        <span className="code whitespace-nowrap text-ink-3">{v.patient_mrn}</span>
                      )}
                    </td>
                    <td className="max-w-[22rem] px-3 py-3 align-top">
                      <span className="line-clamp-1 text-ink">{v.primary_diagnosis}</span>
                      <span className="line-clamp-1 text-ink-3">{v.chief_complaint}</span>
                    </td>
                    <td className="hidden px-3 py-3 align-top text-ink-2 md:table-cell">{v.doctor_name.split(',')[0]}</td>
                    <td className="whitespace-nowrap px-5 py-3 text-right align-top">
                      <span className="block">{formatDate(v.visit_date)}</span>
                      <span className="text-ink-3">{v.visit_type}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Labs outside range" aside={<span className="text-2xs text-ink-3">Most recent first</span>} bodyClassName="p-0">
          <ul>
            {(data.flagged_labs ?? []).map((l) => (
              <li key={l.lab_id} className="border-b border-rule last:border-0">
                <button
                  type="button"
                  onClick={() => navigate({ view: 'chart', patientId: l.patient_id, tab: 'visits', focusVisit: l.visit_id })}
                  className="flex w-full items-start justify-between gap-3 px-5 py-3 text-left hover:bg-well"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[0.8125rem] font-semibold">{l.test_name}</span>
                    <span className="block truncate text-2xs text-ink-3">
                      {l.patient_name}, {formatDate(l.result_date)}
                    </span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="code block text-[0.8125rem] text-ink">
                      {l.value.length > 14 ? l.value.slice(0, 14) + '…' : l.value} {l.unit}
                    </span>
                    <Tag tone={statusTone(l.flag)}>{l.flag}</Tag>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <Panel title="Visits per month">
          <MonthColumns rows={data.visits_by_month ?? []} />
        </Panel>
        <Panel title="How patients were seen">
          <VisitMix rows={data.visit_type_mix ?? []} />
        </Panel>
        <Panel title="Most recorded diagnoses">
          <BarList
            unit="dx"
            rows={data.top_conditions.map((r) => ({ label: r.condition, value: r.count }))}
            onSelect={(label) => navigate({ view: 'search', q: `Find records of ${label}` })}
          />
        </Panel>
        <Panel title="Most reported symptoms">
          <BarList
            unit="reports"
            rows={data.top_symptoms.map((r) => ({ label: r.symptom, value: r.count }))}
            onSelect={(label) => navigate({ view: 'search', q: `Find records mentioning ${label}` })}
          />
        </Panel>
      </div>
    </div>
  );
}
