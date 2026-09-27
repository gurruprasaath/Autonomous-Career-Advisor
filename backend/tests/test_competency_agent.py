"""Competency Assessment Agent: pure-function tests on the depth formula.

No LLM mocking needed for the score itself (deterministic); a couple of
tests patch invoke_llm to keep the rationale-path fast and offline,
following test_quiz_agent.py's pattern.
"""
from unittest.mock import MagicMock, patch

from app.agents.competency_agent import assess_competency


def test_no_signal_returns_resume_depth_unchanged():
    score, rationale = assess_competency("Python", 5, None, None, False)
    assert score == 5
    assert rationale == "Initial assessment based on resume."


def test_quiz_only_uses_renormalized_weights():
    resume_depth, quiz_score = 4, 90
    expected = round(resume_depth * (0.30 / 0.70) + (quiz_score / 10) * (0.40 / 0.70))
    score, _ = assess_competency("Python", resume_depth, quiz_score, None, False)
    assert score == expected == 7


def test_quiz_and_confidence_blend():
    resume_depth, quiz_score, confidence = 4, 90, 4
    base = (resume_depth * 0.30 + (quiz_score / 10) * 0.40 + (confidence * 2) * 0.15) / 0.85
    score, _ = assess_competency("Python", resume_depth, quiz_score, confidence, False)
    assert score == round(base) == 7


def test_github_bonus_is_additive_not_blended():
    resume_depth, quiz_score, confidence = 4, 90, 4
    base = (resume_depth * 0.30 + (quiz_score / 10) * 0.40 + (confidence * 2) * 0.15) / 0.85
    with_github, _ = assess_competency("Python", resume_depth, quiz_score, confidence, True)
    without_github, _ = assess_competency("Python", resume_depth, quiz_score, confidence, False)
    assert with_github == round(min(10, base + 1.5))
    assert with_github > without_github


def test_github_bonus_capped_at_ten():
    # resume/quiz/confidence all maxed -> base already at 10; +1.5 must cap, not overflow
    score, _ = assess_competency("Python", 10, 100, 5, True)
    assert score == 10


def test_score_clamped_to_floor_of_one():
    # resume at its minimum, quiz at zero -> raw weighted average is well under 1
    score, _ = assess_competency("Python", 1, 0, None, False)
    assert score == 1


def test_rationale_uses_llm_when_available():
    with patch("app.agents.competency_agent.get_llm") as mock_get_llm, \
         patch("app.agents.competency_agent.invoke_llm") as mock_invoke:
        resp = MagicMock()
        resp.content = "Depth raised to 7/10 due to a strong quiz score."
        mock_invoke.return_value = resp
        score, rationale = assess_competency("Python", 4, 90, None, False)
    assert score == 7
    assert rationale == "Depth raised to 7/10 due to a strong quiz score."


def test_rationale_falls_back_when_llm_unavailable():
    with patch("app.agents.competency_agent.get_llm", side_effect=RuntimeError("no llm")):
        score, rationale = assess_competency("Python", 4, 90, None, False)
    assert score == 7
    assert "Depth assessed at 7/10" in rationale


def _no_llm():
    return patch("app.agents.competency_agent.get_llm", side_effect=RuntimeError("no llm"))


def test_leetcode_only_signal_blends_instead_of_returning_resume_depth():
    # (4*0.30 + 8*0.35) / 0.65 = 6.15 -> 6
    with _no_llm():
        score, rationale = assess_competency("Problem Solving & DSA", 4, None, None, False,
                                             leetcode_depth=8)
    assert score == 6
    assert "leetcode: 8/10" in rationale


def test_leetcode_can_lower_an_overstated_resume_depth():
    # (8*0.30 + 2*0.35) / 0.65 = 4.77 -> 5
    with _no_llm():
        score, _ = assess_competency("Problem Solving & DSA", 8, None, None, False,
                                     leetcode_depth=2)
    assert score == 5


def test_leetcode_blends_with_quiz_and_confidence():
    base = (4 * 0.30 + 9.0 * 0.40 + 8 * 0.15 + 10 * 0.35) / 1.20
    with _no_llm():
        score, _ = assess_competency("Problem Solving & DSA", 4, 90, 4, False, leetcode_depth=10)
    assert score == round(base) == 8


def test_no_leetcode_leaves_fallback_rationale_unchanged():
    with _no_llm():
        _, rationale = assess_competency("Python", 4, 90, None, False)
    assert rationale == "Depth assessed at 7/10 (resume: 4, quiz: 90%, conf: None, github: No)."
