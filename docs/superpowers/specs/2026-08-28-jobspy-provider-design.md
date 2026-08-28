# JobSpy Job Provider — Design

## Problem

`AdzunaJobProvider` is the only live job-data source wired up. Two live issues motivate a second provider:

1. It's a single source — Adzuna's own India coverage and per-listing description quality vary, and the Job Matches page's "same ~15 jobs every time, doesn't feel well matched" complaint is partly a data-breadth problem, not only a ranking problem.
2. Real-world job description text is much messier/sparser than the old synthetic sample data (already proven by the gap-threshold fix in this same session) — more, better, real postings give every downstream deterministic signal (skill scanning, gap engine, job matcher's overlap score) more to work with.

Deep-research summary (see conversation): Indeed's public API was retired in 2023 and LinkedIn's job API is enterprise-gated — neither is directly available. Of the remaining real options, **JobSpy** (a free, open-source, no-API-key Python scraper covering Indeed/Google Jobs/ZipRecruiter/LinkedIn/Glassdoor) was chosen over JSearch (clean API, but only 200 free requests/month — too tight for active development and demos) and Jooble (free but needs a separate India-region key and is keyword-only with unproven description quality).

## Goals

1. Add `JobSpyProvider` implementing the existing `JobProvider` interface (`fetch`/`available_roles`) — a config change (`JOB_PROVIDER=jobspy`), not a change to `market_agent.py` or `job_matcher.py`, mirroring how `AdzunaJobProvider` was added.
2. Scrape only the reliable sites — `indeed`, `google`, `zip_recruiter` — deliberately excluding LinkedIn and Glassdoor, which JobSpy's own docs flag as heavily rate-limited/blocked without proxy infrastructure this project doesn't have.
3. Degrade gracefully: a scraping failure (site blocks, network error, HTML change) must return `[]`, not propagate a raw exception — `market_agent.analyse_market` and `job_matcher.recommend_jobs` already turn an empty postings list into a clear `"No postings found for role..."` error, so this reuses existing, tested error handling rather than adding new plumbing.

## Non-goals

- Not removing `AdzunaJobProvider` or `SampleJobProvider` — this adds a third pluggable option; `JOB_PROVIDER` still picks exactly one active provider at a time, same as today.
- Not adding LinkedIn/Glassdoor scraping now — flagged as future work if proxy infrastructure is ever added.
- Not changing the Market Demand Agent's skill-scanning, the Gap Engine, or the Job Matcher's scoring blend — this only changes where postings come from.
- Not solving latency: scraping 3 sites synchronously is slower than one API call (likely several seconds per request). Acceptable at this project's scale; not addressed here.

## Design

### New dependency

`requirements.txt` gains `python-jobspy` (PyPI: `python-jobspy`, imported as `from jobspy import scrape_jobs`, requires Python ≥3.10 — already satisfied, this project runs 3.11+).

### New config (`backend/app/config.py`)

```python
jobspy_country: str = "India"  # JobSpy/Indeed expects a full country name,
                                # not an ISO code like ADZUNA_COUNTRY — kept
                                # as its own setting rather than reusing
                                # adzuna_country to avoid coupling the two
                                # providers' config together.
```

### `backend/app/providers/jobspy_provider.py`

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
        from jobspy import scrape_jobs  # imported lazily: heavy optional dep

        country = get_settings().jobspy_country
        try:
            df = scrape_jobs(
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

        postings = []
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

`id` is derived from a hash of the job URL (stable across repeated fetches of the same posting, mirroring why `_repo_collection_name` hashes rather than string-joins in `vectorstore.py`) rather than the DataFrame's row index, which is only stable within one call.

### `backend/app/providers/__init__.py`

```python
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

### Activation

`.env`: `JOB_PROVIDER=jobspy` (replacing `JOB_PROVIDER=adzuna`) plus optionally `JOBSPY_COUNTRY=India`. No `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` needed for this path — that's the point.

## Testing

- `backend/tests/test_jobspy_provider.py`: mock `jobspy.scrape_jobs` (same `unittest.mock.patch` style already used for LLM-touching agents) — a DataFrame-shaped fixture maps to the expected `Posting` list; an empty DataFrame and a raised exception both return `[]` rather than propagating.
- `backend/app/providers/__init__.py`'s `get_job_provider` dispatch: one added case (`job_provider="jobspy"` returns a `JobSpyProvider` instance) alongside whatever existing coverage (if any) already exercises `"adzuna"`/default.
- No live-network test (same policy as `AdzunaJobProvider`, which also has no live-network test) — manual verification against the running server, since scraping in CI would be slow and flaky by nature.
