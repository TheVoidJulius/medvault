import { Component, ErrorInfo, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { CitationProvider } from './components/citations';
import { CommandPalette } from './components/CommandPalette';
import { Button, Notice } from './components/ui';
import { AuditLog } from './features/AuditLog';
import { Overview } from './features/Overview';
import { PatientChart } from './features/chart/PatientChart';
import { PatientDirectory } from './features/PatientDirectory';
import { RegisterPatientModal } from './features/PatientForms';
import { RecordSearch } from './features/RecordSearch';
import { Shell } from './features/Shell';
import { Landing } from './features/Landing';
import { SignIn } from './features/SignIn';
import { createApi, errorText } from './lib/http';
import type { Medication, PatientListItem, User } from './lib/types';
import { Route, WorkspaceContext, hashToRoute, routeToHash } from './workspace';

class ErrorBoundary extends Component<{ children: ReactNode }, { message: string | null }> {
  state = { message: null as string | null };
  static getDerivedStateFromError(error: Error) {
    return { message: error.message || 'The page failed to render.' };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info);
  }
  render() {
    if (!this.state.message) return this.props.children;
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md space-y-4">
          <Notice tone="error">{this.state.message}</Notice>
          <Button tone="ink" onClick={() => window.location.reload()}>
            Reload MedVault
          </Button>
        </div>
      </div>
    );
  }
}

type Theme = 'light' | 'dark';

function readSession(): { token: string | null; user: User | null } {
  try {
    const token = sessionStorage.getItem('medvault_token');
    const raw = sessionStorage.getItem('medvault_user');
    return { token, user: raw ? (JSON.parse(raw) as User) : null };
  } catch {
    return { token: null, user: null };
  }
}

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem('medvault_theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch {
    /* storage blocked */
  }
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function App() {
  return (
    <ErrorBoundary>
      <MedVault />
    </ErrorBoundary>
  );
}

function MedVault() {
  const [{ token, user }, setSession] = useState(readSession);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [route, setRoute] = useState<Route>(() => hashToRoute(window.location.hash));
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(false);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState<{ message: string; tone: 'ok' | 'error' } | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [recentIds, setRecentIds] = useState<number[]>([]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('medvault_theme', theme);
    } catch {
      /* storage blocked */
    }
  }, [theme]);
  const toggleTheme = useCallback(() => setTheme((t) => (t === 'light' ? 'dark' : 'light')), []);

  const signOut = useCallback(() => {
    sessionStorage.removeItem('medvault_token');
    sessionStorage.removeItem('medvault_user');
    setSession({ token: null, user: null });
    setPatients([]);
    setRecentIds([]);
    setNotice(null);
  }, []);

  const api = useMemo(() => createApi(token, signOut), [token, signOut]);

  const navigate = useCallback((next: Route) => {
    const hash = routeToHash(next);
    if (window.location.hash !== hash) window.history.pushState(null, '', hash);
    setRoute(next);
    window.scrollTo?.({ top: 0 });
  }, []);

  useEffect(() => {
    const onPop = () => setRoute(hashToRoute(window.location.hash));
    window.addEventListener('popstate', onPop);
    window.addEventListener('hashchange', onPop);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('hashchange', onPop);
    };
  }, []);

  useEffect(() => {
    if (route.view === 'chart') setRecentIds((ids) => [route.patientId, ...ids.filter((id) => id !== route.patientId)].slice(0, 5));
  }, [route]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement | null)?.tagName ?? '');
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      } else if (e.key === '/' && !typing) {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const reloadPatients = useCallback(async () => {
    if (!token) return;
    setPatientsLoading(true);
    try {
      setPatients(await api<PatientListItem[]>('/api/patients'));
    } catch (err) {
      setNotice({ message: errorText(err), tone: 'error' });
    } finally {
      setPatientsLoading(false);
    }
  }, [api, token]);

  useEffect(() => {
    if (!token) return;
    reloadPatients();
    api<Medication[]>('/api/patients/medications/catalog')
      .then(setMedications)
      .catch(() => undefined);
  }, [token, api, reloadPatients]);

  const notify = useCallback((message: string, tone: 'ok' | 'error' = 'ok') => setNotice({ message, tone }), []);
  useEffect(() => {
    if (notice?.tone !== 'ok') return;
    const t = setTimeout(() => setNotice(null), 6000);
    return () => clearTimeout(t);
  }, [notice]);
  const bumpRevision = useCallback(() => setRevision((r) => r + 1), []);
  const openRegister = useCallback(() => setRegisterOpen(true), []);

  if (!token || !user) {
    if (window.location.hash !== '#/sign-in') {
      return (
        <Landing
          onSignIn={() => {
            window.history.pushState(null, '', '#/sign-in');
            setRoute({ view: 'overview' });
            window.scrollTo?.({ top: 0 });
          }}
        />
      );
    }
    return (
      <SignIn
        onBack={() => {
          window.history.pushState(null, '', '#/');
          setRoute({ view: 'overview' });
        }}
        onSignedIn={(t, u) => {
          sessionStorage.setItem('medvault_token', t);
          sessionStorage.setItem('medvault_user', JSON.stringify(u));
          setSession({ token: t, user: u });
          navigate({ view: 'overview' });
        }}
      />
    );
  }

  const recent = recentIds.map((id) => patients.find((p) => p.id === id)).filter(Boolean) as PatientListItem[];

  const workspace = {
    api,
    user,
    route,
    navigate,
    notify,
    patients,
    patientsLoading,
    reloadPatients,
    medications,
    revision,
    bumpRevision,
    openRegister,
  };

  return (
    <WorkspaceContext.Provider value={workspace}>
      <CitationProvider onOpenVisit={(patientId, visitId) => navigate({ view: 'chart', patientId, tab: 'timeline', focusVisit: visitId })}>
        <Shell
          route={route}
          navigate={navigate}
          user={user}
          recent={recent}
          theme={theme}
          onToggleTheme={toggleTheme}
          onSignOut={signOut}
          onOpenPalette={() => setPaletteOpen(true)}
          onRegister={openRegister}
        >
          {notice && (
            <div className="mb-5">
              <Notice tone={notice.tone} onDismiss={() => setNotice(null)}>
                {notice.message}
              </Notice>
            </div>
          )}
          {route.view === 'overview' && <Overview />}
          {route.view === 'patients' && <PatientDirectory />}
          {route.view === 'chart' && <PatientChart key={route.patientId} patientId={route.patientId} tab={route.tab} focusVisit={route.focusVisit} />}
          {route.view === 'search' && <RecordSearch key={route.q ?? ''} initialQuery={route.q} />}
          {route.view === 'audit' && <AuditLog />}
        </Shell>

        <CommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          patients={patients}
          navigate={navigate}
          onRegister={openRegister}
          onToggleTheme={toggleTheme}
        />
        <RegisterPatientModal
          open={registerOpen}
          onClose={() => setRegisterOpen(false)}
          onCreated={(p) => {
            setRegisterOpen(false);
            notify(`Registered ${p.first_name} ${p.last_name} as ${p.mrn}.`);
            reloadPatients();
            bumpRevision();
            navigate({ view: 'chart', patientId: p.id, tab: 'timeline' });
          }}
        />
      </CitationProvider>
    </WorkspaceContext.Provider>
  );
}
