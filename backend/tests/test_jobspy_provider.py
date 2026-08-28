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
