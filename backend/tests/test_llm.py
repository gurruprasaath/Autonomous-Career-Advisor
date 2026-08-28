"""Groq-first, Ollama-fallback LLM dispatch.

Every agent in this codebase calls get_llm()/invoke_llm() the same way, so
the multi-provider + key-rotation logic lives entirely in invoke_llm() —
no agent file needs to change. A rate-limit or auth error on one Groq key
moves to the next configured key; once all are exhausted (or none are
configured), it falls back to the local Ollama client passed in, exactly
as invoke_llm already behaved before Groq existed.
"""
from unittest.mock import MagicMock, patch

import httpx
from openai import APIStatusError, AuthenticationError, RateLimitError

from app.core.llm import invoke_llm


def _fake_response(status_code):
    return httpx.Response(status_code, request=httpx.Request("POST", "https://api.groq.com"))


def _rate_limit_error():
    return RateLimitError("rate limited", response=_fake_response(429), body=None)


def _auth_error():
    return AuthenticationError("invalid key", response=_fake_response(401), body=None)


def _request_too_large_error():
    # Reproduced directly against the real Groq API: an over-budget
    # max_tokens request comes back as HTTP 413, which openai-python maps
    # to the generic APIStatusError (not RateLimitError) — but the body
    # still carries code="rate_limit_exceeded", which is what actually
    # identifies it as a quota problem worth trying the next key for.
    return APIStatusError("request too large", response=_fake_response(413),
                          body={"code": "rate_limit_exceeded"})


def test_uses_groq_when_configured_and_available():
    ollama_llm = MagicMock()
    with patch("app.core.llm.get_settings") as mock_settings, \
         patch("app.core.llm.ChatOpenAI") as mock_chat_openai:
        mock_settings.return_value.groq_api_keys = "key-a"
        mock_settings.return_value.groq_model = "openai/gpt-oss-120b"
        mock_groq_llm = MagicMock()
        mock_groq_llm.invoke.return_value = "groq response"
        mock_chat_openai.return_value = mock_groq_llm

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "groq response"
    ollama_llm.invoke.assert_not_called()


def test_rotates_to_next_groq_key_on_rate_limit():
    ollama_llm = MagicMock()
    with patch("app.core.llm.get_settings") as mock_settings, \
         patch("app.core.llm.ChatOpenAI") as mock_chat_openai:
        mock_settings.return_value.groq_api_keys = "key-a,key-b"
        mock_settings.return_value.groq_model = "openai/gpt-oss-120b"
        exhausted_llm = MagicMock()
        exhausted_llm.invoke.side_effect = _rate_limit_error()
        working_llm = MagicMock()
        working_llm.invoke.return_value = "response from key-b"
        mock_chat_openai.side_effect = [exhausted_llm, working_llm]

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "response from key-b"
    ollama_llm.invoke.assert_not_called()


def test_falls_back_to_ollama_when_all_groq_keys_exhausted():
    ollama_llm = MagicMock()
    ollama_llm.invoke.return_value = "ollama response"
    with patch("app.core.llm.get_settings") as mock_settings, \
         patch("app.core.llm.ChatOpenAI") as mock_chat_openai:
        mock_settings.return_value.groq_api_keys = "key-a,key-b"
        mock_settings.return_value.groq_model = "openai/gpt-oss-120b"
        dead_llm = MagicMock()
        dead_llm.invoke.side_effect = _auth_error()
        mock_chat_openai.return_value = dead_llm

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "ollama response"
    assert mock_chat_openai.call_count == 2  # tried both keys before falling back


def test_falls_back_to_ollama_when_no_groq_keys_configured():
    ollama_llm = MagicMock()
    ollama_llm.invoke.return_value = "ollama response"
    with patch("app.core.llm.get_settings") as mock_settings:
        mock_settings.return_value.groq_api_keys = ""

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "ollama response"


def test_non_rate_limit_groq_error_stops_trying_more_keys():
    # A real, non-auth/rate-limit error (e.g. a 500) on one key means
    # something else is wrong with Groq generally — burning through every
    # other key for the same failure wastes time. Falls straight to Ollama.
    ollama_llm = MagicMock()
    ollama_llm.invoke.return_value = "ollama response"
    with patch("app.core.llm.get_settings") as mock_settings, \
         patch("app.core.llm.ChatOpenAI") as mock_chat_openai:
        mock_settings.return_value.groq_api_keys = "key-a,key-b"
        mock_settings.return_value.groq_model = "openai/gpt-oss-120b"
        broken_llm = MagicMock()
        broken_llm.invoke.side_effect = RuntimeError("connection reset")
        mock_chat_openai.return_value = broken_llm

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "ollama response"
    assert mock_chat_openai.call_count == 1  # did not try key-b


def test_rotates_to_next_key_on_request_too_large_rate_limit_error():
    # The exact real failure mode reproduced against the live Groq API:
    # HTTP 413 body-flagged as code="rate_limit_exceeded" must be treated
    # the same as a plain 429 RateLimitError, not as "Groq is broken."
    ollama_llm = MagicMock()
    with patch("app.core.llm.get_settings") as mock_settings, \
         patch("app.core.llm.ChatOpenAI") as mock_chat_openai:
        mock_settings.return_value.groq_api_keys = "key-a,key-b"
        mock_settings.return_value.groq_model = "openai/gpt-oss-120b"
        exhausted_llm = MagicMock()
        exhausted_llm.invoke.side_effect = _request_too_large_error()
        working_llm = MagicMock()
        working_llm.invoke.return_value = "response from key-b"
        mock_chat_openai.side_effect = [exhausted_llm, working_llm]

        result = invoke_llm(ollama_llm, "prompt")

    assert result == "response from key-b"
    ollama_llm.invoke.assert_not_called()
