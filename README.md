# old-claude-mcp

Anthropic lets you export your Claude conversation history but provides no way to import it into a new account. This is a local MCP server that makes the export actually useful — index your old conversations into SQLite and Claude can search them automatically in new sessions.

**Background:** [Claude lets you export your data but won't let you use it](https://sawinyh.com/blog/claude-export-no-import)

## Why

If you switch Claude accounts, lose access to an email address, or just want your old context available going forward, you're stuck with a JSON file you can't do anything with. This tool indexes that file and exposes it as three MCP tools Claude calls automatically during conversations.

## Setup

**1. Export your Claude history**

Go to claude.ai → Settings → Export Data. You'll get a ZIP containing `conversations.json`.

**2. Install dependencies**

```bash
git clone https://github.com/sneg55/old-claude-mcp
cd old-claude-mcp
pip install -r requirements.txt
```

**3. Index your export**

```bash
python indexer.py ~/Downloads/conversations.json --db history.db
```

**4. Add to Claude Desktop config**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chat-history": {
      "command": "/usr/local/bin/python3",
      "args": [
        "/path/to/old-claude-mcp/server.py",
        "--db",
        "/path/to/old-claude-mcp/history.db"
      ]
    }
  }
}
```

Use an absolute path to your Python interpreter. Find it with `which python3`.

**5. Restart Claude Desktop**

## Usage

Just talk normally. Claude calls the tools automatically when relevant:

- "What did we decide about X?" → `search_history("X")` → `get_conversation(uuid)`
- "Load context for project Y" → `search_history("Y")`
- "Find all conversations about company Z" → `search_history("Z")`

## Tools

| Tool | Description |
|------|-------------|
| `search_history(query, limit?)` | Full-text search across all conversations, returns ranked results with snippets |
| `get_conversation(uuid)` | Full message thread for a conversation (truncated at 50k chars) |
| `list_conversations(limit?, after?)` | Browse conversations by date descending |

## Adding New Providers

Implement `ConversationParser` from `parsers/base.py` and pass it to `insert_conversations()` in `indexer.py`. ChatGPT export support (`ChatGPTParser`) is a natural next step — PRs welcome.

## Future

- Semantic/vector search (ChromaDB + sentence-transformers)
- ChatGPT export support
- Incremental indexing for updated exports
