"""Live Adzuna job API provider.

Enable by setting in .env:
    JOB_PROVIDER=adzuna
    ADZUNA_APP_ID=...     (register free at https://developer.adzuna.com)
    ADZUNA_APP_KEY=...

Adzuna postings carry no structured skill annotations, so the Market
Demand Agent extracts skills from the raw descriptions (same code path
used for sample data when annotations are missing).
"""
import httpx

from ..config import get_settings
from .base import JobProvider, Posting

API_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

# Adzuna is a general job board; we search by keyword rather than fixed roles.
DEFAULT_ROLES = [
    "Data Scientist", "ML Engineer", "Full-Stack Developer",
    "DevOps Engineer", "Cybersecurity Analyst", "Data Engineer",
]


class AdzunaJobProvider(JobProvider):
    def __init__(self) -> None:
        s = get_settings()
        if not (s.adzuna_app_id and s.adzuna_app_key):
            raise RuntimeError(
                "JOB_PROVIDER=adzuna but ADZUNA_APP_ID/ADZUNA_APP_KEY are not set in .env"
            )
        self._settings = s

    def fetch(self, role: str, limit: int = 50) -> list[Posting]:
        s = self._settings
        resp = httpx.get(
            API_URL.format(country=s.adzuna_country),
            params={
                "app_id": s.adzuna_app_id,
                "app_key": s.adzuna_app_key,
                "what": role,
                "results_per_page": min(limit, 50),
                "content-type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [
            Posting(
                id=f"adzuna-{item['id']}",
                role=role,
                title=item.get("title", role),
                company=(item.get("company") or {}).get("display_name", "Unknown"),
                location=(item.get("location") or {}).get("display_name", ""),
                description=item.get("description", ""),
                skills=[],  # no annotations — extracted downstream
            )
            for item in results
        ]

    def available_roles(self) -> list[str]:
        return DEFAULT_ROLES
