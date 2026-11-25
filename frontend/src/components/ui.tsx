import React, { ReactNode, useEffect, useId, useRef } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, X } from 'lucide-react';
import { cx } from '../lib/format';

/* ------------------------------------------------------------------ Button */

type ButtonTone = 'pen' | 'ink' | 'line' | 'quiet' | 'danger';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ButtonTone;
  size?: 'sm' | 'md';
  loading?: boolean;
  icon?: ReactNode;
}

const BUTTON_TONES: Record<ButtonTone, string> = {
  pen: 'bg-pen text-white hover:bg-pen-strong dark:text-paper',
  ink: 'bg-ink text-sheet hover:bg-ink/85',
  line: 'border border-rule-strong bg-sheet text-ink hover:border-ink-3 hover:bg-well',
  quiet: 'text-ink-2 hover:bg-well hover:text-ink',
  danger: 'bg-trace text-white hover:bg-trace/90',
};

export function Button({
  tone = 'line',
  size = 'md',
  loading = false,
  icon,
  className,
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cx(
        'inline-flex items-center justify-center gap-1.5 rounded-ctl font-semibold whitespace-nowrap transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-50',
        size === 'sm' ? 'h-8 px-2.5 text-[0.8125rem]' : 'h-10 px-4 text-sm',
        BUTTON_TONES[tone],
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

/* --------------------------------------------------------------------- Tag */

export type TagTone = 'neutral' | 'pen' | 'ok' | 'warn' | 'danger' | 'outline';

const TAG_TONES: Record<TagTone, string> = {
  neutral: 'bg-well text-ink-2',
  pen: 'bg-pen-wash text-pen',
  ok: 'bg-ok-wash text-ok',
  warn: 'bg-warn-wash text-warn',
  danger: 'bg-trace-wash text-trace',
  outline: 'border border-rule-strong text-ink-2',
};

export function Tag({ tone = 'neutral', className, children }: { tone?: TagTone; className?: string; children: ReactNode }) {
  return (
    <span className={cx('inline-flex items-center gap-1 rounded-tag px-1.5 py-0.5 text-2xs font-semibold', TAG_TONES[tone], className)}>
      {children}
    </span>
  );
}

/** Maps a stored clinical status to the tag tone that signals it. */
export function statusTone(status: string): TagTone {
  const s = status.toLowerCase();
  if (['critical', 'severe', 'life-threatening', 'high', 'low', 'abnormal', 'active'].includes(s)) return 'danger';
  if (['provisional', 'moderate'].includes(s)) return 'warn';
  if (['confirmed', 'controlled', 'resolved', 'normal', 'mild'].includes(s)) return 'ok';
  return 'neutral';
}

/* ------------------------------------------------------------------- Panel */

export function Panel({
  title,
  aside,
  className,
  bodyClassName,
  children,
  as: Tag = 'section',
}: {
  title?: ReactNode;
  aside?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
  as?: 'section' | 'div' | 'article';
}) {
  return (
    <Tag className={cx('rounded-panel border border-rule bg-sheet', className)}>
      {(title || aside) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-5 py-3">
          {title && <h2 className="text-[0.9375rem] font-bold tracking-[-0.01em]">{title}</h2>}
          {aside}
        </header>
      )}
      <div className={cx('p-5', bodyClassName)}>{children}</div>
    </Tag>
  );
}

/* ------------------------------------------------------------------ Fields */

interface FieldShellProps {
  id: string;
  label?: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}

function FieldShell({ id, label, hint, required, children }: FieldShellProps) {
  return (
    <div className="min-w-0">
      {label && (
        <label htmlFor={id} className="mb-1 block text-[0.8125rem] font-semibold text-ink">
          {label}
          {required && <span className="text-trace"> *</span>}
        </label>
      )}
      {children}
      {hint && <p className="mt-1 text-2xs text-ink-3">{hint}</p>}
    </div>
  );
}

const CONTROL =
  'w-full rounded-ctl border border-rule-strong bg-sheet px-3 text-sm text-ink placeholder:text-ink-3 transition-colors hover:border-ink-3 focus:border-pen focus:outline-none focus:ring-2 focus:ring-pen/20 disabled:opacity-60';

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string };

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { id, label, hint, required, className, ...rest },
  ref,
) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldShell id={fieldId} label={label} hint={hint} required={required}>
      <input ref={ref} id={fieldId} required={required} className={cx(CONTROL, 'h-10', className)} {...rest} />
    </FieldShell>
  );
});

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string; hint?: string };

