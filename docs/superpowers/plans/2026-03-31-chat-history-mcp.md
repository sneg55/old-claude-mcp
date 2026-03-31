# Chat History MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local MCP server that indexes a Claude chat export into SQLite FTS5 and exposes three tools (`search_history`, `get_conversation`, `list_conversations`) Claude can call automatically.

**Architecture:** One-time indexer CLI parses `conversations.json` into a SQLite DB with FTS5 full-text search. A FastMCP server reads that DB and exposes three tools. Provider abstraction lives in `parsers/` — adding new providers means a new parser class only.

**Tech Stack:** Python 3.10+, SQLite (stdlib), `mcp` SDK (`pip install mcp`), pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | `mcp` and `pytest` dependencies |
| `schema.sql` | SQLite table definitions |
| `parsers/__init__.py` | Empty, makes parsers a package |
| `parsers/base.py` | `Message`, `Conversation` dataclasses + `ConversationParser` Protocol |
| `parsers/claude.py` | `ClaudeParser` — parses Claude `conversations.json` export |
| `indexer.py` | CLI: `init_db()`, `insert_conversations()`, `__main__` entry point |
| `server.py` | FastMCP server with three tools; reads DB path from `--db` arg |
| `tests/conftest.py` | Shared pytest fixtures (in-memory DB, sample conversations) |
| `tests/test_parsers.py` | Unit tests for `ClaudeParser` |
| `tests/test_indexer.py` | Unit tests for `init_db` and `insert_conversations` |
| `tests/test_server.py` | Unit tests for the three tool functions |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `schema.sql`
- Create: `parsers/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
mcp>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Create schema.sql**

```sql
CREATE TABLE IF NOT EXISTS conversations (
    uuid        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    summary     TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    full_text   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    uuid        TEXT PRIMARY KEY,
    conv_uuid   TEXT NOT NULL REFERENCES conversations(uuid),
    sender      TEXT NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
    name,
    summary,
    full_text,
    content='conversations',
    content_rowid='rowid'
);
```

- [ ] **Step 3: Create empty package files**

`parsers/__init__.py` — empty file.
`tests/__init__.py` — empty file.

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: mcp and pytest install without errors.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt schema.sql parsers/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

## Task 2: Base Parser Types

**Files:**
- Create: `parsers/base.py`
- Create: `tests/test_parsers.py` (partial — base types only)

- [ ] **Step 1: Write the failing test**

`tests/test_parsers.py`:
```python
from parsers.base import Message, Conversation, ConversationParser
from dataclasses import fields


def test_message_fields():
    msg = Message(uuid="m1", sender="human", text="hello", created_at="2025-01-01T00:00:00Z")
    assert msg.uuid == "m1"
    assert msg.sender == "human"
    assert msg.text == "hello"
    assert msg.created_at == "2025-01-01T00:00:00Z"


def test_conversation_fields():
    msg = Message(uuid="m1", sender="human", text="hello", created_at="2025-01-01T00:00:00Z")
    conv = Conversation(
        uuid="c1",
        name="Test Conv",
        summary="A summary",
        created_at="2025-01-01T00:00:00Z",
        messages=[msg],
    )
    assert conv.uuid == "c1"
    assert conv.name == "Test Conv"
    assert len(conv.messages) == 1


def test_parser_protocol_satisfied_by_callable():
    # Any object with a parse(filepath) -> list[Conversation] method satisfies the protocol
    class FakeParser:
        def parse(self, filepath: str) -> list[Conversation]:
            return []

    parser: ConversationParser = FakeParser()
    assert parser.parse("anything") == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_parsers.py -v
```

Expected: `ImportError: cannot import name 'Message' from 'parsers.base'`

- [ ] **Step 3: Implement parsers/base.py**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Message:
    uuid: str
    sender: str       # 'human' | 'assistant'
    text: str
    created_at: str


@dataclass
class Conversation:
    uuid: str
    name: str
    summary: str
    created_at: str
    messages: list[Message]


class ConversationParser(Protocol):
    def parse(self, filepath: str) -> list[Conversation]:
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_parsers.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add parsers/base.py tests/test_parsers.py
git commit -m "feat: add base parser types"
```

---

## Task 3: ClaudeParser

**Files:**
- Create: `parsers/claude.py`
- Modify: `tests/test_parsers.py` — add Claude parser tests

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parsers.py`:
```python
import json
import tempfile
import os
from parsers.claude import ClaudeParser


