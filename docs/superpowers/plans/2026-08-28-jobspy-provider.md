# JobSpy Job Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `JobSpyProvider`, a free, no-API-key `JobProvider` implementation that scrapes Indeed/Google Jobs/ZipRecruiter via the `python-jobspy` library, selectable with `JOB_PROVIDER=jobspy` alongside the existing `sample`/`adzuna` providers.

**Architecture:** A new provider class implementing the existing `JobProvider` ABC (`fetch`/`available_roles`) — the same shape `AdzunaJobProvider` already follows — so `market_agent.py` and `job_matcher.py` need zero changes. `get_job_provider()`'s dispatch gains one more branch.

**Tech Stack:** `python-jobspy` (new dependency, pandas-based scraper), same FastAPI/pydantic-settings backend as the rest of the project.

## Global Constraints

- Only scrape `indeed`, `google`, `zip_recruiter` — LinkedIn and Glassdoor are excluded (JobSpy's own docs flag them as heavily rate-limited/blocked without proxy infrastructure this project doesn't have).
- `JobSpyProvider.fetch()` must never raise on a scraping failure — return `[]`, reusing `market_agent`/`job_matcher`'s existing "No postings found for role..." error path instead of a new one.
- No change to `market_agent.py`, `gap_engine.py`, `job_matcher.py`, or the `Posting` TypedDict — this is a provider-only addition.
- Every task must leave the backend test suite (`pytest tests/ -v`) passing.

---

### Task 1: `JobSpyProvider`

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Create: `backend/app/providers/jobspy_provider.py`
- Test: `backend/tests/test_jobspy_provider.py`

**Interfaces:**
- Consumes: `JobProvider`, `Posting` from `backend/app/providers/base.py` (existing, unchanged); `get_settings()` from `backend/app/config.py`.
- Produces: `JobSpyProvider` class with `fetch(role: str, limit: int = 50) -> list[Posting]` and `available_roles() -> list[str]` — Task 2's dispatch wiring instantiates this exact class name from this exact module path (`app.providers.jobspy_provider`).

- [ ] **Step 1: Add the dependency**

Append to `backend/requirements.txt`:

```
python-jobspy>=1.1.82
```

- [ ] **Step 2: Install it**

Run: `cd backend && .venv\Scripts\pip install python-jobspy>=1.1.82`
Expected: installs successfully (pulls in pandas, requests, beautifulsoup4, etc. as transitive deps).

- [ ] **Step 3: Add the `jobspy_country` setting**

In `backend/app/config.py`, add one field to the `Settings` class, right after `adzuna_country`:

```python
    adzuna_country: str = "in"
    jobspy_country: str = "India"  # JobSpy/Indeed expects a full country
                                    # name, not an ISO code like
                                    # adzuna_country — kept as its own
                                    # setting so the two providers' config
                                    # isn't coupled together.
    youtube_api_key: str = ""
```

- [ ] **Step 4: Write the failing tests**

Create `backend/tests/test_jobspy_provider.py`:

