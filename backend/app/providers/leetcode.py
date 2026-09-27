"""LeetCode public-profile stats — unauthenticated, undocumented GraphQL.

No login: the student types their LeetCode username, we read what their
public profile page already shows. The endpoint is the one leetcode.com's own
profile page calls; it's undocumented and may change, so every failure other
than "no such user" is reported as LeetcodeUnavailable and never breaks any
other feature.

Only the raw snapshot is stored; dsa_depth/weak_topics are always recomputed
from it, so every number shown to a learner is reproducible from stored data.
"""
import math
from datetime import datetime, timezone

import httpx

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

# The taxonomy's single DSA node — LeetCode evidence applies to this skill only.
DSA_SKILL_ID = "problem-solving"

# Core interview topics, using LeetCode's exact tag names (verified live).
# Order is the tie-break for weak_topics.
CORE_TOPICS = [
    "Array", "String", "Hash Table", "Two Pointers", "Sliding Window",
    "Binary Search", "Stack", "Linked List", "Tree", "Graph Theory", "Heap",
    "Dynamic Programming", "Greedy", "Backtracking",
]
WEAK_TOPIC_THRESHOLD = 5

_QUERY = """query($u: String!) {
  matchedUser(username: $u) {
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    tagProblemCounts {
      advanced { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      fundamental { tagName problemsSolved }
    }
  }
  recentAcSubmissionList(username: $u, limit: 1) { timestamp }
}"""


class LeetcodeUserNotFound(RuntimeError):
    pass


class LeetcodeUnavailable(RuntimeError):
    pass


def fetch_profile(username: str) -> dict:
    try:
        resp = httpx.post(LEETCODE_GRAPHQL,
                          json={"query": _QUERY, "variables": {"u": username}},
                          headers={"Referer": "https://leetcode.com"}, timeout=10)
    except httpx.HTTPError as e:
        raise LeetcodeUnavailable(f"network error: {e}") from e
    if resp.status_code != 200:
        raise LeetcodeUnavailable(f"HTTP {resp.status_code}")

    try:
        data = resp.json()["data"]
        user = data["matchedUser"]
    except (ValueError, KeyError, TypeError) as e:
        raise LeetcodeUnavailable("unexpected response shape") from e
    if user is None:
        raise LeetcodeUserNotFound(username)

    try:
        counts = {row["difficulty"]: row["count"]
                  for row in user["submitStatsGlobal"]["acSubmissionNum"]}
        topics: dict[str, int] = {}
        for tier in ("advanced", "intermediate", "fundamental"):
            for row in user["tagProblemCounts"][tier] or []:
                topics[row["tagName"]] = row["problemsSolved"]
        recent = data.get("recentAcSubmissionList") or []
        last_accepted_at = (
            datetime.fromtimestamp(int(recent[0]["timestamp"]), tz=timezone.utc).isoformat()
            if recent else None)
    except (KeyError, TypeError, ValueError) as e:
        raise LeetcodeUnavailable("unexpected response shape") from e

    return {"easy": counts.get("Easy", 0), "medium": counts.get("Medium", 0),
            "hard": counts.get("Hard", 0), "topics": topics,
            "last_accepted_at": last_accepted_at}


def dsa_depth(snapshot: dict) -> int | None:
    """Log-scaled so each extra solve matters less; medium/hard weighted 2x/3x.
    Zero solves is absence of evidence, not depth 1 — returns None."""
    easy, medium, hard = snapshot["easy"], snapshot["medium"], snapshot["hard"]
    if easy + medium + hard == 0:
        return None
    weighted = easy + 2 * medium + 3 * hard
    return max(1, min(10, round(2 * math.log2(1 + weighted / 15))))


def weak_topics(snapshot: dict, limit: int = 3) -> list[str]:
    topics = snapshot.get("topics", {})
    weak = [t for t in CORE_TOPICS if topics.get(t, 0) < WEAK_TOPIC_THRESHOLD]
    # sorted() is stable, so equal counts keep CORE_TOPICS order.
    weak.sort(key=lambda t: topics.get(t, 0))
    return weak[:limit]


def summarize(username: str, snapshot: dict) -> dict:
    return {
        "username": username,
        "easy": snapshot["easy"], "medium": snapshot["medium"], "hard": snapshot["hard"],
        "total": snapshot["easy"] + snapshot["medium"] + snapshot["hard"],
        "dsa_depth": dsa_depth(snapshot),
        "weak_topics": weak_topics(snapshot),
        "last_accepted_at": snapshot.get("last_accepted_at"),
        "synced_at": snapshot.get("synced_at"),
    }


def depth_for_skill(skill_id: str, snapshot: dict | None) -> int | None:
    if snapshot is None or skill_id != DSA_SKILL_ID:
        return None
    return dsa_depth(snapshot)
