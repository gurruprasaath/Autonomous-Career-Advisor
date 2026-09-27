"""_rebuild must refresh on document/metadata changes, not just count drift."""
import chromadb

from app.core.vectorstore import _rebuild


def _collection():
    return chromadb.EphemeralClient().get_or_create_collection("test-rebuild")


def test_first_call_adds():
    col = _collection()
    _rebuild(col, ids=["a", "b"], documents=["doc a", "doc b"],
              metadatas=[{"k": 1}, {"k": 2}])
    assert col.count() == 2
    assert col.get(ids=["a"])["documents"] == ["doc a"]


def test_second_identical_call_is_a_noop():
    col = _collection()
    ids, docs, metas = ["a", "b"], ["doc a", "doc b"], [{"k": 1}, {"k": 2}]
    _rebuild(col, ids=ids, documents=docs, metadatas=metas)
    _rebuild(col, ids=ids, documents=docs, metadatas=metas)
    assert col.count() == 2
    assert col.get(ids=["a"])["documents"] == ["doc a"]


def test_changed_document_replaces_it():
    col = _collection()
    ids, metas = ["a", "b"], [{"k": 1}, {"k": 2}]
    _rebuild(col, ids=ids, documents=["doc a", "doc b"], metadatas=metas)
    _rebuild(col, ids=ids, documents=["doc a EDITED", "doc b"], metadatas=metas)
    assert col.count() == 2
    assert col.get(ids=["a"])["documents"] == ["doc a EDITED"]


def test_multikey_metadata_identical_call_is_a_noop():
    # Chroma returns metadata dicts with keys reordered (alphabetized) —
    # this must not be mistaken for a change on unchanged multi-key metadata.
    col = _collection()
    ids, docs = ["a", "b"], ["doc a", "doc b"]
    metas = [{"name": "A", "category": "x"}, {"name": "B", "category": "y"}]
    _rebuild(col, ids=ids, documents=docs, metadatas=metas)
    added = []
    col.add = lambda *a, **k: added.append(1)
    _rebuild(col, ids=ids, documents=docs, metadatas=metas)
    assert added == []
