"""
Profiling and hot path optimization for RAG system.
Identifies performance bottlenecks and provides optimization insights.
"""

import cProfile
import pstats
import time
import functools
import logging
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ProfileStats:
    """Statistics for a single profile run."""
    function_name: str
    calls: int
    total_time: float
    per_call: float
    cumulative_time: float
    per_call_cumulative: float


@dataclass
class HotPath:
    """Identified hot path with optimization suggestions."""
    function_name: str
    total_time: float
    call_count: int
    avg_time: float
    is_critical: bool
    suggestion: str


class RAGProfiler:
    """
    Profiler for identifying hot paths and bottlenecks.

    Features:
    - Function-level timing
    - Hot path identification
    - cProfile integration
    - Optimization suggestions
    - Call tree analysis
    """

    def __init__(self):
        """Initialize profiler."""
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.profiler: Optional[cProfile.Profile] = None
        self._last_stats: Optional[pstats.Stats] = None

    @contextmanager
    def profile(self, name: str):
        """
        Profile a block of code.

        Args:
            name: Name for this profile run

        Example:
            with profiler.profile("search_query"):
                results = rag_db.search(query)
        """
        start_time = time.perf_counter()
        self.call_counts[name] += 1

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            self.timings[name].append(elapsed)

    def time_function(self, func: Callable) -> Callable:
        """
        Decorator to time a function.

        Args:
            func: Function to time

        Returns:
            Wrapped function with timing

        Example:
            @profiler.time_function
            def search(self, query):
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.profile(func.__name__):
                return func(*args, **kwargs)

        return wrapper

    def time_method(self, cls_method: Callable) -> Callable:
        """
        Decorator to time a class method.

        Args:
            cls_method: Method to time

        Returns:
            Wrapped method with timing
        """
        @functools.wraps(cls_method)
        def wrapper(self, *args, **kwargs):
            # Use full qualified name
            name = f"{self.__class__.__name__}.{cls_method.__name__}"
            with self.profile(name):
                return cls_method(self, *args, **kwargs)

        return wrapper

    def start_cprofile(self):
        """Start cProfile profiling."""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        logger.debug("cProfile started")

    def stop_cprofile(self) -> pstats.Stats:
        """
        Stop cProfile profiling and get results.

        Returns:
            pstats.Stats object with profiling data
        """
        if self.profiler:
            self.profiler.disable()
            logger.debug("cProfile stopped")
            stats = pstats.Stats(self.profiler)
            self.profiler = None
            return stats
        raise RuntimeError("cProfile not started")

    @contextmanager
    def cprofile_context(self, sort_by: str = "cumulative"):
        """
        Context manager for cProfile.

        Args:
            sort_by: How to sort results (cumulative, time, calls)

        Example:
            with profiler.cprofile_context() as stats:
                rag_db.search(query)
            stats.print_stats(10)
        """
        self.start_cprofile()
        stats = None
        try:
            yield
        finally:
            stats = self.stop_cprofile()
            if stats:
                stats.sort_stats(sort_by)
                # Store stats for demo
                self._last_stats = stats

    def get_timings(self, name: str = None) -> Dict[str, Dict[str, float]]:
        """
        Get timing statistics.

        Args:
            name: Optional function name to filter

        Returns:
            Dictionary with timing statistics
        """
        results = {}

        for func_name, timings in self.timings.items():
            if name and func_name != name:
                continue

            if not timings:
                continue

            timings_sorted = sorted(timings)

            results[func_name] = {
                "count": len(timings),
                "total": sum(timings),
                "avg": sum(timings) / len(timings),
                "min": timings_sorted[0],
                "max": timings_sorted[-1],
                "median": timings_sorted[len(timings) // 2],
                "p95": timings_sorted[int(len(timings) * 0.95)] if len(timings) > 20 else timings_sorted[-1],
                "p99": timings_sorted[int(len(timings) * 0.99)] if len(timings) > 100 else timings_sorted[-1],
            }

        return results

    def identify_hot_paths(self, threshold: float = 0.1) -> List[HotPath]:
        """
        Identify hot paths (functions taking > threshold of total time).

        Args:
            threshold: Time threshold (percentage of total time)

        Returns:
            List of HotPath objects
        """
        timings = self.get_timings()

        # Calculate total time
        total_time = sum(t["total"] for t in timings.values())

        # Identify hot paths
        hot_paths = []
        for func_name, stats in timings.items():
            time_pct = stats["total"] / total_time

            if time_pct > threshold:
                is_critical = time_pct > 0.5 or stats["p99"] > 1.0

                # Generate suggestion
                suggestion = self._generate_optimization_suggestion(
                    func_name, stats, time_pct
                )

                hot_paths.append(HotPath(
                    function_name=func_name,
                    total_time=stats["total"],
                    call_count=stats["count"],
                    avg_time=stats["avg"],
                    is_critical=is_critical,
                    suggestion=suggestion,
                ))

        # Sort by total time (descending)
        hot_paths.sort(key=lambda x: x.total_time, reverse=True)

        return hot_paths

    def _generate_optimization_suggestion(
        self,
        func_name: str,
        stats: Dict[str, float],
        time_pct: float
    ) -> str:
        """Generate optimization suggestion based on stats."""
        suggestions = []

        # High average time
        if stats["avg"] > 0.1:
            suggestions.append("Consider caching results")

        # High variance
        variance = stats["max"] - stats["min"]
        if variance > stats["avg"] * 2:
            suggestions.append("High variance - check for blocking operations")

        # Many calls
        if stats["count"] > 100:
            suggestions.append("High call count - consider batching")

        # Function-specific suggestions
        if "search" in func_name.lower():
            suggestions.append("Use query caching for repeated searches")
            suggestions.append("Consider parallel searches for multiple queries")

        elif "embedding" in func_name.lower():
            suggestions.append("Batch embeddings for better throughput")
            suggestions.append("Consider model quantization")

        elif "database" in func_name.lower() or "db" in func_name.lower():
            suggestions.append("Use connection pooling")
            suggestions.append("Add indexes for frequent queries")

        elif "serialize" in func_name.lower() or "json" in func_name.lower():
            suggestions.append("Consider faster serialization (msgpack, pickle)")

        # Priority based on time percentage
        if time_pct > 0.5:
            suggestions.insert(0, "CRITICAL PATH - optimize immediately")
        elif time_pct > 0.2:
            suggestions.insert(0, "Hot path - high priority")

        return " | ".join(suggestions) if suggestions else "No obvious optimizations"

    def get_call_tree(self, depth: int = 3) -> Dict[str, Any]:
        """
        Get call tree from cProfile.

        Args:
            depth: Maximum depth to display

        Returns:
            Dictionary representing call tree
        """
        if not self.profiler:
            raise RuntimeError("No cProfile data available. Use cprofile_context().")

        stats = pstats.Stats(self.profiler)
        stats.sort_stats("cumulative")

        # Build call tree (simplified)
        tree = {}

        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            name = func[2] if len(func) > 2 else str(func)
            tree[name] = {
                "calls": cc,
                "total_time": tt,
                "cumulative_time": ct,
            }

        return tree

    def print_hot_paths(self, threshold: float = 0.1):
        """
        Print hot paths analysis.

        Args:
            threshold: Time threshold (percentage of total time)
        """
        hot_paths = self.identify_hot_paths(threshold)

        print("\n=== Hot Paths Analysis ===\n")

        if not hot_paths:
            print("No hot paths found")
            return

        for i, hot_path in enumerate(hot_paths, 1):
            status = "🔥 CRITICAL" if hot_path.is_critical else "⚠️ HOT"
            print(f"{i}. {status}: {hot_path.function_name}")
            print(f"   Total time: {hot_path.total_time*1000:.1f}ms")
            print(f"   Calls: {hot_path.call_count}")
            print(f"   Avg per call: {hot_path.avg_time*1000:.1f}ms")
            print(f"   Suggestion: {hot_path.suggestion}")
            print()

    def print_timings(self, name: str = None, limit: int = 10):
        """
        Print timing statistics.

        Args:
            name: Optional function name to filter
            limit: Maximum number of entries to show
        """
        timings = self.get_timings(name)

        if not timings:
            print("No timing data available")
            return

        # Sort by total time
        sorted_timings = sorted(
            timings.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:limit]

        print("\n=== Timing Statistics ===\n")

        for func_name, stats in sorted_timings:
            print(f"{func_name}:")
            print(f"  Calls: {stats['count']}")
            print(f"  Total: {stats['total']*1000:.1f}ms")
            print(f"  Avg: {stats['avg']*1000:.1f}ms")
            print(f"  Min: {stats['min']*1000:.1f}ms")
            print(f"  Max: {stats['max']*1000:.1f}ms")
            print(f"  Median: {stats['median']*1000:.1f}ms")
            print(f"  P95: {stats['p95']*1000:.1f}ms")
            print()

    def reset(self):
        """Reset all profiling data."""
        self.timings.clear()
        self.call_counts.clear()
        self.profiler = None
        logger.debug("Profiler reset")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get profiler summary.

        Returns:
            Dictionary with profiler summary
        """
        timings = self.get_timings()

        total_calls = sum(stats["count"] for stats in timings.values())
        total_time = sum(stats["total"] for stats in timings.values())

        return {
            "functions_profiled": len(timings),
            "total_calls": total_calls,
            "total_time": total_time,
            "avg_function_time": total_time / len(timings) if timings else 0,
            "hot_paths_count": len(self.identify_hot_paths(0.1)),
        }


