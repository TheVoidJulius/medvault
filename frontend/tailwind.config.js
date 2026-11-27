/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: token('paper'),
        sheet: token('sheet'),
        well: token('well'),
        rule: token('rule'),
        'rule-strong': token('rule-strong'),
        ink: token('ink'),
        'ink-2': token('ink-2'),
        'ink-3': token('ink-3'),
        pen: token('pen'),
        'pen-strong': token('pen-strong'),
        'pen-wash': token('pen-wash'),
        trace: token('trace'),
        'trace-wash': token('trace-wash'),
        ok: token('ok'),
        'ok-wash': token('ok-wash'),
        warn: token('warn'),
        'warn-wash': token('warn-wash'),
        rail: token('rail'),
        'rail-ink': token('rail-ink'),
        'rail-line': token('rail-line'),
        grid: token('grid'),
      },
      fontFamily: {
        sans: ['Archivo', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      borderRadius: {
        tag: '2px',
        ctl: '2px',
        panel: '2px',
      },
      boxShadow: {
        float: '0 24px 60px -20px rgb(20 26 31 / 0.35), 0 2px 6px rgb(20 26 31 / 0.08)',
      },
      keyframes: {
        draw: { from: { strokeDashoffset: 'var(--len)' }, to: { strokeDashoffset: '0' } },
        rise: { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'none' } },
        slidein: { from: { transform: 'translateX(24px)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
      },
      animation: {
        draw: 'draw 2.4s cubic-bezier(.6,.05,.3,1) forwards',
        rise: 'rise .18s ease-out',
        slidein: 'slidein .2s ease-out',
      },
    },
  },
  plugins: [],
};
