# LeetCode Evidence — Design

**Status:** approved in brainstorming, 2026-09-27
**Roadmap:** sub-project **A** of the SkillMeet-parity roadmap
(A LeetCode evidence → C JD Analyzer → E evidence-aware job matching → B frequency-ranked DSA problems
→ F AI mock interview → G project challenges → D interview experiences → H verified public profile
→ I daily challenge + streaks). SkillMeet has no public API; each item rebuilds one of its features on
data sources this project may legitimately use.

## Goal

Let a learner connect a public LeetCode username so their real problem-solving record becomes
(1) a graded, deterministic DSA depth input to the competency model and (2) a list of weak DSA topics
that feeds interview prep and, later, sub-project B.

## Data source

LeetCode has no official API. Its public profile pages use an undocumented GraphQL endpoint,
`POST https://leetcode.com/graphql` (headers: `Content-Type: application/json`,
`Referer: https://leetcode.com`), which needs no login for public profile data. Verified live
2026-09-27:

```graphql
query($u: String!) {
  matchedUser(username: $u) {
    submitStatsGlobal { acSubmissionNum { difficulty count } }   # All / Easy / Medium / Hard
    tagProblemCounts {
      advanced     { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      fundamental  { tagName problemsSolved }
    }
  }
  recentAcSubmissionList(username: $u, limit: 1) { timestamp }    # unix seconds, as a string
}
```

A missing user returns HTTP 200 with `data.matchedUser = null` plus an `errors` entry. Because the
endpoint is undocumented and may change, every failure other than "user not found" is treated as
"LeetCode unavailable" and never breaks any other feature.

## Components

### `backend/app/providers/leetcode.py` (new)

- `class LeetcodeUserNotFound(RuntimeError)`, `class LeetcodeUnavailable(RuntimeError)`.
- `fetch_profile(username: str) -> dict` — one GraphQL call with `httpx`, timeout 10 s. Returns the
  snapshot:
  ```python
  {"easy": int, "medium": int, "hard": int,
   "topics": {tag_name: problems_solved, ...},   # all three tiers flattened
   "last_accepted_at": "ISO-8601 UTC" | None}
  ```
  - `matchedUser is None` → `LeetcodeUserNotFound`.
  - Network error, non-200, invalid JSON, or missing expected keys → `LeetcodeUnavailable`.
- `dsa_depth(snapshot: dict) -> int | None` — pure, deterministic:
  ```
  weighted  = easy + 2*medium + 3*hard
  dsa_depth = clamp(round(2 * log2(1 + weighted / 15)), 1, 10)
  ```
  Returns `None` when `easy + medium + hard == 0` (a synced account with no solves is absence of
  evidence, not evidence of depth 1). The log scale gives diminishing returns. Calibration points
  (these are the unit-test cases):
  | Solved | weighted | depth |
  |---|---|---|
  | 0 | 0 | `None` |
  | 20 easy | 20 | 2 |
  | 100 easy | 100 | 6 |
  | 50 easy + 30 medium | 110 | 6 |
  | 100 easy + 150 medium + 50 hard | 550 | 10 |
- `CORE_TOPICS` — the 14 core interview topics, using LeetCode's real tag names: `Array`, `String`,
  `Hash Table`, `Two Pointers`, `Sliding Window`, `Binary Search`, `Stack`, `Linked List`, `Tree`,
  `Graph Theory`, `Heap`, `Dynamic Programming`, `Greedy`, `Backtracking`.
- `weak_topics(snapshot: dict, limit: int = 3) -> list[str]` — pure: core topics with fewer than 5
  solves (a topic absent from `topics` counts as 0), sorted by solve count ascending, ties broken by
  `CORE_TOPICS` order, first `limit` returned.

### Storage (`backend/app/db/models.py`, `database.py`, `crud.py`)

- `users.leetcode_username VARCHAR` and `users.leetcode_stats_json TEXT` — added to
  `run_migrations()`'s additive ALTER list, next to `github_username`. Only the raw snapshot plus
  `synced_at` is stored; `dsa_depth` and `weak_topics` are always recomputed from it, so any
  displayed number can be reproduced from stored data.
