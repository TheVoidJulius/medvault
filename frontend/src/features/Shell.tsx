import { ReactNode, useState } from 'react';
import { LayoutDashboard, LogOut, Menu, MessageSquareText, Moon, ScrollText, Search, Sun, UserPlus, Users, X } from 'lucide-react';
import { Button } from '../components/ui';
import { cx, fullName } from '../lib/format';
import type { PatientListItem, User } from '../lib/types';
import type { Route } from '../workspace';

const NAV = [
  { view: 'overview', label: 'Overview', icon: LayoutDashboard },
  { view: 'patients', label: 'Patients', icon: Users },
  { view: 'search', label: 'Ask the records', icon: MessageSquareText },
  { view: 'audit', label: 'Audit trail', icon: ScrollText },
] as const;

function isActive(route: Route, view: string) {
  return route.view === view || (view === 'patients' && route.view === 'chart');
}

function Rail({
  route,
  navigate,
  user,
  recent,
  onSignOut,
  onClose,
}: {
  route: Route;
  navigate: (r: Route) => void;
  user: User;
  recent: PatientListItem[];
  onSignOut: () => void;
  onClose?: () => void;
}) {
  const go = (r: Route) => {
    navigate(r);
    onClose?.();
  };
  return (
    <div className="flex h-full flex-col bg-rail text-rail-ink">
      <div className="flex h-16 items-center justify-between px-5">
        <span className="flex items-center gap-2.5">
          <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
            <rect width="32" height="32" rx="8" fill="rgb(var(--rail-line))" />
            <path d="M4 17h6l2-6 4 12 3-9 2 3h7" fill="none" stroke="#FF6B76" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-[0.9375rem] font-extrabold tracking-[-0.03em] text-white">MedVault AI</span>
        </span>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close navigation" className="rounded-ctl p-1.5 hover:bg-white/10">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav aria-label="Workspace" className="space-y-0.5 px-3">
        {NAV.map(({ view, label, icon: Icon }) => {
          const active = isActive(route, view);
          return (
            <button
              key={view}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => go({ view } as Route)}
              className={cx(
                'flex w-full items-center gap-3 rounded-ctl px-3 py-2 text-sm font-semibold transition-colors',
                active ? 'bg-white/[0.09] text-white' : 'text-rail-ink/75 hover:bg-white/5 hover:text-white',
              )}
            >
              <Icon className={cx('h-4 w-4', active && 'text-[#9DB0FF]')} aria-hidden />
              {label}
            </button>
          );
        })}
      </nav>

      {recent.length > 0 && (
        <div className="mt-8 px-3">
          <h2 className="px-3 pb-2 text-2xs font-semibold text-rail-ink/50">Recently opened</h2>
          <ul className="space-y-0.5">
            {recent.map((p) => {
              const active = route.view === 'chart' && route.patientId === p.id;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => go({ view: 'chart', patientId: p.id, tab: 'timeline' })}
                    className={cx(
                      'flex w-full items-center justify-between gap-2 rounded-ctl px-3 py-1.5 text-left text-[0.8125rem]',
                      active ? 'bg-white/[0.09] text-white' : 'text-rail-ink/75 hover:bg-white/5 hover:text-white',
                    )}
                  >
                    <span className="truncate">{fullName(p)}</span>
                    <span className="code shrink-0 text-[10px] text-rail-ink/45">{p.mrn.slice(-5)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-auto border-t border-rail-line px-5 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-[0.8125rem] font-semibold text-white">{user.full_name}</p>
            <p className="text-2xs capitalize text-rail-ink/55">{user.doctor_profile?.specialization ?? user.role_name}</p>
          </div>
          <button type="button" onClick={onSignOut} aria-label="Sign out" title="Sign out" className="rounded-ctl p-2 text-rail-ink/70 hover:bg-white/10 hover:text-white">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function Shell({
  route,
  navigate,
  user,
  recent,
  theme,
  onToggleTheme,
  onSignOut,
  onOpenPalette,
  onRegister,
  children,
}: {
  route: Route;
  navigate: (r: Route) => void;
  user: User;
  recent: PatientListItem[];
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onSignOut: () => void;
  onOpenPalette: () => void;
  onRegister: () => void;
  children: ReactNode;
}) {
  const [drawer, setDrawer] = useState(false);
  const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 lg:block">
        <Rail route={route} navigate={navigate} user={user} recent={recent} onSignOut={onSignOut} />
      </aside>
      {drawer && (
        <div className="fixed inset-0 z-50 flex bg-ink/50 lg:hidden" onMouseDown={(e) => e.target === e.currentTarget && setDrawer(false)}>
          <aside className="h-full w-72 max-w-[85vw] animate-slidein">
            <Rail route={route} navigate={navigate} user={user} recent={recent} onSignOut={onSignOut} onClose={() => setDrawer(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-rule bg-paper/90 px-4 backdrop-blur sm:px-6">
          <button type="button" onClick={() => setDrawer(true)} aria-label="Open navigation" className="rounded-ctl border border-rule p-2 lg:hidden">
            <Menu className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onOpenPalette}
            className="flex h-10 min-w-0 flex-1 items-center gap-2.5 rounded-ctl border border-rule bg-sheet px-3 text-left text-sm text-ink-3 transition-colors hover:border-rule-strong sm:max-w-md"
          >
            <Search className="h-4 w-4 shrink-0" aria-hidden />
            <span className="truncate">Find a patient or jump anywhere</span>
            <kbd className="code ml-auto hidden rounded-tag border border-rule px-1.5 text-[10px] sm:inline">{isMac ? '⌘' : 'Ctrl'} K</kbd>
          </button>
          <div className="ml-auto flex items-center gap-2">
            <Button
              tone="quiet"
              size="sm"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              onClick={onToggleTheme}
              icon={theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            />
            <Button tone="pen" size="sm" onClick={onRegister} icon={<UserPlus className="h-4 w-4" />}>
              <span className="hidden sm:inline">Register patient</span>
              <span className="sm:hidden">New</span>
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1320px] flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
