"""
Invisible RAG Wrapper
All RAG operations happen automatically in background - no manual calls needed
Supports: neural, tfidf, and hybrid modes
"""

import sys
sys.path.insert(0, '/home/aka/rag-system')

from rag_auto_hybrid import get_rag_auto

class RAGInvisible:
    """Invisible RAG - happens automatically, no user interaction needed"""

    def __init__(self, mode='neural'):
        """
        Initialize invisible RAG with specified mode

        Args:
            mode: 'neural', 'tfidf', or 'hybrid' (default: neural)
        """
        self.rag = get_rag_auto(mode)
        self._auto_enabled = True
        self.mode = mode

    def before_respond(self, user_message):
        """
        Automatically retrieve context before responding
        Call this at the start of every response generation
        Returns context for use (optional)
        """
        if not self._auto_enabled:
            return None

        try:
            # Capture user message automatically
            self._capture_message('user', user_message)

            # Retrieve relevant context
            context = self.rag.retrieve_context(
                query=user_message,
                limit=5,
                namespaces=['facts', 'sessions', 'projects']
            )

            # Return context silently (for internal use only)
            return context

        except Exception as e:
            # Fail silently - don't interrupt conversation
            return None

    def after_respond(self, assistant_response):
        """
        Automatically capture assistant response
        Call this after generating response
        """
        if not self._auto_enabled:
            return

        try:
            self._capture_message('assistant', assistant_response)
        except Exception:
            pass  # Fail silently

    def before_tool_use(self, tool_name, metadata=None):
        """Automatically capture before tool use (if needed)"""
        if not self._auto_enabled:
            return

        try:
            pass  # Nothing needed before tool use
        except Exception:
            pass

    def after_tool_use(self, tool_name, success=True, metadata=None):
        """
        Automatically track tool usage
        Call this after using any tool
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.track_tool_use(tool_name, success, metadata or {})
        except Exception:
            pass  # Fail silently

    def on_decision(self, decision, reason=None, metadata=None):
        """
        Automatically capture decisions
        Call this when you detect a decision was made
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_decision(
                decision=decision,
                reason=reason,
                metadata=metadata or {}
            )
        except Exception:
            pass  # Fail silently

    def on_correction(self, correction, old_fact=None, metadata=None):
        """
        Automatically capture user corrections
        Call this when user corrects something
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_correction(
                correction=correction,
                old_fact=old_fact,
                metadata=metadata or {}
            )
        except Exception:
            pass  # Fail silently

    def on_preference(self, user, preference, metadata=None):
        """
        Automatically capture user preferences
        Call this when user expresses a preference
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_preference(user, preference, metadata or {})
        except Exception:
            pass  # Fail silently

    def on_task_completion(self, task, outcome, metadata=None):
        """
        Automatically capture task completions
        Call this when a task is completed
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_task_completion(task, outcome, metadata or {})
        except Exception:
            pass  # Fail silently

    def _capture_message(self, role, content):
        """Internal message capture"""
        try:
            self.rag.capture_context(role, content)
        except Exception:
            pass  # Fail silently

    def set_mode(self, mode):
        """
        Change RAG mode at runtime

        Args:
            mode: 'neural', 'tfidf', or 'hybrid'
        """
        self.mode = mode
        self.rag = get_rag_auto(mode)

    def enable_auto(self):
        """Enable automatic RAG operations"""
        self._auto_enabled = True

    def disable_auto(self):
        """Disable automatic RAG operations"""
        self._auto_enabled = False

    def flush(self):
        """Manually flush conversation buffer"""
        try:
            self.rag.flush_buffer()
        except Exception:
            pass


# Global instances for different modes
_instances = {}


def get_rag_invisible(mode='neural'):
    """
    Get singleton RAG invisible instance for specified mode

    Args:
        mode: 'neural', 'tfidf', or 'hybrid'
    """
    if mode not in _instances:
        _instances[mode] = RAGInvisible(mode=mode)
    return _instances[mode]


# Convenience functions for backward compatibility
# Default to neural mode for existing code
def auto_before(user_message, mode='neural'):
    """Auto-retrieve context before responding"""
    rag = get_rag_invisible(mode)
    return rag.before_respond(user_message)


def auto_after(assistant_response, mode='neural'):
    """Auto-capture assistant response"""
    rag = get_rag_invisible(mode)
    return rag.after_respond(assistant_response)


def auto_tool(tool_name, success=True, metadata=None, mode='neural'):
    """Auto-track tool usage"""
    rag = get_rag_invisible(mode)
    return rag.after_tool_use(tool_name, success, metadata)


def auto_decision(decision, reason=None, metadata=None, mode='neural'):
    """Auto-capture decision"""
    rag = get_rag_invisible(mode)
    return rag.on_decision(decision, reason, metadata)


def auto_correction(correction, old_fact=None, metadata=None, mode='neural'):
    """Auto-capture correction"""
    rag = get_rag_invisible(mode)
    return rag.on_correction(correction, old_fact, metadata)


def auto_preference(user, preference, metadata=None, mode='neural'):
    """Auto-capture preference"""
    rag = get_rag_invisible(mode)
    return rag.on_preference(user, preference, metadata)


def auto_task(task, outcome, metadata=None, mode='neural'):
    """Auto-capture task completion"""
    rag = get_rag_invisible(mode)
    return rag.on_task_completion(task, outcome, metadata)


def auto_flush(as_session=False, mode='neural'):
    """Auto-flush conversation buffer"""
    rag = get_rag_invisible(mode)
    return rag.flush()


def auto_end(mode='neural'):
    """Auto-end session (flush buffer)"""
    return auto_flush(as_session=True, mode=mode)
