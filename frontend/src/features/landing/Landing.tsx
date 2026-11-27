import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { LogoMark } from '../../components/Logo';
import { cx } from '../../lib/format';
import type { HeartStage } from './Heart3D';

const Heart3D = lazy(() => import('./Heart3D'));

interface PublicStats {
  patients: number;
  real_patients: number;
  visits: number;
  emergency_visits: number;
  diagnoses: number;
  distinct_conditions: number;
  prescriptions: number;
  lab_results: number;
  abnormal_labs: number;
  symptoms: number;
  notes: number;
  first_year: number | null;
  last_year: number | null;
  source: { name: string; institution: string | null; license: string | null; url: string | null };
}

const INK = '#111317';
const CANVAS = '#B4B7BD';
const n = (v: number | undefined) => (v ?? 0).toLocaleString('en-IN');
const clamp = (v: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));
const ease = (v: number) => v * v * (3 - 2 * v);
/** Map p from [a, b] to [0, 1], clamped and eased. */
const seg = (p: number, a: number, b: number) => ease(clamp((p - a) / (b - a)));

function webglAvailable(): boolean {
  if (typeof window === 'undefined' || typeof (window as unknown as { WebGL2RenderingContext?: unknown }).WebGL2RenderingContext === 'undefined') return false;
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch {
    return false;
  }
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => setReduced(!!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches), []);
  return reduced;
}

function useCountUp(target: number, run: boolean, ms = 1800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!run || !target) {
      setV(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, Math.max(0, (t - t0) / ms));
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, ms]);
  return v;
}

function Mono({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cx('font-mono text-[11px] leading-[1.4] tracking-[-0.01em]', className)}>{children}</span>;
}

function Cta({ onClick, className, children }: { onClick: () => void; className?: string; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={cx('whitespace-nowrap font-mono text-[12px] text-pen hover:underline focus-visible:underline', className)}>
      [ {children} ]
    </button>
  );
}

/** Thin culture-dish contour with scattered cells, behind the heart in the first step. */
function Contour({ opacity }: { opacity: number }) {
  const dots = [
    [130, 150, 9, 5], [210, 95, 6, 4], [330, 62, 10, 4], [460, 50, 7, 5], [610, 54, 12, 5], [750, 74, 8, 4], [865, 128, 10, 6],
    [930, 240, 5, 9], [955, 370, 6, 11], [925, 525, 7, 5], [78, 310, 5, 10], [62, 455, 6, 8], [115, 600, 9, 5], [870, 655, 9, 5],
    [220, 705, 12, 4], [690, 722, 10, 4], [520, 762, 14, 4], [380, 752, 9, 4],
  ];
  return (
    <svg viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid meet" className="absolute inset-0 h-full w-full transition-opacity duration-300" style={{ opacity }} aria-hidden fill="none" stroke={INK} strokeWidth="1.3">
      <path d="M170 270 C 170 130, 340 100, 500 105 C 680 110, 830 150, 840 305 C 846 410, 785 425, 805 520 C 822 605, 750 680, 605 672 C 520 667, 470 710, 385 692 C 260 666, 205 636, 195 560 C 188 495, 140 475, 150 395 C 156 345, 170 325, 170 270 Z" />
      {dots.map(([x, y, rx, ry], i) => (
        <ellipse key={i} cx={x} cy={y} rx={rx} ry={ry} />
      ))}
    </svg>
  );
}

function Stamp() {
  return (
    <svg viewBox="0 0 160 160" className="h-24 w-24 shrink-0 sm:h-28 sm:w-28" aria-hidden>
      <defs>
        <path id="stamp-ring" d="M80 80 m -58 0 a 58 58 0 1 1 116 0 a 58 58 0 1 1 -116 0" />
      </defs>
      <circle cx="80" cy="80" r="76" fill="none" stroke="rgb(var(--pen))" strokeWidth="1.5" />
      <circle cx="80" cy="80" r="40" fill="none" stroke="rgb(var(--pen))" strokeWidth="1" />
      <g className="motion-safe:animate-[spin_28s_linear_infinite]" style={{ transformOrigin: '80px 80px' }}>
        <text className="fill-pen font-mono text-[10.5px] tracking-[0.08em]">
          <textPath href="#stamp-ring">every claim cites a stored row ✳ every claim cites a stored row ✳</textPath>
        </text>
      </g>
      <g transform="translate(64 64)">
        <rect width="32" height="32" rx="8" fill="rgb(var(--pen))" />
        <path d="M10.5 8.5H8v15h2.5M21.5 8.5H24v15h-2.5" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12.5 11.5h7M12.5 20.5h7" stroke="#fff" strokeOpacity=".55" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M12.5 16h7" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
      </g>
    </svg>
  );
}

