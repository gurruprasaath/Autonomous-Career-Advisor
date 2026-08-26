"""Collection-naming + input-validation fix for GitHub repo chat (Critical
finding #3): collections must be scoped per-user and named collision-free,
and username/repo_name must be validated before reaching Chroma or an
outbound GitHub URL. No live Chroma instance needed for either check."""
import pytest
from fastapi import HTTPException

from app.core.vectorstore import _repo_collection_name
from app.main import _validate_github_ident


def test_lossy_old_scheme_collisions_now_produce_different_names():
    # Under the old f"repo_{username}_{repo_name}".replace("-", "_") scheme,
    # these two distinct (username, repo_name) pairs collided.
    name_a = _repo_collection_name(1, "alice", "foo-bar")
    name_b = _repo_collection_name(1, "alice-foo", "bar")
    assert name_a != name_b


def test_same_repo_different_users_are_scoped_separately():
    name_a = _repo_collection_name(1, "alice", "project")
    name_b = _repo_collection_name(2, "alice", "project")
    assert name_a != name_b


def test_same_user_and_repo_is_stable():
    assert _repo_collection_name(1, "alice", "project") == _repo_collection_name(1, "alice", "project")


@pytest.mark.parametrize("value", ["", "-leading-dash", "a" * 100, "has spaces", "semi;colon", "../etc"])
def test_invalid_identifiers_rejected(value):
    with pytest.raises(HTTPException) as exc_info:
        _validate_github_ident(value, "username")
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("value", ["alice", "my-repo.js", "user_123"])
def test_valid_identifiers_accepted(value):
    _validate_github_ident(value, "username")  # must not raise