# Global profiler instance
_global_profiler: Optional[RAGProfiler] = None


def get_profiler() -> RAGProfiler:
    """Get global profiler singleton."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = RAGProfiler()
    return _global_profiler


def demo_profiler():
    """Demonstrate profiler."""
    print("\n=== Profiler Demo ===\n")

    profiler = RAGProfiler()

    # Simulate some work
    def expensive_operation():
        time.sleep(0.01)
        return "result"

    def quick_operation():
        time.sleep(0.001)
        return "quick"

    def search_function(query):
        with profiler.profile("search_function"):
            result1 = expensive_operation()
            result2 = quick_operation()
            return result1 + result2

    # Run multiple times
    print("1. Running profiled operations:")
    for i in range(10):
        search_function(f"query_{i}")

    print(f"   Completed {i+1} iterations")

    # Show timings
    print("\n2. Timing statistics:")
    profiler.print_timings()

    # Show hot paths
    print("\n3. Hot paths analysis:")
    profiler.print_hot_paths(threshold=0.05)

    # Show summary
    print("\n4. Profiler summary:")
    summary = profiler.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    # cProfile demo
    print("\n5. cProfile demonstration:")
    with profiler.cprofile_context(sort_by="cumulative"):
        for i in range(5):
            expensive_operation()

    if profiler._last_stats:
        profiler._last_stats.print_stats(5)

    print("\n✅ Profiler demo complete")


if __name__ == "__main__":
    demo_profiler()
