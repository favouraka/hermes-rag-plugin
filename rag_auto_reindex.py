"""
Automatic Vector Re-Indexing for RAG System
Monitors database growth and automatically rebuilds indexes when needed
"""

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReindexConfig:
    """Configuration for automatic re-indexing."""
    # Size-based triggers
    max_documents_before_reindex: int = 10000  # Reindex after 10k documents
    max_index_size_mb: float = 50.0  # Reindex if index > 50MB

    # Time-based triggers
    reindex_interval_hours: int = 24  # Reindex every 24 hours
    last_reindex_file: str = "reindex_state.json"

    # Performance-based triggers
    avg_search_time_threshold_ms: float = 500.0  # Reindex if avg search > 500ms
    sample_searches: int = 10  # Number of searches to sample

    # Reindex settings
    enable_auto_reindex: bool = True  # Enable automatic reindexing
    require_confirmation: bool = False  # Require user confirmation

    # Callbacks
    on_reindex_start: Optional[callable] = None
    on_reindex_progress: Optional[callable] = None
    on_reindex_complete: Optional[callable] = None


@dataclass
class ReindexState:
    """State of automatic re-indexing."""
    last_reindex_time: str = ""  # ISO timestamp
    last_document_count: int = 0
    last_index_size_mb: float = 0.0
    reindex_count: int = 0
    last_reindex_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage."""
        return {
            'last_reindex_time': self.last_reindex_time,
            'last_document_count': self.last_document_count,
            'last_index_size_mb': self.last_index_size_mb,
            'reindex_count': self.reindex_count,
            'last_reindex_duration_seconds': self.last_reindex_duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReindexState':
        """Create from dict."""
        return cls(
            last_reindex_time=data.get('last_reindex_time', ''),
            last_document_count=data.get('last_document_count', 0),
            last_index_size_mb=data.get('last_index_size_mb', 0.0),
            reindex_count=data.get('reindex_count', 0),
            last_reindex_duration_seconds=data.get('last_reindex_duration_seconds', 0.0),
        )


class AutoReindexer:
    """
    Automatic vector re-indexing manager.

    Monitors database growth and performance, triggers re-indexing
    when thresholds are exceeded.

    Re-indexing strategies:
    1. Size-based: Reindex after N documents or index size exceeds limit
    2. Time-based: Reindex every N hours
    3. Performance-based: Reindex if search performance degrades
    """

    def __init__(self, config: ReindexConfig = None, state_file: str = None):
        """
        Initialize auto re-indexer.

        Args:
            config: ReindexConfig with thresholds
            state_file: Path to store reindex state
        """
        self.config = config or ReindexConfig()
        self.state_file = Path(state_file) if state_file else Path(self.config.last_reindex_file)
        self.state = self._load_state()
        self.rag_db = None  # Will be set via set_database()

        logger.info("Auto re-indexer initialized")

    def _load_state(self) -> ReindexState:
        """Load reindex state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ReindexState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load reindex state: {e}")
        return ReindexState()

    def _save_state(self):
        """Save reindex state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save reindex state: {e}")

    def set_database(self, rag_db):
        """Set the RAG database instance."""
        self.rag_db = rag_db

    def get_document_count(self) -> int:
        """Get current document count from database."""
        if self.rag_db is None:
            return 0

        try:
            cursor = self.rag_db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def get_index_size(self) -> float:
        """Get current index size in MB."""
        if self.rag_db is None:
            return 0.0

        try:
            db_path = Path(self.rag_db.db_path)
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                return size_bytes / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.error(f"Failed to get index size: {e}")

        return 0.0

    def should_reindex(self) -> tuple[bool, str]:
        """
        Check if re-indexing should be triggered.

        Returns:
            (should_reindex, reason)
        """
        reasons = []

        # Check size-based triggers
        doc_count = self.get_document_count()
        new_docs = doc_count - self.state.last_document_count

        if doc_count >= self.config.max_documents_before_reindex:
            reasons.append(f"Document count ({doc_count}) >= threshold ({self.config.max_documents_before_reindex})")
        elif new_docs >= 1000:  # Reindex if 1000+ new documents
            reasons.append(f"New documents ({new_docs}) >= 1000")

        index_size = self.get_index_size()
        if index_size >= self.config.max_index_size_mb:
            reasons.append(f"Index size ({index_size:.1f}MB) >= threshold ({self.config.max_index_size_mb}MB)")

        # Check time-based triggers
        if self.state.last_reindex_time:
            last_reindex = datetime.fromisoformat(self.state.last_reindex_time)
            hours_since_reindex = (datetime.now() - last_reindex).total_seconds() / 3600

            if hours_since_reindex >= self.config.reindex_interval_hours:
                reasons.append(f"Time since last reindex ({hours_since_reindex:.1f}h) >= interval ({self.config.reindex_interval_hours}h)")
        else:
            reasons.append("Never reindexed")

        # Check performance-based triggers (if RAG is available)
        if self.rag_db:
            try:
                avg_search_time = self._sample_search_performance()
                if avg_search_time >= self.config.avg_search_time_threshold_ms:
                    reasons.append(f"Average search time ({avg_search_time:.1f}ms) >= threshold ({self.config.avg_search_time_threshold_ms}ms)")
            except Exception as e:
                logger.debug(f"Could not sample performance: {e}")

        should = len(reasons) > 0
        reason = "; ".join(reasons) if should else "All thresholds OK"

        return should, reason

    def _sample_search_performance(self) -> float:
        """Sample search performance to detect degradation."""
        if self.rag_db is None:
            return 0.0

        # Sample queries
        sample_queries = [
            "database query",
            "system configuration",
            "user preferences",
            "network setup",
            "API usage",
        ]

        times = []
        for query in sample_queries[:self.config.sample_searches]:
            try:
                start = time.time()
                self.rag_db.search(query, limit=5)
                times.append((time.time() - start) * 1000)  # Convert to ms
            except Exception:
                continue

        if not times:
            return 0.0

        return sum(times) / len(times)

    def reindex(self, force: bool = False) -> Dict[str, Any]:
        """
        Re-index the database.

        Args:
            force: Force reindex regardless of thresholds

        Returns:
            Dict with reindex results
        """
        if not force and not self.config.enable_auto_reindex:
            return {
                "success": False,
                "reason": "Auto re-index disabled",
            }

        should, reason = self.should_reindex()

        if not force and not should:
            return {
                "success": False,
                "reason": reason,
            }

        # Confirm if required
        if self.config.require_confirmation and not force:
            response = input(f"Reindex database? Reason: {reason}\nConfirm (y/n): ")
            if response.lower() != 'y':
                return {
                    "success": False,
                    "reason": "User cancelled",
                }

        # Start reindex
        logger.info(f"Starting re-index: {reason}")
        if self.config.on_reindex_start:
            self.config.on_reindex_start(reason)

        start_time = time.time()

        try:
            # Get all documents
            cursor = self.rag_db.conn.cursor()
            cursor.execute("SELECT source_id, content, namespace, metadata FROM documents")
            documents = cursor.fetchall()

            # Drop old documents
            cursor.execute("DELETE FROM documents")
            cursor.execute("DELETE FROM document_chunks")

            # Re-index documents
            reindexed = 0
            batch_size = 100

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]

                for doc in batch:
                    source_id, content, namespace, metadata = doc
                    metadata_dict = json.loads(metadata) if metadata else {}

                    # Re-add document
                    self.rag_db.add_document(
                        namespace=namespace,
                        content=content,
                        source_id=source_id,
                        metadata=metadata_dict
                    )
                    reindexed += 1

                # Report progress
                if self.config.on_reindex_progress:
                    self.config.on_reindex_progress(reindexed, len(documents))

                logger.info(f"Re-indexed {reindexed}/{len(documents)} documents")

            # Commit changes
            self.rag_db.conn.commit()

            # Update state
            duration = time.time() - start_time
            self.state.last_reindex_time = datetime.now().isoformat()
            self.state.last_document_count = self.get_document_count()
            self.state.last_index_size_mb = self.get_index_size()
            self.state.reindex_count += 1
            self.state.last_reindex_duration_seconds = duration
            self._save_state()

            result = {
                "success": True,
                "reason": reason,
                "documents_reindexed": reindexed,
                "duration_seconds": duration,
                "timestamp": self.state.last_reindex_time,
            }

            logger.info(f"Re-index complete: {reindexed} documents in {duration:.1f}s")

            if self.config.on_reindex_complete:
                self.config.on_reindex_complete(result)

            return result

        except Exception as e:
            logger.error(f"Re-index failed: {e}")
            self.rag_db.conn.rollback()

            return {
                "success": False,
                "reason": f"Re-index failed: {str(e)}",
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        doc_count = self.get_document_count()
        index_size = self.get_index_size()
        should, reason = self.should_reindex()

        return {
            "document_count": doc_count,
            "index_size_mb": index_size,
            "last_reindex_time": self.state.last_reindex_time or "Never",
            "last_reindex_duration_seconds": self.state.last_reindex_duration_seconds,
            "reindex_count": self.state.reindex_count,
            "should_reindex": should,
            "reindex_reason": reason if should else "None",
            "config": {
                "max_documents": self.config.max_documents_before_reindex,
                "max_index_size_mb": self.config.max_index_size_mb,
                "reindex_interval_hours": self.config.reindex_interval_hours,
                "enable_auto_reindex": self.config.enable_auto_reindex,
            },
        }


def demo_auto_reindex():
    """Demonstrate automatic re-indexing."""

    print("=" * 70)
    print("Automatic Re-Indexing Demo")
    print("=" * 70)

    # Create config
    config = ReindexConfig(
        max_documents_before_reindex=100,  # Low for demo
        max_index_size_mb=10.0,
        reindex_interval_hours=1,
        enable_auto_reindex=True,
        require_confirmation=False,
    )

    # Create reindexer
    reindexer = AutoReindexer(config=config)

    print("\n✓ Auto re-indexer initialized")
    print(f"  Max documents: {config.max_documents_before_reindex}")
    print(f"  Max index size: {config.max_index_size_mb}MB")
    print(f"  Reindex interval: {config.reindex_interval_hours}h")

    # Check initial status
    print("\n" + "=" * 70)
    print("Initial Status")
    print("=" * 70)

    status = reindexer.get_status()
    print(f"\nDocument count: {status['document_count']}")
    print(f"Index size: {status['index_size_mb']:.1f}MB")
    print(f"Last reindex: {status['last_reindex_time']}")
    print(f"Reindex count: {status['reindex_count']}")
    print(f"Should reindex: {status['should_reindex']}")
    if status['should_reindex']:
        print(f"Reason: {status['reindex_reason']}")

    # Simulate with mock database
    print("\n" + "=" * 70)
    print("Simulating Re-Index (Mock)")
    print("=" * 70)

    class MockConnection:
        """Mock connection for demo."""
        def cursor(self):
            return MockCursor()
        def execute(self, sql, params=None):
            pass
        def commit(self):
            pass
        def rollback(self):
            pass

    class MockCursor:
        """Mock cursor for demo."""
        def execute(self, sql, params=None):
            pass
        def fetchone(self):
            return [150]  # Simulate 150 documents
        def fetchall(self):
            # Simulate documents
            return [
                ('doc1', 'Content 1', 'namespace', '{}'),
                ('doc2', 'Content 2', 'namespace', '{}'),
            ]

    class MockRAG:
        """Mock RAG for demo."""
        def __init__(self):
            self.conn = MockConnection()
            self.db_path = "/tmp/test_reindex.db"

        def search(self, query, limit):
            # Simulate search delay
            time.sleep(0.01)

        def add_document(self, namespace, content, source_id, metadata):
            pass

    reindexer.set_database(MockRAG())

    # Trigger reindex (force)
    print("\nForcing re-index...")
    result = reindexer.reindex(force=True)

    print(f"\nRe-index result: {'Success' if result['success'] else 'Failed'}")
    if result['success']:
        print(f"  Documents re-indexed: {result['documents_reindexed']}")
        print(f"  Duration: {result['duration_seconds']:.1f}s")
        print(f"  Timestamp: {result['timestamp']}")
    else:
        print(f"  Reason: {result['reason']}")

    # Check status after reindex
    print("\n" + "=" * 70)
    print("Status After Re-Index")
    print("=" * 70)

    status = reindexer.get_status()
    print(f"\nDocument count: {status['document_count']}")
    print(f"Index size: {status['index_size_mb']:.1f}MB")
    print(f"Last reindex: {status['last_reindex_time']}")
    print(f"Last reindex duration: {status['last_reindex_duration_seconds']:.1f}s")
    print(f"Reindex count: {status['reindex_count']}")
    print(f"Should reindex: {status['should_reindex']}")
    if status['should_reindex']:
        print(f"Reason: {status['reindex_reason']}")
    else:
        print(f"Reason: {status['reindex_reason']}")

    print("\n✅ Automatic re-indexing demo complete!")


if __name__ == "__main__":
    demo_auto_reindex()
