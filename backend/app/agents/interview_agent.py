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
