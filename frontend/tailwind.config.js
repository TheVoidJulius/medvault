/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        burgundy: "#380F17",
        crimson: "#8F0B13",
        critical: "#DC2011",
        ivory: "#EFDFC5",
        charcoal: "#252B2B",
        "slate-grey": "#4C4F54",
        alabaster: "#FAF8F5",
        sandstone: "#E7E1DA",
        canvas: "var(--bg-canvas)",
        surface: "var(--bg-surface)",
        "surface-muted": "var(--bg-surface-muted)",
        "surface-ivory": "var(--bg-ivory-tint)",
        "border-warm": "var(--border-subtle)",
        "ink-primary": "var(--ink-primary)",
        "ink-secondary": "var(--ink-secondary)",
        "ink-muted": "var(--ink-muted)",
      },
      fontFamily: {
        serif: ['Newsreader', 'Georgia', 'serif'],
        sans: ['IBM Plex Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
