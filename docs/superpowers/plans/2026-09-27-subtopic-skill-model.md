# Sub-topic Skill Model (Roadmap R1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn each learning-path step from "one skill, one generic objective" into an ordered, level-appropriate list of curated sub-topics, backed by an expanded, evidence-based skill taxonomy.

**Architecture:** A new committed data file `skill_subtopics.json` holds 4–8 ordered, levelled sub-topics (plus a roadmap.sh link) per taxonomy skill; `core/taxonomy.py` loads it and selects the sub-topics between a learner's current and required level. The planner attaches those to each step and builds its prompt from them; the verifier rejects any sub-topic not in the curated file. A committed research script adds missing skills from ESCO + live job postings. Steps persist the sub-topics, and the UI lists them.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/SQLite (additive ALTER migrations), httpx, pytest; React 19 + TypeScript, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-27-subtopic-skill-model-design.md`

## Global Constraints

- Sub-topic data licensing: only ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0), Microsoft Learn (topic references only). roadmap.sh is **links only** — never copy roadmap.sh text, topic lists or descriptions. Sub-topic names are generic technical topic labels; no descriptive text is copied from any source.
- Per skill: 4–8 sub-topics; ids kebab-case, globally unique, prefixed `<skill_id>-`; `level` ∈ {beginner, intermediate, advanced}; ordered by learning sequence with non-decreasing level; at least one beginner and at least one intermediate-or-advanced.
- `references` ⊆ {esco, ossu, ciu, mslearn} and lists only sources actually consulted (may be empty). `roadmap_url` is `""` or `https://roadmap.sh/...` and every non-empty URL must have returned HTTP 200 when authored (roadmap.sh returns a real 404 for unknown pages — verified).
- Level ranks: none=0, beginner=1, intermediate=2, advanced=3. Window: `rank(current) < rank(level) ≤ rank(required)`; else `level == required`; else all.
- `WEEKS_PER_SUBTOPIC = 0.75`; fallback weeks = `max(n_subtopics, 1) * 0.75 * (10 / hours_per_week)`, rounded to 1 decimal, clamped 0.5–8. `MAX_PATH_SKILLS` stays 8.
- Verifier: unknown sub-topic id → groundedness capped at 1.0, issue text exactly `Sub-topic '<name>' is not in the curated curriculum for <skill_name>`.
- Taxonomy expansion keep rule: not already matched by the taxonomy (`match_mention` confidence ≥ 0.6) AND whole-word share ≥ 3% of at least one role's live postings. Every newly added skill gets ≥ 1 free catalog course whose URL returned HTTP 200 (preserves the existing invariant that skills have a catalog course).
- Attribution line (exact): `Curriculum data: ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0), Microsoft Learn`
- Backend tests: from `backend/`, `.venv/Scripts/python -m pytest`. Frontend tests: from `frontend/`, `npx vitest run --pool=threads` (default forks pool times out on this machine; retry once on "Timeout waiting for worker"). Type check: `npx tsc -b` (delete the generated `frontend/tsconfig.tsbuildinfo` afterwards — it is not tracked).
- Commit directly on `master` (project practice). Never stage the user's unrelated changes: `frontend/vite.config.ts`, `docs/Research_Paper_Draft.md`, `node_modules/`, `temp_docx_text.txt`, anything under `.superpowers/`. Every commit message ends with exactly one trailer line: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- The suite has pre-existing DeprecationWarnings (datetime.utcnow defaults, PyPDF2); do not add new warning sources.

---

### Task 1: Sub-topic loader and level-window selection

**Files:**
- Modify: `backend/app/schemas.py` (add `Subtopic`)
- Modify: `backend/app/core/taxonomy.py` (add loaders + `select_subtopics`)
- Test: `backend/tests/test_subtopic_selection.py`

**Interfaces:**
- Produces:
  - `schemas.Subtopic(BaseModel)`: `id: str`, `name: str`, `level: Literal["beginner", "intermediate", "advanced"]`
  - `taxonomy.LEVEL_RANK: dict[str, int]`
  - `taxonomy.load_subtopics() -> dict` (cached; reads `DATA_DIR / "skill_subtopics.json"`)
  - `taxonomy.subtopics_for(skill_id: str) -> list[Subtopic]` (`[]` for unknown skill)
  - `taxonomy.roadmap_url_for(skill_id: str) -> str` (`""` for unknown skill)
  - `taxonomy.select_subtopics(skill_id: str, current_level: str, required_level: str) -> list[Subtopic]`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_subtopic_selection.py`:

```python
"""Level-window selection of curated sub-topics. The data file is replaced
by a fixture via patching load_subtopics, so these tests don't depend on the
real curriculum content."""
from unittest.mock import patch

import pytest

from app.core.taxonomy import roadmap_url_for, select_subtopics, subtopics_for

FIXTURE = {
    "skills": {
        "python": {
            "roadmap_url": "https://roadmap.sh/python",
            "references": [],
            "subtopics": [
                {"id": "python-b1", "name": "B1", "level": "beginner"},
                {"id": "python-b2", "name": "B2", "level": "beginner"},
                {"id": "python-i1", "name": "I1", "level": "intermediate"},
                {"id": "python-a1", "name": "A1", "level": "advanced"},
            ],
        },
        "beginner-only": {
            "roadmap_url": "",
            "references": [],
            "subtopics": [
                {"id": "beginner-only-b1", "name": "OB1", "level": "beginner"},
                {"id": "beginner-only-i1", "name": "OI1", "level": "intermediate"},
            ],
        },
    }
}


@pytest.fixture(autouse=True)
def fixture_data():
    with patch("app.core.taxonomy.load_subtopics", return_value=FIXTURE):
        yield


def ids(subs):
    return [s.id for s in subs]


def test_subtopics_for_returns_models_in_file_order():
    subs = subtopics_for("python")
    assert ids(subs) == ["python-b1", "python-b2", "python-i1", "python-a1"]
    assert subs[2].name == "I1" and subs[2].level == "intermediate"


