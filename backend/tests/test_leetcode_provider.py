"""LeetCode provider: pure scoring functions + fetch_profile with mocked httpx
(no real network calls)."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.providers.leetcode import (
    CORE_TOPICS,
    DSA_SKILL_ID,
    LeetcodeUnavailable,
    LeetcodeUserNotFound,
    depth_for_skill,
    dsa_depth,
    fetch_profile,
    summarize,
    weak_topics,
)


def _snap(easy=0, medium=0, hard=0, topics=None, **extra):
    return {"easy": easy, "medium": medium, "hard": hard,
            "topics": topics or {}, "last_accepted_at": None, **extra}


# ---- dsa_depth calibration table (from the spec) ----

@pytest.mark.parametrize("easy,medium,hard,expected", [
    (0, 0, 0, None),
    (20, 0, 0, 2),
    (100, 0, 0, 6),
    (50, 30, 0, 6),
    (100, 150, 50, 10),
])
def test_dsa_depth_calibration(easy, medium, hard, expected):
    assert dsa_depth(_snap(easy, medium, hard)) == expected


def test_dsa_depth_never_below_one_for_a_single_solve():
    assert dsa_depth(_snap(easy=1)) == 1


# ---- weak_topics ----

def _all_core(count):
    return {t: count for t in CORE_TOPICS}


def test_weak_topics_lowest_counts_first():
    topics = _all_core(10)
    topics.update({"Dynamic Programming": 1, "Greedy": 3, "Hash Table": 4})
    assert weak_topics(_snap(topics=topics)) == ["Dynamic Programming", "Greedy", "Hash Table"]


def test_weak_topics_absent_topic_counts_as_zero_and_ties_follow_core_order():
    assert weak_topics(_snap(topics={})) == ["Array", "String", "Hash Table"]


def test_weak_topics_excludes_topics_with_five_or_more_solves():
    topics = _all_core(10)
    topics["Heap"] = 5  # exactly at the threshold -> not weak
    topics["Tree"] = 4
    assert weak_topics(_snap(topics=topics)) == ["Tree"]


def test_weak_topics_empty_when_all_core_topics_practiced():
    assert weak_topics(_snap(topics=_all_core(5))) == []


def test_weak_topics_respects_limit():
    assert weak_topics(_snap(topics={}), limit=5) == CORE_TOPICS[:5]


# ---- summarize / depth_for_skill ----

def test_summarize_builds_display_fields():
    snap = _snap(50, 30, 0, topics=_all_core(10), synced_at="2026-09-27T10:00:00+00:00")
    s = summarize("alice", snap)
    assert s == {
        "username": "alice", "easy": 50, "medium": 30, "hard": 0, "total": 80,
        "dsa_depth": 6, "weak_topics": [], "last_accepted_at": None,
        "synced_at": "2026-09-27T10:00:00+00:00",
    }


def test_depth_for_skill_only_for_dsa_skill():
    snap = _snap(20)
    assert DSA_SKILL_ID == "problem-solving"
    assert depth_for_skill("problem-solving", snap) == 2
    assert depth_for_skill("python", snap) is None
    assert depth_for_skill("problem-solving", None) is None


# ---- fetch_profile (mocked httpx.post) ----

def _response(status_code, body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


REAL_SHAPE = {"data": {
    "matchedUser": {
        "submitStatsGlobal": {"acSubmissionNum": [
            {"difficulty": "All", "count": 80}, {"difficulty": "Easy", "count": 50},
            {"difficulty": "Medium", "count": 30}, {"difficulty": "Hard", "count": 0}]},
        "tagProblemCounts": {
            "advanced": [{"tagName": "Dynamic Programming", "problemsSolved": 2}],
            "intermediate": [{"tagName": "Hash Table", "problemsSolved": 12}],
            "fundamental": [{"tagName": "Array", "problemsSolved": 40}],
        },
    },
    "recentAcSubmissionList": [{"timestamp": "1767225600"}],  # 2026-01-01T00:00:00Z
}}


def test_fetch_profile_parses_real_response_shape():
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, REAL_SHAPE)) as post:
        snap = fetch_profile("alice")
    assert snap == {
        "easy": 50, "medium": 30, "hard": 0,
        "topics": {"Dynamic Programming": 2, "Hash Table": 12, "Array": 40},
        "last_accepted_at": "2026-01-01T00:00:00+00:00",
    }
    assert post.call_args.kwargs["json"]["variables"] == {"u": "alice"}


def test_fetch_profile_no_recent_submissions_gives_none():
    body = {"data": {**REAL_SHAPE["data"], "recentAcSubmissionList": []}}
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        assert fetch_profile("alice")["last_accepted_at"] is None


def test_fetch_profile_missing_user_raises_not_found():
    body = {"errors": [{"message": "That user does not exist."}],
            "data": {"matchedUser": None, "recentAcSubmissionList": []}}
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        with pytest.raises(LeetcodeUserNotFound):
            fetch_profile("nobody")


def test_fetch_profile_non_200_raises_unavailable():
    with patch("app.providers.leetcode.httpx.post", return_value=_response(503, {})):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


def test_fetch_profile_network_error_raises_unavailable():
    with patch("app.providers.leetcode.httpx.post", side_effect=httpx.ConnectError("boom")):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


@pytest.mark.parametrize("body", [
    {"data": None},
    {"unexpected": True},
    {"data": {"matchedUser": {"submitStatsGlobal": None}}},
])
def test_fetch_profile_malformed_body_raises_unavailable(body):
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


def test_fetch_profile_invalid_json_raises_unavailable():
    resp = _response(200, None)
    resp.json.side_effect = ValueError("not json")
    with patch("app.providers.leetcode.httpx.post", return_value=resp):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")
