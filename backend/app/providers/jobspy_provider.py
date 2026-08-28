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
