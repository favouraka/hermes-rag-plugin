"""
Auto-Capture and Retrieval System for RAG
Automatically indexes conversations, patches data, and retrieves context
Supports: neural, tfidf, and hybrid modes
"""

import json
from datetime import datetime
from rag_api import RAG
from rag_api_tfidf import RAG as RAGTfidf

class RAGAuto:
    """Automated RAG integration for conversations with hybrid support"""

    def __init__(self, mode='neural'):
        """
        Initialize RAG system with specified mode

        Args:
            mode: 'neural', 'tfidf', or 'hybrid'
        """
        self.mode = mode
        self.rag_neural = RAG.get()
        self.rag_tfidf = RAGTfidf.get()
        self.conversation_buffer = []
        self.last_search = None
        self.capture_queue = []

        print(f"RAG Auto initialized in {mode} mode")

    def _get_rag(self, mode=None):
        """Get appropriate RAG instance based on mode"""
        mode = mode or self.mode

        if mode == 'neural':
            return self.rag_neural
        elif mode == 'tfidf':
            return self.rag_tfidf
        elif mode == 'hybrid':
            # For hybrid, use neural for now (could implement true hybrid later)
            return self.rag_neural
        else:
            return self.rag_neural  # Default to neural

    def capture_context(self, role, content, metadata=None):
        """
        Capture a message to the conversation buffer
        Messages are batched and indexed when session ends or reaches threshold
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.conversation_buffer.append(message)

        # Check if we should flush the buffer
        if len(self.conversation_buffer) >= 5:  # Every 5 messages
            self.flush_buffer()

    def flush_buffer(self, as_session=False):
        """
        Flush conversation buffer to RAG database
        Adds to both neural and TF-IDF systems
        """
        if not self.conversation_buffer:
            return

        # Build content from buffer
        content_parts = []
        for msg in self.conversation_buffer:
            role = msg['role'].upper()
            text = msg['content']
            content_parts.append(f"{role}: {text}")

        full_content = "\n\n".join(content_parts)

        # Add to sessions namespace (both systems)
        session_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if self.mode in ['neural', 'hybrid']:
            self.rag_neural.add_document(
                namespace="sessions",
                content=full_content,
                source_id=session_id,
                metadata={
                    "type": "auto_session",
                    "message_count": len(self.conversation_buffer),
                    "auto_captured": True,
                    "captured_at": datetime.now().isoformat(),
                    "rag_mode": "neural"
                }
            )

        if self.mode in ['tfidf', 'hybrid']:
            self.rag_tfidf.add_document(
                namespace="sessions",
                content=full_content,
                source_id=session_id,
                metadata={
                    "type": "auto_session",
                    "message_count": len(self.conversation_buffer),
                    "auto_captured": True,
                    "captured_at": datetime.now().isoformat(),
                    "rag_mode": "tfidf"
                }
            )

        # Clear buffer
        self.conversation_buffer = []

    def capture_fact(self, content, fact_type="auto", metadata=None):
        """
        Immediately capture a fact to the facts namespace
        Use for important decisions, corrections, user preferences
        """
        if self.mode in ['neural', 'hybrid']:
            self.rag_neural.add_document(
                namespace="facts",
                content=content,
                source_id=f"fact_{fact_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                metadata={
                    "type": fact_type,
                    "auto_captured": True,
                    "captured_at": datetime.now().isoformat(),
                    "rag_mode": "neural",
                    **(metadata or {})
                }
            )

        if self.mode in ['tfidf', 'hybrid']:
            self.rag_tfidf.add_document(
                namespace="facts",
                content=content,
                source_id=f"fact_{fact_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                metadata={
                    "type": fact_type,
                    "auto_captured": True,
                    "captured_at": datetime.now().isoformat(),
                    "rag_mode": "tfidf",
                    **(metadata or {})
                }
            )

    def capture_decision(self, decision, reason=None, metadata=None):
        """Capture a decision with reasoning"""
        content = f"DECISION: {decision}"
        if reason:
            content += f"\nREASON: {reason}"

        self.capture_fact(content, fact_type="decision", metadata=metadata)

    def capture_correction(self, correction, old_fact=None, metadata=None):
        """Capture a user correction"""
        content = f"CORRECTION: {correction}"
        if old_fact:
            content += f"\nOLD (INCORRECT): {old_fact}"

        self.capture_fact(content, fact_type="correction", metadata=metadata)

    def capture_preference(self, user, preference, metadata=None):
        """Capture a user preference"""
        content = f"PREFERENCE ({user}): {preference}"

        self.capture_fact(content, fact_type="preference", metadata=metadata)

    def capture_task_completion(self, task, outcome, metadata=None):
        """Capture a completed task with outcome"""
        content = f"TASK COMPLETED: {task}\nOUTCOME: {outcome}"

        self.capture_fact(content, fact_type="task_completion", metadata=metadata)

    def track_tool_use(self, tool_name, success=True, metadata=None):
        """Track tool usage for analytics"""
        # Track in neural system
        if self.mode in ['neural', 'hybrid']:
            result = self.rag_neural.track_tool_use(tool_name, success)

        # Also capture as a fact for searchability (both systems)
        content = f"TOOL USED: {tool_name}\nSTATUS: {'SUCCESS' if success else 'FAILED'}"

        if metadata:
            content += f"\nDETAILS: {json.dumps(metadata)}"

        fact_metadata = {
            "tool": tool_name,
            "success": success
        }

        if self.mode in ['neural', 'hybrid']:
            self.rag_neural.add_document(
                namespace="facts",
                content=content,
                source_id=f"tool_{tool_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                metadata={
                    **fact_metadata,
                    "auto_captured": True,
                    "rag_mode": "neural"
                }
            )

        if self.mode in ['tfidf', 'hybrid']:
            self.rag_tfidf.add_document(
                namespace="facts",
                content=content,
                source_id=f"tool_{tool_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                metadata={
                    **fact_metadata,
                    "auto_captured": True,
                    "rag_mode": "tfidf"
                }
            )

    def retrieve_context(self, query, limit=5, namespaces=None):
        """
        Retrieve relevant context before responding
        Supports neural, tfidf, and hybrid modes
        Returns combined results from specified namespaces

        Note: This method returns ALL namespaces, not a single namespace.
        For single namespace search, use the specific RAG instance directly.
        """
        if namespaces is None:
            namespaces = ["facts", "sessions", "projects", "tools_skills"]

        results = {}
        total_results = 0

        if self.mode == 'neural':
            # Neural-only search
            for namespace in namespaces:
                try:
                    namespace_results = self.rag_neural.search(query, namespace=namespace, limit=limit)
                    results[namespace] = namespace_results
                    total_results += len(namespace_results)
                except Exception as e:
                    print(f"Error searching {namespace}: {e}")
                    results[namespace] = []

        elif self.mode == 'tfidf':
            # TF-IDF-only search
            for namespace in namespaces:
                try:
                    namespace_results = self.rag_tfidf.search(query, namespace=namespace, limit=limit)
                    results[namespace] = namespace_results
                    total_results += len(namespace_results)
                except Exception as e:
                    print(f"Error searching {namespace}: {e}")
                    results[namespace] = []

        elif self.mode == 'hybrid':
            # Hybrid search: use neural for semantic understanding
            # (Could be enhanced with true 2-stage retrieval)
            for namespace in namespaces:
                try:
                    namespace_results = self.rag_neural.search(query, namespace=namespace, limit=limit)
                    results[namespace] = namespace_results
                    total_results += len(namespace_results)
                except Exception as e:
                    print(f"Error searching {namespace}: {e}")
                    results[namespace] = []

        self.last_search = query

        return {
            'total_results': total_results,
            'results': results,
            'query': query,
            'mode': self.mode
        }


def get_rag_auto(mode='neural'):
    """
    Get singleton RAG auto instance with specified mode

    Args:
        mode: 'neural', 'tfidf', or 'hybrid'
    """
    if not hasattr(get_rag_auto, '_instance'):
        get_rag_auto._instance = RAGAuto(mode=mode)
        get_rag_auto._mode = mode
    elif get_rag_auto._mode != mode:
        # Reset if mode changed
        get_rag_auto._instance = RAGAuto(mode=mode)
        get_rag_auto._mode = mode

    return get_rag_auto._instance


# Convenience functions for backward compatibility
def auto_retrieve_context(query, limit=5, namespaces=None, mode='neural'):
    """Retrieve context using specified RAG mode"""
    rag = get_rag_auto(mode)
    return rag.retrieve_context(query, limit, namespaces)


def auto_capture_message(role, content, metadata=None, mode='neural'):
    """Capture message using specified RAG mode"""
    rag = get_rag_auto(mode)
    return rag.capture_context(role, content, metadata)


def auto_track_tool(tool_name, success=True, metadata=None, mode='neural'):
    """Track tool usage using specified RAG mode"""
    rag = get_rag_auto(mode)
    return rag.track_tool_use(tool_name, success, metadata)


def auto_flush(as_session=False, mode='neural'):
    """Flush conversation buffer using specified RAG mode"""
    rag = get_rag_auto(mode)
    return rag.flush_buffer(as_session)
