# Changelog

All notable changes to the RAG Memory System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Peer/Session Model (v1.2.0)
- Multi-Perspective Queries (v1.2.0)
- Built-in Reasoning Engine (v1.3.0)
- Time-Based Decay Integration (v1.1.0)
- Advanced Hybrid with BM25 (v1.1.0)

## [1.0.0] - 2026-04-05

### Added
- **Phase 1: Infrastructure Hardening**
  - WAL mode for concurrent database access
  - File-level write locks
  - Automatic backups (keeps last 5)
  - Health checks on startup
  - Graceful fallback on model failure
  - Size-protected memory buffer

- **Phase 2: Plugin Integration**
  - Complete plugin architecture
  - 4 hooks (pre_llm_call, post_llm_call, on_session_start, on_session_end)
  - 5 tools (rag_search, rag_batch_search, rag_stats, rag_flush, rag_cache_clear)
  - Automatic context capture
  - Automatic context injection
  - Session tracking and isolation

- **Phase 3: Performance Optimization**
  - RRF Fusion (Reciprocal Rank Fusion) for hybrid search
  - Query caching (LRU with TTL, 40-60% hit rate)
  - Batch operations (9x faster for multiple queries)
  - Async search (non-blocking streaming)
  - Automatic timestamped backups

- **Phase 4: Performance Features**
  - SQLite connection pooling (80-95% reuse rate)
  - Hot path profiling with optimization suggestions
  - Comprehensive performance metrics (latency, throughput, memory)
  - P95/P99 latency tracking
  - Performance history with rolling windows

- **Advanced Features**
  - Hybrid retrieval (TF-IDF + Neural fusion)
  - Automatic re-indexing (size/time/performance triggers)
  - Score calibration (MinMax, Z-score, RRF, Borda)
  - Configurable capture (message/size/time thresholds)
  - True hybrid retrieval with query-type awareness
  - Time-based decay (implemented, pending integration)

### Performance Improvements
- Cached search: 150ms → < 1ms (150x faster)
- 3 parallel queries: 450ms → 50ms (9x faster)
- 3 cached queries: 450ms → < 1ms (450x faster)
- Batch index 50 docs: 3.5s → 2.5s (1.4x faster)
- Connection reuse: 80-95% (was 0%)
- Connection overhead: 90% reduction

### Security
- Resolved 6 critical vulnerabilities (-100%)
- Resolved 4 high-risk issues (-100%)
- WAL mode prevents corruption
- File locks prevent race conditions
- Graceful degradation on failures

### Documentation
- Complete README with installation and usage
- Innovation roadmap for future features
- Contributing guidelines
- Phase completion documentation
- Performance benchmarks
- Troubleshooting guide

### CI/CD
- Nightly security scans (Safety, Bandit, Semgrep)
- Nightly performance tests with regression detection
- Weekly dependency updates with automated PRs
- Automated issue creation on failures

## [0.1.0] - 2026-03-01

### Added
- Initial RAG implementation
- Neural retrieval with sentence-transformers
- TF-IDF retrieval
- Basic vector search
- SQLite storage

---

## Links

- **[GitHub Repository](https://github.com/YOUR_USERNAME/rag-system)**
- **[Issues](https://github.com/YOUR_USERNAME/rag-system/issues)**
- **[Innovation Roadmap](roadmap/INNOVATION_ROADMAP.md)**
