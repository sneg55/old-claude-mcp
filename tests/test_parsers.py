from parsers.base import Message, Conversation, ConversationParser
import json
import tempfile
import os
from parsers.claude import ClaudeParser


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
