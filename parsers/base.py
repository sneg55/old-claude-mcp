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
