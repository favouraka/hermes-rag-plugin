"""
RAG Database System with sqlite_vec
Supports 4 namespaces: sessions, projects, facts, tools_skills
"""

import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
from datetime import datetime
import hashlib
import struct

class RAGDatabase:
    def __init__(self, db_path="rag_data.db", model_path="sentence-transformers/all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.conn = None
        self.model = SentenceTransformer(model_path)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded with embedding dimension: {self.embedding_dim}")

    def connect(self):
        """Initialize database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like row access

        # Load sqlite_vec extension
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)

        # Create tables
        self._create_tables()
        print(f"Database connected: {self.db_path}")

    def _create_tables(self):
        """Create tables for the RAG system"""
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
        print("Tables created successfully")

    def add_document(self, namespace, content, source_id=None, metadata=None):
        """Add a document to the RAG system"""
        # Generate embedding
        embedding = self.model.encode(content, convert_to_numpy=True)

        # Convert embedding to blob for sqlite_vec
        embedding_blob = struct.pack(f'{len(embedding)}f', *embedding)

        # Generate source_id if not provided
        if source_id is None:
            source_id = hashlib.md5(content.encode()).hexdigest()[:16]

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO doc_vectors (namespace, source_id, embedding, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            namespace,
            source_id,
            embedding_blob,
            content,
            json.dumps(metadata) if metadata else None,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        return cursor.lastrowid

    def search(self, query, namespace=None, limit=5):
        """Search for similar documents"""
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

    def get_by_namespace(self, namespace, limit=None):
        """Get all documents in a namespace"""
        cursor = self.conn.cursor()
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

    def get_by_source_id(self, source_id):
        """Get documents by source ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM doc_vectors
            WHERE source_id = ?
            ORDER BY created_at DESC
        """, (source_id,))
        return [dict(row) for row in cursor.fetchall()]

    def update_tool_usage(self, tool_name, success=True):
        """Track tool/skill usage"""
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

    def add_project(self, name, description=None, metadata=None):
        """Add a project"""
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

    def get_projects(self):
        """Get all projects"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def get_stats(self):
        """Get database statistics"""
        cursor = self.conn.cursor()

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
            "total_projects": total_projects
        }

# Test the database
if __name__ == "__main__":
    rag = RAGDatabase()
    rag.connect()

    # Test adding documents
    test_doc = "This is a test document about Python programming and machine learning."
    rag.add_document("facts", test_doc, source_id="test_001",
                    metadata={"topic": "programming", "language": "Python"})

    # Test search
    results = rag.search("machine learning algorithms")
    print("\nSearch results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['content'][:100]}... (distance: {result['distance']:.4f})")

    # Test stats
    stats = rag.get_stats()
    print("\nDatabase stats:", json.dumps(stats, indent=2))

    rag.close()
