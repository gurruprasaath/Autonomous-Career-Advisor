# Frontend Rewrite — Design

## Problem

The current frontend (`frontend/src/`, plain JS + JSX, 9 component files) works feature-by-feature but was built incrementally across many separate passes with no shared architecture: navigation is in-memory tab state (a page refresh always drops the user back to step 1), every component manages its own server data with ad-hoc `useState`/`useEffect`/`fetch`, there is no record anywhere of which GitHub repos a user has already analyzed (so re-submitting the same repo silently re-downloads and re-indexes it with no "you already did this" signal), and there are zero automated tests for any of it. A live audit also found a genuine mobile layout bug (nav row and confidence-rating row overflow at 375px width) and a data bug (GitHub language evidence double-counts every repo that has both HTML and CSS files, since GitHub reports them as separate languages that map to the same taxonomy skill).

This is a full rebuild of `frontend/`, not an incremental patch: same feature set, real architecture underneath.

## Goals

1. Real URL-based routing — refresh keeps you on the same page; browser back/forward works.
2. A real server-state layer (TanStack Query) so "does the app remember X" stops being a per-component ad-hoc question — it's a cache with defined invalidation rules.
3. Backend support for "have I already analyzed this repo" — the actual root cause of the repeated-analysis complaint (nothing currently records it).
4. TypeScript throughout — typed API responses, typed props, typed query/mutation hooks.
5. A real test suite (Vitest + React Testing Library) — zero exists today.
6. Fix the two bugs the live audit found (GitHub evidence duplication, mobile layout overflow) as part of the rebuild, not as a follow-up patch.
7. Preserve the existing visual design (colors, panel/button styles, typography) — this is an architecture rebuild, not a redesign.

## Non-goals

- No new product features beyond what exists today (Profile intake, role picker, results/path view, learning tracker with quiz/confidence/timer/GitHub-evidence/competency-chart, GitHub repo chat, auth).
- No visual redesign — `index.css`'s existing tokens (colors, spacing, panel/button/badge styles) are ported, not reinvented.
- No other backend changes beyond the one new table/endpoint in Goal 3 — the backend's agents, DB models, and existing endpoints are otherwise untouched.
- Not migrating to Next.js or any other framework — same Vite + React setup, upgraded within it.

## Backend addition: remembering analyzed repos

New table `AnalyzedRepo`: `id, user_id, username, repo_name, file_count, analyzed_at`. `POST /api/github/repo/{username}/{repo_name}/analyze` upserts a row (update `file_count`/`analyzed_at` if `(user_id, username, repo_name)` already exists, insert otherwise) instead of only touching the Chroma collection. New endpoint `GET /api/github/repos` returns the calling user's analyzed repos, ordered by `analyzed_at` descending. The frontend uses this to show "Already analyzed 5 min ago — Chat now / Re-sync" instead of a bare "Analyze" button with no memory of prior state.

## Bug fixes carried into the rebuild

- **GitHub evidence duplication:** `map_languages_to_evidence` (`backend/app/providers/github.py`) must dedupe evidence rows by `(skill_id, repo_name)` before returning — a repo with both HTML and CSS currently produces two rows for the `html-css` skill; keep one.
- **Mobile layout overflow:** the top nav button row and each tracked step's 1-5 confidence-rating row must wrap (flex-wrap) instead of overflowing horizontally at narrow widths — measured concretely at 375px (438px of content in a 375px viewport before the fix).

## Stack

- **TypeScript** — `tsconfig.json`, all source files become `.ts`/`.tsx`. `@types/react`/`@types/react-dom` are already installed.
- **react-router** (v6) — new dependency.
- **@tanstack/react-query** (v5) — new dependency. All server reads/writes go through it; no component holds its own `useState` copy of server data.
- **Vitest + @testing-library/react + @testing-library/jest-dom + jsdom** — new dev dependencies. Vite already provides the config surface Vitest plugs into.
- Existing dependencies kept as-is: `react`, `react-dom`, `reactflow` (the path DAG viz), `react-markdown` + `remark-gfm` (repo-chat answer rendering).

## Routes

