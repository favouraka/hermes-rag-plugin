"""
Advanced hybrid search with BM25 and learned ranking.
Combines multiple ranking methods for optimal relevance.
"""

import math
import re
from typing import Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class BM25Config:
    """Configuration for BM25 ranking."""
    k1: float = 1.5  # Term saturation parameter
    b: float = 0.75   # Length normalization parameter
    epsilon: float = 0.25  # IDF floor


@dataclass
class Document:
    """Document for BM25 indexing."""
    doc_id: str
    content: str
    tokens: List[str] = field(default_factory=list)
    length: int = 0


@dataclass
class RankingResult:
    """Ranked search result."""
    doc_id: str
    content: str
    score: float
    method_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BM25Ranker:
    """
    BM25 ranking algorithm.

    A probabilistic ranking function used in search engines
    to estimate the relevance of documents to search queries.
    """

    def __init__(self, config: BM25Config = None):
        """
        Initialize BM25 ranker.

        Args:
            config: BM25 configuration
        """
        self.config = config or BM25Config()
        self.documents: Dict[str, Document] = {}
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.idf: Dict[str, float] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length = 0.0

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Simple tokenization (lowercase, alphanumeric)
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def index_document(self, doc_id: str, content: str):
        """
        Index a document for BM25.

        Args:
            doc_id: Document ID
            content: Document content
        """
        tokens = self.tokenize(content)
        doc = Document(doc_id=doc_id, content=content, tokens=tokens, length=len(tokens))

        self.documents[doc_id] = doc
        self.doc_lengths[doc_id] = len(tokens)

        # Update document frequencies
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self.doc_freqs[token] += 1

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index from documents.

        Args:
            documents: List of documents with 'doc_id' and 'content'
        """
        # Clear existing index
        self.documents.clear()
        self.doc_freqs.clear()
        self.idf.clear()
        self.doc_lengths.clear()

        # Index all documents
        for doc in documents:
            self.index_document(doc["doc_id"], doc["content"])

        # Calculate average document length
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)

        # Calculate IDF for all terms
        self._calculate_idf()

    def _calculate_idf(self):
        """Calculate IDF for all terms."""
        num_docs = len(self.documents)

        for token, doc_freq in self.doc_freqs.items():
            # BM25 IDF with epsilon smoothing
            idf = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            self.idf[token] = max(idf, self.config.epsilon)

    def search(self, query: str, limit: int = 10) -> List[RankingResult]:
        """
        Search using BM25 ranking.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of ranked results
        """
        query_tokens = self.tokenize(query)
        scores = defaultdict(float)

        for doc_id, doc in self.documents.items():
            score = self._score_document(doc, query_tokens)
            if score > 0:
                scores[doc_id] = score

        # Sort by score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Create result objects
        results = []
        for doc_id, score in sorted_docs[:limit]:
            doc = self.documents[doc_id]
            result = RankingResult(
                doc_id=doc_id,
                content=doc.content,
                score=score,
                method_scores={"bm25": score},
            )
            results.append(result)

        return results

    def _score_document(self, doc: Document, query_tokens: List[str]) -> float:
        """
        Score a document for a query using BM25.

        Args:
            doc: Document to score
            query_tokens: Query tokens

        Returns:
            BM25 score
        """
        score = 0.0

        # Count term frequencies in document
        term_freqs = defaultdict(int)
        for token in doc.tokens:
            term_freqs[token] += 1

        # Calculate BM25 score
        for token in set(query_tokens):  # Unique query tokens
            if token in self.idf:
                tf = term_freqs.get(token, 0)
                idf = self.idf[token]

                # BM25 formula
                numerator = tf * (self.config.k1 + 1)
                denominator = tf + self.config.k1 * (1 - self.config.b + self.config.b * (doc.length / self.avg_doc_length))

                score += idf * (numerator / denominator)

        return score


class LearnedRanker:
    """
    Learned ranking using ensemble methods.

    Combines multiple ranking signals (BM25, neural, TF-IDF)
    using learned weights.
    """

    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize learned ranker.

        Args:
            weights: Method weights (e.g., {"bm25": 0.4, "neural": 0.6})
        """
        self.weights = weights or {
            "bm25": 0.35,
            "neural": 0.45,
            "tfidf": 0.20,
        }

        # Normalize weights
        total = sum(self.weights.values())
        for method in self.weights:
            self.weights[method] /= total

    def rank(
        self,
        bm25_results: List[RankingResult],
        neural_results: List[RankingResult],
        tfidf_results: List[RankingResult],
        limit: int = 10
    ) -> List[RankingResult]:
        """
        Rank documents using learned ensemble.

        Args:
            bm25_results: BM25 ranked results
            neural_results: Neural ranked results
            tfidf_results: TF-IDF ranked results
            limit: Maximum number of results

        Returns:
            Ensembled ranked results
        """
        # Combine scores by doc_id
        combined_scores = defaultdict(lambda: {"total": 0.0, "methods": {}})

        # Add BM25 scores
        for result in bm25_results:
            combined_scores[result.doc_id]["total"] += result.score * self.weights["bm25"]
            combined_scores[result.doc_id]["methods"]["bm25"] = result.score

        # Add neural scores
        for result in neural_results:
            combined_scores[result.doc_id]["total"] += result.score * self.weights["neural"]
            combined_scores[result.doc_id]["methods"]["neural"] = result.score

        # Add TF-IDF scores
        for result in tfidf_results:
            combined_scores[result.doc_id]["total"] += result.score * self.weights["tfidf"]
            combined_scores[result.doc_id]["methods"]["tfidf"] = result.score

        # Sort by combined score
        sorted_docs = sorted(
            combined_scores.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )

        # Create result objects
        final_results = []
        for doc_id, score_info in sorted_docs[:limit]:
            # Get content from any result set
            content = None
            for result in [bm25_results, neural_results, tfidf_results]:
                if result and result[0].doc_id == doc_id:
                    content = result[0].content
                    break

            final_result = RankingResult(
                doc_id=doc_id,
                content=content or "",
                score=score_info["total"],
                method_scores=score_info["methods"],
                metadata={"ensemble_method": "weighted_ensemble"},
            )
            final_results.append(final_result)

        return final_results


