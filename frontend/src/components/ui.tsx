import React, { useEffect } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from 'lucide-react';

export type ButtonVariant = 'primary' | 'brand' | 'secondary' | 'ivory' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-[#8F0B13] hover:bg-[#74080F] active:bg-[#5E060C] text-white border border-transparent',
  brand:
    'bg-[#380F17] hover:bg-[#4B1620] active:bg-[#2A0B11] text-[#EFDFC5] border border-transparent',
  secondary:
    'bg-surface hover:bg-surface-muted text-ink-primary border border-border-warm',
  ivory:
    'bg-[#EFDFC5] hover:bg-[#E7D1AE] text-[#380F17] border border-[#D4BD98]',
  danger:
    'bg-[#DC2011] hover:bg-[#B8190D] active:bg-[#99140A] text-white border border-transparent',
  ghost:
    'bg-transparent hover:bg-surface-muted text-ink-secondary hover:text-ink-primary border border-transparent',
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-lg gap-1.5',
  md: 'px-4 py-2 text-xs rounded-lg gap-2',
  lg: 'px-5 py-2.5 text-sm rounded-lg gap-2',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-semibold transition-colors duration-150 disabled:opacity-55 disabled:cursor-not-allowed ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
      {...props}
    >
      {loading && <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" aria-hidden="true" />}
      {children}
    </button>
  );
}

export type BadgeVariant =
  | 'brand'
  | 'crimson'
  | 'ivory'
  | 'critical'
  | 'warning'
  | 'stable'
  | 'neutral'
  | 'mono';

const BADGE_VARIANTS: Record<BadgeVariant, string> = {
  brand: 'bg-[#380F17] text-[#EFDFC5] border border-[#380F17]',
  crimson: 'bg-[#8F0B13]/10 text-[#8F0B13] dark:text-[#FCA5A5] border border-[#8F0B13]/30',
  ivory: 'bg-[#EFDFC5] text-[#380F17] border border-[#D7C19D]',
  critical:
    'bg-[var(--status-critical-bg)] text-[var(--status-critical-fg)] border border-[var(--status-critical-border)]',
  warning:
    'bg-[var(--status-warning-bg)] text-[var(--status-warning-fg)] border border-[var(--status-warning-border)]',
  stable:
    'bg-[var(--status-stable-bg)] text-[var(--status-stable-fg)] border border-[var(--status-stable-border)]',
  neutral: 'bg-surface-muted text-ink-secondary border border-border-warm',
  mono: 'bg-surface-muted text-ink-primary border border-border-warm font-mono tabular-nums',
};

export function Badge({
  variant = 'neutral',
  className = '',
  children,
}: {
  variant?: BadgeVariant;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold leading-tight ${BADGE_VARIANTS[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Card({
  variant = 'default',
  className = '',
  children,
}: {
  variant?: 'default' | 'muted' | 'ivory' | 'brand';
  className?: string;
  children: React.ReactNode;
}) {
  const surfaceStyles: Record<'default' | 'muted' | 'ivory' | 'brand', string> = {
    default: 'bg-surface border border-border-warm text-ink-primary',
    muted: 'bg-surface-muted border border-border-warm text-ink-primary',
    ivory: 'bg-surface-ivory border border-[#D7C19D] dark:border-[#5C443B] text-ink-primary',
    brand: 'bg-[#380F17] border border-[#561925] text-[#FAF8F5]',
  };
  return (
    <div className={`rounded-xl ${surfaceStyles[variant]} ${className}`}>
      {children}
    </div>
  );
}

interface FieldWrapperProps {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}

function FieldWrapper({ id, label, required, hint, error, children }: FieldWrapperProps) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-xs font-semibold text-ink-primary">
        {label}
        {required && <span className="text-[#DC2011] ml-0.5">*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-[11px] text-ink-muted">{hint}</p>}
      {error && (
        <p role="alert" className="text-[11px] font-medium text-[#DC2011]">
          {error}
        </p>
      )}
    </div>
  );
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label?: string;
  hint?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ id, label, hint, error, required, className = '', ...props }, ref) => {
    const inputNode = (
      <input
        ref={ref}
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        className={`w-full px-3 py-2 rounded-lg border bg-surface text-ink-primary text-xs transition-colors placeholder:text-ink-muted ${
          error ? 'border-[#DC2011]' : 'border-border-warm focus:border-[#8F0B13]'
        } ${className}`}
        {...props}
      />
    );
    if (!label) return inputNode;
    return (
      <FieldWrapper id={id} label={label} required={required} hint={hint} error={error}>
        {inputNode}
      </FieldWrapper>
    );
  }
);
Input.displayName = 'Input';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  id: string;
  label?: string;
  hint?: string;
  error?: string;
}

