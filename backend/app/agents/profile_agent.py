"""Student Profile Agent.

LLM pass: extract skill mentions + self-assessed levels from free text.
Deterministic pass: map every mention onto the taxonomy via alias/embedding
matching, so downstream computation only ever sees taxonomy node ids.

Degrades gracefully without an API key: falls back to scanning the text
for known skill names/aliases (level defaults to "beginner").
"""
import logging
import re

from ..config import get_settings
from ..core.llm import LLMUnavailable, extract_json, get_llm, invoke_llm
from ..core.taxonomy import load_taxonomy, match_mention
from ..schemas import MASTERY_SCORE, StudentProfile, StudentSkill

log = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a career profiling assistant. Extract technical and professional skills from the student's text below.

Return ONLY a JSON array. Each element:
{{"mention": "<one single skill or technology name, e.g. \\"React\\" or \\"Python\\">",
  "level": "beginner" | "intermediate" | "advanced",
  "depth_score": <int 1-10>,
  "evidence": "<short quote from the text supporting this>"}}

Rules:
- One skill per element. If a sentence lists several technologies (e.g. "built an app with React, Node.js and MongoDB"), emit a SEPARATE element for each one ("React", "Node.js", "MongoDB") — never combine them into one mention or copy a whole clause/sentence as the mention.
- Extract only skills the student actually claims, not aspirations ("I want to learn X" is NOT a skill).
- Infer level conservatively from context: coursework/tutorials = beginner; projects = intermediate; internships/production work or multiple substantial projects = advanced.
- Include soft/professional skills only when clearly evidenced.

Example:
Text: "Built a chat app with React and Node.js during an internship."
Output: [{{"mention": "React", "level": "advanced", "depth_score": 7, "evidence": "Built a chat app with React ... during an internship"}}, {{"mention": "Node.js", "level": "advanced", "depth_score": 7, "evidence": "Built a chat app with ... Node.js during an internship"}}]

Student text:
\"\"\"{text}\"\"\"
"""


def _extract_with_llm(text: str) -> list[dict]:
    # Plain prompted JSON, not with_structured_output: Groq's gpt-oss models
    # intermittently 400 on forced tool-choice ("did not call a tool"), while
    # every other agent in this codebase uses this same prompt+extract_json
    # pattern reliably.
    llm = get_llm(get_settings().fast_model)
    response = invoke_llm(llm, EXTRACT_PROMPT.format(text=text))
    data = extract_json(response.content)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    return data if isinstance(data, list) else []


# terms too ambiguous to scan for in free-flowing text ("go far", "James R.")
SCAN_STOPLIST = {"go", "r"}


def _extract_deterministic(text: str) -> list[dict]:
    """No-LLM fallback: scan text for taxonomy names/aliases as whole words."""
    lower = text.lower()
    found = []
    for node in load_taxonomy().values():
        terms = {node.name.lower(), node.id.lower(), *[a.lower() for a in node.aliases]}
        for term in terms - SCAN_STOPLIST:
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
                found.append({"mention": node.name, "level": "beginner", "depth_score": 1,
                              "evidence": f"mentioned '{term}'"})
                break
    return found


def build_profile(resume_text: str, target_role: str,
                  hours_per_week: int = 10, education: str = "") -> tuple[StudentProfile, list[str]]:
    """Returns (profile, notes). Notes surface degradations to the UI."""
    notes: list[str] = []
    try:
        raw_skills = _extract_with_llm(resume_text)
    except LLMUnavailable as e:
        notes.append(f"Profile agent ran WITHOUT the LLM (keyword scan only): {e}")
        raw_skills = _extract_deterministic(resume_text)
    except Exception as e:  # LLM up but response unusable — degrade, don't fail
        log.warning("profile LLM extraction failed: %s", e)
        notes.append(f"LLM extraction failed ({type(e).__name__}); used keyword scan fallback.")
        raw_skills = _extract_deterministic(resume_text)

    skills: dict[str, StudentSkill] = {}
    unmatched: list[str] = []
    for item in raw_skills:
        mention = str(item.get("mention", "")).strip()
        level = item.get("level", "beginner")
        if level not in MASTERY_SCORE or level == "none":
            level = "beginner"
        hit = match_mention(mention)
        if not hit:
            unmatched.append(mention)
            continue
        sid = hit[0]
        node_name = load_taxonomy()[sid].name
        existing = skills.get(sid)
        # keep the highest claimed level per taxonomy node
        if not existing or MASTERY_SCORE[level] > MASTERY_SCORE[existing.level]:
            skills[sid] = StudentSkill(
                skill_id=sid, name=node_name, level=level,
                depth_score=int(item.get("depth_score", 1)),
                evidence=str(item.get("evidence", ""))[:200],
            )
    if unmatched:
        notes.append("Mentions outside the taxonomy (ignored): " + ", ".join(unmatched[:8]))

    profile = StudentProfile(
        raw_text=resume_text, skills=list(skills.values()),
        education=education, hours_per_week=hours_per_week, target_role=target_role,
    )
    return profile, notes
