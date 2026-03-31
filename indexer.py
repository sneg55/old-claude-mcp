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
