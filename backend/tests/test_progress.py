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
