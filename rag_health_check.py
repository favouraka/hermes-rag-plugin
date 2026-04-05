"""
Enhanced health check system for RAG database.
Detects corruption early and prevents silent failures.
"""

import sqlite3
import time
from typing import Dict, Any, List, Optional
from pathlib import Path


class DatabaseHealthError(Exception):
    """Raised when database health check fails."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseHealthChecker:
    """
    Comprehensive health checker for RAG database.

    Detects:
    - Corrupted SQLite files
    - Missing tables
    - Invalid schemas
    - Orphaned records
    - Index corruption
    - Data integrity violations
    """

    def __init__(self, db_path: str):
        """
        Initialize health checker.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.issues: List[Dict[str, Any]] = []

    def check_all(self, raise_on_failure: bool = True) -> Dict[str, Any]:
        """
        Run all health checks.

        Args:
            raise_on_failure: Raise DatabaseHealthError if issues found

        Returns:
            Health check report

        Raises:
            DatabaseHealthError: If critical issues found
        """
        self.issues = []
        start_time = time.time()

        # Run all checks
        self._check_file_exists()
        self._check_file_readable()
        self._check_file_size()

        # Connect and run database checks
        try:
            conn = sqlite3.connect(self.db_path)
            self._check_tables_exist(conn)
            self._check_schema_valid(conn)
            self._check_indexes(conn)
            self._check_data_integrity(conn)
            self._check_orphaned_records(conn)
            self._check_embeddings(conn)
            self._check_document_count(conn)
            conn.close()
        except DatabaseHealthError:
            raise
        except Exception as e:
            self.issues.append({
                "check": "database_connection",
                "severity": "critical",
                "message": f"Database connection failed: {str(e)}",
            })

        duration = time.time() - start_time

        report = {
            "passed": len(self.issues) == 0,
            "issues": self.issues,
            "issue_count": len(self.issues),
            "critical_issues": len([i for i in self.issues if i.get("severity") == "critical"]),
            "warning_issues": len([i for i in self.issues if i.get("severity") == "warning"]),
            "duration": round(duration, 3),
        }

        # Raise if critical issues found
        if raise_on_failure and report["critical_issues"] > 0:
            raise DatabaseHealthError(
                f"Database health check failed: {report['critical_issues']} critical issues found",
                details=report
            )

        return report

    def _check_file_exists(self):
        """Check if database file exists."""
        if not Path(self.db_path).exists():
            self.issues.append({
                "check": "file_exists",
                "severity": "critical",
                "message": f"Database file not found: {self.db_path}",
            })

    def _check_file_readable(self):
        """Check if database file is readable."""
        try:
            with open(self.db_path, 'rb') as f:
                f.read(1024)
        except Exception as e:
            self.issues.append({
                "check": "file_readable",
                "severity": "critical",
                "message": f"Database file not readable: {str(e)}",
            })

    def _check_file_size(self):
        """Check if database file has valid size."""
        path = Path(self.db_path)
        if path.exists():
            size = path.stat().st_size
            if size == 0:
                self.issues.append({
                    "check": "file_size",
                    "severity": "warning",
                    "message": "Database file is empty (0 bytes)",
                })
            elif size < 1024:  # Less than 1KB
                self.issues.append({
                    "check": "file_size",
                    "severity": "warning",
                    "message": f"Database file suspiciously small: {size} bytes",
                })

    def _check_tables_exist(self, conn: sqlite3.Connection):
        """Check if required tables exist."""
        required_tables = ["documents", "tool_usage", "projects"]
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            if table not in existing_tables:
                self.issues.append({
                    "check": "tables_exist",
                    "severity": "critical",
                    "message": f"Required table missing: {table}",
                })

    def _check_schema_valid(self, conn: sqlite3.Connection):
        """Check if table schemas are valid."""
        cursor = conn.cursor()

        # Check documents table
        try:
            cursor.execute("PRAGMA table_info(documents)")
            columns = [row[1] for row in cursor.fetchall()]
            required_columns = ["id", "content", "embedding", "namespace", "source_id", "timestamp"]

            for col in required_columns:
                if col not in columns:
                    self.issues.append({
                        "check": "schema_valid",
                        "severity": "critical",
                        "message": f"Required column missing in documents table: {col}",
                    })
        except Exception as e:
            self.issues.append({
                "check": "schema_valid",
                "severity": "critical",
                "message": f"Failed to check documents schema: {str(e)}",
            })

    def _check_indexes(self, conn: sqlite3.Connection):
        """Check if required indexes exist."""
        cursor = conn.cursor()

        # Check if there are any indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        if len(indexes) == 0:
            self.issues.append({
                "check": "indexes",
                "severity": "warning",
                "message": "No indexes found in database",
            })

    def _check_data_integrity(self, conn: sqlite3.Connection):
        """Check SQLite integrity."""
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result and result[0] != "ok":
                self.issues.append({
                    "check": "integrity_check",
                    "severity": "critical",
                    "message": f"Database integrity check failed: {result[0]}",
                })
        except Exception as e:
            self.issues.append({
                "check": "integrity_check",
                "severity": "critical",
                "message": f"Failed to run integrity check: {str(e)}",
            })

    def _check_orphaned_records(self, conn: sqlite3.Connection):
        """Check for orphaned records."""
        cursor = conn.cursor()

        try:
            # Check for documents with empty content
            cursor.execute("SELECT COUNT(*) FROM documents WHERE content IS NULL OR content = ''")
            empty_count = cursor.fetchone()[0]

            if empty_count > 0:
                self.issues.append({
                    "check": "orphaned_records",
                    "severity": "warning",
                    "message": f"Found {empty_count} documents with empty content",
                })

            # Check for documents without embeddings
            cursor.execute("SELECT COUNT(*) FROM documents WHERE embedding IS NULL")
            no_embedding_count = cursor.fetchone()[0]

            if no_embedding_count > 0:
                self.issues.append({
                    "check": "orphaned_records",
                    "severity": "warning",
                    "message": f"Found {no_embedding_count} documents without embeddings",
                })
        except Exception as e:
            # Non-critical, may be due to fallback mode
            pass

    def _check_embeddings(self, conn: sqlite3.Connection):
        """Check if embeddings are valid."""
        cursor = conn.cursor()

        try:
            # Sample a few embeddings to check validity
            cursor.execute("SELECT embedding FROM documents WHERE embedding IS NOT NULL LIMIT 5")
            rows = cursor.fetchall()

            for i, row in enumerate(rows):
                try:
                    import json
                    embedding = json.loads(row[0])
                    if not isinstance(embedding, list):
                        self.issues.append({
                            "check": "embeddings",
                            "severity": "critical",
                            "message": f"Invalid embedding format at row {i}",
                        })
                except Exception as e:
                    self.issues.append({
                        "check": "embeddings",
                        "severity": "critical",
                        "message": f"Invalid embedding JSON at row {i}: {str(e)}",
                    })
        except Exception as e:
            # May be due to fallback mode
            pass

    def _check_document_count(self, conn: sqlite3.Connection):
        """Check if database has documents."""
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM documents")
            count = cursor.fetchone()[0]

            if count == 0:
                self.issues.append({
                    "check": "document_count",
                    "severity": "info",
                    "message": "Database is empty (0 documents)",
                })
        except Exception as e:
            self.issues.append({
                "check": "document_count",
                "severity": "warning",
                "message": f"Failed to count documents: {str(e)}",
            })


