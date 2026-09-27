"""build_path attaches curated sub-topics + roadmap links and uses them in the
prompt and the fallback week estimate. LLM and resource curation are patched."""
from unittest.mock import MagicMock, patch

from app.agents.planner_agent import WEEKS_PER_SUBTOPIC, build_path
from app.core.taxonomy import roadmap_url_for, select_subtopics
from app.schemas import GapReport, SkillGap, StudentProfile


def _gap(sid, name, current, required):
    return SkillGap(skill_id=sid, name=name, demand_share=0.5, current_level=current,
                    required_level=required, gap_size=1.0, priority=0.5)


GAPS = [_gap("python", "Python", "none", "advanced"), _gap("sql", "SQL", "beginner", "intermediate")]


def _build(hours=10, llm_content=None):
    profile = StudentProfile(hours_per_week=hours, target_role="Backend Developer")
    report = GapReport(target_role="Backend Developer", gaps=GAPS)
    with patch("app.agents.planner_agent.curate_resources", return_value=[]):
        if llm_content is None:
            with patch("app.agents.planner_agent.get_llm", side_effect=RuntimeError("no llm")):
                return build_path(profile, report)
        with patch("app.agents.planner_agent.get_llm"), \
             patch("app.agents.planner_agent.invoke_llm",
                   return_value=MagicMock(content=llm_content)) as invoke:
            path, notes = build_path(profile, report)
            return path, notes, invoke.call_args.args[1]


def test_steps_carry_selected_subtopics_and_roadmap_url():
    path, _ = _build()
    by_id = {s.skill_id: s for s in path.steps}
    assert by_id["python"].subtopics == select_subtopics("python", "none", "advanced")
    assert by_id["sql"].subtopics == select_subtopics("sql", "beginner", "intermediate")
    assert by_id["python"].roadmap_url == roadmap_url_for("python")
    assert all(s.subtopics for s in path.steps)


def test_fallback_weeks_scale_with_subtopic_count_and_hours():
    path, _ = _build(hours=5)
    for step in path.steps:
        expected = round(len(step.subtopics) * WEEKS_PER_SUBTOPIC * (10 / 5), 1)
        assert step.estimated_weeks == min(max(expected, 0.5), 8)


def test_prompt_lists_each_steps_subtopics():
    _path, _notes, prompt = _build(llm_content='{"steps": [], "rationale": "r"}')
    for sid, cur, req in (("python", "none", "advanced"), ("sql", "beginner", "intermediate")):
        for t in select_subtopics(sid, cur, req):
            assert t.name in prompt


def test_step_without_subtopics_is_estimated_as_one_subtopic():
    # Unreachable with real data (every skill has 4-8 curated sub-topics); pins
    # the max(n, 1) guard the project chose over a literal zero.
    with patch("app.agents.planner_agent.select_subtopics", return_value=[]):
        path, _ = _build(hours=5)
    assert path.steps
    assert all(s.estimated_weeks == 1.5 and s.subtopics == [] for s in path.steps)
