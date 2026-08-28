"""ChromaDB collections for taxonomy skills, job postings, and courses.

Uses Chroma's built-in ONNX MiniLM embedding function — no torch, no GPU,
no API key needed. Collections are rebuilt from the JSON data files when
their document counts drift (cheap at this dataset size).
"""
import hashlib
import json
import threading
import uuid
from functools import lru_cache

import chromadb

from ..config import CHROMA_DIR, DATA_DIR

# The bundled chromadb PersistentClient is not safe for concurrent use from
# multiple threads — reproduced directly: two threads each running
# create-collection + add + query + delete-collection against it at once
# corrupt its internal Rust-bindings state (AttributeError on
# RustBindingsAPI, KeyError on the .chroma path). FastAPI runs sync
# endpoint functions in a threadpool, so two overlapping requests hit this
# exact scenario. job_matcher.recommend_jobs serializes its whole
# create/add/query/delete sequence on this lock.
# ponytail: one global lock serializes every caller, not just ones sharing
# a collection — fine at this app's scale (a single-user demo, not a
# multi-tenant service); narrow it (per-collection lock, or a client per
# request) if concurrent load ever matters.
chroma_lock = threading.Lock()


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


def _repo_collection_name(user_id: int, username: str, repo_name: str) -> str:
    # A hash of the real "owner/repo" string avoids the lossy dash/dot
    # substitution the old naming scheme used (which let e.g. "alice/foo-bar"
    # and "alice-foo/bar" collide); user_id scopes collections per-user so
    # one learner's repo chat can't leak into another's.
    digest = hashlib.sha256(f"{username}/{repo_name}".encode()).hexdigest()[:16]
    return f"repo_{user_id}_{digest}"


def repo_collection(user_id: int, username: str, repo_name: str) -> chromadb.Collection:
    """Per-user collection for a specific GitHub repository's contents."""
    return get_client().get_or_create_collection(_repo_collection_name(user_id, username, repo_name))


def reset_repo_collection(user_id: int, username: str, repo_name: str) -> chromadb.Collection:
    """Drop and recreate the collection for a fresh re-index — avoids the
    non-transactional get-all-ids-then-delete-then-re-add round trip."""
    name = _repo_collection_name(user_id, username, repo_name)
    client = get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass  # collection didn't exist yet — nothing to drop
    return client.get_or_create_collection(name)


def job_matching_collection() -> tuple[chromadb.Collection, str]:
    """A fresh, uniquely-named ephemeral collection for one
    /api/jobs/recommendations request's scored postings.

    Deliberately NOT a single shared name: two /api/jobs/recommendations
    requests running concurrently (two users, or the same user with two
    open tabs) would otherwise race on each other's delete/add/query calls
    against the same underlying Chroma collection — reproduced directly as
    real chromadb errors (RustBindingsAPI/KeyError) when exercised with two
    threads. A unique name per call makes that race structurally
    impossible. Callers must drop the collection via
    drop_job_matching_collection() once they're done with it, so scratch
    collections don't accumulate in the persistent Chroma store."""
    name = f"job_matching_scratch_{uuid.uuid4().hex}"
    return get_client().get_or_create_collection(name), name


def drop_job_matching_collection(name: str) -> None:
    try:
        get_client().delete_collection(name)
    except Exception:
        pass  # already gone — nothing to drop


def warm_up() -> dict[str, int]:
    """Build all collections eagerly (called on app startup)."""
    return {
        "skills": skills_collection().count(),
        "postings": postings_collection().count(),
        "courses": courses_collection().count(),
    }
