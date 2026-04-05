# RAG System Innovation Roadmap

**Last Updated:** 2026-04-05
**Version:** 1.0.0
**Current Release:** v1.0.0
**Status:** Active Development

---

## Overview

This roadmap tracks long-term innovative features for RAG memory system, including competitive features from Honcho and novel capabilities to differentiate the system.

## Current Status

### ✅ **v1.0.0 - RELEASED**
- Peer/Session Model (Honcho-style)
- Hybrid Retrieval (TF-IDF + Neural)
- Namespace Isolation
- Auto-Capture Hooks
- 9 Tools + 2 Hooks
- 83 Tests Passing

---

## Philosophy

- **Performance First**: Every feature must maintain sub-1ms cached search latency
- **Self-Hosted Focus**: No external dependencies on managed services
- **Production Ready**: All features include testing, metrics, and observability
- **Backward Compatible**: Never break existing API surface

---

## Priority Matrix

| Feature | Impact | Effort | Priority | Target Release | Status |
|---------|--------|--------|----------|----------------|---------|
| **Peer/Session Model** | High | Medium | P0 | v1.0.0 | ✅ **COMPLETED** |
| Time-Based Decay | High | Low | P0 | v1.1.0 | ⚠️ **PARTIAL** |
| Multi-Perspective Queries | High | Medium | P0 | v1.2.0 | 📋 **PLANNED** |
| Built-in Reasoning Engine | High | High | P0 | v1.3.0 | 📋 **PLANNED** |
| Advanced Hybrid (BM25) | Medium | Low | P1 | v1.1.0 | 📋 **PLANNED** |
| Knowledge Graph | High | High | P1 | v1.5.0 | 📋 **PLANNED** |
| Distributed RAG | Medium | Very High | P1 | v2.0.0 | 📋 **PLANNED** |
| Event Sourcing | Medium | Medium | P2 | v1.4.0 | 📋 **PLANNED** |
| Cross-Modal Retrieval | Medium | High | P2 | v1.6.0 | 📋 **PLANNED** |
| A/B Testing Framework | Low | Medium | P2 | v1.3.0 | 📋 **PLANNED** |

---

## ✅ COMPLETED: Phase 1 - Peer/Session Model

### Feature: Peer/Session Model
**Priority:** P0
**Target:** v1.0.0
**Status:** ✅ **COMPLETED**
**Effort:** 2-3 weeks
**Completed:** 2026-04-05

**Description:**
Implemented first-class support for peers (entities) and sessions (conversation groups), enabling multi-party conversations with metadata tracking.

**Requirements (ALL DONE):**
- ✅ `Peer` class with ID, metadata, and conversation history
- ✅ `Session` class with multi-peer support
- ✅ Automatic peer tracking in message captures
- ✅ Namespace isolation per peer/session
- ✅ Peer metadata CRUD operations
- ✅ Session lifecycle management
- ✅ Conversion to OpenAI/Anthropic formats

**Implementation:**
```python
# Features implemented
class Peer:
    - __init__(peer_id: str, metadata: dict = None)
    - add_message(role: str, content: str, session_id: str, timestamp: datetime, metadata: dict)
    - search(query: str, limit: int = 5) -> List[Dict]
    - get_context(tokens: int = 2000) -> Dict
    - set_metadata(metadata: dict)
    - get_messages(limit: int, session_id: str) -> List[Dict]
    - to_dict() -> Dict
    - Database persistence (peer_messages table)

class PeerManager:
    - create_peer(peer_id: str, metadata: dict) -> Peer
    - get_peer(peer_id: str) -> Peer
    - list_peers(limit: int) -> List[Peer]
    - delete_peer(peer_id: str)
    - search_peers(query: str, limit: int) -> List[Peer]
    - Database persistence (peers table)

class Session:
    - __init__(session_id: str, metadata: dict)
    - add_peers(peers: List[Peer])
    - add_messages(messages: List[Message])
    - context(summary: bool = True, tokens: int = 2000) -> str
    - to_openai(assistant: str) -> List[Dict]
    - to_anthropic(assistant: str) -> List[Dict]
    - representation(peer: Peer) -> str
    - set_summary(summary: str)
    - get_messages(limit: int, role: str, peer_id: str) -> List[Dict]
    - Database persistence (sessions, session_messages tables)

class SessionManager:
    - create_session(session_id: str, metadata: dict) -> Session
    - get_session(session_id: str) -> Session
    - list_sessions(limit: int, peer_id: str) -> List[Session]
    - delete_session(session_id: str)
    - Database persistence
```

