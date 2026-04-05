"""
Performance optimization integration for RAG system.
Combines connection pooling, profiling, and metrics.
"""

from typing import Dict, Any, List, Optional
from contextlib import contextmanager
import logging

from rag_connection_pool import ConnectionPool, ConnectionConfig, PooledConnection
from rag_profiler import RAGProfiler, HotPath, get_profiler
from rag_performance_metrics import PerformanceMetrics, get_metrics

logger = logging.getLogger(__name__)


class RAGPerformanceOptimizer:
    """
    Performance optimization suite for RAG system.

    Combines:
    - Connection pooling
    - Profiling and hot path detection
    - Comprehensive metrics

    Usage:
        optimizer = RAGPerformanceOptimizer(config)
        with optimizer.get_connection() as pooled:
            # Use connection
            pass
    """

    def __init__(
        self,
        db_path: str,
        pool_config: Optional[ConnectionConfig] = None,
        enable_profiling: bool = True,
        enable_metrics: bool = True,
    ):
        """
        Initialize performance optimizer.

        Args:
            db_path: Path to database
            pool_config: Connection pool configuration (uses defaults if None)
            enable_profiling: Enable profiling
            enable_metrics: Enable performance metrics
        """
        self.db_path = db_path
        self.enable_profiling = enable_profiling
        self.enable_metrics = enable_metrics

        # Initialize components
        if pool_config is None:
            pool_config = ConnectionConfig(
                db_path=db_path,
                pool_size=5,
                max_overflow=3,
                recycle=3600,
            )

        self.connection_pool = ConnectionPool(pool_config)
        self.profiler = get_profiler() if enable_profiling else None
        self.metrics = get_metrics() if enable_metrics else None

        logger.info("Performance optimizer initialized")

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Yields:
            PooledConnection wrapper

        Example:
            with optimizer.get_connection() as pooled:
                cursor = pooled.conn.cursor()
                cursor.execute("SELECT * FROM documents")
        """
        if self.metrics:
            with self.metrics.time_operation("connection_checkout"):
                with self.connection_pool.get_connection() as pooled:
                    yield pooled
        else:
            with self.connection_pool.get_connection() as pooled:
                yield pooled

    def profile_search(self, func):
        """
        Decorator to profile search functions.

        Args:
            func: Search function to profile

        Returns:
            Wrapped function with profiling
        """
        if not self.profiler:
            return func

        def wrapper(*args, **kwargs):
            name = f"{func.__name__}_search"
            with self.profiler.profile(name):
                return func(*args, **kwargs)

        return wrapper

    def track_search_latency(self, duration: float, **metadata):
        """
        Track search latency.

        Args:
            duration: Search duration in seconds
            **metadata: Additional metadata (query_type, namespace, etc.)
        """
        if self.metrics:
            self.metrics.record_latency("search", duration, **metadata)
            self.metrics.record_throughput("search", 1)

    def track_embedding_latency(self, duration: float, **metadata):
        """
        Track embedding generation latency.

        Args:
            duration: Embedding duration in seconds
            **metadata: Additional metadata
        """
        if self.metrics:
            self.metrics.record_latency("embedding", duration, **metadata)
            self.metrics.record_throughput("embedding", 1)

    def track_database_operation(self, operation: str, duration: float, **metadata):
        """
        Track database operation latency.

        Args:
            operation: Operation name (insert, select, update, etc.)
            duration: Duration in seconds
            **metadata: Additional metadata
        """
        if self.metrics:
            self.metrics.record_latency(f"database_{operation}", duration, **metadata)

    def get_hot_paths(self, threshold: float = 0.1) -> List[HotPath]:
        """
        Get identified hot paths.

        Args:
            threshold: Time threshold (percentage of total time)

        Returns:
            List of HotPath objects
        """
        if not self.profiler:
            return []
        return self.profiler.identify_hot_paths(threshold)

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.

        Returns:
            Dictionary with performance data
        """
        report = {
            "connection_pool": self.connection_pool.get_stats(),
            "pool_health": self.connection_pool.health_check(),
        }

        if self.profiler:
            report["profiler"] = self.profiler.get_summary()

        if self.metrics:
            report["metrics"] = self.metrics.get_report()

        return report

    def print_performance_report(self):
        """Print formatted performance report."""
        print("\n=== RAG Performance Report ===\n")

        # Connection pool
        print("1. Connection Pool:")
        pool_stats = self.connection_pool.get_stats()
        print(f"   Pool size: {pool_stats['pool_size']}")
        print(f"   Pool available: {pool_stats['pool_available']}")
        print(f"   Overflow available: {pool_stats['overflow_available']}")
        print(f"   In use: {pool_stats['in_use']}")
        print(f"   Total created: {pool_stats['total_created']}")
        print(f"   Total reused: {pool_stats['total_reused']}")
        print(f"   Reuse rate: {pool_stats['reuse_rate']:.1f}%")
        print(f"   Avg checkout: {pool_stats['avg_checkout_time']*1000:.1f}ms")

        # Pool health
        print("\n2. Pool Health:")
        health = self.connection_pool.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Healthy: {health['healthy']}/{health['total']}")
        print(f"   Health %: {health['health_percentage']:.1f}%")

        # Hot paths
        if self.profiler:
            print("\n3. Hot Paths:")
            hot_paths = self.get_hot_paths(threshold=0.05)
            if hot_paths:
                for i, hot_path in enumerate(hot_paths[:5], 1):
                    status = "🔥" if hot_path.is_critical else "⚠️"
                    print(f"   {i}. {status} {hot_path.function_name}")
                    print(f"      Time: {hot_path.total_time*1000:.1f}ms")
                    print(f"      Calls: {hot_path.call_count}")
                    print(f"      Suggestion: {hot_path.suggestion}")
            else:
                print("   No hot paths identified")

        # Metrics
        if self.metrics:
            print("\n4. Performance Metrics:")
            self.metrics.print_report(metric_names=[
                "search_latency",
                "embedding_latency",
                "database_select_latency",
            ])

        print()

    def optimize_database(self):
        """
        Run database optimizations.

        Returns:
            Dictionary with optimization results
        """
        results = {}

        with self.get_connection() as pooled:
            cursor = pooled.conn.cursor()

            # Analyze tables
            cursor.execute("ANALYZE")
            results["analyzed"] = True

            # Reindex
            cursor.execute("REINDEX")
            results["reindexed"] = True

            # Vacuum
            try:
                cursor.execute("VACUUM")
                results["vacuumed"] = True
            except Exception as e:
                results["vacuumed"] = False
                results["vacuum_error"] = str(e)

            pooled.conn.commit()

        logger.info("Database optimizations completed")
        return results

    def close(self):
        """Close all resources."""
        self.connection_pool.close_all()
        logger.info("Performance optimizer closed")


