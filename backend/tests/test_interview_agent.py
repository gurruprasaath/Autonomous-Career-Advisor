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
