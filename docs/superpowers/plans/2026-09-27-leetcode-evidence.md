# LeetCode Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a learner sync a public LeetCode username so their solved-problem record becomes a deterministic DSA depth input to competency scoring and a weak-topics list for interview prep.

**Architecture:** A new `providers/leetcode.py` fetches one GraphQL snapshot and holds the pure scoring functions (`dsa_depth`, `weak_topics`, `summarize`, `depth_for_skill`). The raw snapshot is stored as JSON on the `users` row; all derived numbers are recomputed from it. `assess_competency` gains an optional `leetcode_depth` component (weight 0.35), passed only for the `problem-solving` skill. Two endpoints (`POST /api/leetcode/sync`, `GET /api/leetcode`) and a `LeetcodeConnect` panel on the Tracker page complete it.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite, additive ALTER migrations), httpx, pytest; React 19 + TypeScript, TanStack Query, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-27-leetcode-evidence-design.md`

## Global Constraints

- LeetCode endpoint: `POST https://leetcode.com/graphql`, headers `Content-Type: application/json` and `Referer: https://leetcode.com`, timeout 10 s, no login.
- Missing user = HTTP 200 with `data.matchedUser == null` (verified live 2026-09-27; `recentAcSubmissionList` is `[]` in that case). Any other failure = "LeetCode unavailable".
- `dsa_depth = clamp(round(2 * log2(1 + (easy + 2*medium + 3*hard) / 15)), 1, 10)`; `None` when `easy + medium + hard == 0`.
- Competency weights: resume 0.30, quiz 0.40, confidence 0.15, **LeetCode 0.35**; GitHub stays additive +1.5. LeetCode only for skill id `problem-solving`.
- `CORE_TOPICS` (exact LeetCode tag names, this order): Array, String, Hash Table, Two Pointers, Sliding Window, Binary Search, Stack, Linked List, Tree, Graph Theory, Heap, Dynamic Programming, Greedy, Backtracking. Weak = fewer than 5 solves (absent = 0), ascending, ties by this order, limit 3.
- Username regex: `^[A-Za-z0-9_-]{1,30}$`.
- API errors: invalid username 400 `"Invalid LeetCode username"`; not found 404 `"LeetCode user '<name>' not found"`; unavailable 502 `"LeetCode is unavailable right now — try again later"`.
- Backend tests: run from `backend/` with `.venv/Scripts/python -m pytest`. Frontend tests: run from `frontend/` with `npx vitest run --pool=threads` (the default forks pool times out on this machine).
- Commit directly on `master` (this project's established practice). Do not stage the pre-existing unrelated changes (`frontend/vite.config.ts`, `docs/Research_Paper_Draft.md`, `node_modules/`, `temp_docx_text.txt`). Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: LeetCode provider

**Files:**
- Create: `backend/app/providers/leetcode.py`
- Test: `backend/tests/test_leetcode_provider.py`

**Interfaces:**
- Produces:
  - `class LeetcodeUserNotFound(RuntimeError)`, `class LeetcodeUnavailable(RuntimeError)`
  - `DSA_SKILL_ID: str = "problem-solving"`, `CORE_TOPICS: list[str]`
  - `fetch_profile(username: str) -> dict` → `{"easy": int, "medium": int, "hard": int, "topics": dict[str, int], "last_accepted_at": str | None}`
  - `dsa_depth(snapshot: dict) -> int | None`
  - `weak_topics(snapshot: dict, limit: int = 3) -> list[str]`
  - `summarize(username: str, snapshot: dict) -> dict` with keys `username, easy, medium, hard, total, dsa_depth, weak_topics, last_accepted_at, synced_at` (`synced_at` read from `snapshot.get("synced_at")`)
  - `depth_for_skill(skill_id: str, snapshot: dict | None) -> int | None`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_leetcode_provider.py`:

```python
"""LeetCode provider: pure scoring functions + fetch_profile with mocked httpx
(no real network calls)."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.providers.leetcode import (
    CORE_TOPICS,
    DSA_SKILL_ID,
    LeetcodeUnavailable,
    LeetcodeUserNotFound,
    depth_for_skill,
    dsa_depth,
    fetch_profile,
    summarize,
    weak_topics,
)


def _snap(easy=0, medium=0, hard=0, topics=None, **extra):
    return {"easy": easy, "medium": medium, "hard": hard,
            "topics": topics or {}, "last_accepted_at": None, **extra}


# ---- dsa_depth calibration table (from the spec) ----

@pytest.mark.parametrize("easy,medium,hard,expected", [
    (0, 0, 0, None),
    (20, 0, 0, 2),
    (100, 0, 0, 6),
    (50, 30, 0, 6),
    (100, 150, 50, 10),
])
def test_dsa_depth_calibration(easy, medium, hard, expected):
    assert dsa_depth(_snap(easy, medium, hard)) == expected


def test_dsa_depth_never_below_one_for_a_single_solve():
    assert dsa_depth(_snap(easy=1)) == 1


# ---- weak_topics ----

def _all_core(count):
    return {t: count for t in CORE_TOPICS}


def test_weak_topics_lowest_counts_first():
    topics = _all_core(10)
    topics.update({"Dynamic Programming": 1, "Greedy": 3, "Hash Table": 4})
    assert weak_topics(_snap(topics=topics)) == ["Dynamic Programming", "Greedy", "Hash Table"]


def test_weak_topics_absent_topic_counts_as_zero_and_ties_follow_core_order():
    assert weak_topics(_snap(topics={})) == ["Array", "String", "Hash Table"]


def test_weak_topics_excludes_topics_with_five_or_more_solves():
    topics = _all_core(10)
    topics["Heap"] = 5  # exactly at the threshold -> not weak
    topics["Tree"] = 4
    assert weak_topics(_snap(topics=topics)) == ["Tree"]


def test_weak_topics_empty_when_all_core_topics_practiced():
    assert weak_topics(_snap(topics=_all_core(5))) == []


def test_weak_topics_respects_limit():
    assert weak_topics(_snap(topics={}), limit=5) == CORE_TOPICS[:5]


# ---- summarize / depth_for_skill ----

def test_summarize_builds_display_fields():
    snap = _snap(50, 30, 0, topics=_all_core(10), synced_at="2026-09-27T10:00:00+00:00")
    s = summarize("alice", snap)
    assert s == {
        "username": "alice", "easy": 50, "medium": 30, "hard": 0, "total": 80,
        "dsa_depth": 6, "weak_topics": [], "last_accepted_at": None,
        "synced_at": "2026-09-27T10:00:00+00:00",
    }


def test_depth_for_skill_only_for_dsa_skill():
    snap = _snap(20)
    assert DSA_SKILL_ID == "problem-solving"
    assert depth_for_skill("problem-solving", snap) == 2
    assert depth_for_skill("python", snap) is None
    assert depth_for_skill("problem-solving", None) is None


# ---- fetch_profile (mocked httpx.post) ----

def _response(status_code, body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


REAL_SHAPE = {"data": {
    "matchedUser": {
        "submitStatsGlobal": {"acSubmissionNum": [
            {"difficulty": "All", "count": 80}, {"difficulty": "Easy", "count": 50},
            {"difficulty": "Medium", "count": 30}, {"difficulty": "Hard", "count": 0}]},
        "tagProblemCounts": {
            "advanced": [{"tagName": "Dynamic Programming", "problemsSolved": 2}],
            "intermediate": [{"tagName": "Hash Table", "problemsSolved": 12}],
            "fundamental": [{"tagName": "Array", "problemsSolved": 40}],
        },
    },
    "recentAcSubmissionList": [{"timestamp": "1767225600"}],  # 2026-01-01T00:00:00Z
}}


def test_fetch_profile_parses_real_response_shape():
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, REAL_SHAPE)) as post:
        snap = fetch_profile("alice")
    assert snap == {
        "easy": 50, "medium": 30, "hard": 0,
        "topics": {"Dynamic Programming": 2, "Hash Table": 12, "Array": 40},
        "last_accepted_at": "2026-01-01T00:00:00+00:00",
    }
    assert post.call_args.kwargs["json"]["variables"] == {"u": "alice"}


def test_fetch_profile_no_recent_submissions_gives_none():
    body = {"data": {**REAL_SHAPE["data"], "recentAcSubmissionList": []}}
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        assert fetch_profile("alice")["last_accepted_at"] is None


def test_fetch_profile_missing_user_raises_not_found():
    body = {"errors": [{"message": "That user does not exist."}],
            "data": {"matchedUser": None, "recentAcSubmissionList": []}}
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        with pytest.raises(LeetcodeUserNotFound):
            fetch_profile("nobody")


def test_fetch_profile_non_200_raises_unavailable():
    with patch("app.providers.leetcode.httpx.post", return_value=_response(503, {})):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


def test_fetch_profile_network_error_raises_unavailable():
    with patch("app.providers.leetcode.httpx.post", side_effect=httpx.ConnectError("boom")):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


@pytest.mark.parametrize("body", [
    {"data": None},
    {"unexpected": True},
    {"data": {"matchedUser": {"submitStatsGlobal": None}}},
])
def test_fetch_profile_malformed_body_raises_unavailable(body):
    with patch("app.providers.leetcode.httpx.post", return_value=_response(200, body)):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")


def test_fetch_profile_invalid_json_raises_unavailable():
    resp = _response(200, None)
    resp.json.side_effect = ValueError("not json")
    with patch("app.providers.leetcode.httpx.post", return_value=resp):
        with pytest.raises(LeetcodeUnavailable):
            fetch_profile("alice")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_leetcode_provider.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'app.providers.leetcode'`

- [ ] **Step 3: Write the implementation**

`backend/app/providers/leetcode.py`:

```python
"""LeetCode public-profile stats — unauthenticated, undocumented GraphQL.

No login: the student types their LeetCode username, we read what their
public profile page already shows. The endpoint is the one leetcode.com's own
profile page calls; it's undocumented and may change, so every failure other
than "no such user" is reported as LeetcodeUnavailable and never breaks any
other feature.

Only the raw snapshot is stored; dsa_depth/weak_topics are always recomputed
from it, so every number shown to a learner is reproducible from stored data.
"""
import math
from datetime import datetime, timezone

import httpx

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

# The taxonomy's single DSA node — LeetCode evidence applies to this skill only.
DSA_SKILL_ID = "problem-solving"

# Core interview topics, using LeetCode's exact tag names (verified live).
# Order is the tie-break for weak_topics.
CORE_TOPICS = [
    "Array", "String", "Hash Table", "Two Pointers", "Sliding Window",
    "Binary Search", "Stack", "Linked List", "Tree", "Graph Theory", "Heap",
    "Dynamic Programming", "Greedy", "Backtracking",
]
WEAK_TOPIC_THRESHOLD = 5

_QUERY = """query($u: String!) {
  matchedUser(username: $u) {
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    tagProblemCounts {
      advanced { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      fundamental { tagName problemsSolved }
    }
  }
  recentAcSubmissionList(username: $u, limit: 1) { timestamp }
}"""


class LeetcodeUserNotFound(RuntimeError):
    pass


class LeetcodeUnavailable(RuntimeError):
    pass


def fetch_profile(username: str) -> dict:
    try:
        resp = httpx.post(LEETCODE_GRAPHQL,
                          json={"query": _QUERY, "variables": {"u": username}},
                          headers={"Referer": "https://leetcode.com"}, timeout=10)
    except httpx.HTTPError as e:
        raise LeetcodeUnavailable(f"network error: {e}") from e
    if resp.status_code != 200:
        raise LeetcodeUnavailable(f"HTTP {resp.status_code}")

    try:
        data = resp.json()["data"]
        user = data["matchedUser"]
    except (ValueError, KeyError, TypeError) as e:
        raise LeetcodeUnavailable("unexpected response shape") from e
    if user is None:
        raise LeetcodeUserNotFound(username)

    try:
        counts = {row["difficulty"]: row["count"]
                  for row in user["submitStatsGlobal"]["acSubmissionNum"]}
        topics: dict[str, int] = {}
        for tier in ("advanced", "intermediate", "fundamental"):
            for row in user["tagProblemCounts"][tier] or []:
                topics[row["tagName"]] = row["problemsSolved"]
        recent = data.get("recentAcSubmissionList") or []
        last_accepted_at = (
            datetime.fromtimestamp(int(recent[0]["timestamp"]), tz=timezone.utc).isoformat()
            if recent else None)
    except (KeyError, TypeError, ValueError) as e:
        raise LeetcodeUnavailable("unexpected response shape") from e

    return {"easy": counts.get("Easy", 0), "medium": counts.get("Medium", 0),
            "hard": counts.get("Hard", 0), "topics": topics,
            "last_accepted_at": last_accepted_at}


def dsa_depth(snapshot: dict) -> int | None:
    """Log-scaled so each extra solve matters less; medium/hard weighted 2x/3x.
    Zero solves is absence of evidence, not depth 1 — returns None."""
    easy, medium, hard = snapshot["easy"], snapshot["medium"], snapshot["hard"]
    if easy + medium + hard == 0:
        return None
    weighted = easy + 2 * medium + 3 * hard
    return max(1, min(10, round(2 * math.log2(1 + weighted / 15))))


def weak_topics(snapshot: dict, limit: int = 3) -> list[str]:
    topics = snapshot.get("topics", {})
    weak = [t for t in CORE_TOPICS if topics.get(t, 0) < WEAK_TOPIC_THRESHOLD]
    # sorted() is stable, so equal counts keep CORE_TOPICS order.
    weak.sort(key=lambda t: topics.get(t, 0))
    return weak[:limit]


def summarize(username: str, snapshot: dict) -> dict:
    return {
        "username": username,
        "easy": snapshot["easy"], "medium": snapshot["medium"], "hard": snapshot["hard"],
        "total": snapshot["easy"] + snapshot["medium"] + snapshot["hard"],
        "dsa_depth": dsa_depth(snapshot),
        "weak_topics": weak_topics(snapshot),
        "last_accepted_at": snapshot.get("last_accepted_at"),
        "synced_at": snapshot.get("synced_at"),
    }


def depth_for_skill(skill_id: str, snapshot: dict | None) -> int | None:
    if snapshot is None or skill_id != DSA_SKILL_ID:
        return None
    return dsa_depth(snapshot)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_leetcode_provider.py -v`
Expected: all 22 tests PASS (including parametrized cases)

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/leetcode.py backend/tests/test_leetcode_provider.py
git commit -m "feat(backend): add LeetCode public-profile provider with deterministic DSA depth

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Storage — user snapshot columns and history column

**Files:**
- Modify: `backend/app/db/models.py` (`User`, `CompetencyHistory`)
- Modify: `backend/app/db/database.py` (`run_migrations` statement list)
- Modify: `backend/app/db/crud.py` (imports; new `save_leetcode_snapshot`, `get_leetcode_snapshot`)
- Test: `backend/tests/test_migrations.py`, `backend/tests/test_progress.py`

**Interfaces:**
- Produces:
  - `models.User.leetcode_username: str | None`, `models.User.leetcode_stats_json: str | None`
  - `models.CompetencyHistory.leetcode_depth: int | None` (so `create_competency_history_batch` rows may include `"leetcode_depth"`)
  - `crud.save_leetcode_snapshot(db: Session, user: models.User, username: str, snapshot: dict) -> None`
  - `crud.get_leetcode_snapshot(user: models.User) -> dict | None`

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_migrations.py`, extend the existing test's assertions — after the line `assert "github_username" in user_cols` add:

```python
    assert {"leetcode_username", "leetcode_stats_json"} <= user_cols
    history_cols = {c["name"] for c in inspector.get_columns("competency_history")}
    assert "leetcode_depth" in history_cols
```

Append to `backend/tests/test_progress.py`:

```python
def test_leetcode_snapshot_round_trips():
    db = _db()
    user = _make_user(db, email="lc@example.com")
    assert crud.get_leetcode_snapshot(user) is None

    snapshot = {"easy": 5, "medium": 1, "hard": 0, "topics": {"Array": 3},
                "last_accepted_at": None, "synced_at": "2026-09-27T10:00:00+00:00"}
    crud.save_leetcode_snapshot(db, user, "alice", snapshot)

    db.refresh(user)
    assert user.leetcode_username == "alice"
    assert crud.get_leetcode_snapshot(user) == snapshot


def test_leetcode_snapshot_corrupt_json_reads_as_none():
    db = _db()
    user = _make_user(db, email="lc2@example.com")
    user.leetcode_stats_json = "{not json"
    db.commit()
    assert crud.get_leetcode_snapshot(user) is None


def test_competency_history_batch_accepts_leetcode_depth():
    db = _db()
    user = _make_user(db, email="lc3@example.com")
    crud.create_competency_history_batch(db, [
        {"user_id": user.id, "skill_id": "problem-solving", "depth_score": 6,
         "quiz_score": None, "confidence_rating": None, "has_github_evidence": False,
         "leetcode_depth": 6, "rationale": "r"},
    ])
    row = crud.get_latest_competency(db, user.id, "problem-solving")
    assert row.leetcode_depth == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_migrations.py tests/test_progress.py -v`
Expected: FAIL — `AssertionError` on the migration test; `AttributeError: module 'app.db.crud' has no attribute 'get_leetcode_snapshot'`; `TypeError: 'leetcode_depth' is an invalid keyword argument for CompetencyHistory`

- [ ] **Step 3: Implement**

`backend/app/db/models.py` — in `class User`, after `github_username = Column(String, nullable=True)`:

```python
    leetcode_username = Column(String, nullable=True)
    leetcode_stats_json = Column(Text, nullable=True)
```

In `class CompetencyHistory`, after `has_github_evidence = Column(Boolean, default=False)`:

```python
    leetcode_depth = Column(Integer, nullable=True)
```

`backend/app/db/database.py` — append to the `statements` list in `run_migrations`, after `"ALTER TABLE journeys ADD COLUMN hours_per_week INTEGER DEFAULT 10",`:

```python
        "ALTER TABLE users ADD COLUMN leetcode_username VARCHAR",
        "ALTER TABLE users ADD COLUMN leetcode_stats_json TEXT",
        "ALTER TABLE competency_history ADD COLUMN leetcode_depth INTEGER",
```

`backend/app/db/crud.py` — change the top imports to:

```python
import datetime
import json

from sqlalchemy.orm import Session
from . import models, auth
```

and add, after `get_github_evidence_by_skill`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_migrations.py tests/test_progress.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/app/db/database.py backend/app/db/crud.py backend/tests/test_migrations.py backend/tests/test_progress.py
git commit -m "feat(backend): store LeetCode snapshot per user and leetcode_depth per competency row

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Competency — LeetCode component

**Files:**
- Modify: `backend/app/agents/competency_agent.py` (whole file shown below)
- Test: `backend/tests/test_competency_agent.py`

**Interfaces:**
- Produces: `assess_competency(skill_name: str, resume_depth: int, quiz_score: int | None, confidence_rating: int | None, github_evidence: bool, leetcode_depth: int | None = None) -> tuple[int, str]`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_competency_agent.py`:

```python
def _no_llm():
    return patch("app.agents.competency_agent.get_llm", side_effect=RuntimeError("no llm"))


def test_leetcode_only_signal_blends_instead_of_returning_resume_depth():
    # (4*0.30 + 8*0.35) / 0.65 = 6.15 -> 6
    with _no_llm():
        score, rationale = assess_competency("Problem Solving & DSA", 4, None, None, False,
                                             leetcode_depth=8)
    assert score == 6
    assert "leetcode: 8/10" in rationale


def test_leetcode_can_lower_an_overstated_resume_depth():
    # (8*0.30 + 2*0.35) / 0.65 = 4.77 -> 5
    with _no_llm():
        score, _ = assess_competency("Problem Solving & DSA", 8, None, None, False,
                                     leetcode_depth=2)
    assert score == 5


def test_leetcode_blends_with_quiz_and_confidence():
    base = (4 * 0.30 + 9.0 * 0.40 + 8 * 0.15 + 10 * 0.35) / 1.20
    with _no_llm():
        score, _ = assess_competency("Problem Solving & DSA", 4, 90, 4, False, leetcode_depth=10)
    assert score == round(base) == 8


def test_no_leetcode_leaves_fallback_rationale_unchanged():
    with _no_llm():
        _, rationale = assess_competency("Python", 4, 90, None, False)
    assert rationale == "Depth assessed at 7/10 (resume: 4, quiz: 90%, conf: None, github: No)."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_competency_agent.py -v`
Expected: the three LeetCode tests FAIL with `TypeError: assess_competency() got an unexpected keyword argument 'leetcode_depth'`; `test_no_leetcode_leaves_fallback_rationale_unchanged` PASSES already (it pins current behavior).

- [ ] **Step 3: Implement**

Replace the contents of `backend/app/agents/competency_agent.py` with:

```python
import logging
from ..config import get_settings
from ..core.llm import get_llm, invoke_llm

log = logging.getLogger(__name__)

RATIONALE_PROMPT = """You are a Competency Assessor. You just evaluated a student's skill level in "{skill_name}".
The new depth score is {depth_score} out of 10.
The inputs used were:
- Resume prior depth: {resume_depth}/10
- Quiz score: {quiz_str}
- Confidence rating: {conf_str}
- GitHub evidence (recent repo): {github_str}{leetcode_line}

Write exactly ONE short sentence explaining this score change or current state.
Focus on the most impactful signals. Do not explain the math.
Example: "Depth raised to 7/10 due to a strong quiz score (85%) and recent GitHub practice."
"""

# Accepted LeetCode solutions are judged against real test cases, so they rank
# just below a quiz (0.40) as direct evidence, above the resume prior (0.30).
LEETCODE_WEIGHT = 0.35


def assess_competency(skill_name: str, resume_depth: int, quiz_score: int | None,
                      confidence_rating: int | None, github_evidence: bool,
                      leetcode_depth: int | None = None) -> tuple[int, str]:
    if (quiz_score is None and confidence_rating is None and not github_evidence
            and leetcode_depth is None):
        return resume_depth, "Initial assessment based on resume."

    components = [(resume_depth, 0.30)]
    if quiz_score is not None:
        components.append((quiz_score / 10.0, 0.40))
    if confidence_rating is not None:
        components.append((confidence_rating * 2.0, 0.15))
    if leetcode_depth is not None:
        components.append((leetcode_depth, LEETCODE_WEIGHT))

    total_weight = sum(w for _, w in components)
    base = sum(val * w for val, w in components) / total_weight

    if github_evidence:
        base = min(10.0, base + 1.5)

    depth_score = int(round(max(1.0, min(10.0, base))))

    quiz_str = f"{quiz_score}%" if quiz_score is not None else "None"
    conf_str = f"{confidence_rating}/5" if confidence_rating is not None else "None"
    github_str = "Yes" if github_evidence else "No"
    # Only mentioned when present, so rationales for every non-DSA skill are
    # unchanged from before LeetCode evidence existed.
    leetcode_suffix = f", leetcode: {leetcode_depth}/10" if leetcode_depth is not None else ""
    leetcode_line = (f"\n- LeetCode DSA depth: {leetcode_depth}/10"
                     if leetcode_depth is not None else "")

    fallback_rationale = (f"Depth assessed at {depth_score}/10 (resume: {resume_depth}, "
                          f"quiz: {quiz_str}, conf: {conf_str}, github: {github_str}{leetcode_suffix}).")

    try:
        llm = get_llm(get_settings().planner_model)
        prompt = RATIONALE_PROMPT.format(
            skill_name=skill_name, depth_score=depth_score, resume_depth=resume_depth,
            quiz_str=quiz_str, conf_str=conf_str, github_str=github_str,
            leetcode_line=leetcode_line,
        )
        response = invoke_llm(llm, prompt)
        rationale = response.content.strip().replace('"', '')
        if not rationale:
            rationale = fallback_rationale
    except Exception as e:
        log.warning("competency assessor LLM failed: %s", e)
        rationale = fallback_rationale

    return depth_score, rationale
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_competency_agent.py -v`
Expected: all PASS (existing 8 + new 4)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/competency_agent.py backend/tests/test_competency_agent.py
git commit -m "feat(backend): add LeetCode DSA depth as a 0.35-weight competency component

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: API — sync/read endpoints, interview tips, competency wiring

**Files:**
- Modify: `backend/app/schemas.py` (new `LeetcodeSummary`)
- Modify: `backend/app/main.py` (imports; `advise`; new `_interview_focus_topics`; `get_interview_tips`; new `sync_leetcode`, `get_leetcode`; `recalculate_journey`)
- Test: `backend/tests/test_leetcode_api.py`

**Interfaces:**
- Consumes: Task 1 `leetcode.fetch_profile`, `summarize`, `weak_topics`, `depth_for_skill`, exceptions; Task 2 `crud.save_leetcode_snapshot`, `crud.get_leetcode_snapshot`; Task 3 `assess_competency(..., leetcode_depth=)`.
- Produces:
  - `POST /api/leetcode/sync` body `{"username": str}` → `LeetcodeSummary`
  - `GET /api/leetcode` → `LeetcodeSummary | null`
  - `LeetcodeSummary` JSON: `{username: str, easy: int, medium: int, hard: int, total: int, dsa_depth: int | null, weak_topics: str[], last_accepted_at: str | null, synced_at: str | null}`
  - `main._interview_focus_topics(gap_report_json: str | None, snapshot: dict | None) -> list[str]`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_leetcode_api.py`:

```python
"""LeetCode endpoints + interview focus topics. Endpoint functions are called
directly with an in-memory DB and user (same pattern as test_progress.py);
the provider's network call is patched."""
import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.db import database, models
from app.main import LeetcodeSyncRequest, _interview_focus_topics, get_leetcode, sync_leetcode
from app.providers.leetcode import LeetcodeUnavailable, LeetcodeUserNotFound

SNAPSHOT = {"easy": 50, "medium": 30, "hard": 0,
            "topics": {"Array": 40, "Hash Table": 12, "Dynamic Programming": 2},
            "last_accepted_at": "2026-09-01T00:00:00+00:00"}


def _db_and_user():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    db = database.sessionmaker(bind=engine)()
    user = models.User(email="lcapi@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_sync_rejects_invalid_username_without_calling_leetcode():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile") as fetch:
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="bad name!"), db, user)
    assert exc.value.status_code == 400
    fetch.assert_not_called()


