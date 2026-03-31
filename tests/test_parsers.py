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
