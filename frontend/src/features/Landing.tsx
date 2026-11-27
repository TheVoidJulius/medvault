import { useEffect, useRef, useState } from 'react';
import { LogoMark } from '../components/Logo';
import { cx } from '../lib/format';

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

const n = (v: number | undefined) => (v ?? 0).toLocaleString('en-IN');

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    setReduced(!!mq?.matches);
  }, []);
  return reduced;
}

/** Counts up once, like an indexer working through the rows. */
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
      const p = Math.min(1, (t - t0) / ms);
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, ms]);
  return v;
}

/** 0 → 1 as the element scrolls through the viewport. */
function useScrollProgress<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [p, setP] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      setP(Math.min(1, Math.max(0, (vh - r.top) / (r.height + vh * 0.4))));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);
  return [ref, p] as const;
}

function Mono({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cx('font-mono text-[11px] leading-[1.35] tracking-[-0.01em]', className)}>{children}</span>;
}

function Cta({ onClick, className, children }: { onClick: () => void; className?: string; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={cx('font-mono text-[12px] text-pen hover:underline focus-visible:underline', className)}>
      [ {children} ]
    </button>
  );
}

/** Thin contour around the hero plate: one closed organic line plus scattered cells, drawn like a culture dish. */
function Contour() {
  const dots = [
    [120, 140, 9, 5], [190, 95, 6, 4], [320, 60, 10, 4], [450, 48, 7, 5], [600, 52, 12, 5], [740, 70, 8, 4], [860, 120, 10, 6],
    [925, 230, 5, 9], [960, 360, 6, 11], [930, 520, 7, 5], [80, 300, 5, 10], [60, 450, 6, 8], [110, 590, 9, 5], [880, 650, 9, 5],
    [210, 700, 12, 4], [700, 720, 10, 4], [520, 760, 14, 4], [380, 752, 9, 4],
  ];
  return (
    <svg viewBox="0 0 1000 800" className="absolute inset-0 h-full w-full" aria-hidden fill="none" stroke="rgb(var(--ink))" strokeWidth="1.4">
      <path d="M150 260 C 150 120, 330 90, 500 95 C 690 100, 850 140, 860 300 C 868 410, 800 420, 820 520 C 838 610, 760 690, 610 680 C 520 674, 470 720, 380 700 C 250 672, 190 640, 180 560 C 172 490, 120 470, 130 390 C 136 340, 150 320, 150 260 Z" />
      <path d="M230 560 C 260 610, 330 640, 380 620" />
      <path d="M700 600 C 740 580, 770 540, 760 500" />
      {dots.map(([x, y, rx, ry], i) => (
        <ellipse key={i} cx={x} cy={y} rx={rx} ry={ry} />
      ))}
    </svg>
  );
}

