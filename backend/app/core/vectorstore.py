"""ChromaDB collections for taxonomy skills, job postings, and courses.

Uses Chroma's built-in ONNX MiniLM embedding function — no torch, no GPU,
no API key needed. Collections are rebuilt from the JSON data files when
their document counts drift (cheap at this dataset size).
"""
import json
from functools import lru_cache

import chromadb

from ..config import CHROMA_DIR, DATA_DIR


@lru_cache
def get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _rebuild(collection, ids, documents, metadatas):
    if collection.count() != len(ids):
        existing = collection.get(include=[])["ids"]
        if existing:
            collection.delete(ids=existing)
        collection.add(ids=ids, documents=documents, metadatas=metadatas)


@lru_cache
def skills_collection():
    """One document per taxonomy skill: name + aliases, for fuzzy mention matching."""
    col = get_client().get_or_create_collection("skills")
    skills = _load("skills_taxonomy.json")["skills"]
    _rebuild(
        col,
        ids=[s["id"] for s in skills],
        documents=[f"{s['name']}. Also known as: {', '.join(s['aliases']) or s['name']}"
                   for s in skills],
        metadatas=[{"name": s["name"], "category": s["category"]} for s in skills],
    )
    return col


@lru_cache
def postings_collection():
    """Job postings for RAG retrieval by the Market Demand Agent."""
    col = get_client().get_or_create_collection("postings")
    postings = _load("jobs_sample.json")["postings"]
    _rebuild(
        col,
        ids=[p["id"] for p in postings],
        documents=[f"{p['title']} at {p['company']}, {p['location']}.\n{p['description']}"
                   for p in postings],
        metadatas=[{"role": p["role"], "company": p["company"]} for p in postings],
    )
    return col


@lru_cache
def courses_collection():
    """Course catalog, retrievable by skill for the Curriculum Planner."""
    col = get_client().get_or_create_collection("courses")
    courses = _load("courses_sample.json")["courses"]
    _rebuild(
        col,
        ids=[c["id"] for c in courses],
        documents=[f"{c['title']} by {c['provider']} (teaches skill: {c['skill_id']})"
                   for c in courses],
        metadatas=[{"skill_id": c["skill_id"], "title": c["title"],
                    "provider": c["provider"], "url": c["url"], "free": c["free"]}
                   for c in courses],
    )
    return col


def warm_up() -> dict[str, int]:
    """Build all collections eagerly (called on app startup)."""
    return {
        "skills": skills_collection().count(),
        "postings": postings_collection().count(),
        "courses": courses_collection().count(),
    }
