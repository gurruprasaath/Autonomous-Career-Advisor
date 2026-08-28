# Results Page Redesign — Design

## Problem

Three related complaints about the `/generate/results` page:

1. `PathGraph.tsx`'s reactflow diagram forces every step into a fixed 600px box via `fitView`, so the more steps a path has, the more every node shrinks to fit — the exact cramped, unreadable-boxes look reported live.
2. The rest of the page is a straight stack of full-width panels (profile, gaps, resume review, market demand, verifier, graph, syllabus) — reported as "feels very linear."
3. The page never shows what jobs the generated path could actually land, or how to prepare for an interview for the target role — both already-live capabilities elsewhere in the app (`/jobs`) or straightforward to add, just not surfaced here.

## Goals

1. Redesign `PathGraph.tsx` as a roadmap.sh-style vertical "zigzag spine" — nodes alternate left/right of a center line, sized to the content instead of auto-shrinking to fit a fixed box. Approved directly against real path data via the visual companion.
2. Restructure the Results page into grouped, varied-width sections instead of a uniform stack: profile+gaps, demand+jobs, and resume-review+interview-tips each become a side-by-side pair; only the graph and the full syllabus stay full width. Approved as a wireframe via the visual companion.
3. Add a "Recommended Jobs" section reusing the existing `useJobRecommendations()` hook and `/api/jobs/recommendations` endpoint — no backend change needed for this part.
4. Add a new "Interview Tips" section backed by a new, small `interview_agent.py` (LLM-primary, deterministic fallback, same pattern as every other agent in this codebase) and a new `GET /api/interview-tips` endpoint.

## Non-goals

- No change to the advisor pipeline itself (`/api/advise` still returns the same `AdvisorResult` shape) — jobs and interview tips are fetched separately by the Results page, exactly like the existing Job Matches page already does, not baked into the advise response.
- No change to `RolePicker`, `AgentTerminal`, `ProfileForm`, or the wizard routing — this is scoped to the results step's rendering only.
- Not adding tabs or a sidebar nav (considered and explicitly rejected in favor of restructuring the single scroll — see design discussion).
- Not touching `GapView`, `ProfileView`, `VerifierBadge`, or `ResumeReviewView`'s internals — only their position/grouping on the page changes.

## Design

### 1. `PathGraph.tsx` — zigzag spine

Approved mockup (Option A, "Zigzag Spine"): a vertical center line; nodes alternate left/right, each connected to the spine by a numbered circle badge sitting on the line itself. Concretely:

- The container height is computed from `path.steps.length` (e.g. `steps.length * 110 + 80`px) instead of a fixed 600px — `fitView` no longer needs to shrink nodes to fit a box that's too small for the content.
- Node `position.x` alternates between two fixed columns (left column, right column) instead of every node sharing `x: 250`; `position.y` still increments per step, same as today.
- Node styling switches from the current dark, translucent glass card to a light card (white background, dark border, subtle drop shadow) matching the editorial palette already used everywhere else in the app (`--panel-bg`, `--primary` terracotta for the order badge and weeks chip) — the current dark-glass look was never part of the app's actual design system, just a leftover from before the editorial redesign.
- The order number moves from inline text (`"1. Skill Name"`) to a small circular badge, positioned on the spine line itself, matching the mockup.
- `Controls`/pan-zoom stay (useful for long paths), but `fitView`'s shrink-to-fit is replaced by the height-driven sizing above so it only needs to center the content, never shrink it below a readable size.

### 2. Results page restructuring

`Results.tsx`'s top-level return changes from a flat sequence of full-width components to:

```
VerifierBadge (unchanged, full width — it's a status strip, not a content panel)
.two-col: ProfileView | GapView                          (unchanged pairing, already exists)
.two-col: DemandChart | RecommendedJobsView (NEW)
.two-col: ResumeReviewView | InterviewTipsView (NEW)
PathGraph (full width — the zigzag spine wants the room)
PathTimeline (full width — the detailed syllabus wants the room)
Restart button
```

No new CSS grid system needed — `.two-col` already exists and is already used for the Profile/Gap pairing today; `RecommendedJobsView` and `InterviewTipsView` are new components using it the same way.

### 3. `RecommendedJobsView` (NEW component in `Results.tsx`)

Calls the **existing** `useJobRecommendations()` hook (`frontend/src/api/jobs.ts`, already implemented and live) directly from `Results.tsx`. Renders the top few matches (cap at 5, since this is now a half-width panel next to the demand chart, not the dedicated `/jobs` page) using the same `.syllabus`/`.syl-row` styling `JobsPage.tsx` already established, with a "See all matches →" link to `/jobs` for the full ranked list. On error (e.g. no journey yet — shouldn't happen here since Results only renders once a journey exists, but the hook could still fail on a provider error) or an empty list, shows a quiet inline note instead of a scary error box, since this is a secondary panel, not the page's main content.

### 4. Interview Tips — new agent, endpoint, and view

**`backend/app/schemas.py`** — new model:

```python
class InterviewTips(BaseModel):
    role: str
    focus_topics: list[str]
    common_questions: list[str]
    advice: str
```

**`backend/app/agents/interview_agent.py`** (new) — same LLM-primary, always-degrades-to-something-useful pattern as `competency_agent.py` and `resource_curator_agent.py` (not `review_agent.py`'s return-None-on-failure pattern, since interview prep advice is safe and useful even generically, unlike a personalized resume critique):

```python
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

**`backend/app/main.py`** — new endpoint, mirroring `get_job_recommendations` exactly:

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

(`main.py` does not currently import `json` at the top — add `import json` alongside its existing `import logging` / `import re` block.)

**Frontend** — `frontend/src/api/types.ts` gains an `InterviewTips` interface matching the schema above; `frontend/src/api/jobs.ts`-adjacent new file `frontend/src/api/interview.ts`:

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

`InterviewTipsView` (new component in `Results.tsx`) calls this hook and renders `focus_topics` as `.tag` chips, `common_questions` as a bullet list, `advice` as a short paragraph — styled consistent with `ResumeReviewView`'s existing card. Loading/error states are quiet (same "secondary panel" treatment as `RecommendedJobsView`, not a blocking error box), since interview tips are a bonus, not the page's core deliverable.

## Testing

- `backend/tests/test_interview_agent.py`: valid-JSON case returns the LLM's tips; malformed/missing-field JSON and an LLM exception both fall through to `_fallback_tips` (never raises), mirroring `test_competency_agent.py`'s coverage style.
- `backend/main.py`'s new endpoint: one test asserting 404 when no journey exists, one asserting the happy path returns `InterviewTips` built from the journey's stored `gap_report_json`.
- Frontend: `RecommendedJobsView`/`InterviewTipsView` get smoke tests (renders data, renders quiet empty/error state) following `JobsPage.test.tsx`'s existing mocking pattern; `PathGraph.tsx`'s height-from-step-count logic gets a unit test on the computed container height for a few step counts.
