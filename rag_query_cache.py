"""
Query caching system for RAG searches.
Caches recent queries with TTL-based expiration.
"""

import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class CacheEntry:
    """A cache entry with TTL."""
    query: str
    results: List[Dict[str, Any]]
    timestamp: float
    ttl: float = 3600  # Default 1 hour TTL

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > (self.timestamp + self.ttl)

    @property
    def age(self) -> float:
        """Get age in seconds."""
        return time.time() - self.timestamp

    @property
    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.timestamp + self.ttl - time.time())


class QueryCache:
    """LRU cache for query results with TTL support."""

    def __init__(self, max_size: int = 100, default_ttl: float = 3600):
        """
        Initialize query cache.

        Args:
            max_size: Maximum number of entries to cache
            default_ttl: Default TTL in seconds (default: 3600 = 1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _hash_query(self, query: str, params: Dict[str, Any] = None) -> str:
        """
        Create a hash for the query.

        Args:
            query: Search query string
            params: Optional search parameters (limit, namespace, etc.)

        Returns:
            SHA256 hash of query + params
        """
        # Normalize query
        normalized = query.lower().strip()

        # Create hash with params
        data = {
            "query": normalized,
            "params": params or {}
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def get(self, query: str, params: Dict[str, Any] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached results for a query.

        Args:
            query: Search query string
            params: Optional search parameters

        Returns:
            Cached results if found and not expired, None otherwise
        """
        key = self._hash_query(query, params)

        # Check if entry exists
        if key not in self.cache:
            self.misses += 1
            return None

        # Check if expired
        entry = self.cache[key]
        if entry.is_expired:
            # Remove expired entry
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        self.hits += 1

        return entry.results.copy()

    def set(
        self,
        query: str,
        results: List[Dict[str, Any]],
        params: Dict[str, Any] = None,
        ttl: float = None
    ) -> bool:
        """
        Cache query results.

        Args:
            query: Search query string
            results: Search results to cache
            params: Optional search parameters
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully
        """
        # Don't cache empty results
        if not results:
            return False

        key = self._hash_query(query, params)

        # If full, remove oldest entry
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)  # Remove oldest

        # Add entry
        entry = CacheEntry(
            query=query,
            results=results.copy(),
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )
        self.cache[key] = entry

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)

        return True

    def invalidate(self, query: str, params: Dict[str, Any] = None) -> bool:
        """
        Invalidate a specific query cache entry.

        Args:
            query: Query to invalidate
            params: Optional parameters

        Returns:
            True if entry was removed, False if not found
        """
        key = self._hash_query(query, params)

        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries removed
        """
        count = len(self.cache)
        self.cache.clear()
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "default_ttl": self.default_ttl,
        }

    def get_entries_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get information about cached entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of entry info dictionaries
        """
        entries = []
        for key, entry in reversed(list(self.cache.items())):  # Most recent first
            if len(entries) >= limit:
                break

            entries.append({
                "query": entry.query[:60] + "..." if len(entry.query) > 60 else entry.query,
                "timestamp": entry.timestamp,
                "age": round(entry.age, 1),
                "remaining_ttl": round(entry.remaining_ttl, 1),
                "num_results": len(entry.results),
                "is_expired": entry.is_expired,
            })

        return entries


# Singleton instance
_global_cache: Optional[QueryCache] = None


def get_query_cache(max_size: int = 100, default_ttl: float = 3600) -> QueryCache:
    """
    Get the global query cache singleton.

    Args:
        max_size: Maximum cache size (only used on first call)
        default_ttl: Default TTL (only used on first call)

    Returns:
        QueryCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = QueryCache(max_size=max_size, default_ttl=default_ttl)

    return _global_cache


def demo_cache():
    """Demonstrate query cache."""
    print("\n=== Query Cache Demo ===\n")

    # Create cache
    cache = QueryCache(max_size=10, default_ttl=10)  # 10 second TTL for demo

    # Sample results
    sample_results = [
        {"doc_id": 1, "content": "database setup", "score": 0.85},
        {"doc_id": 2, "content": "API configuration", "score": 0.72},
    ]

    # Cache miss
    print("1. First query (cache miss):")
    result = cache.get("database setup")
    print(f"   Result: {result}")
    print(f"   Stats: {cache.get_stats()}")

    # Cache hit
    print("\n2. Cache and retrieve:")
    cache.set("database setup", sample_results)
    result = cache.get("database setup")
    print(f"   Result: {result}")
    print(f"   Stats: {cache.get_stats()}")

    # Multiple queries
    print("\n3. Add more queries:")
    cache.set("API design", sample_results)
    cache.set("memory management", sample_results)
    cache.set("authentication flow", sample_results)
    print(f"   Stats: {cache.get_stats()}")
    print(f"   Entries: {cache.get_entries_info(limit=3)}")

    # Wait for expiration (simulated)
    print("\n4. Simulate expiration:")
    expired = cache.cleanup_expired()
    print(f"   Expired entries: {expired}")
    print(f"   Stats: {cache.get_stats()}")

    # Clear cache
    print("\n5. Clear cache:")
    count = cache.clear()
    print(f"   Cleared {count} entries")
    print(f"   Stats: {cache.get_stats()}")


if __name__ == "__main__":
    demo_cache()
