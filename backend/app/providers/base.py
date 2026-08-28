"""Job posting provider interface.

The Market Demand Agent only talks to this interface, so swapping the
bundled sample dataset for a live API (Adzuna) is a config change,
not a code change.
"""
from abc import ABC, abstractmethod
from typing import TypedDict


class Posting(TypedDict):
    id: str
    role: str
    title: str
    company: str
    location: str
    description: str
    skills: list  # optional pre-annotated [{skill_id, level}] (sample data only)
    url: str  # apply link — empty string when the provider has none (sample data)


class JobProvider(ABC):
    @abstractmethod
    def fetch(self, role: str, limit: int = 50) -> list[Posting]:
        """Return postings for a target role."""

    @abstractmethod
    def available_roles(self) -> list[str]:
        """Roles this provider can serve."""
