import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Empty, Input } from '../../components/ui';
import { formatDate } from '../../lib/format';
import type { PatientDetail } from '../../lib/types';
import { medGroups } from './records';

export function Medicines({ patient, onOpenVisit }: { patient: PatientDetail; onOpenVisit: (visitId: number) => void }) {
  const groups = useMemo(() => medGroups(patient), [patient]);
  const [q, setQ] = useState('');
  const shown = groups.filter((g) => !q.trim() || g.name.toLowerCase().includes(q.trim().toLowerCase()));

  if (groups.length === 0) return <Empty title="No medicines recorded" body="Medicines ordered at a visit appear here, one row per medicine." />;

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
        <Input aria-label="Search medicines" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a medicine, e.g. heparin" className="pl-9" />
      </div>
      <p className="text-[0.875rem] text-ink-3">{groups.length} different medicines, most recently ordered first.</p>

      <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
        <table className="nums w-full text-left text-[0.9375rem]">
          <thead className="border-b border-rule text-[0.8125rem] text-ink-3">
            <tr>
              <th className="px-4 py-2.5 font-medium">Medicine</th>
              <th className="px-3 py-2.5 font-medium">Last dose and how often</th>
              <th className="hidden px-3 py-2.5 font-medium md:table-cell">Ordered</th>
              <th className="px-4 py-2.5 text-right font-medium">Last ordered</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((g) => {
              const last = g.orders[0];
              const first = g.orders[g.orders.length - 1];
              return (
                <tr key={g.name} className="border-b border-rule align-top last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-semibold">{g.name}</p>
                    {g.strength && g.strength !== 'As charted' && <p className="text-[0.8125rem] text-ink-3">{g.strength}</p>}
                  </td>
                  <td className="px-3 py-3">
                    <p>{last.dosage}</p>
                    <p className="text-[0.8125rem] text-ink-2">{last.frequency}</p>
                  </td>
                  <td className="hidden whitespace-nowrap px-3 py-3 text-ink-2 md:table-cell">
                    {g.orders.length === 1 ? 'Once' : `${g.orders.length} visits`}
                    {g.orders.length > 1 && <span className="block text-[0.8125rem] text-ink-3">since {formatDate(first.date, { day: undefined })}</span>}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <p>{formatDate(last.date)}</p>
                    <button type="button" onClick={() => onOpenVisit(last.visitId)} className="text-[0.8125rem] font-semibold text-pen hover:underline">
                      Open visit
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {shown.length === 0 && <p className="px-4 py-6 text-center text-[0.9375rem] text-ink-3">No medicine matches.</p>}
      </div>
    </div>
  );
}
