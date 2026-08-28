# Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the entire frontend into the approved editorial/academic design system (warm paper palette, Fraunces/Inter/Source Serif/IBM Plex Mono type system, panel/rank-row/syllabus/scorecard/pullquote component patterns) and apply the one approved IA improvement — a tracked step's status becomes a colored tag instead of parenthetical text — with zero changes to routes, hooks, data, or interaction logic.

**Architecture:** One CSS-token-and-component-class rewrite (`styles/index.css` + `index.html` font links) that every existing class name still resolves against, plus targeted JSX changes only where the new visual patterns (pull-quote, numbered rank rows, syllabus rows, status tags, masthead, edition-strip step chips) require new markup. Components whose restyle is pure CSS (ProfileForm, RolePicker, GithubConnect, StepTracker, AppShell, VerifierBadge/FGCR) need no code changes at all.

**Tech Stack:** Same as the existing app — React 19, TypeScript, Vite, Vitest + React Testing Library. No new dependencies.

## Implementation note on the spec's component-pattern names

The design spec names new patterns with an `.ed-` prefix (`.ed-panel`, `.ed-rank-row`, `.ed-badge`, etc.) for discussion purposes. This plan implements the same visual patterns by restyling the app's *existing* class names in place wherever one already does the job that pattern needs (`.panel`/`.card` for the panel look, `.bar-row` extended with a `.bar-num` for the ranked-row look, `.badge` for the solid-fill badge, `.fgcr-card` for the tinted scorecard tile) and only introduces new class names where no existing one fits (`.kicker`, `.pullquote`, `.status-tag`, `.syllabus`/`.syl-row`/`.syl-num`/`.syl-name`/`.syl-obj`, `.repo-history`). This keeps the diff smaller and avoids maintaining two parallel class systems for the same visual result — consistent with the spec's own principle that interactive elements keep their existing class names.

One consequence: `ProfileForm.tsx`, `RolePicker.tsx`, and `GithubConnect.tsx` — all three named in the spec's per-page list — need **zero code changes**. Each already renders inside `.panel`, and their inputs/buttons already use `.input-field`/`.primary`/`.ghost`/`.primary-button`, all of which are restyled by Task 1's CSS alone. `StepTracker.tsx` is the same case for its confidence buttons (Task 1 restyles `.confidence-btn`/`.confidence-btn.active` in place, deliberately keeping the class name unchanged since `StepTracker.test.tsx` asserts on it). No task below touches these four files.

## Global Constraints

- Zero behavioral change: no route, hook, prop, TanStack Query, or data-shape changes anywhere in this plan — only JSX markup/className and CSS.
- Every existing passing test must still pass; a task that changes a class name a test asserts on must update that test in the same task (only `StepTracker.test.tsx`'s `toHaveClass('confidence-btn')` is at risk, and this plan keeps `.confidence-row`/`.confidence-btn` unchanged specifically to avoid touching it).
- The mobile nav-row (`.app-nav`) and confidence-row (`.confidence-row`/`.confidence-btn`, including its 44px touch target) CSS rules are NOT modified by this plan — they must keep working unchanged.
- No new npm dependencies. Fonts load via the existing Google Fonts `<link>` pattern in `index.html`.
- Every task must leave `npm run typecheck`, `npm run test`, and `npm run build` passing.

---

### Task 1: Design tokens, fonts, and global component CSS

**Files:**
- Modify: `frontend/index.html` (font `<link>`)
- Modify: `frontend/src/styles/index.css` (full rewrite)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: every CSS custom property (`--bg-main`, `--panel-bg`, `--panel-border`, `--text-main`, `--text-muted`, `--primary`, `--primary-hover`, `--primary-light`, `--secondary`, `--success`, `--success-light`, `--warning`, `--warning-light`, `--danger`, `--danger-light`, `--shadow-sm/md/lg/hover`) and every class name later tasks rely on: `.panel`/`.card`, `.primary-button`/`.primary`, `.secondary-button`/`.ghost`, `.input-field`, `.tag`/`.tag.good`/`.tag.level`, `.error-box`, `.note`, `.two-col`, `.steps`/`.step-chip`, `.bar-row`/`.bar-num`/`.bar-label`/`.bar-track`/`.bar-fill`/`.bar-value`, `.weeks`, `.milestone`, `.resource`, `.fgcr`/`.fgcr-card`/`.score`/`.dim`, `.badge`/`.badge.pass`/`.badge.fail`, `.role-grid`/`.role-card`, `.app-nav`, `.confidence-row`/`.confidence-btn` (unchanged), `.kicker`, `.pullquote`, `.status-tag` (+ 4 status variants), `.syllabus`/`.syl-row`/`.syl-num`/`.syl-name`/`.syl-obj`, `.repo-history`. Same class names as before for everything that existed; new classes are additive.

This task has no unit test of its own (it's a stylesheet) — verification is `npm run build` succeeding and a visual check deferred to Task 8.

- [ ] **Step 1: Swap the Google Fonts link**

In `frontend/index.html`, replace:
```html
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```
with:
```html
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- [ ] **Step 2: Replace `frontend/src/styles/index.css` in full**

```css
:root {
  /* Editorial / research-instrument palette */
  --bg-main: #fbf5ea;
  --panel-bg: #ffffff;
  --panel-border: #e8dcc4;

  --text-main: #241d12;
  --text-muted: #6e6248;

  --primary: #d15633; /* terracotta accent */
  --primary-hover: #b8461f;
  --primary-light: #fbe4d6;

  --secondary: #d3a02a; /* gold */

  --success: #3a8a5c;
  --success-light: #e2f2e7;
  --warning: #d3a02a;
  --warning-light: #faf0d4;
  --danger: #b23a2e;
  --danger-light: #fbe0dc;

  --shadow-sm: 0 1px 2px 0 rgba(36, 29, 18, 0.06);
  --shadow-md: 0 4px 12px -2px rgba(36, 29, 18, 0.08);
  --shadow-lg: 0 4px 16px rgba(36, 29, 18, 0.06);
  --shadow-hover: 0 10px 24px -6px rgba(36, 29, 18, 0.12);

  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color-scheme: light;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: var(--bg-main);
  color: var(--text-main);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#root {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px 80px;
  animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeUp {
  0% { opacity: 0; transform: translateY(15px); }
  100% { opacity: 1; transform: translateY(0); }
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-main);
}

/* Typography Enhancements */
.app-header {
  text-align: center;
  margin: 40px 0 60px;
}

.app-header h1 {
  font-size: 3.2rem;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--primary);
  display: inline-block;
  letter-spacing: -0.03em;
}

.app-header p {
  color: var(--text-muted);
  font-size: 1.15rem;
  font-weight: 500;
}

/* Solid panels */
.panel, .card {
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-lg);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.panel:hover, .card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}

