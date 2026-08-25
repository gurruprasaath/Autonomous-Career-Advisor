"""OpenRouter LLM access + robust JSON extraction from model output."""
import json
import logging
import re
import time
from functools import lru_cache

from ..config import get_settings

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Raised when an agent needs the LLM but it can't be reached."""


@lru_cache
def get_llm(model: str | None = None, temperature: float = 0.2):
    s = get_settings()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model or s.planner_model,
        temperature=temperature,
        api_key="ollama",  # unused by Ollama, but required by the client
        base_url=s.llm_base_url,
        max_retries=2,
        max_tokens=8000,
    )


def invoke_llm(llm, prompt: str, retries: int = 2, delay: float = 3.0):
    """llm.invoke() with retry on transient errors (e.g. Ollama still loading
    the model into VRAM on the first call)."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            if attempt == retries:
                raise
            last_error = e
            log.warning("LLM call failed, retrying (%d/%d): %s", attempt + 1, retries, e)
            time.sleep(delay)
    raise last_error  # pragma: no cover — loop always returns or raises above


def extract_json(text: str) -> dict | list:
    """Pull the first JSON object/array out of an LLM response.

    Handles bare JSON, ```json fences, and leading/trailing prose.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # first balanced {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"No parseable JSON in LLM output: {text[:200]!r}")
