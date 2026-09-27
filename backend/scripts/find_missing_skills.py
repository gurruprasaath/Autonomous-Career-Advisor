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

# ESCO has no exact occupation for several of this app's roles, and free-text
# search drifts badly (e.g. "Full-Stack Developer" -> "property developer"),
# so each role is mapped by hand to the closest ESCO occupation URI.
ESCO_OCCUPATIONS = {
    "Data Scientist": "http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30",  # data scientist
    "ML Engineer": "http://data.europa.eu/esco/occupation/35553663-deab-4d9a-bf22-15c1625d28e8",  # ICT intelligent systems designer
    "Full-Stack Developer": "http://data.europa.eu/esco/occupation/c40a2919-48a9-40ea-b506-1f34f693496d",  # web developer
    "DevOps Engineer": "http://data.europa.eu/esco/occupation/9e2e6e1e-363b-4e1b-a673-7bc0f7343300",  # ICT system administrator
    "Cybersecurity Analyst": "http://data.europa.eu/esco/occupation/0464b062-cea6-4164-b10d-956c61956ae7",  # ICT security administrator
    "Data Engineer": "http://data.europa.eu/esco/occupation/1562c7a3-c7d9-419d-b9b6-db26610bcf84",  # data warehouse designer
}

EXTRACT_PROMPT = """From the job descriptions below, list every distinct technology, tool, framework, platform, programming language or technical methodology that is named (e.g. "Snowflake", "Power BI", "Jenkins"). Use the name as written. No soft skills, no job titles.

{descriptions}

Return ONLY a JSON array of strings."""


def normalize(term: str) -> str:
    """'Python (computer programming)' -> 'Python'. Also normalizes Unicode hyphens and NBSP."""
    # Convert Unicode hyphens (U+2010-U+2015, U+2212) to ASCII hyphen
    term = re.sub(r"[‐-―−]", "-", term)
    # Convert non-breaking spaces (U+00A0, U+202F) to regular space
    term = re.sub(r"[  ]", " ", term)
    # Strip parentheticals
    term = re.sub(r"\s*\(.*?\)", "", term)
    return term.strip()


def share(term: str, descriptions: list[str]) -> float:
    """Fraction of descriptions mentioning term as a whole word (case-insensitive)."""
    if not descriptions:
        return 0.0
    pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
    return sum(1 for d in descriptions if pattern.search(d)) / len(descriptions)


def esco_skills(role: str) -> tuple[str, list[str]]:
    """('<occupation title> <uri>', essential + optional skill titles)."""
    # Use hand-mapped ESCO occupations when available
    if role in ESCO_OCCUPATIONS:
        uri = ESCO_OCCUPATIONS[role]
        detail = httpx.get(f"{ESCO_API}/resource/occupation", timeout=30, params={
            "uri": uri, "language": "en"}).json()
        links = detail.get("_links", {})
        titles = [s["title"] for key in ("hasEssentialSkill", "hasOptionalSkill")
                  for s in links.get(key, [])]
        return f"{detail['title']} <{uri}> (closest ESCO occupation)", titles

    # Fallback to free-text search for unmapped roles
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
        "ESCO has no exact occupation for several roles; each role is mapped to the closest ESCO occupation by hand (ESCO_OCCUPATIONS in the script).",
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
