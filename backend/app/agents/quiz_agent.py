"""Quiz Agent — generates a short multiple-choice check for one path step.

Malformed questions (wrong option count, out-of-range correct_index) are
dropped rather than surfaced — a partially-broken quiz of 2-3 good
questions is more useful than failing the whole request over one bad item.
"""
import logging

from ..config import get_settings
from ..core.llm import extract_json, get_llm, invoke_llm

log = logging.getLogger(__name__)

QUIZ_PROMPT = """You are writing a short comprehension check for a student who just studied "{skill}".
Their learning objective was: "{objective}"

Write 3 multiple-choice questions that test whether they actually understood this
objective (not trivia). Each question has exactly 4 options and exactly one
correct answer.

Return ONLY JSON:
[{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": <0-3>}}]
"""


def generate_quiz(skill_name: str, objective: str) -> list[dict]:
    llm = get_llm(get_settings().fast_model)
    response = invoke_llm(llm, QUIZ_PROMPT.format(skill=skill_name, objective=objective))
    data = extract_json(response.content)
    if not isinstance(data, list):
        return []

    questions = []
    for item in data:
        options = item.get("options")
        correct_index = item.get("correct_index")
        if (isinstance(options, list) and len(options) == 4
                and isinstance(correct_index, int) and 0 <= correct_index < 4
                and item.get("question")):
            questions.append({
                "question": str(item["question"]),
                "options": [str(o) for o in options],
                "correct_index": correct_index,
            })
    return questions
