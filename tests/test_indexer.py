import sqlite3
import pytest
from indexer import init_db, insert_conversations
from parsers.base import Conversation, Message


def test_init_db_creates_tables():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "conversations" in tables
    assert "messages" in tables
    conn.close()


def test_init_db_creates_fts_table():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "conversations_fts" in tables
    conn.close()


def test_insert_conversations_stores_rows(sample_conversations):
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    insert_conversations(conn, sample_conversations)
    count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    assert count == 2
    conn.close()


def test_insert_messages_stores_rows(sample_conversations):
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    insert_conversations(conn, sample_conversations)
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    assert count == 3
    conn.close()


def test_full_text_is_concatenated(sample_conversations):
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    insert_conversations(conn, sample_conversations)
    row = conn.execute("SELECT full_text FROM conversations WHERE uuid='conv-1'").fetchone()
    assert "GTM plan" in row[0]
    assert "HyperLiquid" in row[0]
    conn.close()


def test_fts_search_finds_match(sample_conversations):
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    insert_conversations(conn, sample_conversations)
    rows = conn.execute(
        "SELECT c.uuid FROM conversations c JOIN conversations_fts fts ON c.rowid = fts.rowid WHERE conversations_fts MATCH ?",
        ("HyperLiquid",),
    ).fetchall()
    assert any(r[0] == "conv-1" for r in rows)
    conn.close()
