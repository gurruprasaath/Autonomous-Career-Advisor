"""Finding 1: recalculate_journey's LeetCode wiring (lc_depth ->
assess_competency(leetcode_depth=...) -> CompetencyHistory.leetcode_depth) had
no test. Endpoint is called directly with an in-memory DB (same pattern as
test_leetcode_api.py / test_progress.py); planner/verifier/LLM are patched so
this only exercises the wiring, not the agents."""
import json
from unittest.mock import patch

from app.db import crud, database, models
from app.main import recalculate_journey
from app.schemas import FGCRCritique, LearningPath, PathStep


def _db_and_user():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    db = database.sessionmaker(bind=engine)()
    user = models.User(email="lcrecalc@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_recalculate_journey_writes_leetcode_depth_only_for_dsa_skill():
    db, user = _db_and_user()
    crud.save_leetcode_snapshot(db, user, "alice", {
        "easy": 20, "medium": 0, "hard": 0, "topics": {},
        "last_accepted_at": None, "synced_at": "2026-09-27T00:00:00+00:00",
    })

    gap_report = {
        "target_role": "Backend Developer",
        "gaps": [
            {"skill_id": "problem-solving", "name": "Problem Solving & DSA",
             "demand_share": 0.5, "current_level": "beginner",
             "required_level": "advanced", "gap_size": 2.0, "priority": 1.0},
            {"skill_id": "python", "name": "Python",
             "demand_share": 0.5, "current_level": "beginner",
             "required_level": "advanced", "gap_size": 2.0, "priority": 1.0},
        ],
        "strengths": [],
    }
    journey = crud.create_learning_journey(db, user.id, "Backend Developer",
                                           gap_report_json=json.dumps(gap_report),
                                           hours_per_week=10)

    for skill_id, name in [("problem-solving", "Problem Solving & DSA"), ("python", "Python")]:
        db.add(models.PathStep(journey_id=journey.id, order=1, skill_id=skill_id,
                               skill_name=name, objective="o", milestone="m",
                               status="struggling", quiz_score=40, confidence_rating=2))
    db.commit()

    fake_path = LearningPath(target_role="Backend Developer", steps=[
        PathStep(order=1, skill_id="python", skill_name="Python", objective="o", milestone="m"),
    ])
    fake_critique = FGCRCritique(feasibility=5, groundedness=5, coverage=5, realism=5, passed=True)

    with patch("app.agents.planner_agent.build_path", return_value=(fake_path, [])), \
         patch("app.agents.verifier_agent.verify_path", return_value=(fake_critique, [])), \
         patch("app.agents.competency_agent.get_llm", side_effect=RuntimeError("no llm")):
        recalculate_journey(journey.id, db, user)

    dsa_row = crud.get_latest_competency(db, user.id, "problem-solving")
    python_row = crud.get_latest_competency(db, user.id, "python")

    assert dsa_row.leetcode_depth == 2
    assert python_row.leetcode_depth is None
