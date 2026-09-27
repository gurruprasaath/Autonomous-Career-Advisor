# Sub-topic Skill Model (Roadmap Overhaul R1) — Design

**Status:** approved in brainstorming, 2026-09-27
**Roadmap:** first build piece of the roadmap overhaul (R1 sub-topic skill model, incl. R0 roadmap.sh
links → R2 profile-driven personalization → R3 per-sub-topic resources → R4 roadmap-style visual),
taking priority over the SkillMeet-parity list (next there: C JD Analyzer).

## Problem

The user rated current learning paths as too shallow, too generic/static, missing skills, weak on
resources, and visually poor. Root causes in code:

- `planner_agent.build_path` emits **one step per gap skill** (max 8) with a single LLM-written
  objective — there is no finer-grained curriculum to draw on.
- `skills_taxonomy.json` has only **78 flat skills**; anything else in a job posting is invisible to
  the market scan and gap analysis.
- Two learners with the same target role get near-identical steps.

R1 fixes depth and coverage and makes each step's sub-topics depend on the learner's current level,
within the required level the market scan reports (see "Known limitations" — with the live provider
that required level is always `intermediate`, so the level-dependence in practice is a two-value
window, not the full beginner→advanced range). Per-sub-topic progress and adaptive re-planning (R2),
new resource sources (R3) and the new visual (R4) are out of scope.

## Licensing constraint (decided)

roadmap.sh content may not be republished without the author's consent (its license forbids use
"in any form" beyond personal use and links). R1 therefore uses only:

| Source | License | Used for |
|---|---|---|
| ESCO (European Skills taxonomy) — API `https://ec.europa.eu/esco/api` | CC BY 4.0 | occupation → essential/optional skills (taxonomy expansion candidates) |
| OSSU Computer Science | MIT | CS-fundamentals topic ordering reference |
| Coding Interview University | CC BY-SA 4.0 | DSA sub-topic ordering reference |
| Microsoft Learn Catalog API — `https://learn.microsoft.com/api/catalog/` | public API for third-party use | module/unit titles as sub-topic reference |
| roadmap.sh | links only (allowed) | one "See on roadmap.sh" URL per skill where a page exists |

Sub-topic *names* are generic technical topic labels (e.g. "Async & concurrency"); no descriptive
text is copied from any source.

## Components

### 1. `backend/app/data/skill_subtopics.json` (new data file)

```json
{
  "version": 1,
  "provenance": "Drafted with LLM assistance using the references listed per skill; reviewed by the project team.",
  "sources": [
    {"id": "esco", "name": "ESCO", "license": "CC BY 4.0", "url": "https://esco.ec.europa.eu",
     "attribution": "ESCO classification, European Commission, CC BY 4.0"},
    {"id": "ossu", "name": "OSSU Computer Science", "license": "MIT", "url": "https://github.com/ossu/computer-science",
     "attribution": "Open Source Society University, Computer Science curriculum, MIT License"},
    {"id": "ciu", "name": "Coding Interview University", "license": "CC BY-SA 4.0", "url": "https://github.com/jwasham/coding-interview-university",
     "attribution": "John Washam, Coding Interview University, CC BY-SA 4.0"},
    {"id": "mslearn", "name": "Microsoft Learn", "license": "Microsoft Learn Catalog API", "url": "https://learn.microsoft.com/training/",
     "attribution": "Microsoft Learn training catalog (topic references only)"}
  ],
  "skills": {
    "python": {
      "roadmap_url": "https://roadmap.sh/python",
      "references": ["mslearn", "ossu"],
      "subtopics": [
        {"id": "python-syntax-types", "name": "Syntax & core data types", "level": "beginner"},
        {"id": "python-control-functions", "name": "Control flow & functions", "level": "beginner"},
        {"id": "python-oop", "name": "Object-oriented programming", "level": "intermediate"}
      ]
    }
  }
}
```

Rules (enforced by a validator test):
- Every taxonomy skill id has an entry; no entry for an unknown skill id.
- 4–8 sub-topics per skill; each sub-topic id is globally unique, kebab-case, and prefixed with its
  skill id; `level` ∈ {beginner, intermediate, advanced}.
- Sub-topics are ordered by learning sequence and their levels are non-decreasing
  (beginners first).
- Every skill has at least one beginner and at least one sub-topic at intermediate or advanced.
- `references` ⊆ source ids; `roadmap_url` is `""` or starts with `https://roadmap.sh/`
  (each non-empty URL verified live once, returning HTTP 200, when authored).

Loaded via `core/taxonomy.py` with `@lru_cache` (same pattern as `load_taxonomy`), exposing
`subtopics_for(skill_id) -> list[Subtopic]` and `roadmap_url_for(skill_id) -> str`.

### 2. Taxonomy expansion (missing skills)

A one-off, committed, re-runnable research script `backend/scripts/find_missing_skills.py`:
1. For each of the app's roles (`get_job_provider().available_roles()`), fetch live postings with the
   configured provider (JobSpy, up to 100 per role).
2. Candidates = (a) ESCO essential + optional skills of the closest ESCO occupation per role — each
   app role is hand-mapped to an ESCO occupation URI (`ESCO_OCCUPATIONS` in the script) because
   free-text `/search?type=occupation` matched unrelated occupations (e.g. "Full-Stack Developer" →
   "property developer"); the mapped URI is then resolved via `/resource/occupation` — plus (b)
   technology terms extracted by the LLM from a sample of 30 postings per role.
