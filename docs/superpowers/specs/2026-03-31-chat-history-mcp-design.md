# Chat History MCP Server — Design Spec

**Date:** 2026-03-31
**Status:** Approved

## Overview

A local MCP server that indexes exported Claude chat history into SQLite and exposes three tools Claude can call automatically to retrieve past context. One-time index, read-only at runtime.

**Use cases:**
- Recall conclusions from a specific past conversation
- Load relevant background context when starting work on a topic
- Search all history for mentions of a person, company, or topic

## Architecture

```
conversations.json
       │
       ▼
  indexer.py          ← run once: python indexer.py conversations.json
       │
       ▼
  history.db          ← SQLite with FTS5
       │
       ▼
  server.py           ← MCP server, read-only
       │
  ┌────┴──────────────────┐
  search_history(query)
  get_conversation(uuid)
  list_conversations()
```

## Project Structure

```
chat-history-mcp/
  indexer.py        # CLI: parse export file, populate DB
  server.py         # MCP server exposing 3 tools
  parsers/
    __init__.py
    base.py         # Conversation + Message dataclasses, Parser protocol
    claude.py       # ClaudeParser (launch)
  schema.sql        # DB schema
  README.md
```

## Database Schema

```sql
CREATE TABLE conversations (
    uuid        TEXT PRIMARY KEY,
    name        TEXT,
    summary     TEXT,
    created_at  TEXT,
    full_text   TEXT   -- concatenated message text, used by FTS
);

CREATE TABLE messages (
    uuid        TEXT PRIMARY KEY,
    conv_uuid   TEXT REFERENCES conversations(uuid),
    sender      TEXT,  -- 'human' | 'assistant'
    text        TEXT,
    created_at  TEXT
);

CREATE VIRTUAL TABLE conversations_fts USING fts5(
    name, summary, full_text,
    content='conversations',
    content_rowid='rowid'
);
```

## MCP Tools

### `search_history(query: str, limit: int = 10)`
FTS5 query against `name`, `summary`, and `full_text`. Returns ranked list of conversation summaries with a ~200-char highlighted snippet around the match.

**Returns:** `[{uuid, name, created_at, snippet, rank}]`

### `get_conversation(uuid: str)`
Fetches the full message thread for a conversation. Truncated at ~50k chars with a note if over limit.

**Returns:** `[{sender, text, created_at}]`

### `list_conversations(limit: int = 20, after: str = None)`
Conversations sorted by date descending. `after` is an ISO date string for pagination.

**Returns:** `[{uuid, name, created_at, message_count}]`

## Typical Call Flows

**"What did we decide about X?"**
1. Claude calls `search_history("X")` → ranked hits with snippets
2. Claude calls `get_conversation(uuid)` on best match
3. Claude answers from full thread

**"Load context before starting work on Y"**
1. Claude calls `search_history("Y")` → 2-3 relevant conversations
2. Claude synthesizes background from snippets, fetches full threads as needed

**"Find everything about company Z"**
1. Claude calls `search_history("Z")` → all matches ranked by relevance
2. Claude summarizes across threads

## Provider Abstraction

```python
# parsers/base.py
@dataclass
class Message:
    uuid: str
    sender: str  # 'human' | 'assistant'
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
    def parse(self, filepath: str) -> list[Conversation]: ...
```

`ClaudeParser` implements this for the Claude export format (`conversations.json` with `uuid`, `name`, `chat_messages[]`). Adding a new provider means writing a new parser class — nothing else changes.

**Claude export format:**
```json
{
  "uuid": "...",
  "name": "Conversation title",
  "summary": "",
  "created_at": "2025-12-07T12:39:33Z",
  "chat_messages": [
    {"uuid": "...", "text": "...", "sender": "human", "created_at": "..."}
  ]
}
```

## Usage

```bash
# One-time index
pip install mcp
python indexer.py ~/Downloads/conversations.json

# Add to Claude Desktop config
```

```json
{
  "mcpServers": {
    "chat-history": {
      "command": "python",
      "args": ["/path/to/chat-history-mcp/server.py", "--db", "/path/to/history.db"]
    }
  }
}
```

## Dependencies

- Python 3.10+
- `mcp` SDK (`pip install mcp`)
- Everything else is stdlib (`sqlite3`, `json`, `argparse`, `pathlib`)

## Future Enhancements (not in scope)

- **Semantic/vector search**: Add embeddings column to SQLite + ChromaDB layer. Indexer adds embedding step, `search_history` falls back to semantic when FTS returns nothing.
- **ChatGPT support**: `ChatGPTParser` implementing the same `ConversationParser` protocol.
- **Incremental indexing**: Track last-indexed timestamp, skip existing UUIDs on re-run.
