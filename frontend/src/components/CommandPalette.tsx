import { useEffect, useMemo, useRef, useState } from 'react';
import { ClipboardList, CornerDownLeft, LayoutDashboard, MessageSquareText, Moon, ScrollText, Search, UserPlus, Users } from 'lucide-react';
import type { PatientListItem } from '../lib/types';
import { ageFrom, cx, fullName } from '../lib/format';
import type { Route } from '../workspace';

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: JSX.Element;
  run: () => void;
  keywords: string;
}

export function CommandPalette({
  open,
  onClose,
  patients,
  navigate,
  onRegister,
  onToggleTheme,
}: {
  open: boolean;
  onClose: () => void;
  patients: PatientListItem[];
  navigate: (r: Route) => void;
  onRegister: () => void;
  onToggleTheme: () => void;
}) {
  const [q, setQ] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setCursor(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const go = (r: Route) => () => navigate(r);
    const actions: Command[] = [
      { id: 'overview', label: 'Go to overview', icon: <LayoutDashboard className="h-4 w-4" />, run: go({ view: 'overview' }), keywords: 'dashboard home overview' },
      { id: 'patients', label: 'Go to patients', icon: <Users className="h-4 w-4" />, run: go({ view: 'patients' }), keywords: 'patients registry list' },
      { id: 'search', label: 'Ask the records', icon: <MessageSquareText className="h-4 w-4" />, run: go({ view: 'search' }), keywords: 'ai search query retrieval ask question' },
      { id: 'audit', label: 'Open audit trail', icon: <ScrollText className="h-4 w-4" />, run: go({ view: 'audit' }), keywords: 'audit log access security' },
      { id: 'register', label: 'Register a patient', icon: <UserPlus className="h-4 w-4" />, run: onRegister, keywords: 'new add register create patient' },
      { id: 'theme', label: 'Switch light / dark', icon: <Moon className="h-4 w-4" />, run: onToggleTheme, keywords: 'theme dark light mode' },
    ];
    const people: Command[] = patients.map((p) => ({
      id: `p${p.id}`,
      label: fullName(p),
      hint: `${p.mrn}, ${ageFrom(p.date_of_birth)} y ${p.sex.toLowerCase()}, ${p.primary_conditions[0] ?? "no conditions recorded"}`,
      icon: <ClipboardList className="h-4 w-4" />,
      run: go({ view: 'chart', patientId: p.id, tab: 'overview' }),
      keywords: `${fullName(p)} ${p.mrn} ${p.phone} ${p.primary_conditions.join(' ')}`.toLowerCase(),
    }));
    return [...actions, ...people];
  }, [patients, navigate, onRegister, onToggleTheme]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return commands.slice(0, 12);
    const words = term.split(/\s+/);
    return commands.filter((c) => words.every((w) => c.keywords.includes(w) || c.label.toLowerCase().includes(w))).slice(0, 12);
  }, [q, commands]);

  if (!open) return null;

  const run = (c: Command | undefined) => {
    if (!c) return;
    onClose();
    c.run();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-ink/40 px-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label="Command palette" className="w-full max-w-xl overflow-hidden rounded-panel border border-rule bg-sheet shadow-float animate-rise">
        <div className="flex items-center gap-3 border-b border-rule px-4">
          <Search className="h-4 w-4 text-ink-3" aria-hidden />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setCursor(0);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose();
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setCursor((c) => Math.min(c + 1, results.length - 1));
              }
              if (e.key === 'ArrowUp') {
                e.preventDefault();
                setCursor((c) => Math.max(c - 1, 0));
              }
              if (e.key === 'Enter') run(results[cursor]);
            }}
            placeholder="Find a patient by name, MRN or condition, or type a command"
            aria-label="Search patients and commands"
            className="h-14 flex-1 bg-transparent text-[0.9375rem] placeholder:text-ink-3 focus:outline-none"
          />
          <kbd className="code rounded-tag border border-rule px-1.5 text-ink-3">esc</kbd>
        </div>
        <ul className="max-h-[52vh] overflow-y-auto p-2" role="listbox" aria-label="Results">
          {results.length === 0 && <li className="px-3 py-6 text-center text-[0.8125rem] text-ink-3">No patient or command matches “{q}”.</li>}
          {results.map((c, i) => (
            <li key={c.id} role="option" aria-selected={i === cursor}>
              <button
                type="button"
                onMouseEnter={() => setCursor(i)}
                onClick={() => run(c)}
                className={cx('flex w-full items-center gap-3 rounded-ctl px-3 py-2 text-left', i === cursor ? 'bg-pen-wash' : '')}
              >
                <span className={cx(i === cursor ? 'text-pen' : 'text-ink-3')}>{c.icon}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">{c.label}</span>
                  {c.hint && <span className="block truncate text-2xs text-ink-3">{c.hint}</span>}
                </span>
                {i === cursor && <CornerDownLeft className="h-3.5 w-3.5 text-pen" aria-hidden />}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
