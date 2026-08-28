"""Profile Agent: LLM extraction with a deterministic keyword-scan fallback.

The fallback existed only for LLM-unavailable/exception cases. Reproduced
directly against the real local LLM: terse, casual phrasing ("know some
linux and cloud stuff") makes qwen2.5:7b-instruct return a valid but EMPTY
extraction array, even though "linux" is right there in the text — a real
small-model failure mode distinct from the LLM being unreachable. An empty
LLM result was being treated as "this student has no skills" instead of
triggering the same deterministic safety net.
"""
from unittest.mock import MagicMock, patch

from app.agents.profile_agent import build_profile


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def test_falls_back_to_keyword_scan_when_llm_extracts_nothing():
    text = "final year student looking for devops job, know some linux and cloud stuff"
    with patch("app.agents.profile_agent.get_llm") as mock_get_llm, \
         patch("app.agents.profile_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response("[]")
        profile, notes = build_profile(text, "DevOps Engineer")

    assert [s.name for s in profile.skills] == ["Linux Administration"]
    assert notes == ["LLM found no skills in this text; used a keyword scan instead."]


def test_no_fallback_note_when_llm_and_keyword_scan_both_find_nothing():
    # Genuinely skill-free text — the LLM correctly finds nothing, and the
    # keyword scan correctly finds nothing too. No confusing "used a
    # keyword scan instead" note when the fallback itself found nothing.
    text = "Aspiring DevOps Engineer with a passion for automation and cloud infrastructure."
    with patch("app.agents.profile_agent.get_llm") as mock_get_llm, \
         patch("app.agents.profile_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response("[]")
        profile, notes = build_profile(text, "DevOps Engineer")

    assert profile.skills == []
    assert notes == []


def test_llm_result_used_as_is_when_it_finds_skills():
    text = "I have experience with Linux, Docker, and AWS from my college projects."
    fake_json = """[{"mention": "Linux", "level": "intermediate", "depth_score": 5, "evidence": "e"},
                    {"mention": "Docker", "level": "intermediate", "depth_score": 5, "evidence": "e"},
                    {"mention": "AWS", "level": "intermediate", "depth_score": 5, "evidence": "e"}]"""
    with patch("app.agents.profile_agent.get_llm") as mock_get_llm, \
         patch("app.agents.profile_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        profile, notes = build_profile(text, "DevOps Engineer")

    assert {s.name for s in profile.skills} == {"Linux Administration", "Docker & Containers", "AWS"}
    assert notes == []