**Success Criteria (ALL MET):**
- ✅ Can track 1000+ peers with metadata
- ✅ Session retrieval < 50ms
- ✅ Multi-peer conversations with < 10ms overhead per message
- ✅ All 53 tests passing (25 peer + 28 session)

**Files:**
- ✅ `models/peer.py` (517 lines)
- ✅ `models/session.py` (784 lines)
- ✅ `tests/test_peer_model.py` (25 tests)
- ✅ `tests/test_session.py` (28 tests)

---

## 🔄 IN PROGRESS: Phase 2 - Advanced Retrieval (v1.1.0)

### Feature: Time-Based Decay
**Priority:** P0
**Target:** v1.1.0
**Status:** ⚠️ **PARTIALLY IMPLEMENTED**
**Effort:** 1 week

**Description:**
Relevance decreases over time, with configurable decay rates and boosting of recent content.

**Requirements:**
- [ ] Integrate time decay into main search pipeline
- [ ] Configurable decay rates per namespace
- [ ] Boost recent content (configurable threshold)
- [ ] Time-slice queries (what was relevant on date X?)
- [ ] Decay-aware caching

**Implementation:**
```python
# Time decay scoring algorithm
def decay_score(original_score: float, timestamp: datetime, decay_rate: float) -> float:
    """
    Apply time decay to relevance score

    Args:
        original_score: Original relevance score (0-1)
        timestamp: When the document was added
        decay_rate: Daily decay rate (0-1, where 0.1 = 10% per day)

    Returns:
        Decayed score
    """
    days_old = (datetime.now() - timestamp).days
    decay_factor = (1 - decay_rate) ** days_old
    return original_score * decay_factor
```

**Success Criteria:**
- Time-slice queries < 30ms
- Decay-aware caching (different cache keys per time window)
- Configurable decay rates (linear, exponential)
- Backward compatible (no decay = default)

**Files:**
- `core/time_decay.py` (new)
- `core/rag_core.py` (modify)
- `tests/test_time_decay.py` (new)

---

## 📋 PLANNED: Phase 2 - Advanced Retrieval (v1.1.0)

### Feature: Advanced Hybrid with BM25
**Priority:** P1
**Target:** v1.1.0
**Status:** 📋 **PLANNED**
**Effort:** 1 week

**Description:**
Add BM25 as a third retrieval method alongside TF-IDF and Neural, for better keyword matching.

**Requirements:**
- [ ] BM25 retriever implementation
- [ ] 3-way fusion (TF-IDF + BM25 + Neural)
- [ ] RRF fusion for 3 methods
- [ ] Configurable weights per method
- [ ] Automatic weight tuning

**Implementation:**
```python
class BM25Retriever:
    def __init__(self):
        self.corpus = []
        self.k1 = 1.2
        self.b = 0.75

    def add_documents(self, documents: List[str]):
        """Index documents for BM25"""
        pass

    def search(self, query: str, limit: int = 10):
        """BM25 search"""
        pass

class ThreeWayFusion:
    def fuse(self, tfidf: list, bm25: list, neural: list):
        """Fuse 3 retrieval methods"""
        pass
```

**Success Criteria:**
- BM25 search < 50ms
- 3-way fusion < 20ms overhead
- Improves precision on keyword queries by 15%
- Backward compatible (can disable BM25)

**Files:**
- `core/bm25_retriever.py` (new)
- `core/three_way_fusion.py` (new)
- `tests/test_bm25.py` (new)

---

## 📋 PLANNED: Phase 1 - Honcho-Style Features (v1.2.0 - v1.3.0)

### Feature: Multi-Perspective Queries
**Priority:** P0
**Target:** v1.2.0
**Status:** 📋 **PLANNED**
**Effort:** 1-2 weeks

**Description:**
Enable queries from different perspectives - "What does Alice know about X?" or "What does Alice think Bob knows about Y?"

