"""Quiz agent: prompts the LLM, validates and returns well-formed MCQs."""
from unittest.mock import MagicMock, patch

from app.agents.quiz_agent import generate_quiz


def _mock_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


def test_generate_quiz_returns_validated_questions():
    fake_json = """[
      {"question": "What hook manages state in a function component?",
       "options": ["useEffect", "useState", "useRef", "useMemo"], "correct_index": 1},
      {"question": "What does JSX compile to?",
       "options": ["HTML", "React.createElement calls", "CSS", "JSON"], "correct_index": 1}
    ]"""
    with patch("app.agents.quiz_agent.get_llm") as mock_get_llm, \
         patch("app.agents.quiz_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        questions = generate_quiz("React", "Build components with hooks")

    assert len(questions) == 2
    assert questions[0]["options"][questions[0]["correct_index"]] == "useState"


def test_generate_quiz_drops_malformed_questions():
    fake_json = """[
      {"question": "Valid one", "options": ["a", "b", "c", "d"], "correct_index": 0},
      {"question": "Missing options", "options": ["a", "b"], "correct_index": 0},
      {"question": "Bad index", "options": ["a", "b", "c", "d"], "correct_index": 9}
    ]"""
    with patch("app.agents.quiz_agent.get_llm") as mock_get_llm, \
         patch("app.agents.quiz_agent.invoke_llm") as mock_invoke:
        mock_invoke.return_value = _mock_llm_response(fake_json)
        questions = generate_quiz("React", "Build components with hooks")

    assert len(questions) == 1
    assert questions[0]["question"] == "Valid one"
