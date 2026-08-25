import os
import requests
import logging
from ..schemas import PathResource

log = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

def search_youtube_videos(query: str, max_results: int = 3) -> list[PathResource]:
    if not YOUTUBE_API_KEY:
        log.warning("No YOUTUBE_API_KEY found, falling back to mock videos.")
        return [
            PathResource(
                course_id=f"yt-mock-{i}",
                title=f"Sample Video for {query}",
                provider="YouTube (Fallback)",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                free=True
            ) for i in range(max_results)
        ]

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{query} tutorial crash course",
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        resources = []
        for item in data.get("items", []):
            resources.append(PathResource(
                course_id=item["id"]["videoId"],
                title=item["snippet"]["title"],
                provider=item["snippet"]["channelTitle"],
                url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                free=True
            ))
        return resources
    except Exception as e:
        log.error("Failed to fetch from YouTube API: %s", e)
        return []
