import { useState } from 'react';
import { cx, monthLabel } from '../lib/format';

/** Horizontal bars for a single measure; one hue, values in text ink beside each bar. */
export function BarList({
  rows,
  onSelect,
  unit,
}: {
  rows: { label: string; value: number }[];
  onSelect?: (label: string) => void;
  unit: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.label}>
          <button
            type="button"
            onClick={() => onSelect?.(r.label)}
            className="group w-full text-left"
            title={`${r.label}: ${r.value} ${unit}`}
          >
            <div className="flex items-baseline justify-between gap-3 text-[0.8125rem]">
              <span className="truncate font-medium text-ink group-hover:text-pen">{r.label}</span>
              <span className="code shrink-0 text-ink-2">{r.value} {unit}</span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-well">
              <div className="h-full rounded-full bg-pen transition-[width]" style={{ width: `${(r.value / max) * 100}%` }} />
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Visit volume per month, columns anchored to the baseline with a hover readout. */
export function MonthColumns({ rows }: { rows: { month: string; count: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...rows.map((r) => r.count));
  const total = rows.reduce((s, r) => s + r.count, 0);
  const shown = hover !== null ? rows[hover] : null;
  return (
    <figure>
      <figcaption className="mb-3 flex items-baseline justify-between text-[0.8125rem]">
        <span className="text-ink-2">
          {shown ? `${monthLabel(shown.month)} ${shown.month.slice(0, 4)}` : 'Last 12 months'}
        </span>
        <span className="code text-ink">{shown ? `${shown.count} visits` : `${total} visits`}</span>
      </figcaption>
      <div className="flex h-36 items-end gap-[2px]" onMouseLeave={() => setHover(null)}>
        {rows.map((r, i) => (
          <button
            key={r.month}
            type="button"
            aria-label={`${monthLabel(r.month)} ${r.month.slice(0, 4)}: ${r.count} visits`}
            onMouseEnter={() => setHover(i)}
            onFocus={() => setHover(i)}
            className="flex h-full flex-1 flex-col justify-end"
          >
            <span
              className={cx('block w-full rounded-t-[4px] transition-colors', hover === i ? 'bg-pen' : 'bg-pen/55')}
              style={{ height: `${Math.max(2, (r.count / max) * 100)}%` }}
            />
          </button>
        ))}
      </div>
      <div className="mt-1.5 flex gap-[2px]">
        {rows.map((r, i) => (
          <span key={r.month} className={cx('code flex-1 text-center text-[10px]', i % 2 ? 'text-transparent sm:text-ink-3' : 'text-ink-3')}>
            {monthLabel(r.month)[0]}
          </span>
        ))}
      </div>
    </figure>
  );
}

const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)'];
const VISIT_TYPE_ORDER = ['Follow-up', 'OPD', 'Emergency', 'Telehealth'];

/** Share of visits by type. Colour follows the visit type, never its rank, so it stays stable across data. */
export function VisitMix({ rows }: { rows: { visit_type: string; count: number }[] }) {
  const total = Math.max(1, rows.reduce((s, r) => s + r.count, 0));
  const ordered = VISIT_TYPE_ORDER.map((t) => ({ type: t, count: rows.find((r) => r.visit_type === t)?.count ?? 0 }));
  return (
    <div>
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-[4px]" role="img" aria-label="Visit type mix">
        {ordered.map((r, i) =>
          r.count ? (
            <span key={r.type} style={{ width: `${(r.count / total) * 100}%`, background: SERIES[i] }} title={`${r.type}: ${r.count}`} />
          ) : null,
        )}
      </div>
      <ul className="mt-3 space-y-1.5 text-[0.8125rem]">
        {ordered.map((r, i) => (
          <li key={r.type} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: SERIES[i] }} aria-hidden />
            <span className="text-ink-2">{r.type}</span>
            <span className="code ml-auto text-ink">{Math.round((r.count / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