CLAUDE_FIXTURE = [
    {
        "uuid": "conv-1",
        "name": "Test Conversation",
        "summary": "A test",
        "created_at": "2025-12-07T12:39:33.684747Z",
        "updated_at": "2025-12-07T12:40:05.192396Z",
        "account": {"uuid": "acc-1"},
        "chat_messages": [
            {
                "uuid": "msg-1",
                "text": "Hello world",
                "sender": "human",
                "created_at": "2025-12-07T12:39:35.181793Z",
                "updated_at": "2025-12-07T12:39:35.181793Z",
                "attachments": [],
                "files": [],
            },
            {
                "uuid": "msg-2",
                "text": "Hi there",
                "sender": "assistant",
                "created_at": "2025-12-07T12:39:40.000000Z",
                "updated_at": "2025-12-07T12:39:40.000000Z",
                "attachments": [],
                "files": [],
            },
        ],
    }
]


def test_claude_parser_returns_conversations():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(CLAUDE_FIXTURE, f)
        path = f.name

    try:
        parser = ClaudeParser()
        convs = parser.parse(path)
        assert len(convs) == 1
        assert convs[0].uuid == "conv-1"
        assert convs[0].name == "Test Conversation"
        assert convs[0].summary == "A test"
    finally:
        os.unlink(path)


def test_claude_parser_messages():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(CLAUDE_FIXTURE, f)
        path = f.name

    try:
        parser = ClaudeParser()
        convs = parser.parse(path)
        msgs = convs[0].messages
        assert len(msgs) == 2
        assert msgs[0].uuid == "msg-1"
        assert msgs[0].sender == "human"
        assert msgs[0].text == "Hello world"
        assert msgs[1].sender == "assistant"
    finally:
        os.unlink(path)


