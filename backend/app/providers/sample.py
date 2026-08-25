"""Bundled synthetic dataset provider (offline development default)."""
import json

from ..config import DATA_DIR
from .base import JobProvider, Posting


class SampleJobProvider(JobProvider):
    def __init__(self) -> None:
        raw = json.loads((DATA_DIR / "jobs_sample.json").read_text(encoding="utf-8"))
        self._postings: list[Posting] = raw["postings"]

    def fetch(self, role: str, limit: int = 50) -> list[Posting]:
        matches = [p for p in self._postings if p["role"].lower() == role.lower()]
        return matches[:limit]

    def available_roles(self) -> list[str]:
        return sorted({p["role"] for p in self._postings})
