from ..config import get_settings
from .base import JobProvider


def get_job_provider() -> JobProvider:
    provider = get_settings().job_provider.lower()
    if provider == "adzuna":
        from .adzuna import AdzunaJobProvider
        return AdzunaJobProvider()
    if provider == "jobspy":
        from .jobspy_provider import JobSpyProvider
        return JobSpyProvider()
    from .sample import SampleJobProvider
    return SampleJobProvider()
