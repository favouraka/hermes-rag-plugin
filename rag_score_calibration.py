"""
Score Calibration for RAG Results
Implements Reciprocal Rank Fusion (RRF) and score normalization
for fair comparison across different retrieval methods
"""

import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CalibratedResult:
    """Calibrated search result."""
    content: str
    source_id: str
    namespace: str
    original_scores: Dict[str, float]  # Original scores from each method
    calibrated_score: float  # Final calibrated score
    rank: int  # Final rank
    metadata: Dict[str, Any]


class ScoreCalibrator:
    """
    Calibrates scores from multiple retrieval methods for fair comparison.

    Methods:
    - MinMax normalization: scales scores to [0, 1]
    - Z-score normalization: standardizes to mean=0, std=1
    - Reciprocal Rank Fusion (RRF): combines rankings, not scores
    - Borda count: rank aggregation
    """

    def __init__(self, k=60):
        """
        Initialize score calibrator.

        Args:
            k: RRF constant (default 60, balances precision vs diversity)
        """
        self.k = k
        self.calibration_history: List[Dict[str, Any]] = []

    def minmax_normalize(
        self,
        scores: Dict[str, float],
        invert: bool = True
    ) -> Dict[str, float]:
        """
        MinMax normalization: scales scores to [0, 1].

        Args:
            scores: Dict of source_id -> score
            invert: If True, lower scores are better (like distance)

        Returns:
            Dict of source_id -> normalized score [0, 1]
        """
        if not scores:
            return {}

        values = list(scores.values())
        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return {k: 0.5 for k in scores}

        normalized = {}
        for source_id, score in scores.items():
            if invert:
                # Lower is better: normalize so lower -> higher (closer to 1)
                normalized[source_id] = 1.0 - (score - min_val) / (max_val - min_val)
            else:
                # Higher is better
                normalized[source_id] = (score - min_val) / (max_val - min_val)

        return normalized

    def zscore_normalize(
        self,
        scores: Dict[str, float],
        invert: bool = True
    ) -> Dict[str, float]:
        """
        Z-score normalization: standardizes to mean=0, std=1.

        Args:
            scores: Dict of source_id -> score
            invert: If True, lower scores are better

        Returns:
            Dict of source_id -> z-score
        """
        if not scores:
            return {}

        values = list(scores.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1.0

        normalized = {}
        for source_id, score in scores.items():
            if invert:
                zscore = (mean - score) / std
            else:
                zscore = (score - mean) / std
            normalized[source_id] = zscore

        return normalized

    def reciprocal_rank_fusion(
        self,
        rankings: List[Dict[str, int]]
    ) -> Dict[str, float]:
        """
        Reciprocal Rank Fusion (RRF) - combines rankings, not scores.

        Formula: RRF(d) = sum(k / (rank + k)) for each method

        Args:
            rankings: List of dicts, each is source_id -> rank (1-indexed)

        Returns:
            Dict of source_id -> RRF score
        """
        rrf_scores = defaultdict(float)

        for ranking in rankings:
            for source_id, rank in ranking.items():
                rrf_scores[source_id] += self.k / (rank + self.k)

        return dict(rrf_scores)

    def calibrate_hybrid(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]],
        method: str = "rrf",
        tfidf_weight: float = 0.3,
        neural_weight: float = 0.7
    ) -> List[CalibratedResult]:
        """
        Calibrate hybrid search results from multiple retrieval methods.

        Args:
            tfidf_results: List of TF-IDF results
            neural_results: List of Neural results
            method: Calibration method ("rrf", "weighted", "borda")
            tfidf_weight: Weight for TF-IDF (for weighted method)
            neural_weight: Weight for Neural (for weighted method)

        Returns:
            List of CalibratedResult
        """
        # Create rankings for RRF
        tfidf_ranking = {r['source_id']: i+1 for i, r in enumerate(tfidf_results)}
        neural_ranking = {r['source_id']: i+1 for i, r in enumerate(neural_results)}

        # Create score dicts for weighted fusion
        tfidf_scores = {r['source_id']: r['distance'] for r in tfidf_results}
        neural_scores = {r['source_id']: r['distance'] for r in neural_results}

        # Normalize scores
        tfidf_normalized = self.minmax_normalize(tfidf_scores, invert=True)
        neural_normalized = self.minmax_normalize(neural_scores, invert=True)

        # Apply calibration method
        if method == "rrf":
            # Reciprocal Rank Fusion
            rrf_scores = self.reciprocal_rank_fusion([tfidf_ranking, neural_ranking])
            final_scores = rrf_scores

        elif method == "weighted":
            # Weighted average of normalized scores
            all_source_ids = set(tfidf_scores.keys()) | set(neural_scores.keys())
            final_scores = {}
            for source_id in all_source_ids:
                tfidf_score = tfidf_normalized.get(source_id, 0.0)
                neural_score = neural_normalized.get(source_id, 0.0)
                final_scores[source_id] = (
                    tfidf_weight * tfidf_score +
                    neural_weight * neural_score
                )

        elif method == "borda":
            # Borda count (sum of rankings)
            all_source_ids = set(tfidf_ranking.keys()) | set(neural_ranking.keys())
            max_rank = max(len(tfidf_ranking), len(neural_ranking))
            final_scores = {}
            for source_id in all_source_ids:
                tfidf_r = tfidf_ranking.get(source_id, max_rank + 1)
                neural_r = neural_ranking.get(source_id, max_rank + 1)
                # Lower total rank = better
                final_scores[source_id] = max_rank * 2 - (tfidf_r + neural_r)

        else:
            raise ValueError(f"Unknown method: {method}")

        # Build calibrated results
        content_lookup = {}
        for r in tfidf_results:
            content_lookup[r['source_id']] = r
        for r in neural_results:
            content_lookup[r['source_id']] = r

        calibrated = []
        for source_id, score in sorted(final_scores.items(), key=lambda x: -x[1]):
            content = content_lookup[source_id]
            calibrated.append(CalibratedResult(
                content=content['content'],
                source_id=source_id,
                namespace=content.get('namespace', ''),
                original_scores={
                    'tfidf_distance': tfidf_scores.get(source_id, float('inf')),
                    'tfidf_normalized': tfidf_normalized.get(source_id, 0.0),
                    'neural_distance': neural_scores.get(source_id, float('inf')),
                    'neural_normalized': neural_normalized.get(source_id, 0.0),
                },
                calibrated_score=score,
                rank=len(calibrated) + 1,
                metadata=content.get('metadata', {})
            ))

        # Store history for analysis
        self.calibration_history.append({
            'method': method,
            'results_count': len(calibrated),
            'timestamp': datetime.now().isoformat()
        })

        return calibrated

    def adaptive_fusion(
        self,
        tfidf_results: List[Dict[str, Any]],
        neural_results: List[Dict[str, Any]],
        query: str,
        keyword_threshold: float = 0.7
    ) -> Tuple[List[CalibratedResult], float]:
        """
        Adaptive fusion: adjust weights based on query type.

        - Keyword queries: more TF-IDF weight
        - Semantic queries: more Neural weight
        - Mixed queries: balanced weights

        Args:
            tfidf_results: TF-IDF results
            neural_results: Neural results
            query: Search query
            keyword_threshold: Threshold for keyword detection

        Returns:
            (Calibrated results, TF-IDF weight used)
        """
        # Detect query type
        keyword_score = self._detect_keyword_query(query)
        neural_score = 1.0 - keyword_score

        # Adapt weights
        tfidf_weight = keyword_score * 0.7 + 0.3  # Range: [0.3, 1.0]
        neural_weight = neural_score * 0.7 + 0.3  # Range: [0.3, 1.0]

        # Normalize to sum to 1.0
        total = tfidf_weight + neural_weight
        tfidf_weight /= total
        neural_weight /= total

        # Calibrate with adaptive weights
        calibrated = self.calibrate_hybrid(
            tfidf_results,
            neural_results,
            method="weighted",
            tfidf_weight=tfidf_weight,
            neural_weight=neural_weight
        )

        return calibrated, tfidf_weight

    def _detect_keyword_query(self, query: str) -> float:
        """
        Detect if query is keyword-focused.

        Returns:
            Score from 0.0 (pure semantic) to 1.0 (pure keyword)
        """
        # Keyword indicators
        keywords = query.lower().split()

        # Exact phrase matches (quoted)
        exact_phrases = query.count('"') // 2

        # Specific technical terms
        technical_terms = ['sql', 'api', 'http', 'ssh', 'port', 'ip', 'db', 'database']

        # Keyword indicators
        keyword_indicators = 0
        for word in keywords:
            if word in technical_terms:
                keyword_indicators += 1

        # Calculate score
        score = 0.0

        # Exact phrases: strongly keyword
        if exact_phrases > 0:
            score += 0.4 * exact_phrases

        # Technical terms: moderately keyword
        if keyword_indicators > 0:
            score += 0.3 * (keyword_indicators / len(keywords))

        # Short queries: more likely keyword
        if len(keywords) <= 3:
            score += 0.2
        elif len(keywords) >= 6:
            score -= 0.2

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def get_calibration_stats(self) -> Dict[str, Any]:
        """Get statistics about calibration history."""
        if not self.calibration_history:
            return {"total_calibrations": 0}

        method_counts = defaultdict(int)
        result_counts = []

        for entry in self.calibration_history:
            method_counts[entry['method']] += 1
            result_counts.append(entry['results_count'])

        return {
            "total_calibrations": len(self.calibration_history),
            "methods_used": dict(method_counts),
            "avg_results_per_calibration": sum(result_counts) / len(result_counts),
            "min_results": min(result_counts),
            "max_results": max(result_counts),
        }


