import { createContext, useContext } from 'react';
import type { Api } from './lib/http';
import type { Medication, PatientListItem, User } from './lib/types';

export type ChartTab = 'overview' | 'visits' | 'labs' | 'medicines' | 'summary' | 'ask' | 'new-visit';

export type Route =
  | { view: 'overview' }
  | { view: 'patients' }
  | { view: 'chart'; patientId: number; tab: ChartTab; focusVisit?: number }
  | { view: 'search'; q?: string }
  | { view: 'audit' };

export interface Workspace {
  api: Api;
  user: User;
  route: Route;
  navigate: (route: Route) => void;
  notify: (message: string, tone?: 'ok' | 'error') => void;
  patients: PatientListItem[];
  patientsLoading: boolean;
  reloadPatients: () => Promise<void>;
  medications: Medication[];
  /** Bumped after any write so views re-fetch what they show. */
  revision: number;
  bumpRevision: () => void;
  openRegister: () => void;
}

export const WorkspaceContext = createContext<Workspace | null>(null);

export function useWorkspace(): Workspace {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used inside the signed-in workspace.');
  return ctx;
}

export function routeToHash(route: Route): string {
  switch (route.view) {
    case 'chart':
      return `#/patients/${route.patientId}/${route.tab}${route.focusVisit ? `?visit=${route.focusVisit}` : ''}`;
    case 'patients':
      return '#/patients';
    case 'search':
      return route.q ? `#/search?q=${encodeURIComponent(route.q)}` : '#/search';
    case 'audit':
      return '#/audit';
    default:
      return '#/overview';
  }
}

const TABS: ChartTab[] = ['overview', 'visits', 'labs', 'medicines', 'summary', 'ask', 'new-visit'];

export function hashToRoute(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#/, '').split('?');
  const parts = path.split('/').filter(Boolean);
  if (parts[0] === 'patients' && parts[1]) {
    // 'timeline' is the old name of the visits tab; keep old links working.
    const raw = parts[2] === 'timeline' ? 'visits' : parts[2] ?? '';
    const tab = (TABS as string[]).includes(raw) ? (raw as ChartTab) : 'overview';
    const visit = Number(new URLSearchParams(query).get('visit')) || undefined;
    return { view: 'chart', patientId: Number(parts[1]), tab, focusVisit: visit };
  }
  if (parts[0] === 'patients') return { view: 'patients' };
  if (parts[0] === 'search') return { view: 'search', q: new URLSearchParams(query).get('q') ?? undefined };
  if (parts[0] === 'audit') return { view: 'audit' };
  return { view: 'overview' };
}
