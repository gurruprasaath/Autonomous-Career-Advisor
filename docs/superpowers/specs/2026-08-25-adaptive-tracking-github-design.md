# Adaptive Tracking + GitHub Evidence — Design

## Problem

The learning path is generated once from the student's profile and never changes
afterward. The tracker's step status is a manual dropdown (`pending` /
`in_progress` / `completed` / `struggling`), and the "Recalculate Sub-Path"
button that would react to a `struggling` mark is a UI mock
(`alert("Re-planning logic triggered! (Mock)")`) — it calls nothing. There is no
automatic signal of whether the student actually did the work.

## Goals

1. Replace the manual status dropdown with signals that derive status
   automatically: a short quiz, a confidence self-rating, time spent, and
   (new) evidence from the student's own public GitHub activity.
2. Wire the "Recalculate Sub-Path" button to a real re-planning call that
   regenerates the *remaining* (not-yet-completed) steps using the reason a
   step was marked `struggling`.

## Non-goals

- GitHub OAuth / private repo access — username + public API only.
- Framework/library detection (React, FastAPI, Express) from dependency
  files — language-level detection only (Python, JavaScript, TypeScript,
  Java, ...) via GitHub's `/languages` endpoint. Framework detection is
  future work (parsing `package.json` / `requirements.txt` per repo).
- Any changes to the initial path-generation pipeline (profile → review →
  market → gap → plan → verify) — this design only adds tracking + a
  re-plan trigger downstream of it.

## Data model changes

`backend/app/db/models.py`

- `PathStep` gains three columns: `quiz_score` (int, nullable),
  `confidence_rating` (int 1-5, nullable), `time_spent_minutes` (int,
  default 0).
- New `GithubEvidence` table: `id, user_id, skill_id, repo_name,
  repo_language, last_pushed_at, detected_at` — one row per (skill × repo)
  match, so every claim is traceable to a specific repo (same evidence-trail
  pattern the Market Demand Agent already uses for job postings).
- `User` gains `github_username` (str, nullable).

## GitHub sync

New `backend/app/providers/github.py`:

- `fetch_repo_languages(username: str) -> dict[str, list[dict]]` — calls
  `GET https://api.github.com/users/{username}/repos` (public, unauthenticated,
  60 req/hour is enough for a single user's repo list), then
  `GET /repos/{owner}/{repo}/languages` per repo. Returns `{language:
  [{repo_name, last_pushed_at}, ...]}`.
- New endpoint `POST /api/github/sync` (auth required): takes `{username}`,
  stores it on the user, fetches languages, maps each GitHub language name to
  a taxonomy skill via the existing `match_mention()` alias system (add
  `"c#"`, `"c++"` etc. aliases where GitHub's language names differ from the
  taxonomy's), writes `GithubEvidence` rows, returns the evidence list.
  GitHub reports many languages the 78-skill taxonomy doesn't cover (Go,
  Rust, Ruby, Kotlin, Swift, ...); those simply produce no evidence row —
  same "ignored, not an error" handling the profile extractor already uses
  for unmatched mentions. Not exhaustively adding every possible language to
  the taxonomy is a deliberate scope call, not an oversight.
- Failure handling: GitHub API errors (rate limit, unknown username) return a
  4xx with a clear message; sync is optional, never blocks path generation
  or tracking.

## Per-step tracking UI (`LearningTracker.jsx`)

Replaces the status `<select>` with:

- **Timer**: start/stop button; accumulates into `time_spent_minutes`. Shown
  against `estimated_weeks × hours_per_week` as a simple progress bar.
- **Confidence**: 1-5 rating control, shown after the student marks a step
  "studied."
- **Quiz**: "Take Quiz" button → `POST /api/tracker/step/{id}/quiz`
  generates 3-4 questions from the step's `objective` via the LLM
  (`invoke_llm`, same pattern as the other agents), returns questions;
  submitting answers scores them and stores `quiz_score`.
- **GitHub evidence** (if any `GithubEvidence` row matches the step's
  `skill_id`): a read-only chip, e.g. "✓ seen in `my-api` (pushed 3 weeks
  ago)" — supporting signal only, not a completion trigger by itself.

## Status derivation (deterministic, mirrors the FGCR verifier's hard-rule +
signal pattern rather than one black-box LLM call)

```
completed:   quiz_score >= 70 AND confidence_rating >= 3
struggling:  quiz_score < 50 OR confidence_rating <= 2
in_progress: anything else (started but not yet scored/rated)
```

GitHub evidence never auto-completes a step on its own (old repos in a
language aren't proof of *this* step's material) — it's surfaced as
supporting context and does not enter the formula above in this first cut.

`update_step_status` in `crud.py` is replaced by a `record_step_progress(db,
step_id, *, quiz_score=None, confidence=None, minutes_delta=0)` that updates
the fields above and recomputes `status` via the formula.

## Adaptive re-planning

`POST /api/tracker/journey/{id}/recalculate` (replaces the mock alert):

1. Loads the journey's remaining steps (`status != "completed"`).
2. Builds a `revision_request` string from the struggling step(s): which
   skill, quiz score, confidence, and (if available) which quiz questions
   were missed.
3. Calls the existing `build_path` / `verify_path` functions from
   `planner_agent.py` / `verifier_agent.py` directly (not a new pipeline) —
   passing the *remaining* gap subset and the revision request — then
   overwrites the remaining `PathStep` rows with the regenerated steps,
   preserving already-`completed` ones untouched.
4. Returns the updated step list; frontend re-renders that journey's
   timeline.

## Testing

- `backend/tests/test_github_provider.py`: `fetch_repo_languages` against a
  mocked `httpx` response (a fixture with 2-3 repos, overlapping languages) —
  asserts aggregation and language→skill mapping.
- `backend/tests/test_progress.py`: `record_step_progress` — asserts the
  three status-derivation branches (completed / struggling / in_progress)
  from combinations of quiz_score/confidence.
- No test for the re-planning HTTP call itself (it's a thin wrapper over
  already-tested `build_path`/`verify_path`); manual verification against the
  live server is enough, matching how the rest of this codebase is tested.
