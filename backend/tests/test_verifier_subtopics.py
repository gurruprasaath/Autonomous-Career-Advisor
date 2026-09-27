"""Verifier hard check: every sub-topic must come from the curated curriculum."""
from unittest.mock import MagicMock, patch

from app.agents.verifier_agent import _hard_checks
from app.core.taxonomy import subtopics_for
from app.schemas import GapReport, LearningPath, PathStep, StudentProfile, Subtopic


def _checks(step: PathStep):
    path = LearningPath(target_role="Backend Developer", steps=[step],
                        total_weeks=step.estimated_weeks)
    catalog = MagicMock()
    catalog.get.return_value = {"ids": [], "metadatas": []}
    with patch("app.agents.verifier_agent.courses_collection", return_value=catalog):
        return _hard_checks(path, GapReport(target_role="Backend Developer"),
                            StudentProfile(hours_per_week=10, target_role="Backend Developer"))


def _step(subtopics):
    return PathStep(order=1, skill_id="python", skill_name="Python", objective="o",
                    estimated_weeks=2.0, subtopics=subtopics)


def test_curated_subtopics_raise_no_subtopic_issue():
    caps, issues = _checks(_step(subtopics_for("python")[:2]))
    assert not any("curated curriculum" in i for i in issues)
    assert caps["groundedness"] == 3.0  # only the pre-existing no-resources cap applies


def test_unknown_subtopic_caps_groundedness_at_one():
    caps, issues = _checks(_step([Subtopic(id="python-made-up", name="Made up", level="beginner")]))
    assert caps["groundedness"] == 1.0
    assert "Sub-topic 'Made up' is not in the curated curriculum for Python" in issues
