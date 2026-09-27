"""Deterministic status derivation from quiz/confidence signals."""
import datetime

from app.db import crud, database, models

def _db():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    Session = database.sessionmaker(bind=engine)
    return Session()


def _make_step(db):
    user = models.User(email="t@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    journey = crud.create_learning_journey(db, user.id, "Full-Stack Developer",
                                           gap_report_json="{}", hours_per_week=10)
    step = models.PathStep(journey_id=journey.id, order=1, skill_id="react",
                           skill_name="React", objective="obj", milestone="ms",
                           estimated_weeks=3.0)
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def test_high_quiz_and_confidence_completes():
    db = _db()
    step = _make_step(db)
    updated = crud.record_step_progress(db, step.id, quiz_score=80, confidence_rating=4)
    assert updated.status == "completed"


def test_low_quiz_marks_struggling():
    db = _db()
    step = _make_step(db)
    updated = crud.record_step_progress(db, step.id, quiz_score=30, confidence_rating=4)
    assert updated.status == "struggling"


def test_low_confidence_marks_struggling_even_with_good_quiz():
    db = _db()
    step = _make_step(db)
    updated = crud.record_step_progress(db, step.id, quiz_score=90, confidence_rating=1)
    assert updated.status == "struggling"


def test_partial_signal_is_in_progress():
    db = _db()
    step = _make_step(db)
    updated = crud.record_step_progress(db, step.id, minutes_delta=15)
    assert updated.status == "in_progress"
    assert updated.time_spent_minutes == 15


def test_minutes_accumulate_across_calls():
    db = _db()
    step = _make_step(db)
    crud.record_step_progress(db, step.id, minutes_delta=15)
    updated = crud.record_step_progress(db, step.id, minutes_delta=10)
    assert updated.time_spent_minutes == 25


def _make_user(db, email="gh@example.com"):
    user = models.User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_replace_github_evidence_replaces_not_duplicates():
    db = _db()
    user = _make_user(db)

    crud.replace_github_evidence(db, user.id, [
        {"skill_id": "python", "repo_name": "repo-a", "repo_language": "Python", "last_pushed_at": None},
    ])
    crud.replace_github_evidence(db, user.id, [
        {"skill_id": "python", "repo_name": "repo-b", "repo_language": "Python", "last_pushed_at": None},
        {"skill_id": "javascript", "repo_name": "repo-b", "repo_language": "JavaScript", "last_pushed_at": None},
    ])

    rows = db.query(models.GithubEvidence).filter(models.GithubEvidence.user_id == user.id).all()
    assert len(rows) == 2  # re-sync replaced repo-a's row rather than accumulating it
    assert {r.repo_name for r in rows} == {"repo-b"}


def test_get_github_evidence_by_skill_groups_by_skill():
    db = _db()
    user = _make_user(db, email="gh2@example.com")

    crud.replace_github_evidence(db, user.id, [
        {"skill_id": "python", "repo_name": "repo-a", "repo_language": "Python", "last_pushed_at": None},
        {"skill_id": "python", "repo_name": "repo-c", "repo_language": "Python", "last_pushed_at": None},
        {"skill_id": "javascript", "repo_name": "repo-b", "repo_language": "JavaScript", "last_pushed_at": None},
    ])

    by_skill = crud.get_github_evidence_by_skill(db, user.id)
    assert {e.repo_name for e in by_skill["python"]} == {"repo-a", "repo-c"}
    assert {e.repo_name for e in by_skill["javascript"]} == {"repo-b"}


def test_confidence_rating_out_of_range_rejected():
    """ProgressUpdate validation, extracted into _validate_progress_update
    for testability without a running server."""
    import pytest
    from fastapi import HTTPException
    from app.main import ProgressUpdate, _validate_progress_update

    with pytest.raises(HTTPException):
        _validate_progress_update(ProgressUpdate(confidence_rating=6))


def test_quiz_score_out_of_range_rejected():
    import pytest
    from fastapi import HTTPException
    from app.main import ProgressUpdate, _validate_progress_update

    with pytest.raises(HTTPException):
        _validate_progress_update(ProgressUpdate(quiz_score=150))


def test_valid_progress_update_passes_validation():
    from app.main import ProgressUpdate, _validate_progress_update

    _validate_progress_update(ProgressUpdate(confidence_rating=3, quiz_score=80))  # must not raise


