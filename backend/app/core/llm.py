"""LLM access + robust JSON extraction from model output.

Groq-first, Ollama-fallback: every agent calls get_llm()/invoke_llm() the
same way regardless of provider, so the multi-provider + key-rotation
logic lives entirely in invoke_llm() below — no agent file needs to know
about Groq at all.
"""
import json
import logging
import re
import time
from functools import lru_cache

from langchain_openai import ChatOpenAI
from openai import APIStatusError, AuthenticationError, RateLimitError

from ..config import get_settings

log = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq's on-demand free tier caps input+output combined at 8000 tokens per
# minute for this model (confirmed directly: a single call with
# max_tokens=8000 was rejected with HTTP 413 "Requested 8078" — the 8000
# output budget alone left no room for the prompt itself). 3000 leaves
# headroom for this app's longer prompts (e.g. the verifier's full path
# JSON) while still being enough for every agent's compact JSON responses.
GROQ_MAX_TOKENS = 3000


class LLMUnavailable(RuntimeError):
    """Raised when an agent needs the LLM but it can't be reached."""


@lru_cache
def get_llm(model: str | None = None, temperature: float = 0.2):
    s = get_settings()
    return ChatOpenAI(
        model=model or s.planner_model,
        temperature=temperature,
        api_key="ollama",  # unused by Ollama, but required by the client
        base_url=s.llm_base_url,
        max_retries=2,
        max_tokens=8000,
    )


def _groq_keys() -> list[str]:
    return [k.strip() for k in get_settings().groq_api_keys.split(",") if k.strip()]


def _is_rate_limit_flavored(e: Exception) -> bool:
    """RateLimitError is the normal case (HTTP 429). Groq's TPM cap can also
    surface as a generic APIStatusError (HTTP 413, "request too large")
    whose body still carries code="rate_limit_exceeded" — reproduced
    directly. Either way it's an account-specific quota problem worth
    trying the next key for, not evidence Groq itself is down."""
    if isinstance(e, RateLimitError):
        return True
    return isinstance(e, APIStatusError) and getattr(e, "code", None) == "rate_limit_exceeded"


def _invoke_groq(prompt: str):
    """Try each configured Groq key in turn. A rate-limit-flavored or
    invalid-key error on one key moves to the next; any other error stops
    immediately — that key works, so a different error means something
    else is wrong with Groq generally, and burning through the rest wastes
    time."""
    keys = _groq_keys()
    if not keys:
        raise LLMUnavailable("no Groq keys configured")

    last_error: Exception | None = None
    for key in keys:
        try:
            llm = ChatOpenAI(
                model=get_settings().groq_model, temperature=0.2,
                api_key=key, base_url=GROQ_BASE_URL, max_retries=0, max_tokens=GROQ_MAX_TOKENS,
            )
            return llm.invoke(prompt)
        except AuthenticationError as e:
            log.warning("Groq key ...%s invalid, trying next: %s", key[-4:], e)
            last_error = e
        except Exception as e:
            if _is_rate_limit_flavored(e):
                log.warning("Groq key ...%s rate-limited, trying next: %s", key[-4:], e)
                last_error = e
                continue
            # Not a per-key problem — something else is wrong with Groq
            # generally, so trying the remaining keys for the same failure
            # would just waste time.
            log.warning("Groq call failed (not rate-limit/auth): %s", e)
            raise LLMUnavailable(f"Groq call failed: {e}") from e
    raise LLMUnavailable(f"all {len(keys)} configured Groq keys are exhausted/invalid") from last_error


def invoke_llm(llm, prompt: str, retries: int = 2, delay: float = 3.0):
    """Tries Groq first (rotating through configured keys), falling back to
    the local Ollama client (`llm`) if Groq is unconfigured, exhausted, or
    a non-rate-limit error occurs — same graceful-degradation shape every
    agent already expects from this function, just with a faster primary
    path. The Ollama retry loop below is unchanged from before Groq existed
    (e.g. Ollama still loading the model into VRAM on the first call)."""
    if get_settings().groq_api_keys:
        try:
            return _invoke_groq(prompt)
        except LLMUnavailable as e:
            log.warning("Groq unavailable (%s); falling back to local Ollama", e)

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