| Path | Renders | Notes |
|---|---|---|
| `/login` | Auth (login/register toggle, as today) | Redirects to `/generate` if already authenticated |
| `/generate` | The existing Profile → Role → Analysis → Results wizard | Kept as one route with internal step state — a genuinely linear flow; fragmenting each step into its own route would add routing complexity (deep-linking into step 3 with no step 1/2 data makes no sense) for no real benefit |
| `/tracker` | Learning Tracker (journeys, per-step timer/confidence/quiz, GitHub-evidence chips, competency chart) | |
| `/repo-analysis` | GitHub Repo Chat, now showing the list of previously-analyzed repos from `GET /api/github/repos` | |

A route guard redirects to `/login` when there's no auth token, mirroring today's `isLoggedIn` gate in `App.jsx` but as real routing instead of a conditional render.

## Data layer

One typed API client (`src/api/client.ts`) wrapping `fetch` with the auth header + 401 handling `App.jsx`/`api.js` already do today, plus one file per domain under `src/api/` exporting typed TanStack Query hooks:

| File | Hooks | Backing endpoints |
|---|---|---|
| `auth.ts` | `useLogin`, `useRegister` (mutations) | `/api/auth/login`, `/api/auth/register` |
| `advise.ts` | `useAdvise` (mutation), `useRoles` (query) | `/api/advise`, `/api/roles`, `/api/extract_pdf` |
| `tracker.ts` | `useJourneys`, `useCompetencyHistory` (queries); `useRecordProgress`, `useGenerateQuiz`, `useSubmitQuiz`, `useRecalculateJourney` (mutations) | `/api/tracker/*` |
| `github.ts` | `useAnalyzedRepos` (query); `useSyncGithub`, `useAnalyzeRepo`, `useChatRepo` (mutations) | `/api/github/*` |

Mutation → invalidation rules (this is what actually fixes "the app doesn't remember/update"):
- `useRecordProgress`, `useSubmitQuiz` invalidate `useJourneys` (a step's status/quiz score changed).
- `useRecalculateJourney` invalidates both `useJourneys` and `useCompetencyHistory` (steps regenerated, competency reassessed).
- `useSyncGithub` invalidates `useJourneys` (new evidence chips may now apply to existing steps).
- `useAnalyzeRepo` invalidates `useAnalyzedRepos`.

## File structure

```
frontend/src/
  main.tsx                    — QueryClientProvider + RouterProvider setup
  api/
    client.ts                 — typed fetch wrapper, auth header, 401 handling
    types.ts                  — shared response/request types (mirrors backend Pydantic schemas)
    auth.ts / advise.ts / tracker.ts / github.ts
  routes/
    LoginPage.tsx
    GeneratePage.tsx           — hosts the existing step wizard
    TrackerPage.tsx
    RepoAnalysisPage.tsx
  components/
    ProfileForm.tsx, RolePicker.tsx, AgentTerminal.tsx, Results.tsx, PathGraph.tsx
    StepTracker.tsx, QuizModal.tsx, GithubConnect.tsx, CompetencyChart.tsx   — split out of today's single LearningTracker.jsx, each with one responsibility
  styles/
    index.css                  — ported as-is
  test/
    setup.ts                   — jsdom + testing-library matchers
  Component/hook test files co-located as `*.test.tsx` next to what they test
```

## Testing

- Component tests (RTL): `ProfileForm`, `RolePicker`, `StepTracker` (timer/confidence/quiz interactions), `GithubConnect` (shows analyzed-repo state correctly), `CompetencyChart` (renders a trajectory, handles a single data point without divide-by-zero — a real edge case already found in this codebase's history).
- Data-layer tests: each query/mutation hook against a mocked API client — cache invalidation rules are exactly the kind of thing worth locking down with a test (e.g. "submitting a quiz invalidates journeys").
- No end-to-end/browser tests in this pass — component + hook tests are the bar being set from zero; full E2E is future work, not a gap this rewrite needs to close.

## Migration approach

`frontend/src/` is replaced in place (new TypeScript files alongside/replacing the `.jsx` ones as each piece is rebuilt), `package.json` gains the new dependencies, `vite.config.js` becomes `vite.config.ts` with a `test` block for Vitest, and a `tsconfig.json` is added. The backend addition (Goal 3) is a small, separate, additive change (new table + one new endpoint), not a rewrite of anything backend-side.
