import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from 'react';
import { Database, ExternalLink, X } from 'lucide-react';
import type { CitationRef } from '../lib/types';
import { formatDate } from '../lib/format';
import { Button, Drawer } from './ui';

const RECORD_LABEL: Record<string, string> = {
  Visit: 'Visit',
  Symptom: 'Symptom',
  Diagnosis: 'Diagnosis',
  Prescription: 'Prescription',
  TestResult: 'Lab result',
  Allergy: 'Allergy',
  MedicalHistory: 'History entry',
  ClinicalNote: 'Clinical note',
};

interface CitationCtx {
  inspect: (ref: CitationRef, patientId?: number) => void;
}

const Ctx = createContext<CitationCtx>({ inspect: () => undefined });

export function CitationProvider({ children, onOpenVisit }: { children: ReactNode; onOpenVisit: (patientId: number, visitId: number) => void }) {
  const [current, setCurrent] = useState<{ ref: CitationRef; patientId?: number } | null>(null);
  const inspect = useCallback((ref: CitationRef, patientId?: number) => setCurrent({ ref, patientId }), []);
  const close = useCallback(() => setCurrent(null), []);
  const value = useMemo(() => ({ inspect }), [inspect]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <Drawer open={!!current} onClose={close} label="Citation source record inspector">
        {current && (
          <>
            <header className="flex items-start justify-between gap-3 border-b border-rule px-5 py-4">
              <div>
                <p className="flex items-center gap-1.5 text-[0.8125rem] text-ink-2">
                  <Database className="h-3.5 w-3.5" aria-hidden />
                  Stored {RECORD_LABEL[current.ref.record_type]?.toLowerCase() ?? 'record'}
                </p>
                <p className="code mt-1 text-lg text-pen">[{current.ref.tag}]</p>
              </div>
              <button type="button" onClick={close} aria-label="Close source record inspector" className="rounded-ctl p-1.5 text-ink-3 hover:bg-well hover:text-ink">
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
              <section>
                <h3 className="text-base font-bold leading-snug">{current.ref.label}</h3>
                <p className="mt-2 whitespace-pre-line rounded-ctl bg-well p-3 text-[0.8125rem] leading-relaxed text-ink">{current.ref.snippet}</p>
              </section>
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-[0.8125rem]">
                <dt className="text-ink-3">Table</dt>
                <dd className="code">{current.ref.record_type}</dd>
                <dt className="text-ink-3">Row id</dt>
                <dd className="code">{current.ref.record_id}</dd>
                {current.ref.visit_id && (
                  <>
                    <dt className="text-ink-3">Visit</dt>
                    <dd className="code">V-{current.ref.visit_id}</dd>
                  </>
                )}
                <dt className="text-ink-3">Recorded</dt>
                <dd>{formatDate(current.ref.visit_date)}</dd>
              </dl>
              <p className="text-2xs leading-relaxed text-ink-3">
                This is the row the AI cited, read straight from the database. If the statement doesn't match it, flag the statement for review.
              </p>
            </div>
            {current.ref.visit_id && current.patientId && (
              <footer className="border-t border-rule px-5 py-4">
                <Button
                  tone="ink"
                  className="w-full"
                  icon={<ExternalLink className="h-4 w-4" />}
                  onClick={() => {
                    onOpenVisit(current.patientId!, current.ref.visit_id!);
                    close();
                  }}
                >
                  Open visit in timeline
                </Button>
              </footer>
            )}
          </>
        )}
      </Drawer>
    </Ctx.Provider>
  );
}

export function useCitations() {
  return useContext(Ctx);
}

/** Inline citation chips that follow an AI statement. */
export function Citations({
  tags,
  index,
  patientId,
}: {
  tags: string[];
  index: Record<string, CitationRef>;
  patientId?: number;
}) {
  const { inspect } = useCitations();
  if (!tags?.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-baseline">
      {tags.map((tag) => {
        const ref = index[tag];
        return (
          <button
            key={tag}
            type="button"
            disabled={!ref}
            onClick={() => ref && inspect(ref, patientId)}
            aria-label={`Inspect source record ${tag}`}
            title={ref ? ref.label : `${tag} is not in the citation index`}
            className="code rounded-tag border border-pen/30 bg-pen-wash px-1 text-[0.6875rem] leading-[1.35rem] text-pen transition-colors hover:border-pen hover:bg-pen hover:text-white disabled:opacity-40 dark:hover:text-paper"
          >
            {tag}
          </button>
        );
      })}
    </span>
  );
}