def test_unknown_skill_has_no_subtopics_and_no_url():
    assert subtopics_for("nope") == []
    assert roadmap_url_for("nope") == ""
    assert select_subtopics("nope", "none", "advanced") == []


def test_roadmap_url_for_known_skill():
    assert roadmap_url_for("python") == "https://roadmap.sh/python"


@pytest.mark.parametrize("current,required,expected", [
    ("none", "beginner", ["python-b1", "python-b2"]),
    ("none", "intermediate", ["python-b1", "python-b2", "python-i1"]),
    ("none", "advanced", ["python-b1", "python-b2", "python-i1", "python-a1"]),
    ("beginner", "advanced", ["python-i1", "python-a1"]),
    ("intermediate", "advanced", ["python-a1"]),
])
def test_window_is_strictly_above_current_up_to_required(current, required, expected):
    assert ids(select_subtopics("python", current, required)) == expected


def test_empty_window_falls_back_to_required_level():
    # current == required: window is empty -> sub-topics AT the required level
    assert ids(select_subtopics("python", "intermediate", "intermediate")) == ["python-i1"]


def test_no_subtopic_at_required_level_falls_back_to_all():
    # nothing at "advanced" for this skill and window (intermediate, advanced] is empty
    assert ids(select_subtopics("beginner-only", "intermediate", "advanced")) == [
        "beginner-only-b1", "beginner-only-i1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_subtopic_selection.py -v`
Expected: collection error — `ImportError: cannot import name 'roadmap_url_for' from 'app.core.taxonomy'`

- [ ] **Step 3: Implement**

`backend/app/schemas.py` — add after `class StudentProfile` (the file already imports `Literal` and `BaseModel`):

```python
class Subtopic(BaseModel):
    """One curated, ordered sub-topic of a taxonomy skill (skill_subtopics.json)."""
    id: str
    name: str
    level: Literal["beginner", "intermediate", "advanced"]
```

`backend/app/core/taxonomy.py` — add the import below the existing `from .vectorstore import skills_collection` line:

```python
from ..schemas import Subtopic
```

and append at the end of the file:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_subtopic_selection.py -v`
Expected: 10 PASS

Run the full suite once: `cd backend && .venv/Scripts/python -m pytest -q` → all pass (the real data file does not exist yet; nothing else calls these functions).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/core/taxonomy.py backend/tests/test_subtopic_selection.py
git commit -m "feat(backend): add curated sub-topic loader and level-window selection

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Author the sub-topic curriculum for the existing 78 skills

**Files:**
- Create: `backend/app/data/skill_subtopics.json`
- Test: `backend/tests/test_subtopics_data.py`

**Interfaces:**
- Consumes: taxonomy skill ids from `backend/app/data/skills_taxonomy.json` (via `load_taxonomy()`); Task 1's loader reads this file.
- Produces: the data file every later task reads.

This is a content-authoring task: quality matters (the project team will review it and the paper cites it). Use your own technical knowledge; consult the listed open sources where they apply, and record only sources you actually consulted in `references`:
- Microsoft Learn Catalog API (no key): e.g. `curl -s "https://learn.microsoft.com/api/catalog/?type=modules&subject=<subject>"` or browse module unit titles — useful for cloud/Azure/.NET/data/AI/security skills.
- OSSU CS (`https://github.com/ossu/computer-science`) for CS-fundamentals ordering.
- Coding Interview University (`https://github.com/jwasham/coding-interview-university`) for `problem-solving` (DSA) ordering.
- ESCO skill pages where a matching ESCO skill exists.
Never copy roadmap.sh content (links only).

- [ ] **Step 1: Write the validator test**

`backend/tests/test_subtopics_data.py`:

```python
"""Validator for the curated curriculum file (skill_subtopics.json).
Runs against the real data so a malformed edit fails CI."""
import json
import re

from app.config import DATA_DIR
from app.core.taxonomy import load_taxonomy

DATA = json.loads((DATA_DIR / "skill_subtopics.json").read_text(encoding="utf-8"))
LEVELS = ["beginner", "intermediate", "advanced"]
SOURCE_IDS = {"esco", "ossu", "ciu", "mslearn"}
KEBAB = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def test_header():
    assert DATA["version"] == 1
    assert DATA["provenance"].strip()
    assert {s["id"] for s in DATA["sources"]} == SOURCE_IDS
    for s in DATA["sources"]:
        assert s["name"] and s["license"] and s["attribution"]
        assert s["url"].startswith("https://")


def test_covers_exactly_the_taxonomy():
    assert set(DATA["skills"]) == set(load_taxonomy())


def test_every_skill_entry_is_well_formed():
    seen: set[str] = set()
    for sid, entry in DATA["skills"].items():
        assert set(entry) == {"roadmap_url", "references", "subtopics"}, sid
        subs = entry["subtopics"]
        assert 4 <= len(subs) <= 8, f"{sid}: {len(subs)} sub-topics"
        ranks = [LEVELS.index(t["level"]) for t in subs]
        assert ranks == sorted(ranks), f"{sid}: levels must be non-decreasing"
        assert 0 in ranks, f"{sid}: needs a beginner sub-topic"
        assert any(r >= 1 for r in ranks), f"{sid}: needs an intermediate/advanced sub-topic"
        for t in subs:
            assert set(t) == {"id", "name", "level"}, t
            assert KEBAB.fullmatch(t["id"]), t["id"]
            assert t["id"].startswith(sid + "-"), t["id"]
            assert t["id"] not in seen, f"duplicate id {t['id']}"
            seen.add(t["id"])
            assert t["name"].strip(), t["id"]
        assert set(entry["references"]) <= SOURCE_IDS, sid
        url = entry["roadmap_url"]
        assert url == "" or url.startswith("https://roadmap.sh/"), f"{sid}: {url}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_subtopics_data.py -v`
Expected: collection error — `FileNotFoundError: ... skill_subtopics.json`

- [ ] **Step 3: Author the data file**

Create `backend/app/data/skill_subtopics.json` with this exact header and one entry per skill id in `skills_taxonomy.json` (all 78; list them with `.venv/Scripts/python -c "import json;print([s['id'] for s in json.load(open('app/data/skills_taxonomy.json'))['skills']])"`):

```json
{
  "version": 1,
  "provenance": "Drafted with LLM assistance using the references listed per skill; reviewed by the project team. Sub-topic names are generic technical topic labels; no source text is reproduced.",
  "sources": [
    {"id": "esco", "name": "ESCO", "license": "CC BY 4.0", "url": "https://esco.ec.europa.eu",
     "attribution": "ESCO classification, European Commission, CC BY 4.0"},
    {"id": "ossu", "name": "OSSU Computer Science", "license": "MIT", "url": "https://github.com/ossu/computer-science",
     "attribution": "Open Source Society University, Computer Science curriculum, MIT License"},
    {"id": "ciu", "name": "Coding Interview University", "license": "CC BY-SA 4.0", "url": "https://github.com/jwasham/coding-interview-university",
     "attribution": "John Washam, Coding Interview University, CC BY-SA 4.0"},
    {"id": "mslearn", "name": "Microsoft Learn", "license": "Microsoft Learn Catalog API", "url": "https://learn.microsoft.com/training/",
     "attribution": "Microsoft Learn training catalog (topic references only)"}
  ],
  "skills": {
    "python": {
      "roadmap_url": "https://roadmap.sh/python",
      "references": ["mslearn", "ossu"],
      "subtopics": [
        {"id": "python-syntax-types", "name": "Syntax & core data types", "level": "beginner"},
        {"id": "python-control-functions", "name": "Control flow & functions", "level": "beginner"},
        {"id": "python-collections", "name": "Lists, dicts, sets & comprehensions", "level": "beginner"},
        {"id": "python-oop", "name": "Object-oriented programming", "level": "intermediate"},
        {"id": "python-modules-packaging", "name": "Modules, packaging & virtual environments", "level": "intermediate"},
        {"id": "python-errors-testing", "name": "Error handling & testing with pytest", "level": "intermediate"},
        {"id": "python-async-concurrency", "name": "Async & concurrency", "level": "advanced"}
      ]
    }
  }
}
```

(The `python` entry above is the required style example — keep or improve it.) For every skill:
- 4–8 sub-topics in the order a learner should study them, non-decreasing level, at least one beginner and one intermediate/advanced — per Global Constraints.
- Names short (≤ 60 chars), concrete, and distinct within the skill.
- `roadmap_url`: set only when a roadmap.sh page specifically covers that skill or its direct domain (e.g. `go` → `https://roadmap.sh/golang`, `git` → `https://roadmap.sh/git-github`, `problem-solving` → `https://roadmap.sh/datastructures-and-algorithms`); otherwise `""`. Verify every non-empty URL:
  `curl -s -o /dev/null -w "%{http_code}" <url>` must print `200` (a missing page prints `404`). Record the full list of checked URLs and codes in your report.

- [ ] **Step 4: Run the validator and the full suite**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_subtopics_data.py tests/test_subtopic_selection.py -v`
Expected: all PASS
Run: `cd backend && .venv/Scripts/python -m pytest -q` → all pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/skill_subtopics.json backend/tests/test_subtopics_data.py
git commit -m "feat(data): add curated sub-topic curriculum for all 78 skills

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Evidence-based taxonomy expansion

**Files:**
- Create: `backend/scripts/find_missing_skills.py`
- Create: `docs/research/2026-09-taxonomy-expansion.md` (generated, then annotated)
- Modify: `backend/app/data/skills_taxonomy.json` (append new skills)
- Modify: `backend/app/data/skill_subtopics.json` (entries for new skills)
- Modify: `backend/app/data/courses_sample.json` (≥ 1 course per new skill)
- Test: `backend/tests/test_find_missing_skills.py`, `backend/tests/test_taxonomy_aliases.py`

**Interfaces:**
- Consumes: `app.providers.get_job_provider()` (`fetch(role, limit) -> list[Posting]`, `available_roles() -> list[str]`; `Posting["description"]`), `app.core.taxonomy.match_mention(str) -> (skill_id, confidence) | None`, `app.core.llm.get_llm / invoke_llm / extract_json`, `app.config.get_settings().fast_model`. Task 2's validator enforces the new sub-topic entries.
- Produces: more taxonomy skills (existing schema: `id, name, aliases, category, prerequisites`), each with sub-topics and a catalog course.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_find_missing_skills.py`:

```python
"""Pure helpers of the taxonomy-expansion research script."""
from scripts.find_missing_skills import normalize, share


def test_normalize_strips_esco_parentheticals():
    assert normalize("Python (computer programming)") == "Python"
    assert normalize("  Power BI ") == "Power BI"


def test_share_is_case_insensitive_whole_word():
    docs = ["We use Snowflake daily", "snowflake + dbt", "snowflakes are pretty", "nothing here"]
    assert share("Snowflake", docs) == 0.5


def test_share_handles_symbols_in_terms():
    docs = ["C# and .NET developer", "C developer", "Node.js backend"]
    assert share("C#", docs) == 1 / 3
    assert share("Node.js", docs) == 1 / 3


def test_share_of_no_postings_is_zero():
    assert share("Kafka", []) == 0.0
```

`backend/tests/test_taxonomy_aliases.py`:

```python
"""No two taxonomy skills may claim the same name/id/alias — the alias index
would silently map it to whichever skill loaded last."""
from collections import Counter

from app.core.taxonomy import load_taxonomy


def test_names_ids_and_aliases_are_unique_across_skills():
    owners = Counter()
    for node in load_taxonomy().values():
        keys = {node.id.lower(), node.name.lower(), *(a.lower() for a in node.aliases)}
        owners.update(keys)
    duplicates = sorted(k for k, n in owners.items() if n > 1)
    assert duplicates == []
```

- [ ] **Step 2: Run tests to verify state**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_find_missing_skills.py tests/test_taxonomy_aliases.py -v`
Expected: `test_find_missing_skills.py` errors with `ModuleNotFoundError: No module named 'scripts'`. `test_taxonomy_aliases.py` should PASS on the current taxonomy — if it FAILS, stop and report NEEDS_CONTEXT with the duplicate list (do not edit existing skills).

- [ ] **Step 3: Write the script**

`backend/scripts/find_missing_skills.py`:

```python
"""Taxonomy-expansion research script (one-off; the app never runs it).

Finds skills that live job postings demand but skills_taxonomy.json lacks,
and writes the evidence to docs/research/2026-09-taxonomy-expansion.md.

Candidates come from (a) ESCO essential/optional skills of the closest ESCO
occupation per role and (b) technology terms an LLM extracts from a sample of
postings. A candidate is KEPT when the taxonomy doesn't already match it
(match_mention confidence >= 0.6) and it appears whole-word in >= 3% of at
least one role's postings.

Run from backend/:  .venv/Scripts/python -m scripts.find_missing_skills
"""
import datetime
import re
from pathlib import Path

import httpx

from app.config import get_settings
from app.core.llm import extract_json, get_llm, invoke_llm
from app.core.taxonomy import match_mention
from app.providers import get_job_provider

ESCO_API = "https://ec.europa.eu/esco/api"
POSTINGS_PER_ROLE = 100
LLM_SAMPLE = 30
LLM_BATCH = 10
DESC_CHARS = 1000
KEEP_SHARE = 0.03
MATCH_FLOOR = 0.6
REPORT = Path(__file__).resolve().parents[2] / "docs" / "research" / "2026-09-taxonomy-expansion.md"

EXTRACT_PROMPT = """From the job descriptions below, list every distinct technology, tool, framework, platform, programming language or technical methodology that is named (e.g. "Snowflake", "Power BI", "Jenkins"). Use the name as written. No soft skills, no job titles.

{descriptions}

Return ONLY a JSON array of strings."""


def normalize(term: str) -> str:
    """'Python (computer programming)' -> 'Python'."""
    return re.sub(r"\s*\(.*?\)", "", term).strip()


def share(term: str, descriptions: list[str]) -> float:
    """Fraction of descriptions mentioning term as a whole word (case-insensitive)."""
    if not descriptions:
        return 0.0
    pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
    return sum(1 for d in descriptions if pattern.search(d)) / len(descriptions)


def esco_skills(role: str) -> tuple[str, list[str]]:
    """('<occupation title> <uri>', essential + optional skill titles)."""
    search = httpx.get(f"{ESCO_API}/search", timeout=30, params={
        "text": role, "type": "occupation", "language": "en", "limit": 1}).json()
    results = search.get("_embedded", {}).get("results", [])
    if not results:
        return "(no ESCO match)", []
    occ = results[0]
    detail = httpx.get(f"{ESCO_API}/resource/occupation", timeout=30, params={
        "uri": occ["uri"], "language": "en"}).json()
    links = detail.get("_links", {})
    titles = [s["title"] for key in ("hasEssentialSkill", "hasOptionalSkill")
              for s in links.get(key, [])]
    return f"{occ['title']} <{occ['uri']}>", titles


def llm_terms(descriptions: list[str]) -> list[str]:
    llm = get_llm(get_settings().fast_model)
    terms: list[str] = []
    for i in range(0, len(descriptions), LLM_BATCH):
        batch = "\n---\n".join(d[:DESC_CHARS] for d in descriptions[i:i + LLM_BATCH])
        try:
            data = extract_json(invoke_llm(llm, EXTRACT_PROMPT.format(descriptions=batch)).content)
        except Exception as e:  # research script: log a bad batch and keep going
            print(f"  LLM batch failed: {e}")
            continue
        if isinstance(data, list):
            terms += [t for t in data if isinstance(t, str)]
    return terms


def main() -> None:
    provider = get_job_provider()
    roles = provider.available_roles()
    postings: dict[str, list[str]] = {}
    occupations: dict[str, str] = {}
    candidates: dict[str, dict] = {}  # lowercase name -> {"name", "sources"}

    def add(name: str, source: str) -> None:
        name = normalize(name)
        if len(name) < 2:
            return
        entry = candidates.setdefault(name.lower(), {"name": name, "sources": set()})
        entry["sources"].add(source)

    for role in roles:
        print(f"[{role}] fetching postings...")
        postings[role] = [p["description"] for p in provider.fetch(role, limit=POSTINGS_PER_ROLE)]
        occupations[role], titles = esco_skills(role)
        for t in titles:
            add(t, "esco")
        for t in llm_terms(postings[role][:LLM_SAMPLE]):
            add(t, "llm")

    rows = []
    for c in candidates.values():
        hit = match_mention(c["name"])
        if hit and hit[1] >= MATCH_FLOOR:
            continue  # already covered by the taxonomy
        per_role = {r: share(c["name"], postings[r]) for r in roles}
        best = max(per_role.values()) if per_role else 0.0
        rows.append((c["name"], sorted(c["sources"]), per_role, best, best >= KEEP_SHARE))
    rows.sort(key=lambda r: (-r[3], r[0].lower()))

    lines = [
        "# Taxonomy expansion evidence (2026-09)",
        "",
        f"Generated by `backend/scripts/find_missing_skills.py` on {datetime.date.today()} "
        f"with job provider `{get_settings().job_provider}`.",
        "",
        f"Rule: keep a candidate the taxonomy does not already match (confidence >= {MATCH_FLOOR}) "
        f"that appears whole-word in >= {KEEP_SHARE:.0%} of at least one role's postings.",
        "",
        "## Postings analysed",
        "",
        "| Role | Postings | ESCO occupation used |",
        "|---|---|---|",
        *[f"| {r} | {len(postings[r])} | {occupations[r]} |" for r in roles],
        "",
        "## Candidates (sorted by highest share)",
        "",
        "| Candidate | Source | " + " | ".join(roles) + " | Max | Kept |",
        "|---|---|" + "---|" * len(roles) + "---|---|",
        *[f"| {name} | {', '.join(src)} | " + " | ".join(f"{per[r]:.1%}" for r in roles)
          + f" | {best:.1%} | {'yes' if kept else 'no'} |"
          for name, src, per, best, kept in rows],
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT} ({sum(1 for r in rows if r[4])} kept of {len(rows)} candidates)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the unit tests**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_find_missing_skills.py tests/test_taxonomy_aliases.py -v`
Expected: all PASS

- [ ] **Step 5: Run the script live**

Confirm `backend/.env` has `JOB_PROVIDER=jobspy` (read-only check; do not print API keys). Run from `backend/`:
`.venv/Scripts/python -m scripts.find_missing_skills`
Expected: `wrote ...2026-09-taxonomy-expansion.md (N kept of M candidates)`. JobSpy scraping and LLM batches can take several minutes; if a role returns 0 postings, re-run once. Record the command output in your report.

- [ ] **Step 6: Choose and add the new skills**

From the report's kept rows, add every candidate that is a concrete technical skill (language, framework, tool, platform, technique). Skip soft skills, job titles, vague terms, and near-duplicates of existing skills. Append to the report:

```markdown
## Added to the taxonomy

| Skill id | Name | Aliases | Category | Prerequisites | Evidence (max share) |
|---|---|---|---|---|---|

## Kept but not added

| Candidate | Reason |
|---|---|
```

For each added skill:
- `skills_taxonomy.json`: append `{"id", "name", "aliases", "category", "prerequisites"}`; `category` must be one of the existing categories (`programming, web-frontend, web-backend, data-science, machine-learning, data-engineering, devops-cloud, cybersecurity, professional`); `prerequisites` only existing skill ids, keeping the graph acyclic; aliases must not collide with any existing name/id/alias.
- `skill_subtopics.json`: an entry following every Task 2 rule (roadmap URLs verified 200 or `""`).
- `courses_sample.json`: at least one course `{"id": "course-NNN" (next free number), "skill_id", "title", "provider", "url", "free": true}` for a real, free resource whose URL returns 200 (`curl -sL -o /dev/null -w "%{http_code}" <url>`).

- [ ] **Step 7: Run the full suite**

Run: `cd backend && .venv/Scripts/python -m pytest -q`
Expected: all pass — including `test_taxonomy_is_dag` (test_core.py), `test_subtopics_data.py` (covers the new skills) and `test_taxonomy_aliases.py`.

- [ ] **Step 8: Commit**

```bash
git add backend/scripts/find_missing_skills.py backend/tests/test_find_missing_skills.py backend/tests/test_taxonomy_aliases.py docs/research/2026-09-taxonomy-expansion.md backend/app/data/skills_taxonomy.json backend/app/data/skill_subtopics.json backend/app/data/courses_sample.json
git commit -m "feat(data): expand skill taxonomy from ESCO + live job-posting evidence

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Planner attaches sub-topics; verifier guards them

**Files:**
- Modify: `backend/app/schemas.py` (`PathStep` fields)
- Modify: `backend/app/agents/planner_agent.py`
- Modify: `backend/app/agents/verifier_agent.py` (`_hard_checks`)
- Test: `backend/tests/test_planner_subtopics.py`, `backend/tests/test_verifier_subtopics.py`

**Interfaces:**
- Consumes: Task 1 `select_subtopics`, `roadmap_url_for`, `subtopics_for`, `Subtopic`; Task 2/3 data.
- Produces: `PathStep.subtopics: list[Subtopic] = []`, `PathStep.roadmap_url: str = ""`; `planner_agent.WEEKS_PER_SUBTOPIC = 0.75`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_planner_subtopics.py`:

```python
"""build_path attaches curated sub-topics + roadmap links and uses them in the
prompt and the fallback week estimate. LLM and resource curation are patched."""
from unittest.mock import MagicMock, patch

from app.agents.planner_agent import WEEKS_PER_SUBTOPIC, build_path
from app.core.taxonomy import roadmap_url_for, select_subtopics
from app.schemas import GapReport, SkillGap, StudentProfile


def _gap(sid, name, current, required):
    return SkillGap(skill_id=sid, name=name, demand_share=0.5, current_level=current,
                    required_level=required, gap_size=1.0, priority=0.5)


GAPS = [_gap("python", "Python", "none", "advanced"), _gap("sql", "SQL", "beginner", "intermediate")]


def _build(hours=10, llm_content=None):
    profile = StudentProfile(hours_per_week=hours, target_role="Backend Developer")
    report = GapReport(target_role="Backend Developer", gaps=GAPS)
    with patch("app.agents.planner_agent.curate_resources", return_value=[]):
        if llm_content is None:
            with patch("app.agents.planner_agent.get_llm", side_effect=RuntimeError("no llm")):
                return build_path(profile, report)
        with patch("app.agents.planner_agent.get_llm"), \
             patch("app.agents.planner_agent.invoke_llm",
                   return_value=MagicMock(content=llm_content)) as invoke:
            path, notes = build_path(profile, report)
            return path, notes, invoke.call_args.args[1]


def test_steps_carry_selected_subtopics_and_roadmap_url():
    path, _ = _build()
    by_id = {s.skill_id: s for s in path.steps}
    assert by_id["python"].subtopics == select_subtopics("python", "none", "advanced")
    assert by_id["sql"].subtopics == select_subtopics("sql", "beginner", "intermediate")
    assert by_id["python"].roadmap_url == roadmap_url_for("python")
    assert all(s.subtopics for s in path.steps)


def test_fallback_weeks_scale_with_subtopic_count_and_hours():
    path, _ = _build(hours=5)
    for step in path.steps:
        expected = round(len(step.subtopics) * WEEKS_PER_SUBTOPIC * (10 / 5), 1)
        assert step.estimated_weeks == min(max(expected, 0.5), 8)


def test_prompt_lists_each_steps_subtopics():
    _path, _notes, prompt = _build(llm_content='{"steps": [], "rationale": "r"}')
    for sid, cur, req in (("python", "none", "advanced"), ("sql", "beginner", "intermediate")):
        for t in select_subtopics(sid, cur, req):
            assert t.name in prompt
```

`backend/tests/test_verifier_subtopics.py`:

```python
"""Verifier hard check: every sub-topic must come from the curated curriculum."""
from unittest.mock import MagicMock, patch

from app.agents.verifier_agent import _hard_checks
from app.core.taxonomy import subtopics_for
from app.schemas import GapReport, LearningPath, PathStep, StudentProfile, Subtopic


def _checks(step: PathStep):
    path = LearningPath(target_role="Backend Developer", steps=[step],
                        total_weeks=step.estimated_weeks)
    catalog = MagicMock()
    catalog.get.return_value = {"ids": [], "metadatas": []}
    with patch("app.agents.verifier_agent.courses_collection", return_value=catalog):
        return _hard_checks(path, GapReport(target_role="Backend Developer"),
                            StudentProfile(hours_per_week=10, target_role="Backend Developer"))


def _step(subtopics):
    return PathStep(order=1, skill_id="python", skill_name="Python", objective="o",
                    estimated_weeks=2.0, subtopics=subtopics)


def test_curated_subtopics_raise_no_subtopic_issue():
    caps, issues = _checks(_step(subtopics_for("python")[:2]))
    assert not any("curated curriculum" in i for i in issues)
    assert caps["groundedness"] == 3.0  # only the pre-existing no-resources cap applies


def test_unknown_subtopic_caps_groundedness_at_one():
    caps, issues = _checks(_step([Subtopic(id="python-made-up", name="Made up", level="beginner")]))
    assert caps["groundedness"] == 1.0
    assert "Sub-topic 'Made up' is not in the curated curriculum for Python" in issues
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_planner_subtopics.py tests/test_verifier_subtopics.py -v`
Expected: `ImportError: cannot import name 'WEEKS_PER_SUBTOPIC'` and a pydantic error for the unknown `subtopics` field on `PathStep`.

- [ ] **Step 3: Implement**

`backend/app/schemas.py` — `class PathStep` gains two fields after `milestone: str = ""`:

```python
    subtopics: list[Subtopic] = []
    roadmap_url: str = ""
```

(`Subtopic` is defined in Task 1 right after `StudentProfile`, which is above `PathStep`.)

`backend/app/agents/planner_agent.py`:

(a) imports: change `from ..core.taxonomy import prerequisite_order` to

```python
from ..core.taxonomy import prerequisite_order, roadmap_url_for, select_subtopics
```

(b) constants: replace

```python
# fallback weeks per unit of gap_size at 10 h/week
BASE_WEEKS_PER_GAP_UNIT = 1.5
```

with

```python
# fallback weeks per curated sub-topic at 10 h/week
WEEKS_PER_SUBTOPIC = 0.75
```

(c) `PLAN_PROMPT`: replace the line

```
For each skill below, write:
```

with

```
For each skill below, write (the objective and milestone must cover that skill's listed sub-topics):
```

(d) in `build_path`, replace

```python
    gap_by_id = {g.skill_id: g for g in top_gaps}
    ordered_ids = prerequisite_order(list(gap_by_id.keys()))

    skills_block = "\n".join(
        f"- {gap_by_id[sid].name} (skill_id: {sid}; current: {gap_by_id[sid].current_level}; "
        f"required: {gap_by_id[sid].required_level}; demanded by "
        f"{gap_by_id[sid].demand_share:.0%} of postings)"
        for sid in ordered_ids
    )
```

with

```python
    gap_by_id = {g.skill_id: g for g in top_gaps}
    ordered_ids = prerequisite_order(list(gap_by_id.keys()))
    subtopics_by_id = {
        sid: select_subtopics(sid, gap_by_id[sid].current_level, gap_by_id[sid].required_level)
        for sid in ordered_ids
    }

    skills_block = "\n".join(
        f"- {gap_by_id[sid].name} (skill_id: {sid}; current: {gap_by_id[sid].current_level}; "
        f"required: {gap_by_id[sid].required_level}; demanded by "
        f"{gap_by_id[sid].demand_share:.0%} of postings; sub-topics: "
        f"{', '.join(t.name for t in subtopics_by_id[sid]) or 'none listed'})"
        for sid in ordered_ids
    )
```

(e) in the steps loop, replace the fallback-weeks block

```python
        if not 0.5 <= weeks <= 8:
            # deterministic estimate scaled by study hours
            weeks = round(gap.gap_size * BASE_WEEKS_PER_GAP_UNIT * (10 / max(profile.hours_per_week, 1)), 1)
            weeks = min(max(weeks, 0.5), 8)
```

with

```python
        subtopics = subtopics_by_id[sid]
        if not 0.5 <= weeks <= 8:
            # deterministic estimate: curated sub-topic count, scaled by study hours
            weeks = round(max(len(subtopics), 1) * WEEKS_PER_SUBTOPIC
                          * (10 / max(profile.hours_per_week, 1)), 1)
            weeks = min(max(weeks, 0.5), 8)
```

and in the `steps.append(PathStep(...))` call add, after `estimated_weeks=weeks,`:

```python
            subtopics=subtopics,
            roadmap_url=roadmap_url_for(sid),
```

`backend/app/agents/verifier_agent.py`:

(a) change `from ..core.taxonomy import load_taxonomy` to `from ..core.taxonomy import load_taxonomy, subtopics_for`

(b) in `_hard_checks`, directly after the resource loop (after the `issues.append(f"Resource '{r.title}' ... (possible hallucination).")` block) and before `# C: top-priority gaps must be covered`, add:

```python
    # G: sub-topics must come from the curated curriculum (nothing invented)
    for step in path.steps:
        curated = {t.id for t in subtopics_for(step.skill_id)}
        for t in step.subtopics:
            if t.id not in curated:
                caps["groundedness"] = 1.0
                issues.append(f"Sub-topic '{t.name}' is not in the curated curriculum "
                              f"for {step.skill_name}")
```

Also update the module docstring's `G` line to: `G  Groundedness  every resource exists in the course catalog and actually teaches that step's skill; every sub-topic is in the curated curriculum`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_planner_subtopics.py tests/test_verifier_subtopics.py -v`
Expected: 5 PASS
Run: `cd backend && .venv/Scripts/python -m pytest -q` → all pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/agents/planner_agent.py backend/app/agents/verifier_agent.py backend/tests/test_planner_subtopics.py backend/tests/test_verifier_subtopics.py
git commit -m "feat(backend): build path steps from curated sub-topics; verifier rejects uncurated ones

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Persist sub-topics and return them from the tracker

**Files:**
- Modify: `backend/app/db/models.py` (`PathStep`)
- Modify: `backend/app/db/database.py` (`run_migrations`)
- Modify: `backend/app/db/crud.py` (`create_path_steps`)
- Modify: `backend/app/main.py` (`get_journeys` step dict)
- Test: `backend/tests/test_migrations.py`, `backend/tests/test_subtopic_storage.py`

**Interfaces:**
- Consumes: Task 4 `PathStep.subtopics` / `PathStep.roadmap_url` (pydantic).
- Produces: `GET /api/tracker/journeys` steps include `"subtopics": [{"id","name","level"}, ...]` and `"roadmap_url": str` (`[]` / `""` for pre-R1 rows).

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_migrations.py`, after the line `assert {"quiz_score", "confidence_rating", "time_spent_minutes"} <= path_step_cols` add:

```python
    assert {"subtopics_json", "roadmap_url"} <= path_step_cols
```

`backend/tests/test_subtopic_storage.py`:

```python
"""Sub-topics round-trip: planner PathStep -> DB -> tracker journeys endpoint."""
from app.db import crud, database, models
from app.main import get_journeys
from app.schemas import PathStep, Subtopic


def _db_and_user():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    db = database.sessionmaker(bind=engine)()
    user = models.User(email="subtopics@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_subtopics_and_roadmap_url_round_trip_to_tracker():
    db, user = _db_and_user()
    journey = crud.create_learning_journey(db, user.id, "Backend Developer")
    step = PathStep(order=1, skill_id="python", skill_name="Python", objective="o",
                    milestone="m", estimated_weeks=2.0,
                    subtopics=[Subtopic(id="python-oop", name="OOP", level="intermediate")],
                    roadmap_url="https://roadmap.sh/python")
    crud.create_path_steps(db, journey.id, [step])

    tracked = get_journeys(db, user)[0]["steps"][0]
    assert tracked["subtopics"] == [{"id": "python-oop", "name": "OOP", "level": "intermediate"}]
    assert tracked["roadmap_url"] == "https://roadmap.sh/python"


def test_pre_r1_step_rows_read_as_empty():
    db, user = _db_and_user()
    journey = crud.create_learning_journey(db, user.id, "Backend Developer")
    db.add(models.PathStep(journey_id=journey.id, order=1, skill_id="python", skill_name="Python",
                           objective="o", milestone="m", estimated_weeks=1.0))
    db.commit()

    tracked = get_journeys(db, user)[0]["steps"][0]
    assert tracked["subtopics"] == []
    assert tracked["roadmap_url"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_migrations.py tests/test_subtopic_storage.py -v`
Expected: migration assertion fails; storage tests fail with `KeyError: 'subtopics'`.

- [ ] **Step 3: Implement**

`backend/app/db/models.py` — in `class PathStep`, after `resources_json = Column(Text, default="[]") # JSON string of resources`:

```python
    subtopics_json = Column(Text, default="[]")  # JSON list of {id, name, level}
    roadmap_url = Column(String, default="")
```

`backend/app/db/database.py` — append to `run_migrations`' `statements` list:

```python
        "ALTER TABLE path_steps ADD COLUMN subtopics_json TEXT DEFAULT '[]'",
        "ALTER TABLE path_steps ADD COLUMN roadmap_url VARCHAR DEFAULT ''",
```

`backend/app/db/crud.py` — in `create_path_steps`, the `models.PathStep(...)` call gains after `resources_json=json.dumps([r.model_dump() for r in s.resources])` (add a comma to that line):

```python
            subtopics_json=json.dumps([t.model_dump() for t in s.subtopics]),
            roadmap_url=s.roadmap_url,
```

`backend/app/main.py` — in `get_journeys`, the per-step dict gains after the `"resources": ...` entry:

```python
                    "subtopics": json.loads(s.subtopics_json) if s.subtopics_json else [],
                    "roadmap_url": s.roadmap_url or "",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_migrations.py tests/test_subtopic_storage.py -v` → PASS
Run: `cd backend && .venv/Scripts/python -m pytest -q` → all pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/app/db/database.py backend/app/db/crud.py backend/app/main.py backend/tests/test_migrations.py backend/tests/test_subtopic_storage.py
git commit -m "feat(backend): persist step sub-topics and roadmap links; return them from the tracker

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Frontend — sub-topic list, roadmap link, attribution

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/components/SubtopicList.tsx`
- Modify: `frontend/src/components/Results.tsx` (`PathTimeline`)
- Modify: `frontend/src/routes/TrackerPage.tsx`
- Modify: `frontend/src/styles/index.css`
- Test: `frontend/src/components/SubtopicList.test.tsx`

**Interfaces:**
- Consumes: Task 4/5 JSON — `PathStep` / tracker step `subtopics: {id, name, level}[]`, `roadmap_url: string`.
- Produces: `SubtopicList` (default export, props `{ subtopics: Subtopic[]; roadmapUrl: string }`), `CurriculumAttribution` (named export).

- [ ] **Step 1: Write the failing test**

`frontend/src/components/SubtopicList.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import SubtopicList, { CurriculumAttribution } from './SubtopicList'
import type { Subtopic } from '../api/types'

const SUBS: Subtopic[] = [
  { id: 'python-oop', name: 'Object-oriented programming', level: 'intermediate' },
  { id: 'python-async', name: 'Async & concurrency', level: 'advanced' },
]

describe('SubtopicList', () => {
  it('renders sub-topics in order with level tags and the roadmap link', () => {
    render(<SubtopicList subtopics={SUBS} roadmapUrl="https://roadmap.sh/python" />)
    const items = screen.getAllByRole('listitem')
    expect(items.map((li) => li.textContent)).toEqual([
      'Object-oriented programming Intermediate',
      'Async & concurrency Advanced',
    ])
    expect(screen.getByText(/See on roadmap\.sh/)).toHaveAttribute('href', 'https://roadmap.sh/python')
  })

  it('omits the roadmap link when there is no URL', () => {
    render(<SubtopicList subtopics={SUBS} roadmapUrl="" />)
    expect(screen.queryByText(/See on roadmap\.sh/)).not.toBeInTheDocument()
  })

  it('renders nothing when there are no sub-topics and no link', () => {
    const { container } = render(<SubtopicList subtopics={[]} roadmapUrl="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the curriculum attribution text', () => {
    render(<CurriculumAttribution />)
    expect(screen.getByText(
      'Curriculum data: ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0), Microsoft Learn',
    )).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/components/SubtopicList.test.tsx --pool=threads`
Expected: FAIL — `Failed to resolve import "./SubtopicList"`

- [ ] **Step 3: Implement**

`frontend/src/api/types.ts` — add above `export interface PathStep`:

```ts
export interface Subtopic {
  id: string
  name: string
  level: 'beginner' | 'intermediate' | 'advanced'
}
```

In `PathStep` add after `milestone: string` (optional so older fixtures/journeys stay valid):

```ts
  subtopics?: Subtopic[]
  roadmap_url?: string
```

In `TrackerStep` add after `github_evidence: TrackerStepGithubEvidence[]`:

```ts
  subtopics?: Subtopic[]
  roadmap_url?: string
```

`frontend/src/components/SubtopicList.tsx`:

```tsx
import type { Subtopic } from '../api/types'

const LEVEL_LABEL: Record<Subtopic['level'], string> = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

export default function SubtopicList({ subtopics, roadmapUrl }: { subtopics: Subtopic[]; roadmapUrl: string }) {
  if (subtopics.length === 0 && !roadmapUrl) return null
  return (
    <div className="subtopics">
      {subtopics.length > 0 && (
        <ol className="subtopic-list">
          {subtopics.map((t) => (
            <li key={t.id}>
              {t.name} <span className={`tag level-${t.level}`}>{LEVEL_LABEL[t.level]}</span>
            </li>
          ))}
        </ol>
      )}
      {roadmapUrl && (
        <a className="resource" href={roadmapUrl} target="_blank" rel="noreferrer">
          🗺 See on roadmap.sh ↗
        </a>
      )}
    </div>
  )
}

export function CurriculumAttribution() {
  return (
    <p className="hint">
      Curriculum data: ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0), Microsoft Learn
    </p>
  )
}
```

`frontend/src/components/Results.tsx`:
- add the import `import SubtopicList, { CurriculumAttribution } from './SubtopicList'` next to the other component imports;
- in `PathTimeline`, directly after `<p className="milestone">🏁 {s.milestone}</p>` add
  `<SubtopicList subtopics={s.subtopics ?? []} roadmapUrl={s.roadmap_url ?? ''} />`;
- directly after the closing `</div>` of `<div className="syllabus">` (still inside the panel) add `<CurriculumAttribution />`.

`frontend/src/routes/TrackerPage.tsx`:
- add `import SubtopicList from '../components/SubtopicList'`;
- directly after `<p className="milestone">🏁 {s.milestone}</p>` add
  `<SubtopicList subtopics={s.subtopics ?? []} roadmapUrl={s.roadmap_url ?? ''} />`.

`frontend/src/styles/index.css` — append:

```css
/* Curated sub-topics inside a path step */
.subtopics {
  margin-top: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  align-items: flex-start;
}
.subtopic-list {
  margin: 0;
  padding-left: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.subtopic-list .tag {
  margin-left: 0.35rem;
  font-size: 0.72rem;
}
```

- [ ] **Step 4: Run tests and type check**

Run: `cd frontend && npx vitest run src/components/SubtopicList.test.tsx --pool=threads` → 4 PASS
Run: `cd frontend && npx vitest run --pool=threads` → all pass
Run: `cd frontend && npx tsc -b` → no errors; then delete `frontend/tsconfig.tsbuildinfo`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/components/SubtopicList.tsx frontend/src/components/SubtopicList.test.tsx frontend/src/components/Results.tsx frontend/src/routes/TrackerPage.tsx frontend/src/styles/index.css
git commit -m "feat(frontend): show curated sub-topics, roadmap.sh links and curriculum attribution

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Live verification

No new committed code.

- [ ] **Step 1: Full suites** — backend `pytest -q` and frontend `vitest run --pool=threads` all pass.
- [ ] **Step 2: Live advisory run** — start the backend (`preview_start` name `backend`, port 8000). With a throwaway local test account, POST `/api/advise` for a real role (e.g. "Full-Stack Developer") with a short resume; confirm every step in the response has non-empty `subtopics` drawn from `skill_subtopics.json`, sensible `estimated_weeks`, a `roadmap_url` where one exists, and that the critique has no "curated curriculum" issue. Confirm two different resumes (beginner vs experienced) for the same role get different sub-topic windows for a shared skill.
- [ ] **Step 3: UI** — port 8080 is held by Docker Desktop on this machine and `frontend/vite.config.ts` proxies `/api` to 8080, so run a temporary Vite config (`frontend/vite.verify.config.ts` merging the base config with `server: { host: '127.0.0.1', port: 5174, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } }`) via a temporary `.claude/launch.json` entry; log in, check the Results path and Tracker steps show ordered sub-topics with level tags, roadmap links and the attribution line; screenshot. Remove the temporary config file and launch entry afterwards (`git checkout -- .claude/launch.json`).
- [ ] **Step 4:** Update the `skillmeet-parity-roadmap` memory (roadmap overhaul R1 shipped; next R2).
