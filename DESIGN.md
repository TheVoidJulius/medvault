---
name: MedVault AI — Burgundy Clinical Design System
description: Editorial healthcare record system pairing deep burgundy identity with warm ivory clinical surfaces and semantic clinical status clarity.
colors:
  primary-brand: "#380F17"
  primary-interaction: "#8F0B13"
  critical-accent: "#DC2011"
  warm-ivory: "#EFDFC5"
  deep-charcoal: "#252B2B"
  slate-grey: "#4C4F54"
  white: "#FFFFFF"
  warm-background: "#FAF8F5"
  light-border: "#E7E1DA"
  dark-background: "#161415"
  dark-surface: "#1E1B1C"
  dark-elevated: "#272224"
  dark-border: "#3B3133"
  status-stable: "#2F6B48"
  status-warning: "#A16207"
typography:
  display:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: "6px"
  md: "10px"
  lg: "12px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary-interaction}"
    textColor: "{colors.white}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-brand:
    backgroundColor: "{colors.primary-brand}"
    textColor: "{colors.warm-ivory}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  card-clinical:
    backgroundColor: "{colors.white}"
    textColor: "{colors.deep-charcoal}"
    rounded: "{rounded.lg}"
    padding: "20px"
---

# Design System: MedVault AI (Burgundy Clinical)

## Overview

**Creative North Star: "The Editorial Clinical Folio"**

MedVault AI treats patient medical records with the precision of an authoritative clinical monograph. Deep burgundy (`#380F17`) anchors institutional navigation and identity, crimson (`#8F0B13`) guides deliberate clinician actions, and warm alabaster (`#FAF8F5`) paired with ivory (`#EFDFC5`) reduces harsh glare during extended chart review.

We reject generic blue-and-teal AI dashboard tropes, heavy drop shadows, neon gradients, and decorative glassmorphism. Surfaces rely on crisp 1px borders (`#E7E1DA` in light mode, `#3B3133` in dark mode) and clear typographic weight steps.

## Colors

### Primary & Brand
- **Deep Burgundy** (`#380F17`): Sidebar navigation shell, active brand identity, primary table headers, and dark editorial panels.
- **Clinical Crimson** (`#8F0B13`): Primary CTA buttons, active tab indicators, focus rings, text selection, and interactive citation links.
- **Critical Red** (`#DC2011`): Life-threatening allergies, abnormal critical labs, error banners, and destructive confirmation actions.

### Accents & Neutrals
- **Warm Ivory** (`#EFDFC5`): Highlighted AI synthesis callouts, citation verification containers, and warm editorial emphasis on dark burgundy backgrounds.
- **Deep Charcoal** (`#252B2B`): High-contrast primary body text and data values on light surfaces.
- **Slate Grey** (`#4C4F54`): Secondary metadata, table column headers, helper captions, and muted descriptions.
- **Alabaster Canvas** (`#FAF8F5`), **Pure White** (`#FFFFFF`), and **Warm Sandstone Border** (`#E7E1DA`): Layered light-mode surfaces.
- **Obsidian Wine Canvas** (`#161415`), **Espresso Surface** (`#1E1B1C`), and **Muted Garnet Border** (`#3B3133`): Cohesive dark-mode surfaces preserving brand identity.

### Named Rules
**The Clinical Semantics Rule.** Never reuse `#DC2011` (critical red) for ordinary buttons or decorative badges. Reserve `#DC2011` exclusively for clinical alerts, abnormal/critical lab flags, errors, and destructive actions. Keep confirmed/normal clinical status indicators (`#2F6B48` forest green, `#A16207` clinical amber) distinct from brand burgundy.

## Typography

**Display Font:** `Newsreader` (serif) for page titles and patient record headers.
**Body Font:** `IBM Plex Sans` for dense clinical tables, form controls, and SOAP notes.
**Mono / Tabular Font:** `JetBrains Mono` with `font-variant-numeric: tabular-nums` for MRNs, ICD-10 codes, timestamps, vital signs, and record tags (`[V-1]`, `[SYM-2]`).

## Layout

- **Desktop:** Persistent `260px` Deep Burgundy (`#380F17`) navigation sidebar alongside a fluid workspace capped at `1280px` (`max-w-7xl`) on Alabaster Canvas (`#FAF8F5`).
- **Mobile & Tablet (`< 1024px`):** Sidebar collapses cleanly into an accessible slide-over navigation drawer toggled from the top header bar.
- **Breadcrumbs & Density:** Top bar displays hierarchical breadcrumbs (`Workspace / Section / Patient`) plus theme switcher and primary actions.

## Elevation & Depth

**The Flat-By-Default Rule.** Clinical record cards and tables use 1px structural borders (`#E7E1DA` / `#3B3133`) with zero ambient shadow. Shadows appear exclusively on floating overlays (`Modal` dialogs and the Citation Inspector Drawer).

## Shapes

- **Cards & Panels:** `12px` radius (`rounded-xl`).
- **Inputs, Buttons & Citation Tags:** `8px`–`10px` radius (`rounded-lg`).
- **Status Pills:** `9999px` full pill strictly for compact metadata badges.

## Components

Reusable primitives in `frontend/src/components/ui.tsx` govern `Button`, `Badge`, `Card`, `Input`, `Select`, `Textarea`, `Modal`, `EmptyState`, `SkeletonBlock`, and `AlertBanner`. Every control ships with consistent hover, `:focus-visible` ring (`2px solid #8F0B13`), disabled, loading, and validation error states.

## Do's and Don'ts

- **Do** distinguish AI-synthesized output inside Warm Ivory (`#EFDFC5`) and Deep Burgundy (`#380F17`) containers from plain factual relational cards (`#FFFFFF`).
- **Do** preserve `tabular-nums` on every numeric measurement, date, and identifier.
- **Don't** introduce unrelated blue, purple, teal, or neon gradients anywhere in the UI.
- **Don't** replace real clinical labels or empty states with placeholder numbers.