.panel h2, .card h2 {
  font-size: 1.5rem;
  margin-bottom: 16px;
  color: var(--text-main);
}

.panel .hint, .card .hint {
  color: var(--text-muted);
  font-size: 1rem;
  margin-bottom: 24px;
  line-height: 1.6;
}

/* Inputs & Forms */
label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 0.95rem;
}

.input-field, textarea, input[type="text"], input[type="number"], input[type="email"], input[type="password"] {
  width: 100%;
  background: var(--bg-main);
  color: var(--text-main);
  border: 2px solid var(--panel-border);
  border-radius: 12px;
  padding: 16px 20px;
  font-size: 1rem;
  font-family: 'Inter', sans-serif;
  transition: all 0.2s ease;
}

textarea {
  min-height: 180px;
  resize: vertical;
  line-height: 1.6;
}

.input-field:focus, textarea:focus, input[type="text"]:focus, input[type="number"]:focus, input[type="email"]:focus, input[type="password"]:focus {
  outline: none;
  border-color: var(--primary);
  background: var(--panel-bg);
  box-shadow: 0 0 0 4px var(--primary-light);
}

/* Buttons */
button {
  font-family: 'Inter', sans-serif;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.primary-button, .primary {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 14px 28px;
  font-size: 1.05rem;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(209, 86, 51, 0.28);
}

.primary-button:hover:not(:disabled), .primary:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(209, 86, 51, 0.35);
}

.primary-button:active:not(:disabled), .primary:active:not(:disabled) {
  transform: translateY(0);
}

.primary-button:disabled, .primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.secondary-button, .ghost {
  background: var(--panel-bg);
  color: var(--text-main);
  border: 2px solid var(--panel-border);
  border-radius: 12px;
  padding: 12px 24px;
  font-size: 1rem;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.secondary-button:hover, .secondary-button.active, .ghost:hover {
  background: var(--bg-main);
  border-color: #d8c9a8;
}

.secondary-button.active {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
  box-shadow: none;
}

/* Step strip (Generate wizard) */
.steps {
  display: flex;
  gap: 0;
  justify-content: center;
  margin-bottom: 50px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--panel-border);
}

.step-chip {
  padding: 12px 20px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s ease;
}

.step-chip.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.step-chip.done {
  color: var(--success);
}

/* Tags */
.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  margin: 4px 6px 4px 0;
  border: 1px solid var(--panel-border);
  background: var(--bg-main);
  font-family: 'Inter', sans-serif;
  color: var(--text-main);
}

.tag.good {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-light);
}

.tag.level {
  color: var(--primary);
  margin-left: 8px;
  font-size: 0.8rem;
  background: transparent;
  border: none;
  padding: 0;
}

/* Rank rows (skill gaps / market demand) */
.bar-row {
  display: grid;
  grid-template-columns: 28px 200px 1fr 60px;
  gap: 16px;
  align-items: center;
  margin: 14px 0;
  font-size: 1rem;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--panel-border);
}

.bar-num {
  font-family: 'Fraunces', serif;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--primary);
}

.bar-label {
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

.bar-track {
  background: var(--bg-main);
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
  border: 1px solid var(--panel-border);
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--secondary), var(--primary));
  transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
}

.bar-fill.gap {
  background: var(--primary);
}

