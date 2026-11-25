import { FormEvent, useState } from 'react';
import { ArrowRight, Lock } from 'lucide-react';
import { Button, Input, Notice } from '../components/ui';
import { EcgTrace } from '../components/vitals';
import { cx } from '../lib/format';
import type { User } from '../lib/types';

const DEMO_ACCOUNTS = [
  { name: 'Dr. Ananya Sharma, MD', role: 'Internal medicine', email: 'dr.sharma@medvault.edu', password: 'Doctor@123' },
  { name: 'Dr. Rajesh Verma, DM', role: 'Neurology', email: 'dr.verma@medvault.edu', password: 'Doctor@123' },
  { name: 'Dr. Harpreet Kaur, MD', role: 'Paediatrics', email: 'dr.kaur@medvault.edu', password: 'Doctor@123' },
  { name: 'Pushkar Panwar', role: 'Records administrator', email: 'admin@medvault.edu', password: 'Admin@123' },
];

export function SignIn({ onSignedIn }: { onSignedIn: (token: string, user: User) => void }) {
  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState(DEMO_ACCOUNTS[0].password);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'That email and password don’t match an account.');
      onSignedIn(body.access_token, body.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.15fr_1fr]">
      <section className="ecg-paper relative flex flex-col justify-between overflow-hidden border-b border-rule px-6 py-8 sm:px-12 lg:border-b-0 lg:border-r lg:py-12">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
            <rect width="32" height="32" rx="8" fill="rgb(var(--ink))" />
            <path d="M4 17h6l2-6 4 12 3-9 2 3h7" fill="none" stroke="rgb(var(--trace))" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-lg font-extrabold tracking-[-0.03em]">MedVault AI</span>
        </div>

        <div className="my-10 lg:my-0">
          <h1 className="max-w-xl text-[2.5rem] font-extrabold leading-[1.02] tracking-[-0.045em] sm:text-[3.5rem]">
            Every patient’s history, read back to you with its sources.
          </h1>
          <EcgTrace className="mt-8 h-20 w-full sm:h-24" />
          <p className="mt-6 max-w-lg text-[0.9375rem] leading-relaxed text-ink-2">
            Visits, diagnoses, prescriptions and labs live in one relational record. Summaries and answers cite the exact rows they came from, and say so when the record is silent.
          </p>
        </div>

        <dl className="grid max-w-lg grid-cols-3 gap-4 text-[0.8125rem]">
          <div>
            <dt className="text-ink-3">Patients</dt>
            <dd className="text-xl font-bold">160+</dd>
          </div>
          <div>
            <dt className="text-ink-3">Linked tables</dt>
            <dd className="text-xl font-bold">13</dd>
          </div>
          <div>
            <dt className="text-ink-3">Claims cited</dt>
            <dd className="text-xl font-bold">100%</dd>
          </div>
        </dl>
      </section>

      <section className="flex items-center justify-center bg-sheet px-6 py-10 sm:px-12">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-extrabold tracking-[-0.03em]">Sign in</h2>
          <p className="mt-1 text-[0.8125rem] text-ink-2">All records here are synthetic. Pick a demo account or use your own credentials.</p>

          <fieldset className="mt-6">
            <legend className="mb-2 text-[0.8125rem] font-semibold">Demo accounts</legend>
            <div className="overflow-hidden rounded-ctl border border-rule">
              {DEMO_ACCOUNTS.map((a) => {
                const selected = email === a.email;
                return (
                  <button
                    key={a.email}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => {
                      setEmail(a.email);
                      setPassword(a.password);
                    }}
                    className={cx(
                      'flex w-full items-center justify-between border-b border-rule px-3.5 py-2.5 text-left last:border-b-0 transition-colors',
                      selected ? 'bg-pen-wash' : 'hover:bg-well',
                    )}
                  >
                    <span>
                      <span className={cx('block text-sm font-semibold', selected && 'text-pen')}>{a.name}</span>
                      <span className="block text-2xs text-ink-3">{a.role}</span>
                    </span>
                    <span className={cx('h-2 w-2 rounded-full', selected ? 'bg-pen' : 'bg-rule-strong')} aria-hidden />
                  </button>
                );
              })}
            </div>
          </fieldset>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Input label="Email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <Input
              label="Password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <Notice tone="error">{error}</Notice>}
            <Button type="submit" tone="ink" loading={busy} className="w-full" icon={!busy ? <Lock className="h-4 w-4" /> : undefined}>
              Sign in
            </Button>
          </form>

          <div className="mt-8 flex items-center justify-between border-t border-rule pt-4 text-2xs text-ink-3">
            <span>Pushkar Panwar &amp; Saksham Singh</span>
            <a href="/presentation.html" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-pen hover:underline">
              Project slides <ArrowRight className="h-3 w-3" aria-hidden />
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