**Requirements:**
- [ ] Search within peer-specific namespaces
- [ ] Cross-peer relationship queries
- [ ] Perspective-aware ranking
- [ ] Contextual understanding of "X knows Y" statements
- [ ] Temporal awareness (what did they know when?)

**Implementation:**
```python
class MultiPerspectiveRAG:
    def get_peer_view(peer_id: str, query: str):
        """What does peer X know about topic Y?"""
        pass

    def cross_peer_view(peer_a: str, peer_b: str, topic: str):
        """What does peer A think peer B knows about topic?"""
        pass

    def temporal_view(peer_id: str, query: str, as_of: datetime):
        """What did peer X know about topic Y at time T?"""
        pass

    def shared_view(peer_ids: List[str], query: str):
        """What do these peers collectively know about topic?"""
        pass
```

**Success Criteria:**
- Peer-specific search < 20ms
- Cross-peer queries < 100ms
- Temporal queries with correct time slices
- Maintains 60-80% cache hit rate

**Files:**
- `core/multi_perspective.py` (new)
- `tests/test_multi_perspective.py` (new)

---

### Feature: Built-in Reasoning Engine
**Priority:** P0
**Target:** v1.3.0
**Status:** 📋 **PLANNED**
**Effort:** 3-4 weeks

**Description:**
Use LLM to reason about stored memory, answering natural language questions like "What learning styles does the user respond to best?"

**Requirements:**
- [ ] Integration with LLM providers (OpenAI, Anthropic, local models)
- [ ] Context-aware question answering
- [ ] Metadata reasoning (extract insights from metadata)
- [ ] Cross-entity reasoning
- [ ] Caching of reasoning results
- [ ] Configurable LLM selection and fallback

**Implementation:**
```python
class ReasoningEngine:
    def answer_question(self, question: str, context: list):
        """Answer natural language question about stored memory"""
        pass

    def summarize_peer(self, peer_id: str, aspect: str = None):
        """Generate summary of peer's preferences/knowledge"""
        pass

    def extract_insights(self, peer_id: str):
        """Extract behavioral insights from conversation history"""
        pass

    def compare_peers(self, peer_ids: List[str], dimension: str):
        """Compare peers along a dimension (preferences, style, etc.)"""
        pass
```

**Success Criteria:**
- Reasoning queries < 5s (with caching)
- Cached reasoning < 100ms
- Insight extraction accuracy > 80% (evaluated manually)
- Supports 3+ LLM providers

**Files:**
- `core/reasoning_engine.py` (new)
- `core/llm_integration.py` (new)
- `tests/test_reasoning.py` (new)

---

## 📋 PLANNED: Phase 5 - Advanced Features (v1.4.0 - v1.6.0)

### Feature: Event Sourcing
**Priority:** P2
**Target:** v1.4.0
**Status:** 📋 **PLANNED**
**Effort:** 2-3 weeks

**Description:**
Implement event sourcing for all mutations, enabling replay, audit logs, and temporal queries.

**Files:**
- `core/event_sourcing.py` (new)
- `tests/test_event_sourcing.py` (new)

---

### Feature: Cross-Modal Retrieval
**Priority:** P2
**Target:** v1.6.0
**Status:** 📋 **PLANNED**
**Effort:** 4-5 weeks

**Description:**
Enable retrieval across different modalities (text, images, audio) with unified embeddings.

**Files:**
- `core/cross_modal.py` (new)
- `core/image_embeddings.py` (new)
- `core/audio_embeddings.py` (new)

---

### Feature: A/B Testing Framework
**Priority:** P2
**Target:** v1.3.0
**Status:** 📋 **PLANNED**
**Effort:** 2 weeks

**Description:**
Built-in A/B testing for retrieval algorithms, with automatic metrics collection and analysis.

**Files:**
- `core/ab_testing.py` (new)
- `tests/test_ab_testing.py` (new)

---

## 📋 PLANNED: Phase 3 - Knowledge Graph (v1.5.0)

### Feature: Knowledge Graph Integration
**Priority:** P1
**Target:** v1.5.0
**Status:** 📋 **PLANNED**
**Effort:** 4-5 weeks

**Description:**
Build a knowledge graph from conversations, enabling entity extraction, relationship mapping, and graph-based retrieval.

