import sqlite3
import pytest
from parsers.base import Conversation, Message


@pytest.fixture
def sample_conversations():
    return [
        Conversation(
            uuid="conv-1",
            name="Tradeium strategy discussion",
            summary="Discussed GTM strategy",
            created_at="2026-03-10T13:18:10Z",
            messages=[
                Message(uuid="m1", sender="human", text="What is the GTM plan?", created_at="2026-03-10T13:18:11Z"),
                Message(uuid="m2", sender="assistant", text="The GTM focuses on HyperLiquid launch.", created_at="2026-03-10T13:18:15Z"),
            ],
        ),
        Conversation(
            uuid="conv-2",
            name="Sablier onboarding",
            summary="",
            created_at="2026-02-01T10:00:00Z",
            messages=[
                Message(uuid="m3", sender="human", text="How do we onboard protocols?", created_at="2026-02-01T10:00:01Z"),
            ],
        ),
    ]


@pytest.fixture
def mem_db(sample_conversations):
    """In-memory SQLite DB pre-populated with sample data."""
    from indexer import init_db, insert_conversations
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    insert_conversations(conn, sample_conversations)
    yield conn
    conn.close()
