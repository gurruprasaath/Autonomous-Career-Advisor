"""Analyzed-repo memory: upsert on re-analyze, not duplicate rows."""
from app.db import crud, database, models


def _db():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    Session = database.sessionmaker(bind=engine)
    return Session()


def _make_user(db, email="t@example.com"):
    user = models.User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_upsert_inserts_new_repo():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=12)

    repos = crud.get_analyzed_repos(db, user.id)
    assert len(repos) == 1
    assert repos[0].username == "octocat"
    assert repos[0].repo_name == "Hello-World"
    assert repos[0].file_count == 12


def test_upsert_updates_existing_repo_instead_of_duplicating():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=12)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=20)

    repos = crud.get_analyzed_repos(db, user.id)
    assert len(repos) == 1
    assert repos[0].file_count == 20


def test_get_analyzed_repos_scoped_to_user():
    db = _db()
    user_a = _make_user(db, "a@example.com")
    user_b = _make_user(db, "b@example.com")

    crud.upsert_analyzed_repo(db, user_a.id, "octocat", "Hello-World", file_count=1)
    crud.upsert_analyzed_repo(db, user_b.id, "torvalds", "linux", file_count=1)

    assert [r.repo_name for r in crud.get_analyzed_repos(db, user_a.id)] == ["Hello-World"]
    assert [r.repo_name for r in crud.get_analyzed_repos(db, user_b.id)] == ["linux"]


def test_get_analyzed_repos_orders_most_recent_first():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "first-repo", file_count=1)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "second-repo", file_count=1)

    repos = crud.get_analyzed_repos(db, user.id)
    assert [r.repo_name for r in repos] == ["second-repo", "first-repo"]
