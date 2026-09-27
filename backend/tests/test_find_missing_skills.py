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


def test_normalize_converts_unicode_hyphens_and_nbsp():
    assert normalize("Time‑Series Analysis") == "Time-Series Analysis"
    assert normalize("real‐time systems") == "real-time systems"
    assert normalize("A−B") == "A-B"
    assert normalize("Power BI") == "Power BI"
    assert normalize("Power BI") == "Power BI"


def test_every_app_role_has_a_hand_mapped_esco_occupation():
    from app.providers import get_job_provider
    from scripts.find_missing_skills import ESCO_OCCUPATIONS
    assert set(get_job_provider().available_roles()) <= set(ESCO_OCCUPATIONS)
    assert all(u.startswith("http://data.europa.eu/esco/occupation/") for u in ESCO_OCCUPATIONS.values())
