"""GitHub public-repo language fetch — unauthenticated public API only.

No OAuth: the student types their GitHub username, we read what's already
public. Good enough to answer "have they actually written code in this
language recently," which is the only claim this evidence makes.
"""
import httpx
import io
import zipfile

from ..core.taxonomy import match_mention

GITHUB_API = "https://api.github.com"

# Recent-30 cap: evidence of *recent* practice is what matters (per design
# spec), and it bounds the per-repo /languages calls against the
# unauthenticated 60 req/hour limit shared by the whole server.
MAX_REPOS = 30

# Below this, match_mention's embedding fallback is producing noise, not
# signal — e.g. "Jupyter Notebook" weakly matching "python" at ~0.056.
EVIDENCE_CONFIDENCE_FLOOR = 0.6


class GithubUserNotFound(RuntimeError):
    pass


class GithubRateLimited(RuntimeError):
    pass


def fetch_repo_languages(username: str) -> dict[str, list[dict]]:
    """username -> {language: [{"repo_name", "last_pushed_at"}, ...]}.

    Forked repos are skipped (they're not evidence the student wrote that
    code). Unauthenticated GitHub API allows 60 requests/hour, which is
    enough for one user's repo list plus a handful of language lookups.
    """
    repos_resp = httpx.get(f"{GITHUB_API}/users/{username}/repos",
                           params={"per_page": 100}, timeout=10)
    if repos_resp.status_code == 404:
        raise GithubUserNotFound(username)
    if repos_resp.status_code in (403, 429):
        raise GithubRateLimited("GitHub API rate limit hit; try again later")
    repos_resp.raise_for_status()

    repos = [r for r in repos_resp.json() if not r.get("fork")]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    repos = repos[:MAX_REPOS]

    result: dict[str, list[dict]] = {}
    for repo in repos:
        lang_resp = httpx.get(
            f"{GITHUB_API}/repos/{username}/{repo['name']}/languages", timeout=10)
        if lang_resp.status_code != 200:
            continue
        for language in lang_resp.json():
            result.setdefault(language, []).append({
                "repo_name": repo["name"],
                "last_pushed_at": repo["pushed_at"],
            })
    return result


def map_languages_to_evidence(languages: dict[str, list[dict]],
                              confidence_floor: float = EVIDENCE_CONFIDENCE_FLOOR) -> list[dict]:
    """GitHub language name -> taxonomy skill via match_mention, dropping
    matches below confidence_floor. Returns evidence rows with
    last_pushed_at still as the raw ISO string from GitHub (caller converts
    to a datetime for storage)."""
    evidence_rows = []
    for language, repos in languages.items():
        hit = match_mention(language)
        if not hit or hit[1] < confidence_floor:
            continue
        skill_id = hit[0]
        for repo in repos:
            evidence_rows.append({
                "skill_id": skill_id, "repo_name": repo["repo_name"],
                "repo_language": language, "last_pushed_at": repo["last_pushed_at"],
            })
    return evidence_rows


def download_and_extract_repo(username: str, repo_name: str) -> list[dict]:
    """Downloads a public repo zipball and extracts text files.
    Returns [{"path": "...", "content": "..."}, ...]
    """
    url = f"{GITHUB_API}/repos/{username}/{repo_name}/zipball"
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    if resp.status_code == 404:
        raise GithubUserNotFound(f"Repo {username}/{repo_name} not found")
    if resp.status_code in (403, 429):
        raise GithubRateLimited("GitHub API rate limit hit; try again later")
    resp.raise_for_status()

    files = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
                
            # Zipball adds a root dir like owner-repo-sha
            path_parts = info.filename.split('/', 1)
            path = path_parts[1] if len(path_parts) > 1 else info.filename

            ignore_dirs = ['node_modules/', '.git/', '__pycache__/', 'venv/', '.venv/', 'dist/', 'build/', 'package-lock.json']
            if any(path.startswith(d) or f"/{d}" in path for d in ignore_dirs):
                continue

            ignore_exts = ['.jpg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.mp4', '.pyc', '.ico', '.svg', '.lock']
            if any(path.endswith(ext) for ext in ignore_exts):
                continue

            try:
                content = z.read(info.filename).decode('utf-8')
                if len(content) > 100_000:
                    continue
                files.append({"path": path, "content": content})
            except UnicodeDecodeError:
                continue

    return files
