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


def test_get_conversation_returns_messages(db):
    messages = get_conversation(db, "conv-1")
    assert len(messages) == 2
    assert messages[0]["sender"] == "human"
    assert messages[0]["text"] == "What is the GTM plan?"
    assert messages[1]["sender"] == "assistant"


def test_get_conversation_unknown_uuid(db):
    messages = get_conversation(db, "nonexistent-uuid")
    assert messages == []


def test_get_conversation_truncates_long_thread(db, monkeypatch):
    import indexer
    # Insert a conversation with a very long message
    conn = db
    from parsers.base import Conversation, Message
    long_conv = Conversation(
        uuid="conv-long",
        name="Long conversation",
        summary="",
        created_at="2026-01-01T00:00:00Z",
        messages=[
            Message(uuid=f"ml-{i}", sender="human", text="x" * 10_000, created_at=f"2026-01-01T00:00:{i:02d}Z")
            for i in range(10)
        ],
    )
    indexer.insert_conversations(conn, [long_conv])
    messages = get_conversation(conn, "conv-long")
    assert any(m["sender"] == "system" and "truncated" in m["text"] for m in messages)


def test_list_conversations_returns_all(db):
    results = list_conversations(db)
    assert len(results) == 2


def test_list_conversations_sorted_by_date(db):
    results = list_conversations(db)
    dates = [r["created_at"] for r in results]
    assert dates == sorted(dates, reverse=True)


def test_list_conversations_limit(db):
    results = list_conversations(db, limit=1)
    assert len(results) == 1


def test_list_conversations_after(db):
    # conv-1 is 2026-03-10, conv-2 is 2026-02-01
    # after 2026-03-10 should return only conv-2 (earlier)
    results = list_conversations(db, after="2026-03-10T13:18:10Z")
    assert len(results) == 1
    assert results[0]["uuid"] == "conv-2"


def test_list_conversations_includes_message_count(db):
    results = list_conversations(db)
    conv1 = next(r for r in results if r["uuid"] == "conv-1")
    assert conv1["message_count"] == 2
