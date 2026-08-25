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

def create_learning_journey(db: Session, user_id: int, target_role: str):
    db_journey = models.LearningJourney(user_id=user_id, target_role=target_role)
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

def create_path_steps(db: Session, journey_id: int, steps: list):
    import json
    db_steps = []
    for s in steps:
        db_step = models.PathStep(
            journey_id=journey_id,
            order=s.order,
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

def update_step_status(db: Session, step_id: int, status: str):
    db_step = db.query(models.PathStep).filter(models.PathStep.id == step_id).first()
    if db_step:
        db_step.status = status
        db.commit()
        db.refresh(db_step)
    return db_step
