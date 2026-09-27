"""Sub-topics round-trip: planner PathStep -> DB -> tracker journeys endpoint."""
from app.db import crud, database, models
from app.main import get_journeys
from app.schemas import PathStep, Subtopic


def _db_and_user():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    db = database.sessionmaker(bind=engine)()
    user = models.User(email="subtopics@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_subtopics_and_roadmap_url_round_trip_to_tracker():
    db, user = _db_and_user()
    journey = crud.create_learning_journey(db, user.id, "Backend Developer")
    step = PathStep(order=1, skill_id="python", skill_name="Python", objective="o",
                    milestone="m", estimated_weeks=2.0,
                    subtopics=[Subtopic(id="python-oop", name="OOP", level="intermediate")],
                    roadmap_url="https://roadmap.sh/python")
    crud.create_path_steps(db, journey.id, [step])

    tracked = get_journeys(db, user)[0]["steps"][0]
    assert tracked["subtopics"] == [{"id": "python-oop", "name": "OOP", "level": "intermediate"}]
    assert tracked["roadmap_url"] == "https://roadmap.sh/python"


def test_pre_r1_step_rows_read_as_empty():
    db, user = _db_and_user()
    journey = crud.create_learning_journey(db, user.id, "Backend Developer")
    db.add(models.PathStep(journey_id=journey.id, order=1, skill_id="python", skill_name="Python",
                           objective="o", milestone="m", estimated_weeks=1.0))
    db.commit()

    tracked = get_journeys(db, user)[0]["steps"][0]
    assert tracked["subtopics"] == []
    assert tracked["roadmap_url"] == ""
