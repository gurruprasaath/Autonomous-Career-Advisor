import logging
from ..config import get_settings
from ..core.llm import get_llm, invoke_llm

log = logging.getLogger(__name__)

RATIONALE_PROMPT = """You are a Competency Assessor. You just evaluated a student's skill level in "{skill_name}".
The new depth score is {depth_score} out of 10.
The inputs used were:
- Resume prior depth: {resume_depth}/10
- Quiz score: {quiz_str}
- Confidence rating: {conf_str}
- GitHub evidence (recent repo): {github_str}{leetcode_line}

Write exactly ONE short sentence explaining this score change or current state.
Focus on the most impactful signals. Do not explain the math.
Example: "Depth raised to 7/10 due to a strong quiz score (85%) and recent GitHub practice."
"""

# Accepted LeetCode solutions are judged against real test cases, so they rank
# just below a quiz (0.40) as direct evidence, above the resume prior (0.30).
LEETCODE_WEIGHT = 0.35


def assess_competency(skill_name: str, resume_depth: int, quiz_score: int | None,
                      confidence_rating: int | None, github_evidence: bool,
                      leetcode_depth: int | None = None) -> tuple[int, str]:
    if (quiz_score is None and confidence_rating is None and not github_evidence
            and leetcode_depth is None):
        return resume_depth, "Initial assessment based on resume."

    components = [(resume_depth, 0.30)]
    if quiz_score is not None:
        components.append((quiz_score / 10.0, 0.40))
    if confidence_rating is not None:
        components.append((confidence_rating * 2.0, 0.15))
    if leetcode_depth is not None:
        components.append((leetcode_depth, LEETCODE_WEIGHT))

    total_weight = sum(w for _, w in components)
    base = sum(val * w for val, w in components) / total_weight

    if github_evidence:
        base = min(10.0, base + 1.5)

    depth_score = int(round(max(1.0, min(10.0, base))))

    quiz_str = f"{quiz_score}%" if quiz_score is not None else "None"
    conf_str = f"{confidence_rating}/5" if confidence_rating is not None else "None"
    github_str = "Yes" if github_evidence else "No"
    # Only mentioned when present, so rationales for every non-DSA skill are
    # unchanged from before LeetCode evidence existed.
    leetcode_suffix = f", leetcode: {leetcode_depth}/10" if leetcode_depth is not None else ""
    leetcode_line = (f"\n- LeetCode DSA depth: {leetcode_depth}/10"
                     if leetcode_depth is not None else "")

    fallback_rationale = (f"Depth assessed at {depth_score}/10 (resume: {resume_depth}, "
                          f"quiz: {quiz_str}, conf: {conf_str}, github: {github_str}{leetcode_suffix}).")

    try:
        llm = get_llm(get_settings().planner_model)
        prompt = RATIONALE_PROMPT.format(
            skill_name=skill_name, depth_score=depth_score, resume_depth=resume_depth,
            quiz_str=quiz_str, conf_str=conf_str, github_str=github_str,
            leetcode_line=leetcode_line,
        )
        response = invoke_llm(llm, prompt)
        rationale = response.content.strip().replace('"', '')
        if not rationale:
            rationale = fallback_rationale
    except Exception as e:
        log.warning("competency assessor LLM failed: %s", e)
        rationale = fallback_rationale

    return depth_score, rationale
