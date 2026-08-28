# Visual Redesign — Design

## Problem

The app's current visual design (`frontend/src/styles/index.css`, ported as-is in the architecture rewrite) reads as generic and templated: an off-the-shelf indigo-on-white SaaS look with no point of view, no visual hierarchy that helps a reader parse dense data (skill gaps, market demand, competency growth, a multi-week learning path), and a set of pages that feel like they accumulated over several separate passes rather than one coherent system — because they did. For a tool whose stated purpose is to support a research-paper submission, it needs to look and read like a credible analytical instrument, not a hackathon demo.

## Goals

1. A single, coherent visual system — one palette, one type system, one set of component patterns — applied consistently across every page.
2. An "editorial/research-instrument" direction: serif display type for headings and data numerals, a warm paper-toned surface, restrained-but-real color used functionally (status, priority, verification), footnote-style evidence citations, syllabus-style numbered lists for sequential content (the learning path).
3. Real information-architecture improvements where the current layout itself is part of the problem — most notably: a tracked step's status (`pending`/`in_progress`/`struggling`/`completed`) becomes a scannable colored tag instead of parenthetical text buried in a heading.
4. Zero behavioral change: every component keeps exactly the interactions, data, routes, and TanStack Query wiring it has today. This is a restyle + IA pass, not a feature or architecture change.
5. Carry forward the two accessibility/layout fixes already shipped (mobile nav-row wrap, confidence-row wrap + 44px touch targets) — the new component versions must preserve that behavior under the new class names, not regress it.

## Non-goals

- No new product features, routes, or data.
- No backend changes.
- No changes to component logic, props, hooks, or TanStack Query cache behavior — only JSX markup/className and CSS change.
- Not a rebuild of the design system into a component library/theming abstraction — this is a shared stylesheet (`styles/index.css`) plus consistent class-name conventions, matching how the codebase already works. No CSS-in-JS, no new styling dependency.

## Design system

**Approved via iterative mockup review** (`.superpowers/brainstorm/1760-1787894069/content/results-page-v2-5.html` — kept for reference, not shipped).

### Palette

```css
--paper: #fbf5ea;        /* page background */
--paper-line: #e8dcc4;   /* hairline rules/borders */
--panel: #ffffff;        /* card/panel background */
--ink: #241d12;          /* primary text */
--ink-soft: #6e6248;     /* secondary text */
--accent: #d15633;       /* primary accent — terracotta */
--accent-soft: #f0b787;
--accent-tint: #fbe4d6;
--gold: #d3a02a;          /* secondary accent */
--gold-tint: #faf0d4;
--good: #3a8a5c;          /* success / completed / pass */
--good-tint: #e2f2e7;
--warn: #d3a02a;          /* struggling / borderline — reuses gold */
--warn-tint: #faf0d4;
--danger: #b23a2e;        /* fail / error — new token, not in the mockups */
--danger-tint: #fbe0dc;
```

`--danger` is a new addition for this pass (error boxes, failed verification) — the mockups only needed pass/warn bands. Derived from `--accent` shifted darker/desaturated so it reads as "error" without clashing with the accent.

### Type

- **Fraunces** (variable, opsz 9–144) — display serif: page titles, section titles, numerals (rank numbers, syllabus badges, score numbers).
- **Source Serif 4**, italic — pull-quotes / resume-review "overall impression" text only.
- **Inter** — all UI text: labels, body copy, buttons, form inputs, meta text.
- **IBM Plex Mono** — kickers, section labels (uppercase, letter-spaced), scores/percentages, footnote markers, week/status chips.

