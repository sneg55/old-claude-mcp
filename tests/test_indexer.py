import sqlite3
import pytest
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path
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


def test_cli_indexes_file(sample_conversations, tmp_path):
    # Write a minimal Claude export fixture
    fixture = [
        {
            "uuid": "conv-cli-1",
            "name": "CLI test conversation",
            "summary": "",
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:00:00Z",
            "account": {"uuid": "acc-1"},
            "chat_messages": [
                {
                    "uuid": "msg-cli-1",
                    "text": "Testing the CLI indexer",
                    "sender": "human",
                    "created_at": "2026-03-01T00:00:01Z",
                    "updated_at": "2026-03-01T00:00:01Z",
                    "attachments": [],
                    "files": [],
                }
            ],
        }
    ]
    export_path = tmp_path / "conversations.json"
    export_path.write_text(json.dumps(fixture))
    db_path = tmp_path / "history.db"

    indexer_path = Path(__file__).parent.parent / "indexer.py"
    result = subprocess.run(
        [sys.executable, str(indexer_path), str(export_path), "--db", str(db_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    conn.close()
    assert count == 1