class AdvancedHybridSearcher:
    """
    Advanced hybrid searcher combining BM25 and learned ranking.

    Provides the best of both worlds:
    - BM25: Keyword-based, fast, interpretable
    - Neural: Semantic understanding, handles synonyms
    - Learned: Optimized combination of signals
    """

    def __init__(self, bm25_config: BM25Config = None, learned_weights: Dict[str, float] = None):
        """
        Initialize advanced hybrid searcher.

        Args:
            bm25_config: BM25 configuration
            learned_weights: Learned ranking weights
        """
        self.bm25 = BM25Ranker(bm25_config)
        self.learned = LearnedRanker(learned_weights)

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build search indexes.

        Args:
            documents: List of documents to index
        """
        self.bm25.build_index(documents)

    def search(
        self,
        query: str,
        neural_search_fn: Callable,
        tfidf_search_fn: Callable,
        limit: int = 10
    ) -> List[RankingResult]:
        """
        Search using advanced hybrid ranking.

        Args:
            query: Search query
            neural_search_fn: Function to perform neural search
            tfidf_search_fn: Function to perform TF-IDF search
            limit: Maximum number of results

        Returns:
            Ranked results
        """
        # BM25 search
        bm25_results = self.bm25.search(query, limit=limit)

        # Neural search
        neural_docs = neural_search_fn(query, limit)
        neural_results = [
            RankingResult(
                doc_id=d.get("id", ""),
                content=d.get("content", ""),
                score=d.get("score", 0.0),
            )
            for d in neural_docs
        ]

        # TF-IDF search
        tfidf_docs = tfidf_search_fn(query, limit)
        tfidf_results = [
            RankingResult(
                doc_id=d.get("id", ""),
                content=d.get("content", ""),
                score=d.get("score", 0.0),
            )
            for d in tfidf_docs
        ]

        # Learned ranking (ensemble)
        final_results = self.learned.rank(
            bm25_results,
            neural_results,
            tfidf_results,
            limit=limit
        )

        return final_results


def demo_advanced_hybrid():
    """Demonstrate advanced hybrid search."""
    print("\n=== Advanced Hybrid Search Demo ===\n")

    # Sample documents
    documents = [
        {"doc_id": 1, "content": "Database setup with PostgreSQL configuration"},
        {"doc_id": 2, "content": "API design using REST principles"},
        {"doc_id": 3, "content": "Memory management in Python programming"},
        {"doc_id": 4, "content": "PostgreSQL and MySQL relational databases"},
        {"doc_id": 5, "content": "Python memory optimization techniques"},
    ]

    # Initialize BM25 ranker
    print("1. Building BM25 index:")
    bm25_config = BM25Config(k1=1.5, b=0.75)
    bm25 = BM25Ranker(bm25_config)
    bm25.build_index(documents)
    print(f"   Indexed {len(bm25.documents)} documents")
    print(f"   Avg doc length: {bm25.avg_doc_length:.1f}")

    # BM25 search
    print("\n2. BM25 search for 'database':")
    bm25_results = bm25.search("database", limit=3)
    for i, result in enumerate(bm25_results, 1):
        print(f"   {i}. {result.doc_id}: {result.content[:50]}... (BM25: {result.score:.3f})")

    # Learned ranking
    print("\n3. Learned ranking (BM25 + Neural + TF-IDF):")
    learned = LearnedRanker(weights={"bm25": 0.4, "neural": 0.4, "tfidf": 0.2})

    # Simulate other ranking methods
    neural_results = [
        RankingResult(doc_id=1, content=documents[0]["content"], score=0.85),
        RankingResult(doc_id=4, content=documents[3]["content"], score=0.78),
    ]
    tfidf_results = [
        RankingResult(doc_id=1, content=documents[0]["content"], score=0.72),
        RankingResult(doc_id=4, content=documents[3]["content"], score=0.68),
    ]

    final_results = learned.rank(bm25_results, neural_results, tfidf_results, limit=3)
    for i, result in enumerate(final_results, 1):
        methods = ", ".join(f"{m}: {s:.2f}" for m, s in result.method_scores.items())
        print(f"   {i}. {result.doc_id}: {result.content[:50]}... (Ensemble: {result.score:.3f})")
        print(f"      Methods: {methods}")

    # Advanced hybrid search
    print("\n4. Advanced hybrid search:")

    def mock_neural_search(query, limit):
        """Mock neural search function."""
        return [
            {"id": d["doc_id"], "content": d["content"], "score": 0.9 - i*0.1}
            for i, d in enumerate(documents[:limit])
        ]

    def mock_tfidf_search(query, limit):
        """Mock TF-IDF search function."""
        return [
            {"id": d["doc_id"], "content": d["content"], "score": 0.8 - i*0.1}
            for i, d in enumerate(documents[:limit])
        ]

    hybrid = AdvancedHybridSearcher(bm25_config)
    hybrid.build_index(documents)

    hybrid_results = hybrid.search(
        "database",
        mock_neural_search,
        mock_tfidf_search,
        limit=3
    )

    for i, result in enumerate(hybrid_results, 1):
        methods = ", ".join(f"{m}: {s:.2f}" for m, s in result.method_scores.items())
        print(f"   {i}. {result.doc_id}: {result.content[:50]}... (Score: {result.score:.3f})")
        print(f"      Methods: {methods}")

    print("\n✅ Advanced hybrid search demo complete")


if __name__ == "__main__":
    demo_advanced_hybrid()