- `competency_history.leetcode_depth INTEGER` (nullable) — records the LeetCode input used for each
  assessment, so every history row remains recomputable from its inputs.
- crud: `get_leetcode_snapshot(user) -> dict | None` (parses the JSON);
  `create_competency_history_batch` accepts an optional `leetcode_depth` key per row (default `None`).

### Competency (`backend/app/agents/competency_agent.py`)

`assess_competency(..., leetcode_depth: int | None = None)` — new keyword argument with a default,
so existing callers and tests are unaffected.

- When `leetcode_depth is not None`, add the component `(leetcode_depth, 0.35)`. Existing weights are
  unchanged: resume 0.30, quiz 0.40, confidence 0.15; GitHub stays an additive +1.5. The weighted
  average already normalizes by total weight.
- The early "resume only" return also requires `leetcode_depth is None`.
- The rationale prompt and deterministic fallback string both include the LeetCode input.
- Callers pass `leetcode_depth` **only for the `problem-solving` skill** (the taxonomy's single DSA
  node); every other skill gets `None`.

Callers updated: `recalculate_journey` (per remaining step) and `/api/advise` (initial history rows,
when the user is logged in and has synced). Both store `leetcode_depth` in the history row.

### API (`backend/app/main.py`)

- `POST /api/leetcode/sync` `{"username": str}` (authenticated)
  - Username must match `^[A-Za-z0-9_-]{1,30}$`, otherwise 400.
  - `LeetcodeUserNotFound` → 404 `"LeetCode user '<name>' not found"`.
  - `LeetcodeUnavailable` → 502 `"LeetCode is unavailable right now — try again later"`.
  - On success: saves username + snapshot (with `synced_at`), returns a `LeetcodeSummary`.
- `GET /api/leetcode` (authenticated) → `LeetcodeSummary`, or `null` if never synced.
- `LeetcodeSummary` (pydantic, `schemas.py`): `username, easy, medium, hard, total, dsa_depth,
  weak_topics, last_accepted_at, synced_at`.
- `GET /api/interview-tips` — when the user has a snapshot, appends `weak_topics(snapshot)` to
  `focus_topics` (after the gap skills, de-duplicated).

### Frontend

- `frontend/src/api/leetcode.ts` — `useLeetcodeSummary()` (GET) and `useSyncLeetcode()` (POST,
  invalidates the summary query and interview tips), mirroring `api/github.ts`.
- `frontend/src/components/LeetcodeConnect.tsx` — panel rendered on `TrackerPage` directly below
  `GithubConnect`: username input + Sync button; once synced shows Easy / Medium / Hard counts,
  "DSA depth X/10" (or "No solved problems yet" when `null`), weak-topic chips, and last-synced time.
  Errors show the API's message, as `GithubConnect` does.

## Out of scope (deliberate)

- Feeding LeetCode into the initial advisory LangGraph pipeline's gap analysis. That means threading
  user state through the graph; the existing Recalculate flow applies LeetCode evidence once synced.
- Recency decay: solved counts are cumulative knowledge; `last_accepted_at` is display-only.
- Automatic periodic re-sync: the learner clicks Sync.
- Problem recommendations — that is sub-project B, built on `weak_topics`.

## Testing

- `test_leetcode_provider.py`: `dsa_depth` calibration table (incl. `None` for zero solves);
  `weak_topics` (absent topic = 0, threshold 5, ordering, tie-break, limit); `fetch_profile` with
  mocked `httpx` — success parsing, `matchedUser: null` → `LeetcodeUserNotFound`, non-200 / network
  error / malformed body → `LeetcodeUnavailable`.
- `test_competency_agent.py` additions: LeetCode component weighting changes the score as expected;
  `leetcode_depth=None` leaves existing behavior byte-identical.
- API tests: sync validation (400), 404 and 502 mapping, persisted snapshot round-trips through
  `GET /api/leetcode`, interview tips include weak topics after sync.
- Frontend: `LeetcodeConnect.test.tsx` — not-synced state, successful sync renders counts / depth /
  chips, error message shown.
- One live smoke test against the real endpoint (throwaway script, deleted afterwards), as done for
  the Groq integration.