```python
"""JobSpyProvider: wraps python-jobspy's scrape_jobs, mapping its
DataFrame output onto the shared Posting shape. Mocked at the
jobspy.scrape_jobs boundary — no real network/scraping in tests, same
policy as AdzunaJobProvider (which also has no live-network test)."""
import pandas as pd
from unittest.mock import patch

from app.providers.jobspy_provider import JobSpyProvider


def _fake_df():
    return pd.DataFrame([
        {"title": "Data Engineer", "company": "Acme Corp", "city": "Bengaluru",
         "description": "Build ETL pipelines with Python and Airflow.",
         "job_url": "https://indeed.com/job/abc123"},
        {"title": "Senior Data Engineer", "company": "Globex", "city": "Pune",
         "description": "Own our Spark data platform.",
         "job_url": "https://indeed.com/job/def456"},
    ])


def test_fetch_maps_dataframe_rows_to_postings():
    with patch("jobspy.scrape_jobs", return_value=_fake_df()) as mock_scrape:
        postings = JobSpyProvider().fetch("Data Engineer", limit=10)

    assert len(postings) == 2
    assert postings[0]["title"] == "Data Engineer"
    assert postings[0]["company"] == "Acme Corp"
    assert postings[0]["location"] == "Bengaluru"
    assert postings[0]["url"] == "https://indeed.com/job/abc123"
    assert postings[0]["skills"] == []
    # ids are stable hashes of the job url, not the DataFrame row index
    assert postings[0]["id"] != postings[1]["id"]
    mock_scrape.assert_called_once()
    call_kwargs = mock_scrape.call_args.kwargs
    assert call_kwargs["site_name"] == ["indeed", "google", "zip_recruiter"]
    assert call_kwargs["search_term"] == "Data Engineer"


def test_fetch_returns_empty_list_on_empty_dataframe():
    with patch("jobspy.scrape_jobs", return_value=pd.DataFrame()):
        postings = JobSpyProvider().fetch("Data Engineer")
    assert postings == []


def test_fetch_returns_empty_list_on_scrape_failure_instead_of_raising():
    with patch("jobspy.scrape_jobs", side_effect=RuntimeError("blocked by Indeed")):
        postings = JobSpyProvider().fetch("Data Engineer")
    assert postings == []


def test_available_roles_returns_default_role_list():
    roles = JobSpyProvider().available_roles()
    assert "Data Engineer" in roles
    assert len(roles) == 6
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_jobspy_provider.py -v`
Expected: FAIL — `app.providers.jobspy_provider` does not exist yet.

- [ ] **Step 6: Implement `JobSpyProvider`**

Create `backend/app/providers/jobspy_provider.py`:

```python
"""Live JobSpy-based job provider — scrapes Indeed/Google Jobs/ZipRecruiter
directly, no API key or request quota.

LinkedIn and Glassdoor are deliberately excluded from the default site set:
JobSpy's own docs flag them as heavily rate-limited/blocked without proxy
infrastructure this project doesn't have — Indeed/Google/ZipRecruiter cover
the same skill-signal need without that risk.
"""
import hashlib
import logging

from ..config import get_settings
from .base import JobProvider, Posting

log = logging.getLogger(__name__)

SITES = ["indeed", "google", "zip_recruiter"]

# Same role list Adzuna uses today — JobSpy is a general job-board scraper,
# not a fixed-taxonomy source, so roles are search keywords either way.
DEFAULT_ROLES = [
    "Data Scientist", "ML Engineer", "Full-Stack Developer",
    "DevOps Engineer", "Cybersecurity Analyst", "Data Engineer",
]


class JobSpyProvider(JobProvider):
    def fetch(self, role: str, limit: int = 50) -> list[Posting]:
        import jobspy  # imported lazily: heavy optional dependency

        country = get_settings().jobspy_country
        try:
            df = jobspy.scrape_jobs(
                site_name=SITES,
                search_term=role,
                google_search_term=f"{role} jobs in {country}",
                location=country,
                results_wanted=limit,
                hours_old=24 * 30,  # last 30 days
                country_indeed=country,
            )
        except Exception as e:
            log.warning("JobSpy scrape failed for role %r: %s", role, e)
            return []

        if df is None or df.empty:
            return []

        postings: list[Posting] = []
        for _, row in df.iterrows():
            url = str(row.get("job_url") or "")
            digest = hashlib.sha256(url.encode()).hexdigest()[:16] if url else str(row.name)
            postings.append(Posting(
                id=f"jobspy-{digest}",
                role=role,
                title=str(row.get("title") or role),
                company=str(row.get("company") or "Unknown"),
                location=str(row.get("city") or country),
                description=str(row.get("description") or ""),
                skills=[],  # no annotations — extracted downstream, same as Adzuna
                url=url,
            ))
        return postings

    def available_roles(self) -> list[str]:
        return DEFAULT_ROLES
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_jobspy_provider.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/providers/jobspy_provider.py backend/tests/test_jobspy_provider.py
git commit -m "feat(backend): add JobSpyProvider (free, no-key Indeed/Google/ZipRecruiter scraper)"
```