def test_sync_unknown_user_is_404():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", side_effect=LeetcodeUserNotFound("ghost")):
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="ghost"), db, user)
    assert exc.value.status_code == 404
    assert "ghost" in exc.value.detail


def test_sync_leetcode_down_is_502_and_stores_nothing():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", side_effect=LeetcodeUnavailable("HTTP 503")):
        with pytest.raises(HTTPException) as exc:
            sync_leetcode(LeetcodeSyncRequest(username="alice"), db, user)
    assert exc.value.status_code == 502
    assert user.leetcode_stats_json is None


def test_sync_success_persists_and_get_returns_same_summary():
    db, user = _db_and_user()
    with patch("app.providers.leetcode.fetch_profile", return_value=dict(SNAPSHOT)):
        synced = sync_leetcode(LeetcodeSyncRequest(username="alice"), db, user)

    assert synced["username"] == "alice"
    assert synced["total"] == 80
    assert synced["dsa_depth"] == 6
    assert synced["synced_at"] is not None
    assert json.loads(user.leetcode_stats_json)["easy"] == 50

    assert get_leetcode(user) == synced


def test_get_leetcode_never_synced_is_none():
    _db, user = _db_and_user()
    assert get_leetcode(user) is None


def test_interview_focus_topics_appends_weak_topics_after_gaps_without_duplicates():
    gap_json = json.dumps({"gaps": [{"name": "Docker"}, {"name": "Array"}]})
    snapshot = {"easy": 1, "medium": 0, "hard": 0, "topics": {}, "last_accepted_at": None}
    # weak topics for an empty topic map are Array, String, Hash Table
    assert _interview_focus_topics(gap_json, snapshot) == ["Docker", "Array", "String", "Hash Table"]


