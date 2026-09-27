"""Market Demand Agent.

Aggregates skill demand for a target role from job postings, with an
evidence trail (posting ids) for every skill — no LLM in the counting
path, so demand numbers are reproducible and citable.

Sample postings carry skill annotations; live postings (Adzuna) don't,
so skills are extracted from descriptions by deterministic taxonomy
scanning (names + aliases as whole words).
"""
import logging
import re
from collections import defaultdict

from ..core.taxonomy import load_taxonomy
from ..providers import get_job_provider
from ..providers.base import Posting
from ..schemas import MASTERY_SCORE, MarketDemandProfile, SkillDemand

log = logging.getLogger(__name__)


# terms too ambiguous to scan for in free-flowing text ("go far", "James R.",
# "maintenance windows")
SCAN_STOPLIST = {"go", "r", "windows"}


def _scan_description(text: str) -> list[dict]:
    lower = text.lower()
    found = []
    for node in load_taxonomy().values():
        terms = {node.name.lower(), node.id.lower(), *[a.lower() for a in node.aliases]}
        for term in terms - SCAN_STOPLIST:
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
                found.append({"skill_id": node.id, "level": "intermediate"})
                break
    return found


def _posting_skills(posting: Posting) -> list[dict]:
    return posting.get("skills") or _scan_description(posting["description"])


def analyse_market(target_role: str, limit: int = 50
                   ) -> tuple[MarketDemandProfile, dict[str, str], list[str]]:
    """Returns (demand_profile, required_levels, notes).

    required_levels: skill_id -> the highest level postings commonly ask
    for (mode of demanded levels), consumed by the gap engine.
    """
    notes: list[str] = []
    provider = get_job_provider()
    postings = provider.fetch(target_role, limit=limit)
    if not postings:
        raise ValueError(
            f"No postings found for role '{target_role}'. "
            f"Available roles: {provider.available_roles()}"
        )

    taxonomy = load_taxonomy()
    freq: dict[str, int] = defaultdict(int)
    evidence: dict[str, list[str]] = defaultdict(list)
    level_votes: dict[str, list[str]] = defaultdict(list)

    for posting in postings:
        seen_in_posting = set()
        for entry in _posting_skills(posting):
            sid = entry["skill_id"]
            if sid not in taxonomy or sid in seen_in_posting:
                continue
            seen_in_posting.add(sid)
            freq[sid] += 1
            evidence[sid].append(posting["id"])
            level_votes[sid].append(entry.get("level", "intermediate"))

    n = len(postings)
    skills = [
        SkillDemand(
            skill_id=sid, name=taxonomy[sid].name, frequency=count,
            share=round(count / n, 3), posting_ids=evidence[sid][:10],
        )
        for sid, count in freq.items()
    ]
    skills.sort(key=lambda s: s.frequency, reverse=True)

    required_levels = {
        sid: max(votes, key=lambda lv: (votes.count(lv), MASTERY_SCORE[lv]))
        for sid, votes in level_votes.items()
    }

    demand = MarketDemandProfile(target_role=target_role,
                                 postings_analysed=n, skills=skills)
    log.info("market: %d postings, %d distinct skills for %s", n, len(skills), target_role)
    return demand, required_levels, notes
