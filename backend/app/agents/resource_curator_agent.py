import logging
import json
from ..config import get_settings
from ..core.llm import get_llm, invoke_llm, extract_json, LLMUnavailable
from ..core.vectorstore import courses_collection
from ..providers.youtube import search_youtube_videos
from ..schemas import PathResource

log = logging.getLogger(__name__)

CURATOR_PROMPT = """You are a Resource Curator for a learning app.
You need to pick the best {k} resources for a student studying "{skill_name}".
The student's depth score is {depth_score}/10.
The objective of this step is: "{objective}"

Here are the retrieved candidate resources (each has a unique candidate_id):
{candidates_block}

Pick exactly {k} resources from the list above that best fit the objective and depth score.
You MUST NOT invent resources. You must ONLY use candidate_ids from the list above.
For each pick, write a one-line "justification" (e.g. "Best fits the objective due to focus on X").

Return ONLY JSON:
{{"picks": [
  {{"candidate_id": "...", "justification": "..."}}
]}}
"""

def curate_resources(skill_id: str, skill_name: str, depth_score: int, objective: str, k: int = 2) -> list[PathResource]:
    if depth_score < 4:
        level = "beginner"
    elif depth_score < 8:
        level = "intermediate"
    else:
        level = "advanced"
        
    # 1. Retrieve candidates
    candidates: dict[str, PathResource] = {}
    
    # YouTube candidates
    yt_resources = search_youtube_videos(f"{level} {skill_name}", max_results=5)
    for res in yt_resources:
        candidates[res.course_id] = res
        
    # Course catalog candidates
    hits = courses_collection().get(where={"skill_id": skill_id})
    if hits and hits["ids"]:
        for cid, meta in zip(hits["ids"][:5], hits["metadatas"][:5]):
            candidates[cid] = PathResource(
                course_id=cid, title=meta["title"], provider=meta["provider"],
                url=meta["url"], free=bool(meta.get("free", True))
            )

    if not candidates:
        return yt_resources[:k] if yt_resources else []

    candidate_list = list(candidates.values())
    if len(candidate_list) <= k:
        return candidate_list[:k]
        
    # 2. LLM Curation
    candidates_block = "\n".join(
        f"- candidate_id: {res.course_id} | title: {res.title} | provider: {res.provider}"
        for res in candidate_list
    )
    
    try:
        llm = get_llm(get_settings().planner_model)
        prompt = CURATOR_PROMPT.format(
            k=k, skill_name=skill_name, depth_score=depth_score,
            objective=objective, candidates_block=candidates_block
        )
        response = invoke_llm(llm, prompt)
        data = extract_json(response.content)
        
        picks = data.get("picks", [])
        final_resources = []
        for pick in picks:
            cid = pick.get("candidate_id")
            if cid in candidates:
                # We could attach justification, but PathResource currently doesn't have it.
                # Just return the selected resource.
                final_resources.append(candidates[cid])
                
        if final_resources:
            return final_resources[:k]
            
    except Exception as e:
        log.warning("Curator LLM failed or returned invalid data: %s", e)
        
    # Fallback to deterministic first-k if LLM fails or returns 0 valid
    return candidate_list[:k]
