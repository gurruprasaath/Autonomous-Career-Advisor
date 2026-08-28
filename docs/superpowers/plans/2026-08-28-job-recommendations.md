# Job Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/jobs` page that recommends live job postings ranked by fit to the user's current skills (from their resume/competency history) and the skills they're actively learning right now, using a deterministic skill-overlap score blended with a semantic-similarity score from the app's existing local embedding model.

**Architecture:** A new backend agent (`job_matcher.py`) reuses the existing `JobProvider` interface and `market_agent._posting_skills` extraction — same pluggable-source, same skill-extraction — to score postings against two already-persisted signals (`CompetencyHistory`, in-progress `PathStep`s). Semantic similarity reuses the exact "Chroma collection + `.query()`" pattern `core/taxonomy.py`'s `match_mention` already established, applied to a fresh per-request scratch collection instead of a stable long-lived one. The frontend adds one route, one hook, one page, reusing the editorial design system's existing `.syllabus`/`.syl-row`/`.tag`/`.resource` classes — no new CSS.

**Tech Stack:** Same as the rest of the app — FastAPI/SQLAlchemy, Chroma (already-installed `chromadb>=0.5.20`, no new dependency), React/TypeScript/TanStack Query.

## Global Constraints

- Reuse the existing pluggable `JobProvider` interface — no code path may hardcode Adzuna or the sample provider; both must work unchanged.
- No new database tables — postings and recommendations are computed fresh per request, never persisted.
- The overlap score is the primary, auditable signal; the semantic score is a secondary blend (`0.7 * overlap + 0.3 * semantic`) — never let semantic similarity alone drive ranking.
- No new pip/npm dependencies.
- Every task must leave the full backend (`pytest`) and frontend (`npm run typecheck && npm run test && npm run build`) suites passing.

---

### Task 1: Provider `url` field + Adzuna population + skill-signal crud helpers

**Files:**
- Modify: `backend/app/providers/base.py`
- Modify: `backend/app/providers/adzuna.py`
- Modify: `backend/app/db/crud.py`
- Test: `backend/tests/test_progress.py` (add crud-helper tests — same file the other `crud.py` function tests already live in)

**Interfaces:**
- Consumes: `models.CompetencyHistory`, `models.LearningJourney` (existing).
- Produces: `Posting` now carries `url: str`; `crud.get_latest_competency_per_skill(db, user_id) -> dict[str, models.CompetencyHistory]`; `crud.get_most_recent_journey(db, user_id) -> models.LearningJourney | None` — Task 2's `job_matcher.py` calls both by these exact names.

- [ ] **Step 1: Add `url` to the `Posting` type**

In `backend/app/providers/base.py`, add one field to the `Posting` TypedDict:

```python
class Posting(TypedDict):
    id: str
    role: str
    title: str
    company: str
    location: str
    description: str
    skills: list  # optional pre-annotated [{skill_id, level}] (sample data only)
    url: str  # apply link — empty string when the provider has none (sample data)
```

- [ ] **Step 2: Populate `url` in the Adzuna provider**

In `backend/app/providers/adzuna.py`, add `url=item.get("redirect_url", "")` to the `Posting(...)` construction inside `fetch`:

```python
        return [
            Posting(
                id=f"adzuna-{item['id']}",
                role=role,
                title=item.get("title", role),
                company=(item.get("company") or {}).get("display_name", "Unknown"),
                location=(item.get("location") or {}).get("display_name", ""),
                description=item.get("description", ""),
                skills=[],  # no annotations — extracted downstream
                url=item.get("redirect_url", ""),
            )
            for item in results
        ]
```

`backend/app/providers/sample.py` needs no change — its `Posting` dicts come straight from `jobs_sample.json`, which has no `url` key; every consumer reads it defensively with `.get("url", "")`, never `posting["url"]`.

- [ ] **Step 3: Write the failing crud-helper tests**

Append to `backend/tests/test_progress.py` (it already has the `_db()`/`_make_step()` helpers this reuses):