export function Select({ id, label, hint, required, className, children, ...rest }: SelectProps) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldShell id={fieldId} label={label} hint={hint} required={required}>
      <select id={fieldId} required={required} className={cx(CONTROL, 'h-10 pr-8', className)} {...rest}>
        {children}
      </select>
    </FieldShell>
  );
}

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; hint?: string };

export function Textarea({ id, label, hint, required, className, ...rest }: TextareaProps) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldShell id={fieldId} label={label} hint={hint} required={required}>
      <textarea id={fieldId} required={required} className={cx(CONTROL, 'min-h-[96px] py-2 leading-relaxed', className)} {...rest} />
    </FieldShell>
  );
}

/* ------------------------------------------------------- Overlays & dialogs */

function useEscape(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  width = 'max-w-2xl',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  width?: string;
}) {
  useEscape(open, onClose);
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open) ref.current?.querySelector<HTMLElement>('input, select, textarea, button')?.focus();
  }, [open]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 p-0 backdrop-blur-[2px] sm:items-center sm:p-6"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx('flex max-h-[92vh] w-full flex-col rounded-t-panel border border-rule bg-sheet shadow-float animate-rise sm:rounded-panel', width)}
      >
        <header className="flex items-start justify-between gap-4 border-b border-rule px-6 py-4">
          <div>
            <h2 id={titleId} className="text-lg font-bold tracking-[-0.015em]">{title}</h2>
            {description && <p className="mt-0.5 text-[0.8125rem] text-ink-2">{description}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-ctl p-1.5 text-ink-3 hover:bg-well hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

export function Drawer({
  open,
  onClose,
  label,
  children,
}: {
  open: boolean;
  onClose: () => void;
  label: string;
  children: ReactNode;
}) {
  useEscape(open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-ink/25" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside role="dialog" aria-modal="true" aria-label={label} className="flex h-full w-full max-w-md flex-col border-l border-rule bg-sheet shadow-float animate-slidein">
        {children}
      </aside>
    </div>
  );
}

/* ------------------------------------------------------- Feedback & states */

export function Notice({ tone, children, onDismiss }: { tone: 'ok' | 'error'; children: ReactNode; onDismiss?: () => void }) {
  const Icon = tone === 'ok' ? CheckCircle2 : AlertTriangle;
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cx(
        'flex items-start gap-2.5 rounded-ctl border px-3.5 py-2.5 text-[0.8125rem] font-medium',
        tone === 'ok' ? 'border-ok/25 bg-ok-wash text-ok' : 'border-trace/25 bg-trace-wash text-trace',
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="flex-1">{children}</div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss message" className="opacity-70 hover:opacity-100">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function Empty({
  title,
  body,
  action,
  icon,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-panel border border-dashed border-rule-strong px-6 py-12 text-center">
      {icon && <div className="mb-3 text-ink-3">{icon}</div>}
      <h3 className="text-[0.9375rem] font-bold">{title}</h3>
      {body && <p className="mt-1 max-w-sm text-[0.8125rem] text-ink-2">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('animate-pulse rounded-ctl bg-well', className)} aria-hidden />;
}

/* -------------------------------------------------------------------- Tabs */

export function Tabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: string; icon?: ReactNode; count?: number }[];
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-rule">
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cx(
              '-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors',
              active ? 'border-pen text-ink' : 'border-transparent text-ink-3 hover:text-ink',
            )}
          >
            {item.icon}
            {item.label}
            {item.count !== undefined && <span className="code text-ink-3">{item.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/* ---------------------------------------------------------------- Headings */

export function PageHeader({ title, lede, actions }: { title: string; lede?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <h1 className="text-[1.75rem] font-extrabold leading-tight tracking-[-0.03em]">{title}</h1>
        {lede && <p className="mt-1 text-ink-2">{lede}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