/** Rotating stamp in the hero's corner. */
function Stamp() {
  return (
    <svg viewBox="0 0 160 160" className="h-28 w-28 sm:h-32 sm:w-32" aria-hidden>
      <defs>
        <path id="stamp-ring" d="M80 80 m -58 0 a 58 58 0 1 1 116 0 a 58 58 0 1 1 -116 0" />
      </defs>
      <circle cx="80" cy="80" r="76" fill="none" stroke="rgb(var(--pen))" strokeWidth="1.5" />
      <circle cx="80" cy="80" r="40" fill="none" stroke="rgb(var(--pen))" strokeWidth="1" />
      <g className="origin-center motion-safe:animate-[spin_28s_linear_infinite]" style={{ transformBox: 'fill-box' }}>
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
  { n: '1', title: 'Store', text: 'Every admission, diagnosis, drug and lab is a row in one relational record.' },
  { n: '2', title: 'Summarise', text: 'AI reads the rows back as a summary. Each sentence names the row it came from.' },
  { n: '3', title: 'Ask', text: 'Plain-English questions return the matching rows, or say plainly that nothing matches.' },
];

export function Landing({ onSignIn }: { onSignIn: () => void }) {
  const reduced = useReducedMotion();
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [bodyRef, bodyP] = useScrollProgress<HTMLElement>();

  useEffect(() => {
    fetch('/api/dashboard/public')
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => s && setStats(s))
      .catch(() => undefined);
    const t = setTimeout(() => setLoaded(true), 60);
    return () => clearTimeout(t);
  }, []);

  const totalRows = stats ? stats.visits + stats.diagnoses + stats.prescriptions + stats.lab_results + stats.symptoms + stats.notes : 0;
  const indexed = useCountUp(totalRows, !reduced && !!stats);
  const pct = totalRows ? Math.round((indexed / totalRows) * 100) : 0;
  const real = (stats?.real_patients ?? 0) > 0;
  const years = stats?.first_year ? `${stats.first_year}–${stats.last_year}` : '';

  const table = stats
    ? [
        { name: 'Admissions and ED visits', desc: 'Each hospital admission or emergency attendance, with triage vitals and how the patient left.', count: stats.visits, unit: 'visits' },
        { name: 'Diagnoses', desc: `Discharge diagnoses coded in ICD-9 and ICD-10, ranked by importance. ${n(stats.distinct_conditions)} distinct conditions.`, count: stats.diagnoses, unit: 'codes' },
        { name: 'Prescriptions', desc: 'Drugs ordered during the stay, with dose, route and how many times a day.', count: stats.prescriptions, unit: 'orders' },
        { name: 'Lab results', desc: `First result of each key test per admission, with reference range. ${n(stats.abnormal_labs)} fall outside it.`, count: stats.lab_results, unit: 'results' },
        { name: 'Triage complaints', desc: 'What patients said at the emergency desk, with pain score.', count: stats.symptoms, unit: 'entries' },
      ]
    : [];
  const maxCount = Math.max(1, ...table.map((r) => r.count));

  return (
    <div className="landing min-h-screen overflow-x-hidden bg-[#B4B7BD] text-[#111317] [--ink:17_19_23] [--pen:31_53_198] dark:bg-[#B4B7BD]">
      {/* grain */}
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-[0.18] mix-blend-multiply"
        aria-hidden
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />

      {/* Top bar */}
      <header className="fixed inset-x-0 top-0 z-30 grid grid-cols-2 items-start gap-4 border-b border-[#111317]/15 bg-[#B4B7BD]/90 px-4 py-3 backdrop-blur-sm sm:grid-cols-[1fr_1fr_1fr_auto] sm:px-6">
        <a href="#/" className="flex items-center gap-2">
          <LogoMark className="h-6 w-6" />
          <span className="display text-[1.05rem] uppercase leading-none tracking-[0.01em]">MedVault</span>
        </a>
        <Mono className="hidden sm:block">
          Where patient records
          <br />
          meet reasoning.
        </Mono>
        <Mono className="hidden sm:block">{real ? `Source: MIMIC-IV, ${stats?.source.institution?.split(',')[0]}` : 'Grounded AI active'}</Mono>
        <Cta onClick={onSignIn} className="justify-self-end">
          Open the records
        </Cta>
      </header>

      {/* Hero */}
      <section className="relative z-10 min-h-[100svh] px-4 pb-10 pt-20 sm:px-6">
        <ol className="absolute left-4 top-24 hidden border-l border-[#111317] pl-0 sm:left-6 md:block" aria-label="How MedVault works">
          {STEPS.map((s) => (
            <li key={s.n} className="relative -ml-px flex items-center gap-6 py-3 before:mr-0 before:block before:h-px before:w-3 before:bg-[#111317]">
              <Mono>({s.n})</Mono>
              <Mono>{s.title}</Mono>
            </li>
          ))}
        </ol>

        <Mono className="absolute right-4 top-24 hidden text-right sm:right-6 md:block">
          Real patients,
          <br />
          cited answers.
        </Mono>
        <Mono className="absolute right-4 top-40 hidden text-right sm:right-6 lg:block">
          Grounded at the
          <br />
          row level
        </Mono>

        <div className="relative mx-auto mt-6 aspect-[5/4] w-full max-w-[880px]">
          <Contour />
          <img
            src="/art/heart-anterior.png"
            alt="Engraving of the human heart, front view, from Gray's Anatomy (1918)"
            className={cx(
              'absolute left-1/2 top-1/2 w-[64%] -translate-x-1/2 -translate-y-1/2 mix-blend-multiply transition-[opacity,transform] duration-[1600ms] ease-out',
              loaded || reduced ? 'scale-100 opacity-100' : 'scale-[0.96] opacity-0',
            )}
          />
          {STEPS.map((s, i) => (
            <div
              key={s.n}
              className={cx(
                'absolute hidden max-w-[13rem] md:block',
                i === 0 && '-left-[4%] top-[14%]',
                i === 1 && '-right-[6%] top-[38%] text-right',
                i === 2 && 'bottom-[6%] left-[2%]',
              )}
            >
              <Mono className="text-pen">({s.n})</Mono>
              <p className="mt-1 font-mono text-[11px] leading-[1.35]">{s.text}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-4 md:hidden">
          {STEPS.map((s) => (
            <p key={s.n} className="font-mono text-[12px] leading-snug">
              <span className="text-pen">({s.n}) {s.title}.</span> {s.text}
            </p>
          ))}
        </div>

        <div className="absolute left-4 top-[46%] hidden sm:left-6 md:block">
          <Mono className="block text-[13px]">{String(pct).padStart(3, '0')}%</Mono>
          <Mono className="block opacity-70">{stats ? `${n(indexed)} rows indexed` : 'Indexing'}</Mono>
        </div>

        <div className="mt-8 flex items-end justify-between gap-4 md:absolute md:inset-x-6 md:bottom-6 md:mt-0">
          <Stamp />
          <Mono className="hidden sm:block">Scroll</Mono>
          <Mono className="text-right">
            {real ? `${n(stats?.real_patients)} real de-identified patients` : 'Patient records'}
            <br />
            {years}
          </Mono>
        </div>
      </section>

      {/* Statement */}
      <section className="relative z-10 px-4 py-16 sm:px-6 sm:py-24">
        <div className="mx-auto max-w-[1320px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <Mono className="block opacity-70">Program</Mono>
              <Mono className="block">
                Status: <span className="text-pen">[ live ]</span>
              </Mono>
            </div>
            <h1 className="display max-w-5xl text-[13vw] uppercase leading-[0.86] sm:text-[8.5vw] xl:text-[7.4rem]">
              Every record, read back with its sources
            </h1>
          </div>

          <div className="relative mt-8 grid gap-10 border-y-2 border-[#111317] py-10 md:grid-cols-[1fr_1.1fr_1fr] md:border-x-2 md:px-8">
            <div className="space-y-8">
              <div>
                <Mono className="block opacity-70">Summaries grounded in SQL</Mono>
                <p className="mt-2 max-w-xs font-mono text-[12px] leading-[1.45]">
                  The summary is built from counts, status changes and lab trends computed over stored rows. A validator drops any sentence whose citation is not a real row.
                </p>
              </div>
              <div className="border border-[#111317] bg-[#C3C6CB] p-4">
                <Mono className="block opacity-70">How a summary line looks (illustration)</Mono>
                <p className="mt-2 text-[0.95rem] leading-snug">
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

            <div className="relative flex items-center justify-center">
              <img src="/art/heart-posterior.png" alt="Engraving of the heart, back view, from Gray's Anatomy (1918)" className="w-full max-w-sm mix-blend-multiply" loading="lazy" />
            </div>

            <div className="flex flex-col justify-between gap-8">
              <div>
                <Mono className="block opacity-70">How a question is answered</Mono>
                <p className="mt-2 max-w-xs font-mono text-[12px] leading-[1.45]">
                  Words in the question become filters: dates, record types, clinical terms and their synonyms. Every stored row is scored and the best are returned with citations.
                </p>
              </div>
              <div className="relative h-56">
                {[
                  { k: '03', t: 'Citation', d: 'DX-1840 → diagnoses row 1840' },
                  { k: '02', t: 'Diagnosis', d: 'ICD-9 584.9, acute kidney failure' },
                  { k: '01', t: 'Visit', d: 'Emergency admission, 6 days' },
                ].map((plate, i) => (
                  <div
                    key={plate.k}
                    className="absolute w-48 border border-[#111317] bg-[#B4B7BD] p-3 shadow-[2px_2px_0_#111317]"
                    style={{ left: `${i * 26}px`, top: `${i * 46}px`, transform: 'skewY(-6deg)' }}
                  >
                    <Mono className="block">{plate.k}</Mono>
                    <p className="mt-1 text-sm font-semibold">{plate.t}</p>
                    <Mono className="block opacity-75">{plate.d}</Mono>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Figure with ink */}
      <section ref={bodyRef} className="relative z-10 overflow-hidden px-4 py-16 sm:px-6">
        <div className="relative mx-auto aspect-square w-full max-w-[760px]">
          {[
            'left-0 top-0', 'right-0 top-0', 'left-0 bottom-0', 'right-0 bottom-0',
          ].map((pos) => (
            <div key={pos} className={cx('absolute h-[42%] w-[42%] rounded-full border border-[#111317]', pos)}>
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 font-mono text-[12px]">+</span>
            </div>
          ))}
          <svg viewBox="0 0 200 200" className="absolute inset-0 h-full w-full" aria-hidden>
            <path
              d="M100 22 C 140 18, 176 48, 178 92 C 181 140, 150 178, 104 180 C 60 182, 24 150, 22 104 C 20 60, 58 26, 100 22 Z"
              fill="rgb(var(--pen))"
              style={{
                transformOrigin: '100px 100px',
                transform: `scale(${reduced ? 1 : 0.15 + bodyP * 1.05}) rotate(${bodyP * 40}deg)`,
                transition: 'transform 120ms linear',
              }}
            />
            {Array.from({ length: 14 }).map((_, i) => {
              const a = (i / 14) * Math.PI * 2;
              const r = 92;
              return (
                <circle
                  key={i}
                  cx={100 + Math.cos(a) * r}
                  cy={100 + Math.sin(a) * r}
                  r={1.4 + (i % 3)}
                  fill="rgb(var(--pen))"
                  opacity={reduced ? 1 : Math.min(1, Math.max(0, bodyP * 2 - 0.6))}
                />
              );
            })}
          </svg>
          <img
            src="/art/torso.png"
            alt="Outline of the human torso with abdominal regions, from Gray's Anatomy (1918)"
            className="absolute left-1/2 top-1/2 w-[62%] -translate-x-1/2 -translate-y-1/2"
            style={{ filter: bodyP > 0.55 || reduced ? 'brightness(0) invert(0.92)' : undefined, transition: 'filter 300ms' }}
            loading="lazy"
          />
        </div>
        <div className="mx-auto mt-10 grid max-w-[1100px] grid-cols-2 gap-6 md:grid-cols-4">
          {[
            { v: n(stats?.patients), l: real ? 'real patients' : 'patients' },
            { v: n(stats?.visits), l: 'admissions and ED visits' },
            { v: n(stats?.lab_results), l: 'lab results' },
            { v: years || '—', l: 'years of care' },
          ].map((s) => (
            <div key={s.l} className="border-t border-[#111317] pt-2">
              <p className="display text-[2.6rem] leading-none">{s.v}</p>
              <Mono className="opacity-80">{s.l}</Mono>
            </div>
          ))}
        </div>
      </section>

      {/* The data, as a pipeline-style table */}
      <section id="data" className="relative z-10 px-4 py-16 sm:px-6 sm:py-24">
        <div className="mx-auto max-w-[1320px] border-2 border-[#111317] p-5 sm:p-8">
          <h2 className="display text-[15vw] uppercase leading-[0.85] sm:text-[7rem]">The data</h2>
          <p className="mt-4 max-w-2xl font-mono text-[12px] leading-[1.5]">
            {real ? (
              <>
                Real, de-identified patients of {stats?.source.institution}, from the {stats?.source.name}, published on PhysioNet under the{' '}
                {stats?.source.license}. Names, addresses and exact dates were removed by the publishers; dates here are shifted back into each patient&rsquo;s real era.
              </>
            ) : (
              'Synthetic demonstration records.'
            )}
          </p>
          <div className="mt-8 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left">
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
                    <td className="py-5 pr-6 font-mono text-[12px] text-pen">
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
        </div>
      </section>

      {/* Close */}
      <section className="relative z-10 px-4 pb-10 pt-10 sm:px-6">
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