export function Select({ id, label, hint, error, required, className = '', children, ...props }: SelectProps) {
  const selectNode = (
    <select
      id={id}
      required={required}
      aria-invalid={error ? true : undefined}
      className={`w-full px-3 py-2 rounded-lg border bg-surface text-ink-primary text-xs transition-colors ${
        error ? 'border-[#DC2011]' : 'border-border-warm focus:border-[#8F0B13]'
      } ${className}`}
      {...props}
    >
      {children}
    </select>
  );
  if (!label) return selectNode;
  return (
    <FieldWrapper id={id} label={label} required={required} hint={hint} error={error}>
      {selectNode}
    </FieldWrapper>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  id: string;
  label?: string;
  hint?: string;
  error?: string;
}

export function Textarea({ id, label, hint, error, required, className = '', ...props }: TextareaProps) {
  const node = (
    <textarea
      id={id}
      required={required}
      aria-invalid={error ? true : undefined}
      className={`w-full px-3 py-2 rounded-lg border bg-surface text-ink-primary text-xs transition-colors placeholder:text-ink-muted ${
        error ? 'border-[#DC2011]' : 'border-border-warm focus:border-[#8F0B13]'
      } ${className}`}
      {...props}
    />
  );
  if (!label) return node;
  return (
    <FieldWrapper id={id} label={label} required={required} hint={hint} error={error}>
      {node}
    </FieldWrapper>
  );
}

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  maxWidth = 'max-w-xl',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 bg-black/55 flex items-center justify-center p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={`bg-surface border border-border-warm rounded-xl w-full ${maxWidth} shadow-2xl overflow-hidden my-auto`}>
        <div className="px-6 py-4 border-b border-border-warm flex items-start justify-between gap-4 bg-surface-muted/50">
          <div>
            <h3 className="font-serif text-xl font-semibold text-ink-primary leading-snug">{title}</h3>
            {subtitle && <p className="text-xs text-ink-secondary mt-0.5">{subtitle}</p>}
          </div>
          <button
            type="button"
            aria-label={`Close ${title}`}
            onClick={onClose}
            className="p-1.5 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-muted transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-6 max-h-[75vh] overflow-y-auto">{children}</div>
        {footer && (
          <div className="px-6 py-3.5 border-t border-border-warm bg-surface-muted/40 flex items-center justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function AlertBanner({
  variant = 'error',
  message,
  onDismiss,
  className = '',
}: {
  variant?: 'error' | 'warning' | 'success' | 'ivory';
  message: string;
  onDismiss?: () => void;
  className?: string;
}) {
  const styles = {
    error:
      'bg-[var(--status-critical-bg)] border-[var(--status-critical-border)] text-[var(--status-critical-fg)]',
    warning:
      'bg-[var(--status-warning-bg)] border-[var(--status-warning-border)] text-[var(--status-warning-fg)]',
    success:
      'bg-[var(--status-stable-bg)] border-[var(--status-stable-border)] text-[var(--status-stable-fg)]',
    ivory: 'bg-surface-ivory border-[#D7C19D] dark:border-[#5C443B] text-ink-primary',
  };

  const Icon =
    variant === 'error'
      ? AlertTriangle
      : variant === 'success'
      ? CheckCircle2
      : variant === 'warning'
      ? AlertTriangle
      : Info;

  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 ${styles[variant]} ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
        <span className="font-medium leading-relaxed">{message}</span>
      </div>
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss notification"
          onClick={onDismiss}
          className="p-1 rounded-md hover:bg-black/10 transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border-warm bg-surface p-8 text-center space-y-2.5">
      <h3 className="text-sm font-semibold text-ink-primary">{title}</h3>
      <p className="text-xs text-ink-secondary max-w-md mx-auto leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <div className="pt-1">
          <Button variant="secondary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
}

export function SkeletonBlock({ className = 'h-24 w-full' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`rounded-xl border border-border-warm bg-surface-muted/70 animate-pulse ${className}`}
    />
  );
}
