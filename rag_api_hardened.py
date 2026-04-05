"""
RAG API for Agent Integration (Hardened Version)
Uses RAGDatabaseHardened with all safety features
"""

from rag_database_hardened import RAGDatabaseHardened

class RAGHardened:
    """Hardened RAG API with safety features"""

    _instance = None
    _db = None

    @classmethod
    def get(cls):
        """Get singleton instance with hardening"""
        if cls._instance is None:
            cls._instance = cls()
            cls._db = RAGDatabaseHardened(
                db_path="rag_data.db",
                enable_backup=True
            )
            cls._db.connect()
        return cls._instance

    def search_sessions(self, query, limit=5):
        """Search across all sessions"""
        return self._db.search(query, namespace="sessions", limit=limit)

    def search_projects(self, query, limit=5):
        """Search across all projects"""
        return self._db.search(query, namespace="projects", limit=limit)

    def search_facts(self, query, limit=5):
        """Search across all facts"""
        return self._db.search(query, namespace="facts", limit=limit)

    def search_skills(self, query, limit=5):
        """Search across all tools and skills"""
        return self._db.search(query, namespace="tools_skills", limit=limit)

    def search_all(self, query, limit=10):
        """Search across all namespaces"""
        return self._db.search(query, limit=limit)

    def search(self, query, namespace=None, limit=5):
        """Search for similar documents (wrapper for RAGDatabaseHardened)"""
        return self._db.search(query, namespace=namespace, limit=limit)

    def add_session_note(self, content, session_id, metadata=None):
        """Add a note about a session with write locking"""
        return self._db.add_document(
            namespace="sessions",
            content=content,
            source_id=f"note_{session_id}",
            metadata=metadata or {}
        )

    def add_fact(self, content, fact_type="general", metadata=None):
        """Add a fact to database with write locking"""
        if metadata is None:
            metadata = {}
        metadata['type'] = fact_type
        return self._db.add_document(
            namespace="facts",
            content=content,
            source_id=f"fact_{fact_type}",
            metadata=metadata
        )

    def add_document(self, namespace, content, source_id=None, metadata=None):
        """Add a document to database (wrapper with write locking)"""
        return self._db.add_document(namespace, content, source_id, metadata)

    def track_tool_use(self, tool_name, success=True):
        """Track tool/skill usage with write locking"""
        return self._db.update_tool_usage(tool_name, success)

    def add_project(self, name, description=None, metadata=None):
        """Add a project with write locking"""
        return self._db.add_project(name, description, metadata)

    def get_by_source_id(self, source_id):
        """Get documents by source ID"""
        return self._db.get_by_source_id(source_id)

    def get_context_for_task(self, task_description, limit=5):
        """
        Get relevant context for a task by searching all namespaces
        Returns combined context from sessions, facts, projects and skills
        """
        results = {
            'sessions': self.search_sessions(task_description, limit=limit),
            'facts': self.search_facts(task_description, limit=limit),
            'projects': self.search_projects(task_description, limit=limit),
            'skills': self.search_skills(task_description, limit=limit)
        }

        # Count total results
        total_results = sum(len(v) for v in results.values())

        return {
            'total_results': total_results,
            'results': results
        }

    def get_stats(self):
        """Get database statistics with fallback mode info"""
        return self._db.get_stats()

    def is_fallback_mode(self):
        """Check if running in TF-IDF fallback mode"""
        return self._db.is_fallback_mode()

    def close(self):
        """Close database connection"""
        if self._db:
            self._db.close()
            self._db = None
            self._instance = None


# Convenience functions
def search(query, namespace=None, limit=5):
    """Quick search function"""
    rag = RAGHardened.get()
    return rag._db.search(query, namespace=namespace, limit=limit)


def search_sessions(query, limit=5):
    """Search sessions"""
    return RAGHardened.get().search_sessions(query, limit)


def search_facts(query, limit=5):
    """Search facts"""
    return RAGHardened.get().search_facts(query, limit)


def search_projects(query, limit=5):
    """Search projects"""
    return RAGHardened.get().search_projects(query, limit)


def search_skills(query, limit=5):
    """Search skills"""
    return RAGHardened.get().search_skills(query, limit)


def get_task_context(task_description, limit=5):
    """Get context for a task"""
    return RAGHardened.get().get_context_for_task(task_description, limit)
