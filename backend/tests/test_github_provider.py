"""GitHub public-repo language fetch. Mocks httpx — no real network calls."""
from unittest.mock import patch, MagicMock

import pytest

from app.providers.github import (
    GithubRateLimited,
    GithubUserNotFound,
    fetch_repo_languages,
)


def _mock_response(status_code, json_data):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


REPOS = [
    {"name": "my-api", "pushed_at": "2026-07-01T00:00:00Z", "fork": False},
    {"name": "old-website", "pushed_at": "2024-01-01T00:00:00Z", "fork": False},
    {"name": "forked-repo", "pushed_at": "2026-08-01T00:00:00Z", "fork": True},
]

LANGUAGES_BY_REPO = {
    "my-api": {"Python": 9000, "Dockerfile": 40},
    "old-website": {"JavaScript": 5000, "HTML": 1000},
}


def test_aggregates_languages_across_repos_skips_forks():
    with patch("app.providers.github.httpx.get") as mock_get:
        def side_effect(url, **kwargs):
            if url.endswith("/repos"):
                return _mock_response(200, REPOS)
            for repo_name, langs in LANGUAGES_BY_REPO.items():
                if f"/repos/testuser/{repo_name}/languages" in url:
                    return _mock_response(200, langs)
            return _mock_response(200, {})

        mock_get.side_effect = side_effect

        result = fetch_repo_languages("testuser")

        assert "Python" in result
        assert result["Python"][0]["repo_name"] == "my-api"
        assert "JavaScript" in result
        # forked-repo must never be queried or appear in results
        assert all(r["repo_name"] != "forked-repo"
                   for repos in result.values() for r in repos)


def test_unknown_user_raises():
    with patch("app.providers.github.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(404, {})
        with pytest.raises(GithubUserNotFound):
            fetch_repo_languages("no-such-user-xyz")


def test_rate_limit_raises():
    with patch("app.providers.github.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(403, {})
        with pytest.raises(GithubRateLimited):
            fetch_repo_languages("testuser")