# Integration with RAGDatabaseHardened
def patch_rag_database_with_performance(rag_db, optimizer: RAGPerformanceOptimizer):
    """
    Patch RAGDatabaseHardened with performance tracking.

    Args:
        rag_db: RAGDatabaseHardened instance
        optimizer: RAGPerformanceOptimizer instance
    """
    import time

    # Save original methods
    original_search = rag_db.search
    original_add_document = rag_db.add_document

    # Patched search with profiling
    def search_with_performance(query, namespace=None, limit=5):
        start_time = time.time()

        results = original_search(query, namespace=namespace, limit=limit)

        duration = time.time() - start_time
        optimizer.track_search_latency(duration, query_type="neural")

        return results

    # Patched add_document with profiling
    def add_document_with_performance(namespace, content, source_id=None, metadata=None):
        start_time = time.time()

        result = original_add_document(namespace, content, source_id, metadata)

        duration = time.time() - start_time
        optimizer.track_database_operation("insert", duration, namespace=namespace)

        return result

    # Apply patches
    rag_db.search = search_with_performance
    rag_db.add_document = add_document_with_performance

    logger.info("RAG database patched with performance tracking")


def demo_performance_integration():
    """Demonstrate performance integration."""
    print("\n=== Performance Integration Demo ===\n")

    import tempfile
    import os
    import time

    # Create test database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Initialize optimizer
        optimizer = RAGPerformanceOptimizer(
            db_path=db_path,
            enable_profiling=True,
            enable_metrics=True,
        )

        print("1. Performance optimizer created:")
        print(f"   DB path: {db_path}")
        print(f"   Profiling: {optimizer.enable_profiling}")
        print(f"   Metrics: {optimizer.enable_metrics}")

        # Create tables
        print("\n2. Creating tables:")
        with optimizer.get_connection() as pooled:
            cursor = pooled.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test (
                    id INTEGER PRIMARY KEY,
                    content TEXT,
                    created_at TEXT
                )
            """)
            pooled.conn.commit()
            print("   ✓ Tables created")

        # Simulate operations
        print("\n3. Simulating operations:")
        for i in range(20):
            with optimizer.profiler.profile("insert_test"):
                with optimizer.get_connection() as pooled:
                    cursor = pooled.conn.cursor()
                    cursor.execute(
                        "INSERT INTO test (content, created_at) VALUES (?, ?)",
                        (f"test_{i}", time.time())
                    )
                    pooled.conn.commit()

                    # Track latency
                    optimizer.track_database_operation("insert", 0.001)

            if i % 5 == 0:
                print(f"   Inserted {i+1} records")

        # Simulate searches
        print("\n4. Simulating searches:")
        for i in range(10):
            start_time = time.time()

            with optimizer.get_connection() as pooled:
                cursor = pooled.conn.cursor()
                cursor.execute("SELECT * FROM test LIMIT 5")
                results = cursor.fetchall()

            duration = time.time() - start_time
            optimizer.track_search_latency(duration, query_type="select")

            time.sleep(0.01)  # Simulate work

        print(f"   Completed 10 searches")

        # Show report
        print("\n5. Performance Report:")
        optimizer.print_performance_report()

        # Show hot paths
        print("\n6. Hot Paths Analysis:")
        optimizer.profiler.print_hot_paths(threshold=0.05)

        # Show metrics
        print("\n7. Metrics Summary:")
        if optimizer.metrics:
            import json
            report = optimizer.metrics.get_report()
            print(json.dumps(report, indent=2, default=str)[:600])

        # Close
        print("\n8. Cleaning up:")
        optimizer.close()
        print("   ✓ Optimizer closed")

    print("\n✅ Performance integration demo complete")


if __name__ == "__main__":
    demo_performance_integration()
