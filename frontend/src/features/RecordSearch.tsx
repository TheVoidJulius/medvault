import { FormEvent, useEffect, useRef, useState } from 'react';
import { ArrowUpRight, CornerDownLeft, SearchX } from 'lucide-react';
import { Citations } from '../components/citations';
import { Button, Empty, Notice, PageHeader, Select, Skeleton, Tag } from '../components/ui';
import { formatDate, fullName } from '../lib/format';
import { errorText } from '../lib/http';
import type { AIQueryResponse, PatientDetail } from '../lib/types';
import { useWorkspace } from '../workspace';

const COHORT_QUESTIONS = [
  'Which patients had heart failure?',
  'Find sepsis admissions',
  'Show high creatinine results',
  'Which patients were given vancomycin?',
  'Find previous records mentioning chest pain',
  'Find records mentioning Ebola',
];

const PATIENT_QUESTIONS = [
  "What were this patient's previous diagnoses?",
  'Has this patient reported similar symptoms before?',
  'What medications were prescribed during previous visits?',
  'Show abnormal lab results',
  'Show the medical history from the last two years',
];

const RECORD_LABEL: Record<string, string> = {
  TestResult: 'Lab result',
  ClinicalNote: 'Note',
  MedicalHistory: 'History',
};

export function QueryPanel({ scopePatient, initialQuery, showScope = false }: { scopePatient?: PatientDetail; initialQuery?: string; showScope?: boolean }) {
  const { api, navigate, patients } = useWorkspace();
  const [q, setQ] = useState(initialQuery ?? (scopePatient ? PATIENT_QUESTIONS[0] : COHORT_QUESTIONS[0]));
  const [scope, setScope] = useState<number | 'all'>(scopePatient?.id ?? 'all');
  const [result, setResult] = useState<AIQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const run = async (question = q, s = scope) => {
    if (!question.trim()) {
      setError('Type a question about the records first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(
        await api<AIQueryResponse>('/api/ai/query', {
          method: 'POST',
          body: JSON.stringify({ query: question, patient_id: s === 'all' ? null : s }),
        }),
      );
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    run();
  };
  const presets = scope === 'all' ? COHORT_QUESTIONS : PATIENT_QUESTIONS;
  const f = result?.interpreted_filters;

  return (
    <div className="space-y-5">
      <form onSubmit={submit} className="rounded-panel border border-rule bg-sheet focus-within:border-pen focus-within:ring-2 focus-within:ring-pen/15">
        <textarea
          ref={inputRef}
          aria-label="Question about the records"
          value={q}
          rows={2}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              run();
            }
          }}
          placeholder={scopePatient ? `Ask about ${fullName(scopePatient)}’s record` : 'Ask about any patient’s record'}
          className="block w-full resize-none rounded-t-panel bg-transparent px-4 pt-3.5 text-[1rem] leading-relaxed placeholder:text-ink-3 focus:outline-none"
        />
        <div className="flex flex-wrap items-center gap-2 px-3 pb-3 pt-1">
          {showScope && (
            <Select aria-label="Which patients to search" value={scope} onChange={(e) => setScope(e.target.value === 'all' ? 'all' : Number(e.target.value))} className="h-8 w-auto max-w-[16rem] text-[0.8125rem]">
              <option value="all">All patients</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {fullName(p)} ({p.mrn})
                </option>
              ))}
            </Select>
          )}
          <span className="text-2xs text-ink-3">Answers only cite stored rows. If nothing matches, it says so.</span>
          <Button type="submit" tone="ink" size="sm" loading={loading} className="ml-auto" icon={!loading ? <CornerDownLeft className="h-3.5 w-3.5" /> : undefined}>
            Ask
          </Button>
        </div>
      </form>

      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => {
              setQ(p);
              run(p);
            }}
            className="rounded-full border border-rule bg-sheet px-3 py-1 text-[0.8125rem] text-ink-2 transition-colors hover:border-pen hover:text-pen"
          >
            {p}
          </button>
        ))}
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      {loading && !result && (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
        </div>
      )}

      {result && (
        <div className={loading ? 'opacity-60 transition-opacity' : ''}>
          <p className="mb-3 text-2xs text-ink-3">
            Read as: {f?.expanded_clinical_terms.length ? <>terms <span className="code text-ink-2">{f.expanded_clinical_terms.slice(0, 8).join(', ')}</span></> : 'no clinical term'}
            {f?.target_record_types?.length && f.target_record_types[0] !== 'All' ? <>, in {f.target_record_types.join(', ').toLowerCase()} rows</> : null}
            {f?.date_from ? <>, from {formatDate(f.date_from)}</> : null}.{' '}
            <span className="font-semibold text-ink-2">{result.total_matches === 1 ? '1 matching record' : `${result.total_matches} matching records`}</span>
          </p>

          {result.total_matches === 0 ? (
            <Empty
              icon={<SearchX className="h-6 w-6" />}
              title="Nothing in the record matches"
              body={`${result.direct_summary} Nothing was inferred beyond the stored rows.`}
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
              <section className="self-start rounded-panel border border-rule bg-sheet p-4 lg:sticky lg:top-24">
                <h2 className="text-[0.875rem] font-bold">Answer</h2>
                <p className="mt-1 text-[0.9375rem] leading-relaxed">{result.direct_summary}</p>
                <ul className="mt-3 space-y-2 border-t border-rule pt-3">
                  {result.answer_statements.map((s, i) => (
                    <li key={i} className="text-[0.8125rem] leading-relaxed">
                      {s.text}
                      <Citations tags={s.citations} index={result.citation_index} patientId={scopePatient?.id ?? result.retrieved_records.find((r) => s.citations.includes(r.citation_tag))?.patient_id} />
                    </li>
                  ))}
                </ul>
                <p className="mt-3 border-t border-rule pt-3 text-2xs text-ink-3">{result.disclaimer}</p>
              </section>

              <section>
                <h2 className="mb-2 text-[0.875rem] font-bold">Source records ({result.retrieved_records.length})</h2>
                <ul className="space-y-2">
                  {result.retrieved_records.map((r) => (
                    <li key={r.citation_tag} className="rounded-panel border border-rule bg-sheet px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="code text-pen">{r.citation_tag}</span>
                        <Tag tone="outline">{RECORD_LABEL[r.record_type] ?? r.record_type}</Tag>
                        <span className="ml-auto text-2xs text-ink-3">{r.visit_date ? formatDate(r.visit_date) : 'Profile'}</span>
                      </div>
                      <h3 className="mt-1 text-[0.875rem] font-semibold">{r.title}</h3>
                      <p className="mt-0.5 line-clamp-3 text-[0.8125rem] text-ink-2">{r.details}</p>
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-2xs">
                        <span className="text-ink-3">
                          {r.patient_name}, <span className="code">{r.patient_mrn}</span>
                          {r.matched_terms.length > 0 && <> matched “{r.matched_terms.slice(0, 3).join('”, “')}”</>}
                        </span>
                        <button
                          type="button"
                          onClick={() => navigate({ view: 'chart', patientId: r.patient_id, tab: 'timeline', focusVisit: r.visit_id ?? undefined })}
                          className="inline-flex items-center gap-0.5 font-semibold text-pen hover:underline"
                        >
                          Open in chart <ArrowUpRight className="h-3 w-3" aria-hidden />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function RecordSearch({ initialQuery }: { initialQuery?: string }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Ask the records" lede="Ask in plain English across every patient, or pick one. Each answer links to the rows it was built from." />
      <QueryPanel initialQuery={initialQuery} showScope />
    </div>
  );
}
