# Results Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `PathGraph.tsx`'s cramped shrink-to-fit diagram with a roadmap.sh-style zigzag spine, restructure the Results page into grouped side-by-side sections instead of a linear stack, and add "Recommended Jobs" and "Interview Tips" sections to it.

**Architecture:** A new `interview_agent.py` (LLM-primary, deterministic fallback, same shape as `competency_agent.py`) backs a new `GET /api/interview-tips` endpoint, mirroring the already-live `GET /api/jobs/recommendations` exactly. `PathGraph.tsx` is restyled in place — same `{path}` prop, same reactflow dependency, different node layout/sizing math. `Results.tsx` is restructured to pair related panels via the existing `.two-col` CSS class and add two new panel components that call the (new and existing) hooks directly.

**Tech Stack:** Same as the rest of the app — FastAPI/pydantic, React/TypeScript/TanStack Query, reactflow (already a dependency, no new packages).

## Global Constraints

- No change to `/api/advise`'s response shape or the advisor pipeline (`graph.py`) — jobs and interview tips are fetched separately by the Results page, exactly like the existing Job Matches page already does.
- No change to `RolePicker`, `AgentTerminal`, `ProfileForm`, the wizard routing, or `GapView`/`ProfileView`/`VerifierBadge`/`ResumeReviewView`'s internals — only new components and `Results.tsx`'s layout change.
- The interview tips agent must never raise or return nothing — it always returns a usable `InterviewTips`, falling back to a templated one built from the real gap-skill names if the LLM is unavailable or returns bad output (same philosophy as `competency_agent.py`, not `review_agent.py`'s return-`None`-on-failure pattern).
- This codebase has no FastAPI `TestClient` endpoint tests anywhere (verified: `grep -r TestClient backend/tests` finds nothing) — new endpoints are unit-tested at the agent-function level only, same as `get_job_recommendations` today, and verified live manually, not via a new HTTP test pattern.
- Every task must leave the relevant test suite (`pytest tests/ -v` for backend, `npm run typecheck && npm run test && npm run build` for frontend) passing.

---

### Task 1: Interview Tips agent + endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/agents/interview_agent.py`
- Test: `backend/tests/test_interview_agent.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `get_llm`/`invoke_llm`/`extract_json` from `app.core.llm` (existing); `crud.get_most_recent_journey(db, user_id) -> models.LearningJourney | None` (existing, already used by `get_job_recommendations`).
- Produces: `schemas.InterviewTips(role: str, focus_topics: list[str], common_questions: list[str], advice: str)`; `generate_interview_tips(role: str, focus_topics: list[str]) -> tuple[InterviewTips, list[str]]` — Task 3's frontend hook consumes the endpoint this task adds, by its exact path `/api/interview-tips`.

- [ ] **Step 1: Add the `InterviewTips` schema**

In `backend/app/schemas.py`, append after the existing `JobRecommendation` class (end of file):

```python
class InterviewTips(BaseModel):
    role: str
    focus_topics: list[str] = []
    common_questions: list[str] = []
    advice: str = ""
```

- [ ] **Step 2: Write the failing agent tests**

Create `backend/tests/test_interview_agent.py`:

```python
"""Interview Tips agent: LLM-primary, always degrades to a usable
templated result built from the real gap-skill names — never raises,
never returns nothing. Same pattern as test_competency_agent.py."""
from unittest.mock import MagicMock, patch

from app.agents.interview_agent import generate_interview_tips


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def test_uses_llm_output_when_valid():
    fake_json = """{"focus_topics": ["SIEM", "Incident Response"],
      "common_questions": ["Describe a SIEM alert you triaged."],
      "advice": "Brush up on log analysis before the interview."}"""
    with patch("app.agents.interview_agent.get_llm") as mock_get_llm, \
         patch("app.agents.interview_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        tips, notes = generate_interview_tips("Cybersecurity Analyst", ["SIEM", "Incident Response"])

    assert notes == []
    assert tips.role == "Cybersecurity Analyst"
    assert tips.common_questions == ["Describe a SIEM alert you triaged."]
    assert tips.advice == "Brush up on log analysis before the interview."


def test_falls_back_to_templated_tips_on_malformed_json():
    with patch("app.agents.interview_agent.get_llm") as mock_get_llm, \
         patch("app.agents.interview_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response("not json at all")
        tips, notes = generate_interview_tips("Data Engineer", ["ETL / Data Pipelines"])

    assert len(notes) == 1
    assert tips.role == "Data Engineer"
    assert "ETL / Data Pipelines" in tips.common_questions[0]
    assert "ETL / Data Pipelines" in tips.advice


def test_falls_back_to_templated_tips_when_llm_unavailable():
    with patch("app.agents.interview_agent.get_llm", side_effect=RuntimeError("no llm")):
        tips, notes = generate_interview_tips("Data Engineer", [])

    assert len(notes) == 1
    assert tips.role == "Data Engineer"
    assert tips.common_questions  # never empty, even with no focus topics
    assert "Data Engineer" in tips.advice
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_interview_agent.py -v`
Expected: FAIL — `app.agents.interview_agent` does not exist yet.

- [ ] **Step 4: Implement `interview_agent.py`**

Create `backend/app/agents/interview_agent.py`:

```python
"""Interview Tips agent — role-specific interview prep advice.

LLM-primary, but never returns nothing: a candidate opening this panel
always sees something useful, even if the LLM is unreachable or returns
bad output, via a templated fallback built from the learner's real gap
skills (same "always degrade to something usable" philosophy as
competency_agent.py and resource_curator_agent.py, not review_agent.py's
return-None-on-failure pattern — interview prep advice is safe and useful
even generically, unlike a personalized resume critique).
"""
import logging

from ..config import get_settings
from ..core.llm import extract_json, get_llm, invoke_llm
from ..schemas import InterviewTips

log = logging.getLogger(__name__)

TIPS_PROMPT = """You are a career coach preparing a candidate for a "{role}" interview.
Their current focus areas (skills they're learning or missing) are: {topics}.

Return ONLY JSON:
{{"focus_topics": ["...", "..."],
  "common_questions": ["...", "...", "..."],
  "advice": "one short paragraph of practical interview prep advice"}}
"""


def _fallback_tips(role: str, focus_topics: list[str]) -> InterviewTips:
    top = focus_topics[:3]
    questions = [f"Walk me through your experience with {t}." for t in top]
    questions.append("Describe a challenging technical problem you solved recently.")
    questions.append(f"Why are you interested in a {role} role?")
    advice = (
        f"Review the fundamentals of {', '.join(top) if top else role} before your "
        "interview, and prepare one concrete project story for each."
    )
    return InterviewTips(role=role, focus_topics=focus_topics, common_questions=questions, advice=advice)


def generate_interview_tips(role: str, focus_topics: list[str]) -> tuple[InterviewTips, list[str]]:
    notes: list[str] = []
    fallback = _fallback_tips(role, focus_topics)
    try:
        llm = get_llm(get_settings().fast_model)
        response = invoke_llm(llm, TIPS_PROMPT.format(role=role, topics=", ".join(focus_topics) or role))
        data = extract_json(response.content)
        if isinstance(data, dict) and data.get("common_questions") and data.get("advice"):
            return InterviewTips(
                role=role,
                focus_topics=[str(t) for t in data.get("focus_topics", focus_topics)],
                common_questions=[str(q) for q in data["common_questions"]],
                advice=str(data["advice"]),
            ), notes
        notes.append("Interview tips agent returned invalid format; showing generic tips.")
    except Exception as e:
        log.warning("interview tips LLM failed: %s", e)
        notes.append("Interview tips generated without the LLM.")
    return fallback, notes
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_interview_agent.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 6: Wire the endpoint**

In `backend/app/main.py`:

1. Add `import json` to the top import block (alongside the existing `import logging` / `import re` / `import io`).
2. Add `InterviewTips` to the existing schemas import line:

```python
from .schemas import AdviseRequest, AdvisorResult, UserCreate, Token, RepoChatRequest, RepoChatResponse, JobRecommendation, InterviewTips
```

3. Add the endpoint immediately after the existing `get_job_recommendations` endpoint:

```python
@app.get("/api/interview-tips", response_model=InterviewTips)
def get_interview_tips(db: Session = Depends(get_db),
                       current_user: models.User = Depends(get_current_user)):
    from .agents.interview_agent import generate_interview_tips
    journey = crud.get_most_recent_journey(db, current_user.id)
    if not journey:
        raise HTTPException(404, "Generate a learning path first to get interview tips.")
    focus_topics = []
    if journey.gap_report_json:
        try:
            gaps = json.loads(journey.gap_report_json).get("gaps", [])
            focus_topics = [g["name"] for g in gaps[:5]]
        except (ValueError, KeyError):
            pass
    tips, _notes = generate_interview_tips(journey.target_role, focus_topics)
    return tips
```

- [ ] **Step 7: Run the full backend test suite**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS (this task added a new agent/endpoint; nothing existing changed behavior).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/agents/interview_agent.py backend/tests/test_interview_agent.py backend/app/main.py
git commit -m "feat(backend): add interview tips agent and GET /api/interview-tips"
```

---

### Task 2: `PathGraph.tsx` zigzag spine

**Files:**
- Modify: `frontend/src/components/PathGraph.tsx`
- Test: `frontend/src/components/PathGraph.test.tsx`

**Interfaces:**
- Consumes: `LearningPath` from `../api/types` (existing, unchanged).
- Produces: `PathGraph({ path }: { path: LearningPath | null })` — same prop signature as today, so `Results.tsx` (Task 3) needs no change to how it calls `<PathGraph path={result.path} />`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/PathGraph.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import PathGraph from './PathGraph'
import type { LearningPath } from '../api/types'

function makePath(stepCount: number): LearningPath {
  return {
    target_role: 'Cybersecurity Analyst',
    total_weeks: stepCount * 2,
    rationale: 'test path',
    steps: Array.from({ length: stepCount }, (_, i) => ({
      order: i + 1, skill_id: `skill-${i}`, skill_name: `Skill ${i + 1}`,
      objective: 'obj', resources: [], estimated_weeks: 2, milestone: 'ms',
    })),
  }
}

describe('PathGraph', () => {
  it('renders nothing when there is no path', () => {
    const { container } = render(<PathGraph path={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders one node per step with its order and weeks', () => {
    render(<PathGraph path={makePath(3)} />)
    expect(screen.getByText(/1\. Skill 1/)).toBeInTheDocument()
    expect(screen.getByText(/3\. Skill 3/)).toBeInTheDocument()
    expect(screen.getAllByText('2 weeks')).toHaveLength(3)
  })

  it('sizes the canvas to the step count instead of a fixed height', () => {
    const { container: three } = render(<PathGraph path={makePath(3)} />)
    const { container: nine } = render(<PathGraph path={makePath(9)} />)
    const threeHeight = (three.querySelector('.rf-canvas') as HTMLElement).style.height
    const nineHeight = (nine.querySelector('.rf-canvas') as HTMLElement).style.height
    expect(parseInt(nineHeight)).toBeGreaterThan(parseInt(threeHeight))
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- PathGraph.test.tsx`
Expected: FAIL — no `.rf-canvas` element exists yet, and node styling doesn't alternate left/right (the third test fails first since the current code always uses a fixed 600px panel, not a step-count-driven height).

- [ ] **Step 3: Implement the zigzag spine**

Replace the full contents of `frontend/src/components/PathGraph.tsx` with:

```tsx
import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import type { LearningPath } from '../api/types'

const NODE_TYPES = {}
const EDGE_TYPES = {}

const ROW_HEIGHT = 130
const TOP_PADDING = 60
const LEFT_X = 40
const RIGHT_X = 340
const NODE_WIDTH = 250

export default function PathGraph({ path }: { path: LearningPath | null }) {
  const { nodes, edges, canvasHeight } = useMemo(() => {
    if (!path || !path.steps) return { nodes: [] as Node[], edges: [] as Edge[], canvasHeight: 0 }

    const newNodes: Node[] = path.steps.map((step, i) => ({
      id: step.skill_id,
      position: { x: i % 2 === 0 ? LEFT_X : RIGHT_X, y: i * ROW_HEIGHT + TOP_PADDING },
      data: {
        label: (
          <div style={{ padding: '10px', textAlign: 'center' }}>
            <strong>{step.order}. {step.skill_name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#b8461f', marginTop: '4px', fontWeight: 600 }}>
              {step.estimated_weeks} weeks
            </div>
          </div>
        ),
      },
      style: {
        background: '#ffffff', color: '#241d12', border: '1.5px solid #241d12',
        borderRadius: '10px', width: NODE_WIDTH, boxShadow: '2px 2px 0 rgba(36,29,18,0.08)',
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

    // Sized to the content — fitView only needs to center it, never shrink
    // nodes below a readable size the way a fixed-height box forced it to.
    const canvasHeight = path.steps.length * ROW_HEIGHT + TOP_PADDING * 2

    return { nodes: newNodes, edges: newEdges, canvasHeight }
  }, [path])

  if (!path) return null

  return (
    <div className="panel" style={{ padding: 0 }}>
      <div style={{ padding: '20px', borderBottom: '1px solid #e8dcc4', background: 'var(--panel-bg)' }}>
        <h2 style={{ margin: 0 }}>Interactive Learning Path ({path.total_weeks} weeks)</h2>
        <p className="hint" style={{ margin: 0 }}>{path.rationale}</p>
      </div>
      <div className="rf-canvas" style={{ width: '100%', height: `${canvasHeight}px` }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
          <Background color="#e8dcc4" gap={16} />
          <Controls style={{ background: '#241d12', fill: '#fbf5ea' }} />
        </ReactFlow>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- PathGraph.test.tsx`
Expected: all 3 tests PASS.

- [ ] **Step 5: Run typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both succeed with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/PathGraph.tsx frontend/src/components/PathGraph.test.tsx
git commit -m "feat(frontend): redesign PathGraph as a roadmap.sh-style zigzag spine"
```

---

### Task 3: Results page restructuring + Recommended Jobs + Interview Tips

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/api/interview.ts`
- Modify: `frontend/src/components/Results.tsx`
- Test: `frontend/src/components/Results.test.tsx`

**Interfaces:**
- Consumes: `useJobRecommendations()` from `../api/jobs` (existing, unchanged); `GET /api/interview-tips` (Task 1); `PathGraph` (Task 2, unchanged prop signature).
- Produces: `useInterviewTips()` hook (`app.api.interview`); `Results({ result, onRestart })` keeps its exact existing prop signature — nothing outside this file needs to change to keep using it.

- [ ] **Step 1: Add the `InterviewTips` frontend type**

In `frontend/src/api/types.ts`, append after the existing `JobRecommendation` interface:

```ts
export interface InterviewTips {
  role: string
  focus_topics: string[]
  common_questions: string[]
  advice: string
}
```

- [ ] **Step 2: Add the `useInterviewTips` hook**

Create `frontend/src/api/interview.ts`:

```ts
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { InterviewTips } from './types'

export function useInterviewTips() {
  return useQuery({
    queryKey: ['interview-tips'],
    queryFn: () => apiRequest<InterviewTips>('/api/interview-tips'),
    retry: false,
  })
}
```

- [ ] **Step 3: Write the failing test for the new sections and layout**

Create `frontend/src/components/Results.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Results from './Results'
import type { AdvisorResult } from '../api/types'

const RESULT: AdvisorResult = {
  profile: { raw_text: 'x', skills: [], education: '', interests: [], hours_per_week: 10, target_role: 'Data Engineer' },
  demand: { target_role: 'Data Engineer', postings_analysed: 0, skills: [] },
  gap_report: { target_role: 'Data Engineer', gaps: [], strengths: [] },
  path: null,
  critique: null,
  resume_review: null,
  revisions_used: 0,
  notes: [],
}

function renderResults() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Results result={RESULT} onRestart={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// Results renders both RecommendedJobsView and InterviewTipsView at once,
// so every test's mock must answer BOTH endpoints correctly — a single
// blanket mockResolvedValue would hand the jobs array to useInterviewTips()
// too, and InterviewTipsView would crash calling .map on the missing
// focus_topics field. Route by URL instead, with sane defaults for
// whichever endpoint a given test isn't focused on.
function mockBothEndpoints(overrides: { jobs?: Response; tips?: Response } = {}) {
  const defaultJobs = { ok: true, status: 200, json: async () => ([]) } as Response
  const defaultTips = {
    ok: true, status: 200,
    json: async () => ({ role: 'Data Engineer', focus_topics: [], common_questions: [], advice: '' }),
  } as Response
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/api/jobs/recommendations')) return Promise.resolve(overrides.jobs ?? defaultJobs)
    if (url.includes('/api/interview-tips')) return Promise.resolve(overrides.tips ?? defaultTips)
    throw new Error(`unexpected fetch in test: ${url}`)
  }))
}

describe('Results', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('renders recommended jobs once the job-recommendations request resolves', async () => {
    mockBothEndpoints({
      jobs: {
        ok: true, status: 200,
        json: async () => ([
          { posting_id: 'job-a', title: 'Data Engineer', company: 'Acme', location: 'Remote',
            url: 'https://example.com/job-a', score: 0.7, matched_skills: ['Python'] },
        ]),
      } as Response,
    })

    renderResults()

    await waitFor(() => expect(screen.getByText(/Data Engineer — Acme/)).toBeInTheDocument())
  })

  it('renders interview tips once the interview-tips request resolves', async () => {
    mockBothEndpoints({
      tips: {
        ok: true, status: 200,
        json: async () => ({
          role: 'Data Engineer', focus_topics: ['ETL / Data Pipelines'],
          common_questions: ['Describe an ETL pipeline you built.'],
          advice: 'Review ETL fundamentals before your interview.',
        }),
      } as Response,
    })

    renderResults()

    await waitFor(() => expect(screen.getByText('Describe an ETL pipeline you built.')).toBeInTheDocument())
    expect(screen.getByText('Review ETL fundamentals before your interview.')).toBeInTheDocument()
  })

  it('shows a quiet note instead of an error box when jobs or tips fail to load', async () => {
    const notFound = {
      ok: false, status: 404, statusText: 'Not Found',
      json: async () => ({ detail: 'Generate a learning path first.' }),
    } as Response
    mockBothEndpoints({ jobs: notFound, tips: notFound })

    renderResults()

    await waitFor(() => expect(screen.getByText(/No job matches available/)).toBeInTheDocument())
    expect(screen.getByText(/No interview tips available/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- Results.test.tsx`
Expected: FAIL — no `RecommendedJobsView`/`InterviewTipsView` rendered yet.

- [ ] **Step 5: Restructure `Results.tsx`**

Replace the full contents of `frontend/src/components/Results.tsx` with:

```tsx
import { Link } from 'react-router-dom'
import PathGraph from './PathGraph'
import { useJobRecommendations } from '../api/jobs'
import { useInterviewTips } from '../api/interview'
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

function RecommendedJobsView() {
  const { data: jobs, error } = useJobRecommendations()
  return (
    <div className="panel">
      <h2>Recommended jobs</h2>
      <p className="hint">Real postings ranked against this path's skills.</p>
      {error && <p className="hint">No job matches available for this path yet.</p>}
      {jobs && jobs.length === 0 && <p className="hint">No matching postings found right now.</p>}
      {jobs && jobs.length > 0 && (
        <div className="syllabus">
          {jobs.slice(0, 5).map((job, i) => (
            <div className="syl-row" key={job.posting_id}>
              <div className="syl-num">{i + 1}</div>
              <div>
                <div className="syl-name">{job.title} — {job.company}</div>
                <p className="syl-obj">{job.location}</p>
              </div>
              <div className="weeks">{Math.round(job.score * 100)}%</div>
            </div>
          ))}
        </div>
      )}
      <Link to="/jobs" className="ghost" style={{ textDecoration: 'none', marginTop: '0.75rem', display: 'inline-block' }}>
        See all matches →
      </Link>
    </div>
  )
}

function InterviewTipsView() {
  const { data: tips, error } = useInterviewTips()
  return (
    <div className="panel">
      <h2>Interview tips</h2>
      {error && <p className="hint">No interview tips available for this path yet.</p>}
      {tips && (
        <>
          <div className="skill-list">
            {tips.focus_topics.map((t) => <span key={t} className="tag">{t}</span>)}
          </div>
          <ul className="hint" style={{ marginTop: '0.75rem' }}>
            {tips.common_questions.map((q, i) => <li key={i}>{q}</li>)}
          </ul>
          <p style={{ marginTop: '0.75rem' }}>{tips.advice}</p>
        </>
      )}
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
      <VerifierBadge critique={result.critique} revisions={result.revisions_used} />
      <div className="two-col">
        <ProfileView profile={result.profile} />
        <GapView report={result.gap_report} />
      </div>
      <div className="two-col">
        <DemandChart demand={result.demand} />
        <RecommendedJobsView />
      </div>
      <div className="two-col">
        <ResumeReviewView review={result.resume_review} />
        <InterviewTipsView />
      </div>
      <PathGraph path={result.path} />
      <PathTimeline path={result.path} />
      <button className="ghost" onClick={onRestart}>↺ Start over</button>
    </>
  )
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd frontend && npm run test -- Results.test.tsx`
Expected: all 3 tests PASS.

- [ ] **Step 7: Run the full frontend suite, typecheck, and build**

Run: `cd frontend && npm run typecheck && npm run test && npm run build`
Expected: all pass, including every pre-existing test file — `Results`'s prop signature (`{ result, onRestart }`) is unchanged, so `ResultsStepPage.tsx` (which renders `<Results result={result} onRestart={restart} />`) needs no changes and its existing tests are unaffected.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/interview.ts frontend/src/components/Results.tsx frontend/src/components/Results.test.tsx
git commit -m "feat(frontend): restructure Results into grouped sections, add recommended jobs + interview tips"
```

---

### Task 4: Live verification

**Files:** none (verification only).

**Interfaces:** none.

- [ ] **Step 1: Restart the backend**

Stop any running `uvicorn` process (Windows: `Get-NetTCPConnection -LocalPort 8080` then `Stop-Process -Force` on its `OwningProcess`) and start it fresh so the new endpoint is registered:

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8080`

- [ ] **Step 2: Generate a fresh path and view the Results page**

Through the running frontend, log in, go through `/generate` with any profile and role, and land on `/generate/results`. Confirm:
- The learning path diagram shows nodes alternating left/right of a center line, each sized to fit its text (not shrunk to fit a tiny box).
- The page reads as grouped sections (profile+gaps, demand+jobs, resume review+interview tips side by side) rather than one long stack of identical-width panels.
- The "Recommended jobs" panel shows real postings (or its quiet fallback text if none exist yet).
- The "Interview tips" panel shows focus topics, questions, and advice tied to the real gap skills from this run.

- [ ] **Step 3: Report back**

No commit for this task — confirm to the user that the live check passed (or describe what didn't match, if anything) before considering the plan complete.
