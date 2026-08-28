"""Job matcher: deterministic overlap scoring, blended with semantic
similarity from the local embedding model. Uses a fake in-memory
JobProvider — no real network calls, no Adzuna credentials needed."""
from unittest.mock import patch

from app.agents import job_matcher
from app.db import crud, database, models
from app.providers import get_job_provider


def _db():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    Session = database.sessionmaker(bind=engine)
    return Session()


def _make_user_with_journey(db):
    user = models.User(email="t@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(models.CompetencyHistory(user_id=user.id, skill_id="python", depth_score=8,
                                    quiz_score=None, confidence_rating=None,
                                    has_github_evidence=False, rationale="resume"))
    db.commit()

    journey = crud.create_learning_journey(db, user.id, "Backend Engineer",
                                           gap_report_json="{}", hours_per_week=10)
    step = models.PathStep(journey_id=journey.id, order=1, skill_id="docker",
                           skill_name="Docker", objective="obj", milestone="ms",
                           estimated_weeks=2.0, status="in_progress")
    db.add(step)
    db.commit()
    db.refresh(journey)
    return user, journey


class _FakeProvider:
    def __init__(self, postings):
        self._postings = postings

    def fetch(self, role, limit=50):
        return self._postings

    def available_roles(self):
        return ["Backend Engineer"]


def test_recommend_jobs_ranks_by_overlap_and_returns_matched_skill_names():
    db = _db()
    user, journey = _make_user_with_journey(db)

    postings = [
        {"id": "job-a", "role": "Backend Engineer", "title": "Backend Engineer",
         "company": "Acme", "location": "Remote", "url": "https://example.com/a",
         "description": "irrelevant",
         "skills": [{"skill_id": "python", "level": "advanced"},
                    {"skill_id": "docker", "level": "intermediate"}]},
        {"id": "job-b", "role": "Backend Engineer", "title": "Backend Engineer",
         "company": "Beta", "location": "Remote", "url": "",
         "description": "irrelevant",
         "skills": [{"skill_id": "rust", "level": "advanced"}]},
    ]

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider(postings)):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    # job-a: python (weight 0.8, resume depth) + docker (weight 0.4, in-progress) -> overlap 0.6
    # job-b: rust (weight 0, no signal) -> overlap 0.0
    # Overlap alone (weighted 0.7) already separates them regardless of the
    # semantic component's actual value, so this assertion is robust.
    assert [r.posting_id for r in results] == ["job-a", "job-b"]
    assert set(results[0].matched_skills) == {"Python", "Docker & Containers"}
    assert results[0].score > results[1].score


def test_recommend_jobs_returns_empty_list_when_provider_has_no_postings():
    db = _db()
    user, journey = _make_user_with_journey(db)

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider([])):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    assert results == []


def test_recommend_jobs_handles_a_user_with_no_competency_history_yet():
    # A brand-new journey with no CompetencyHistory rows at all (e.g. the
    # /advise call that created it hasn't written history yet) must not
    # crash — everyone just scores 0 on overlap.
    db = _db()
    user = models.User(email="new@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    journey = crud.create_learning_journey(db, user.id, "Backend Engineer",
                                           gap_report_json="{}", hours_per_week=10)

    postings = [{"id": "job-a", "role": "Backend Engineer", "title": "Backend Engineer",
                "company": "Acme", "location": "Remote", "url": "",
                "description": "irrelevant", "skills": [{"skill_id": "python", "level": "advanced"}]}]

    with patch("app.agents.job_matcher.get_job_provider", return_value=_FakeProvider(postings)):
        results = job_matcher.recommend_jobs(db, user.id, journey)

    assert len(results) == 1
    assert results[0].matched_skills == []


def test_get_job_provider_returns_jobspy_provider_when_configured():
    with patch("app.providers.get_settings") as mock_settings:
        mock_settings.return_value.job_provider = "jobspy"
        provider = get_job_provider()

    from app.providers.jobspy_provider import JobSpyProvider
    assert isinstance(provider, JobSpyProvider)
