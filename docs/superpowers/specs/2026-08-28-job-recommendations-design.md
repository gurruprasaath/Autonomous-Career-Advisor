# Job Recommendations — Design

## Problem

`analyse_market` already fetches full job postings (title, company, location, description, skills) to compute aggregate skill-demand stats for the Results page, then discards the individual postings entirely. There is no way for a user to see *which specific jobs* fit them — only the aggregate "X% of postings want skill Y." Separately, job data today comes only from a bundled synthetic sample dataset; there's a fully-written but never-activated Adzuna provider sitting unused in the codebase.

## Goals

1. A new `/jobs` page recommending live job postings ranked by fit to the user's current skills *and* the skills they're actively learning right now.
2. A deterministic, auditable skill-overlap score as the primary ranking signal (matches the app's existing pattern: Gap Engine, Market Demand agent — reproducible, citable, no LLM in the counting path), blended with a semantic-similarity score from the local embedding model the app already runs for free (Chroma's bundled ONNX MiniLM — the same model backing `skills_collection`/`postings_collection`/`courses_collection`/repo-chat retrieval today).
3. Built on the existing pluggable `JobProvider` interface, so it works against the sample dataset today and against Adzuna (or any future provider) with zero code change once credentials exist.
4. Adzuna wired up as the first live provider — this requires adding an `url` (apply link) field to postings, since a recommendation needs somewhere to send the user.
5. Auto-scoped to the user's most recently created `LearningJourney`'s `target_role` — no extra input required to see matches.

## Non-goals

- Not implementing JobSpy or any other provider in this pass. That was already identified this session as blocked on an unrelated Python 3.13/numpy build-tooling issue; the `JobProvider` interface stays open for it later as a separate follow-up.
- Not persisting fetched postings or computed recommendations in the database — postings are live and ephemeral by nature; nothing here needs a history table.
- No change to the existing `analyse_market` aggregate-stats path or the Results page's Market Demand chart — this is a new, separate code path that happens to reuse the same `JobProvider.fetch()` call and the same `_posting_skills` skill-extraction helper.
- Not building a saved-jobs/bookmarking feature.

## Data & scoring

### Skill signals (both already persisted — no new tables)

- **Skills you have**: your most recent `CompetencyHistory` row per `skill_id`. Weight = `depth_score / 10` (0–1).
- **Skills you're studying**: `skill_id`s of your most recently created journey's `PathStep`s whose `status != "completed"`. Weight = fixed `0.4`.
- If a skill_id has both signals, use the higher weight — don't double-count.
- "Most recent journey" = the user's `LearningJourney` ordered by `created_at` descending, first row (same ordering `GET /api/tracker/journeys` already uses).

### Scoring per posting

1. Determine the posting's required skills exactly the way the Market Demand agent already does — reuse `market_agent._posting_skills(posting)` directly (pre-annotated `skills` list for sample data, taxonomy-description-scan for live data) rather than reimplementing skill extraction.
2. **Overlap score** = (sum of the user's weight across the posting's skills) / (number of the posting's skills) — 0 to 1.
3. **Semantic score** = cosine similarity between an embedding of the user's skill-profile text (skill names they have, plus a `"currently learning: ..."` clause for in-progress ones, joined into one string) and an embedding of the posting's `title + description`, computed with the same local embedding model already used elsewhere in this codebase (Chroma's bundled ONNX MiniLM function) — no new dependency, no API key, no GPU.
4. **Final score** = `0.7 * overlap_score + 0.3 * semantic_score`. Sort descending, return the top 15.
5. Each result carries the matched skill *names* (from the overlap step) so the UI shows *why* a job ranked where it did — not a black-box number.

## Backend

- `backend/app/providers/base.py` — add `url: str` to the `Posting` TypedDict.
- `backend/app/providers/adzuna.py` — populate `url=item.get("redirect_url", "")` when building each `Posting`.
- `backend/app/providers/sample.py` — no change; sample JSON simply has no `url` key, and consumers read it with `.get("url", "")`.
- `backend/app/db/crud.py` — add two functions:
  - `get_latest_competency_per_skill(db, user_id) -> dict[str, models.CompetencyHistory]` (the existing `get_latest_competency` only looks up one skill at a time; this is the "give me the whole current picture" version).
  - `get_most_recent_journey(db, user_id) -> models.LearningJourney | None`.
- New `backend/app/agents/job_matcher.py` — `recommend_jobs(db, user_id, target_role, limit=15) -> list[JobRecommendation]`, implementing the scoring above.
- `backend/app/schemas.py` — add `JobRecommendation(posting_id, title, company, location, url, score, matched_skills: list[str])`.
- `backend/app/main.py` — new `GET /api/jobs/recommendations` (auth required): look up the user's most recent journey (if none exists, return a 404 with a message pointing them to Generate Path — this is a real, expected state for a new user, not an error condition to hide), then call `recommend_jobs` with that journey's `target_role`.

## Frontend

- `frontend/src/api/types.ts` — add a `JobRecommendation` type mirroring the schema.
- `frontend/src/api/jobs.ts` — `useJobRecommendations()` query hook.
- `frontend/src/routes/JobsPage.tsx` — new page, styled in the already-shipped editorial system: a ranked list reusing the existing `.syl-row`-style numbered rows, matched-skill chips styled like the existing `.tag`, an apply link styled like `.resource`. A clear empty state ("no journey yet — generate a learning path first") when the backend 404s for that reason, with a link to `/generate`.
- `frontend/src/AppShell.tsx` — add a "Job Matches" nav link alongside the existing three.
- `frontend/src/main.tsx` — add the `/jobs` route inside the existing `RequireAuth`-guarded layout route.

## Setup required from the user

Register a free account at https://developer.adzuna.com, then set `JOB_PROVIDER=adzuna`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` in `backend/.env`. Until that's done, the feature works end-to-end against the bundled sample dataset — clearly synthetic, no real apply links — exactly like every other feature that already reads job postings in this app.

## Testing

- Backend: unit tests for `get_latest_competency_per_skill`, `get_most_recent_journey`, and `recommend_jobs`'s scoring math (overlap calculation, the "higher weight wins" rule when a skill has both signals, the 0.7/0.3 blend) using a fake in-memory `JobProvider` — no real network calls, no dependency on live Adzuna credentials in tests (same mocking pattern `test_github_provider.py` already uses for `httpx`).
- Frontend: `JobsPage.test.tsx` covering the empty-state (no journey yet) and the rendered-recommendations case, using the same patterns already established (`vi.stubGlobal('fetch', ...)`, a real `QueryClientProvider`).
