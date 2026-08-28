# Generate Wizard Flow — Design

## Problem

The Generate Path wizard (`/generate`) is the only remaining part of the app using in-memory step state on a single route — every other page (`/login`, `/tracker`, `/repo-analysis`, `/jobs`) has a real URL and survives a refresh. Refreshing mid-wizard, or using the browser's back button, silently resets to step 1 with everything typed lost. Separately, uploading a resume PDF feels flimsy: a plain button triggers a hidden file input, the extracted text just appears in the same textarea you'd type into with no acknowledgment of what happened, and a failed extraction shows a native `alert()` that breaks out of the app's designed UI entirely.

## Goals

1. Give each wizard step a real URL (`/generate/profile`, `/generate/role`, `/generate/analysis`, `/generate/results`) so refresh keeps your place and back/forward moves between steps, matching every other page in the app.
2. Persist in-progress wizard data (profile input, chosen role, the result) across a refresh — client-side only, ephemeral for the session, not a new backend concern.
3. Redesign the resume-upload interaction: a real drop-zone, a visible "here's what we got" confirmation (filename + extracted length), and inline error handling instead of `alert()`.
4. Resuming `/generate` (the bare nav link) picks up wherever you left off instead of always restarting at step 1.

## Non-goals

- No changes to the advisor pipeline, the `/api/advise` endpoint, the PDF-extraction endpoint, or any agent — this is entirely frontend navigation/UX.
- No change to `ProfileForm`'s manual-paste textarea behavior, `RolePicker`, `AgentTerminal`'s log animation, or `Results`' content — only how they're wired into the new step pages and (for `ProfileForm`) the upload interaction specifically.
- Not adding resumability across devices/browsers or backend persistence of in-progress wizard state — `sessionStorage` (cleared when the tab closes) is enough for "don't lose my typing on a refresh."
- Not changing the editorial visual system — new elements (drop-zone, upload-confirmation card) use the existing palette/tokens, no new design language.

## Routing and state persistence

Four sibling routes replace the single `/generate` route + its internal `step` state:

| Route | Renders | Redirects to `/generate/profile` if... |
|---|---|---|
| `/generate/profile` | `ProfileForm` | (never — this is the entry point) |
| `/generate/role` | `RolePicker` | no profile input saved yet |
| `/generate/analysis` | `AgentTerminal`, fires the advise mutation | no profile input or no role saved yet |
| `/generate/results` | `Results` | no result saved yet |

Bare `/generate` (index) resumes: no saved state → `/generate/profile`; profile saved but no result → `/generate/role`; result saved → `/generate/results`.

State lives in one `sessionStorage` key (`generate-wizard-state`, JSON: `{ profileInput, role, result }`), read on each step page's mount and written on each step's submit — the same `try/catch`-guarded local-storage idiom already established for the RepoAnalysis chat history, just session-scoped instead of persistent (this data should not survive closing the tab — it's mid-task scratch, not something to remember forever). "Start over" on the results page clears this key and returns to `/generate/profile`.

The `AnalysisStepPage` fires the advise mutation once on mount (guarded against React StrictMode's dev-mode double-effect-invocation) rather than waiting for a user click — matches today's behavior where arriving at the analysis step immediately kicks off the real request behind the fake terminal animation. On failure, the error shows inline and the user is returned to `/generate/role`, same as today's `setStep(1)` fallback.

None of `ProfileForm`, `RolePicker`, `AgentTerminal`, or `Results` need prop-signature changes beyond `ProfileForm` gaining an optional `initialValues` prop (so refreshing on `/generate/profile` restores what you'd already typed) — the routing/state work is entirely in new thin page wrappers around the existing, already-tested components.

## Resume upload redesign

Replaces the current button-triggers-hidden-input pattern in `ProfileForm` with:

- A drop-zone (drag-and-drop, or click to open the file picker) shown when no file has been uploaded yet, styled with the editorial system's palette (dashed border, warm tones, a hover/drag-active state).
- While extracting: an inline "Extracting text from your resume..." message in the drop-zone itself (no more relying on a button label change).
- On success: the drop-zone is replaced by a compact confirmation ("✓ Extracted 1,204 characters from resume.pdf") with a "Remove" action that clears it and shows the drop-zone again.
- On failure: an inline `.error-box` (the same class already used for advisor/login errors elsewhere) instead of `alert()`.
- The manual-paste textarea stays exactly as it is today, unchanged in behavior, still the thing that actually gets submitted — the drop-zone is just a nicer way to fill it.

## Testing

- `ProfileForm.test.tsx` gains cases for: a dropped/selected PDF shows the confirmation with filename + character count; a non-PDF file (or a failed extraction) shows an inline error, never `alert()`; "Remove" clears back to the drop-zone. Existing cases (Continue disabled/enabled, submitted payload) are unaffected since the textarea/labels/button text don't change.
- New page-level tests (`ProfileStepPage`, `RoleStepPage`, `AnalysisStepPage`, `ResultsStepPage`) covering: each page's redirect-when-prerequisite-missing behavior, and that submitting a step persists to `sessionStorage` and navigates to the next route.
