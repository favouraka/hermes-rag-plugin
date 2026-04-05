"""
Invisible RAG Wrapper
All RAG operations happen automatically in background - no manual calls needed
"""

import sys
sys.path.insert(0, '/home/aka/rag-system')

from rag_auto import get_rag_auto, auto_retrieve_context, auto_capture_message, auto_track_tool, auto_flush

class RAGInvisible:
    """Invisible RAG - happens automatically, no user interaction needed"""

    def __init__(self):
        self.rag = get_rag_auto()
        self._auto_enabled = True

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
            context = auto_retrieve_context(
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
            auto_track_tool(tool_name, success, metadata or {})
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

    def on_preference(self, preference, metadata=None):
        """
        Automatically capture user preferences
        Call this when user expresses a preference
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_preference(
                user='Mr. Aka',
                preference=preference,
                metadata=metadata or {}
            )
        except Exception:
            pass  # Fail silently

    def on_task_completion(self, task, outcome, metadata=None):
        """
        Automatically capture task completion
        Call this when a task is completed
        """
        if not self._auto_enabled:
            return

        try:
            self.rag.capture_task_completion(
                task=task,
                outcome=outcome,
                metadata=metadata or {}
            )
        except Exception:
            pass  # Fail silently

    def on_session_end(self):
        """
        Automatically flush at end of conversation
        Call this when conversation ends
        """
        if not self._auto_enabled:
            return

        try:
            auto_flush()
        except Exception:
            pass  # Fail silently

    def _capture_message(self, role, content):
        """Internal: capture message without exposing to user"""
        try:
            auto_capture_message(role, content)
        except Exception:
            pass  # Fail silently

    def disable(self):
        """Temporarily disable auto-capture (for testing)"""
        self._auto_enabled = False

    def enable(self):
        """Re-enable auto-capture"""
        self._auto_enabled = True

# Singleton instance
_rag_invisible_instance = None

def get_rag_invisible():
    """Get singleton RAGInvisible instance"""
    global _rag_invisible_instance
    if _rag_invisible_instance is None:
        _rag_invisible_instance = RAGInvisible()
    return _rag_invisible_instance

# Convenience functions that work invisibly
def auto_before(user_message):
    """Auto-retrieve context and capture user message"""
    return get_rag_invisible().before_respond(user_message)

def auto_after(assistant_response):
    """Auto-capture assistant response"""
    return get_rag_invisible().after_respond(assistant_response)

def auto_tool(tool_name, success=True, metadata=None):
    """Auto-track tool usage"""
    return get_rag_invisible().after_tool_use(tool_name, success, metadata)

def auto_decision(decision, reason=None, metadata=None):
    """Auto-capture decision"""
    return get_rag_invisible().on_decision(decision, reason, metadata)

def auto_correction(correction, old_fact=None, metadata=None):
    """Auto-capture correction"""
    return get_rag_invisible().on_correction(correction, old_fact, metadata)

def auto_preference(preference, metadata=None):
    """Auto-capture preference"""
    return get_rag_invisible().on_preference(preference, metadata)

def auto_task(task, outcome, metadata=None):
    """Auto-capture task completion"""
    return get_rag_invisible().on_task_completion(task, outcome, metadata)

def auto_end():
    """Auto-flush at session end"""
    return get_rag_invisible().on_session_end()