Load via Google Fonts `<link>` in `index.html` (already the pattern used today for Inter/Outfit — swapping the font list, not the loading mechanism):
```html
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### Component patterns (new CSS classes in `styles/index.css`)

- `.kicker` — solid-accent uppercase mono pill (small label above a title, e.g. "CAREER READINESS REPORT").
- `.ed-badge` — solid-color pill with a leading checkmark (e.g. "Verified").
- `.ed-panel` — white rounded panel (14–16px radius), soft shadow (`0 2px 10px rgba(36,29,18,0.05)`), replaces the old `.panel`/`.card` flat-bordered look.
- `.ed-rank-row` — numbered row (accent-colored serif numeral, label, optional footnote-marker superscript, a gradient-free two-stop progress bar, a mono value) — used for skill gaps and market demand lists.
- `.ed-syl-row` — syllabus-style row: solid-accent circular numbered badge, Fraunces title, Inter description, mono chip (e.g. week count). Used for the learning path and tracker steps.
- `.ed-scorecard` / `.ed-score-cell` — tinted tile with a colored bottom border and a large serif number, used for the FGCR rubric.
- `.ed-pullquote` — italic serif blockquote with a left accent/gold gradient bar and a mono citation line.
- `.status-tag` — small colored pill for a tracked step's status (`pending`=neutral gray, `in_progress`=accent tint, `struggling`=danger tint, `completed`=good tint) — this is the concrete IA fix from Goal 3.

All existing interactive elements (buttons, inputs, links) get reskinned within the existing `.primary-button`/`.secondary-button`/`.ghost`/`.input-field` class names — same class names, new visual treatment — so JSX markup for those elements does not need to change, only the CSS rules.

## Per-page treatment

No routes, hooks, or component props change. Only JSX structure/classNames (where a new pattern like `.ed-syl-row` replaces old markup) and `styles/index.css` change.

- **LoginPage** — same form fields, same toggle logic. Adds a `.kicker` + Fraunces headline framing the tool above the form; form moves into an `.ed-panel`.
- **GeneratePage / step chips** — the `.steps`/`.step-chip` row becomes a mono-uppercase numbered edition strip (`01 PROFILE — 02 TARGET ROLE — 03 ANALYSIS — 04 LEARNING PATH`) with an accent underline on the active step and a checkmark on completed ones. Same `step` state machine, same 4 steps.
- **ProfileForm** — wrapped in `.ed-panel`; textarea/buttons keep their existing behavior, restyled.
- **RolePicker** — `.role-grid`/`.role-card` restyled as index cards (bordered, Fraunces role name, `.ed-panel`-style selected state) — same click-to-select behavior.
- **AgentTerminal** — keeps the fake-log "AI at work" metaphor (still IBM Plex Mono), recolored from neon-green-on-black to the palette's ink/accent tones — reads as "typesetting your report" rather than a generic hacker console. Same log-line timing logic, unchanged.
- **Results** — the page already validated in mockups: `.kicker`+badge header, Fraunces title, `.ed-pullquote` for the resume review, `.ed-rank-row` lists for gaps/demand (with footnote markers), `.ed-scorecard` for FGCR, `.ed-syl-row` list for the learning path, footnote block at the bottom for evidence posting IDs.
- **PathGraph** — the ReactFlow node/edge styling (currently hardcoded dark-mode colors unrelated to the rest of the app) gets recolored to the palette so it doesn't look like a dropped-in widget from a different app; ReactFlow's own chrome (controls, background dots) stays functionally identical.
- **TrackerPage** — journey header becomes a Fraunces "volume" title; each step becomes an `.ed-syl-row` with a `.status-tag` replacing the old parenthetical `(status)` text — the concrete IA improvement from Goal 3.
- **CompetencyChart** — same SVG line/point structure, recolored (accent line/points instead of the old flat blue), panel wrapper restyled.
- **StepTracker** — confidence rating becomes a pill row using `.status-tag`-adjacent styling with a filled accent state for the selected rating; timer readout becomes a small mono chip; GitHub evidence becomes a small tagged chip. The existing `.confidence-row`/`.confidence-btn` flex-wrap + 44px-touch-target fix is preserved under whatever class names the new pill treatment uses — this is a hard requirement, not optional, since it's a previously-fixed accessibility bug.
- **GithubConnect** — wrapped in `.ed-panel`, restyled inputs/button.
- **RepoAnalysisPage** — analyzed-repo history list restyled as a small mono citation index; chat bubbles: user message solid-accent, assistant message tinted `.ed-panel`; code blocks in mono on a paper-tint background instead of the old generic dark/light split.

## Testing impact

Existing component tests assert primarily on text content, ARIA roles, and a small number of class-name checks (notably `StepTracker.test.tsx`'s `toHaveClass('confidence-btn')`). Any test asserting on a class name that this pass renames must be updated in the same task that renames it — text/role-based assertions should be unaffected since no copy or interaction changes. No new test files are needed for this pass (no new logic); existing suites must stay green throughout.

## Non-goals confirmed by omission

Layout/IA changes are scoped to what's listed above. Anything not mentioned (routing, data shape, wizard step count, auth flow, GitHub-analyzed-repo memory, quiz mechanics) is unchanged.
