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
