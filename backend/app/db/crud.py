from sqlalchemy.orm import Session
from . import models, auth

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: dict):
    hashed_password = auth.get_password_hash(user["password"])
    db_user = models.User(email=user["email"], hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_journeys_by_user(db: Session, user_id: int):
    return db.query(models.LearningJourney).filter(models.LearningJourney.user_id == user_id).all()

def create_learning_journey(db: Session, user_id: int, target_role: str,
                            gap_report_json: str = "{}", hours_per_week: int = 10):
    db_journey = models.LearningJourney(user_id=user_id, target_role=target_role,
                                        gap_report_json=gap_report_json,
                                        hours_per_week=hours_per_week)
    db.add(db_journey)
    db.commit()
    db.refresh(db_journey)
    return db_journey

def create_path_step(db: Session, step_data: dict):
    db_step = models.PathStep(**step_data)
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    return db_step

def create_path_steps(db: Session, journey_id: int, steps: list, order_offset: int = 0):
    """order_offset lets recalculation append after already-kept completed
    steps instead of renumbering from 1; normal path creation leaves it 0."""
    import json
    db_steps = []
    # order is derived from list position, not s.order — safe because build_path always emits steps in final order
    for i, s in enumerate(steps):
        db_step = models.PathStep(
            journey_id=journey_id,
            order=order_offset + i + 1,
            skill_id=s.skill_id,
            skill_name=s.skill_name,
            objective=s.objective,
            milestone=s.milestone,
            estimated_weeks=s.estimated_weeks,
            resources_json=json.dumps([r.model_dump() for r in s.resources])
        )
        db_steps.append(db_step)
        db.add(db_step)
    db.commit()
    return db_steps


# quiz_score >= 70 and confidence >= 3 -> completed; either signal below its
# floor -> struggling; anything else (partial signals, e.g. only time
# logged) -> in_progress. Deterministic on purpose, same "hard rule over an
# LLM guess" philosophy as the FGCR verifier.
def record_step_progress(db: Session, step_id: int, *, quiz_score: int | None = None,
                         confidence_rating: int | None = None, minutes_delta: int = 0):
    step = db.query(models.PathStep).filter(models.PathStep.id == step_id).first()
    if not step:
        return None
    if quiz_score is not None:
        step.quiz_score = quiz_score
    if confidence_rating is not None:
        step.confidence_rating = confidence_rating
    step.time_spent_minutes = (step.time_spent_minutes or 0) + minutes_delta

    if step.quiz_score is not None and step.confidence_rating is not None:
        if step.quiz_score >= 70 and step.confidence_rating >= 3:
            step.status = "completed"
        elif step.quiz_score < 50 or step.confidence_rating <= 2:
            step.status = "struggling"
        else:
            step.status = "in_progress"
    elif step.quiz_score is not None and step.quiz_score < 50:
        step.status = "struggling"
    elif step.confidence_rating is not None and step.confidence_rating <= 2:
        step.status = "struggling"
    elif step.time_spent_minutes > 0 or step.quiz_score is not None or step.confidence_rating is not None:
        step.status = "in_progress"

    db.commit()
    db.refresh(step)
    return step


def replace_github_evidence(db: Session, user_id: int, evidence_rows: list[dict]) -> None:
    """Re-sync: drop this user's old evidence, write the fresh set."""
    db.query(models.GithubEvidence).filter(models.GithubEvidence.user_id == user_id).delete()
    for row in evidence_rows:
        db.add(models.GithubEvidence(
            user_id=user_id, skill_id=row["skill_id"], repo_name=row["repo_name"],
            repo_language=row["repo_language"], last_pushed_at=row["last_pushed_at"],
        ))
    db.commit()


def get_github_evidence_by_skill(db: Session, user_id: int) -> dict[str, list]:
    rows = db.query(models.GithubEvidence).filter(models.GithubEvidence.user_id == user_id).all()
    by_skill: dict[str, list] = {}
    for row in rows:
        by_skill.setdefault(row.skill_id, []).append(row)
    return by_skill
