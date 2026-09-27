"""No two taxonomy skills may claim the same name/id/alias — the alias index
would silently map it to whichever skill loaded last."""
from collections import Counter

from app.core.taxonomy import load_taxonomy


def test_names_ids_and_aliases_are_unique_across_skills():
    owners = Counter()
    for node in load_taxonomy().values():
        keys = {node.id.lower(), node.name.lower(), *(a.lower() for a in node.aliases)}
        owners.update(keys)
    duplicates = sorted(k for k, n in owners.items() if n > 1)
    assert duplicates == []
