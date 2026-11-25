const DAY = 86_400_000;

export function ageFrom(dob: string, at: Date = new Date()): number {
  const d = new Date(dob);
  let age = at.getFullYear() - d.getFullYear();
  const m = at.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && at.getDate() < d.getDate())) age -= 1;
  return age;
}

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!iso) return '—';
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', ...opts });
}

export function relativeDays(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return 'No visits yet';
  const days = Math.round((now.getTime() - new Date(iso).getTime()) / DAY);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 45) return `${days} days ago`;
  const months = Math.round(days / 30.4);
  if (months < 18) return `${months} months ago`;
  return `${Math.round(days / 365)} years ago`;
}

export function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'short' });
}

export function initials(first: string, last: string): string {
  return `${first.trim()[0] ?? ''}${last.trim()[0] ?? ''}`.toUpperCase();
}

export const fullName = (p: { first_name: string; last_name: string }) => `${p.first_name} ${p.last_name}`;

/** Parse "128/84 mmHg" into systolic/diastolic numbers. */
export function parseBp(bp: string | null | undefined): { sys: number; dia: number } | null {
  const m = bp?.match(/(\d{2,3})\s*\/\s*(\d{2,3})/);
  return m ? { sys: Number(m[1]), dia: Number(m[2]) } : null;
}

export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(' ');
