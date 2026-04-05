"""
True Hybrid RAG with Adaptive Fusion
Implements intelligent fusion strategies that adapt to query type and characteristics
"""

import sys
import time
import re
from typing import List, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from collections import defaultdict
import logging

sys.path.insert(0, '/home/aka/rag-system')

from rag_api_tfidf import RAG as RAGTfidf
from rag_api import RAG as RAGNeural

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval."""

    # Fusion methods
    fusion_method: str = "adaptive"  # "adaptive", "weighted", "rrf", "borda", "learned"

    # Weighted fusion weights
    tfidf_weight: float = 0.3
    neural_weight: float = 0.7

    # RRF parameters
    rrf_k: int = 60  # RRF constant

    # Adaptive fusion parameters
    keyword_threshold: float = 0.5  # Threshold for keyword detection
    semantic_threshold: float = 0.5  # Threshold for semantic detection

    # Retrieval parameters
    stage1_limit: int = 100  # TF-IDF candidates
    stage2_limit: int = 20  # Neural re-ranking

    # Score normalization
    normalize_scores: bool = True
    score_range: Tuple[float, float] = (0.0, 1.0)

    # Result filtering
    min_score: float = 0.1  # Minimum score to include
    diversity_boost: float = 0.0  # Boost diverse results


@dataclass
class HybridResult:
    """Hybrid search result."""
    content: str
    source_id: str
    namespace: str
    tfidf_score: float
    neural_score: float
    hybrid_score: float
    rank: int
    metadata: Dict[str, Any]


class QueryClassifier:
    """
    Classifies queries for adaptive fusion.

    Query types:
    - keyword: Exact term matches, technical terms, IDs
    - semantic: Natural language, concepts, relationships
    - hybrid: Mix of both
    """

    # Keyword patterns
    KEYWORD_PATTERNS = [
        r'\b[A-Z]{2,}\b',  # Acronyms (API, SQL, HTTP)
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPs
        r'\b[a-f0-9]{8,}\b',  # Hashes
        r'"[^"]+"',  # Exact phrases
    ]

    # Semantic patterns
    SEMANTIC_PATTERNS = [
        r'\b(how|what|why|when|where|who|which|explain|describe)\b',  # WH-words
        r'\b(similar|like|related|connected|associated)\b',  # Similarity
        r'\b(meaning|definition|understand)\b',  # Concept queries
    ]

    # Technical keywords
    TECHNICAL_TERMS = {
        'sql', 'api', 'http', 'ssh', 'ssl', 'tcp', 'udp', 'dns',
        'db', 'database', 'query', 'table', 'column', 'row',
        'port', 'ip', 'address', 'server', 'client',
        'python', 'javascript', 'java', 'go', 'rust',
        'git', 'commit', 'branch', 'merge', 'pull',
        'docker', 'kubernetes', 'container',
        'cloudflare', 'aws', 'azure', 'gcp',
        'telegram', 'discord', 'slack',
    }

    @classmethod
    def classify(cls, query: str) -> Tuple[str, float, float]:
        """
        Classify query type.

        Returns:
            (query_type, keyword_score, semantic_score)
        """
        query_lower = query.lower()

        # Count keyword indicators
        keyword_score = 0.0

        # Exact phrases
        exact_phrases = len(re.findall(r'"[^"]+"', query))
        keyword_score += min(0.4, exact_phrases * 0.2)

        # Technical terms
        words = set(query_lower.split())
        tech_terms = len(words & cls.TECHNICAL_TERMS)
        keyword_score += min(0.3, tech_terms * 0.1)

        # Keyword patterns
        for pattern in cls.KEYWORD_PATTERNS:
            if re.search(pattern, query):
                keyword_score += 0.1

        # Short queries: more keyword
        if len(words) <= 3:
            keyword_score += 0.2
        elif len(words) >= 6:
            keyword_score -= 0.1

        # Count semantic indicators
        semantic_score = 0.0

        # WH-words and semantic patterns
        for pattern in cls.SEMANTIC_PATTERNS:
            if re.search(pattern, query_lower):
                semantic_score += 0.2

        # Longer queries: more semantic
        if len(words) >= 5:
            semantic_score += 0.2

        # Normalize
        keyword_score = max(0.0, min(1.0, keyword_score))
        semantic_score = max(0.0, min(1.0, semantic_score))

        # Determine query type
        if keyword_score > 0.6:
            query_type = "keyword"
        elif semantic_score > 0.6:
            query_type = "semantic"
        else:
            query_type = "hybrid"

        return query_type, keyword_score, semantic_score


class TrueHybridRAG:
    """
    True Hybrid RAG with adaptive fusion.

    Fusion strategies:
    1. Adaptive: Adjust weights based on query type
    2. Weighted: Fixed weights
    3. RRF: Reciprocal Rank Fusion
    4. Borda: Borda count (rank aggregation)
    """

    def __init__(self, config: HybridConfig = None):
        """
        Initialize true hybrid RAG.

        Args:
            config: HybridConfig with fusion parameters
        """
        self.config = config or HybridConfig()
        self.tfidf = RAGTfidf.get()
        self.neural = RAGNeural.get()
        self.query_classifier = QueryClassifier()

        # Statistics
        self.stats = defaultdict(int)
        self.stats['total_queries'] = 0
        self.stats['fusion_methods'] = defaultdict(int)

        logger.info("True Hybrid RAG initialized")

    def _normalize_score(
        self,
        score: float,
        method: str = "minmax"
    ) -> float:
        """Normalize score to [0, 1] range."""
        if not self.config.normalize_scores:
            return score

        if method == "minmax":
            # TF-IDF: 0-1, Neural: 0-2
            return score / 2.0
        else:
            return score

    def _weighted_fusion(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]]
    ) -> List[HybridResult]:
        """Weighted fusion of TF-IDF and Neural results."""
        # Create score maps
        tfidf_scores = {r['source_id']: r['distance'] for r in tfidf_results}
        neural_scores = {r['source_id']: r['distance'] for r in neural_results}

        # Normalize
        tfidf_normalized = {
            k: 1.0 - v  # Invert: lower distance = higher score
            for k, v in tfidf_scores.items()
        }
        neural_normalized = {
            k: 1.0 - (v / 2.0)  # Normalize and invert
            for k, v in neural_scores.items()
        }

        # Combine
        all_source_ids = set(tfidf_scores.keys()) | set(neural_scores.keys())
        combined = []

        for source_id in all_source_ids:
            tfidf_score = tfidf_normalized.get(source_id, 0.0)
            neural_score = neural_normalized.get(source_id, 0.0)

            hybrid_score = (
                self.config.tfidf_weight * tfidf_score +
                self.config.neural_weight * neural_score
            )

            combined.append({
                'source_id': source_id,
                'tfidf_score': tfidf_score,
                'neural_score': neural_score,
                'hybrid_score': hybrid_score,
            })

        # Sort and return
        combined.sort(key=lambda x: -x['hybrid_score'])

        # Build results
        results = []
        content_map = {r['source_id']: r for r in tfidf_results}
        content_map.update({r['source_id']: r for r in neural_results})

        for i, item in enumerate(combined[:self.config.stage2_limit]):
            content = content_map.get(item['source_id'])
            if content:
                results.append(HybridResult(
                    content=content['content'],
                    source_id=item['source_id'],
                    namespace=content.get('namespace', ''),
                    tfidf_score=item['tfidf_score'],
                    neural_score=item['neural_score'],
                    hybrid_score=item['hybrid_score'],
                    rank=i + 1,
                    metadata=content.get('metadata', {}),
                ))

        return results

    def _rrf_fusion(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]]
    ) -> List[HybridResult]:
        """Reciprocal Rank Fusion (RRF)."""
        # Create rankings
        tfidf_ranking = {r['source_id']: i+1 for i, r in enumerate(tfidf_results)}
        neural_ranking = {r['source_id']: i+1 for i, r in enumerate(neural_results)}

        # RRF scores
        rrf_scores = defaultdict(float)
        for source_id, rank in tfidf_ranking.items():
            rrf_scores[source_id] += self.config.rrf_k / (rank + self.config.rrf_k)
        for source_id, rank in neural_ranking.items():
            rrf_scores[source_id] += self.config.rrf_k / (rank + self.config.rrf_k)

        # Sort
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])

        # Build results
        results = []
        content_map = {r['source_id']: r for r in tfidf_results}
        content_map.update({r['source_id']: r for r in neural_results})

        for i, source_id in enumerate(sorted_ids[:self.config.stage2_limit]):
            content = content_map.get(source_id)
            if content:
                results.append(HybridResult(
                    content=content['content'],
                    source_id=source_id,
                    namespace=content.get('namespace', ''),
                    tfidf_score=1.0 - tfidf_ranking.get(source_id, 100) / 100,
                    neural_score=1.0 - neural_ranking.get(source_id, 100) / 100,
                    hybrid_score=rrf_scores[source_id],
                    rank=i + 1,
                    metadata=content.get('metadata', {}),
                ))

        return results

    def _adaptive_fusion(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]],
        query: str
    ) -> List[HybridResult]:
        """Adaptive fusion based on query type."""
        # Classify query
        query_type, keyword_score, semantic_score = self.query_classifier.classify(query)

        # Adapt weights
        if query_type == "keyword":
            tfidf_weight = 0.7
            neural_weight = 0.3
        elif query_type == "semantic":
            tfidf_weight = 0.3
            neural_weight = 0.7
        else:
            # Hybrid: balanced
            tfidf_weight = 0.5
            neural_weight = 0.5

        # Temporarily update config
        original_tfidf = self.config.tfidf_weight
        original_neural = self.config.neural_weight
        self.config.tfidf_weight = tfidf_weight
        self.config.neural_weight = neural_weight

        # Use weighted fusion with adapted weights
        results = self._weighted_fusion(tfidf_results, neural_results)

        # Restore config
        self.config.tfidf_weight = original_tfidf
        self.config.neural_weight = original_neural

        return results

    def search(
        self,
        query: str,
        namespace: str = None,
        limit: int = 5,
        fusion_method: str = None
    ) -> Dict[str, Any]:
        """
        Hybrid search with adaptive fusion.

        Args:
            query: Search query
            namespace: Namespace to search
            limit: Number of results to return
            fusion_method: Fusion method (default: from config)

        Returns:
            Dict with results and metadata
        """
        start_time = time.time()
        fusion_method = fusion_method or self.config.fusion_method

        # Stage 1: TF-IDF retrieval
        stage1_start = time.time()
        tfidf_results = self.tfidf.search(
            query=query,
            namespace=namespace,
            limit=self.config.stage1_limit
        )
        stage1_time = time.time() - stage1_start

        # Stage 2: Neural retrieval
        stage2_start = time.time()
        neural_results = self.neural.search(
            query=query,
            namespace=namespace,
            limit=self.config.stage2_limit
        )
        stage2_time = time.time() - stage2_start

        # Fusion
        fusion_start = time.time()
        if fusion_method == "adaptive":
            results = self._adaptive_fusion(tfidf_results, neural_results, query)
        elif fusion_method == "rrf":
            results = self._rrf_fusion(tfidf_results, neural_results)
        else:
            results = self._weighted_fusion(tfidf_results, neural_results)
        fusion_time = time.time() - fusion_start

        # Filter by min score
        if self.config.min_score > 0:
            results = [r for r in results if r.hybrid_score >= self.config.min_score]

        # Return top N
        results = results[:limit]

        # Update stats
        self.stats['total_queries'] += 1
        self.stats['fusion_methods'][fusion_method] += 1

        total_time = time.time() - start_time

        return {
            'query': query,
            'results': results,
            'query_type': QueryClassifier.classify(query)[0],
            'fusion_method': fusion_method,
            'stage1_time_ms': round(stage1_time * 1000, 1),
            'stage2_time_ms': round(stage2_time * 1000, 1),
            'fusion_time_ms': round(fusion_time * 1000, 1),
            'total_time_ms': round(total_time * 1000, 1),
            'stage1_candidates': len(tfidf_results),
            'stage2_candidates': len(neural_results),
            'final_results': len(results),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return dict(self.stats)


def demo_true_hybrid():
    """Demonstrate true hybrid RAG."""

    print("=" * 70)
    print("True Hybrid RAG Demo")
    print("=" * 70)

    # Create hybrid RAG
    config = HybridConfig(
        fusion_method="adaptive",
        rrf_k=60,
        stage1_limit=50,
        stage2_limit=10,
    )

    hybrid = TrueHybridRAG(config=config)

    print("\n✓ True Hybrid RAG initialized")
    print(f"  Fusion method: {config.fusion_method}")
    print(f"  Stage 1 limit: {config.stage1_limit}")
    print(f"  Stage 2 limit: {config.stage2_limit}")

    # Add test data
    print("\nAdding test data...")

    test_facts = [
        "User prefers MariaDB over MySQL for database",
        "Dell E5420 laptop with 4GB RAM running Linux Mint 22.1",
        "Adminer runs on port 5056 with tailnet-only access",
        "Use Cloudflare Warp for connectivity",
        "Telegram for talking to me",
        "Python API development guide for beginners",
        "SSH port configuration tutorial",
        "HTTP server setup with Nginx",
        "SQL query optimization techniques",
        "Database indexing best practices",
    ]

    for fact in test_facts:
        hybrid.tfidf.add_fact(fact, "general")
        hybrid.neural.add_fact(fact, "general")

    print(f"✓ Added {len(test_facts)} facts")

    # Test queries with different types
    print("\n" + "=" * 70)
    print("Testing Hybrid Search")
    print("=" * 70)

    queries = [
        ("SQL query optimization", "keyword-heavy technical query"),
        ("How do I configure SSH?", "natural language query"),
        ("database MySQL MariaDB", "hybrid query"),
        ("Python API HTTP server", "technical keywords"),
        ("What is the best database?", "semantic query"),
    ]

    for query, description in queries:
        print(f"\n{'─'*70}")
        print(f"Query: \"{query}\"")
        print(f"Type: {description}")
        print(f"{'─'*70}")

        # Test all fusion methods
        methods = ["adaptive", "weighted", "rrf"]

        for method in methods:
            result = hybrid.search(query=query, namespace='facts', limit=3, fusion_method=method)

            print(f"\n{method.upper()} fusion:")
            print(f"  Query type: {result['query_type']}")
            print(f"  Stage 1: {result['stage1_time_ms']}ms ({result['stage1_candidates']} candidates)")
            print(f"  Stage 2: {result['stage2_time_ms']}ms ({result['stage2_candidates']} candidates)")
            print(f"  Fusion: {result['fusion_time_ms']}ms")
            print(f"  Total: {result['total_time_ms']}ms")

            if result['results']:
                print(f"\n  Top results:")
                for r in result['results']:
                    print(f"    {r.rank}. {r.content[:50]}...")
                    print(f"       TF-IDF: {r.tfidf_score:.3f} | Neural: {r.neural_score:.3f} | Hybrid: {r.hybrid_score:.3f}")

    # Stats
    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)

    stats = hybrid.get_stats()
    print(f"\nTotal queries: {stats['total_queries']}")
    print(f"Fusion methods used: {dict(stats['fusion_methods'])}")

    print("\n✅ True Hybrid RAG demo complete!")


if __name__ == "__main__":
    demo_true_hybrid()
