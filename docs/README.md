# RAG Memory Plugin for Hermes Agent

Production-grade RAG (Retrieval-Augmented Generation) memory plugin with peer/session tracking and namespace isolation.

## Features

- **Hybrid Retrieval**: TF-IDF (fast, 1-5ms) + Neural (semantic, coming soon)
- **Peer/Session Tracking**: Automatic multi-party conversation tracking
- **Namespace Isolation**: Scoped search by peer, session, or combined
- **Auto-Capture**: Automatic message capture via Hermes hooks
- **Context Injection**: Auto-inject peer/session context before LLM calls
- **Zero Configuration**: Drop-in installation, works immediately

## Installation

### Quick Install

1. Clone or download the plugin:

```bash
cd ~/.hermes/plugins/
git clone https://github.com/favouraka/hermes-rag-plugin.git rag-memory
cd rag-memory
git checkout feature/hermes-plugin-integration
```

2. The plugin directory structure:

```
~/.hermes/plugins/rag-memory/
├── plugin.yaml         # Plugin manifest
├── __init__.py        # Registration function
├── schemas.py         # Tool schemas (what LLM sees)
├── tools.py           # Tool handlers
├── peer_model.py      # Peer model
├── session.py         # Session model
├── auto_capture.py    # Auto peer capture
├── namespace.py       # Namespace isolation
└── rag_core.py        # RAG core
```

3. Start Hermes and verify loading:

```bash
hermes
```

Then in the chat interface, type:

```
/plugins
```

You should see:

```
Plugins (1): rag-memory v2.0.0 (9 tools, 2 hooks)
```

### Development Install

For development or local testing:

```bash
# Copy plugin files
cp -r rag-system-phase1/* ~/.hermes/plugins/rag-memory/
```

## Tools

The plugin exposes 9 tools to the LLM:

### `rag_search`

Search RAG memory for relevant information.

**Parameters:**
- `query` (required): Search query or question
- `mode` (optional): 'hybrid' (default), 'tfidf' (fast), 'neural' (semantic)
- `namespace` (optional): Specific namespace (e.g., 'peer_alice')
- `peer_id` (optional): Search within peer's namespace
- `session_id` (optional): Search within session's namespace
- `limit` (optional, default: 10): Maximum results
- `tokens` (optional, default: 500): Token budget

**Example usage:**
```
Search RAG for information about Alice's preferences
```
```
Search RAG in session chat-1 for what we discussed about Python
```

### `rag_add_document`

Add a document to RAG memory.

**Parameters:**
- `content` (required): Document content
- `namespace` (optional): Namespace to store in
- `peer_id` (optional): Store in peer's namespace
- `session_id` (optional): Store in session's namespace
- `metadata` (optional): Metadata to attach
- `document_id` (optional): Custom document ID

**Example usage:**
```
Save this note: "Alice prefers Python over JavaScript for web scraping"
```
```
Add to Alice's memory: She works at Acme Corp in the engineering team
```

### `rag_get_peer_context`

Get conversation context for a specific peer.

**Parameters:**
- `peer_id` (required): Peer identifier
- `tokens` (optional, default: 500): Token budget
- `include_metadata` (optional, default: false): Include peer metadata
- `format` (optional, default: 'text'): 'text', 'openai', or 'anthropic'

**Example usage:**
```
Get conversation context for Alice
```
```
What has Alice been discussing recently?
```

### `rag_get_session_context`

Get full context of a session.

**Parameters:**
- `session_id` (required): Session identifier
- `limit` (optional, default: 100): Maximum messages
- `format` (optional, default: 'text'): 'text', 'openai', or 'anthropic'
- `include_metadata` (optional, default: false): Include session metadata

**Example usage:**
```
Show me the full conversation from session planning-1
```

### `rag_start_session`

Start a new session with multiple peers.

**Parameters:**
- `peer_ids` (required): List of peer IDs
- `session_id` (optional): Custom session ID
- `metadata` (optional): Session metadata
- `activate` (optional, default: true): Set as active session

**Example usage:**
```
Start a session with Alice, Bob, and Charlie
```
```
Create a planning session with the engineering team
```

### `rag_end_session`

End a session.

**Parameters:**
- `session_id` (optional): Session ID to end (ends active session if not provided)

**Example usage:**
```
End the current session
```

### `rag_capture_message`

Capture a message with automatic peer/session tracking.

**Parameters:**
- `peer_id` (required): Peer identifier
- `content` (required): Message content
- `role` (optional, default: 'user'): 'user', 'assistant', or 'system'
- `session_id` (optional): Session ID (uses active session if not provided)
- `metadata` (optional): Message metadata
- `timestamp` (optional): ISO timestamp

