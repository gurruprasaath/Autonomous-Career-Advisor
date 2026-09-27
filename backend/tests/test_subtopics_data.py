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
