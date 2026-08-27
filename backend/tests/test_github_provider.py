"""GitHub public-repo language fetch. Mocks httpx — no real network calls."""
import io
import zipfile
from unittest.mock import patch, MagicMock

import pytest

from app.providers.github import (
    GithubRateLimited,
    GithubUserNotFound,
    download_and_extract_repo,
    fetch_repo_languages,
    map_languages_to_evidence,
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


def test_map_languages_matches_legitimate_language():
    languages = {"Python": [{"repo_name": "my-api", "last_pushed_at": "2026-07-01T00:00:00Z"}]}
    rows = map_languages_to_evidence(languages)
    assert len(rows) == 1
    assert rows[0]["skill_id"] == "python"
    assert rows[0]["repo_name"] == "my-api"


def test_map_languages_excludes_low_confidence_matches():
    # "Jupyter Notebook" only weakly matches "python" via the embedding
    # fallback (well under the 0.6 confidence floor) — must not produce
    # a false evidence chip.
    languages = {
        "Python": [{"repo_name": "my-api", "last_pushed_at": "2026-07-01T00:00:00Z"}],
        "Jupyter Notebook": [{"repo_name": "notebooks", "last_pushed_at": "2026-06-01T00:00:00Z"}],
    }
    rows = map_languages_to_evidence(languages)
    assert any(r["repo_language"] == "Python" for r in rows)
    assert not any(r["repo_language"] == "Jupyter Notebook" for r in rows)


def test_map_languages_unmapped_language_produces_no_row():
    # Languages the taxonomy simply doesn't cover (Go, Rust, ...) are
    # ignored, not an error.
    languages = {"Rust": [{"repo_name": "systems-proj", "last_pushed_at": "2026-07-01T00:00:00Z"}]}
    rows = map_languages_to_evidence(languages)
    assert rows == []


def _make_zip(entries):
    """entries: list of (path, content_bytes). Wrapped in a root dir like a
    real GitHub zipball (owner-repo-sha/...)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in entries:
            z.writestr(f"owner-repo-abc123/{path}", content)
    return buf.getvalue()


def _mock_zip_download(zip_bytes):
    resp = MagicMock()
    resp.status_code = 200
    resp.content = zip_bytes
    resp.raise_for_status.return_value = None
    return resp


def test_oversized_entry_skipped_via_pre_decompression_size_check():
    small_content = b"print('hello')\n"
    # Highly compressible: a few MB of one repeated byte compresses to almost
    # nothing but decompresses to a lot — the fix must reject it using the
    # zip header's file_size, not by decompressing first.
    huge_compressible = b"A" * (5 * 1024 * 1024)
    zip_bytes = _make_zip([("small.py", small_content), ("huge.py", huge_compressible)])

    with patch("app.providers.github.httpx.get", return_value=_mock_zip_download(zip_bytes)):
        files = download_and_extract_repo("owner", "repo")

    paths = {f["path"] for f in files}
    assert "small.py" in paths
    assert "huge.py" not in paths


def test_total_file_count_cap_respected():
    entries = [(f"file_{i}.py", f"print({i})".encode()) for i in range(10)]
    zip_bytes = _make_zip(entries)

    with patch("app.providers.github.httpx.get", return_value=_mock_zip_download(zip_bytes)), \
         patch("app.providers.github.MAX_TOTAL_FILES", 3):
        files = download_and_extract_repo("owner", "repo")

    assert len(files) == 3


def test_total_byte_cap_respected():
    entries = [(f"file_{i}.py", b"x" * 20) for i in range(5)]
    zip_bytes = _make_zip(entries)

    with patch("app.providers.github.httpx.get", return_value=_mock_zip_download(zip_bytes)), \
         patch("app.providers.github.MAX_TOTAL_BYTES", 25):
        files = download_and_extract_repo("owner", "repo")

    assert len(files) == 2  # 20 bytes, then 40 >= 25 cap -> stop


def test_package_lock_json_excluded_by_exact_basename():
    entries = [("package-lock.json", b'{"lockfileVersion": 1}'),
               ("sub/package-lock.json", b'{"lockfileVersion": 1}'),
               ("app.py", b"print('ok')")]
    zip_bytes = _make_zip(entries)

    with patch("app.providers.github.httpx.get", return_value=_mock_zip_download(zip_bytes)):
        files = download_and_extract_repo("owner", "repo")

    assert {f["path"] for f in files} == {"app.py"}


def test_map_languages_dedupes_same_skill_from_multiple_languages_in_one_repo():
    # GitHub reports HTML and CSS as separate languages that both map to the
    # taxonomy's single "html-css" skill — a repo with both must contribute
    # only one evidence row for that skill, not two.
    languages = {
        "HTML": [{"repo_name": "portfolio-site", "last_pushed_at": "2026-07-01T00:00:00Z"}],
        "CSS": [{"repo_name": "portfolio-site", "last_pushed_at": "2026-07-01T00:00:00Z"}],
    }
    rows = map_languages_to_evidence(languages)
    matching = [r for r in rows if r["repo_name"] == "portfolio-site"]
    assert len(matching) == 1
