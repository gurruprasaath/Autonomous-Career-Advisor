import datetime
import json

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

def save_leetcode_snapshot(db: Session, user: models.User, username: str, snapshot: dict) -> None:
    """Re-sync overwrites: only the latest snapshot matters, and derived
    numbers (dsa_depth, weak topics) are recomputed from it on read."""
    user.leetcode_username = username
    user.leetcode_stats_json = json.dumps(snapshot)
    db.commit()


def get_leetcode_snapshot(user: models.User) -> dict | None:
    if not user.leetcode_stats_json:
        return None
    try:
        return json.loads(user.leetcode_stats_json)
    except ValueError:
        return None

def create_competency_history(db: Session, user_id: int, skill_id: str, depth_score: int,
                              quiz_score: int | None, confidence_rating: int | None,
                              has_github_evidence: bool, rationale: str) -> models.CompetencyHistory:
    db_history = models.CompetencyHistory(
        user_id=user_id,
        skill_id=skill_id,
        depth_score=depth_score,
        quiz_score=quiz_score,
        confidence_rating=confidence_rating,
        has_github_evidence=has_github_evidence,
        rationale=rationale
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def create_competency_history_batch(db: Session, rows: list[dict]) -> None:
    """Write several CompetencyHistory rows in one commit (e.g. one per skill
    at initial /api/advise time) instead of one commit per row."""
    db.add_all([models.CompetencyHistory(**row) for row in rows])
    db.commit()


def get_latest_competency(db: Session, user_id: int, skill_id: str) -> models.CompetencyHistory | None:
    """Most recent CompetencyHistory row for this (user, skill), if any —
    used as the reassessment prior instead of re-deriving a coarse bucket
    from the original static gap report every time."""
    return (db.query(models.CompetencyHistory)
            .filter(models.CompetencyHistory.user_id == user_id,
                    models.CompetencyHistory.skill_id == skill_id)
            .order_by(models.CompetencyHistory.recorded_at.desc())
            .first())


def get_competency_history(db: Session, user_id: int) -> dict[str, list]:
    rows = db.query(models.CompetencyHistory).filter(
        models.CompetencyHistory.user_id == user_id
    ).order_by(models.CompetencyHistory.recorded_at.asc()).all()
    history: dict[str, list] = {}
    for row in rows:
        history.setdefault(row.skill_id, []).append({
            "depth_score": row.depth_score,
            "quiz_score": row.quiz_score,
            "confidence_rating": row.confidence_rating,
            "has_github_evidence": row.has_github_evidence,
            "rationale": row.rationale,
            "recorded_at": row.recorded_at.isoformat() if hasattr(row.recorded_at, "isoformat") else row.recorded_at
        })
    return history


def upsert_analyzed_repo(db: Session, user_id: int, username: str, repo_name: str,
                         file_count: int) -> models.AnalyzedRepo:
    """Record that this user has analyzed this repo — update the existing row
    if they've analyzed it before, insert otherwise, so re-submitting the same
    repo is recognized instead of silently re-downloading with no memory of
    the prior run."""
    existing = (db.query(models.AnalyzedRepo)
                .filter(models.AnalyzedRepo.user_id == user_id,
                        models.AnalyzedRepo.username == username,
                        models.AnalyzedRepo.repo_name == repo_name).first())
    if existing:
        existing.file_count = file_count
        existing.analyzed_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    db_repo = models.AnalyzedRepo(user_id=user_id, username=username,
                                  repo_name=repo_name, file_count=file_count)
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def get_analyzed_repos(db: Session, user_id: int) -> list[models.AnalyzedRepo]:
    return (db.query(models.AnalyzedRepo)
            .filter(models.AnalyzedRepo.user_id == user_id)
            .order_by(models.AnalyzedRepo.analyzed_at.desc()).all())


def get_latest_competency_per_skill(db: Session, user_id: int) -> dict[str, models.CompetencyHistory]:
    """Most recent CompetencyHistory row per skill_id for this user — the
    'skills you currently have, and how deep' snapshot used by job
    matching. Unlike get_latest_competency (one skill at a time), this
    returns the whole current picture in one query."""
    rows = (db.query(models.CompetencyHistory)
            .filter(models.CompetencyHistory.user_id == user_id)
            .order_by(models.CompetencyHistory.recorded_at.desc())
            .all())
    latest: dict[str, models.CompetencyHistory] = {}
    for row in rows:
        if row.skill_id not in latest:
            latest[row.skill_id] = row
    return latest


def get_most_recent_journey(db: Session, user_id: int) -> models.LearningJourney | None:
    return (db.query(models.LearningJourney)
            .filter(models.LearningJourney.user_id == user_id)
            .order_by(models.LearningJourney.created_at.desc())
            .first())
