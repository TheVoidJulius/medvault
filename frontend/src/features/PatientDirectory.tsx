import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Search, UserPlus } from 'lucide-react';
import { Button, Empty, Input, PageHeader, Select, Skeleton, Tag } from '../components/ui';
import { ageFrom, fullName, relativeDays } from '../lib/format';
import type { PatientListItem } from '../lib/types';
import { useWorkspace } from '../workspace';
import { BLOOD_GROUPS } from './PatientForms';

const PAGE_SIZE = 15;
type Sort = 'recent' | 'name' | 'visits' | 'mrn';

function matches(p: PatientListItem, q: string) {
  const hay = [fullName(p), p.mrn, p.phone, p.email ?? '', p.blood_group ?? '', ...p.primary_conditions, ...p.active_allergies]
    .join(' ')
    .toLowerCase();
  return q
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((w) => hay.includes(w));
}

export function PatientDirectory() {
  const { patients, patientsLoading, navigate, openRegister } = useWorkspace();
  const [q, setQ] = useState('');
  const [sex, setSex] = useState('');
  const [blood, setBlood] = useState('');
  const [sort, setSort] = useState<Sort>('recent');
  const [page, setPage] = useState(1);

  const rows = useMemo(() => {
    const list = patients.filter((p) => (!sex || p.sex === sex) && (!blood || p.blood_group === blood) && (!q.trim() || matches(p, q)));
    const by: Record<Sort, (a: PatientListItem, b: PatientListItem) => number> = {
      recent: (a, b) => (b.last_visit_date ?? '').localeCompare(a.last_visit_date ?? ''),
      name: (a, b) => fullName(a).localeCompare(fullName(b)),
      visits: (a, b) => b.visit_count - a.visit_count,
      mrn: (a, b) => a.mrn.localeCompare(b.mrn),
    };
    return [...list].sort(by[sort]);
  }, [patients, q, sex, blood, sort]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const shown = rows.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const filtered = q || sex || blood;
  const resetTo = (fn: () => void) => {
    fn();
    setPage(1);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Patients"
        lede={`${patients.length} patients. Search by name, MRN, condition or allergy.`}
        actions={
          <Button tone="pen" onClick={openRegister} icon={<UserPlus className="h-4 w-4" />}>
            Register patient
          </Button>
        }
      />

      <div className="grid gap-3 rounded-panel border border-rule bg-sheet p-3 md:grid-cols-[1fr_auto_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
          <Input
            aria-label="Search patients"
            value={q}
            onChange={(e) => resetTo(() => setQ(e.target.value))}
            placeholder="Try “sepsis”, “heart failure” or “10002428”"
            className="pl-9"
          />
        </div>
        <Select aria-label="Filter by sex" value={sex} onChange={(e) => resetTo(() => setSex(e.target.value))}>
          <option value="">Any sex</option>
          <option>Female</option>
          <option>Male</option>
          <option>Other</option>
        </Select>
        <Select aria-label="Filter by blood group" value={blood} onChange={(e) => resetTo(() => setBlood(e.target.value))}>
          <option value="">Any blood group</option>
          {BLOOD_GROUPS.map((b) => (
            <option key={b}>{b}</option>
          ))}
        </Select>
        <Select aria-label="Sort patients" value={sort} onChange={(e) => resetTo(() => setSort(e.target.value as Sort))}>
          <option value="recent">Most recently seen</option>
          <option value="name">Name A–Z</option>
          <option value="visits">Most visits</option>
          <option value="mrn">MRN</option>
        </Select>
      </div>

      {patientsLoading && patients.length === 0 ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <Empty
          title="No patient matches"
          body={filtered ? 'Nothing in the registry fits that search and these filters.' : 'Register the first patient to start a record.'}
          action={
            filtered ? (
              <Button
                onClick={() =>
                  resetTo(() => {
                    setQ('');
                    setSex('');
                    setBlood('');
                  })
                }
              >
                Clear search and filters
              </Button>
            ) : (
              <Button tone="pen" onClick={openRegister}>
                Register patient
              </Button>
            )
          }
        />
      ) : (
        <div className="overflow-hidden rounded-panel border border-rule bg-sheet">
          <table className="w-full text-left text-[0.8125rem]">
            <thead className="border-b border-rule text-ink-3">
              <tr>
                <th className="px-5 py-2.5 font-medium">Patient</th>
                <th className="hidden px-3 py-2.5 font-medium sm:table-cell" title="Age at the most recent visit">Age, sex</th>
                <th className="hidden px-3 py-2.5 font-medium lg:table-cell">Blood</th>
                <th className="px-3 py-2.5 font-medium">Conditions</th>
                <th className="hidden px-3 py-2.5 font-medium md:table-cell">Allergies</th>
                <th className="px-5 py-2.5 text-right font-medium">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id} className="group border-b border-rule last:border-0 hover:bg-well">
                  <td className="px-5 py-3 align-top">
                    <button
                      type="button"
                      onClick={() => navigate({ view: 'chart', patientId: p.id, tab: 'overview' })}
                      className="text-left font-semibold text-ink group-hover:text-pen"
                      aria-label={`Open chart for ${fullName(p)}`}
                    >
                      {fullName(p)}
                    </button>
                    <span className="code block whitespace-nowrap text-ink-3">{p.mrn}</span>
                  </td>
                  <td className="hidden whitespace-nowrap px-3 py-3 align-top text-ink-2 sm:table-cell">
                    {ageFrom(p.date_of_birth, p.last_visit_date ? new Date(p.last_visit_date) : undefined)}, {p.sex}
                  </td>
                  <td className="hidden px-3 py-3 align-top lg:table-cell">
                    {p.blood_group ? <span className="code">{p.blood_group}</span> : <span className="text-ink-3">Not recorded</span>}
                  </td>
                  <td className="max-w-[22rem] px-3 py-3 align-top">
                    <span className="line-clamp-2 text-ink">{p.primary_conditions.slice(0, 2).join(', ') || <span className="text-ink-3">None recorded</span>}</span>
                  </td>
                  <td className="hidden px-3 py-3 align-top md:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {p.active_allergies.length ? p.active_allergies.map((a) => <Tag key={a} tone="danger">{a}</Tag>) : <span className="text-ink-3">None known</span>}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-right align-top">
                    <span className="block text-ink">{relativeDays(p.last_visit_date)}</span>
                    <span className="text-ink-3">{p.visit_count} {p.visit_count === 1 ? 'visit' : 'visits'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <footer className="flex items-center justify-between border-t border-rule px-5 py-2.5 text-[0.8125rem] text-ink-2">
            <span>
              {(current - 1) * PAGE_SIZE + 1}–{Math.min(current * PAGE_SIZE, rows.length)} of {rows.length}
            </span>
            <div className="flex gap-1">
              <Button size="sm" tone="quiet" disabled={current === 1} onClick={() => setPage(current - 1)} icon={<ChevronLeft className="h-4 w-4" />}>
                Previous
              </Button>
              <Button size="sm" tone="quiet" disabled={current === pages} onClick={() => setPage(current + 1)}>
                Next <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </footer>
        </div>
      )}
    </div>
  );
}
