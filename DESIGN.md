---
name: MedVault AI — Anatomical Plate
description: Cool lab grey with one ultramarine ink, after anatomical plates printed in a single colour; condensed headlines, monospace annotations, trace red reserved for danger.
colors:
  paper: "#DEE0E4"
  sheet: "#F4F5F6"
  ink: "#111317"
  pen: "#1F35C6"
  trace: "#BE1E30"
  landing-canvas: "#B4B7BD"
typography:
  ui: "Archivo (variable width 62–125; body at 100, headlines condensed at 72%)"
  labels: "IBM Plex Mono (annotations, codes, record tags)"
rounded:
  tag: "4px"
  control: "8px"
  panel: "14px"
---

# MedVault AI design system

> Revised: the landing page and app now share an anatomical-plate look. Gray's Anatomy (1918, public domain) engravings recoloured to ultramarine ink sit on a cool grey canvas, with condensed Archivo headlines and IBM Plex Mono annotations. The vitals strip keeps its graph paper, now in faint ink instead of ECG pink.

## Idea

The look comes from printed anatomical plates: one ultramarine ink on grey paper. Engravings of the heart and torso carry the landing page, where tiny monospace annotations label them like a lab specimen and a blue ink blob grows as you scroll. Inside the app the same palette stays quiet: grey paper, white panels, hairline rules, and ultramarine only for actions and citations. Graph paper sits behind each patient's vitals strip, where heart rate and blood pressure are plotted from their recorded visits.

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