**Example usage:**
```
Record that Alice said she prefers dark mode
```

### `rag_list_peers`

List all peers in memory.

**Parameters:**
- `limit` (optional, default: 50): Maximum peers
- `include_stats` (optional, default: true): Include statistics
- `filter_metadata` (optional): Filter by metadata

**Example usage:**
```
List all peers I've tracked
```
```
Show me all peers with metadata platform=telegram
```

### `rag_list_sessions`

List all sessions in memory.

**Parameters:**
- `limit` (optional, default: 50): Maximum sessions
- `peer_id` (optional): Filter by peer ID
- `include_messages` (optional, default: false): Include session messages
- `include_metadata` (optional, default: true): Include session metadata

**Example usage:**
```
List all sessions involving Alice
```

## Hooks

The plugin registers 2 hooks for automatic functionality:

### `pre_llm_call`

Automatically injects peer/session context before each LLM call.

**Behavior:**
- Checks for active session
- Retrieves recent messages from each peer in session
- Returns context dict added to system prompt
- Reduces need for manual context retrieval

### `post_tool_call`

Automatically captures tool outputs to memory.

**Behavior:**
- Captures tool calls (except RAG tools to avoid recursion)
- Records to active session if available
- Enables automatic memory of actions taken

## Usage Examples

### Example 1: Track a conversation

```
You: Start a session with alice and bob
Hermes: ✓ Session started: session-abc123
         Peers: alice, bob

You: Record that Alice prefers Python
Hermes: ✓ Message captured from: alice

You: What has Alice been discussing?
Hermes: (Uses rag_get_peer_context automatically)
         Alice said she prefers Python...
```

### Example 2: Search peer-specific memory

```
You: What are Bob's preferences?
Hermes: (Searches RAG in peer_bob namespace)
         Found: Bob prefers TypeScript, uses VS Code...
```

### Example 3: Multi-session tracking

```
You: List all sessions with alice
Hermes: Sessions (2):
         chat-1 (15 messages, 2 peers)
         planning-1 (23 messages, 3 peers)
```

## Namespace Isolation

The plugin provides strict namespace isolation to ensure data privacy and scope:

### Namespace Types

1. **Peer Namespace**: `peer_<peer_id>`
   - All messages/documents for a specific peer
   - Search: `rag_search(peer_id="alice")`

2. **Session Namespace**: `session_<session_id>`
   - All messages/documents for a specific session
   - Search: `rag_search(session_id="chat-1")`

3. **Combined Namespace**: `peer_<peer_id>_session_<session_id>`
   - Intersection of peer and session
   - Search: `rag_search(peer_id="alice", session_id="chat-1")`

4. **Default Namespace**: `default`
   - Global documents not scoped to peer/session
   - Search: `rag_search()` or `rag_search(namespace="default")`

### Security

- Peers cannot access other peers' namespaces
- Sessions are isolated from each other
- Same peer can access their data across sessions
- Combined namespace provides strict scoping

## Performance

- **TF-IDF Retrieval**: 1-5ms
- **Peer Context Retrieval**: <10ms
- **Session Context Retrieval**: <50ms
- **Message Capture**: <1ms
- **Search with 100 peers**: <100ms

## Database

Two SQLite databases are created in `~/.hermes/plugins/rag-memory/`:

1. **`rag_memory.db`**: Peer/Session/AutoCapture data
   - Peers table: peer metadata and profiles
   - Sessions table: session metadata and participants
   - Messages table: all captured messages
   - Indexes on peer_id, session_id, timestamp

2. **`rag_core.db`**: RAG document index
   - Documents table: indexed documents
   - TF-IDF terms table: term frequencies
   - Embeddings table: neural embeddings (future)
   - Indexes on namespace, terms

## Development

### Project Structure

```
rag-memory/
├── plugin.yaml         # Plugin manifest
├── __init__.py        # register(ctx) - registration logic
├── schemas.py         # 9 tool schemas for LLM
├── tools.py           # 9 tool handlers + 2 hooks
├── peer_model.py      # Peer model and manager
├── session.py         # Session model and manager
├── auto_capture.py    # Auto peer capture
├── namespace.py       # Namespace isolation
└── rag_core.py        # RAG core (TF-IDF retrieval)
```

### Testing

Run structure verification:

```bash
python3 test_plugin_structure.py
```

Run integration test:

```bash
python3 test_plugin_integration.py
```

## Compatibility

- **Hermes Agent**: Latest (plugins support)
- **Python**: 3.8+
- **Dependencies**: None (uses standard library only)

## Version

Current: **v2.0.0**

## License

MIT

## Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

## Support

- GitHub Issues: https://github.com/favouraka/hermes-rag-plugin/issues
- Discord: https://discord.gg/NousResearch