.bar-value {
  color: var(--text-muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 0.85rem;
}

/* Syllabus rows (learning path steps, tracker steps) */
.syllabus {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.syl-row {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  gap: 18px;
  align-items: start;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  padding: 18px 22px;
  box-shadow: var(--shadow-sm);
}

.syl-row.done { border-left: 4px solid var(--success); }
.syl-row.warn { border-left: 4px solid var(--danger); }

.syl-num {
  font-family: 'Fraunces', serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
  background: var(--primary);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.syl-name {
  font-family: 'Fraunces', serif;
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.syl-obj {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

/* Status tag (tracker step status — replaces parenthetical text) */
.status-tag {
  display: inline-block;
  font-family: 'Inter', sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: capitalize;
  padding: 4px 12px;
  border-radius: 999px;
  margin-left: 10px;
  vertical-align: middle;
}

.status-tag.status-pending { background: var(--panel-border); color: var(--text-muted); }
.status-tag.status-in_progress { background: var(--primary-light); color: var(--primary-hover); }
.status-tag.status-struggling { background: var(--danger-light); color: var(--danger); }
.status-tag.status-completed { background: var(--success-light); color: var(--success); }

.weeks {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 600;
  background: var(--primary-light);
  padding: 6px 12px;
  border-radius: 999px;
  white-space: nowrap;
}

.milestone {
  color: #8a4a1f;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--warning-light);
  padding: 12px 16px;
  border-radius: 10px;
  border-left: 4px solid var(--warning);
  font-size: 0.9rem;
  margin-top: 10px;
}

.resource {
  display: inline-flex;
  align-items: center;
  color: var(--primary-hover);
  font-size: 0.95rem;
  font-weight: 600;
  text-decoration: none;
  background: var(--primary-light);
  padding: 10px 16px;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.resource:hover {
  background: #f3c9b0;
  transform: translateY(-2px);
}

/* Pull-quote (resume review overall impression) */
.pullquote {
  background: var(--panel-bg);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  padding: 24px 28px;
  margin: 8px 0 20px;
  border-left: 4px solid var(--primary);
}

.pullquote p {
  font-family: 'Source Serif 4', serif;
  font-style: italic;
  font-size: 1.2rem;
  line-height: 1.5;
  color: var(--text-main);
  margin: 0;
}

.pullquote cite {
  display: block;
  font-family: 'IBM Plex Mono', monospace;
  font-style: normal;
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 12px;
}

/* Kicker pill (Login masthead) */
.kicker {
  display: inline-block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #fff;
  background: var(--primary);
  padding: 6px 14px;
  border-radius: 999px;
  margin-bottom: 16px;
}

/* Select Dropdown */
select {
  appearance: none;
  background: var(--bg-main) url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23241d12' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e") no-repeat right 1rem center/1em;
  color: var(--text-main);
  border: 2px solid var(--panel-border);
  padding: 12px 40px 12px 16px;
  border-radius: 12px;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

select:hover {
  border-color: #d8c9a8;
}

select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

/* Error/Alert */
.error-box {
  background: var(--danger-light);
  border: 1px solid rgba(178, 58, 46, 0.2);
  color: #8a2a1f;
  border-radius: 14px;
  padding: 16px 20px;
  margin: 0 0 24px;
  font-weight: 500;
}

.note {
  background: var(--warning-light);
  border: 1px solid rgba(211, 160, 42, 0.25);
  color: #8a4a1f;
  border-radius: 14px;
  padding: 16px 20px;
  font-size: 1rem;
  margin: 0 0 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 500;
}

/* Two Column Layout */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

@media (max-width: 850px) {
  .two-col { grid-template-columns: 1fr; gap: 16px; }
  .bar-row { grid-template-columns: 1fr; gap: 6px; margin: 14px 0; }
  .bar-num { display: none; }
  .bar-value { text-align: left; }
  .syl-row { grid-template-columns: 40px 1fr; }
  .syl-row .weeks { grid-column: 2; justify-self: start; margin-top: 8px; }
}

/* Card Overrides */
.card a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.card a:hover {
  text-decoration: underline;
}

/* FGCR scorecard */
.fgcr {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin: 24px 0;
}

.fgcr-card {
  background: var(--bg-main);
  border-radius: 14px;
  padding: 24px 20px;
  text-align: center;
  border-bottom: 3px solid var(--panel-border);
  transition: transform 0.2s ease;
}

.fgcr-card:has(.score.good) { background: var(--success-light); border-bottom-color: var(--success); }
.fgcr-card:has(.score.warn) { background: var(--warning-light); border-bottom-color: var(--warning); }
.fgcr-card:has(.score.bad) { background: var(--danger-light); border-bottom-color: var(--danger); }

.fgcr-card:hover {
  transform: translateY(-2px);
}

.fgcr-card .score {
  font-family: 'Fraunces', serif;
  font-size: 2.3rem;
  font-weight: 700;
  margin-bottom: 6px;
}

.fgcr-card .dim {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.score.good { color: var(--success); }
.score.warn { color: var(--warning); }
.score.bad { color: var(--danger); }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  margin-left: 16px;
  vertical-align: middle;
}

.badge.pass { background: var(--success); color: #fff; }
.badge.fail { background: var(--danger); color: #fff; }

/* Roles Grid */
.role-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.role-card {
  font-family: 'Fraunces', serif;
  background: var(--panel-bg);
  border: 2px solid var(--panel-border);
  border-radius: 14px;
  padding: 20px;
  cursor: pointer;
  text-align: left;
  color: var(--text-main);
  font-size: 1.1rem;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}
.role-card:hover {
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.role-card.selected {
  border-color: var(--primary);
  background: var(--primary-light);
  color: var(--primary-hover);
}

/* App nav (Generate Path / Tracker / GitHub Analysis / Logout) — must wrap
   instead of overflowing horizontally at narrow widths. UNCHANGED by the
   redesign — do not modify. */
.app-nav {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}

/* Confidence-rating row (StepTracker) — must wrap at narrow widths instead
   of overflowing horizontally, and each button needs a touch-friendly
   (~44px) target. UNCHANGED by the redesign — do not modify (a test asserts
   the .confidence-btn class name). Colors below are the only redesign-era
   edit: solid accent fill on the active rating instead of the old
   indigo-tint. */
.confidence-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.confidence-btn {
  padding: 10px 16px;
  min-width: 44px;
  min-height: 44px;
  border-radius: 999px;
}

.confidence-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

/* Repo-analysis "already analyzed" history */
.repo-history {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
  background: var(--bg-main);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}
.repo-history strong {
  display: block;
  font-family: 'Inter', sans-serif;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-main);
  margin-bottom: 8px;
}
.repo-history ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.repo-history a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}
.repo-history a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 3: Verify the build still succeeds and existing tests are unaffected**

Run: `cd frontend && npm run typecheck && npm run test && npm run build`
Expected: all pass. (No component JSX changed yet, so this only proves the CSS/HTML edit didn't break anything mechanically — e.g. no stray syntax error in the stylesheet.)

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/src/styles/index.css
git commit -m "feat(frontend): editorial design system — tokens, fonts, global component CSS"
```

---

### Task 2: LoginPage masthead

**Files:**
- Modify: `frontend/src/routes/LoginPage.tsx` (full replacement)

**Interfaces:**
- Consumes: `.kicker` class (Task 1).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Replace `frontend/src/routes/LoginPage.tsx` in full**

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLogin, useRegister } from '../api/auth'

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()

  const login = useLogin()
  const register = useRegister()
  const active = isLogin ? login : register

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    active.mutate({ email, password }, {
      onSuccess: () => navigate('/generate', { replace: true }),
    })
  }

  return (
    <div style={{ maxWidth: 440, margin: '3rem auto 2rem', textAlign: 'center' }}>
      <span className="kicker">Autonomous Career Advisor</span>
      <h1 style={{ fontSize: '2.2rem', marginBottom: '0.5rem' }}>
        {isLogin ? 'Welcome back.' : 'Begin your assessment.'}
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Multi-agent skill gap analysis &amp; verified learning path generation.
      </p>

      <div className="card" style={{ textAlign: 'left' }}>
        <h2>{isLogin ? 'Login' : 'Register'}</h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-field"
          />
          <div style={{ position: 'relative' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="input-field"
              style={{ paddingRight: '40px' }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              title={showPassword ? 'Hide password' : 'Show password'}
              style={{
                position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', padding: 0, boxShadow: 'none',
              }}
            >
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
          {active.isError && <div className="error-box">{active.error.message}</div>}
          <button type="submit" className="primary-button">
            {isLogin ? 'Login' : 'Register'}
          </button>
        </form>
        <p style={{ marginTop: '1rem', textAlign: 'center' }}>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <a href="#" onClick={(e) => { e.preventDefault(); setIsLogin(!isLogin) }}>
            {isLogin ? 'Register here' : 'Login here'}
          </a>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run the existing LoginPage tests to confirm they still pass unmodified**

Run: `cd frontend && npm run test -- LoginPage.test.tsx`
Expected: 3 tests PASS (no test file changes needed — it queries by placeholder/role/text, none of which changed).

- [ ] **Step 3: Full verification**

Run: `npm run typecheck && npm run build`
Expected: both succeed.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/LoginPage.tsx
git commit -m "feat(frontend): restyle LoginPage as an editorial masthead"
```

---

### Task 3: Generate wizard edition strip

**Files:**
- Modify: `frontend/src/routes/GeneratePage.tsx`

**Interfaces:**
- Consumes: `.step-chip` restyled CSS (Task 1).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Replace `frontend/src/routes/GeneratePage.tsx` in full**

```tsx
import { useState } from 'react'
import { useAdvise, useRoles } from '../api/advise'
import type { AdvisorResult } from '../api/types'
import ProfileForm, { type ProfileFormValues } from '../components/ProfileForm'
import RolePicker from '../components/RolePicker'
import AgentTerminal from '../components/AgentTerminal'
import Results from '../components/Results'

const STEPS = ['Profile', 'Target role', 'Analysis', 'Learning path']

export default function GeneratePage() {
  const [step, setStep] = useState(0)
  const [profileInput, setProfileInput] = useState<ProfileFormValues | null>(null)
  const [role, setRole] = useState('')
  const [result, setResult] = useState<AdvisorResult | null>(null)
  const [error, setError] = useState('')

  const { data: rolesData, error: rolesError } = useRoles()
  const advise = useAdvise()

  const runAdvisor = async () => {
    if (!profileInput) return
    setStep(2)
    setError('')
    try {
      const res = await advise.mutateAsync({ ...profileInput, target_role: role })
      setResult(res)
      setStep(3)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStep(1)
    }
  }

  const restart = () => {
    setStep(0)
    setProfileInput(null)
    setRole('')
    setResult(null)
    setError('')
  }

  return (
    <>
      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`step-chip ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
            {String(i + 1).padStart(2, '0')} {i < step ? '✓ ' : ''}{s}
          </span>
        ))}
      </div>

      {error && <div className="error-box">Advisor failed: {error}</div>}

      {step === 0 && (
        <ProfileForm onSubmit={(input) => { setProfileInput(input); setStep(1) }} />
      )}

      {step === 1 && (
        <RolePicker
          roles={rolesData?.roles ?? []}
          selected={role}
          onSelect={setRole}
          onBack={() => setStep(0)}
          onAnalyse={runAdvisor}
          loadError={rolesError instanceof Error ? rolesError.message : ''}
        />
      )}

      {step === 2 && <AgentTerminal role={role} />}

      {step === 3 && result && <Results result={result} onRestart={restart} />}
    </>
  )
}
```

(The only change from the current file is the step-chip label line, which now prefixes a zero-padded step number — `"01 Profile"`, `"02 ✓ Target role"`, etc. — matching the edition-strip look. `ProfileForm.tsx` and `RolePicker.tsx` need no changes: their restyle comes entirely from Task 1's CSS.)

- [ ] **Step 2: Verify ProfileForm and RolePicker tests still pass with no code changes**

Run: `cd frontend && npm run test -- ProfileForm.test.tsx RolePicker.test.tsx`
Expected: 4 tests PASS.

- [ ] **Step 3: Full verification**

Run: `npm run typecheck && npm run build`
Expected: both succeed.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/GeneratePage.tsx
git commit -m "feat(frontend): numbered edition-strip step indicator for the Generate wizard"
```

---

### Task 4: Results page — pull-quote, ranked lists, syllabus-style path

**Files:**
- Modify: `frontend/src/components/Results.tsx` (full replacement)

**Interfaces:**
- Consumes: `.pullquote`, `.bar-num`, `.syllabus`/`.syl-row`/`.syl-num`/`.syl-name`/`.syl-obj`, `.weeks`, `.milestone`, `.badge.pass/.fail` (solid fill, CSS-only, no JSX change needed here), `.fgcr-card` tinted-via-`:has()` (CSS-only, no JSX change needed here) — all from Task 1.
- Produces: `Bar` now accepts an optional `rank?: number` prop (internal to this file only, not exported).

- [ ] **Step 1: Replace `frontend/src/components/Results.tsx` in full**

```tsx
import PathGraph from './PathGraph'
import type {
  AdvisorResult, FGCRCritique, GapReport, LearningPath, MarketDemandProfile,
  ResumeReviewResult, StudentProfile,
} from '../api/types'

function Bar({ label, value, max = 1, gap = false, right, rank }: {
  label: string; value: number; max?: number; gap?: boolean; right?: string; rank?: number
}) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div className="bar-row">
      {rank != null && <span className="bar-num">{rank}</span>}
      <span className="bar-label" title={label}>{label}</span>
      <div className="bar-track">
        <div className={`bar-fill ${gap ? 'gap' : ''}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-value">{right ?? `${pct}%`}</span>
    </div>
  )
}

function DemandChart({ demand }: { demand: MarketDemandProfile }) {
  const top = demand.skills.slice(0, 12)
  return (
    <div className="panel">
      <h2>Market demand — {demand.target_role}</h2>
      <p className="hint">
        From {demand.postings_analysed} job postings. Every bar is backed by real
        posting IDs (hover a skill to see them) — nothing here is model guesswork.
      </p>
      {top.map((s, i) => (
        <div key={s.skill_id} title={`Evidence: ${s.posting_ids.join(', ')}`}>
          <Bar rank={i + 1} label={s.name} value={s.share} right={`${Math.round(s.share * 100)}%`} />
        </div>
      ))}
    </div>
  )
}

function ProfileView({ profile }: { profile: StudentProfile }) {
  return (
    <div className="panel">
      <h2>Your extracted profile</h2>
      <p className="hint">{profile.skills.length} skills mapped onto the taxonomy.</p>
      <div className="skill-list">
        {profile.skills.map((s) => (
          <span key={s.skill_id} className="tag" title={s.evidence}>
            {s.name} <span className="tag level">{s.level} (Depth: {s.depth_score}/10)</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function ResumeReviewView({ review }: { review: ResumeReviewResult | null }) {
  if (!review) return null
  return (
    <div className="panel">
      <h2>Resume Feedback (AI Agent)</h2>
      <div className="pullquote">
        <p>{review.overall_impression}</p>
        <cite>Resume Review Agent</cite>
      </div>
      <div className="two-col">
        <div>
          <h3 style={{ color: 'var(--success)', marginTop: 0 }}>Strengths</h3>
          <ul>{review.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div>
          <h3 style={{ color: 'var(--warning)', marginTop: 0 }}>Areas to Improve</h3>
          <ul>{review.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      <div style={{ marginTop: '1rem', fontStyle: 'italic', fontSize: '0.9rem' }}>
        <strong>Formatting Feedback:</strong> {review.formatting_feedback}
      </div>
    </div>
  )
}

function GapView({ report }: { report: GapReport }) {
  const maxP = Math.max(...report.gaps.map((g) => g.priority), 0.001)
  return (
    <div className="panel">
      <h2>Skill gaps (priority = demand × gap)</h2>
      <p className="hint">Computed deterministically over the taxonomy — auditable, not LLM-guessed.</p>
      {report.gaps.slice(0, 10).map((g, i) => (
        <div key={g.skill_id} title={`${g.current_level} → ${g.required_level}`}>
          <Bar rank={i + 1} label={g.name} value={g.priority} max={maxP} gap right={g.priority.toFixed(2)} />
        </div>
      ))}
      {report.strengths.length > 0 && (
        <>
          <label>Already at market level:</label>
          <div className="skill-list">
            {report.strengths.map((s) => <span key={s} className="tag good">✓ {s}</span>)}
          </div>
        </>
      )}
    </div>
  )
}

function VerifierBadge({ critique, revisions }: { critique: FGCRCritique | null; revisions: number }) {
  if (!critique) return null
  const cls = (v: number) => (v >= 4 ? 'good' : v >= 3 ? 'warn' : 'bad')
  const dims: [string, number][] = [
    ['Feasibility', critique.feasibility], ['Groundedness', critique.groundedness],
    ['Coverage', critique.coverage], ['Realism', critique.realism],
  ]
  return (
    <div className="panel">
      <h2>
        Verifier (FGCR rubric){' '}
        <span className={`badge ${critique.passed ? 'pass' : 'fail'}`}>
          {critique.passed ? '✓ verified' : '✗ issues remain'}
        </span>
      </h2>
      <p className="hint">
        An adversarial critic agent scored this path; hard rule-checks cap the LLM's
        scores. Revision loops used: {revisions}.
      </p>
      <div className="fgcr">
        {dims.map(([dim, v]) => (
          <div className="fgcr-card" key={dim}>
            <div className={`score ${cls(v)}`}>{v.toFixed(1)}</div>
            <div className="dim">{dim} / 5</div>
          </div>
        ))}
      </div>
      {critique.issues.length > 0 && (
        <ul className="hint">{critique.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
      )}
    </div>
  )
}

function PathTimeline({ path }: { path: LearningPath | null }) {
  if (!path) return null
  return (
    <div className="panel">
      <h2>Your learning path — {path.total_weeks} weeks total</h2>
      <p className="hint">{path.rationale}</p>
      <div className="syllabus">
        {path.steps.map((s) => (
          <div className="syl-row" key={s.skill_id}>
            <div className="syl-num">{s.order}</div>
            <div>
              <div className="syl-name">{s.skill_name}</div>
              <p className="syl-obj">{s.objective}</p>
              <p className="milestone">🏁 {s.milestone}</p>
              {s.resources.length > 0 && (
                <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {s.resources.map((r) => (
                    <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                      📚 {r.title} — {r.provider}{r.free ? ' (free)' : ''}
                    </a>
                  ))}
                </div>
              )}
            </div>
            <div className="weeks">{s.estimated_weeks} wk</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Results({ result, onRestart }: { result: AdvisorResult; onRestart: () => void }) {
  return (
    <>
      {result.notes.length > 0 && result.notes.map((n, i) => <div className="note" key={i}>⚠ {n}</div>)}
      <div className="two-col">
        <ProfileView profile={result.profile} />
        <GapView report={result.gap_report} />
      </div>
      <ResumeReviewView review={result.resume_review} />
      <DemandChart demand={result.demand} />
      <VerifierBadge critique={result.critique} revisions={result.revisions_used} />
      <PathGraph path={result.path} />
      <PathTimeline path={result.path} />
      <button className="ghost" onClick={onRestart}>↺ Start over</button>
    </>
  )
}
```

- [ ] **Step 2: Full verification (no `Results.test.tsx` exists, so this is typecheck/build/full-suite only)**

Run: `cd frontend && npm run typecheck && npm run test && npm run build`
Expected: all pass, no regressions.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Results.tsx
git commit -m "feat(frontend): restyle Results page — pull-quote, ranked lists, syllabus path"
```

---

### Task 5: Tracker page — status tags and syllabus-style steps

**Files:**
- Modify: `frontend/src/routes/TrackerPage.tsx` (full replacement)

**Interfaces:**
- Consumes: `.syllabus`/`.syl-row`/`.syl-num`/`.syl-name`/`.syl-obj`, `.status-tag` + 4 status variants, `.weeks`, `.milestone` (Task 1). `StepTracker` and `CompetencyChart`'s own prop signatures are unchanged — this task only changes how `TrackerPage` wraps them.
- Produces: nothing new for later tasks.

- [ ] **Step 1: Replace `frontend/src/routes/TrackerPage.tsx` in full**

```tsx
import { useState } from 'react'
import { useCompetencyHistory, useJourneys, useRecalculateJourney } from '../api/tracker'
import GithubConnect from '../components/GithubConnect'
import CompetencyChart from '../components/CompetencyChart'
import StepTracker from '../components/StepTracker'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  struggling: 'Struggling',
  completed: 'Completed',
}

export default function TrackerPage() {
  const { data: journeys, isLoading, error } = useJourneys()
  const { data: historyData } = useCompetencyHistory()
  const recalculate = useRecalculateJourney()
  const [recalculatingId, setRecalculatingId] = useState<number | null>(null)

  if (isLoading) return <div>Loading journeys...</div>
  if (error) return <div className="error-box">{error instanceof Error ? error.message : String(error)}</div>

  const skillNames: Record<string, string> = {}
  journeys?.forEach((j) => j.steps.forEach((s) => { skillNames[s.skill_id] = s.skill_name }))

  const runRecalculate = async (journeyId: number) => {
    setRecalculatingId(journeyId)
    try {
      await recalculate.mutateAsync(journeyId)
    } catch (e) {
      alert('Recalculate failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      setRecalculatingId(null)
    }
  }

  return (
    <div className="tracker">
      <GithubConnect />
      <CompetencyChart historyData={historyData ?? {}} skillNames={skillNames} />
      {journeys?.length === 0 && <div>No learning paths generated yet. Go to Generate Path!</div>}
      {journeys?.map((j) => {
        const hasStruggling = j.steps.some((s) => s.status === 'struggling')
        return (
          <div key={j.id} className="panel" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2>Target Role: {j.target_role}</h2>
                <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
              </div>
              {hasStruggling && (
                <button className="primary-button" disabled={recalculatingId === j.id}
                        onClick={() => runRecalculate(j.id)}>
                  {recalculatingId === j.id ? 'Recalculating...' : 'Recalculate Sub-Path'}
                </button>
              )}
            </div>
            <div className="syllabus">
              {j.steps.map((s) => (
                <div className={`syl-row ${s.status === 'completed' ? 'done' : s.status === 'struggling' ? 'warn' : ''}`} key={s.id}>
                  <div className="syl-num">{s.order}</div>
                  <div>
                    <div className="syl-name">
                      {s.skill_name}
                      <span className={`status-tag status-${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span>
                    </div>
                    <p className="syl-obj">{s.objective}</p>
                    <p className="milestone">🏁 {s.milestone}</p>
                    {s.resources.length > 0 && (
                      <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                        {s.resources.map((r) => (
                          <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                            📚 {r.title} — {r.provider} {r.free ? '(free)' : ''}
                          </a>
                        ))}
                      </div>
                    )}
                    <StepTracker step={s} hoursPerWeek={j.hours_per_week} />
                  </div>
                  <div className="weeks">{s.estimated_weeks} wk</div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

(`StepTracker.tsx` itself is unchanged — its restyle is CSS-only via Task 1's `.confidence-btn`/`.confidence-btn.active` rules.)

- [ ] **Step 2: Verify StepTracker's own tests still pass unmodified**

Run: `cd frontend && npm run test -- StepTracker.test.tsx`
Expected: 2 tests PASS (they render `StepTracker` in isolation, not through `TrackerPage`, so this task doesn't touch them).

- [ ] **Step 3: Full verification**

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/TrackerPage.tsx
git commit -m "feat(frontend): tracker steps as syllabus rows with a status tag"
```

---

### Task 6: Recolor decorative/canvas components (AgentTerminal, PathGraph, CompetencyChart)

**Files:**
- Modify: `frontend/src/components/AgentTerminal.tsx` (full replacement)
- Modify: `frontend/src/components/PathGraph.tsx` (full replacement)
- Modify: `frontend/src/components/CompetencyChart.tsx` (full replacement)

**Interfaces:**
- Consumes: nothing from other tasks (these three use hardcoded hex/inline styles, not shared CSS classes).
- Produces: nothing new for later tasks.

These three components render their own colors as hardcoded hex (terminal chrome, ReactFlow node/edge styles, SVG chart strokes) rather than through `styles/index.css`, so they need direct hex updates to match the new palette. Grouped into one task because each change is a mechanical hex swap with no shared review surface.

- [ ] **Step 1: Replace `frontend/src/components/AgentTerminal.tsx` in full**

```tsx
import { useEffect, useState } from 'react'

const LOGS = [
  '[System] Initializing Multi-Agent System...',
  '[ProfileAgent] Parsing user background...',
  '[ProfileAgent] Extracted skills. Mapping to taxonomy...',
  '[MarketAgent] Connecting to live job board...',
  '[MarketAgent] Analyzing recent postings for target role...',
  '[MarketAgent] Extracting core competencies and demand shares...',
  '[GapAgent] Comparing user profile vs market demand...',
  '[GapAgent] Identifying critical skill gaps...',
  '[PathAgent] Generating learning path steps...',
  '[PathAgent] Searching for relevant courses...',
  '[VerifierAgent] Evaluating path feasibility (FGCR Rubric)...',
  '[VerifierAgent] Path looks good. Finalizing results...',
]

interface LogLine {
  text: string
  time: Date
}

export default function AgentTerminal({ role }: { role: string }) {
  const [lines, setLines] = useState<LogLine[]>([])

  useEffect(() => {
    let current = 0
    const interval = setInterval(() => {
      if (current < LOGS.length) {
        const text = LOGS[current].replace('target role', role || 'target role')
        setLines((prev) => [...prev, { text, time: new Date() }])
        current++
      } else {
        setLines((prev) => {
          if (!prev.some((l) => l.text === '[System] Waiting for final LLM verification...')) {
            return [...prev, { text: '[System] Waiting for final LLM verification...', time: new Date() }]
          }
          return prev
        })
        clearInterval(interval)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [role])

  return (
    <div className="panel" style={{ padding: '0', overflow: 'hidden' }}>
      <div style={{ background: '#2a2116', padding: '8px 16px', borderBottom: '1px solid #3d3122', display: 'flex', gap: '6px' }}>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f' }}></div>
        <span style={{ marginLeft: '12px', color: '#8a7a5c', fontSize: '0.85rem', fontFamily: "'IBM Plex Mono', monospace" }}>typesetting ~ /usr/bin/advisor</span>
      </div>
      <div style={{ padding: '20px', background: '#1a140c', minHeight: '250px', fontFamily: "'IBM Plex Mono', monospace", fontSize: '0.9rem', color: '#e0a94a', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {lines.map((l, i) => (
          <div key={i} style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <span style={{ color: '#8a7a5c' }}>{l.time.toLocaleTimeString('en-GB')}</span> {l.text}
          </div>
        ))}
        {lines.length < LOGS.length && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', color: '#8a7a5c' }}>
            <div className="spinner" style={{ width: 16, height: 16, margin: 0, borderWidth: 2 }} />
            Processing...
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Replace `frontend/src/components/PathGraph.tsx` in full**

```tsx
import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import type { LearningPath } from '../api/types'

const NODE_TYPES = {}
const EDGE_TYPES = {}

export default function PathGraph({ path }: { path: LearningPath | null }) {
  const { nodes, edges } = useMemo(() => {
    if (!path || !path.steps) return { nodes: [] as Node[], edges: [] as Edge[] }

    const newNodes: Node[] = path.steps.map((step, i) => ({
      id: step.skill_id,
      position: { x: 250, y: i * 150 + 50 },
      data: {
        label: (
          <div style={{ padding: '10px', textAlign: 'center' }}>
            <strong>{step.order}. {step.skill_name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#d3a02a', marginTop: '4px' }}>
              {step.estimated_weeks} weeks
            </div>
          </div>
        ),
      },
      style: {
        background: 'rgba(36, 29, 18, 0.85)', color: '#fbf5ea', border: '1px solid #6e6248',
        borderRadius: '10px', width: 250, backdropFilter: 'blur(12px)',
      },
    }))

    const newEdges: Edge[] = []
    for (let i = 0; i < path.steps.length - 1; i++) {
      newEdges.push({
        id: `e-${path.steps[i].skill_id}-${path.steps[i + 1].skill_id}`,
        source: path.steps[i].skill_id,
        target: path.steps[i + 1].skill_id,
        animated: true,
        style: { stroke: '#d15633', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#d15633' },
      })
    }

    return { nodes: newNodes, edges: newEdges }
  }, [path])

  if (!path) return null

  return (
    <div className="panel" style={{ height: '600px', padding: 0 }}>
      <div style={{ padding: '20px', borderBottom: '1px solid #e8dcc4', background: 'var(--panel-bg)' }}>
        <h2 style={{ margin: 0 }}>Interactive Learning Path ({path.total_weeks} weeks)</h2>
        <p className="hint" style={{ margin: 0 }}>{path.rationale}</p>
      </div>
      <div style={{ width: '100%', height: 'calc(100% - 80px)' }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
          <Background color="#e8dcc4" gap={16} />
          <Controls style={{ background: '#241d12', fill: '#fbf5ea' }} />
        </ReactFlow>
      </div>
    </div>
  )
}
```

(Also fixes a pre-existing bug on this line: the original referenced `var(--panel)`, a CSS custom property that was never defined anywhere in `index.css` — only `--panel-bg` exists. Corrected to `var(--panel-bg)` since this line is being touched for the recolor anyway.)

- [ ] **Step 3: Replace `frontend/src/components/CompetencyChart.tsx` in full**

```tsx
import { useState } from 'react'
import type { CompetencyHistory } from '../api/types'

export default function CompetencyChart({ historyData, skillNames }: {
  historyData: CompetencyHistory
  skillNames: Record<string, string>
}) {
  const [selectedSkill, setSelectedSkill] = useState('')

  const skillIds = Object.keys(historyData || {})
  if (skillIds.length === 0) return null

  const activeSkill = selectedSkill || skillIds[0]
  const data = historyData[activeSkill] || []

  const width = 500
  const height = 200
  const pad = 30

  const mapY = (val: number) => height - pad - ((val - 1) / 9) * (height - 2 * pad)
  const minTime = data.length > 0 ? new Date(data[0].recorded_at).getTime() : 0
  const maxTime = data.length > 0 ? new Date(data[data.length - 1].recorded_at).getTime() : 0
  const timeRange = maxTime - minTime || 1
  const mapX = (time: number) => pad + ((time - minTime) / timeRange) * (width - 2 * pad)

  const points = data.map((d) => `${mapX(new Date(d.recorded_at).getTime())},${mapY(d.depth_score)}`).join(' ')

  return (
    <div className="panel" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Competency Growth</h2>
        <select value={activeSkill} onChange={(e) => setSelectedSkill(e.target.value)} className="input-field">
          {skillIds.map((id) => <option key={id} value={id}>{skillNames[id] || id}</option>)}
        </select>
      </div>
      {data.length > 0 && (
        <>
          <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ background: '#fbf5ea', borderRadius: '8px', marginTop: '1rem' }}>
            {[1, 5, 10].map((val) => (
              <g key={val}>
                <line x1={pad} y1={mapY(val)} x2={width - pad} y2={mapY(val)} stroke="#e8dcc4" strokeDasharray="4 4" />
                <text x={pad - 5} y={mapY(val) + 4} fontSize="10" textAnchor="end" fill="#6e6248">{val}</text>
              </g>
            ))}
            <polyline points={points} fill="none" stroke="#d15633" strokeWidth="2" />
            {data.map((d, i) => {
              const cx = mapX(new Date(d.recorded_at).getTime())
              const cy = mapY(d.depth_score)
              return (
                <g key={i}>
                  <circle cx={cx} cy={cy} r="4" fill="#d15633" />
                  <title>Depth: {d.depth_score}&#10;{d.rationale}</title>
                </g>
              )
            })}
          </svg>
          <div style={{ marginTop: '0.5rem' }} className="hint">
            Latest assessment: {data[data.length - 1].rationale}
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Verify CompetencyChart's tests still pass unmodified**

Run: `cd frontend && npm run test -- CompetencyChart.test.tsx`
Expected: 3 tests PASS (they assert text content only, not colors).

- [ ] **Step 5: Full verification**

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/AgentTerminal.tsx frontend/src/components/PathGraph.tsx frontend/src/components/CompetencyChart.tsx
git commit -m "feat(frontend): recolor AgentTerminal, PathGraph, CompetencyChart to the editorial palette"
```

---

### Task 7: RepoAnalysisPage — chat bubbles and analyzed-repo history

**Files:**
- Modify: `frontend/src/routes/RepoAnalysisPage.tsx` (full replacement)

**Interfaces:**
- Consumes: `.repo-history` class (Task 1).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Replace `frontend/src/routes/RepoAnalysisPage.tsx` in full**

```tsx
import { useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAnalyzedRepos, useAnalyzeRepo, useChatRepo } from '../api/github'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

export default function RepoAnalysisPage() {
  const [username, setUsername] = useState('')
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')
  const [analyzed, setAnalyzed] = useState(false)
  const [query, setQuery] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])

  const { data: analyzedRepos } = useAnalyzedRepos()
  const analyzeRepo = useAnalyzeRepo()
  const chatRepo = useChatRepo()

  const handleAnalyze = () => {
    if (!username || !repo) return
    setStatus('Downloading and analyzing repository... This might take a minute depending on repo size.')
    setAnalyzed(false)
    analyzeRepo.mutate({ username, repoName: repo }, {
      onSuccess: (res) => {
        setStatus(`Success! Indexed ${res.files_processed} files.`)
        setAnalyzed(true)
        setChatHistory([])
      },
      onError: (e) => setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`),
    })
  }

  const openFromHistory = (u: string, r: string) => {
    setUsername(u)
    setRepo(r)
    setAnalyzed(true)
    setChatHistory([])
    setStatus(`Reusing previous analysis of ${u}/${r} — ask a question below, or hit Analyze to re-sync.`)
  }

  const handleChat = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    const userMsg = query
    setChatHistory((prev) => [...prev, { role: 'user', text: userMsg }])
    setQuery('')

    chatRepo.mutate({ username, repoName: repo, query: userMsg }, {
      onSuccess: (res) => setChatHistory((prev) => [...prev, { role: 'assistant', text: res.answer }]),
      onError: (e) => setChatHistory((prev) => [...prev, { role: 'assistant', text: `Error: ${e instanceof Error ? e.message : String(e)}` }]),
    })
  }

  return (
    <div className="panel" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>GitHub Repository Analysis</h2>
      <p className="hint">Enter a public GitHub repository to download its source code and chat with it locally using AI RAG.</p>

      {analyzedRepos && analyzedRepos.length > 0 && (
        <div className="repo-history">
          <strong>Already analyzed</strong>
          <ul>
            {analyzedRepos.map((r) => (
              <li key={`${r.username}/${r.repo_name}`}>
                <a href="#" onClick={(e) => { e.preventDefault(); openFromHistory(r.username, r.repo_name) }}>
                  {r.username}/{r.repo_name}
                </a>{' '}
                — {r.file_count} files, analyzed {new Date(r.analyzed_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '1rem' }}>
        <input className="input-field" placeholder="GitHub Username (e.g. torvalds)" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className="input-field" placeholder="Repository Name (e.g. linux)" value={repo} onChange={(e) => setRepo(e.target.value)} />
        <button className="primary-button" onClick={handleAnalyze}>Analyze</button>
      </div>

      {status && <div className="hint" style={{ marginBottom: '1rem' }}>{status}</div>}

      {analyzed && (
        <div style={{ border: '1px solid var(--panel-border)', borderRadius: '12px', padding: '1rem' }}>
          <div style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '1rem' }}>
            {chatHistory.length === 0 && <p className="hint">Ask a question about the code!</p>}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ marginBottom: '1rem', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                <div style={{
                  display: 'inline-block', padding: '0.5rem 1rem', borderRadius: '10px',
                  background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-main)',
                  color: msg.role === 'user' ? 'white' : 'var(--text-main)',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--panel-border)',
                  whiteSpace: 'pre-wrap', textAlign: 'left',
                }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ ...props }) => <p style={{ margin: '0 0 0.5rem 0' }} {...props} />,
                      ul: ({ ...props }) => <ul style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      ol: ({ ...props }) => <ol style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      li: ({ ...props }) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
                      code: ({ className, ...props }) =>
                        className?.includes('language-')
                          ? <code style={{ display: 'block', fontFamily: "'IBM Plex Mono', monospace", background: 'rgba(36,29,18,0.08)', padding: '0.5rem', borderRadius: '6px', overflowX: 'auto' }} className={className} {...props} />
                          : <code style={{ fontFamily: "'IBM Plex Mono', monospace", background: 'rgba(36,29,18,0.08)', padding: '0.1rem 0.3rem', borderRadius: '4px' }} {...props} />,
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {chatRepo.isPending && <div className="hint">Thinking...</div>}
          </div>
          <form onSubmit={handleChat} style={{ display: 'flex', gap: '10px' }}>
            <input
              className="input-field" style={{ flex: 1 }} value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Where is the database connection setup?"
              disabled={chatRepo.isPending}
            />
            <button className="primary-button" type="submit" disabled={chatRepo.isPending || !query.trim()}>Send</button>
          </form>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify RepoAnalysisPage's test still passes unmodified**

Run: `cd frontend && npm run test -- RepoAnalysisPage.test.tsx`
Expected: 1 test PASS (asserts on the link text `octocat/Hello-World`, which is unchanged).

- [ ] **Step 3: Full verification**

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/RepoAnalysisPage.tsx
git commit -m "feat(frontend): restyle RepoAnalysisPage chat bubbles and analyzed-repo history"
```

---

### Task 8: Final visual QA sweep

**Files:** none expected — verification only.

**Interfaces:** none (terminal task).

- [ ] **Step 1: Full automated verification**

Run: `cd frontend && npm run typecheck && npm run test && npm run build`
Expected: typecheck clean, full suite passes (same count as before this plan — no test was added or removed, only a few had unrelated-to-styling assertions re-verified), build succeeds.

- [ ] **Step 2: Live browser check — desktop**

Start the backend (`uvicorn app.main:app --port 8080`, no `--reload`) and the frontend (`npm run dev`). In the Browser pane:
1. `/login` — confirm the kicker pill + Fraunces headline render above the form, fonts loaded (Fraunces on headings, IBM Plex Mono on the kicker).
2. Register/login → `/generate` — confirm the step strip shows `01 Profile`, `02 Target role`, etc., with the active step underlined in the accent color.
3. Run the wizard with the sample profile → confirm the Analysis step (AgentTerminal) renders in the new warm dark colors, not the old black/neon-green.
4. On the Results page: confirm the pull-quote block renders (italic serif + citation), the skill-gap and market-demand lists show numbered rank markers, the FGCR scorecard tiles are tinted by pass/warn/fail band, and the learning path renders as syllabus rows with circular numbered badges.
5. `/tracker` — confirm each step shows a colored status tag next to its name (not parenthetical text), and steps render as syllabus rows.
6. `/repo-analysis` — analyze a repo, confirm the "Already analyzed" block renders in the new mono citation-index style, and chat bubbles use the new accent/panel colors.

- [ ] **Step 3: Live browser check — mobile regression**

Resize to 375px width (per the existing project pattern for this check) on `/generate` and `/tracker`:
1. Confirm the top nav (`.app-nav`) still wraps instead of causing horizontal scroll — `document.body.scrollWidth` should equal `window.innerWidth`.
2. On a tracked step with a confidence row, confirm `.confidence-row` still wraps and each `.confidence-btn` still computes to a minimum ~44×44px touch target (`getComputedStyle` check), and confirm the active-rating button now shows the solid accent fill instead of the old indigo tint.
3. Confirm the new `.syl-row` grid collapses to a single column at this width (per Task 1's `@media (max-width: 850px)` rule) rather than clipping content.

- [ ] **Step 4: Report results**

No commit expected from this task unless the live check finds a real regression — if it does, fix it in the relevant earlier task's files, re-run that task's verification, and re-check here.
