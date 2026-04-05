"""
Comprehensive performance metrics for RAG system.
Tracks latency, throughput, and system resources over time.
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    """A single metric sample."""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    name: str
    count: int
    min: float
    max: float
    avg: float
    median: float
    p95: float
    p99: float
    total: float


class PerformanceMetrics:
    """
    Comprehensive performance metrics tracking.

    Features:
    - Latency tracking (query, embedding, database)
    - Throughput monitoring (queries/second)
    - Memory usage tracking
    - Time-series data (rolling window)
    - Percentiles (p50, p95, p99)
    - Performance history
    """

    def __init__(self, window_size: int = 1000, history_limit: int = 10000):
        """
        Initialize metrics tracker.

        Args:
            window_size: Maximum samples per metric (rolling window)
            history_limit: Maximum total samples across all metrics
        """
        self.window_size = window_size
        self.history_limit = history_limit

        # Metric storage (rolling windows)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # Counters for throughput
        self.counters: Dict[str, int] = defaultdict(int)
        self.counter_start_times: Dict[str, float] = {}

        # Current operation tracking
        self._current_operations: Dict[str, float] = {}

        # Lock for thread safety
        self._lock = threading.Lock()

    def record(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            metadata: Optional metadata

        Example:
            metrics.record("search_latency", 0.123, {"query": "database"})
        """
        with self._lock:
            sample = MetricSample(
                timestamp=time.time(),
                value=value,
                metadata=metadata or {}
            )
            self.metrics[name].append(sample)

            # Prune if over limit
            total_samples = sum(len(samples) for samples in self.metrics.values())
            if total_samples > self.history_limit:
                self._prune_old_samples()

    def record_latency(self, operation: str, duration: float, **metadata):
        """
        Record operation latency.

        Args:
            operation: Operation name (e.g., "search", "embedding")
            duration: Duration in seconds
            **metadata: Additional metadata

        Example:
            metrics.record_latency("search", 0.150, query_type="neural")
        """
        self.record(f"{operation}_latency", duration, metadata)

    def record_throughput(self, operation: str, count: int = 1):
        """
        Record throughput counter.

        Args:
            operation: Operation name
            count: Number of operations (default: 1)

        Example:
            metrics.record_throughput("search")  # 1 search
            metrics.record_throughput("search", 5)  # 5 searches
        """
        with self._lock:
            self.counters[operation] += count

            # Start tracking if first time
            if operation not in self.counter_start_times:
                self.counter_start_times[operation] = time.time()

    def get_throughput(self, operation: str, window_seconds: float = 60.0) -> float:
        """
        Calculate throughput for an operation.

        Args:
            operation: Operation name
            window_seconds: Time window in seconds

        Returns:
            Operations per second
        """
        with self._lock:
            if operation not in self.counters or operation not in self.counter_start_times:
                return 0.0

            elapsed = time.time() - self.counter_start_times[operation]
            if elapsed == 0:
                return 0.0

            ops_per_sec = self.counters[operation] / elapsed
            return ops_per_sec

    def reset_throughput(self, operation: str = None):
        """
        Reset throughput counter(s).

        Args:
            operation: Optional operation to reset (all if None)
        """
        with self._lock:
            if operation:
                self.counters[operation] = 0
                self.counter_start_times[operation] = time.time()
            else:
                for op in list(self.counters.keys()):
                    self.counters[op] = 0
                    self.counter_start_times[op] = time.time()

    def start_operation(self, operation: str):
        """
        Start timing an operation.

        Args:
            operation: Operation name

        Returns:
            Operation ID

        Example:
            op_id = metrics.start_operation("search")
            # ... do work ...
            metrics.end_operation("search", op_id)
        """
        op_id = f"{operation}_{time.time()}_{id(threading.current_thread())}"
        self._current_operations[op_id] = time.time()
        return op_id

    def end_operation(self, operation: str, op_id: str, **metadata):
        """
        End timing an operation and record latency.

        Args:
            operation: Operation name
            op_id: Operation ID from start_operation()
            **metadata: Additional metadata
        """
        start_time = self._current_operations.pop(op_id, None)
        if start_time:
            duration = time.time() - start_time
            self.record_latency(operation, duration, **metadata)
            self.record_throughput(operation, 1)

    @contextmanager
    def time_operation(self, operation: str, **metadata):
        """
        Context manager for timing an operation.

        Args:
            operation: Operation name
            **metadata: Additional metadata

        Example:
            with metrics.time_operation("search", query="database"):
                results = rag_db.search(query)
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_latency(operation, duration, **metadata)
            self.record_throughput(operation, 1)

    def get_summary(self, name: str) -> Optional[MetricSummary]:
        """
        Get summary statistics for a metric.

        Args:
            name: Metric name

        Returns:
            MetricSummary or None if no data
        """
        samples = list(self.metrics.get(name, []))
        if not samples:
            return None

        values = [s.value for s in samples]
        values_sorted = sorted(values)

        return MetricSummary(
            name=name,
            count=len(values),
            min=values_sorted[0],
            max=values_sorted[-1],
            avg=sum(values) / len(values),
            median=values_sorted[len(values) // 2],
            p95=values_sorted[int(len(values) * 0.95)] if len(values) > 20 else values_sorted[-1],
            p99=values_sorted[int(len(values) * 0.99)] if len(values) > 100 else values_sorted[-1],
            total=sum(values),
        )

    def get_timeseries(self, name: str, since: float = None) -> List[MetricSample]:
        """
        Get time-series data for a metric.

        Args:
            name: Metric name
            since: Optional timestamp (only samples after this time)

        Returns:
            List of MetricSample objects
        """
        samples = list(self.metrics.get(name, []))

        if since:
            samples = [s for s in samples if s.timestamp >= since]

        return samples

    def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """
        Get summaries for all metrics.

        Returns:
            Dictionary of metric names to MetricSummary objects
        """
        summaries = {}
        for name in self.metrics.keys():
            summary = self.get_summary(name)
            if summary:
                summaries[name] = summary
        return summaries

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage.

        Returns:
            Dictionary with memory stats
        """
        process = psutil.Process()

        return {
            "rss_mb": process.memory_info().rss / (1024 * 1024),  # Resident Set Size
            "vms_mb": process.memory_info().vms / (1024 * 1024),  # Virtual Memory Size
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
        }

    def get_system_resources(self) -> Dict[str, float]:
        """
        Get system resource usage.

        Returns:
            Dictionary with system resource stats
        """
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_usage_percent": psutil.disk_usage('/').percent,
        }

    def _prune_old_samples(self):
        """Remove old samples if over history limit."""
        # Sort metrics by oldest timestamp
        metrics_by_age = sorted(
            self.metrics.items(),
            key=lambda x: min((s.timestamp for s in x[1]), default=0)
        )

        # Remove from oldest metrics first
        removed = 0
        for name, samples in metrics_by_age:
            if not samples:
                continue

            samples.popleft()
            removed += 1

            if sum(len(s) for s in self.metrics.values()) <= self.history_limit:
                break

        logger.debug(f"Pruned {removed} old samples")

    def get_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.

        Returns:
            Dictionary with all performance data
        """
        return {
            "summaries": {
                name: {
                    "count": s.count,
                    "min_ms": s.min * 1000,
                    "max_ms": s.max * 1000,
                    "avg_ms": s.avg * 1000,
                    "median_ms": s.median * 1000,
                    "p95_ms": s.p95 * 1000,
                    "p99_ms": s.p99 * 1000,
                    "total_ms": s.total * 1000,
                }
                for name, s in self.get_all_summaries().items()
            },
            "throughput": {
                name: self.get_throughput(name)
                for name in self.counters.keys()
            },
            "memory": self.get_memory_usage(),
            "system": self.get_system_resources(),
            "metrics_count": len(self.metrics),
            "total_samples": sum(len(s) for s in self.metrics.values()),
        }

    def print_report(self, metric_names: List[str] = None):
        """
        Print performance report.

        Args:
            metric_names: Optional list of metrics to show (all if None)
        """
        summaries = self.get_all_summaries()

        if metric_names:
            summaries = {k: v for k, v in summaries.items() if k in metric_names}

        print("\n=== Performance Report ===\n")

        # Latency metrics
        print("1. Latency Metrics:")
        for name, summary in summaries.items():
            if "latency" in name:
                print(f"   {name}:")
                print(f"     Count: {summary.count}")
                print(f"     Avg: {summary.avg*1000:.1f}ms")
                print(f"     P50: {summary.median*1000:.1f}ms")
                print(f"     P95: {summary.p95*1000:.1f}ms")
                print(f"     P99: {summary.p99*1000:.1f}ms")
                print(f"     Min: {summary.min*1000:.1f}ms")
                print(f"     Max: {summary.max*1000:.1f}ms")

        # Throughput
        print("\n2. Throughput:")
        for operation in self.counters.keys():
            throughput = self.get_throughput(operation)
            print(f"   {operation}: {throughput:.2f} ops/sec")

        # Memory
        print("\n3. Memory Usage:")
        mem = self.get_memory_usage()
        print(f"   RSS: {mem['rss_mb']:.1f}MB")
        print(f"   VMS: {mem['vms_mb']:.1f}MB")
        print(f"   Percent: {mem['percent']:.1f}%")
        print(f"   Available: {mem['available_mb']:.1f}MB")

        # System resources
        print("\n4. System Resources:")
        sys = self.get_system_resources()
        print(f"   CPU: {sys['cpu_percent']:.1f}%")
        print(f"   Memory: {sys['memory_percent']:.1f}%")
        print(f"   Disk: {sys['disk_usage_percent']:.1f}%")

        print()

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        for name, summary in self.get_all_summaries().items():
            name_safe = name.replace(".", "_").replace("-", "_")

            lines.append(f"# TYPE {name_safe}_count gauge")
            lines.append(f"{name_safe}_count {summary.count}")

            lines.append(f"# TYPE {name_safe}_sum gauge")
            lines.append(f"{name_safe}_sum {summary.total}")

            lines.append(f"# TYPE {name_safe}_avg gauge")
            lines.append(f"{name_safe}_avg {summary.avg}")

            lines.append(f"# TYPE {name_safe}_p95 gauge")
            lines.append(f"{name_safe}_p95 {summary.p95}")

            lines.append(f"# TYPE {name_safe}_p99 gauge")
            lines.append(f"{name_safe}_p99 {summary.p99}")

        # Throughput
        for operation, throughput in self.get_throughput_all().items():
            name_safe = operation.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {name_safe}_throughput gauge")
            lines.append(f"{name_safe}_throughput {throughput}")

        return "\n".join(lines)

    def get_throughput_all(self) -> Dict[str, float]:
        """Get throughput for all operations."""
        return {op: self.get_throughput(op) for op in self.counters.keys()}

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.counter_start_times.clear()
            self._current_operations.clear()
            logger.debug("Performance metrics reset")


# Global metrics instance
_global_metrics: Optional[PerformanceMetrics] = None


def get_metrics() -> PerformanceMetrics:
    """Get global metrics singleton."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PerformanceMetrics()
    return _global_metrics


