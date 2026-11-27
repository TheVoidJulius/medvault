import { useLayoutEffect, useRef, useState } from 'react';
import type { Visit } from '../lib/types';
import { cx, formatDate, parseBp } from '../lib/format';

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(640);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const cs = getComputedStyle(el);
      setWidth(Math.max(240, el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)));
    };
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

interface Point {
  visit: Visit;
  x: number;
}

const PAD = { l: 44, r: 16 };

/**
 * The patient's recorded vitals drawn on ECG chart paper: heart rate as a line,
 * blood pressure as a systolic-diastolic span per visit. Two strips, one scale each.
 * Points outside the normal band are drawn in trace red and named in the tooltip.
 */
export function VitalsStrip({ visits, onSelectVisit }: { visits: Visit[]; onSelectVisit?: (id: number) => void }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const ordered = [...visits].sort((a, b) => a.visit_date.localeCompare(b.visit_date));
  if (ordered.length === 0) return null;

  const span = width - PAD.l - PAD.r;
  const pts: Point[] = ordered.map((visit, i) => ({
    visit,
    x: PAD.l + (ordered.length === 1 ? span / 2 : (span * i) / (ordered.length - 1)),
  }));

  const hrStrip = { h: 88, lo: 40, hi: 140, okLo: 60, okHi: 100 };
  const bpStrip = { h: 104, lo: 50, hi: 190, okLo: 60, okHi: 130 };
  const y = (s: typeof hrStrip, v: number) => 10 + (1 - (Math.min(Math.max(v, s.lo), s.hi) - s.lo) / (s.hi - s.lo)) * (s.h - 20);

  const hrPts = pts.filter((p) => p.visit.vitals_hr != null);
  const hrPath = hrPts.map((p, i) => `${i ? 'L' : 'M'}${p.x} ${y(hrStrip, p.visit.vitals_hr!)}`).join(' ');
  const active = hover !== null ? pts[hover] : null;

  const strip = (label: string, unit: string, s: typeof hrStrip, body: JSX.Element, ticks: number[]) => (
    <div className="relative">
      <svg width={width} height={s.h} className="block overflow-visible" role="img" aria-label={`${label} across ${ordered.length} visits`}>
        <rect x={PAD.l} y={y(s, s.okHi)} width={span} height={y(s, s.okLo) - y(s, s.okHi)} fill="rgb(var(--ok) / 0.07)" />
        {ticks.map((t) => (
          <text key={t} x={PAD.l - 8} y={y(s, t) + 3} textAnchor="end" className="fill-ink-3 font-mono text-[10px]">
            {t}
          </text>
        ))}
        <text x={0} y={12} className="fill-ink-2 text-[11px] font-semibold">
          {label}
        </text>
        <text x={0} y={25} className="fill-ink-3 text-[10px]">
          {unit}
        </text>
        {body}
      </svg>
    </div>
  );

  return (
    <div ref={ref} className="relative ecg-paper rounded-ctl border border-rule px-3 pb-2 pt-3" onMouseLeave={() => setHover(null)}>
      {strip(
        'Heart rate',
        'bpm',
        hrStrip,
        <>
          <path d={hrPath} fill="none" stroke="rgb(var(--ink))" strokeWidth="2" strokeLinejoin="round" />
          {hrPts.map((p) => {
            const v = p.visit.vitals_hr!;
            const off = v < hrStrip.okLo || v > hrStrip.okHi;
            return (
              <circle key={p.visit.id} cx={p.x} cy={y(hrStrip, v)} r={4.5} fill={off ? 'rgb(var(--trace))' : 'rgb(var(--ink))'} stroke="rgb(var(--sheet))" strokeWidth="2" />
            );
          })}
        </>,
        [60, 100],
      )}
      {strip(
        'Blood pressure',
        'mmHg',
        bpStrip,
        <>
          {pts.map((p) => {
            const bp = parseBp(p.visit.vitals_bp);
            if (!bp) return null;
            const off = bp.sys >= 140 || bp.dia >= 90 || bp.sys < 90;
            const color = off ? 'rgb(var(--trace))' : 'rgb(var(--ink))';
            return (
              <g key={p.visit.id}>
                <line x1={p.x} x2={p.x} y1={y(bpStrip, bp.sys)} y2={y(bpStrip, bp.dia)} stroke={color} strokeWidth="4" strokeLinecap="round" />
              </g>
            );
          })}
        </>,
        [80, 130],
      )}
      <div className="relative h-5" style={{ width }}>
        {pts.map((p, i) => {
          const show = pts.length <= 8 || i === 0 || i === pts.length - 1 || i === hover;
          return show ? (
            <span key={p.visit.id} className="code absolute -translate-x-1/2 whitespace-nowrap text-[10px] text-ink-3" style={{ left: p.x }}>
              {formatDate(p.visit.visit_date, { day: undefined, month: 'short', year: '2-digit' })}
            </span>
          ) : null;
        })}
      </div>

      {/* Hit targets: one full-height column per visit, wider than the marks. */}
      <div className="absolute inset-x-3 top-3 bottom-7">
        {pts.map((p, i) => {
          const w = Math.max(18, span / Math.max(1, pts.length - 1));
          return (
            <button
              key={p.visit.id}
              type="button"
              aria-label={`Visit V-${p.visit.id} on ${formatDate(p.visit.visit_date)}`}
              onMouseEnter={() => setHover(i)}
              onFocus={() => setHover(i)}
              onClick={() => onSelectVisit?.(p.visit.id)}
              className="absolute top-0 h-full -translate-x-1/2 focus:outline-none"
              style={{ left: p.x, width: w }}
            >
              <span className={cx('mx-auto block h-full w-px', hover === i ? 'bg-ink/30' : 'bg-transparent')} />
            </button>
          );
        })}
      </div>

      {active && (
        <div
          className="pointer-events-none absolute top-2 z-10 w-52 rounded-ctl border border-rule bg-sheet p-2.5 text-2xs shadow-float"
          style={{ left: Math.min(Math.max(active.x - 92, 8), width - 200) }}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-ink">{formatDate(active.visit.visit_date)}</span>
            <span className="code text-ink-3">V-{active.visit.id}</span>
          </div>
          <div className="mt-1 text-ink-2">{active.visit.visit_type}</div>
          <dl className="mt-1.5 grid grid-cols-2 gap-x-2 gap-y-0.5 text-ink">
            <dt className="text-ink-3">HR</dt>
            <dd className="code">{active.visit.vitals_hr ?? '—'} bpm</dd>
            <dt className="text-ink-3">BP</dt>
            <dd className="code">{active.visit.vitals_bp ?? '—'}</dd>
            <dt className="text-ink-3">SpO₂</dt>
            <dd className="code">{active.visit.vitals_spo2 ?? '—'}%</dd>
            <dt className="text-ink-3">Temp</dt>
            <dd className="code">{active.visit.vitals_temp_c ?? '—'} °C</dd>
          </dl>
        </div>
      )}
    </div>
  );
}
