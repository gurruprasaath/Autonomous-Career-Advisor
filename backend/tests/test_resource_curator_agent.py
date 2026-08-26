"""Resource Curator Agent: mocked-LLM tests mirroring test_quiz_agent.py's
pattern — retrieval is mocked (courses_collection, search_youtube_videos) so
these run offline with no real Chroma/YouTube calls."""
import json
from unittest.mock import MagicMock, patch

from app.agents.resource_curator_agent import curate_resources
from app.schemas import PathResource


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def _catalog_hits(n):
    return {
        "ids": [f"course-{i}" for i in range(n)],
        "metadatas": [
            {"title": f"Course {i}", "provider": "Udemy", "url": f"https://ex.com/{i}", "free": True}
            for i in range(n)
        ],
    }


def _no_courses():
    return {"ids": [], "metadatas": []}


def test_valid_picks_pass_through():
    picks = json.dumps({"picks": [{"candidate_id": "course-1", "justification": "fits"},
                                   {"candidate_id": "course-2", "justification": "fits"}]})
    with patch("app.agents.resource_curator_agent.search_youtube_videos", return_value=[]), \
         patch("app.agents.resource_curator_agent.courses_collection") as mock_courses, \
         patch("app.agents.resource_curator_agent.get_llm") as mock_get_llm, \
         patch("app.agents.resource_curator_agent.invoke_llm") as mock_invoke:
        mock_courses.return_value.get.return_value = _catalog_hits(4)
        mock_invoke.return_value = _mock_llm_response(picks)
        resources = curate_resources("python", "Python", 5, "Learn Python basics", k=2)

    assert {r.course_id for r in resources} == {"course-1", "course-2"}


def test_invented_candidate_id_is_dropped():
    picks = json.dumps({"picks": [{"candidate_id": "course-1", "justification": "fits"},
                                   {"candidate_id": "not-a-real-id", "justification": "hallucinated"}]})
    with patch("app.agents.resource_curator_agent.search_youtube_videos", return_value=[]), \
         patch("app.agents.resource_curator_agent.courses_collection") as mock_courses, \
         patch("app.agents.resource_curator_agent.get_llm") as mock_get_llm, \
         patch("app.agents.resource_curator_agent.invoke_llm") as mock_invoke:
        mock_courses.return_value.get.return_value = _catalog_hits(4)
        mock_invoke.return_value = _mock_llm_response(picks)
        resources = curate_resources("python", "Python", 5, "Learn Python basics", k=2)

    assert [r.course_id for r in resources] == ["course-1"]


def test_all_invalid_picks_trigger_deterministic_fallback():
    picks = json.dumps({"picks": [{"candidate_id": "bogus-1"}, {"candidate_id": "bogus-2"}]})
    with patch("app.agents.resource_curator_agent.search_youtube_videos", return_value=[]), \
         patch("app.agents.resource_curator_agent.courses_collection") as mock_courses, \
         patch("app.agents.resource_curator_agent.get_llm") as mock_get_llm, \
         patch("app.agents.resource_curator_agent.invoke_llm") as mock_invoke:
        mock_courses.return_value.get.return_value = _catalog_hits(4)
        mock_invoke.return_value = _mock_llm_response(picks)
        resources = curate_resources("python", "Python", 5, "Learn Python basics", k=2)

    # Falls back to the deterministic first-k of the retrieved candidate pool.
    assert [r.course_id for r in resources] == ["course-0", "course-1"]


def test_duplicate_picks_are_deduped():
    picks = json.dumps({"picks": [{"candidate_id": "course-1"}, {"candidate_id": "course-1"},
                                   {"candidate_id": "course-2"}]})
    with patch("app.agents.resource_curator_agent.search_youtube_videos", return_value=[]), \
         patch("app.agents.resource_curator_agent.courses_collection") as mock_courses, \
         patch("app.agents.resource_curator_agent.get_llm") as mock_get_llm, \
         patch("app.agents.resource_curator_agent.invoke_llm") as mock_invoke:
        mock_courses.return_value.get.return_value = _catalog_hits(4)
        mock_invoke.return_value = _mock_llm_response(picks)
        resources = curate_resources("python", "Python", 5, "Learn Python basics", k=2)

    ids = [r.course_id for r in resources]
    assert ids == ["course-1", "course-2"]
    assert len(ids) == len(set(ids))


def test_mock_youtube_results_never_enter_candidate_pool():
    mock_yt = [PathResource(course_id="yt-mock-0", title="Sample Video for x",
                             provider="YouTube (Fallback)",
                             url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", free=True)]
    with patch("app.agents.resource_curator_agent.search_youtube_videos", return_value=mock_yt), \
         patch("app.agents.resource_curator_agent.courses_collection") as mock_courses:
        mock_courses.return_value.get.return_value = _no_courses()
        resources = curate_resources("python", "Python", 5, "Learn Python basics", k=2)

    # No real candidates at all (mock yt excluded, no catalog hits) -> empty, not the mock.
    assert resources == []
    assert all(not r.course_id.startswith("yt-mock-") for r in resources)