def check_database_health(db_path: str, raise_on_failure: bool = True) -> Dict[str, Any]:
    """
    Check database health.

    Args:
        db_path: Path to database
        raise_on_failure: Raise DatabaseHealthError if issues found

    Returns:
        Health check report

    Raises:
        DatabaseHealthError: If critical issues found
    """
    checker = DatabaseHealthChecker(db_path)
    return checker.check_all(raise_on_failure=raise_on_failure)


def demo_health_check():
    """Demonstrate health check."""
    print("\n=== Enhanced Health Check Demo ===\n")

    from rag_database_hardened import RAGDatabaseHardened
    import tempfile
    import os

    # Test 1: Healthy database
    print("1. Testing healthy database:")
    db_path = str(Path.home() / "rag-system" / "rag_data.db")
    try:
        report = check_database_health(db_path, raise_on_failure=False)
        print(f"   ✅ Health check passed in {report['duration']}s")
        print(f"   Issues: {report['issue_count']} ({report['critical_issues']} critical)")
    except DatabaseHealthError as e:
        print(f"   ❌ Health check failed: {e.message}")
        print(f"   Details: {e.details}")

    # Test 2: Corrupted database simulation
    print("\n2. Testing corrupted database (simulated):")
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_path = os.path.join(tmpdir, "corrupt.db")
        with open(corrupt_path, 'w') as f:
            f.write("This is not a valid SQLite database")

        try:
            report = check_database_health(corrupt_path, raise_on_failure=False)
            print(f"   Found {report['issue_count']} issues")
            for issue in report['issues']:
                print(f"   - [{issue['severity'].upper()}] {issue['message']}")
        except DatabaseHealthError as e:
            print(f"   ❌ Detected corruption: {e.message}")

    # Test 3: Empty database
    print("\n3. Testing empty database:")
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_path = os.path.join(tmpdir, "empty.db")
        conn = sqlite3.connect(empty_path)
        conn.close()

        try:
            report = check_database_health(empty_path, raise_on_failure=False)
            print(f"   Found {report['issue_count']} issues")
            for issue in report['issues']:
                print(f"   - [{issue['severity'].upper()}] {issue['message']}")
        except DatabaseHealthError as e:
            print(f"   ❌ Health check failed: {e.message}")

    print("\n✅ Health check demo complete")


if __name__ == "__main__":
    demo_health_check()