3. Drop candidates that `match_mention` already maps to an existing skill (confidence ≥ 0.6).
4. For each remaining candidate, count whole-word mentions (case-insensitive) across that role's
   postings. **Keep a candidate if it appears in ≥ 3% of postings for at least one role.**
5. Write the evidence table (candidate, source, per-role frequency, ESCO URI if any) to
   `docs/research/2026-09-taxonomy-expansion.md`.

Kept candidates are added to `skills_taxonomy.json` (id, name, aliases, category, prerequisites —
existing schema) and to `skill_subtopics.json`. The research doc is the citable evidence for the
paper. The script is not run by the app.

### 3. Schemas and planner

- `schemas.py`: new `Subtopic(id: str, name: str, level: Literal["beginner","intermediate","advanced"])`;
  `PathStep` gains `subtopics: list[Subtopic] = []` and `roadmap_url: str = ""`.
- Level window (pure function in `core/taxonomy.py`):
  `select_subtopics(skill_id, current_level, required_level) -> list[Subtopic]` with ranks
  none=0, beginner=1, intermediate=2, advanced=3:
  1. keep sub-topics with `rank(current) < rank(level) ≤ rank(required)`, in file order;
  2. if that is empty, keep those with `level == required_level`;
  3. if still empty, keep all sub-topics for the skill.
- `build_path`:
  - attaches `select_subtopics(...)` and `roadmap_url_for(...)` to each step;
  - adds the selected sub-topic names to each skill line in `PLAN_PROMPT` and instructs the LLM that
    the objective and milestone must cover those sub-topics;
  - fallback week estimate becomes
    `max(n_subtopics, 1) * WEEKS_PER_SUBTOPIC * (10 / hours_per_week)` with `WEEKS_PER_SUBTOPIC = 0.75`,
    clamped to 0.5–8 (the max() guards the zero-sub-topic case, which the curated data makes unreachable) (the LLM estimate is still used when it is within 0.5–8).
- `MAX_PATH_SKILLS` stays 8.

### 4. Verifier

New deterministic check in `verifier_agent._hard_checks`: for each step, every sub-topic id must be
in `subtopics_for(step.skill_id)`; otherwise cap **groundedness at 1.0** and add an issue
"Sub-topic '<name>' is not in the curated curriculum for <skill>". (Planner-generated paths always
pass; the check guards against future regressions and makes the "nothing invented" claim true for
sub-topics as it already is for resources.)

### 5. Storage and API

- `path_steps.subtopics_json TEXT` and `path_steps.roadmap_url VARCHAR` — models + additive ALTERs in
  `run_migrations()`; `crud.create_path_steps` writes them.
- `GET /api/tracker/journeys` returns `subtopics` (parsed list) and `roadmap_url` per step. Journeys
  created before R1 return `[]` / `""`.
- `/api/advise` response carries them through `PathStep`.

### 6. Frontend

- Types: `Subtopic`, and `subtopics` / `roadmap_url` on `PathStep` and `TrackerStep`.
- `Results` path step cards and `TrackerPage` steps show an ordered sub-topic list with a small level
  tag, and a "See on roadmap.sh ↗" link when `roadmap_url` is non-empty.
- The attribution line "Sub-topics drafted with LLM assistance and reviewed by the authors; some
  skills cross-checked against ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA
  4.0) and Microsoft Learn." appears under the learning path.

## Out of scope (deliberate)

- Per-sub-topic progress, completion and adaptive re-planning — R2.
- New resource sources per sub-topic — R3 (resources stay per skill).
- New graph visual — R4 (`PathGraph` unchanged).
- Adding new target roles.

## Known limitations

- With the live JobSpy provider, `market_agent.py::_scan_description` labels every skill it detects
  in a posting `"intermediate"` (there's no signal in a free-text description to distinguish
  beginner/intermediate/advanced demand), so `required_level` computed from live postings is always
  `intermediate`. A learner's `select_subtopics` window is therefore either beginner+intermediate
  (when `current_level == "none"`) or intermediate-only (when `current_level == "beginner"`) —
  `advanced` sub-topics are only reachable with the annotated sample job provider, which does carry
  per-skill levels.
- `recalculate_journey` rebuilds the path from the stored gap report's `current_level`, so
  reassessing a learner's competency (e.g. via GitHub/LeetCode analysis) does not move this window
  unless a fresh `/api/advise` run also produces a new gap report.

  Both are deferred to R2: seniority-aware required levels for the live provider, and mapping a
  reassessed depth score back onto `current_level` so recalculation can widen the window.

## Testing

- `test_subtopics_data.py`: validator for every rule in §1 against the real data file, plus
  coverage of every taxonomy skill.
- `select_subtopics` unit tests for each window case and both fallbacks.
- Planner test (LLM patched) that steps carry sub-topics and roadmap URLs, and that the fallback
  week estimate follows the formula.
- Verifier test: a step with an unknown sub-topic id caps groundedness at 1.0.
- Storage round-trip (migration adds columns; `create_path_steps` writes; journeys endpoint reads).
- Frontend tests: step cards render sub-topics, level tags and the roadmap link; no link when empty.
- Live end-to-end: one real `/api/advise` run showing sub-topics in the result and in the Tracker UI.