---

### Task 2: Wire `JobSpyProvider` into the provider dispatch

**Files:**
- Modify: `backend/app/providers/__init__.py`
- Test: `backend/tests/test_job_matcher.py` (add one dispatch-level test)

**Interfaces:**
- Consumes: `JobSpyProvider` from `app.providers.jobspy_provider` (Task 1).
- Produces: `get_job_provider()` returns a `JobSpyProvider` instance when `settings.job_provider == "jobspy"` — nothing later depends on this beyond the dispatch itself, since `market_agent`/`job_matcher` only ever call the returned object through the `JobProvider` interface.

- [ ] **Step 1: Write the failing dispatch test**

Open `backend/tests/test_job_matcher.py`. It already imports `from unittest.mock import patch` at the top (line 4) — add one more import line right after it, `from app.providers import get_job_provider`, then add this test as a standalone function (not inside an existing test class) anywhere in the file:

```python
def test_get_job_provider_returns_jobspy_provider_when_configured():
    with patch("app.providers.get_settings") as mock_settings:
        mock_settings.return_value.job_provider = "jobspy"
        provider = get_job_provider()

    from app.providers.jobspy_provider import JobSpyProvider
    assert isinstance(provider, JobSpyProvider)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_job_matcher.py::test_get_job_provider_returns_jobspy_provider_when_configured -v`
Expected: FAIL — `get_job_provider()` has no `"jobspy"` branch yet, so it falls through to `SampleJobProvider` and the `isinstance` assertion fails.

- [ ] **Step 3: Add the dispatch branch**

In `backend/app/providers/__init__.py`, replace the full contents with:

```python
from ..config import get_settings
from .base import JobProvider


def get_job_provider() -> JobProvider:
    provider = get_settings().job_provider.lower()
    if provider == "adzuna":
        from .adzuna import AdzunaJobProvider
        return AdzunaJobProvider()
    if provider == "jobspy":
        from .jobspy_provider import JobSpyProvider
        return JobSpyProvider()
    from .sample import SampleJobProvider
    return SampleJobProvider()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv\Scripts\python -m pytest tests/test_job_matcher.py::test_get_job_provider_returns_jobspy_provider_when_configured -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && .venv\Scripts\python -m pytest tests/ -v`
Expected: all tests PASS (this task touched only the dispatch function; every other provider's behavior is unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app/providers/__init__.py backend/tests/test_job_matcher.py
git commit -m "feat(backend): wire JobSpyProvider into the job-provider dispatch"
```

---

### Task 3: Activate JobSpy and verify live

**Files:**
- Modify: `backend/.env` (not committed — gitignored, matches how `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` were configured earlier this project)

**Interfaces:**
- Consumes: `JOB_PROVIDER` env var (Task 2's dispatch reads it via `get_settings().job_provider`).
- Produces: nothing further downstream — this is the activation + manual verification task, not a code change.

- [ ] **Step 1: Switch the active provider**

In `backend/.env`, change:

```
JOB_PROVIDER=jobspy
```

(Leave `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` in place, unused but harmless, in case you want to switch back later.)

- [ ] **Step 2: Restart the backend**

Stop any running `uvicorn` process (Windows: find the PID via `Get-NetTCPConnection -LocalPort 8080` in PowerShell, then `Stop-Process -Force`) and start it fresh so the new `.env` value and the new provider module are picked up:

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8080`

- [ ] **Step 3: Verify a live scrape**

With the backend running, call the roles/jobs endpoints for a real role (via the browser, curl, or the running frontend's Job Matches page) and confirm real postings come back with non-empty `title`/`company`/`url` fields from `indeed`/`google`/`zip_recruiter` — expect this call to take noticeably longer than Adzuna did (several seconds, scraping three sites), which is expected and documented in the spec, not a bug.

- [ ] **Step 4: Report back**

No commit for this task (`.env` is gitignored) — confirm to the user that the live verification succeeded (or what error appeared, if JobSpy was blocked on this network) before considering the plan complete.
