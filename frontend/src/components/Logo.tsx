import { cx } from '../lib/format';

/**
 * MedVault mark: citation brackets around three record rows, the middle row
 * highlighted as the one being cited. It is the product in one glyph:
 * stored records, and an answer that points at exactly one of them.
 */
export function LogoMark({ className, onDark = false }: { className?: string; onDark?: boolean }) {
  const tile = onDark ? '#2A323A' : 'rgb(var(--ink))';
  const line = onDark ? '#D8DEE4' : 'rgb(var(--sheet))';
  const cited = onDark ? '#9DB0FF' : '#8EA2FF';
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" fill={tile} />
      <path d="M10.5 8.5H8v15h2.5M21.5 8.5H24v15h-2.5" fill="none" stroke={line} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12.5 11.5h7M12.5 20.5h7" stroke={line} strokeOpacity="0.55" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M12.5 16h7" stroke={cited} strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ className, onDark = false, size = 'md' }: { className?: string; onDark?: boolean; size?: 'md' | 'lg' }) {
  return (
    <span className={cx('flex items-center gap-2.5', className)}>
      <LogoMark onDark={onDark} className={size === 'lg' ? 'h-8 w-8' : 'h-7 w-7'} />
      <span className={cx('font-extrabold tracking-[-0.035em]', size === 'lg' ? 'text-lg' : 'text-[0.9375rem]', onDark && 'text-white')}>MedVault</span>
    </span>
  );
}
