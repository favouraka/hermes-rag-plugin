"""
RAG Memory Plugin for Hermes Agent
Production-grade RAG memory with peer/session tracking and namespace isolation.
"""

import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

# Import from organized subpackages
from .models import Peer, PeerManager, Session, SessionManager
from .core import RAGCore, NamespaceIsolation, AutoPeerCapture
from . import tools


# Global instances - initialized in register()
_peer_manager = None
_session_manager = None
_auto_capture = None
_isolation = None
_rag_core = None


def register(ctx):
    """
    Register RAG Memory plugin with Hermes.

    This is called when the plugin loads. We register:
    - Tools: RAG search, add document, get context, session management
    - Hooks: Pre-LLM call (inject context), Post-tool call (capture output)
    """
    global _peer_manager, _session_manager, _auto_capture, _isolation, _rag_core

    try:
        logger.info("Initializing RAG Memory plugin...")

        # Initialize database path
        db_path = Path.home() / ".hermes" / "plugins" / "rag-memory" / "rag_memory.db"

        # Create database connection
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row

        # Initialize core managers
        _peer_manager = PeerManager(db_conn=conn)
        logger.info("✓ Peer manager initialized")

        _session_manager = SessionManager(db_conn=conn)
        logger.info("✓ Session manager initialized")

        _auto_capture = AutoPeerCapture(db_path=str(db_path))
        logger.info("✓ Auto peer capture initialized")

        _isolation = NamespaceIsolation(db_conn=_auto_capture.conn)
        logger.info("✓ Namespace isolation initialized")

        _rag_core = RAGCore()
        logger.info("✓ RAG core initialized")

        # Set managers in tools module
        tools.set_managers(
            peer_manager=_peer_manager,
            session_manager=_session_manager,
            auto_capture=_auto_capture,
            isolation=_isolation,
            rag_core=_rag_core
        )

        # Register tools
        ctx.register_tool(
            toolset="rag-memory",
            name="rag_search",
            schema=tools.RAG_SEARCH,
            handler=tools.rag_search
        )
        logger.info("✓ Registered tool: rag_search")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_add_document",
            schema=tools.RAG_ADD_DOCUMENT,
            handler=tools.rag_add_document
        )
        logger.info("✓ Registered tool: rag_add_document")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_get_peer_context",
            schema=tools.RAG_GET_PEER_CONTEXT,
            handler=tools.rag_get_peer_context
        )
        logger.info("✓ Registered tool: rag_get_peer_context")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_get_session_context",
            schema=tools.RAG_GET_SESSION_CONTEXT,
            handler=tools.rag_get_session_context
        )
        logger.info("✓ Registered tool: rag_get_session_context")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_start_session",
            schema=tools.RAG_START_SESSION,
            handler=tools.rag_start_session
        )
        logger.info("✓ Registered tool: rag_start_session")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_end_session",
            schema=tools.RAG_END_SESSION,
            handler=tools.rag_end_session
        )
        logger.info("✓ Registered tool: rag_end_session")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_capture_message",
            schema=tools.RAG_CAPTURE_MESSAGE,
            handler=tools.rag_capture_message
        )
        logger.info("✓ Registered tool: rag_capture_message")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_list_peers",
            schema=tools.RAG_LIST_PEERS,
            handler=tools.rag_list_peers
        )
        logger.info("✓ Registered tool: rag_list_peers")

        ctx.register_tool(
            toolset="rag-memory",
            name="rag_list_sessions",
            schema=tools.RAG_LIST_SESSIONS,
            handler=tools.rag_list_sessions
        )
        logger.info("✓ Registered tool: rag_list_sessions")

        # Register hooks
        ctx.register_hook(
            "pre_llm_call",
            tools.inject_context
        )
        logger.info("✓ Registered hook: pre_llm_call (inject context)")

        ctx.register_hook(
            "post_tool_call",
            tools.capture_output
        )
        logger.info("✓ Registered hook: post_tool_call (capture output)")

        logger.info("✓ RAG Memory plugin loaded successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize RAG Memory plugin: {e}")
        raise


def cleanup():
    """
    Cleanup function called when plugin is unloaded.
    """
    global _peer_manager, _session_manager, _auto_capture, _isolation, _rag_core

    try:
        logger.info("Cleaning up RAG Memory plugin...")

        if _auto_capture:
            _auto_capture.cleanup()

        if _rag_core:
            _rag_core.close()

        logger.info("✓ RAG Memory plugin cleaned up")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


# Expose useful functions for direct access if needed
def get_peer_manager():
    """Get the peer manager instance."""
    return _peer_manager


def get_session_manager():
    """Get the session manager instance."""
    return _session_manager


def get_auto_capture():
    """Get the auto capture instance."""
    return _auto_capture


def get_isolation():
    """Get the namespace isolation instance."""
    return _isolation


def get_rag_core():
    """Get the RAG core instance."""
    return _rag_core
