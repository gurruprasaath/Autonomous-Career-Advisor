"""Job Matcher — ranks live job postings against the user's current skills
and the skills they're actively learning.

Overlap score (primary, auditable): deterministic weighted skill overlap,
same "hard math, not LLM-guessed" philosophy as the Gap Engine and Market
Demand agent. Semantic score (secondary boost): embedding similarity via
the same local Chroma/ONNX MiniLM model already used for taxonomy mention
matching (core/taxonomy.py's match_mention), so postings worded differently
from the taxonomy still surface. Neither path calls an LLM.
"""
from sqlalchemy.orm import Session

from ..core.taxonomy import load_taxonomy
from ..core.vectorstore import job_matching_collection
from ..db import crud, models
from ..providers import get_job_provider
from ..providers.base import Posting
from ..schemas import JobRecommendation
from .market_agent import _posting_skills

OVERLAP_WEIGHT = 0.7
SEMANTIC_WEIGHT = 0.3
IN_PROGRESS_WEIGHT = 0.4
FETCH_LIMIT = 50
RESULT_LIMIT = 15


def _user_skill_weights(db: Session, user_id: int, journey: models.LearningJourney) -> dict[str, float]:
    weights: dict[str, float] = {
        skill_id: history.depth_score / 10
        for skill_id, history in crud.get_latest_competency_per_skill(db, user_id).items()
    }
    for step in journey.steps:
        if step.status != "completed":
            weights[step.skill_id] = max(weights.get(step.skill_id, 0.0), IN_PROGRESS_WEIGHT)
    return weights


def _skill_profile_text(weights: dict[str, float], journey: models.LearningJourney) -> str:
    taxonomy = load_taxonomy()
    learning_ids = {s.skill_id for s in journey.steps if s.status != "completed"}
    have = [taxonomy[sid].name for sid in weights if sid in taxonomy and sid not in learning_ids]
    learning = [taxonomy[sid].name for sid in learning_ids if sid in taxonomy]
    parts = []
    if have:
        parts.append("Skilled in: " + ", ".join(have))
    if learning:
        parts.append("Currently learning: " + ", ".join(learning))
    return ". ".join(parts) or journey.target_role


def _overlap_score(posting: Posting, weights: dict[str, float]) -> tuple[float, list[str]]:
    taxonomy = load_taxonomy()
    matched_ids = [e["skill_id"] for e in _posting_skills(posting) if e["skill_id"] in taxonomy]
    if not matched_ids:
        return 0.0, []
    total = sum(weights.get(sid, 0.0) for sid in matched_ids)
    matched_names = [taxonomy[sid].name for sid in matched_ids if weights.get(sid, 0.0) > 0]
    return total / len(matched_ids), matched_names


def recommend_jobs(db: Session, user_id: int, journey: models.LearningJourney,
                   limit: int = RESULT_LIMIT) -> list[JobRecommendation]:
    weights = _user_skill_weights(db, user_id, journey)
    profile_text = _skill_profile_text(weights, journey)

    postings = get_job_provider().fetch(journey.target_role, limit=FETCH_LIMIT)
    if not postings:
        return []

    collection = job_matching_collection()
    collection.add(
        ids=[p["id"] for p in postings],
        documents=[f"{p['title']}\n{p['description']}" for p in postings],
    )
    # Chroma's default metric returns squared-L2 distance for the
    # unit-normalized ONNX MiniLM vectors it embeds with; for normalized
    # vectors that's cos_sim = 1 - distance/2 (clamped for float drift).
    query = collection.query(query_texts=[profile_text], n_results=len(postings))
    semantic_by_id = {
        pid: max(0.0, min(1.0, 1 - dist / 2))
        for pid, dist in zip(query["ids"][0], query["distances"][0])
    }

    scored: list[tuple[float, Posting, list[str]]] = []
    for posting in postings:
        overlap, matched_names = _overlap_score(posting, weights)
        semantic = semantic_by_id.get(posting["id"], 0.0)
        final_score = OVERLAP_WEIGHT * overlap + SEMANTIC_WEIGHT * semantic
        scored.append((final_score, posting, matched_names))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        JobRecommendation(
            posting_id=p["id"], title=p["title"], company=p["company"],
            location=p["location"], url=p.get("url", ""), score=round(score, 3),
            matched_skills=names,
        )
        for score, p, names in scored[:limit]
    ]