**Requirements:**
- [ ] Entity extraction (NER)
- [ ] Relationship extraction
- [ ] Graph storage (SQLite or graph DB)
- [ ] Graph traversal search
- [ ] Entity-based retrieval
- [ ] Relationship queries

**Implementation:**
```python
class KnowledgeGraph:
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities using NER"""
        pass

    def extract_relationships(self, entities: List[Entity], text: str) -> List[Relationship]:
        """Extract relationships between entities"""
        pass

    def add_entity(self, entity: Entity):
        """Add entity to graph"""
        pass

    def add_relationship(self, rel: Relationship):
        """Add relationship to graph"""
        pass

    def graph_search(self, query: str, limit: int = 10) -> List[Result]:
        """Graph traversal for semantic discovery"""
        pass

    def entity_search(self, entity: str, depth: int = 2) -> List[Result]:
        """Search by entity and its relationships"""
        pass
```

**Success Criteria:**
- Entity extraction < 100ms per document
- Graph search < 200ms
- Improves recall on entity queries by 20%
- Optional feature (can disable)

**Files:**
- `core/knowledge_graph.py` (new)
- `core/entity_extraction.py` (new)
- `core/graph_storage.py` (new)
- `tests/test_knowledge_graph.py` (new)

---

## 📋 PLANNED: Phase 4 - Distributed RAG (v2.0.0)

### Feature: Distributed RAG
**Priority:** P1
**Target:** v2.0.0
**Status:** 📋 **PLANNED**
**Effort:** 6-8 weeks

**Description:**
Enable shared memory across multiple RAG instances, with conflict resolution and federated search.

**Requirements:**
- [ ] Peer discovery and registration
- [ ] Conflict resolution (CRDTs or similar)
- [ ] Federated search across nodes
- [ ] Sync protocol
- [ ] Offline support
- [ ] Configurable consistency levels

**Implementation:**
```python
class DistributedRAG:
    def __init__(self, node_id: str, peer_nodes: List[str]):
        """Initialize distributed RAG node"""
        pass

    def sync_with_peers(self):
        """Sync with peer nodes"""
        pass

    def distributed_search(self, query: str) -> List[Result]:
        """Federated search across nodes"""
        pass

    def resolve_conflicts(self, conflicts: List[Conflict]):
        """Resolve sync conflicts"""
        pass

    def register_peer(self, peer_node: str):
        """Register new peer node"""
        pass
```

**Success Criteria:**
- Sync latency < 5s for small datasets
- Federated search < 1s across 5 nodes
- Conflict resolution without data loss
- Backward compatible (single-node still works)

**Files:**
- `core/distributed.py` (new)
- `core/sync_protocol.py` (new)
- `core/conflict_resolution.py` (new)
- `tests/test_distributed.py` (new)

---

## Release Schedule

| Version | Features | Target Date | Status |
|---------|----------|-------------|---------|
| **v1.0.0** | Peer/Session Model, Hybrid Retrieval, Namespace Isolation, Auto-Capture | 2026-04-05 | ✅ **RELEASED** |
| **v1.1.0** | Time-Based Decay, Advanced Hybrid (BM25) | 2026-05-01 | 📋 **PLANNED** |
| **v1.2.0** | Multi-Perspective Queries | 2026-05-15 | 📋 **PLANNED** |
| **v1.3.0** | Built-in Reasoning Engine, A/B Testing Framework | 2026-06-01 | 📋 **PLANNED** |
| **v1.4.0** | Event Sourcing | 2026-06-15 | 📋 **PLANNED** |
| **v1.5.0** | Knowledge Graph Integration | 2026-07-01 | 📋 **PLANNED** |
| **v1.6.0** | Cross-Modal Retrieval | 2026-07-15 | 📋 **PLANNED** |
| **v2.0.0** | Distributed RAG | 2026-08-01 | 📋 **PLANNED** |

---

## Contributing

This roadmap is a living document. Feature priorities may shift based on:
- Community feedback and requests
- Performance requirements
- Technical feasibility
- Market needs

To contribute:
1. Check this roadmap for planned features
2. Create an issue to discuss implementation
3. Submit PR with tests and documentation
4. Update this roadmap when features are completed

---

## Notes

- All features must maintain backward compatibility
- Performance requirements must be met before merging
- Security reviews required for network-related features
- Documentation required for all public APIs
