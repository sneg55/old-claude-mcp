# chat-history-mcp

Local MCP server that indexes exported Claude chat history and lets Claude search it during conversations.

## Setup

1. Export your Claude history from claude.ai (Settings → Export Data)
2. Install dependencies: `pip install -r requirements.txt`
3. Index your export: `python indexer.py ~/Downloads/conversations.json --db history.db`
4. Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "chat-history": {
      "command": "python",
      "args": ["/path/to/server.py", "--db", "/path/to/history.db"]
    }
  }
}
```

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