```python
def test_get_latest_competency_per_skill_returns_most_recent_row_per_skill():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=5,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="resume"))
    db.commit()
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=8,
                                    quiz_score=80, confidence_rating=4,
                                    has_github_evidence=True, rationale="improved"))
    db.commit()

    latest = crud.get_latest_competency_per_skill(db, user_id)
    assert latest["python"].depth_score == 8


def test_get_latest_competency_per_skill_covers_multiple_skills():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=5,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="a"))
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="sql", depth_score=3,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="b"))
    db.commit()

    latest = crud.get_latest_competency_per_skill(db, user_id)
    assert set(latest.keys()) == {"python", "sql"}


def test_get_most_recent_journey_orders_by_created_at_desc():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    second_journey = crud.create_learning_journey(db, user_id, "Full-Stack Developer",
                                                   gap_report_json="{}", hours_per_week=10)

    most_recent = crud.get_most_recent_journey(db, user_id)
    assert most_recent.id == second_journey.id


def test_get_most_recent_journey_returns_none_for_user_with_no_journeys():
    db = _db()
    user = models.User(email="nobody@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert crud.get_most_recent_journey(db, user.id) is None
```

`_make_step` returns the `PathStep` it created; `step.journey.user_id` resolves correctly via the existing `PathStep.journey` relationship (lazy-loaded through the still-open `db` session `_make_step` used) — no fixture changes needed.

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd backend && ".venv/Scripts/python" -m pytest tests/test_progress.py -k "competency_per_skill or most_recent_journey" -v`
Expected: FAIL — `AttributeError: module 'app.db.crud' has no attribute 'get_latest_competency_per_skill'` (and similarly for `get_most_recent_journey`).

- [ ] **Step 5: Implement the crud helpers**

Append to `backend/app/db/crud.py`:

```python
def get_latest_competency_per_skill(db: Session, user_id: int) -> dict[str, models.CompetencyHistory]:
    """Most recent CompetencyHistory row per skill_id for this user — the
    'skills you currently have, and how deep' snapshot used by job
    matching. Unlike get_latest_competency (one skill at a time), this
    returns the whole current picture in one query."""
    rows = (db.query(models.CompetencyHistory)
            .filter(models.CompetencyHistory.user_id == user_id)
            .order_by(models.CompetencyHistory.recorded_at.desc())
            .all())
    latest: dict[str, models.CompetencyHistory] = {}
    for row in rows:
        if row.skill_id not in latest:
            latest[row.skill_id] = row
    return latest


def get_most_recent_journey(db: Session, user_id: int) -> models.LearningJourney | None:
    return (db.query(models.LearningJourney)
            .filter(models.LearningJourney.user_id == user_id)
            .order_by(models.LearningJourney.created_at.desc())
            .first())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && ".venv/Scripts/python" -m pytest tests/test_progress.py -k "competency_per_skill or most_recent_journey" -v`
Expected: 4 tests PASS.

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && ".venv/Scripts/python" -m pytest -q`
Expected: all pass (77 existing + 4 new = 81).

- [ ] **Step 8: Commit**

```bash
git add backend/app/providers/base.py backend/app/providers/adzuna.py backend/app/db/crud.py backend/tests/test_progress.py
git commit -m "feat(backend): add posting apply-link field and skill-signal crud helpers"
```

---

### Task 2: Job matcher agent, schema, and endpoint

**Files:**
- Modify: `backend/app/core/vectorstore.py`
- Create: `backend/app/agents/job_matcher.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_job_matcher.py` (new)