def test_interview_focus_topics_without_leetcode_is_gap_names_only():
    gap_json = json.dumps({"gaps": [{"name": f"S{i}"} for i in range(7)]})
    assert _interview_focus_topics(gap_json, None) == ["S0", "S1", "S2", "S3", "S4"]


def test_interview_focus_topics_tolerates_bad_gap_json():
    assert _interview_focus_topics("{not json", None) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_leetcode_api.py -v`
Expected: collection error — `ImportError: cannot import name 'LeetcodeSyncRequest' from 'app.main'`

- [ ] **Step 3: Implement**

`backend/app/schemas.py` — append after `class InterviewTips`:

```python
class LeetcodeSummary(BaseModel):
    username: str
    easy: int
    medium: int
    hard: int
    total: int
    dsa_depth: Optional[int] = None
    weak_topics: list[str] = []
    last_accepted_at: Optional[str] = None
    synced_at: Optional[str] = None
```

`backend/app/main.py`:

(a) Imports — change

```python
from .providers import get_job_provider, github
```
to
```python
from .providers import get_job_provider, github, leetcode
```
and change the schemas import line to end with `..., JobRecommendation, InterviewTips, LeetcodeSummary`.

(b) In `advise`, replace the competency-row loop

```python
            from .agents.competency_agent import assess_competency
            rows = []
            for skill in result.profile.skills:
                depth_score, rationale = assess_competency(
                    skill.name, skill.depth_score, None, None, False)
                rows.append({
                    "user_id": user.id, "skill_id": skill.skill_id,
                    "depth_score": depth_score, "quiz_score": None,
                    "confidence_rating": None, "has_github_evidence": False,
                    "rationale": rationale,
                })
