"""LeetCode endpoints + interview focus topics. Endpoint functions are called
directly with an in-memory DB and user (same pattern as test_progress.py);
the provider's network call is patched."""
import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.db import database, models
from app.main import LeetcodeSyncRequest, _interview_focus_topics, get_leetcode, sync_leetcode
from app.providers.leetcode import LeetcodeUnavailable, LeetcodeUserNotFound

SNAPSHOT = {"easy": 50, "medium": 30, "hard": 0,
            "topics": {"Array": 40, "Hash Table": 12, "Dynamic Programming": 2},
            "last_accepted_at": "2026-09-01T00:00:00+00:00"}


def _db_and_user():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    db = database.sessionmaker(bind=engine)()
    user = models.User(email="lcapi@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_sync_rejects_invalid_username_without_calling_leetcode():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile") as fetch:
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="bad name!"), db, user)
    assert exc.value.status_code == 400
    fetch.assert_not_called()


def test_sync_unknown_user_is_404():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", side_effect=LeetcodeUserNotFound("ghost")):
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="ghost"), db, user)
    assert exc.value.status_code == 404
    assert "ghost" in exc.value.detail


def test_sync_leetcode_down_is_502_and_stores_nothing():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", side_effect=LeetcodeUnavailable("HTTP 503")):
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="alice"), db, user)
    assert exc.value.status_code == 502
    assert user.leetcode_stats_json is None


def test_sync_success_persists_and_get_returns_same_summary():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", return_value=dict(SNAPSHOT)):
        synced = sync_leetcode(LeetcodeSyncRequest(username="alice"), db, user)

    assert synced["username"] == "alice"
    assert synced["total"] == 80
    assert synced["dsa_depth"] == 6
    assert synced["synced_at"] is not None
    assert json.loads(user.leetcode_stats_json)["easy"] == 50

    assert get_leetcode(user) == synced


def test_get_leetcode_never_synced_is_none():
    _db, user = _db_and_user()
    assert get_leetcode(user) is None


def test_interview_focus_topics_appends_dsa_labeled_weak_topics_after_gaps():
    gap_json = json.dumps({"gaps": [{"name": "Docker"}, {"name": "Array"}]})
    snapshot = {"easy": 1, "medium": 0, "hard": 0, "topics": {}, "last_accepted_at": None}
    # weak topics for an empty topic map are Array, String, Hash Table (labeled with DSA suffix)
    assert _interview_focus_topics(gap_json, snapshot) == ["Docker", "Array", "Array (DSA)", "String (DSA)", "Hash Table (DSA)"]


def test_interview_focus_topics_does_not_repeat_an_existing_labeled_topic():
    gap_json = json.dumps({"gaps": [{"name": "Array (DSA)"}]})
    snapshot = {"easy": 1, "medium": 0, "hard": 0, "topics": {}, "last_accepted_at": None}
    assert _interview_focus_topics(gap_json, snapshot) == ["Array (DSA)", "String (DSA)", "Hash Table (DSA)"]


def test_interview_focus_topics_without_leetcode_is_gap_names_only():
    gap_json = json.dumps({"gaps": [{"name": f"S{i}"} for i in range(7)]})
    assert _interview_focus_topics(gap_json, None) == ["S0", "S1", "S2", "S3", "S4"]


def test_interview_focus_topics_tolerates_bad_gap_json():
    assert _interview_focus_topics("{not json", None) == []
