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


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a Claude chat export into SQLite.")
    parser.add_argument("export", help="Path to conversations.json export file")
    parser.add_argument("--db", default="history.db", help="Output SQLite DB path (default: history.db)")
    parser.add_argument("--provider", default="claude", choices=["claude"], help="Export provider format")
    args = parser.parse_args()

    if args.provider == "claude":
        from parsers.claude import ClaudeParser
        provider_parser = ClaudeParser()
    else:
        raise ValueError(f"Unknown provider: {args.provider}")

    print(f"Parsing {args.export}...")
    conversations = provider_parser.parse(args.export)
    print(f"Found {len(conversations)} conversations.")

    conn = sqlite3.connect(args.db)
    init_db(conn)
    insert_conversations(conn, conversations)
    conn.close()

    print(f"Done. DB written to {args.db}")


if __name__ == "__main__":
    main()
