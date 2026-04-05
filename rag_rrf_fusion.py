"""
Reciprocal Rank Fusion (RRF) for hybrid search.
Combines TF-IDF and neural search results using RRF algorithm.

Reference: Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning methods."
"""

from typing import List, Dict, Any, Tuple
import math


class RRFSearcher:
    """Reciprocal Rank Fusion for combining multiple search results."""

    def __init__(self, k: int = 60):
        """
        Initialize RRF searcher.

        Args:
            k: RRF constant (default 60). Higher k gives more weight to top results.
                Typical values: 50-100. 60 is standard.
        """
        self.k = k

    def fuse(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]],
        weights: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuse TF-IDF and neural results using RRF.

        Args:
            tfidf_results: List of TF-IDF results with 'doc_id' and 'score'
            neural_results: List of neural results with 'doc_id' and 'score'
            weights: Optional weights for each source. Defaults to {tfidf: 1.0, neural: 1.0}

        Returns:
            List of fused results sorted by combined score
        """
        if weights is None:
            weights = {"tfidf": 1.0, "neural": 1.0}

        # Initialize score dictionary
        rrf_scores: Dict[str, float] = {}
        doc_info: Dict[str, Dict[str, Any]] = {}

        # Process TF-IDF results
        for rank, result in enumerate(tfidf_results[:10]):  # Top 10 only
            doc_id = result.get("doc_id", result.get("id"))
            if not doc_id:
                continue

            # RRF score = 1 / (k + rank)
            rrf_score = 1.0 / (self.k + rank + 1)  # rank is 0-indexed

            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                doc_info[doc_id] = result

            rrf_scores[doc_id] += rrf_score * weights.get("tfidf", 1.0)

            # Track original TF-IDF rank
            if "tfidf_rank" not in doc_info[doc_id]:
                doc_info[doc_id]["tfidf_rank"] = rank + 1
                doc_info[doc_id]["tfidf_score"] = result.get("score", 0)

        # Process neural results
        for rank, result in enumerate(neural_results[:10]):  # Top 10 only
            doc_id = result.get("doc_id", result.get("id"))
            if not doc_id:
                continue

            # RRF score = 1 / (k + rank)
            rrf_score = 1.0 / (self.k + rank + 1)  # rank is 0-indexed

            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
                doc_info[doc_id] = result

            rrf_scores[doc_id] += rrf_score * weights.get("neural", 1.0)

            # Track original neural rank
            if "neural_rank" not in doc_info[doc_id]:
                doc_info[doc_id]["neural_rank"] = rank + 1
                doc_info[doc_id]["neural_score"] = result.get("score", 0)

        # Sort by combined RRF score
        sorted_docs = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build final results
        fused_results = []
        for doc_id, rrf_score in sorted_docs:
            result = doc_info[doc_id].copy()
            result["rrf_score"] = rrf_score
            result["fusion_method"] = "rrf"

            # Add fusion metadata
            metadata = {
                "rrf_score": round(rrf_score, 6),
                "tfidf_weight": weights.get("tfidf", 1.0),
                "neural_weight": weights.get("neural", 1.0),
            }

            if "tfidf_rank" in result:
                metadata["tfidf_rank"] = result["tfidf_rank"]
            if "neural_rank" in result:
                metadata["neural_rank"] = result["neural_rank"]

            result["fusion_metadata"] = metadata
            fused_results.append(result)

        return fused_results

    def fuse_multiple(
        self,
        result_sets: List[List[Dict[str, Any]]],
        names: List[str],
        weights: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuse multiple result sets (extensible for >2 sources).

        Args:
            result_sets: List of result sets (each with 'doc_id' and 'score')
            names: Names of each result set (e.g., ["tfidf", "neural", "bm25"])
            weights: Optional weights for each source

        Returns:
            List of fused results sorted by combined score
        """
        if weights is None:
            weights = {name: 1.0 for name in names}

        # Initialize score dictionary
        rrf_scores: Dict[str, float] = {}
        doc_info: Dict[str, Dict[str, Any]] = {}

        # Process each result set
        for result_set, name in zip(result_sets, names):
            for rank, result in enumerate(result_set[:10]):
                doc_id = result.get("doc_id", result.get("id"))
                if not doc_id:
                    continue

                # RRF score = 1 / (k + rank)
                rrf_score = 1.0 / (self.k + rank + 1)

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0.0
                    doc_info[doc_id] = result

                rrf_scores[doc_id] += rrf_score * weights.get(name, 1.0)

                # Track original rank
                rank_key = f"{name}_rank"
                if rank_key not in doc_info[doc_id]:
                    doc_info[doc_id][rank_key] = rank + 1

        # Sort by combined RRF score
        sorted_docs = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build final results
        fused_results = []
        for doc_id, rrf_score in sorted_docs:
            result = doc_info[doc_id].copy()
            result["rrf_score"] = rrf_score
            result["fusion_method"] = "rrf"
            fused_results.append(result)

        return fused_results

    def get_optimal_k(self, num_results: int = 10) -> int:
        """
        Get optimal k value based on number of results.

        Lower k = more spread, higher k = top results weighted more.

        Args:
            num_results: Number of results to consider

        Returns:
            Optimal k value
        """
        # Standard formula: k = num_results * 6
        # This gives reasonable weight distribution
        return max(num_results * 6, 20)  # Minimum 20


