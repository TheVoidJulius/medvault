import { Fragment, useMemo, useState } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import { Empty, Input, Tag } from '../../components/ui';
import { cx, formatDate } from '../../lib/format';
import type { PatientDetail } from '../../lib/types';
import { LabPoint, labGroups } from './records';

/** A tiny trend line: one dot per measurement, out-of-range dots in red. Single values show as one dot. */
function Trend({ points }: { points: LabPoint[] }) {
  const nums = points.filter((p) => p.num !== null);
  if (nums.length === 0) return <span className="text-[0.8125rem] text-ink-3">Text result</span>;
  const w = 120;
  const h = 28;
  const min = Math.min(...nums.map((p) => p.num!));
  const max = Math.max(...nums.map((p) => p.num!));
  const span = max - min || 1;
  const xy = nums.map((p, i) => ({
    x: nums.length === 1 ? w / 2 : 4 + (i * (w - 8)) / (nums.length - 1),
    y: max === min ? h / 2 : 4 + (1 - (p.num! - min) / span) * (h - 8),
    bad: p.flag !== 'Normal',
  }));
  return (
    <svg width={w} height={h} role="img" aria-label={`Trend over ${nums.length} results`} className="overflow-visible">
      {xy.length > 1 && <polyline points={xy.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke="rgb(var(--ink-3))" strokeWidth="1.5" />}
      {xy.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill={p.bad ? 'rgb(var(--trace))' : 'rgb(var(--ink))'} stroke="rgb(var(--sheet))" strokeWidth="1.5" />
      ))}
    </svg>
  );
}

export function Labs({ patient, onOpenVisit }: { patient: PatientDetail; onOpenVisit: (visitId: number) => void }) {
  const groups = useMemo(() => labGroups(patient), [patient]);
  const [q, setQ] = useState('');
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const shown = groups.filter((g) => (!onlyFlagged || g.latest.flag !== 'Normal') && (!q.trim() || g.name.toLowerCase().includes(q.trim().toLowerCase())));
  const flaggedCount = groups.filter((g) => g.latest.flag !== 'Normal').length;

  if (groups.length === 0) return <Empty title="No lab results yet" body="Results recorded with a visit appear here, grouped by test." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
          <Input aria-label="Search lab tests" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a test, e.g. creatinine" className="pl-9" />
        </div>
        <label className="flex h-10 cursor-pointer items-center gap-2 rounded-ctl border border-rule-strong bg-sheet px-3 text-[0.9375rem]">
          <input type="checkbox" checked={onlyFlagged} onChange={(e) => setOnlyFlagged(e.target.checked)} className="h-4 w-4 accent-[rgb(var(--pen))]" />
          Only out of range ({flaggedCount})
        </label>
      </div>
      <p className="text-[0.875rem] text-ink-3">
        {groups.length} tests across {patient.visits.length} visits. Tests whose latest result is out of range come first. Click a test for its full history.
      </p>

      <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
        <table className="nums w-full text-left text-[0.9375rem]">
          <thead className="border-b border-rule text-[0.8125rem] text-ink-3">
            <tr>
              <th className="px-4 py-2.5 font-medium">Test</th>
              <th className="px-3 py-2.5 font-medium">Latest result</th>
              <th className="hidden px-3 py-2.5 font-medium md:table-cell">Normal range</th>
              <th className="hidden px-3 py-2.5 font-medium sm:table-cell">Trend</th>
              <th className="px-4 py-2.5 text-right font-medium">Tested</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((g) => {
              const isOpen = open === g.name;
              const bad = g.latest.flag !== 'Normal';
              return (
                <Fragment key={g.name}>
                  <tr className="cursor-pointer border-b border-rule hover:bg-well/60" onClick={() => setOpen(isOpen ? null : g.name)}>
                    <td className="px-4 py-3">
                      <button type="button" aria-expanded={isOpen} className="flex items-center gap-2 text-left font-semibold">
                        <ChevronDown className={cx('h-4 w-4 shrink-0 text-ink-3 transition-transform', isOpen && 'rotate-180')} aria-hidden />
                        {g.name}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      <span className={cx('font-semibold', bad && 'text-trace')}>
                        {g.latest.value} {g.latest.unit}
                      </span>{' '}
                      {bad ? <Tag tone="danger">{g.latest.flag}</Tag> : <Tag tone="ok">Normal</Tag>}
                      <span className="block text-[0.8125rem] text-ink-3">{formatDate(g.latest.date)}</span>
                    </td>
                    <td className="hidden whitespace-nowrap px-3 py-3 text-ink-2 md:table-cell">{g.latest.range ?? '—'}</td>
                    <td className="hidden px-3 py-3 sm:table-cell">
                      <Trend points={g.points} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-ink-2">
                      {g.points.length}×{g.outOfRange > 0 && <span className="block text-[0.8125rem] text-trace">{g.outOfRange} out of range</span>}
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="border-b border-rule bg-paper/40">
                      <td colSpan={5} className="px-4 py-3">
                        <table className="w-full text-[0.875rem]">
                          <thead className="text-ink-3">
                            <tr>
                              <th className="pb-1 text-left font-medium">Date</th>
                              <th className="pb-1 text-left font-medium">Result</th>
                              <th className="pb-1 text-left font-medium">Normal range</th>
                              <th className="pb-1 text-right font-medium">Visit</th>
                            </tr>
                          </thead>
                          <tbody>
                            {[...g.points].reverse().map((p) => (
                              <tr key={p.tag} className="border-t border-rule">
                                <td className="py-1.5">{formatDate(p.date)}</td>
                                <td className={cx('py-1.5', p.flag !== 'Normal' && 'font-semibold text-trace')}>
                                  {p.value} {p.unit} {p.flag !== 'Normal' && `(${p.flag})`}
                                </td>
                                <td className="py-1.5 text-ink-2">{p.range ?? '—'}</td>
                                <td className="py-1.5 text-right">
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onOpenVisit(p.visitId);
                                    }}
                                    className="font-semibold text-pen hover:underline"
                                  >
                                    Open visit
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {shown.length === 0 && <p className="px-4 py-6 text-center text-[0.9375rem] text-ink-3">No test matches.</p>}
      </div>
    </div>
  );
}