def demo_performance_metrics():
    """Demonstrate performance metrics."""
    print("\n=== Performance Metrics Demo ===\n")

    metrics = PerformanceMetrics(window_size=100, history_limit=1000)

    # Simulate some operations
    print("1. Simulating operations:")
    for i in range(50):
        import random
        latency = random.uniform(0.05, 0.3)
        query_type = random.choice(["neural", "tfidf", "hybrid"])

        # Record latency
        metrics.record_latency("search", latency, query_type=query_type)

        # Record throughput
        metrics.record_throughput("search")

        # Time some operations
        with metrics.time_operation("embedding", model="MiniLM"):
            time.sleep(0.01)

        if i % 10 == 0:
            print(f"   Recorded {i} operations")

    print(f"   Completed 50 operations")

    # Show report
    print("\n2. Performance report:")
    metrics.print_report(metric_names=["search_latency", "embedding_latency"])

    # Show raw data
    print("\n3. Raw timeseries (last 5 search_latency samples):")
    samples = metrics.get_timeseries("search_latency")[-5:]
    for sample in samples:
        print(f"   {datetime.fromtimestamp(sample.timestamp).strftime('%H:%M:%S')}: "
              f"{sample.value*1000:.1f}ms")

    # Get JSON report
    print("\n4. JSON report:")
    import json
    report = metrics.get_report()
    print(json.dumps(report, indent=2, default=str)[:500])

    # Prometheus export
    print("\n5. Prometheus export (first 10 lines):")
    prometheus = metrics.export_prometheus()
    for line in prometheus.split("\n")[:10]:
        print(f"   {line}")

    print("\n✅ Performance metrics demo complete")


if __name__ == "__main__":
    demo_performance_metrics()