def demo_score_calibration():
    """Demonstrate score calibration."""

    print("=" * 70)
    print("Score Calibration Demo")
    print("=" * 70)

    calibrator = ScoreCalibrator(k=60)

    # Sample results
    tfidf_results = [
        {'source_id': 'doc1', 'content': 'SQL database query optimization', 'distance': 0.12},
        {'source_id': 'doc2', 'content': 'Python API development guide', 'distance': 0.35},
        {'source_id': 'doc3', 'content': 'SSH port configuration', 'distance': 0.28},
        {'source_id': 'doc4', 'content': 'HTTP server setup', 'distance': 0.45},
    ]

    neural_results = [
        {'source_id': 'doc3', 'content': 'SSH port configuration', 'distance': 0.18},
        {'source_id': 'doc1', 'content': 'SQL database query optimization', 'distance': 0.22},
        {'source_id': 'doc4', 'content': 'HTTP server setup', 'distance': 0.35},
        {'source_id': 'doc2', 'content': 'Python API development guide', 'distance': 0.42},
    ]

    print("\n1. TF-IDF Results (sorted by distance):")
    for i, r in enumerate(tfidf_results, 1):
        print(f"   {i}. {r['content']:40} distance: {r['distance']:.3f}")

    print("\n2. Neural Results (sorted by distance):")
    for i, r in enumerate(neural_results, 1):
        print(f"   {i}. {r['content']:40} distance: {r['distance']:.3f}")

    # Test different calibration methods
    methods = ["rrf", "weighted", "borda"]

    for method in methods:
        print(f"\n{'='*70}")
        print(f"Calibration Method: {method.upper()}")
        print(f"{'='*70}")

        calibrated = calibrator.calibrate_hybrid(
            tfidf_results,
            neural_results,
            method=method
        )

        print("\nCalibrated Results:")
        for result in calibrated:
            print(f"\n{result.rank}. {result.content}")
            print(f"   Original scores:")
            print(f"     TF-IDF distance: {result.original_scores['tfidf_distance']:.3f}")
            print(f"     TF-IDF normalized: {result.original_scores['tfidf_normalized']:.3f}")
            print(f"     Neural distance: {result.original_scores['neural_distance']:.3f}")
            print(f"     Neural normalized: {result.original_scores['neural_normalized']:.3f}")
            print(f"   Calibrated score: {result.calibrated_score:.4f}")

    # Test adaptive fusion
    print(f"\n{'='*70}")
    print("Adaptive Fusion")
    print(f"{'='*70}")

    queries = [
        ("SQL query optimization",  # Technical, keyword-heavy
         "How do I optimize database queries?"),
        ("semantic search",  # Semantic
         "What is the best way to find similar documents?"),
    ]

    for query_type, query in queries:
        calibrated, tfidf_weight = calibrator.adaptive_fusion(
            tfidf_results,
            neural_results,
            query=query
        )

        print(f"\nQuery: \"{query}\"")
        print(f"Detected as: {query_type}")
        print(f"TF-IDF weight: {tfidf_weight:.2f}, Neural weight: {1.0-tfidf_weight:.2f}")
        print("\nTop 3 calibrated results:")
        for result in calibrated[:3]:
            print(f"   {result.rank}. {result.content[:50]}... (score: {result.calibrated_score:.4f})")

    # Stats
    print(f"\n{'='*70}")
    print("Calibration Statistics")
    print(f"{'='*70}")

    stats = calibrator.get_calibration_stats()
    print(f"\nTotal calibrations: {stats['total_calibrations']}")
    print(f"Methods used: {stats['methods_used']}")
    if stats['total_calibrations'] > 0:
        print(f"Avg results per calibration: {stats['avg_results_per_calibration']:.1f}")

    print("\n✅ Score calibration demo complete!")


if __name__ == "__main__":
    from datetime import datetime
    demo_score_calibration()
