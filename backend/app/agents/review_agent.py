import logging
from ..config import get_settings
from ..core.llm import LLMUnavailable, extract_json, get_llm, invoke_llm
from ..schemas import ResumeReviewResult

log = logging.getLogger(__name__)

REVIEW_PROMPT = """You are an expert career coach and resume reviewer. Review the following resume text against the target role "{role}".

Provide a structured, qualitative review highlighting:
- Strengths: What the candidate is doing well (e.g. strong impact statements, good tech stack).
- Weaknesses: Areas lacking depth, missing keywords, or weak formatting.
- Formatting feedback: How they can structure or write the resume better.
- Overall impression: A short concluding paragraph.

Resume Text:
\"\"\"{text}\"\"\"

Return ONLY JSON matching this structure:
{{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "formatting_feedback": "...",
  "overall_impression": "..."
}}
"""

def review_resume(resume_text: str, target_role: str) -> tuple[ResumeReviewResult | None, list[str]]:
    notes: list[str] = []
    try:
        llm = get_llm(get_settings().fast_model)
        response = invoke_llm(llm, REVIEW_PROMPT.format(text=resume_text, role=target_role))
        data = extract_json(response.content)
        if isinstance(data, dict):
            return ResumeReviewResult(**data), notes
        else:
            notes.append("Review agent returned invalid format.")
            return None, notes
    except LLMUnavailable as e:
        notes.append(f"Review agent skipped due to LLM unavailability: {e}")
        return None, notes
    except Exception as e:
        log.warning("review LLM extraction failed: %s", e)
        notes.append(f"Review extraction failed ({type(e).__name__}).")
        return None, notes
