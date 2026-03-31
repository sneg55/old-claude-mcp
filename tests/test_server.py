import sqlite3
import pytest
from server import search_history, get_conversation, list_conversations


@pytest.fixture
def db(mem_db):
    """Re-use the mem_db fixture from conftest; pass connection to server functions."""
    return mem_db


def test_search_history_finds_match(db):
    results = search_history(db, "HyperLiquid")
    assert len(results) >= 1
    assert results[0]["uuid"] == "conv-1"
    assert "snippet" in results[0]
    assert "rank" in results[0]


def test_search_history_returns_limit(db):
    results = search_history(db, "the", limit=1)
    assert len(results) <= 1


def test_search_history_no_match(db):
    results = search_history(db, "xyznotfoundever")
    assert results == []


def test_search_history_snippet_contains_term(db):
    results = search_history(db, "GTM")
    assert any("GTM" in r["snippet"] for r in results)
