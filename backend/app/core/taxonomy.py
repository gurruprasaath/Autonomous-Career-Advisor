"""Skill taxonomy: loading, normalization, and mention→node matching.

Matching is two-stage:
  1. exact/alias lookup (lowercased) — free and precise
  2. embedding similarity against the skills collection — catches
     paraphrases like "neural nets" → Deep Learning

This is deliberately NOT an LLM call: gap computation stays auditable.
"""
import json
from dataclasses import dataclass, field
from functools import lru_cache

from ..config import DATA_DIR
from ..schemas import Subtopic
from .vectorstore import skills_collection

# Chroma returns squared-L2 distance for unit-normalized ONNX MiniLM vectors.
# Calibrated on this taxonomy: true paraphrases ("neural nets"→Deep Learning)
# land at ≤1.06, unrelated mentions ("cooking pasta") at ≥1.53.
MATCH_DISTANCE_THRESHOLD = 1.25


@dataclass
class SkillNode:
    id: str
    name: str
    aliases: list[str]
    category: str
    prerequisites: list[str] = field(default_factory=list)


@lru_cache
def load_taxonomy() -> dict[str, SkillNode]:
    raw = json.loads((DATA_DIR / "skills_taxonomy.json").read_text(encoding="utf-8"))
    return {s["id"]: SkillNode(**s) for s in raw["skills"]}


@lru_cache
def _alias_index() -> dict[str, str]:
    """lowercased name/alias -> skill_id"""
    index: dict[str, str] = {}
    for node in load_taxonomy().values():
        index[node.name.lower()] = node.id
        index[node.id.lower()] = node.id
        for alias in node.aliases:
            index[alias.lower()] = node.id
    return index


def match_mention(mention: str) -> tuple[str, float] | None:
    """Map a free-text skill mention to (skill_id, confidence 0..1), or None."""
    text = mention.strip().lower()
    if not text:
        return None
    exact = _alias_index().get(text)
    if exact:
        return exact, 1.0
    res = skills_collection().query(query_texts=[mention], n_results=1)
    if not res["ids"] or not res["ids"][0]:
        return None
    distance = res["distances"][0][0]
    if distance > MATCH_DISTANCE_THRESHOLD:
        return None
    confidence = max(0.0, 1.0 - distance / MATCH_DISTANCE_THRESHOLD)
    return res["ids"][0][0], round(confidence, 3)


def match_mentions(mentions: list[str]) -> dict[str, str]:
    """Batch version: mention -> skill_id for all matchable mentions."""
    out: dict[str, str] = {}
    for m in mentions:
        hit = match_mention(m)
        if hit:
            out[m] = hit[0]
    return out


def prerequisite_order(skill_ids: list[str]) -> list[str]:
    """Topologically sort skill ids so prerequisites come first.

    Prerequisites outside the input set are ignored (the student either
    has them or they weren't demanded). Cycles can't occur: the taxonomy
    is authored as a DAG and validated at generation time.
    """
    nodes = load_taxonomy()
    in_set = set(skill_ids)
    visited: dict[str, bool] = {}
    order: list[str] = []

    def visit(sid: str) -> None:
        if visited.get(sid):
            return
        visited[sid] = True
        for pre in nodes[sid].prerequisites:
            if pre in in_set:
                visit(pre)
        order.append(sid)

    for sid in skill_ids:
        visit(sid)
    return order


# ---- curated sub-topics (skill_subtopics.json) ----

LEVEL_RANK = {"none": 0, "beginner": 1, "intermediate": 2, "advanced": 3}


@lru_cache
def load_subtopics() -> dict:
    return json.loads((DATA_DIR / "skill_subtopics.json").read_text(encoding="utf-8"))


def subtopics_for(skill_id: str) -> list[Subtopic]:
    entry = load_subtopics()["skills"].get(skill_id)
    return [Subtopic(**t) for t in entry["subtopics"]] if entry else []


def roadmap_url_for(skill_id: str) -> str:
    entry = load_subtopics()["skills"].get(skill_id)
    return entry["roadmap_url"] if entry else ""


def select_subtopics(skill_id: str, current_level: str, required_level: str) -> list[Subtopic]:
    """Sub-topics strictly above what the learner already has, up to what the
    role requires. Falls back to the required level's sub-topics, then to all
    of them, so a gap step is never left without a curriculum."""
    subs = subtopics_for(skill_id)
    current = LEVEL_RANK.get(current_level, 0)
    required = LEVEL_RANK.get(required_level, 0)
    window = [t for t in subs if current < LEVEL_RANK[t.level] <= required]
    if window:
        return window
    at_required = [t for t in subs if t.level == required_level]
    return at_required or subs
