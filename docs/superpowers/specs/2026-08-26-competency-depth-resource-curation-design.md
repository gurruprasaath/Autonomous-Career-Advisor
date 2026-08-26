# Competency-Aware Depth Assessment + Resource Curation — Design

## Problem

Two compounding issues make the app's core output feel arbitrary:

1. **Resources are fake.** `backend/app/providers/youtube.py` has no `YOUTUBE_API_KEY` configured anywhere in this project, so every "tutorial" recommendation silently falls back to a mock (`"Sample Video for {query}"` linking to a placeholder video). Whatever the depth logic does, the resources it points to aren't real.
2. **Depth is a one-shot guess.** `depth_score` (1-10) is extracted once from the resume text by the Profile Agent and never revisited, even though the app already tracks quiz scores, self-reported confidence, and GitHub language evidence per skill (built in the prior "Adaptive Tracking" feature). None of that real, earned evidence ever updates the number that actually drives resource selection.

## Research framing

This project's own base-paper analysis (`Career_Advisor_Project_Analysis.docx`) identifies "learner-profile matching" as GenMentor's weakest-rated component and calls for "a structured, taxonomy-anchored student profile with explicit mastery levels" as this project's opportunity. Continuous, evidence-based competency reassessment — not a static one-shot guess — is a direct, citable answer to that named gap. The depth-scoring methodology below is therefore kept deterministic and explicit (a stated equation with justified weights), not an opaque LLM judgment, so it can be described and reproduced in a paper's methods section.

## Goals

1. Real resources: wire up a real YouTube Data API key; stop silently degrading to a mock.
2. Replace the one-shot depth guess with a **Competency Assessment Agent** that recomputes `depth_score` per skill from every signal actually available (resume prior, quiz score, confidence rating, GitHub evidence), with a written rationale.
3. Replace blind first-k resource selection with a **Resource Curator Agent** that retrieves real candidates and has an LLM pick + justify the best ones for the specific objective and assessed depth — never inventing a resource, same rule the Planner already follows for courses.
4. Track depth **over time**, per skill, per learner (not per journey) — an append-only history with a chart, so growth is visible and evidenced, not just a current number.

## Non-goals

- No manual "reassess now" button outside the existing recalculate flow — competency reassessment only runs where tracking signals actually change (recalculate) or get created for the first time (initial `/api/advise`).
- No new resource providers beyond YouTube + the existing course catalog.
- No change to what the Profile Agent extracts from the resume itself — `resume_depth` stays exactly as it is today; this design only adds what happens to it *afterward*.

## Competency Assessment Agent (new: `backend/app/agents/competency_agent.py`)

### Inputs, per skill

| Signal | Source | Availability |
|---|---|---|
| `resume_depth` (1-10) | `StudentProfile.skills[].depth_score`, existing Profile Agent output | Always |
| `quiz_score` (0-100) | `PathStep.quiz_score` for that skill's tracked step(s) | Only after a quiz is taken |
| `confidence_rating` (1-5) | `PathStep.confidence_rating` | Only after self-rated |
| `github_evidence` (bool) | `crud.get_github_evidence_by_skill` — at least one repo in that skill's language with `last_pushed_at` within 180 days of the assessment | Only after GitHub sync |

### Formula

```
if no tracking signal (quiz_score, confidence_rating, github_evidence) exists yet for this skill:
    depth_score = resume_depth                      # unchanged — identical to today's behavior

else:
    components = [(resume_depth, 0.30)]              # prior: least reliable long-term, still informative
    if quiz_score is not None:
        components.append((quiz_score / 10, 0.40))    # most objective signal — a real, graded check
    if confidence_rating is not None:
        components.append((confidence_rating * 2, 0.15))  # weakest signal — self-report, low weight
    # weights renormalized to sum to 1 over only the components present
    base = weighted_average(components)
    if github_evidence:
        base = min(10, base + 1.5)                    # practice bonus, not blended — it's evidence of
                                                        # doing, not a graded score, so additive not averaged
    depth_score = round(clamp(base, 1, 10))
```