**Interfaces:**
- Consumes: `crud.get_latest_competency_per_skill`, `crud.get_most_recent_journey` (Task 1); `market_agent._posting_skills(posting)` (existing); `providers.get_job_provider()`, `providers.base.Posting` (existing + Task 1's `url` field); `core.taxonomy.load_taxonomy()` (existing).
- Produces: `schemas.JobRecommendation`; `job_matcher.recommend_jobs(db, user_id, journey, limit=15) -> list[JobRecommendation]` — the frontend's contract is the `GET /api/jobs/recommendations` endpoint this task wires up, returning `list[JobRecommendation]` as JSON.

- [ ] **Step 1: Add the ephemeral job-matching collection**

Append to `backend/app/core/vectorstore.py`:

```python
def job_matching_collection() -> chromadb.Collection:
    """Ephemeral, reset-per-call collection of the postings scored in one
    /api/jobs/recommendations request — unlike skills/postings/courses,
    this is not a stable long-lived collection (live postings differ every
    call). A single shared name is fine: results are consumed synchronously
    within the same request, before the next call resets it again."""
    client = get_client()
    try:
        client.delete_collection("job_matching_scratch")
    except Exception:
        pass  # collection didn't exist yet — nothing to drop
    return client.get_or_create_collection("job_matching_scratch")
```

- [ ] **Step 2: Add the `JobRecommendation` schema**

Append to `backend/app/schemas.py`:

```python
class JobRecommendation(BaseModel):
    posting_id: str
    title: str
    company: str
    location: str
    url: str = ""
    score: float
    matched_skills: list[str] = []
```

- [ ] **Step 3: Write the failing job-matcher tests**

Create `backend/tests/test_job_matcher.py`:

```python
"""Job matcher: deterministic overlap scoring, blended with semantic
similarity from the local embedding model. Uses a fake in-memory
JobProvider — no real network calls, no Adzuna credentials needed."""
from unittest.mock import patch

from app.agents import job_matcher
from app.db import crud, database, models


def _db():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    Session = database.sessionmaker(bind=engine)
    return Session()


def _make_user_with_journey(db):
    user = models.User(email="t@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(models.CompetencyHistory(user_id=user.id, skill_id="python", depth_score=8,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="resume"))
    db.commit()

    journey = crud.create_learning_journey(db, user.id, "Backend Engineer",
                                           gap_report_json="{}", hours_per_week=10)
    step = models.PathStep(journey_id=journey.id, order=1, skill_id="docker",
                           skill_name="Docker", objective="obj", milestone="ms",
                           estimated_weeks=2.0, status="in_progress")
    db.add(step)
    db.commit()
    db.refresh(journey)
    return user, journey


class _FakeProvider:
    def __init__(self, postings):
        self._postings = postings

    def fetch(self, role, limit=50):
        return self._postings

    def available_roles(self):
        return ["Backend Engineer"]


def test_recommend_jobs_ranks_by_overlap_and_returns_matched_skill_names():
    db = _db()
    user, journey = _make_user_with_journey(db)

    postings = [
        {"id": "job-a", "role": "Backend Engineer", "title": "Backend Engineer",
         "company": "Acme", "location": "Remote", "url": "https://example.com/a",
         "description": "irrelevant",
         "skills": [{"skill_id": "python", "level": "advanced"},
                    {"skill_id": "docker", "level": "intermediate"}]},
        {"id": "job-b", "role": "Backend Engineer", "title": "Backend Engineer",
         "company": "Beta", "location": "Remote", "url": "",
         "description": "irrelevant",
         "skills": [{"skill_id": "rust", "level": "advanced"}]},
    ]

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider(postings)):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    # job-a: python (weight 0.8, resume depth) + docker (weight 0.4, in-progress) -> overlap 0.6
    # job-b: rust (weight 0, no signal) -> overlap 0.0
    # Overlap alone (weighted 0.7) already separates them regardless of the
    # semantic component's actual value, so this assertion is robust.
    assert [r.posting_id for r in results] == ["job-a", "job-b"]
    assert set(results[0].matched_skills) == {"Python", "Docker"}
    assert results[0].score > results[1].score


def test_recommend_jobs_returns_empty_list_when_provider_has_no_postings():
    db = _db()
    user, journey = _make_user_with_journey(db)

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider([])):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    assert results == []


def test_recommend_jobs_handles_a_user_with_no_competency_history_yet():
    # A brand-new journey with no CompetencyHistory rows at all (e.g. the
    # /advise call that created it hasn't written history yet) must not
    # crash — everyone just scores 0 on overlap.
    db = _db()
    user = models.User(email="new@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    journey = crud.create_learning_journey(db, user.id, "Backend Engineer",
                                           gap_report_json="{}", hours_per_week=10)

    postings = [{"id": "job-a", "role": "Backend Engineer", "title": "Backend Engineer",
                "company": "Acme", "location": "Remote", "url": "",
                "description": "irrelevant", "skills": [{"skill_id": "python", "level": "advanced"}]}]

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider(postings)):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    assert len(results) == 1
    assert results[0].matched_skills == []
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd backend && ".venv/Scripts/python" -m pytest tests/test_job_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.job_matcher'`.

- [ ] **Step 5: Implement the job matcher**

Create `backend/app/agents/job_matcher.py`:

```python
"""Job Matcher — ranks live job postings against the user's current skills
and the skills they're actively learning.

Overlap score (primary, auditable): deterministic weighted skill overlap,
same "hard math, not LLM-guessed" philosophy as the Gap Engine and Market
Demand agent. Semantic score (secondary boost): embedding similarity via
the same local Chroma/ONNX MiniLM model already used for taxonomy mention
matching (core/taxonomy.py's match_mention), so postings worded differently
from the taxonomy still surface. Neither path calls an LLM.
"""
from sqlalchemy.orm import Session

from ..core.taxonomy import load_taxonomy
from ..core.vectorstore import job_matching_collection
from ..db import crud, models
from ..providers import get_job_provider
from ..providers.base import Posting
from ..schemas import JobRecommendation
from .market_agent import _posting_skills

OVERLAP_WEIGHT = 0.7
SEMANTIC_WEIGHT = 0.3
IN_PROGRESS_WEIGHT = 0.4
FETCH_LIMIT = 50
RESULT_LIMIT = 15


def _user_skill_weights(db: Session, user_id: int, journey: models.LearningJourney) -> dict[str, float]:
    weights: dict[str, float] = {
        skill_id: history.depth_score / 10
        for skill_id, history in crud.get_latest_competency_per_skill(db, user_id).items()
    }
    for step in journey.steps:
        if step.status != "completed":
            weights[step.skill_id] = max(weights.get(step.skill_id, 0.0), IN_PROGRESS_WEIGHT)
    return weights


def _skill_profile_text(weights: dict[str, float], journey: models.LearningJourney) -> str:
    taxonomy = load_taxonomy()
    learning_ids = {s.skill_id for s in journey.steps if s.status != "completed"}
    have = [taxonomy[sid].name for sid in weights if sid in taxonomy and sid not in learning_ids]
    learning = [taxonomy[sid].name for sid in learning_ids if sid in taxonomy]
    parts = []
    if have:
        parts.append("Skilled in: " + ", ".join(have))
    if learning:
        parts.append("Currently learning: " + ", ".join(learning))
    return ". ".join(parts) or journey.target_role


def _overlap_score(posting: Posting, weights: dict[str, float]) -> tuple[float, list[str]]:
    taxonomy = load_taxonomy()
    matched_ids = [e["skill_id"] for e in _posting_skills(posting) if e["skill_id"] in taxonomy]
    if not matched_ids:
        return 0.0, []
    total = sum(weights.get(sid, 0.0) for sid in matched_ids)
    matched_names = [taxonomy[sid].name for sid in matched_ids if weights.get(sid, 0.0) > 0]
    return total / len(matched_ids), matched_names


def recommend_jobs(db: Session, user_id: int, journey: models.LearningJourney,
                   limit: int = RESULT_LIMIT) -> list[JobRecommendation]:
    weights = _user_skill_weights(db, user_id, journey)
    profile_text = _skill_profile_text(weights, journey)

    postings = get_job_provider().fetch(journey.target_role, limit=FETCH_LIMIT)
    if not postings:
        return []

    collection = job_matching_collection()
    collection.add(
        ids=[p["id"] for p in postings],
        documents=[f"{p['title']}\n{p['description']}" for p in postings],
    )
    # Chroma's default metric returns squared-L2 distance for the
    # unit-normalized ONNX MiniLM vectors it embeds with; for normalized
    # vectors that's cos_sim = 1 - distance/2 (clamped for float drift).
    query = collection.query(query_texts=[profile_text], n_results=len(postings))
    semantic_by_id = {
        pid: max(0.0, min(1.0, 1 - dist / 2))
        for pid, dist in zip(query["ids"][0], query["distances"][0])
    }

    scored: list[tuple[float, Posting, list[str]]] = []
    for posting in postings:
        overlap, matched_names = _overlap_score(posting, weights)
        semantic = semantic_by_id.get(posting["id"], 0.0)
        final_score = OVERLAP_WEIGHT * overlap + SEMANTIC_WEIGHT * semantic
        scored.append((final_score, posting, matched_names))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        JobRecommendation(
            posting_id=p["id"], title=p["title"], company=p["company"],
            location=p["location"], url=p.get("url", ""), score=round(score, 3),
            matched_skills=names,
        )
        for score, p, names in scored[:limit]
    ]
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && ".venv/Scripts/python" -m pytest tests/test_job_matcher.py -v`
Expected: 3 tests PASS. (This loads the real local embedding model the first time `job_matching_collection()` is used, so this run may take longer than a typical unit test — that's expected, not a hang.)

- [ ] **Step 7: Wire up the endpoint**

In `backend/app/main.py`, add `JobRecommendation` to the existing schemas import line:

```python
from .schemas import AdviseRequest, AdvisorResult, UserCreate, Token, RepoChatRequest, RepoChatResponse, JobRecommendation
```

Add the endpoint (place it near the other tracker/journey endpoints):

```python
@app.get("/api/jobs/recommendations", response_model=list[JobRecommendation])
def get_job_recommendations(db: Session = Depends(get_db),
                            current_user: models.User = Depends(get_current_user)):
    from .agents.job_matcher import recommend_jobs
    journey = crud.get_most_recent_journey(db, current_user.id)
    if not journey:
        raise HTTPException(404, "Generate a learning path first to get job recommendations.")
    return recommend_jobs(db, current_user.id, journey)
```

- [ ] **Step 8: Run the full backend suite**

Run: `cd backend && ".venv/Scripts/python" -m pytest -q`
Expected: all pass (81 existing + 3 new = 84).

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/vectorstore.py backend/app/agents/job_matcher.py backend/app/schemas.py backend/app/main.py backend/tests/test_job_matcher.py
git commit -m "feat(backend): add job recommendation matcher and GET /api/jobs/recommendations"
```

---

### Task 3: Frontend — Job Matches page, hook, and routing

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/api/jobs.ts`
- Create: `frontend/src/routes/JobsPage.tsx`
- Create: `frontend/src/routes/JobsPage.test.tsx`
- Modify: `frontend/src/AppShell.tsx`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Consumes: `apiRequest` from `client.ts`; `GET /api/jobs/recommendations` (Task 2), returning `JobRecommendation[]` or a 404 with a `detail` message when no journey exists.
- Produces: `/jobs` route, reachable from `AppShell`'s nav.

- [ ] **Step 1: Add the `JobRecommendation` type**

Append to `frontend/src/api/types.ts`:

```ts
export interface JobRecommendation {
  posting_id: string
  title: string
  company: string
  location: string
  url: string
  score: number
  matched_skills: string[]
}
```

- [ ] **Step 2: Add the query hook**

Create `frontend/src/api/jobs.ts`:

```ts
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { JobRecommendation } from './types'

export function useJobRecommendations() {
  return useQuery({
    queryKey: ['job-recommendations'],
    queryFn: () => apiRequest<JobRecommendation[]>('/api/jobs/recommendations'),
    retry: false,
  })
}
```

- [ ] **Step 3: Write the failing JobsPage tests**

Create `frontend/src/routes/JobsPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import JobsPage from './JobsPage'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <JobsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('JobsPage', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows an empty state pointing to Generate Path when no journey exists yet', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 404, statusText: 'Not Found',
      json: async () => ({ detail: 'Generate a learning path first to get job recommendations.' }),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText('Generate a learning path first to get job recommendations.')).toBeInTheDocument())
    expect(screen.getByText('Generate Path →')).toBeInTheDocument()
  })

  it('renders ranked job matches with matched skills and an apply link', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ([
        { posting_id: 'job-a', title: 'Backend Engineer', company: 'Acme', location: 'Remote',
          url: 'https://example.com/job-a', score: 0.82, matched_skills: ['Python', 'Docker'] },
      ]),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText(/Backend Engineer — Acme/)).toBeInTheDocument())
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('🔗 Apply')).toHaveAttribute('href', 'https://example.com/job-a')
  })
})
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd frontend && npm run test -- JobsPage.test.tsx`
Expected: FAIL — `./JobsPage` does not exist.

- [ ] **Step 5: Implement JobsPage**

Create `frontend/src/routes/JobsPage.tsx`:

```tsx
import { Link } from 'react-router-dom'
import { useJobRecommendations } from '../api/jobs'

export default function JobsPage() {
  const { data: jobs, isLoading, error } = useJobRecommendations()

  if (isLoading) return <div>Finding job matches...</div>

  if (error) {
    return (
      <div className="panel">
        <h2>Job Matches</h2>
        <p className="hint">{error instanceof Error ? error.message : String(error)}</p>
        <Link to="/generate" className="primary-button" style={{ textDecoration: 'none' }}>Generate Path →</Link>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>Job Matches</h2>
      <p className="hint">Ranked by overlap with your current skills and what you're actively learning.</p>
      {jobs && jobs.length === 0 && <div>No matching postings found right now — try again later.</div>}
      <div className="syllabus">
        {jobs?.map((job, i) => (
          <div className="syl-row" key={job.posting_id}>
            <div className="syl-num">{i + 1}</div>
            <div>
              <div className="syl-name">{job.title} — {job.company}</div>
              <p className="syl-obj">{job.location}</p>
              {job.matched_skills.length > 0 && (
                <div className="skill-list" style={{ marginTop: '0.5rem' }}>
                  {job.matched_skills.map((s) => <span key={s} className="tag good">{s}</span>)}
                </div>
              )}
              {job.url && (
                <a className="resource" href={job.url} target="_blank" rel="noreferrer" style={{ marginTop: '0.6rem', display: 'inline-flex' }}>
                  🔗 Apply
                </a>
              )}
            </div>
            <div className="weeks">{Math.round(job.score * 100)}% match</div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd frontend && npm run test -- JobsPage.test.tsx`
Expected: 2 tests PASS.

- [ ] **Step 7: Wire up the nav link and the route**

In `frontend/src/AppShell.tsx`, add a fourth `NavLink` between "GitHub Analysis" and the Logout button:

```tsx
        <NavLink to="/jobs" className={({ isActive }) => `secondary-button ${isActive ? 'active' : ''}`}>
          Job Matches
        </NavLink>
```

In `frontend/src/main.tsx`, import `JobsPage` alongside the other route imports:

```tsx
import JobsPage from './routes/JobsPage'
```

Add the route inside the existing `RequireAuth`-guarded layout route, alongside `generate`/`tracker`/`repo-analysis`:

```tsx
            <Route path="jobs" element={<JobsPage />} />
```

- [ ] **Step 8: Full verification**

Run: `cd frontend && npm run typecheck && npm run test && npm run build`
Expected: typecheck clean, full suite passes (23 existing + 2 new = 25), build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/jobs.ts frontend/src/routes/JobsPage.tsx frontend/src/routes/JobsPage.test.tsx frontend/src/AppShell.tsx frontend/src/main.tsx
git commit -m "feat(frontend): add Job Matches page, hook, and routing"
```

---

### Task 4: Final verification

**Files:** none expected — verification only.

**Interfaces:** none (terminal task).

- [ ] **Step 1: Full automated verification**

Run: `cd backend && ".venv/Scripts/python" -m pytest -q` — Expected: 84 passed.
Run: `cd frontend && npm run typecheck && npm run test && npm run build` — Expected: typecheck clean, 25 tests passed, build succeeds.

- [ ] **Step 2: Live browser check**

Start the backend and frontend dev servers. In the Browser pane:
1. Log in with an account that has **no** learning journey yet, visit `/jobs` — confirm the empty state renders ("Generate a learning path first..." + a working "Generate Path →" link).
2. Run the Generate Path wizard once (sample profile is fine) to create a journey.
3. Visit `/jobs` again — confirm it now renders ranked matches (against the bundled sample dataset unless Adzuna credentials were added to `backend/.env`), each with a rank number, title/company/location, matched-skill tags, a match percentage, and (for Adzuna results only) a working "🔗 Apply" link.
4. Confirm the "Job Matches" nav link appears in the header alongside the other three and highlights when active.

- [ ] **Step 3: If Adzuna credentials are available, verify the live path**

If `backend/.env` has `JOB_PROVIDER=adzuna` with real `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` set, repeat Step 2.3 and confirm the postings are real (spot-check a title/company against a browser search) and the Apply link opens Adzuna's redirect for that posting.

- [ ] **Step 4: Report results**

No commit expected from this task unless the live check finds a real regression — if it does, fix it in the relevant earlier task's files, re-run that task's verification, and re-check here.
