"""GitHub public-repo language fetch — unauthenticated public API only.

No OAuth: the student types their GitHub username, we read what's already
public. Good enough to answer "have they actually written code in this
language recently," which is the only claim this evidence makes.
"""
import httpx

GITHUB_API = "https://api.github.com"


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

    result: dict[str, list[dict]] = {}
    for repo in repos_resp.json():
        if repo.get("fork"):
            continue
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