```
with
```python
            from .agents.competency_agent import assess_competency
            leetcode_snapshot = crud.get_leetcode_snapshot(user)
            rows = []
            for skill in result.profile.skills:
                lc_depth = leetcode.depth_for_skill(skill.skill_id, leetcode_snapshot)
                depth_score, rationale = assess_competency(
                    skill.name, skill.depth_score, None, None, False, leetcode_depth=lc_depth)
                rows.append({
                    "user_id": user.id, "skill_id": skill.skill_id,
                    "depth_score": depth_score, "quiz_score": None,
                    "confidence_rating": None, "has_github_evidence": False,
                    "leetcode_depth": lc_depth, "rationale": rationale,
                })
```

(c) Replace the whole `get_interview_tips` endpoint with a helper plus the endpoint:

```python
def _interview_focus_topics(gap_report_json: str | None, snapshot: dict | None) -> list[str]:
    """Top-5 gap skills, then LeetCode weak topics (if synced), de-duplicated."""
    topics: list[str] = []
    if gap_report_json:
        try:
            gaps = json.loads(gap_report_json).get("gaps", [])
            topics = [g["name"] for g in gaps[:5]]
        except (ValueError, KeyError, AttributeError):
            pass
    if snapshot:
        topics += [t for t in leetcode.weak_topics(snapshot) if t not in topics]
    return topics