def demo_rrf():
    """Demonstrate RRF fusion."""
    print("\n=== RRF Fusion Demo ===\n")

    # Create searcher
    searcher = RRFSearcher(k=60)

    # Sample TF-IDF results (sparse, good for keyword matches)
    tfidf_results = [
        {"doc_id": 1, "content": "database setup configuration", "score": 0.85},
        {"doc_id": 2, "content": "user authentication flow", "score": 0.72},
        {"doc_id": 3, "content": "API endpoint design", "score": 0.68},
        {"doc_id": 5, "content": "memory management", "score": 0.45},
    ]

    # Sample neural results (dense, good for semantic matches)
    neural_results = [
        {"doc_id": 2, "content": "user authentication OAuth flow", "score": 0.92},
        {"doc_id": 3, "content": "RESTful API design patterns", "score": 0.88},
        {"doc_id": 4, "content": "database indexing optimization", "score": 0.81},
        {"doc_id": 5, "content": "efficient memory allocation", "score": 0.75},
    ]

    print("TF-IDF Results:")
    for i, r in enumerate(tfidf_results, 1):
        print(f"  {i}. Doc {r['doc_id']}: {r['content'][:50]} (score: {r['score']:.3f})")

    print("\nNeural Results:")
    for i, r in enumerate(neural_results, 1):
        print(f"  {i}. Doc {r['doc_id']}: {r['content'][:50]} (score: {r['score']:.3f})")

    # Fuse with equal weights
    fused = searcher.fuse(tfidf_results, neural_results)

    print("\n✅ Fused Results (RRF, equal weights):")
    for i, result in enumerate(fused, 1):
        meta = result["fusion_metadata"]
        print(f"  {i}. Doc {result['doc_id']}: {result['content'][:50]}")
        print(f"     RRF: {meta['rrf_score']:.6f}")
        if "tfidf_rank" in meta:
            print(f"     TF-IDF: #{meta['tfidf_rank']} (score: {meta.get('tfidf_score', 0):.3f})")
        if "neural_rank" in meta:
            print(f"     Neural: #{meta['neural_rank']} (score: {meta.get('neural_score', 0):.3f})")

    # Fuse with neural-weighted (semantic focus)
    fused_weighted = searcher.fuse(
        tfidf_results,
        neural_results,
        weights={"tfidf": 0.5, "neural": 1.0}
    )

    print("\n✅ Fused Results (RRF, neural-weighted):")
    for i, result in enumerate(fused_weighted[:3], 1):
        meta = result["fusion_metadata"]
        print(f"  {i}. Doc {result['doc_id']}: {result['content'][:50]} (RRF: {meta['rrf_score']:.6f})")


if __name__ == "__main__":
    demo_rrf()
