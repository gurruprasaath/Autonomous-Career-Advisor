"""Review agent: LLM resume feedback, with graceful degradation when the
model's output isn't parseable JSON.

The malformed-JSON fixture below is captured verbatim from a real failure
reproduced against the local qwen2.5:7b-instruct model: it sometimes turns
each "strengths"/"weaknesses" array item into a "Label": text pair instead
of a single plain string, which is invalid JSON syntax `extract_json` can
never parse. `REVIEW_PROMPT` was tightened with a negative example to cut
the failure rate (0/8 in a follow-up repro, vs. 2/5 before); this test locks
in that the agent still degrades gracefully — never raises, never surfaces
the raw exception type to the caller — on the rare case it still happens.
"""
from unittest.mock import MagicMock, patch

from app.agents.review_agent import review_resume

MALFORMED_JSON = """```json
{
  "strengths": [
    "Technical Skills": The candidate has demonstrated proficiency in Python, SQL, and machine learning.",
    "Project Experience": The resume mentions several projects, indicating hands-on experience."
  ],
  "weaknesses": [
    "Lack of Cybersecurity Specific Experience": The resume does not mention any specific experience in cybersecurity."
  ],
  "formatting_feedback": "The resume could be structured more effectively.",
  "overall_impression": "The candidate has a solid foundation in technical skills."
}
```"""


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def test_review_resume_returns_result_on_valid_json():
    valid_json = """{"strengths": ["Strong Python skills."], "weaknesses": ["No cloud experience."],
      "formatting_feedback": "Add a summary.", "overall_impression": "Solid candidate."}"""
    with patch("app.agents.review_agent.get_llm") as mock_get_llm, \
         patch("app.agents.review_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(valid_json)
        review, notes = review_resume("resume text", "Data Engineer")

    assert notes == []
    assert review.strengths == ["Strong Python skills."]


def test_review_resume_degrades_gracefully_on_malformed_json():
    with patch("app.agents.review_agent.get_llm") as mock_get_llm, \
         patch("app.agents.review_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(MALFORMED_JSON)
        review, notes = review_resume("resume text", "Cybersecurity Analyst")

    assert review is None
    assert len(notes) == 1
    assert "ValueError" not in notes[0]  # no raw exception type leaked to the caller