Weight reasoning (for the paper's methods section): quiz score is weighted highest because it's the only signal that directly tests understanding under a consistent rubric; the resume prior is weighted second because it's the sole signal available before any tracking exists and shouldn't be discarded once other signals arrive; confidence is weighted lowest because self-report is the least reliable predictor of actual competence; GitHub evidence is treated as a bonus rather than blended into the average because presence of a recent repo is binary proof-of-practice, not a graded measurement, and forcing it into a weighted average would imply a precision it doesn't have.

### Rationale

A one-sentence LLM-written explanation citing which signals moved the score (e.g. "Depth raised to 7/10 — quiz score 85% and a recent repo in Python"). Degrades to a template sentence assembled from the same inputs if the LLM is unavailable — same graceful-degradation pattern every other agent in this codebase follows.

### Where it runs

Inside `recalculate_journey` (`backend/app/main.py`), replacing the current `StudentSkill(depth_score=_LEVEL_TO_DEPTH.get(...))` reconstruction with a real per-skill call into this agent, pulling quiz/confidence from that journey's `PathStep` rows and GitHub evidence via the existing `crud.get_github_evidence_by_skill`. Also runs once at initial `/api/advise` time to write the very first `CompetencyHistory` row per skill (resume-only, no tracking signals yet — identical output to today, just persisted as history point #1 for later comparison).

## Resource Curator Agent (new: `backend/app/agents/resource_curator_agent.py`)

Replaces `planner_agent.py`'s `_courses_for()`.

1. **Retrieve** real candidates: catalog courses for the skill (existing Chroma query, unchanged) + real YouTube results (once a real API key is configured) at the depth-appropriate level (`beginner`/`intermediate`/`advanced` derived from the assessed `depth_score`, same thresholds `_courses_for` already uses: `<4` / `<8` / else).
2. **Curate**: one LLM call given the objective, assessed depth, and the retrieved candidate list picks the best 2 and writes a one-line "why this fits" justification per pick.
3. **Validate**: any pick that doesn't match a real candidate id from step 1 is dropped — mirrors the Quiz Agent's malformed-output filtering. If validation leaves zero picks, or the LLM is unavailable, fall back to today's deterministic first-k behavior.

## Depth-over-time tracking

### New table: `CompetencyHistory`

`id, user_id, skill_id, depth_score, quiz_score (nullable), confidence_rating (nullable), has_github_evidence (bool), rationale, recorded_at`

Keyed by `user_id` + `skill_id`, not `journey_id` — skill growth belongs to the learner, not to one job-role path, so switching target roles later doesn't fragment a skill's history into disconnected series.

**Written at two points:**
1. Initial `/api/advise` — one row per skill in `StudentProfile.skills` (every skill the Profile Agent extracted, including ones that already meet market demand and never get a path step — a learner's competency model is about everything they know, not only their gaps). Resume-only signals at this point.
2. Every `recalculate_journey` call — one row per skill in the regenerated gap set (the skills that actually got reassessed), reflecting whatever tracking signals now exist.

### New endpoint

`GET /api/tracker/competency-history` (auth required) → `{skill_id: [{depth_score, recorded_at, rationale}, ...]}` for the logged-in user, ordered by `recorded_at`.

### Frontend

A small hand-rolled SVG line chart component (no new npm dependency — consistent with how `PathGraph` already does custom rendering in this app) added to the tracker page: depth_score (1-10) on the Y axis, `recorded_at` on the X axis, a skill selector (dropdown) since a learner will have multiple skills' histories.

## Testing

- `competency_agent.py`: pure-function unit tests on the formula (no tracking data → unchanged; quiz-only; quiz+confidence; quiz+confidence+github; weight renormalization when a component is missing) — deterministic, no LLM mocking needed for the score itself. A separate mocked-LLM test for the rationale-generation path, following the Quiz Agent's test pattern.
- `resource_curator_agent.py`: mocked-LLM tests mirroring the Quiz Agent's — valid picks pass through, invented/mismatched candidate ids are dropped, empty valid picks trigger the deterministic fallback.
- `CompetencyHistory` CRUD: real in-memory-SQLite tests (write on advise, write on recalculate, fetch ordered by time) — same pattern as `test_progress.py`.
