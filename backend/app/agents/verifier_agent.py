"""Verifier / Critic Agent — FGCR rubric.

  F  Feasibility   prerequisite order respected in the step sequence
  G  Groundedness  every resource exists in the course catalog and
                   actually teaches that step's skill
  C  Coverage      the top-priority gaps all appear in the path
  R  Realism       week estimates sane per-step and in total

Hard checks are deterministic (they re-verify independently of the
planner). The LLM adds a qualitative pass — pedagogical soundness,
objective quality — and can flag issues the rules cannot. Deterministic
failures cap the corresponding dimension regardless of LLM opinion.
"""
import logging
from urllib.parse import urlparse

from ..config import get_settings
from ..core.llm import LLMUnavailable, extract_json, get_llm, invoke_llm
from ..core.taxonomy import load_taxonomy
from ..core.vectorstore import courses_collection
from ..schemas import FGCRCritique, GapReport, LearningPath, StudentProfile

log = logging.getLogger(__name__)

COVERAGE_TOP_N = 5
MAX_TOTAL_WEEKS = 40

CRITIQUE_PROMPT = """You are a strict reviewer of learning paths for a career-advisor system. Score this path for a student targeting "{role}" ({hours} h/week available).

Rubric — score each 1-5 (5 = excellent):
- feasibility: is the ordering pedagogically sensible beyond mere prerequisites?
- groundedness: do objectives/milestones stay concrete and tied to the listed resources?
- coverage: does the path address the student's most important gaps (listed below)?
- realism: are the week estimates believable at {hours} h/week?

Top gaps (priority order): {gaps}

Path:
{path_json}

Return ONLY JSON:
{{"feasibility": <1-5>, "groundedness": <1-5>, "coverage": <1-5>, "realism": <1-5>,
  "issues": ["..."], "revision_request": "<specific fix instructions, or empty string if acceptable>"}}
"""


def _hard_checks(path: LearningPath, gap_report: GapReport,
                 profile: StudentProfile) -> tuple[dict[str, float], list[str]]:
    """Deterministic score caps per dimension + issues found."""
    caps = {"feasibility": 5.0, "groundedness": 5.0, "coverage": 5.0, "realism": 5.0}
    issues: list[str] = []
    taxonomy = load_taxonomy()

    # F: prerequisites must come before dependants within the path
    position = {s.skill_id: s.order for s in path.steps}
    for step in path.steps:
        for pre in taxonomy[step.skill_id].prerequisites if step.skill_id in taxonomy else []:
            if pre in position and position[pre] > step.order:
                caps["feasibility"] = 2.0
                issues.append(f"'{taxonomy[pre].name}' must come before '{step.skill_name}'.")

    # G: resources must exist in the catalog and teach the right skill
    catalog = courses_collection().get()
    catalog_skill = dict(zip(catalog["ids"], [m["skill_id"] for m in catalog["metadatas"]]))
    for step in path.steps:
        if not step.resources:
            caps["groundedness"] = min(caps["groundedness"], 3.0)
            issues.append(f"No resources attached for '{step.skill_name}'.")
        for r in step.resources:
            if catalog_skill.get(r.course_id) != step.skill_id and urlparse(r.url).hostname != "www.youtube.com":
                caps["groundedness"] = 1.0
                issues.append(f"Resource '{r.title}' is not a catalog course for "
                              f"'{step.skill_name}' (possible hallucination).")

    # C: top-priority gaps must be covered
    top = [g for g in gap_report.gaps[:COVERAGE_TOP_N]]
    missing = [g.name for g in top if g.skill_id not in position]
    if missing:
        caps["coverage"] = 2.0
        issues.append("Path misses top-priority gaps: " + ", ".join(missing))

    # R: sane durations
    for step in path.steps:
        if not 0.5 <= step.estimated_weeks <= 8:
            caps["realism"] = min(caps["realism"], 2.0)
            issues.append(f"Unrealistic duration for '{step.skill_name}': "
                          f"{step.estimated_weeks} weeks.")
    if path.total_weeks > MAX_TOTAL_WEEKS:
        caps["realism"] = min(caps["realism"], 3.0)
        issues.append(f"Total {path.total_weeks} weeks exceeds {MAX_TOTAL_WEEKS}-week horizon.")

    return caps, issues


def verify_path(path: LearningPath, gap_report: GapReport,
                profile: StudentProfile) -> tuple[FGCRCritique, list[str]]:
    notes: list[str] = []
    caps, hard_issues = _hard_checks(path, gap_report, profile)

    scores = dict(caps)  # default: deterministic result stands alone
    llm_issues: list[str] = []
    revision_request = ""
    try:
        llm = get_llm(get_settings().planner_model)
        response = invoke_llm(llm, CRITIQUE_PROMPT.format(
            role=path.target_role, hours=profile.hours_per_week,
            gaps=", ".join(f"{g.name} (p={g.priority})" for g in gap_report.gaps[:COVERAGE_TOP_N]),
            path_json=path.model_dump_json(indent=1),
        ))
        data = extract_json(response.content)
        for dim in scores:
            try:
                llm_score = float(data.get(dim, scores[dim]))
            except (TypeError, ValueError):
                llm_score = scores[dim]
            # deterministic failures cap the LLM's opinion
            scores[dim] = min(max(1.0, llm_score), caps[dim])
        llm_issues = [str(i) for i in data.get("issues", [])][:6]
        revision_request = str(data.get("revision_request", ""))
    except LLMUnavailable as e:
        notes.append(f"Verifier ran WITHOUT the LLM (rule checks only): {e}")
    except Exception as e:
        log.warning("verifier LLM failed: %s", e)
        notes.append(f"Verifier LLM failed ({type(e).__name__}); rule checks only.")

    issues = hard_issues + [i for i in llm_issues if i not in hard_issues]
    if hard_issues and not revision_request:
        revision_request = "Fix these verified problems: " + " ".join(hard_issues)

    mean = sum(scores.values()) / 4
    passed = mean >= get_settings().verifier_pass_threshold and not hard_issues
    critique = FGCRCritique(
        feasibility=scores["feasibility"], groundedness=scores["groundedness"],
        coverage=scores["coverage"], realism=scores["realism"],
        passed=passed, issues=issues,
        revision_request="" if passed else revision_request,
    )
    return critique, notes