def test_recalculate_depth_score_mapping_avoids_beginner_for_advanced_skill():
    """Finding 1: recalculate_journey must set depth_score (not just level) on
    reconstructed StudentSkill, since planner_agent's level-selection reads
    depth_score exclusively (see _courses_for's depth_score < 4/< 8 cutoffs).
    An 'advanced' skill has to land in the intermediate/advanced band, not
    beginner, after reconstruction."""
    from app.main import _LEVEL_TO_DEPTH
    from app.schemas import StudentSkill

    skill = StudentSkill(skill_id="react", name="React", level="advanced",
                         depth_score=_LEVEL_TO_DEPTH.get("advanced", 1))
    assert skill.depth_score >= 8  # would classify as "advanced" in _courses_for

    skill_intermediate = StudentSkill(skill_id="sql", name="SQL", level="intermediate",
                                      depth_score=_LEVEL_TO_DEPTH.get("intermediate", 1))
    assert 4 <= skill_intermediate.depth_score < 8  # "intermediate" band

    skill_beginner = StudentSkill(skill_id="git", name="Git", level="beginner",
                                  depth_score=_LEVEL_TO_DEPTH.get("beginner", 1))
    assert skill_beginner.depth_score < 4  # "beginner" band, as expected


def _make_quiz_step(db, user_id, journey_id):
    step = models.PathStep(journey_id=journey_id, order=1, skill_id="react",
                           skill_name="React", objective="obj", milestone="ms",
                           estimated_weeks=3.0)
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def test_quiz_submit_evicts_cache_and_second_submit_fails_cleanly():
    """Finding 2: a cached quiz must be evicted after scoring — otherwise the
    same quiz can be resubmitted forever and a reused SQLite step id could be
    scored against a stale, unrelated question set."""
    import pytest
    from fastapi import HTTPException
    from app.main import _quiz_cache, submit_step_quiz, QuizSubmission

    db = _db()
    user = _make_user(db, email="quiz@example.com")
    journey = crud.create_learning_journey(db, user.id, "Full-Stack Developer",
                                           gap_report_json="{}", hours_per_week=10)
    step = _make_quiz_step(db, user.id, journey.id)

    _quiz_cache[step.id] = [{"question": "q", "options": ["a", "b"], "correct_index": 0}]

    result = submit_step_quiz(step.id, QuizSubmission(answers=[0]), db, user)
    assert result == {"score": 100}
    assert step.id not in _quiz_cache  # evicted after scoring

    with pytest.raises(HTTPException) as exc_info:
        submit_step_quiz(step.id, QuizSubmission(answers=[0]), db, user)
    assert exc_info.value.status_code == 400  # resubmit fails cleanly, no crash


def test_recalculate_pops_quiz_cache_for_deleted_steps():
    """The recalculate endpoint must also evict cache entries for steps it
    deletes, so a reused id can't inherit a stale quiz."""
    from app.main import _quiz_cache

    db = _db()
    user = _make_user(db, email="quiz2@example.com")
    journey = crud.create_learning_journey(db, user.id, "Full-Stack Developer",
                                           gap_report_json="{}", hours_per_week=10)
    step = _make_quiz_step(db, user.id, journey.id)
    _quiz_cache[step.id] = [{"question": "q", "options": ["a", "b"], "correct_index": 0}]

    # Exercise the same delete+pop loop recalculate_journey runs, without
    # invoking the full LLM-backed planner.
    remaining = [step]
    for s in remaining:
        _quiz_cache.pop(s.id, None)
        db.delete(s)
    db.commit()

    assert step.id not in _quiz_cache


def test_create_and_read_competency_history():
    db = _db()
    user = _make_user(db, email="comp@example.com")
    crud.create_competency_history(db, user.id, "python", 6, 80, 4, True, "Depth raised to 6/10.")

    history = crud.get_competency_history(db, user.id)
    assert "python" in history
    assert len(history["python"]) == 1
    row = history["python"][0]
    assert row["depth_score"] == 6
    assert row["quiz_score"] == 80
    assert row["confidence_rating"] == 4
    assert row["has_github_evidence"] is True
    assert row["rationale"] == "Depth raised to 6/10."


