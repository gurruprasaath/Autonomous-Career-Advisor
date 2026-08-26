"""Application configuration, loaded from environment / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"
CHROMA_DIR = BACKEND_DIR / ".chroma"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    job_provider: str = "sample"  # "sample" | "adzuna"

    # Local Ollama (OpenAI-compatible API at localhost:11434/v1) — no API key,
    # no rate limits, no cloud latency. Switched from OpenRouter after its free
    # tier hit its 50-requests/day cap. Qwen2.5 7B fits an 8GB-VRAM GPU and is
    # strong at structured JSON output.
    llm_base_url: str = "http://localhost:11434/v1"
    planner_model: str = "qwen2.5:7b-instruct"
    fast_model: str = "qwen2.5:7b-instruct"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"
    youtube_api_key: str = ""

    max_revision_loops: int = 2
    verifier_pass_threshold: float = 3.5  # mean FGCR score out of 5

    @property
    def llm_available(self) -> bool:
        return True  # local Ollama server, always available once running


@lru_cache
def get_settings() -> Settings:
    return Settings()
