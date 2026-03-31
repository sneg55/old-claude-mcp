from __future__ import annotations
import argparse
import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncIterator
from mcp.server.fastmcp import FastMCP

# Pure functions (testable without MCP)

def search_history(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    if not query or not query.strip():
        return []
    try:
        rows = conn.execute(
            """
            SELECT
                c.uuid,
                c.name,
                c.created_at,
                snippet(conversations_fts, -1, '[', ']', '...', 32) AS snippet,
                rank
            FROM conversations c
            JOIN conversations_fts ON c.rowid = conversations_fts.rowid
            WHERE conversations_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except Exception:
        return []
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
    conn = sqlite3.connect(db_path, check_same_thread=False)

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            conn.close()

    mcp = FastMCP("chat-history", lifespan=lifespan)

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
