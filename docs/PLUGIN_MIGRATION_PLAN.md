# RAG Plugin Integration Plan

## Critical Issue Identified

Based on the Hermes plugin documentation (https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin), the RAG system needs to be converted from a standalone library into a proper Hermes plugin.

## Current State (Phase 1 Complete)

### Completed Components ✓
1. **Peer Model** (`rag_peer_model.py`)
   - Peer class with ID, metadata, conversation history
   - Methods: add_message(), search(), get_context(), set_metadata(), get_sessions()

2. **Session Model** (`rag_session.py`)
   - Multi-peer support
   - Methods: add_peers(), add_messages(), context(), to_openai(), to_anthropic(), representation()

3. **Auto Peer Capture** (`rag_auto_capture_peer.py`)
   - Automatic peer tracking in message captures
   - Session management with active session tracking
   - Message buffering and auto-flushing
   - Comprehensive test suite (27 tests passing)

4. **Namespace Isolation** (`rag_namespace_isolation.py`)
   - Peer namespace: peer_<peer_id>
   - Session namespace: session_<session_id>
   - Combined namespace: peer_<peer_id>_session_<session_id>
   - Namespace validation and access control
   - Comprehensive test suite (30 tests passing)

### Test Coverage ✓
- `test_peer_model.py`: 14 tests passing
- `test_session.py`: 19 tests passing
- `test_auto_capture_peer.py`: 27 tests passing
- `test_namespace_isolation.py`: 30 tests passing

**Total: 90 tests passing ✓**

## Required Migration to Hermes Plugin

The RAG system needs to be restructured as a proper Hermes plugin with the following directory structure:

```
~/.hermes/plugins/rag-memory/
├── plugin.yaml         # Plugin manifest (name, version, tools, hooks)
├── __init__.py        # Registration function (ctx.register_tool, ctx.register_hook)
├── schemas.py         # Tool schemas (what LLM sees)
├── tools.py           # Tool handlers (code that runs)
├── peer_model.py      # Peer model (from rag_peer_model.py)
├── session.py         # Session model (from rag_session.py)
├── auto_capture.py    # Auto capture (from rag_auto_capture_peer.py)
├── namespace.py       # Namespace isolation (from rag_namespace_isolation.py)
└── rag_core.py        # Core RAG functionality (TF-IDF + Neural)
```

## Migration Steps

### Step 1: Create Plugin Directory Structure
```bash
mkdir -p ~/.hermes/plugins/rag-memory
cd ~/.hermes/plugins/rag-memory
```

### Step 2: Write `plugin.yaml`
```yaml
name: rag-memory
version: 2.0.0
description: Production-grade RAG memory plugin with peer/session tracking and namespace isolation

provides_tools:
  - rag_search
  - rag_add_document
  - rag_get_peer_context
  - rag_get_session_context
  - rag_start_session
  - rag_end_session
  - rag_capture_message
  - rag_list_peers
  - rag_list_sessions

provides_hooks:
  - pre_llm_call    # Inject peer/session context
  - post_tool_call  # Auto-capture messages

author: favouraka
```

### Step 3: Write `schemas.py`
Define tool schemas for the LLM:
- `rag_search`: Search RAG with namespace options
- `rag_add_document`: Add document with peer/session scoping
- `rag_get_peer_context`: Get conversation context for a peer
- `rag_get_session_context`: Get full session context
- `rag_start_session`: Start a new multi-peer session
- `rag_end_session`: End active session
- `rag_capture_message`: Capture message with peer/session tracking
- `rag_list_peers`: List all peers
- `rag_list_sessions`: List all sessions

### Step 4: Write `tools.py`
Tool handlers that execute when LLM calls tools:
- Import existing core modules
- Implement tool logic
- Return formatted results

### Step 5: Write `__init__.py` (Registration)
```python
from . import schemas, tools
from .peer_model import PeerManager
from .session import SessionManager
from .auto_capture import AutoPeerCapture
from .namespace import NamespaceIsolation, IsolatedSearch

# Global instances
_peer_manager = None
_session_manager = None
_auto_capture = None
_isolation = None

def register(ctx):
    """Register all RAG tools and hooks to Hermes."""

    # Initialize global managers
    global _peer_manager, _session_manager, _auto_capture, _isolation
    _peer_manager = PeerManager(db_path=get_db_path())
    _session_manager = SessionManager(db_path=get_db_path())
    _auto_capture = AutoPeerCapture(db_path=get_db_path())
    _isolation = NamespaceIsolation()

    # Register tools
    ctx.register_tool(
        name="rag_search",
        schema=schemas.RAG_SEARCH,
        handler=tools.rag_search
    )
    # ... register other tools

    # Register hooks
    ctx.register_hook("pre_llm_call", tools.inject_context)
    ctx.register_hook("post_tool_call", tools.capture_output)
```

### Step 6: Migrate Core Modules
Rename and adapt existing files:
- `rag_peer_model.py` → `peer_model.py`
- `rag_session.py` → `session.py`
- `rag_auto_capture_peer.py` → `auto_capture.py`
- `rag_namespace_isolation.py` → `namespace.py`
- Create `rag_core.py` for TF-IDF + Neural RAG

### Step 7: Implement `rag_core.py`
Core RAG functionality:
- TF-IDF retrieval (1-5ms)
- Neural retrieval (40-100ms)
- Hybrid retrieval with auto-reranking
- Document addition with embeddings
- Namespace support

### Step 8: Update Documentation
- Create `SKILL.md` for the plugin
- Update README with plugin installation instructions
- Add migration guide from standalone to plugin

### Step 9: Testing
- Adapt existing tests to work with plugin
- Add integration tests for tool registration
- Test hooks (pre_llm_call, post_tool_call)
- Test namespace isolation with tools

### Step 10: Distribution
- Package as pip installable plugin
- Add entry point: `hermes_agent.plugins`
- Update version and publish

## Key Benefits of Plugin Approach

1. **Automatic Integration**: Tools appear alongside built-in tools
2. **Lifecycle Hooks**: Auto-inject context, auto-capture messages
3. **Zero Configuration**: Drop-in installation
4. **Centralized Management**: `/plugins` command to list
5. **Slash Commands**: Add RAG-specific commands
6. **Skills Integration**: Bundle RAG skill automatically

## Remaining Work

1. Create plugin directory structure
2. Write `plugin.yaml` manifest
3. Write `schemas.py` with all tool definitions
4. Write `tools.py` with tool handlers
5. Write `__init__.py` with registration logic
6. Create `rag_core.py` for TF-IDF + Neural
7. Migrate existing modules to plugin structure
8. Adapt tests for plugin context
9. Update documentation
10. Test and distribute

## Notes

- All existing Phase 1 code is solid and tested
- Just needs restructuring for plugin format
- Test suite (90 tests) provides good foundation
- Namespace isolation ensures security
- Peer/Session tracking enables context-aware search

## Next Actions

1. Create `~/.hermes/plugins/rag-memory/` directory
2. Start with `plugin.yaml`
3. Write `schemas.py` first (LLM needs to see tools)
4. Implement `tools.py` (use existing modules)
5. Write `__init__.py` (register everything)
6. Test with `/plugins` command