@app.get("/api/interview-tips", response_model=InterviewTips)
def get_interview_tips(db: Session = Depends(get_db),
                       current_user: models.User = Depends(get_current_user)):
    from .agents.interview_agent import generate_interview_tips
    journey = crud.get_most_recent_journey(db, current_user.id)
    if not journey:
        raise HTTPException(404, "Generate a learning path first to get interview tips.")
    focus_topics = _interview_focus_topics(journey.gap_report_json,
                                           crud.get_leetcode_snapshot(current_user))
    tips, _notes = generate_interview_tips(journey.target_role, focus_topics)
    return tips
```

(d) After the `sync_github` endpoint, add:

```python
_LEETCODE_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")


class LeetcodeSyncRequest(BaseModel):
    username: str


@app.post("/api/leetcode/sync", response_model=LeetcodeSummary)
def sync_leetcode(req: LeetcodeSyncRequest, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    username = req.username.strip()
    if not _LEETCODE_USERNAME_RE.match(username):
        raise HTTPException(400, "Invalid LeetCode username")
    try:
        snapshot = leetcode.fetch_profile(username)
    except leetcode.LeetcodeUserNotFound as e:
        raise HTTPException(404, f"LeetCode user '{username}' not found") from e
    except leetcode.LeetcodeUnavailable as e:
        log.warning("LeetCode sync failed for %s: %s", username, e)
        raise HTTPException(502, "LeetCode is unavailable right now — try again later") from e

    snapshot["synced_at"] = datetime.now(timezone.utc).isoformat()
    crud.save_leetcode_snapshot(db, current_user, username, snapshot)
    return leetcode.summarize(username, snapshot)


@app.get("/api/leetcode", response_model=LeetcodeSummary | None)
def get_leetcode(current_user: models.User = Depends(get_current_user)):
    snapshot = crud.get_leetcode_snapshot(current_user)
    if snapshot is None:
        return None
    return leetcode.summarize(current_user.leetcode_username, snapshot)
```

(e) In `recalculate_journey`, directly after `github_evidence = crud.get_github_evidence_by_skill(db, current_user.id)` add:

```python
    leetcode_snapshot = crud.get_leetcode_snapshot(current_user)
```

and inside the per-skill loop replace

```python
                new_depth, rationale = assess_competency(
                    s.name, resume_prior, step.quiz_score, step.confidence_rating, has_github
                )
                s.depth_score = new_depth
                pending_history.append({
                    "user_id": current_user.id, "skill_id": s.skill_id,
                    "depth_score": new_depth, "quiz_score": step.quiz_score,
                    "confidence_rating": step.confidence_rating,
                    "has_github_evidence": has_github, "rationale": rationale,
                })
```
with
```python
                lc_depth = leetcode.depth_for_skill(s.skill_id, leetcode_snapshot)
                new_depth, rationale = assess_competency(
                    s.name, resume_prior, step.quiz_score, step.confidence_rating, has_github,
                    leetcode_depth=lc_depth,
                )
                s.depth_score = new_depth
                pending_history.append({
                    "user_id": current_user.id, "skill_id": s.skill_id,
                    "depth_score": new_depth, "quiz_score": step.quiz_score,
                    "confidence_rating": step.confidence_rating,
                    "has_github_evidence": has_github, "leetcode_depth": lc_depth,
                    "rationale": rationale,
                })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_leetcode_api.py -v`
Expected: all 8 PASS

Then the full backend suite (the `advise`/`recalculate_journey` wiring is exercised live in Task 6):
Run: `cd backend && .venv/Scripts/python -m pytest -q`
Expected: all tests pass, 0 failures

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/main.py backend/tests/test_leetcode_api.py
git commit -m "feat(backend): add LeetCode sync/read endpoints; feed weak topics into interview tips and DSA depth into competency scoring

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Frontend — LeetcodeConnect panel

**Files:**
- Modify: `frontend/src/api/types.ts` (append `LeetcodeSummary`)
- Create: `frontend/src/api/leetcode.ts`
- Create: `frontend/src/components/LeetcodeConnect.tsx`
- Modify: `frontend/src/routes/TrackerPage.tsx`
- Test: `frontend/src/components/LeetcodeConnect.test.tsx`

**Interfaces:**
- Consumes: Task 4 `GET /api/leetcode`, `POST /api/leetcode/sync`, `LeetcodeSummary` JSON.
- Produces: `useLeetcodeSummary()`, `useSyncLeetcode()`, default-export `LeetcodeConnect` component.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/LeetcodeConnect.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LeetcodeConnect from './LeetcodeConnect'
import type { LeetcodeSummary } from '../api/types'

const SUMMARY: LeetcodeSummary = {
  username: 'alice', easy: 50, medium: 30, hard: 0, total: 80,
  dsa_depth: 6, weak_topics: ['Dynamic Programming', 'Greedy'],
  last_accepted_at: '2026-09-01T00:00:00+00:00', synced_at: '2026-09-27T10:00:00+00:00',
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response
}

function fail(status: number, detail: string) {
  return { ok: false, status, statusText: 'Error', json: async () => ({ detail }) } as Response
}

function mockApi({ current, sync }: { current: LeetcodeSummary | null; sync?: Response }) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/leetcode/sync') return sync ?? ok(SUMMARY)
    return ok(current)
  }))
}

function renderConnect() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LeetcodeConnect />
    </QueryClientProvider>
  )
}

describe('LeetcodeConnect', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows only the connect form when never synced', async () => {
    mockApi({ current: null })
    renderConnect()
    expect(await screen.findByPlaceholderText('LeetCode username')).toBeInTheDocument()
    expect(screen.queryByText(/DSA depth/)).not.toBeInTheDocument()
  })

  it('shows counts, depth and weak topics after a successful sync', async () => {
    mockApi({ current: null })
    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('LeetCode username'), { target: { value: 'alice' } })
    fireEvent.click(screen.getByText('Sync'))

    await waitFor(() => expect(screen.getByText('DSA depth 6/10')).toBeInTheDocument())
    expect(screen.getByText('Easy 50 · Medium 30 · Hard 0')).toBeInTheDocument()
    expect(screen.getByText('Dynamic Programming')).toBeInTheDocument()
    expect(screen.getByText('Greedy')).toBeInTheDocument()
  })

  it('shows an existing synced profile on load', async () => {
    mockApi({ current: { ...SUMMARY, dsa_depth: null, weak_topics: [] } })
    renderConnect()
    expect(await screen.findByText('No solved problems yet')).toBeInTheDocument()
  })

  it('shows the API error message when sync fails', async () => {
    mockApi({ current: null, sync: fail(404, "LeetCode user 'ghost' not found") })
    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('LeetCode username'), { target: { value: 'ghost' } })
    fireEvent.click(screen.getByText('Sync'))

    expect(await screen.findByText("LeetCode user 'ghost' not found")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/LeetcodeConnect.test.tsx --pool=threads`
Expected: FAIL — `Failed to resolve import "./LeetcodeConnect"`

- [ ] **Step 3: Implement**

Append to `frontend/src/api/types.ts`:

```ts

export interface LeetcodeSummary {
  username: string
  easy: number
  medium: number
  hard: number
  total: number
  dsa_depth: number | null
  weak_topics: string[]
  last_accepted_at: string | null
  synced_at: string | null
}
```

`frontend/src/api/leetcode.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { LeetcodeSummary } from './types'

export function useLeetcodeSummary() {
  return useQuery({
    queryKey: ['leetcode'],
    queryFn: () => apiRequest<LeetcodeSummary | null>('/api/leetcode'),
  })
}

export function useSyncLeetcode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiRequest<LeetcodeSummary>('/api/leetcode/sync', {
        method: 'POST', body: JSON.stringify({ username }),
      }),
    onSuccess: (summary) => {
      queryClient.setQueryData(['leetcode'], summary)
      // Weak topics feed interview prep focus areas.
      queryClient.invalidateQueries({ queryKey: ['interview-tips'] })
    },
  })
}
```

`frontend/src/components/LeetcodeConnect.tsx`:

```tsx
import { useState } from 'react'
import { useLeetcodeSummary, useSyncLeetcode } from '../api/leetcode'

export default function LeetcodeConnect() {
  const [username, setUsername] = useState('')
  const { data: summary } = useLeetcodeSummary()
  const syncLeetcode = useSyncLeetcode()

  const sync = () => {
    if (!username.trim()) return
    syncLeetcode.mutate(username.trim())
  }

  return (
    <div className="panel" style={{ marginBottom: '1.5rem' }}>
      <h2>Connect LeetCode</h2>
      <p className="hint">We read your public LeetCode stats as evidence of problem-solving skill. No login required.</p>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input className="input-field" placeholder="LeetCode username" value={username}
               onChange={(e) => setUsername(e.target.value)} style={{ maxWidth: 300 }} />
        <button className="primary-button" onClick={sync} disabled={syncLeetcode.isPending}>
          {syncLeetcode.isPending ? 'Syncing...' : 'Sync'}
        </button>
      </div>
      {syncLeetcode.error && <p className="hint">{syncLeetcode.error.message}</p>}
      {summary && (
        <div style={{ marginTop: '1rem' }}>
          <p style={{ margin: '0 0 0.3rem' }}><strong>{summary.username}</strong></p>
          <p style={{ margin: '0 0 0.3rem' }}>{`Easy ${summary.easy} · Medium ${summary.medium} · Hard ${summary.hard}`}</p>
          <p style={{ margin: '0 0 0.5rem', fontWeight: 600 }}>
            {summary.dsa_depth !== null ? `DSA depth ${summary.dsa_depth}/10` : 'No solved problems yet'}
          </p>
          {summary.weak_topics.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
              <span className="hint" style={{ margin: 0 }}>Practice next:</span>
              {summary.weak_topics.map((t) => <span key={t} className="tag">{t}</span>)}
            </div>
          )}
          {summary.synced_at && (
            <p className="hint">Last synced {new Date(summary.synced_at).toLocaleString()}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

`frontend/src/routes/TrackerPage.tsx` — add the import after `import GithubConnect from '../components/GithubConnect'`:

```tsx
import LeetcodeConnect from '../components/LeetcodeConnect'
```

and render it directly below `<GithubConnect />`:

```tsx
      <GithubConnect />
      <LeetcodeConnect />
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/LeetcodeConnect.test.tsx --pool=threads`
Expected: 4 PASS

Then the full frontend suite and type check:
Run: `cd frontend && npx vitest run --pool=threads`
Expected: all pass, 0 failures (TrackerPage tests, if any, must still pass — they now also render `LeetcodeConnect`; if one fails because its fetch stub doesn't answer `/api/leetcode`, make that stub return `null` for `/api/leetcode`)
Run: `cd frontend && npx tsc -b`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/leetcode.ts frontend/src/components/LeetcodeConnect.tsx frontend/src/components/LeetcodeConnect.test.tsx frontend/src/routes/TrackerPage.tsx
git commit -m "feat(frontend): add LeetCode connect panel to the Tracker page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Live verification

No new committed code — this proves the feature against the real endpoint and real app.

- [ ] **Step 1: Live smoke test of the provider** (throwaway, not committed)

Run from `backend/`:
```bash
.venv/Scripts/python -c "from app.providers import leetcode as l; s=l.fetch_profile('lee215'); print(l.summarize('lee215', s))"
```
Expected: a dict with `easy`/`medium`/`hard` matching the public profile (e.g. 126/410/148 at time of writing), `dsa_depth` 10, `weak_topics` a list (may be empty for a very strong profile), `last_accepted_at` an ISO string.

```bash
.venv/Scripts/python -c "from app.providers import leetcode as l; l.fetch_profile('zz-no-such-user-xq91')"
```
Expected: `LeetcodeUserNotFound` traceback.

- [ ] **Step 2: Full suites**

Run: `cd backend && .venv/Scripts/python -m pytest -q` → all pass.
Run: `cd frontend && npx vitest run --pool=threads` → all pass.

- [ ] **Step 3: Live UI check**

Start the backend (`cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8080`, background) and the `frontend` preview server. Log in with a local test account, open the Tracker page, sync a real public LeetCode username, and confirm the panel shows counts, DSA depth and weak topics; then open the Results page's interview tips and confirm the weak topics appear among the focus topics. Take a screenshot as proof. If the logged-in test user has a journey containing a `problem-solving` step marked struggling, run Recalculate and confirm the new `competency_history` row has `leetcode_depth` set.

- [ ] **Step 4: Update the roadmap memory**

Mark sub-project A as shipped in the `skillmeet-parity-roadmap` memory file.
