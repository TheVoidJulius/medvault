---
name: MedVault AI — Chart Paper
description: Clinical workspace built from ward materials (ECG chart paper, graphite case-sheet ink, the blue ballpoint prescriptions are signed with), with trace red reserved for danger.
colors:
  paper: "#F5F6F4"
  sheet: "#FFFFFF"
  ink: "#141A1F"
  pen: "#2340C8"
  trace: "#C42032"
  grid: "#ECB2AC"
  ok: "#17704C"
  warn: "#965600"
  rail: "#141A1F"
typography:
  ui: "Schibsted Grotesk, 400-800"
  codes: "Fragment Mono (MRNs, ICD-10 codes, record tags, vitals only)"
rounded:
  tag: "4px"
  control: "8px"
  panel: "14px"
---

# MedVault AI design system

## Idea

The interface uses what Indian clinicians already work with. ECG chart paper, with its rose millimetre grid, is the one signature surface. It appears on the sign-in hero and behind each patient's vitals strip, where heart rate and blood pressure are plotted from their recorded visits. Everything else is quiet: neutral paper, graphite ink, hairline rules.

## Colour roles

| Token | Use |
|---|---|
| `paper` / `sheet` / `well` | Canvas, panels, inset fills |
| `ink`, `ink-2`, `ink-3` | Primary, secondary and muted text |
| `pen` (ballpoint blue) | Primary actions, links, citation chips, selection, focus ring |
| `trace` (ECG red) | Allergies, out-of-range labs, emergency visits, errors. Never decorative |
| `ok` / `warn` | Confirmed or controlled vs. provisional status. Always paired with a text label |
| `grid` | ECG paper lines only |
| `--series-1..4` | Visit-type mix chart. Validated for colour-blind separation in both themes; colour follows the visit type, not its rank |

All tokens are RGB triplets in `frontend/src/index.css` with a complete dark set under `[data-theme='dark']`.

## Type

One family, Schibsted Grotesk, in sentence case throughout. Page titles are 28–32px extra-bold with tight tracking; panel titles are 15px bold; body text is 14px. Fragment Mono appears only where the content is literally a code (MRN, ICD-10, `V-12`, `LAB-88`). Tables and definition lists use tabular figures.

## Shape and depth

Radius encodes hierarchy: 4px on tags and citation chips, 8px on controls, 14px on panels. Panels are flat with 1px rules. Only floating layers (dialogs, the citation inspector, the command palette, tooltips) cast a shadow.

## Components

`frontend/src/components/`:
- `ui.tsx`: Button, Tag, Panel, Input, Select, Textarea, Modal, Drawer, Notice, Empty, Skeleton, Tabs, PageHeader
- `vitals.tsx`: EcgTrace (sign-in) and VitalsStrip (patient chart)
- `charts.tsx`: BarList, MonthColumns, VisitMix
- `citations.tsx`: citation chips and the source-row inspector drawer
- `CommandPalette.tsx`: ⌘K / Ctrl K / `/` patient and command search

## Rules

- AI output always shows its receipt: how many citations matched stored rows, the grounding score, and the provider.
- Every AI statement can be flagged for review, and every citation opens the stored row it points to.
- Allergies stay visible on every chart tab.
- Copy is plain and specific: "Register patient", "Save visit", "Nothing in the record matches".
- Motion is limited to the ECG trace drawing once on sign-in and to transitions that answer an action (dialogs, drawer). Reduced-motion is respected.