const STEPS = [
  {
    n: '1',
    title: 'Store',
    head: 'One record per patient',
    text: 'Every admission, diagnosis, drug order and lab result is a row in one relational database, linked to the visit it came from.',
  },
  {
    n: '2',
    title: 'Summarise',
    head: 'Read back with sources',
    text: 'The AI turns those rows into a summary. Each sentence carries a tag that opens the exact row it came from; anything it cannot cite is dropped.',
  },
  {
    n: '3',
    title: 'Ask',
    head: 'Answers, or an honest no',
    text: 'Ask in plain English across every patient. Matching rows come back ranked, or the record says plainly that nothing matches.',
  },
];

export function Landing({ onSignIn }: { onSignIn: () => void }) {
  const reduced = useReducedMotion();
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [gl] = useState(webglAvailable);
  const [glReady, setGlReady] = useState(false);
  const [p, setP] = useState(0);
  const storyRef = useRef<HTMLElement>(null);
  const stage = useRef<HeartStage>({ white: 0, scale: 1, x: 0, y: 0, spin: 0 });

  useEffect(() => {
    fetch('/api/dashboard/public')
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => s && setStats(s))
      .catch(() => undefined);
  }, []);

  // Scroll through the sticky story: 0 at its top, 1 when its last screen is reached.
  useEffect(() => {
    const onScroll = () => {
      const el = storyRef.current;
      if (!el) return;
      const total = el.offsetHeight - window.innerHeight;
      const prog = total > 0 ? clamp(-el.getBoundingClientRect().top / total) : 0;
      setP(prog);
      const wide = window.innerWidth >= 1024;
      stage.current = {
        white: seg(prog, 0.28, 0.5),
        // Step 3: the heart shrinks and settles into the chest of the torso
        scale: (wide ? 1.18 : 1) * (1 - 0.7 * seg(prog, 0.62, 0.86)),
        x: 0.035 * seg(prog, 0.62, 0.86),
        y: 0.13 * seg(prog, 0.62, 0.86),
        spin: prog * Math.PI * 2.2,
      };
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  const onReady = useCallback(() => setGlReady(true), []);
  const totalRows = stats ? stats.visits + stats.diagnoses + stats.prescriptions + stats.lab_results + stats.symptoms + stats.notes : 0;
  const indexed = useCountUp(totalRows, !reduced && !!stats);
  const pct = totalRows ? Math.round((indexed / totalRows) * 100) : 0;
  const real = (stats?.real_patients ?? 0) > 0;
  const years = stats?.first_year ? `${stats.first_year}–${stats.last_year}` : '';
  const phase = p < 0.33 ? 0 : p < 0.62 ? 1 : 2;
  const torso = seg(p, 0.6, 0.8);
  const blob = seg(p, 0.66, 1);

  const table = stats
    ? [
        { name: 'Admissions and ED visits', desc: 'Each hospital admission or emergency attendance, with triage vitals and where the patient went next.', count: stats.visits, unit: 'visits' },
        { name: 'Diagnoses', desc: `Discharge diagnoses in ICD-9 and ICD-10, ranked by importance. ${n(stats.distinct_conditions)} distinct conditions.`, count: stats.diagnoses, unit: 'codes' },
        { name: 'Prescriptions', desc: 'Drugs ordered during the stay, with dose, route and doses per day.', count: stats.prescriptions, unit: 'orders' },
        { name: 'Lab results', desc: `First result of each key test per admission, with its reference range. ${n(stats.abnormal_labs)} fall outside it.`, count: stats.lab_results, unit: 'results' },
        { name: 'Triage complaints', desc: 'What patients told the emergency desk, with their pain score.', count: stats.symptoms, unit: 'entries' },
      ]
    : [];
  const maxCount = Math.max(1, ...table.map((r) => r.count));

  return (
    <div className="landing relative min-h-screen bg-[#B4B7BD] text-[#111317] [--ink:17_19_23] [--pen:31_53_198]">
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-[0.16] mix-blend-multiply"
        aria-hidden
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />

      <header className="fixed inset-x-0 top-0 z-30 flex items-start justify-between gap-6 border-b border-[#111317]/15 bg-[#B4B7BD]/90 px-4 py-3 backdrop-blur-sm sm:px-6">
        <a href="#/" className="flex shrink-0 items-center gap-2">
          <LogoMark className="h-6 w-6" />
          <span className="display text-[1.05rem] uppercase leading-none tracking-[0.01em]">MedVault</span>
        </a>
        <Mono className="hidden md:block">Where patient records meet reasoning.</Mono>
        <Mono className="hidden lg:block">{real ? `Source: MIMIC-IV, ${stats?.source.institution?.split(',')[0]}` : 'Grounded AI'}</Mono>
        <Cta onClick={onSignIn}>Open the records</Cta>
      </header>

      {/* Sticky 3D story */}
      <section ref={storyRef} className="relative z-10 h-[320svh]" aria-label="How MedVault works">
        <div className="sticky top-0 flex h-[100svh] flex-col overflow-hidden px-4 pb-4 pt-16 sm:px-6">
          <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_auto] gap-4 lg:grid-cols-[220px_minmax(0,1fr)_300px] lg:grid-rows-1 lg:gap-8">
            {/* Left: steps and indexer */}
            <div className="hidden flex-col justify-between py-6 lg:flex">
              <ol className="border-l border-[#111317]">
                {STEPS.map((s, i) => (
                  <li key={s.n} className="flex items-center gap-4 py-3 before:block before:h-px before:w-3 before:bg-[#111317]">
                    <Mono className={cx('transition-colors', phase === i ? 'text-pen' : 'opacity-60')}>({s.n})</Mono>
                    <Mono className={cx('transition-colors', phase === i ? 'text-[#111317]' : 'opacity-60')}>{s.title}</Mono>
                  </li>
                ))}
              </ol>
              <div>
                <Mono className="block text-[13px]">{String(pct).padStart(3, '0')}%</Mono>
                <Mono className="block opacity-70">{stats ? `${n(indexed)} rows indexed` : 'Indexing'}</Mono>
              </div>
            </div>

            {/* Centre: the plate */}
            <div className="relative min-h-0">
              <div className="absolute inset-0">
                <Contour opacity={1 - seg(p, 0.15, 0.35)} />
                {/* blue ink spreading behind the torso */}
                <svg viewBox="0 0 200 200" preserveAspectRatio="xMidYMid meet" className="absolute inset-0 h-full w-full" aria-hidden>
                  <path
                    d="M100 24 C 142 18, 178 50, 178 96 C 178 142, 150 178, 104 180 C 58 182, 22 150, 22 104 C 22 58, 58 30, 100 24 Z"
                    fill="rgb(var(--pen))"
                    style={{ transformOrigin: '100px 100px', transform: `scale(${blob}) rotate(${blob * 50}deg)` }}
                  />
                  {Array.from({ length: 16 }).map((_, i) => {
                    const a = (i / 16) * Math.PI * 2;
                    return (
                      <circle key={i} cx={100 + Math.cos(a) * 92} cy={100 + Math.sin(a) * 92} r={1.2 + (i % 3) * 0.9} fill="rgb(var(--pen))" opacity={seg(p, 0.8 + (i % 4) * 0.03, 0.95)} />
                    );
                  })}
                </svg>
                <img
                  src="/art/torso.png"
                  alt=""
                  aria-hidden
                  className="absolute left-1/2 top-1/2 h-[88%] max-w-none -translate-x-1/2 -translate-y-1/2 object-contain"
                  style={{ opacity: torso, filter: blob > 0.55 ? 'brightness(0) invert(0.93)' : undefined, transition: 'filter 300ms' }}
                />
              </div>
              {gl && !reduced ? (
                <div className={cx('absolute inset-0 transition-opacity duration-700', glReady ? 'opacity-100' : 'opacity-0')}>
                  <Suspense fallback={null}>
                    <Heart3D stage={stage} onReady={onReady} reducedMotion={reduced} />
                  </Suspense>
                </div>
              ) : (
                <img
                  src="/art/heart-anterior.png"
                  alt="Engraving of the human heart from Gray's Anatomy (1918)"
                  className="absolute left-1/2 top-1/2 w-[70%] max-w-[560px] -translate-x-1/2 -translate-y-1/2 mix-blend-multiply transition-transform duration-300"
                  style={{ transform: `translate(-50%, -50%) scale(${1 - 0.6 * seg(p, 0.62, 0.86)})` }}
                />
              )}
              {gl && !reduced && (
                <Mono className="pointer-events-none absolute bottom-2 left-1/2 -translate-x-1/2 opacity-70">Drag to rotate</Mono>
              )}
            </div>

            {/* Right: the current step */}
            <div className="flex flex-col justify-end lg:justify-center lg:py-6">
              <div key={phase} className="motion-safe:animate-rise">
                <Mono className="text-pen">
                  ({STEPS[phase].n}) {STEPS[phase].title}
                </Mono>
                <h2 className="display mt-2 text-[2.1rem] uppercase leading-[0.9] sm:text-[2.6rem]">{STEPS[phase].head}</h2>
                <p className="mt-3 max-w-sm font-mono text-[12px] leading-[1.5]">{STEPS[phase].text}</p>
              </div>
              <div className="mt-4 flex gap-1.5 lg:hidden" aria-hidden>
                {STEPS.map((s, i) => (
                  <span key={s.n} className={cx('h-1 flex-1', i === phase ? 'bg-pen' : 'bg-[#111317]/25')} />
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-end justify-between gap-4">
            <Stamp />
            <Mono className="hidden text-center sm:block">Scroll</Mono>
            <Mono className="text-right">
              {real ? `${n(stats?.real_patients)} real de-identified patients` : 'Patient records'}
              <br />
              {years}
            </Mono>
          </div>
        </div>
      </section>

      {/* Statement */}
      <section className="relative z-10 px-4 py-16 sm:px-6 sm:py-24">
        <div className="mx-auto max-w-[1320px]">
          <h2 className="display max-w-5xl text-[12vw] uppercase leading-[0.86] sm:text-[8vw] xl:text-[7.2rem]">Every record, read back with its sources</h2>

          <div className="mt-10 grid gap-10 border-t-2 border-[#111317] pt-10 md:grid-cols-2 xl:grid-cols-[1fr_0.9fr_1fr]">
            <div className="space-y-6">
              <div>
                <Mono className="block opacity-70">Summaries grounded in SQL</Mono>
                <p className="mt-2 max-w-sm font-mono text-[12px] leading-[1.5]">
                  The summary is built from counts, status changes and lab trends computed over stored rows. A validator drops any sentence whose citation is not a real row.
                </p>
              </div>
              <div className="max-w-md border border-[#111317] bg-[#C3C6CB] p-4">
                <Mono className="block opacity-70">How a summary line looks (illustration)</Mono>
                <p className="mt-2 text-[1rem] leading-snug">
                  Acute kidney failure recorded across three admissions; creatinine fell from 3.1 to 1.4 mg/dL.{' '}
                  {['V-112', 'DX-1840', 'LAB-2311'].map((t) => (
                    <span key={t} className="mr-1 inline-block border border-pen px-1 font-mono text-[11px] text-pen">
                      {t}
                    </span>
                  ))}
                </p>
                <Mono className="mt-2 block opacity-70">Each tag opens the exact row it cites.</Mono>
              </div>
            </div>

            <div className="hidden items-center justify-center xl:flex">
              <img src="/art/heart-posterior.png" alt="Engraving of the heart, back view, from Gray's Anatomy (1918)" className="w-full max-w-xs mix-blend-multiply" loading="lazy" />
            </div>

            <div>
              <Mono className="block opacity-70">How a question becomes rows</Mono>
              <ol className="mt-4 border-l border-[#111317]">
                {[
                  ['Question', '“Which patients had heart failure?”'],
                  ['Filters', 'Dates, record types and clinical terms, with synonyms.'],
                  ['Scores', 'Every stored row is scored; exact phrases count most.'],
                  ['Answer', 'Top rows with citations, or an explicit “nothing matches”.'],
                ].map(([t, d], i) => (
                  <li key={t} className="relative pb-5 pl-6 last:pb-0">
                    <span className="absolute -left-[5px] top-1 h-[9px] w-[9px] rounded-full border border-[#111317] bg-[#B4B7BD]" />
                    <Mono className="block opacity-70">0{i + 1}</Mono>
                    <p className="text-[0.95rem] font-semibold">{t}</p>
                    <Mono className="block opacity-80">{d}</Mono>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      {/* Numbers */}
      <section className="relative z-10 px-4 sm:px-6">
        <div className="mx-auto grid max-w-[1320px] grid-cols-2 gap-6 md:grid-cols-4">
          {[
            { v: n(stats?.patients), l: real ? 'real patients' : 'patients' },
            { v: n(stats?.visits), l: 'admissions and ED visits' },
            { v: n(stats?.lab_results), l: 'lab results' },
            { v: years || '—', l: 'years of care' },
          ].map((s) => (
            <div key={s.l} className="border-t border-[#111317] pt-2">
              <p className="display text-[2.6rem] leading-none sm:text-[3.2rem]">{s.v}</p>
              <Mono className="opacity-80">{s.l}</Mono>
            </div>
          ))}
        </div>
      </section>

      {/* The data */}
      <section id="data" className="relative z-10 px-4 py-16 sm:px-6 sm:py-24">
        <div className="mx-auto max-w-[1320px] border-2 border-[#111317] p-5 sm:p-8">
          <h2 className="display text-[15vw] uppercase leading-[0.85] sm:text-[7rem]">The data</h2>
          <p className="mt-4 max-w-2xl font-mono text-[12px] leading-[1.55]">
            {real ? (
              <>
                Real, de-identified patients of {stats?.source.institution}, from the {stats?.source.name}, published on PhysioNet under the {stats?.source.license}.
                Names, addresses and exact dates were removed by the publishers; dates here are shifted back into each patient&rsquo;s real era.
              </>
            ) : (
              'Synthetic demonstration records.'
            )}
          </p>

          <ul className="mt-8 divide-y divide-[#111317]/40 border-y border-[#111317] md:hidden">
            {table.map((r) => (
              <li key={r.name} className="py-4">
                <div className="flex items-baseline justify-between gap-3">
                  <Mono className="text-[12px]">{r.name}</Mono>
                  <Mono className="text-[12px] text-pen">{n(r.count)}</Mono>
                </div>
                <p className="mt-1 font-mono text-[11px] leading-[1.45] opacity-80">{r.desc}</p>
                <div className="mt-2 h-1.5 bg-[#111317]/15">
                  <div className="h-full bg-pen" style={{ width: `${(r.count / maxCount) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>

          <table className="mt-8 hidden w-full text-left md:table">
            <thead>
              <tr className="border-b border-[#111317]">
                {['Table', 'What it holds', 'Rows', 'Relative size'].map((h) => (
                  <th key={h} className="pb-3 pr-6 font-mono text-[11px] font-normal">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.map((r) => (
                <tr key={r.name} className="border-b border-[#111317]/50 align-top">
                  <td className="py-5 pr-6 font-mono text-[12px]">{r.name}</td>
                  <td className="max-w-md py-5 pr-6 font-mono text-[12px] leading-[1.45] opacity-80">{r.desc}</td>
                  <td className="whitespace-nowrap py-5 pr-6 font-mono text-[12px] text-pen">
                    {n(r.count)} {r.unit}
                  </td>
                  <td className="w-48 py-5">
                    <div className="relative h-4 border-x border-b border-[#111317]">
                      <span className="absolute left-1/2 top-0 h-2 w-px bg-[#111317]" />
                      <span className="absolute bottom-0 top-1 w-1.5 bg-pen" style={{ left: `calc(${(r.count / maxCount) * 100}% - 6px)` }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="relative z-10 px-4 pb-10 pt-6 sm:px-6">
        <div className="mx-auto flex max-w-[1320px] flex-col items-start gap-8 md:flex-row md:items-end md:justify-between">
          <button type="button" onClick={onSignIn} className="group text-left">
            <span className="display block text-[14vw] uppercase leading-[0.85] group-hover:text-pen sm:text-[8rem]">Open the records</span>
            <Mono className="mt-2 block text-pen">[ sign in with a demo doctor account ]</Mono>
          </button>
          <div className="max-w-sm space-y-2">
            <Mono className="block">Pushkar Panwar (2501730022) and Saksham Singh (2501730270)</Mono>
            {real && stats?.source.url && (
              <Mono className="block opacity-80">
                Data: Johnson A, et al. MIMIC-IV Clinical Database Demo (v2.2), PhysioNet, ODbL.{' '}
                <a className="underline" href={stats.source.url} target="_blank" rel="noreferrer">
                  physionet.org
                </a>
              </Mono>
            )}
            <Mono className="block opacity-80">Illustrations: Gray&rsquo;s Anatomy (1918), public domain.</Mono>
          </div>
        </div>
      </section>
    </div>
  );
}
