"""Level-window selection of curated sub-topics. The data file is replaced
by a fixture via patching load_subtopics, so these tests don't depend on the
real curriculum content."""
from unittest.mock import patch

import pytest

from app.core.taxonomy import roadmap_url_for, select_subtopics, subtopics_for

FIXTURE = {
    "skills": {
        "python": {
            "roadmap_url": "https://roadmap.sh/python",
            "references": [],
            "subtopics": [
                {"id": "python-b1", "name": "B1", "level": "beginner"},
                {"id": "python-b2", "name": "B2", "level": "beginner"},
                {"id": "python-i1", "name": "I1", "level": "intermediate"},
                {"id": "python-a1", "name": "A1", "level": "advanced"},
            ],
        },
        "beginner-only": {
            "roadmap_url": "",
            "references": [],
            "subtopics": [
                {"id": "beginner-only-b1", "name": "OB1", "level": "beginner"},
                {"id": "beginner-only-i1", "name": "OI1", "level": "intermediate"},
            ],
        },
    }
}


@pytest.fixture(autouse=True)
def fixture_data():
    with patch("app.core.taxonomy.load_subtopics", return_value=FIXTURE):
        yield


def ids(subs):
    return [s.id for s in subs]


def test_subtopics_for_returns_models_in_file_order():
    subs = subtopics_for("python")
    assert ids(subs) == ["python-b1", "python-b2", "python-i1", "python-a1"]
    assert subs[2].name == "I1" and subs[2].level == "intermediate"


def test_unknown_skill_has_no_subtopics_and_no_url():
    assert subtopics_for("nope") == []
    assert roadmap_url_for("nope") == ""
    assert select_subtopics("nope", "none", "advanced") == []


def test_roadmap_url_for_known_skill():
    assert roadmap_url_for("python") == "https://roadmap.sh/python"


@pytest.mark.parametrize("current,required,expected", [
    ("none", "beginner", ["python-b1", "python-b2"]),
    ("none", "intermediate", ["python-b1", "python-b2", "python-i1"]),
    ("none", "advanced", ["python-b1", "python-b2", "python-i1", "python-a1"]),
    ("beginner", "advanced", ["python-i1", "python-a1"]),
    ("intermediate", "advanced", ["python-a1"]),
])
def test_window_is_strictly_above_current_up_to_required(current, required, expected):
    assert ids(select_subtopics("python", current, required)) == expected


def test_empty_window_falls_back_to_required_level():
    # current == required: window is empty -> sub-topics AT the required level
    assert ids(select_subtopics("python", "intermediate", "intermediate")) == ["python-i1"]


def test_no_subtopic_at_required_level_falls_back_to_all():
    # nothing at "advanced" for this skill and window (intermediate, advanced] is empty
    assert ids(select_subtopics("beginner-only", "intermediate", "advanced")) == [
        "beginner-only-b1", "beginner-only-i1"]
