"""Deterministic status derivation from quiz/confidence signals."""
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
