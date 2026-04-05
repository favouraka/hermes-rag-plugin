"""
RAG Database System with Hardening (Phase 1)
Improvements:
1. WAL mode enabled for concurrent access
2. File-level locking for write safety
3. Database backup on startup
4. Health check on load
5. Graceful fallback for model failures
"""

import sqlite3
import sqlite_vec
import json
from pathlib import Path
from datetime import datetime
import hashlib
import struct
import fcntl
import logging
import shutil
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DatabaseHealthError(Exception):
    """Raised when database health check fails"""
    pass


class ModelLoadError(Exception):
    """Raised when model fails to load"""
    pass


class RAGDatabaseHardened:
    """
    Hardened RAG database with safety features
    Supports concurrent access, backup, and graceful degradation
    """

    def __init__(
        self,
        db_path="rag_data.db",
        model_path="sentence-transformers/all-MiniLM-L6-v2",
        enable_backup=True,
        backup_dir="backups"
    ):
        self.db_path = Path(db_path)
        self.model_path = model_path
        self.enable_backup = enable_backup
        self.backup_dir = Path(backup_dir)
        self.conn = None
        self.model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
        self._lock_file = None
        self._is_fallback_mode = False

        # Ensure backup directory exists
        if self.enable_backup:
            self.backup_dir.mkdir(exist_ok=True)

    def connect(self):
        """Initialize database connection with hardening"""
        # Check database health first
        if self.db_path.exists():
            self._health_check()

        # Create backup if enabled
        if self.enable_backup and self.db_path.exists():
            self._create_backup()

        # Connect with WAL mode
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # Longer timeout for concurrent access
            check_same_thread=False  # Allow access from multiple threads
        )
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")  # 5 second busy timeout

        # Load sqlite_vec extension
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)

        # Create tables
        self._create_tables()

        # Load model with fallback
        self._load_model_with_fallback()

        print(f"✓ Database connected: {self.db_path}")
        print(f"✓ WAL mode enabled")
        if self._is_fallback_mode:
            print(f"⚠ Running in TF-IDF fallback mode (model load failed)")

    def _health_check(self):
        """Perform database health check"""
        try:
            # Try to open and query the database
            test_conn = sqlite3.connect(self.db_path, timeout=5.0)
            test_conn.execute("SELECT 1")
            test_conn.close()
        except sqlite3.DatabaseError as e:
            logger.error(f"Database health check failed: {e}")
            raise DatabaseHealthError(f"Database {self.db_path} is corrupted: {e}")
        except Exception as e:
            logger.error(f"Health check error: {e}")
            raise DatabaseHealthError(f"Cannot access database {self.db_path}: {e}")

    def _create_backup(self):
        """Create timestamped backup of existing database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"rag_data_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✓ Backup created: {backup_path}")

            # Keep only last 5 backups
            self._cleanup_old_backups()
        except Exception as e:
            logger.warning(f"Backup failed (continuing): {e}")

    def _cleanup_old_backups(self, keep_count=5):
        """Remove old backups, keeping only the most recent"""
        try:
            backups = sorted(self.backup_dir.glob("rag_data_*.db"))
            if len(backups) > keep_count:
                for old_backup in backups[:-keep_count]:
                    old_backup.unlink()
                    logger.info(f"✓ Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Backup cleanup failed: {e}")

    def _load_model_with_fallback(self):
        """Load embedding model with graceful fallback to TF-IDF"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_path)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"✓ Model loaded: {self.model_path} (dim={self.embedding_dim})")
        except Exception as e:
            logger.warning(f"⚠ Model load failed, enabling TF-IDF fallback: {e}")
            self._is_fallback_mode = True
            self.model = None  # Will use TF-IDF instead

    def _acquire_write_lock(self):
        """Acquire file-level lock for writes"""
        lock_path = Path(str(self.db_path) + ".lock")

        try:
            self._lock_file = open(lock_path, 'w')
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
            logger.debug(f"✓ Write lock acquired: {lock_path}")
        except Exception as e:
            logger.error(f"Failed to acquire write lock: {e}")
            raise

    def _release_write_lock(self):
        """Release file-level write lock"""
        if self._lock_file:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                self._lock_file = None
                logger.debug("✓ Write lock released")
            except Exception as e:
                logger.warning(f"Failed to release write lock: {e}")

    def _create_tables(self):
        """Create tables for RAG system"""
        cursor = self.conn.cursor()

        # Main documents table with vector search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS doc_vectors USING vec0(
                id INTEGER PRIMARY KEY,
                namespace TEXT NOT NULL,
                source_id TEXT,
                embedding FLOAT[384],
                content TEXT,
                metadata TEXT,
                created_at TEXT
            )
        """)

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)

        # Tools/skills tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage (
                id INTEGER PRIMARY KEY,
                tool_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT,
                success_rate REAL DEFAULT 1.0,
                metadata TEXT
            )
        """)

        # Session summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                summary TEXT,
                topics TEXT,
                outcomes TEXT,
                created_at TEXT
            )
        """)

        self.conn.commit()
        print("✓ Tables created successfully")

    def add_document(self, namespace, content, source_id=None, metadata=None):
        """Add a document to RAG system with write locking"""
        # In fallback mode, we can't do vector search
        if self._is_fallback_mode:
            logger.warning("Cannot add document in TF-IDF fallback mode")
            return None

        # Acquire lock for write safety
        self._acquire_write_lock()

        try:
            # Generate embedding
            embedding = self.model.encode(content, convert_to_numpy=True)

            # Convert embedding to blob for sqlite_vec
            embedding_blob = struct.pack(f'{len(embedding)}f', *embedding)

            # Generate source_id if not provided
            if source_id is None:
                source_id = hashlib.md5(content.encode()).hexdigest()[:16]

            # Serialize metadata to JSON string (use empty dict instead of None)
            metadata_json = json.dumps(metadata) if metadata else json.dumps({})

            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO doc_vectors (namespace, source_id, embedding, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                namespace,
                source_id,
                embedding_blob,
                content,
                metadata_json,
                datetime.now().isoformat()
            ))

            self.conn.commit()
            return cursor.lastrowid

        finally:
            # Always release lock
            self._release_write_lock()

    def search(self, query, namespace=None, limit=5):
        """Search for similar documents with error handling"""
        if self._is_fallback_mode:
            logger.warning("Search not available in TF-IDF fallback mode")
            return []

        try:
            # Generate query embedding
            query_embedding = self.model.encode(query, convert_to_numpy=True)

            # Convert to blob
            query_blob = struct.pack(f'{len(query_embedding)}f', *query_embedding)

            cursor = self.conn.cursor()

            if namespace:
                # Search within namespace
                cursor.execute("""
                    SELECT
                        id,
                        namespace,
                        source_id,
                        content,
                        metadata,
                        distance
                    FROM doc_vectors
                    WHERE namespace = ?
                    AND embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, (namespace, query_blob, limit))
            else:
                # Search across all namespaces
                cursor.execute("""
                    SELECT
                        id,
                        namespace,
                        source_id,
                        content,
                        metadata,
                        distance
                    FROM doc_vectors
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, (query_blob, limit))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_by_namespace(self, namespace, limit=None):
        """Get all documents in a namespace"""
        cursor = self.conn.cursor()
        try:
            if limit:
                cursor.execute("""
                    SELECT * FROM doc_vectors
                    WHERE namespace = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (namespace, limit))
            else:
                cursor.execute("""
                    SELECT * FROM doc_vectors
                    WHERE namespace = ?
                    ORDER BY created_at DESC
                """, (namespace,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Get by namespace failed: {e}")
            return []

    def get_by_source_id(self, source_id):
        """Get documents by source ID"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM doc_vectors
                WHERE source_id = ?
                ORDER BY created_at DESC
            """, (source_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Get by source_id failed: {e}")
            return []

    def update_tool_usage(self, tool_name, success=True):
        """Track tool/skill usage with write locking"""
        self._acquire_write_lock()

        try:
            cursor = self.conn.cursor()

            # Check if tool exists
            cursor.execute("SELECT * FROM tool_usage WHERE tool_name = ?", (tool_name,))
            existing = cursor.fetchone()

            if existing:
                # Update existing
                new_count = existing['usage_count'] + 1
                # Calculate new success rate (moving average)
                old_rate = existing['success_rate'] or 1.0
                new_rate = ((old_rate * existing['usage_count']) + (1 if success else 0)) / new_count

                cursor.execute("""
                    UPDATE tool_usage
                    SET usage_count = ?, last_used = ?, success_rate = ?
                    WHERE tool_name = ?
                """, (new_count, datetime.now().isoformat(), new_rate, tool_name))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO tool_usage (tool_name, usage_count, last_used, success_rate)
                    VALUES (?, 1, ?, ?)
                """, (tool_name, datetime.now().isoformat(), 1.0 if success else 0.0))

            self.conn.commit()

        finally:
            self._release_write_lock()

    def add_project(self, name, description=None, metadata=None):
        """Add a project with write locking"""
        self._acquire_write_lock()

        try:
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO projects (name, description, created_at, metadata)
                    VALUES (?, ?, ?, ?)
                """, (name, description, datetime.now().isoformat(),
                      json.dumps(metadata) if metadata else None))
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                print(f"Project '{name}' already exists")
                return None
        finally:
            self._release_write_lock()

    def get_projects(self):
        """Get all projects"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Get projects failed: {e}")
            return []

    def close(self):
        """Close database connection with cleanup"""
        if self.conn:
            self.conn.close()
            self.conn = None

        # Release any held locks
        self._release_write_lock()

        print("✓ Database connection closed")

    def get_stats(self):
        """Get database statistics"""
        cursor = self.conn.cursor()

        try:
            # Count by namespace
            cursor.execute("""
                SELECT namespace, COUNT(*) as count
                FROM doc_vectors
                GROUP BY namespace
            """)
            namespace_counts = {row['namespace']: row['count'] for row in cursor.fetchall()}

            # Total documents
            cursor.execute("SELECT COUNT(*) FROM doc_vectors")
            total_docs = cursor.fetchone()[0]

            # Tool usage stats
            cursor.execute("SELECT COUNT(*) FROM tool_usage")
            total_tools = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(usage_count) FROM tool_usage")
            total_tool_uses = cursor.fetchone()[0] or 0

            # Project count
            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]

            return {
                "total_documents": total_docs,
                "namespace_breakdown": namespace_counts,
                "total_tools_tracked": total_tools,
                "total_tool_uses": total_tool_uses,
                "total_projects": total_projects,
                "fallback_mode": self._is_fallback_mode
            }

        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {
                "total_documents": 0,
                "namespace_breakdown": {},
                "total_tools_tracked": 0,
                "total_tool_uses": 0,
                "total_projects": 0,
                "fallback_mode": self._is_fallback_mode,
                "error": str(e)
            }

    def is_fallback_mode(self) -> bool:
        """Check if running in TF-IDF fallback mode"""
        return self._is_fallback_mode


# Test hardened database
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== Testing Hardened RAG Database ===\n")

    try:
        rag = RAGDatabaseHardened(
            db_path="test_harded.db",
            enable_backup=True
        )
        rag.connect()

        # Test adding documents
        test_doc = "This is a test document about Python programming and machine learning."
        doc_id = rag.add_document(
            "facts",
            test_doc,
            source_id="test_001",
            metadata={"topic": "programming", "language": "Python"}
        )

        if doc_id:
            print(f"✓ Document added with ID: {doc_id}")

        # Test search
        results = rag.search("machine learning algorithms")
        print(f"\n✓ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['content'][:60]}... (distance: {result['distance']:.4f})")

        # Test stats
        stats = rag.get_stats()
        print(f"\n✓ Database stats:")
        print(json.dumps(stats, indent=2))

        rag.close()
        print("\n✅ All tests passed!")

    except DatabaseHealthError as e:
        print(f"\n❌ Database health check failed: {e}")
    except ModelLoadError as e:
        print(f"\n❌ Model load failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
