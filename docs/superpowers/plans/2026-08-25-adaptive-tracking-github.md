# Adaptive Tracking + GitHub Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the manual tracker status dropdown with automatic signals (quiz, confidence rating, timer, GitHub public-repo evidence), and wire the currently-mocked "Recalculate Sub-Path" button to a real re-planning call.

**Architecture:** Extend the existing SQLAlchemy models (`PathStep`, `User`, `LearningJourney`) with new columns/tables, add a GitHub public-API provider and a quiz-generation agent (both following the existing `providers/` and `agents/` patterns), add four new FastAPI endpoints, and rework `LearningTracker.jsx` to drive them. Re-planning reuses the existing `build_path`/`verify_path` functions — no new pipeline.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), httpx (already a dependency, used for GitHub's public REST API), the existing Ollama-backed `invoke_llm`, React.

## Global Constraints

- No git commits in this plan — this project is not a git repository. Each task's final step is a verification run instead.
- No new Python packages — `httpx` is already in `requirements.txt`.
- GitHub calls use the public, unauthenticated API only (`api.github.com`, no token). No OAuth.
- Language→skill mapping is via the existing `match_mention()` (exact alias, then embedding fallback) — do not hand-roll a second matcher.
- SQLite has no live migration tool in this project (no Alembic) — new columns are added via a small raw-SQL migration helper, not by editing existing rows.

---

### Task 1: DB migration helper + model changes

**Files:**
- Modify: `backend/app/db/database.py`
- Modify: `backend/app/db/models.py`
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Produces: `database.run_migrations(engine)` — idempotent, called once at app startup.
- Produces: `models.PathStep.quiz_score` (`Integer`, nullable), `models.PathStep.confidence_rating` (`Integer`, nullable), `models.PathStep.time_spent_minutes` (`Integer`, default 0).
- Produces: `models.User.github_username` (`String`, nullable).
- Produces: `models.LearningJourney.gap_report_json` (`Text`, nullable), `models.LearningJourney.hours_per_week` (`Integer`, default 10).
- Produces: `models.GithubEvidence` table: `id, user_id, skill_id, repo_name, repo_language, last_pushed_at (DateTime), detected_at (DateTime)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_migrations.py`:

```python
"""Migration helper is idempotent and adds the expected columns."""
import sqlalchemy as sa
from sqlalchemy import create_engine

from app.db.database import run_migrations
from app.db import models


def test_migrations_add_columns_and_are_idempotent():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)

    run_migrations(engine)
    run_migrations(engine)  # must not raise on second run

    inspector = sa.inspect(engine)
    path_step_cols = {c["name"] for c in inspector.get_columns("path_steps")}
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    journey_cols = {c["name"] for c in inspector.get_columns("journeys")}

    assert {"quiz_score", "confidence_rating", "time_spent_minutes"} <= path_step_cols
    assert "github_username" in user_cols
    assert {"gap_report_json", "hours_per_week"} <= journey_cols
    assert "github_evidence" in inspector.get_table_names()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_migrations.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_migrations'` (doesn't exist yet), and `models.GithubEvidence` doesn't exist.

- [ ] **Step 3: Add the new model fields and table**

In `backend/app/db/models.py`, add `Text` isn't yet imported alongside `Integer`/`Float` — check the existing import line and extend it. Update the `User`, `LearningJourney`, and `PathStep` classes and add `GithubEvidence`:

```python
from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    github_username = Column(String, nullable=True)

    journeys = relationship("LearningJourney", back_populates="user")

class LearningJourney(Base):
    __tablename__ = "journeys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_role = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    gap_report_json = Column(Text, nullable=True)  # GapReport, serialized — needed to regenerate remaining steps
    hours_per_week = Column(Integer, default=10)

    user = relationship("User", back_populates="journeys")
    steps = relationship("PathStep", back_populates="journey")

class PathStep(Base):
    __tablename__ = "path_steps"
    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"))
    order = Column(Integer)
    skill_id = Column(String)
    skill_name = Column(String)
    objective = Column(String)
    milestone = Column(String)
    estimated_weeks = Column(Float)
    status = Column(String, default="pending") # pending, in_progress, struggling, completed
    resources_json = Column(Text, default="[]") # JSON string of resources
    quiz_score = Column(Integer, nullable=True)       # 0-100
    confidence_rating = Column(Integer, nullable=True)  # 1-5
    time_spent_minutes = Column(Integer, default=0)

    journey = relationship("LearningJourney", back_populates="steps")

class GithubEvidence(Base):
    __tablename__ = "github_evidence"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    skill_id = Column(String)
    repo_name = Column(String)
    repo_language = Column(String)
    last_pushed_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 4: Add the migration helper**

In `backend/app/db/database.py`, add below the existing `get_db` function:

```python
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./advisor.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLite ADD COLUMN is safe for existing tables; there's no Alembic here, so
# this is a deliberately minimal "add columns if missing" migration — not a
# general migration system.
def run_migrations(engine) -> None:
    statements = [
        "ALTER TABLE path_steps ADD COLUMN quiz_score INTEGER",
        "ALTER TABLE path_steps ADD COLUMN confidence_rating INTEGER",
        "ALTER TABLE path_steps ADD COLUMN time_spent_minutes INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN github_username VARCHAR",
        "ALTER TABLE journeys ADD COLUMN gap_report_json TEXT",
        "ALTER TABLE journeys ADD COLUMN hours_per_week INTEGER DEFAULT 10",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except OperationalError:
                conn.rollback()  # column already exists — fine
```

Note: `create_engine`/`SessionLocal`/`Base`/`get_db` already exist in this file —
only add the `text`/`OperationalError` imports and the new `run_migrations`
function; don't duplicate the existing declarations.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_migrations.py -v`
Expected: PASS

- [ ] **Step 6: Verify (no git repo — run the full existing suite instead of committing)**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS, including the pre-existing `tests/test_core.py`.

---

### Task 2: Wire the migration into app startup

**Files:**
- Modify: `backend/app/main.py:23-30` (the `lifespan` function)

**Interfaces:**
- Consumes: `database.run_migrations(engine)` from Task 1.

- [ ] **Step 1: Update the import and lifespan function**

In `backend/app/main.py`, change:

```python
from .db import database, models, crud, auth
```

to:

```python
from .db import database, models, crud, auth
from .db.database import engine, run_migrations
```

and change the `lifespan` function body from:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    counts = warm_up()
```

to:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    run_migrations(engine)
    counts = warm_up()
```

- [ ] **Step 2: Verify the server starts and picks up new columns**

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8090` (a scratch port, doesn't disturb whatever's already running), then in another terminal:
`curl http://localhost:8090/api/health`
Expected: `{"status":"ok", ...}` with no startup errors in the server log. Stop the scratch server (Ctrl+C) once confirmed.

---

### Task 3: GitHub provider

**Files:**
- Create: `backend/app/providers/github.py`
- Test: `backend/tests/test_github_provider.py`

**Interfaces:**
- Produces: `fetch_repo_languages(username: str) -> dict[str, list[dict]]` — keys are GitHub language names (e.g. `"Python"`), values are lists of `{"repo_name": str, "last_pushed_at": str}` (ISO 8601 string, from the repo's `pushed_at` field).
- Raises: `GithubUserNotFound` (username doesn't exist, 404) and `GithubRateLimited` (403/429) — both subclasses of `RuntimeError`, so callers can catch either narrowly or broadly.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_github_provider.py`:

```python
"""GitHub public-repo language fetch. Mocks httpx — no real network calls."""
from unittest.mock import patch, MagicMock

import pytest

from app.providers.github import (
    GithubRateLimited,
    GithubUserNotFound,
    fetch_repo_languages,
)


def _mock_response(status_code, json_data):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


REPOS = [
    {"name": "my-api", "pushed_at": "2026-07-01T00:00:00Z", "fork": False},
    {"name": "old-website", "pushed_at": "2024-01-01T00:00:00Z", "fork": False},
    {"name": "forked-repo", "pushed_at": "2026-08-01T00:00:00Z", "fork": True},
]

LANGUAGES_BY_REPO = {
    "my-api": {"Python": 9000, "Dockerfile": 40},
    "old-website": {"JavaScript": 5000, "HTML": 1000},
}


def test_aggregates_languages_across_repos_skips_forks():
    with patch("app.providers.github.httpx.get") as mock_get:
        def side_effect(url, **kwargs):
            if url.endswith("/repos"):
                return _mock_response(200, REPOS)
            for repo_name, langs in LANGUAGES_BY_REPO.items():
                if f"/repos/testuser/{repo_name}/languages" in url:
                    return _mock_response(200, langs)
            return _mock_response(200, {})

        mock_get.side_effect = side_effect

        result = fetch_repo_languages("testuser")

        assert "Python" in result
        assert result["Python"][0]["repo_name"] == "my-api"
        assert "JavaScript" in result
        # forked-repo must never be queried or appear in results
        assert all(r["repo_name"] != "forked-repo"
                   for repos in result.values() for r in repos)


def test_unknown_user_raises():
    with patch("app.providers.github.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(404, {})
        with pytest.raises(GithubUserNotFound):
            fetch_repo_languages("no-such-user-xyz")


def test_rate_limit_raises():
    with patch("app.providers.github.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(403, {})
        with pytest.raises(GithubRateLimited):
            fetch_repo_languages("testuser")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_github_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.providers.github'`

- [ ] **Step 3: Write the provider**

Create `backend/app/providers/github.py`:

```python
"""GitHub public-repo language fetch — unauthenticated public API only.

No OAuth: the student types their GitHub username, we read what's already
public. Good enough to answer "have they actually written code in this
language recently," which is the only claim this evidence makes.
"""
import httpx

GITHUB_API = "https://api.github.com"


class GithubUserNotFound(RuntimeError):
    pass


class GithubRateLimited(RuntimeError):
    pass


def fetch_repo_languages(username: str) -> dict[str, list[dict]]:
    """username -> {language: [{"repo_name", "last_pushed_at"}, ...]}.

    Forked repos are skipped (they're not evidence the student wrote that
    code). Unauthenticated GitHub API allows 60 requests/hour, which is
    enough for one user's repo list plus a handful of language lookups.
    """
    repos_resp = httpx.get(f"{GITHUB_API}/users/{username}/repos",
                           params={"per_page": 100}, timeout=10)
    if repos_resp.status_code == 404:
        raise GithubUserNotFound(username)
    if repos_resp.status_code in (403, 429):
        raise GithubRateLimited("GitHub API rate limit hit; try again later")
    repos_resp.raise_for_status()

    result: dict[str, list[dict]] = {}
    for repo in repos_resp.json():
        if repo.get("fork"):
            continue
        lang_resp = httpx.get(
            f"{GITHUB_API}/repos/{username}/{repo['name']}/languages", timeout=10)
        if lang_resp.status_code != 200:
            continue
        for language in lang_resp.json():
            result.setdefault(language, []).append({
                "repo_name": repo["name"],
                "last_pushed_at": repo["pushed_at"],
            })
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_github_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Verify**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS.

---

### Task 4: crud.py additions — progress recording + GitHub evidence

**Files:**
- Modify: `backend/app/db/crud.py`
- Test: `backend/tests/test_progress.py`

**Interfaces:**
- Consumes: `models.PathStep`, `models.GithubEvidence` from Task 1.
- Produces: `record_step_progress(db, step_id, *, quiz_score=None, confidence_rating=None, minutes_delta=0) -> PathStep | None`.
- Produces: `replace_github_evidence(db, user_id, evidence_rows: list[dict]) -> None` — `evidence_rows` items are `{"skill_id", "repo_name", "repo_language", "last_pushed_at"}`.
- Produces: `get_github_evidence_by_skill(db, user_id) -> dict[str, list[GithubEvidence]]`.
- Produces: `create_learning_journey(db, user_id, target_role, gap_report_json, hours_per_week)` — signature changed from the current 3-arg version.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_progress.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_progress.py -v`
Expected: FAIL — `TypeError: create_learning_journey() got an unexpected keyword argument 'gap_report_json'`

- [ ] **Step 3: Update crud.py**

In `backend/app/db/crud.py`, replace `create_learning_journey` and `update_step_status`, and add the two new functions:

```python
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
```

Note: `update_step_status` is removed entirely — `record_step_progress` replaces
it. Task 6 updates `main.py` to match.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_progress.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Verify**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS.

---

### Task 5: Quiz agent

**Files:**
- Create: `backend/app/agents/quiz_agent.py`
- Test: `backend/tests/test_quiz_agent.py`

**Interfaces:**
- Consumes: `invoke_llm`, `get_llm`, `extract_json` from `app.core.llm` (existing).
- Produces: `generate_quiz(skill_name: str, objective: str) -> list[dict]` — each dict is `{"question": str, "options": list[str] (len 4), "correct_index": int (0-3)}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quiz_agent.py`:

```python
"""Quiz agent: prompts the LLM, validates and returns well-formed MCQs."""
from unittest.mock import MagicMock, patch

from app.agents.quiz_agent import generate_quiz


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def test_generate_quiz_returns_validated_questions():
    fake_json = """[
      {"question": "What hook manages state in a function component?",
       "options": ["useEffect", "useState", "useRef", "useMemo"], "correct_index": 1},
      {"question": "What does JSX compile to?",
       "options": ["HTML", "React.createElement calls", "CSS", "JSON"], "correct_index": 1}
    ]"""
    with patch("app.agents.quiz_agent.get_llm") as mock_get_llm, \
         patch("app.agents.quiz_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        questions = generate_quiz("React", "Build components with hooks")

    assert len(questions) == 2
    assert questions[0]["options"][questions[0]["correct_index"]] == "useState"


def test_generate_quiz_drops_malformed_questions():
    fake_json = """[
      {"question": "Valid one", "options": ["a", "b", "c", "d"], "correct_index": 0},
      {"question": "Missing options", "options": ["a", "b"], "correct_index": 0},
      {"question": "Bad index", "options": ["a", "b", "c", "d"], "correct_index": 9}
    ]"""
    with patch("app.agents.quiz_agent.get_llm") as mock_get_llm, \
         patch("app.agents.quiz_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        questions = generate_quiz("React", "Build components with hooks")

    assert len(questions) == 1
    assert questions[0]["question"] == "Valid one"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_quiz_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.quiz_agent'`

- [ ] **Step 3: Write the quiz agent**

Create `backend/app/agents/quiz_agent.py`:

```python
"""Quiz Agent — generates a short multiple-choice check for one path step.

Malformed questions (wrong option count, out-of-range correct_index) are
dropped rather than surfaced — a partially-broken quiz of 2-3 good
questions is more useful than failing the whole request over one bad item.
"""
import logging

from ..config import get_settings
from ..core.llm import extract_json, get_llm, invoke_llm

log = logging.getLogger(__name__)

QUIZ_PROMPT = """You are writing a short comprehension check for a student who just studied "{skill}".
Their learning objective was: "{objective}"

Write 3 multiple-choice questions that test whether they actually understood this
objective (not trivia). Each question has exactly 4 options and exactly one
correct answer.

Return ONLY JSON:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": <0-3>}}]
"""


def generate_quiz(skill_name: str, objective: str) -> list[dict]:
    llm = get_llm(get_settings().fast_model)
    response = invoke_llm(llm, QUIZ_PROMPT.format(skill=skill_name, objective=objective))
    data = extract_json(response.content)
    if not isinstance(data, list):
        return []

    questions = []
    for item in data:
        options = item.get("options")
        correct_index = item.get("correct_index")
        if (isinstance(options, list) and len(options) == 4
                and isinstance(correct_index, int) and 0 <= correct_index < 4
                and item.get("question")):
            questions.append({
                "question": str(item["question"]),
                "options": [str(o) for o in options],
                "correct_index": correct_index,
            })
    return questions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_quiz_agent.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Verify**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS.

---

### Task 6: FastAPI endpoints — progress, quiz, GitHub sync

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `crud.record_step_progress`, `crud.replace_github_evidence`, `crud.get_github_evidence_by_skill` (Task 4); `providers.github.fetch_repo_languages`, `GithubUserNotFound`, `GithubRateLimited` (Task 3); `quiz_agent.generate_quiz` (Task 5); `core.taxonomy.match_mention` (existing).

- [ ] **Step 1: Replace the status endpoint with the progress endpoint**

In `backend/app/main.py`, replace:

```python
@app.post("/api/tracker/step/{step_id}/status")
def update_step_status(step_id: int, status: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if status not in ["pending", "in_progress", "struggling", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    step = crud.update_step_status(db, step_id, status)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    import json
    return {
        "id": step.id,
        "status": step.status,
        "skill_name": step.skill_name
    }
```

with:

```python
class ProgressUpdate(BaseModel):
    quiz_score: int | None = None
    confidence_rating: int | None = None
    minutes_delta: int = 0

@app.post("/api/tracker/step/{step_id}/progress")
def record_progress(step_id: int, update: ProgressUpdate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    if update.confidence_rating is not None and not (1 <= update.confidence_rating <= 5):
        raise HTTPException(400, "confidence_rating must be 1-5")
    if update.quiz_score is not None and not (0 <= update.quiz_score <= 100):
        raise HTTPException(400, "quiz_score must be 0-100")
    step = crud.record_step_progress(
        db, step_id, quiz_score=update.quiz_score,
        confidence_rating=update.confidence_rating, minutes_delta=update.minutes_delta)
    if not step:
        raise HTTPException(404, "Step not found")
    return {"id": step.id, "status": step.status, "skill_name": step.skill_name,
           "quiz_score": step.quiz_score, "confidence_rating": step.confidence_rating,
           "time_spent_minutes": step.time_spent_minutes}


@app.post("/api/tracker/step/{step_id}/quiz")
def get_step_quiz(step_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    from .agents.quiz_agent import generate_quiz
    step = db.query(models.PathStep).filter(models.PathStep.id == step_id).first()
    if not step:
        raise HTTPException(404, "Step not found")
    questions = generate_quiz(step.skill_name, step.objective)
    if not questions:
        raise HTTPException(502, "Could not generate a quiz for this step right now")
    return {"questions": questions}


class GithubSyncRequest(BaseModel):
    username: str

@app.post("/api/github/sync")
def sync_github(req: GithubSyncRequest, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    from .providers.github import GithubRateLimited, GithubUserNotFound, fetch_repo_languages
    from .core.taxonomy import match_mention

    try:
        languages = fetch_repo_languages(req.username)
    except GithubUserNotFound:
        raise HTTPException(404, f"GitHub user '{req.username}' not found")
    except GithubRateLimited as e:
        raise HTTPException(429, str(e))

    current_user.github_username = req.username
    db.commit()

    evidence_rows = []
    for language, repos in languages.items():
        hit = match_mention(language)
        if not hit:
            continue
        skill_id = hit[0]
        for repo in repos:
            evidence_rows.append({
                "skill_id": skill_id, "repo_name": repo["repo_name"],
                "repo_language": language, "last_pushed_at": repo["last_pushed_at"],
            })
    crud.replace_github_evidence(db, current_user.id, evidence_rows)
    return {"matched_skills": sorted({r["skill_id"] for r in evidence_rows}),
           "evidence_count": len(evidence_rows)}
```

Add the `BaseModel` import at the top of `main.py` (it isn't imported yet) —
change:

```python
from .schemas import AdviseRequest, AdvisorResult, UserCreate, Token
```

to:

```python
from pydantic import BaseModel

from .schemas import AdviseRequest, AdvisorResult, UserCreate, Token
```

- [ ] **Step 2: Extend `get_journeys` to include the new fields and GitHub evidence**

Replace the `get_journeys` function body's dict comprehension:

```python
@app.get("/api/tracker/journeys")
def get_journeys(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from sqlalchemy.orm import joinedload
    journeys = db.query(models.LearningJourney).options(joinedload(models.LearningJourney.steps)).filter(models.LearningJourney.user_id == current_user.id).order_by(models.LearningJourney.created_at.desc()).all()

    evidence_by_skill = crud.get_github_evidence_by_skill(db, current_user.id)

    result = []
    for j in journeys:
        import json
        j_dict = {
            "id": j.id,
            "target_role": j.target_role,
            "created_at": j.created_at.isoformat(),
            "steps": [
                {
                    "id": s.id,
                    "order": s.order,
                    "skill_id": s.skill_id,
                    "skill_name": s.skill_name,
                    "objective": s.objective,
                    "milestone": s.milestone,
                    "estimated_weeks": s.estimated_weeks,
                    "status": s.status,
                    "quiz_score": s.quiz_score,
                    "confidence_rating": s.confidence_rating,
                    "time_spent_minutes": s.time_spent_minutes,
                    "resources": json.loads(s.resources_json) if s.resources_json else [],
                    "github_evidence": [
                        {"repo_name": e.repo_name, "last_pushed_at":
                         e.last_pushed_at.isoformat() if hasattr(e.last_pushed_at, "isoformat") else e.last_pushed_at}
                        for e in evidence_by_skill.get(s.skill_id, [])
                    ],
                } for s in sorted(j.steps, key=lambda x: x.order)
            ]
        }
        result.append(j_dict)
    return result
```

- [ ] **Step 3: Verify manually against a scratch server**

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8090`

In another terminal, register a user and check the new endpoints exist (401 without a real journey/step is expected and fine — this just confirms the routes are wired):

```bash
curl -s -X POST http://localhost:8090/api/auth/register -H "Content-Type: application/json" -d "{\"email\":\"plantest@example.com\",\"password\":\"testpass123\"}"
```

Expected: `{"access_token": "...", "token_type": "bearer"}` — copy the token, then:

```bash
curl -s -X POST http://localhost:8090/api/github/sync -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"username\":\"torvalds\"}"
```

Expected: `{"matched_skills": [...], "evidence_count": <number > 0>}` (Linus
Torvalds' public repos are almost entirely C, so expect `"c"` if that's in
the taxonomy, otherwise an empty/small match list — either is fine, it just
confirms the endpoint runs end to end without erroring).

Stop the scratch server (Ctrl+C).

---

### Task 7: Persist `gap_report_json` / `hours_per_week` when a journey is created

**Files:**
- Modify: `backend/app/main.py:66-80` (the `advise` endpoint)

**Interfaces:**
- Consumes: `crud.create_learning_journey(db, user_id, target_role, gap_report_json, hours_per_week)` (Task 4's new signature).

- [ ] **Step 1: Update the `advise` endpoint**

Replace:

```python
@app.post("/api/advise", response_model=AdvisorResult)
def advise(request: AdviseRequest, token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)), db: Session = Depends(get_db)):
    if not request.resume_text.strip():
        raise HTTPException(422, "resume_text must not be empty")
    if not request.target_role.strip():
        raise HTTPException(422, "target_role must not be empty")
    try:
        result = run_advisor(request)
        if token and result.path:
            user = get_current_user(token, db)
            journey = crud.create_learning_journey(db, user.id, result.path.target_role)
            crud.create_path_steps(db, journey.id, result.path.steps)
        return result
    except ValueError as e:  # e.g. unknown role
        raise HTTPException(400, str(e))
```

with:

```python
@app.post("/api/advise", response_model=AdvisorResult)
def advise(request: AdviseRequest, token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)), db: Session = Depends(get_db)):
    if not request.resume_text.strip():
        raise HTTPException(422, "resume_text must not be empty")
    if not request.target_role.strip():
        raise HTTPException(422, "target_role must not be empty")
    try:
        result = run_advisor(request)
        if token and result.path:
            user = get_current_user(token, db)
            journey = crud.create_learning_journey(
                db, user.id, result.path.target_role,
                gap_report_json=result.gap_report.model_dump_json(),
                hours_per_week=request.hours_per_week)
            crud.create_path_steps(db, journey.id, result.path.steps)
        return result
    except ValueError as e:  # e.g. unknown role
        raise HTTPException(400, str(e))
```

- [ ] **Step 2: Verify with a real end-to-end request**

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8090`, then (reusing the token from Task 6's manual check, or registering a fresh user first):

```bash
curl -s -X POST http://localhost:8090/api/advise -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"resume_text\":\"Final year CS student. Know Python and basic SQL.\",\"target_role\":\"Data Scientist\",\"hours_per_week\":10}"
```

Expected: `200 OK` with a full `AdvisorResult`. Then:

```bash
curl -s http://localhost:8090/api/tracker/journeys -H "Authorization: Bearer <token>"
```

Expected: a journey with steps present — confirms `gap_report_json` didn't
break journey/step creation. Stop the scratch server (Ctrl+C).

---

### Task 8: Recalculate endpoint (adaptive re-planning)

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `planner_agent.build_path(profile, gap_report, revision_request)`, `verifier_agent.verify_path(path, gap_report, profile)` (existing, unchanged signatures).

- [ ] **Step 1: Add the recalculate endpoint**

Add to `backend/app/main.py`, after the `sync_github` endpoint:

```python
@app.post("/api/tracker/journey/{journey_id}/recalculate")
def recalculate_journey(journey_id: int, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    import json
    from .agents.planner_agent import build_path
    from .agents.verifier_agent import verify_path
    from .schemas import GapReport, StudentProfile

    journey = db.query(models.LearningJourney).filter(
        models.LearningJourney.id == journey_id,
        models.LearningJourney.user_id == current_user.id).first()
    if not journey:
        raise HTTPException(404, "Journey not found")

    all_steps = db.query(models.PathStep).filter(models.PathStep.journey_id == journey_id).all()
    completed = [s for s in all_steps if s.status == "completed"]
    remaining = [s for s in all_steps if s.status != "completed"]
    if not remaining:
        raise HTTPException(400, "No remaining steps to recalculate — every step is completed")

    struggling = [s for s in remaining if s.status == "struggling"]
    revision_request = "Student is struggling with: " + "; ".join(
        f"{s.skill_name} (quiz_score={s.quiz_score}, confidence={s.confidence_rating})"
        for s in struggling
    ) if struggling else "Regenerate the remaining steps with fresh pacing."

    full_gap_report = GapReport(**json.loads(journey.gap_report_json or "{}"))
    remaining_skill_ids = {s.skill_id for s in remaining}
    partial_gap_report = GapReport(
        target_role=full_gap_report.target_role,
        gaps=[g for g in full_gap_report.gaps if g.skill_id in remaining_skill_ids],
        strengths=full_gap_report.strengths,
    )
    profile = StudentProfile(hours_per_week=journey.hours_per_week, target_role=journey.target_role)

    path, _notes = build_path(profile, partial_gap_report, revision_request=revision_request)
    critique, _notes2 = verify_path(path, partial_gap_report, profile)
    if not critique.passed and critique.revision_request:
        path, _notes3 = build_path(profile, partial_gap_report, revision_request=critique.revision_request)

    for step in remaining:
        db.delete(step)
    db.commit()

    next_order = (max((s.order for s in completed), default=0)) + 1
    for i, step in enumerate(path.steps):
        db.add(models.PathStep(
            journey_id=journey_id, order=next_order + i, skill_id=step.skill_id,
            skill_name=step.skill_name, objective=step.objective, milestone=step.milestone,
            estimated_weeks=step.estimated_weeks,
            resources_json=json.dumps([r.model_dump() for r in step.resources]),
        ))
    db.commit()

    return {"journey_id": journey_id, "regenerated_steps": len(path.steps),
           "kept_completed_steps": len(completed)}
```

- [ ] **Step 2: Verify manually**

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8090`

Using the journey created in Task 7's verification, mark a step struggling
and recalculate (replace `<step_id>` and `<journey_id>` with real values from
`GET /api/tracker/journeys`):

```bash
curl -s -X POST http://localhost:8090/api/tracker/step/<step_id>/progress -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"quiz_score\":20,\"confidence_rating\":1}"
```

Expected: `"status": "struggling"`. Then:

```bash
curl -s -X POST http://localhost:8090/api/tracker/journey/<journey_id>/recalculate -H "Authorization: Bearer <token>"
```

Expected: `200 OK` with `regenerated_steps` > 0 (may take 30-90s — this calls
the local LLM). This is the slow path in the whole feature; that's expected,
not a bug. Stop the scratch server (Ctrl+C).

---

### Task 9: Frontend API client additions

**Files:**
- Modify: `frontend/src/api.js`

**Interfaces:**
- Produces: `recordProgress(stepId, {quiz_score, confidence_rating, minutes_delta})`, `getStepQuiz(stepId)`, `syncGithub(username)`, `recalculateJourney(journeyId)`.

- [ ] **Step 1: Replace `updateStepStatus` and add the new calls**

In `frontend/src/api.js`, replace:

```javascript
export const updateStepStatus = (stepId, status) =>
  request(`/api/tracker/step/${stepId}/status?status=${status}`, { method: "POST" });
```

with:

```javascript
export const recordProgress = (stepId, update) =>
  request(`/api/tracker/step/${stepId}/progress`, {
    method: "POST", body: JSON.stringify(update),
  });

export const getStepQuiz = (stepId) =>
  request(`/api/tracker/step/${stepId}/quiz`, { method: "POST" });

export const syncGithub = (username) =>
  request("/api/github/sync", { method: "POST", body: JSON.stringify({ username }) });

export const recalculateJourney = (journeyId) =>
  request(`/api/tracker/journey/${journeyId}/recalculate`, { method: "POST" });
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors (this only type/syntax-checks via
Vite's build, since there's no separate lint-on-save step configured for
this file).

---

### Task 10: LearningTracker.jsx — timer, confidence, quiz, GitHub, recalculate

**Files:**
- Modify: `frontend/src/components/LearningTracker.jsx`

**Interfaces:**
- Consumes: `recordProgress`, `getStepQuiz`, `syncGithub`, `recalculateJourney` from Task 9.

- [ ] **Step 1: Replace the whole file**

Replace `frontend/src/components/LearningTracker.jsx` in full:

```jsx
import { useState, useEffect, useRef } from "react";
import { getJourneys, recordProgress, getStepQuiz, syncGithub, recalculateJourney } from "../api";

function QuizModal({ step, onClose, onScored }) {
  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStepQuiz(step.id)
      .then((d) => setQuestions(d.questions))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [step.id]);

  const submit = () => {
    const correct = questions.filter((q, i) => answers[i] === q.correct_index).length;
    const score = Math.round((correct / questions.length) * 100);
    onScored(score);
  };

  return (
    <div className="card" style={{ maxWidth: 600, margin: "2rem auto" }}>
      <h2>Quiz: {step.skill_name}</h2>
      {loading && <p>Generating questions...</p>}
      {error && <div className="error-box">{error}</div>}
      {questions && questions.map((q, i) => (
        <div key={i} style={{ marginBottom: "1rem" }}>
          <p><strong>{i + 1}. {q.question}</strong></p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: "block", marginLeft: "1rem" }}>
              <input type="radio" name={`q${i}`} checked={answers[i] === oi}
                    onChange={() => setAnswers({ ...answers, [i]: oi })} /> {opt}
            </label>
          ))}
        </div>
      ))}
      {questions && (
        <button className="primary-button" onClick={submit}
               disabled={Object.keys(answers).length !== questions.length}>
          Submit
        </button>
      )}
      <button className="secondary-button" style={{ marginLeft: "0.5rem" }} onClick={onClose}>Cancel</button>
    </div>
  );
}

function StepTracker({ step, onChanged }) {
  const [running, setRunning] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [quizOpen, setQuizOpen] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  const stopAndSave = async () => {
    setRunning(false);
    const minutes = Math.round(elapsedSec / 60);
    if (minutes > 0) {
      await recordProgress(step.id, { minutes_delta: minutes });
      onChanged();
    }
    setElapsedSec(0);
  };

  const rateConfidence = async (rating) => {
    await recordProgress(step.id, { confidence_rating: rating });
    onChanged();
  };

  const budgetMinutes = step.estimated_weeks * 10 * 60; // rough: hours_per_week baked into estimated_weeks already
  const pct = Math.min(100, Math.round(((step.time_spent_minutes || 0) / Math.max(budgetMinutes, 1)) * 100));

  return (
    <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {!running ? (
          <button className="secondary-button" onClick={() => setRunning(true)}>▶ Start timer</button>
        ) : (
          <button className="secondary-button" onClick={stopAndSave}>⏸ Stop ({Math.floor(elapsedSec / 60)}m{elapsedSec % 60}s)</button>
        )}
        <span className="hint">{step.time_spent_minutes || 0}m logged · {pct}% of budget</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span className="hint">Confidence:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} className={`secondary-button ${step.confidence_rating === n ? "active" : ""}`}
                 style={{ padding: "4px 10px" }} onClick={() => rateConfidence(n)}>{n}</button>
        ))}
      </div>

      <div>
        <button className="primary-button" onClick={() => setQuizOpen(true)}>Take Quiz</button>
        {step.quiz_score != null && <span className="hint" style={{ marginLeft: "0.5rem" }}>Last score: {step.quiz_score}%</span>}
      </div>

      {step.github_evidence && step.github_evidence.length > 0 && (
        <div className="hint">
          ✓ GitHub evidence: {step.github_evidence.map((e) => e.repo_name).join(", ")}
        </div>
      )}

      {quizOpen && (
        <QuizModal step={step} onClose={() => setQuizOpen(false)}
                  onScored={async (score) => {
                    await recordProgress(step.id, { quiz_score: score });
                    setQuizOpen(false);
                    onChanged();
                  }} />
      )}
    </div>
  );
}

function GithubConnect({ onSynced }) {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("");

  const sync = async () => {
    if (!username.trim()) return;
    setStatus("Syncing...");
    try {
      const res = await syncGithub(username.trim());
      setStatus(`Matched ${res.matched_skills.length} skill(s) from ${res.evidence_count} repo entries.`);
      onSynced();
    } catch (e) {
      setStatus(e.message);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: "1.5rem" }}>
      <h2>Connect GitHub</h2>
      <p className="hint">We read your public repos' languages as evidence you've practiced a skill. No login required.</p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input className="input-field" placeholder="GitHub username" value={username}
              onChange={(e) => setUsername(e.target.value)} style={{ maxWidth: 300 }} />
        <button className="primary-button" onClick={sync}>Sync</button>
      </div>
      {status && <p className="hint">{status}</p>}
    </div>
  );
}

export default function LearningTracker() {
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recalculating, setRecalculating] = useState(null);

  const fetchJourneys = async () => {
    try {
      setLoading(true);
      const data = await getJourneys();
      setJourneys(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJourneys(); }, []);

  const recalculate = async (journeyId) => {
    setRecalculating(journeyId);
    try {
      await recalculateJourney(journeyId);
      await fetchJourneys();
    } catch (e) {
      alert("Recalculate failed: " + e.message);
    } finally {
      setRecalculating(null);
    }
  };

  if (loading) return <div>Loading journeys...</div>;
  if (error) return <div className="error-box">{error}</div>;

  return (
    <div className="tracker">
      <GithubConnect onSynced={fetchJourneys} />
      {journeys.length === 0 && <div>No learning paths generated yet. Go to Generate Path!</div>}
      {journeys.map((j) => {
        const hasStruggling = j.steps.some((s) => s.status === "struggling");
        return (
          <div key={j.id} className="panel" style={{ marginBottom: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2>Target Role: {j.target_role}</h2>
                <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
              </div>
              {hasStruggling && (
                <button className="primary-button" disabled={recalculating === j.id}
                       onClick={() => recalculate(j.id)}>
                  {recalculating === j.id ? "Recalculating..." : "Recalculate Sub-Path"}
                </button>
              )}
            </div>
            <div className="timeline">
              {j.steps.map((s) => (
                <div className={`tstep ${s.status === "completed" ? "done" : s.status === "struggling" ? "warn" : ""}`} key={s.id}>
                  <h3 style={{ margin: 0 }}>
                    {s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span>
                    <span className="hint" style={{ marginLeft: "0.5rem" }}>({s.status})</span>
                  </h3>
                  <p>{s.objective}</p>
                  <p className="milestone">🏁 {s.milestone}</p>
                  {s.resources && s.resources.length > 0 && (
                    <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {s.resources.map((r) => (
                        <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                          📚 {r.title} — {r.provider} {r.free ? "(free)" : ""}
                        </a>
                      ))}
                    </div>
                  )}
                  <StepTracker step={s} onChanged={fetchJourneys} />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Verify with the dev server**

Run: `cd frontend && npm run dev` (or confirm the already-running instance
picks up the change via HMR), navigate to `http://localhost:5173`, log in,
click "My Learning Tracker".

Expected:
- The GitHub connect box renders; entering a real GitHub username and
  clicking Sync shows a match count.
- If there's an existing journey, each step shows a timer, 1-5 confidence
  buttons, and a "Take Quiz" button.
- Clicking "Take Quiz" opens the modal, generates real questions (takes
  30-90s on the local model — expected), and submitting sets a score and
  updates the step's status/badge.
- Marking a step's confidence to 1 flips its status to `struggling` and the
  journey header shows a "Recalculate Sub-Path" button; clicking it
  regenerates the remaining steps (again, expect 30-90s).

---

## Self-Review Notes

- **Spec coverage:** data model (Task 1), GitHub sync (Tasks 3, 6), quiz
  (Tasks 5, 6), confidence + timer (Tasks 4, 6, 10), status derivation
  (Task 4), adaptive re-planning (Task 8) — all five spec sections have a
  task.
- **Type consistency checked:** `record_step_progress`'s keyword names
  (`quiz_score`, `confidence_rating`, `minutes_delta`) match the
  `ProgressUpdate` Pydantic model in Task 6 and the `recordProgress` calls
  in Task 10. `GapReport`/`StudentProfile` field names in Task 8 match
  `backend/app/schemas.py` exactly (`gaps`, `strengths`, `target_role`,
  `hours_per_week`).
- **Known limitation carried into the plan, not hidden:** the timer's
  "budget" percentage in `StepTracker` assumes 10 hours/week
  (`step.estimated_weeks * 10 * 60` minutes) because `estimated_weeks` on
  the persisted `PathStep` doesn't carry the journey's actual
  `hours_per_week` — it's a display-only approximation, not used in the
  completed/struggling logic, so the imprecision doesn't affect status
  derivation.