def test_claude_parser_empty_text_skipped():
    fixture = [
        {
            "uuid": "conv-2",
            "name": "Empty messages",
            "summary": "",
            "created_at": "2025-12-07T12:00:00Z",
            "updated_at": "2025-12-07T12:00:00Z",
            "account": {"uuid": "acc-1"},
            "chat_messages": [
                {
                    "uuid": "msg-3",
                    "text": "",
                    "sender": "human",
                    "created_at": "2025-12-07T12:00:01Z",
                    "updated_at": "2025-12-07T12:00:01Z",
                    "attachments": [],
                    "files": [],
                }
            ],
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fixture, f)
        path = f.name

    try:
        parser = ClaudeParser()
        convs = parser.parse(path)
        assert convs[0].messages == []
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_parsers.py -v -k "claude"
```

Expected: `ImportError: cannot import name 'ClaudeParser' from 'parsers.claude'`

- [ ] **Step 3: Implement parsers/claude.py**

```python
from __future__ import annotations
import json
from parsers.base import Conversation, Message


class ClaudeParser:
    def parse(self, filepath: str) -> list[Conversation]:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        conversations = []
        for raw in data:
            messages = [
                Message(
                    uuid=msg["uuid"],
                    sender=msg["sender"],
                    text=msg.get("text", ""),
                    created_at=msg["created_at"],
                )
                for msg in raw.get("chat_messages", [])
                if msg.get("text", "").strip()
            ]
            conversations.append(
                Conversation(
                    uuid=raw["uuid"],
                    name=raw.get("name", ""),
                    summary=raw.get("summary", ""),
                    created_at=raw["created_at"],
                    messages=messages,
                )
            )
        return conversations
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_parsers.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add parsers/claude.py tests/test_parsers.py
git commit -m "feat: add ClaudeParser"
```

---

## Task 4: Database Init and Insertion

**Files:**
- Create: `indexer.py`
- Create: `tests/conftest.py`
- Create: `tests/test_indexer.py`

- [ ] **Step 1: Create conftest.py with shared fixtures**

`tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Write failing tests**

`tests/test_indexer.py`:
```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_indexer.py -v
```

Expected: `ImportError: cannot import name 'init_db' from 'indexer'`

- [ ] **Step 4: Implement init_db and insert_conversations in indexer.py**

```python
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
from parsers.base import Conversation


def init_db(conn: sqlite3.Connection) -> None:
    schema = Path(__file__).parent / "schema.sql"
    conn.executescript(schema.read_text())
    conn.commit()


def insert_conversations(conn: sqlite3.Connection, conversations: list[Conversation]) -> None:
    for conv in conversations:
        full_text = "\n".join(
            f"{msg.sender}: {msg.text}" for msg in conv.messages
        )
        conn.execute(
            "INSERT OR REPLACE INTO conversations (uuid, name, summary, created_at, full_text) VALUES (?,?,?,?,?)",
            (conv.uuid, conv.name, conv.summary, conv.created_at, full_text),
        )
        for msg in conv.messages:
            conn.execute(
                "INSERT OR REPLACE INTO messages (uuid, conv_uuid, sender, text, created_at) VALUES (?,?,?,?,?)",
                (msg.uuid, conv.uuid, msg.sender, msg.text, msg.created_at),
            )

    # Rebuild FTS index
    conn.execute("INSERT INTO conversations_fts(conversations_fts) VALUES('rebuild')")
    conn.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_indexer.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add indexer.py tests/conftest.py tests/test_indexer.py
git commit -m "feat: add DB init and conversation insertion"
```

---

## Task 5: Indexer CLI

**Files:**
- Modify: `indexer.py` — add `__main__` entry point

- [ ] **Step 1: Write the failing test**

Append to `tests/test_indexer.py`:
```python
import subprocess
import sys
import json
import tempfile
import os


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

    result = subprocess.run(
        [sys.executable, "indexer.py", str(export_path), "--db", str(db_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    conn.close()
    assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_indexer.py::test_cli_indexes_file -v
```

Expected: FAIL — `indexer.py` has no `__main__` block, subprocess exits with error.

- [ ] **Step 3: Add CLI entry point to indexer.py**

Append to `indexer.py`:
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Index a Claude chat export into SQLite.")
    parser.add_argument("export", help="Path to conversations.json export file")
    parser.add_argument("--db", default="history.db", help="Output SQLite DB path (default: history.db)")
    parser.add_argument("--provider", default="claude", choices=["claude"], help="Export provider format")
    args = parser.parse_args()

    if args.provider == "claude":
        from parsers.claude import ClaudeParser
        parser_cls = ClaudeParser()
    else:
        raise ValueError(f"Unknown provider: {args.provider}")

    print(f"Parsing {args.export}...")
    conversations = parser_cls.parse(args.export)
    print(f"Found {len(conversations)} conversations.")

    conn = sqlite3.connect(args.db)
    init_db(conn)
    insert_conversations(conn, conversations)
    conn.close()

    print(f"Done. DB written to {args.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_indexer.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Smoke test against real export**

```bash
python indexer.py ~/Downloads/data-2026-03-31-14-39-01-batch-0000/conversations.json --db history.db
```

Expected output:
```
Parsing .../conversations.json...
Found 255 conversations.
Done. DB written to history.db
```

- [ ] **Step 6: Commit**

```bash
git add indexer.py tests/test_indexer.py
git commit -m "feat: add indexer CLI"
```

---

## Task 6: MCP Server — search_history

**Files:**
- Create: `server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

`tests/test_server.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v -k "search"
```

Expected: `ImportError: cannot import name 'search_history' from 'server'`

- [ ] **Step 3: Implement server.py with search_history**

```python
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Pure functions (testable without MCP)

def search_history(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            c.uuid,
            c.name,
            c.created_at,
            snippet(conversations_fts, 2, '[', ']', '...', 32) AS snippet,
            rank
        FROM conversations c
        JOIN conversations_fts ON c.rowid = conversations_fts.rowid
        WHERE conversations_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    return [
        {"uuid": r[0], "name": r[1], "created_at": r[2], "snippet": r[3], "rank": r[4]}
        for r in rows
    ]


def get_conversation(conn: sqlite3.Connection, uuid: str) -> list[dict]:
    rows = conn.execute(
        "SELECT sender, text, created_at FROM messages WHERE conv_uuid = ? ORDER BY created_at",
        (uuid,),
    ).fetchall()
    messages = [{"sender": r[0], "text": r[1], "created_at": r[2]} for r in rows]

    # Truncate at 50k total chars
    total = 0
    truncated = []
    for msg in messages:
        total += len(msg["text"])
        if total > 50_000:
            truncated.append({"sender": "system", "text": "[conversation truncated at 50k chars]", "created_at": ""})
            break
        truncated.append(msg)
    return truncated


def list_conversations(conn: sqlite3.Connection, limit: int = 20, after: str | None = None) -> list[dict]:
    if after:
        rows = conn.execute(
            """
            SELECT c.uuid, c.name, c.created_at, COUNT(m.uuid) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conv_uuid = c.uuid
            WHERE c.created_at < ?
            GROUP BY c.uuid
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (after, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.uuid, c.name, c.created_at, COUNT(m.uuid) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conv_uuid = c.uuid
            GROUP BY c.uuid
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{"uuid": r[0], "name": r[1], "created_at": r[2], "message_count": r[3]} for r in rows]


# MCP server

def make_server(db_path: str) -> FastMCP:
    mcp = FastMCP("chat-history")
    conn = sqlite3.connect(db_path, check_same_thread=False)

    @mcp.tool(description="Search chat history using full-text search. Returns ranked conversations with snippets.")
    def search_history_tool(query: str, limit: int = 10) -> list[dict]:
        return search_history(conn, query, limit)

    @mcp.tool(description="Get the full message thread for a conversation by UUID.")
    def get_conversation_tool(uuid: str) -> list[dict]:
        return get_conversation(conn, uuid)

    @mcp.tool(description="List conversations sorted by date descending. Use 'after' (ISO date) for pagination.")
    def list_conversations_tool(limit: int = 20, after: str = "") -> list[dict]:
        return list_conversations(conn, limit, after or None)

    return mcp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat history MCP server")
    parser.add_argument("--db", required=True, help="Path to history.db")
    args = parser.parse_args()
    mcp = make_server(args.db)
    mcp.run(transport="stdio")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_server.py -v -k "search"
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add MCP server with search_history tool"
```

---

## Task 7: MCP Server — get_conversation and list_conversations

**Files:**
- Modify: `tests/test_server.py` — add remaining tool tests

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v -k "get_conversation or list_conversations"
```

Expected: FAIL — functions exist but tests for `get_conversation` and `list_conversations` with the `db` fixture will fail because `mem_db` is a sqlite3 connection but the server functions already accept a connection. Tests should actually pass for the pure functions. If they fail for other reasons, read the error.

- [ ] **Step 3: Run all server tests**

```bash
pytest tests/test_server.py -v
```

Expected: all tests PASS (the pure functions `get_conversation` and `list_conversations` were already implemented in Task 6's server.py).

If any fail, fix the implementation in `server.py` to match the test expectations.

- [ ] **Step 4: Commit**

```bash
git add tests/test_server.py
git commit -m "feat: add tests for get_conversation and list_conversations tools"
```

---

## Task 8: End-to-End Smoke Test

**Files:**
- No code changes — manual verification only

- [ ] **Step 1: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS with no warnings.

- [ ] **Step 2: Start the MCP server manually and verify it launches**

```bash
python server.py --db history.db
```

Expected: server starts and listens on stdio without errors. Press Ctrl+C to stop.

- [ ] **Step 3: Add MCP server to Claude Desktop config**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chat-history": {
      "command": "python",
      "args": [
        "/Users/sneg55/Documents/GitHub/old-claude-mcp/server.py",
        "--db",
        "/Users/sneg55/Documents/GitHub/old-claude-mcp/history.db"
      ]
    }
  }
}
```

Restart Claude Desktop. In a new conversation, ask:
> "Search my history for anything about Tradeium"

Expected: Claude calls `search_history_tool` with query "Tradeium" and returns results from the indexed history.

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete chat history MCP server"
```

---

## Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# chat-history-mcp

Local MCP server that indexes exported Claude chat history and lets Claude search it during conversations.

## Setup

1. Export your Claude history from claude.ai (Settings → Export Data)
2. Install dependencies: `pip install -r requirements.txt`
3. Index your export: `python indexer.py ~/Downloads/conversations.json --db history.db`
4. Add to Claude Desktop config:

\`\`\`json
{
  "mcpServers": {
    "chat-history": {
      "command": "python",
      "args": ["/path/to/server.py", "--db", "/path/to/history.db"]
    }
  }
}
\`\`\`

5. Restart Claude Desktop.

## Usage

Just talk normally. Claude will call the tools when relevant:

- "What did we decide about X?" → `search_history("X")` → `get_conversation(uuid)`
- "Load context for project Y" → `search_history("Y")`
- "Find all conversations about company Z" → `search_history("Z")`

## Tools

| Tool | Description |
|------|-------------|
| `search_history(query, limit?)` | Full-text search, returns ranked summaries with snippets |
| `get_conversation(uuid)` | Full message thread for a conversation |
| `list_conversations(limit?, after?)` | Browse by date |

## Adding New Providers

Implement `ConversationParser` from `parsers/base.py` and pass it to `insert_conversations()` in `indexer.py`.

## Future

- Semantic/vector search (ChromaDB + sentence-transformers)
- ChatGPT export support (`ChatGPTParser`)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```