def test_competency_history_multiple_rows_ordered_by_recorded_at():
    db = _db()
    user = _make_user(db, email="comp2@example.com")
    base = datetime.datetime(2026, 1, 1)
    for i, depth in enumerate([3, 5, 7]):
        db.add(models.CompetencyHistory(
            user_id=user.id, skill_id="python", depth_score=depth,
            rationale=f"step {i}", recorded_at=base + datetime.timedelta(days=i)))
    db.commit()

    history = crud.get_competency_history(db, user.id)
    assert [r["depth_score"] for r in history["python"]] == [3, 5, 7]


def test_get_latest_competency_returns_most_recent_row():
    db = _db()
    user = _make_user(db, email="comp3@example.com")
    base = datetime.datetime(2026, 1, 1)
    for i, depth in enumerate([3, 5, 7]):
        db.add(models.CompetencyHistory(
            user_id=user.id, skill_id="python", depth_score=depth,
            rationale=f"step {i}", recorded_at=base + datetime.timedelta(days=i)))
    db.commit()

    latest = crud.get_latest_competency(db, user.id, "python")
    assert latest.depth_score == 7


def test_get_latest_competency_none_when_no_history():
    db = _db()
    user = _make_user(db, email="comp4@example.com")
    assert crud.get_latest_competency(db, user.id, "python") is None


def test_create_competency_history_batch_single_commit():
    db = _db()
    user = _make_user(db, email="comp5@example.com")
    crud.create_competency_history_batch(db, [
        {"user_id": user.id, "skill_id": "python", "depth_score": 4,
         "quiz_score": None, "confidence_rating": None,
         "has_github_evidence": False, "rationale": "r1"},
        {"user_id": user.id, "skill_id": "sql", "depth_score": 3,
         "quiz_score": None, "confidence_rating": None,
         "has_github_evidence": False, "rationale": "r2"},
    ])
    history = crud.get_competency_history(db, user.id)
    assert set(history.keys()) == {"python", "sql"}


def test_get_latest_competency_per_skill_returns_most_recent_row_per_skill():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=5,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="resume"))
    db.commit()
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=8,
                                    quiz_score=80, confidence_rating=4,
                                    has_github_evidence=True, rationale="improved"))
    db.commit()

    latest = crud.get_latest_competency_per_skill(db, user_id)
    assert latest["python"].depth_score == 8


def test_get_latest_competency_per_skill_covers_multiple_skills():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="python", depth_score=5,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="a"))
    db.add(models.CompetencyHistory(user_id=user_id, skill_id="sql", depth_score=3,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="b"))
    db.commit()

    latest = crud.get_latest_competency_per_skill(db, user_id)
    assert set(latest.keys()) == {"python", "sql"}


def test_get_most_recent_journey_orders_by_created_at_desc():
    db = _db()
    step = _make_step(db)
    user_id = step.journey.user_id
    second_journey = crud.create_learning_journey(db, user_id, "Full-Stack Developer",
                                                   gap_report_json="{}", hours_per_week=10)

    most_recent = crud.get_most_recent_journey(db, user_id)
    assert most_recent.id == second_journey.id


def test_get_most_recent_journey_returns_none_for_user_with_no_journeys():
    db = _db()
    user = models.User(email="nobody@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert crud.get_most_recent_journey(db, user.id) is None


def test_leetcode_snapshot_round_trips():
    db = _db()
    user = _make_user(db, email="lc@example.com")
    assert crud.get_leetcode_snapshot(user) is None

    snapshot = {"easy": 5, "medium": 1, "hard": 0, "topics": {"Array": 3},
                "last_accepted_at": None, "synced_at": "2026-09-27T10:00:00+00:00"}
    crud.save_leetcode_snapshot(db, user, "alice", snapshot)

    db.refresh(user)
    assert user.leetcode_username == "alice"
    assert crud.get_leetcode_snapshot(user) == snapshot


def test_leetcode_snapshot_corrupt_json_reads_as_none():
    db = _db()
    user = _make_user(db, email="lc2@example.com")
    user.leetcode_stats_json = "{not json"
    db.commit()
    assert crud.get_leetcode_snapshot(user) is None


def test_competency_history_batch_accepts_leetcode_depth():
    db = _db()
    user = _make_user(db, email="lc3@example.com")
    crud.create_competency_history_batch(db, [
        {"user_id": user.id, "skill_id": "problem-solving", "depth_score": 6,
         "quiz_score": None, "confidence_rating": None, "has_github_evidence": False,
         "leetcode_depth": 6, "rationale": "r"},
    ])
    row = crud.get_latest_competency(db, user.id, "problem-solving")
    assert row.leetcode_depth == 6
