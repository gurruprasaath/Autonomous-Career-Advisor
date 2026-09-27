"""Curriculum Planner Agent.

Design principle: the LLM never invents resources. Courses are retrieved
from the catalog per gap skill; step order is fixed deterministically by
prerequisite topology. The LLM contributes what it is good at — writing
learning objectives, milestones, and calibrating week estimates — inside
that verified scaffold.
"""
import logging

from ..config import get_settings
from ..core.llm import LLMUnavailable, extract_json, get_llm, invoke_llm
from ..core.taxonomy import prerequisite_order, roadmap_url_for, select_subtopics
from ..schemas import GapReport, LearningPath, PathResource, PathStep, StudentProfile
from .resource_curator_agent import curate_resources

log = logging.getLogger(__name__)

MAX_PATH_SKILLS = 8
# fallback weeks per curated sub-topic at 10 h/week
WEEKS_PER_SUBTOPIC = 0.75

PLAN_PROMPT = """You are a curriculum planner for a career-advisor system. A student targeting the role "{role}" can study {hours} hours/week.

For each skill below, write (the objective and milestone must cover that skill's listed sub-topics):
- "objective": one concrete, measurable learning objective (what they can DO afterwards)
- "milestone": a small verifiable deliverable (e.g., "build and deploy X", "solve N problems")
- "estimated_weeks": realistic weeks at {hours} h/week given the gap shown (0.5 to 8 per skill)

Guidelines:
- For 'REST API Design', avoid duplicating Node.js basic CRUD; focus on deeper API concepts like OpenAPI specs, versioning, or security.
- For 'Software Testing', assign at least 3 weeks to ensure sufficient time for 80% full-stack coverage.
- For 'Authentication & Authorization', the milestone should explicitly involve a concrete implementation tutorial (e.g., Auth0 or Firebase quickstart).

Skills (in fixed prerequisite order — do NOT reorder):
{skills_block}

{revision_block}
Also write a short "rationale" (2-3 sentences) explaining the ordering and focus of
the path as a whole. Do NOT state a total duration or week count in the rationale —
the exact total is computed separately from your per-step estimates.

Return ONLY JSON:
{{"steps": [{{"skill_id": "...", "objective": "...", "milestone": "...", "estimated_weeks": <number>}}],
  "rationale": "..."}}
"""



def build_path(profile: StudentProfile, gap_report: GapReport,
               revision_request: str = "") -> tuple[LearningPath, list[str]]:
    notes: list[str] = []
    top_gaps = gap_report.gaps[:MAX_PATH_SKILLS]
    if not top_gaps:
        return LearningPath(target_role=gap_report.target_role, steps=[],
                            rationale="No significant skill gaps — the profile already "
                                      "meets market demand for this role."), notes

    gap_by_id = {g.skill_id: g for g in top_gaps}
    ordered_ids = prerequisite_order(list(gap_by_id.keys()))
    subtopics_by_id = {
        sid: select_subtopics(sid, gap_by_id[sid].current_level, gap_by_id[sid].required_level)
        for sid in ordered_ids
    }

    skills_block = "\n".join(
        f"- {gap_by_id[sid].name} (skill_id: {sid}; current: {gap_by_id[sid].current_level}; "
        f"required: {gap_by_id[sid].required_level}; demanded by "
        f"{gap_by_id[sid].demand_share:.0%} of postings; sub-topics: "
        f"{', '.join(t.name for t in subtopics_by_id[sid]) or 'none listed'})"
        for sid in ordered_ids
    )
    revision_block = (
        f"IMPORTANT — a verifier rejected the previous draft. Fix this:\n{revision_request}\n"
        if revision_request else ""
    )

    llm_steps: dict[str, dict] = {}
    rationale = ""
    try:
        llm = get_llm(get_settings().planner_model)
        response = invoke_llm(llm, PLAN_PROMPT.format(
            role=gap_report.target_role, hours=profile.hours_per_week,
            skills_block=skills_block, revision_block=revision_block,
        ))
        data = extract_json(response.content)
        rationale = str(data.get("rationale", ""))
        for step in data.get("steps", []):
            if step.get("skill_id") in gap_by_id:
                llm_steps[step["skill_id"]] = step
    except LLMUnavailable as e:
        notes.append(f"Planner ran WITHOUT the LLM (template objectives): {e}")
    except Exception as e:
        log.warning("planner LLM failed: %s", e)
        notes.append(f"Planner LLM failed ({type(e).__name__}); used template objectives.")

    steps: list[PathStep] = []
    for order, sid in enumerate(ordered_ids, start=1):
        gap = gap_by_id[sid]
        llm_step = llm_steps.get(sid, {})
        try:
            weeks = float(llm_step.get("estimated_weeks", 0)) or 0.0
        except (TypeError, ValueError):
            weeks = 0.0
        subtopics = subtopics_by_id[sid]
        if not 0.5 <= weeks <= 8:
            # deterministic estimate: curated sub-topic count, scaled by study hours
            weeks = round(max(len(subtopics), 1) * WEEKS_PER_SUBTOPIC
                          * (10 / max(profile.hours_per_week, 1)), 1)
            weeks = min(max(weeks, 0.5), 8)
        # Extract depth score if available
        depth_score = 1
        for s in profile.skills:
            if s.skill_id == sid:
                depth_score = getattr(s, 'depth_score', 1)
                break
                
        obj_text = str(llm_step.get("objective", "")) or f"Reach {gap.required_level} level in {gap.name} (demanded by {gap.demand_share:.0%} of {gap_report.target_role} postings)."

        # curate_resources makes one LLM call per step (up to MAX_PATH_SKILLS
        # per plan) where the old first-k selection made zero — a known,
        # accepted latency tradeoff for real curated resources, not a bug.
        steps.append(PathStep(
            order=order, skill_id=sid, skill_name=gap.name,
            objective=obj_text,
            milestone=str(llm_step.get("milestone", ""))
                or f"Complete a hands-on exercise or mini-project using {gap.name}.",
            resources=curate_resources(sid, gap.name, depth_score, obj_text),
            estimated_weeks=weeks,
            subtopics=subtopics,
            roadmap_url=roadmap_url_for(sid),
        ))

    path = LearningPath(
        target_role=gap_report.target_role, steps=steps,
        total_weeks=round(sum(s.estimated_weeks for s in steps), 1),
        rationale=rationale or "Path ordered by prerequisite topology; priorities from "
                               "market demand share × mastery gap.",
    )
    return path, notes
