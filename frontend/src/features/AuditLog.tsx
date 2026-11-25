import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Empty, Input, Notice, PageHeader, Skeleton, Tag } from '../components/ui';
import { errorText } from '../lib/http';
import type { AuditEntry } from '../lib/types';
import { useWorkspace } from '../workspace';

const ACTION_LABEL: Record<string, string> = {
  USER_LOGIN: 'Signed in',
  CREATE_PATIENT: 'Registered patient',
  UPDATE_PATIENT: 'Edited patient',
  CREATE_VISIT_RECORD: 'Recorded visit',
  UPDATE_VISIT_RECORD: 'Edited visit',
  ADD_ALLERGY: 'Added allergy',
  ADD_MEDICAL_HISTORY: 'Added history',
  AI_GENERATE_SUMMARY: 'Generated AI summary',
  AI_HISTORICAL_RETRIEVAL: 'Asked the records',
  AI_EXTRACT_CLINICAL_NOTE: 'Extracted note',
};

const humanise = (action: string) => ACTION_LABEL[action] ?? action.toLowerCase().replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

export function AuditLog() {
  const { api, revision } = useWorkspace();
  const [logs, setLogs] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');

  useEffect(() => {
    api<AuditEntry[]>('/api/auth/audit-logs?limit=200')
      .then(setLogs)
      .catch((e) => setError(errorText(e)));
  }, [api, revision]);

  const rows = useMemo(() => {
    const term = q.trim().toLowerCase();
    return (logs ?? []).filter((l) => !term || `${l.action} ${humanise(l.action)} ${l.user_name} ${l.user_role} ${l.detail ?? ''}`.toLowerCase().includes(term));
  }, [logs, q]);

  return (
    <div className="space-y-5">
      <PageHeader title="Audit trail" lede="Every sign-in, record change, AI summary and question, with who did it and when." />
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-ink-3" aria-hidden />
        <Input aria-label="Filter audit entries" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by person, action or patient" className="pl-9" />
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {!logs && !error && <Skeleton className="h-96" />}
      {logs && rows.length === 0 && <Empty title="No entries match" body="Try a different name or action." />}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
          <table className="w-full text-left text-[0.8125rem]">
            <thead className="border-b border-rule text-ink-3">
              <tr>
                <th className="px-5 py-2.5 font-medium">When</th>
                <th className="px-3 py-2.5 font-medium">Who</th>
                <th className="px-3 py-2.5 font-medium">Action</th>
                <th className="px-5 py-2.5 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((l) => (
                <tr key={l.id} className="border-b border-rule align-top last:border-0">
                  <td className="code whitespace-nowrap px-5 py-2.5 text-ink-2">{l.created_at.slice(0, 16).replace('T', ' ')}</td>
                  <td className="px-3 py-2.5">
                    <span className="block font-semibold">{l.user_name}</span>
                    <span className="text-2xs capitalize text-ink-3">{l.user_role}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5">
                    <Tag tone={l.action.startsWith('AI_') ? 'pen' : 'neutral'}>{humanise(l.action)}</Tag>
                  </td>
                  <td className="px-5 py-2.5 text-ink-2">{l.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
