"""
SQLite connection pool for RAG system.
Manages connection lifecycle and provides connection reuse.
"""

import sqlite3
import threading
import time
import logging
from queue import Queue, Empty, Full
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for connection pool."""
    db_path: str
    pool_size: int = 5
    max_overflow: int = 3
    timeout: float = 30.0
    recycle: int = 3600  # Recycle connections after this many seconds
    check_same_thread: bool = False
    enable_wal: bool = True
    synchronous: str = "NORMAL"
    busy_timeout: int = 5000


@dataclass
class PooledConnection:
    """A pooled connection wrapper."""
    conn: sqlite3.Connection
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    in_use: bool = False
    use_count: int = 0
    is_valid: bool = True


class ConnectionPool:
    """
    SQLite connection pool with lifecycle management.

    Features:
    - Connection pooling and reuse
    - Connection recycling (prevent stale connections)
    - Overflow support
    - Thread-safe
    - Health checks
    - Statistics tracking
    """

    def __init__(self, config: ConnectionConfig):
        """
        Initialize connection pool.

        Args:
            config: Connection configuration
        """
        self.config = config
        self._pool: Queue[PooledConnection] = Queue(maxsize=config.pool_size)
        self._overflow: Queue[PooledConnection] = Queue(maxsize=config.max_overflow)
        self._lock = threading.Lock()
        self._all_connections: list[PooledConnection] = []
        self._created_count = 0
        self._reused_count = 0

        # Statistics
        self.stats = {
            "created": 0,
            "reused": 0,
            "recycled": 0,
            "closed": 0,
            "checkout_time_total": 0.0,
            "checkout_count": 0,
        }

        # Pre-create connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Pre-create initial pool connections."""
        for _ in range(self.config.pool_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn, block=False)
                logger.debug(f"Pre-created connection: {conn.created_at}")
            except Full:
                logger.warning("Pool full during initialization")
                break

    def _create_connection(self) -> PooledConnection:
        """
        Create a new SQLite connection.

        Returns:
            PooledConnection wrapper
        """
        conn = sqlite3.connect(
            self.config.db_path,
            timeout=self.config.timeout,
            check_same_thread=self.config.check_same_thread,
        )
        conn.row_factory = sqlite3.Row

        # Enable WAL mode if configured
        if self.config.enable_wal:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA synchronous={self.config.synchronous}")
            conn.execute(f"PRAGMA busy_timeout={self.config.busy_timeout}")

        # Load sqlite_vec extension
        try:
            import sqlite_vec
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        except Exception as e:
            logger.warning(f"Failed to load sqlite_vec: {e}")

        pooled = PooledConnection(conn=conn)
        self._all_connections.append(pooled)
        self.stats["created"] += 1
        self._created_count += 1

        logger.debug(f"Created new connection (total: {self._created_count})")
        return pooled

    def _validate_connection(self, pooled: PooledConnection) -> bool:
        """
        Validate that a connection is still usable.

        Args:
            pooled: Pooled connection to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try a simple query
            pooled.conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Connection validation failed: {e}")
            pooled.is_valid = False
            return False

    def _recycle_if_needed(self, pooled: PooledConnection) -> bool:
        """
        Recycle connection if it's too old.

        Args:
            pooled: Pooled connection to check

        Returns:
            True if recycled, False otherwise
        """
        age = time.time() - pooled.created_at
        if age > self.config.recycle:
            logger.debug(f"Recycling old connection (age: {age:.1f}s)")
            pooled.is_valid = False
            self.stats["recycled"] += 1
            return True
        return False

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Yields:
            PooledConnection wrapper

        Example:
            with pool.get_connection() as pooled:
                cursor = pooled.conn.cursor()
                cursor.execute("SELECT * FROM documents")
        """
        pooled = self._checkout()
        start_time = time.time()

        try:
            yield pooled
        finally:
            elapsed = time.time() - start_time
            self._checkin(pooled, elapsed)

    def _checkout(self) -> PooledConnection:
        """
        Checkout a connection from the pool.

        Returns:
            PooledConnection wrapper
        """
        start_time = time.time()

        # Try to get from main pool
        try:
            pooled = self._pool.get(block=True, timeout=self.config.timeout)
            pooled.in_use = True
            pooled.last_used = time.time()
            pooled.use_count += 1
            self.stats["reused"] += 1
            self._reused_count += 1

            # Validate and recycle if needed
            if not self._validate_connection(pooled):
                pooled.conn.close()
                pooled = self._create_connection()

            self._recycle_if_needed(pooled)

            elapsed = time.time() - start_time
            self.stats["checkout_time_total"] += elapsed
            self.stats["checkout_count"] += 1

            logger.debug(f"Checkout from pool (age: {time.time() - pooled.created_at:.1f}s)")
            return pooled

        except Empty:
            pass

        # Pool exhausted, try overflow
        try:
            with self._lock:
                pooled = self._overflow.get(block=True, timeout=self.config.timeout)
                pooled.in_use = True
                pooled.last_used = time.time()
                pooled.use_count += 1

                elapsed = time.time() - start_time
                self.stats["checkout_time_total"] += elapsed
                self.stats["checkout_count"] += 1

                logger.debug("Checkout from overflow")
                return pooled

        except Empty:
            pass

        # Create new connection if under limit
        with self._lock:
            total_conns = (
                self._pool.qsize() +
                self._overflow.qsize() +
                sum(1 for p in self._all_connections if p.in_use)
            )
            max_conns = self.config.pool_size + self.config.max_overflow

            if total_conns < max_conns:
                pooled = self._create_connection()
                pooled.in_use = True
                pooled.last_used = time.time()

                elapsed = time.time() - start_time
                self.stats["checkout_time_total"] += elapsed
                self.stats["checkout_count"] += 1

                logger.debug("Created new connection for overflow")
                return pooled

        # All connections exhausted
        raise RuntimeError(
            f"Connection pool exhausted (max: {self.config.pool_size + self.config.max_overflow})"
        )

    def _checkin(self, pooled: PooledConnection, elapsed: float):
        """
        Return a connection to the pool.

        Args:
            pooled: Pooled connection to return
            elapsed: Time the connection was in use
        """
        pooled.in_use = False
        pooled.last_used = time.time()

        # Close if invalid
        if not pooled.is_valid:
            pooled.conn.close()
            self.stats["closed"] += 1
            return

        # Return to appropriate pool
        try:
            self._pool.put(pooled, block=False)
        except Full:
            try:
                self._overflow.put(pooled, block=False)
            except Full:
                # Both pools full, close connection
                pooled.conn.close()
                self.stats["closed"] += 1
                logger.debug("Connection closed (pools full)")

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for pooled in self._all_connections:
                try:
                    pooled.conn.close()
                    logger.debug(f"Closed connection (use count: {pooled.use_count})")
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            self._all_connections.clear()
            logger.info(f"Closed all {self._created_count} connections")

    def get_stats(self) -> dict:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool stats
        """
        avg_checkout_time = (
            self.stats["checkout_time_total"] / self.stats["checkout_count"]
            if self.stats["checkout_count"] > 0
            else 0
        )

        in_use_count = sum(1 for p in self._all_connections if p.in_use)

        return {
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "total_limit": self.config.pool_size + self.config.max_overflow,
            "pool_available": self._pool.qsize(),
            "overflow_available": self._overflow.qsize(),
            "in_use": in_use_count,
            "total_created": self.stats["created"],
            "total_reused": self.stats["reused"],
            "total_recycled": self.stats["recycled"],
            "total_closed": self.stats["closed"],
            "reuse_rate": (
                self.stats["reused"] / (self.stats["created"] + self.stats["reused"]) * 100
                if (self.stats["created"] + self.stats["reused"]) > 0
                else 0
            ),
            "avg_checkout_time": round(avg_checkout_time, 3),
            "checkout_count": self.stats["checkout_count"],
        }

    def health_check(self) -> dict:
        """
        Check pool health.

        Returns:
            Dictionary with health status
        """
        healthy_count = 0
        unhealthy_count = 0

        with self._lock:
            for pooled in self._all_connections:
                if pooled.is_valid and self._validate_connection(pooled):
                    healthy_count += 1
                else:
                    unhealthy_count += 1

        total = healthy_count + unhealthy_count
        health_pct = (healthy_count / total * 100) if total > 0 else 0

        return {
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "total": total,
            "health_percentage": round(health_pct, 2),
            "status": "healthy" if health_pct > 90 else "degraded" if health_pct > 50 else "unhealthy",
        }


def demo_connection_pool():
    """Demonstrate connection pool."""
    print("\n=== Connection Pool Demo ===\n")

    import tempfile
    import os

    # Create test database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Create pool
        config = ConnectionConfig(
            db_path=db_path,
            pool_size=3,
            max_overflow=2,
            recycle=10,  # 10 second recycle for demo
        )
        pool = ConnectionPool(config)

        print("1. Pool created:")
        print(f"   Pool size: {pool.config.pool_size}")
        print(f"   Max overflow: {pool.config.max_overflow}")
        print(f"   Stats: {pool.get_stats()}")

        # Create tables
        print("\n2. Creating tables:")
        with pool.get_connection() as pooled:
            cursor = pooled.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
            """)
            pooled.conn.commit()
            print("   ✓ Tables created")

        # Insert data
        print("\n3. Inserting data:")
        with pool.get_connection() as pooled:
            cursor = pooled.conn.cursor()
            cursor.execute("INSERT INTO test (value) VALUES (?)", ("test1",))
            cursor.execute("INSERT INTO test (value) VALUES (?)", ("test2",))
            pooled.conn.commit()
            print("   ✓ Data inserted")

        # Query data (multiple times to show reuse)
        print("\n4. Querying data (demonstrating reuse):")
        for i in range(5):
            with pool.get_connection() as pooled:
                cursor = pooled.conn.cursor()
                cursor.execute("SELECT * FROM test")
                results = cursor.fetchall()
                print(f"   Query {i+1}: {len(results)} rows (conn age: {time.time() - pooled.created_at:.1f}s)")

        # Show stats
        print("\n5. Pool statistics:")
        stats = pool.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Health check
        print("\n6. Health check:")
        health = pool.health_check()
        for key, value in health.items():
            print(f"   {key}: {value}")

        # Close pool
        print("\n7. Closing pool:")
        pool.close_all()
        print("   ✓ All connections closed")

    print("\n✅ Connection pool demo complete")


if __name__ == "__main__":
    demo_connection_pool()
