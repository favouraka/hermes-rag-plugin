"""
Time-based decay for RAG system.
Adjusts relevance scores based on document age.
"""

import time
import math
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DecayConfig:
    """Configuration for time-based decay."""
    decay_type: str = "exponential"  # exponential, linear, logarithmic
    half_life: float = 86400.0  # 24 hours in seconds
    min_score: float = 0.1  # Minimum score after decay
    boost_recent: bool = True  # Boost recent documents
    boost_hours: int = 24  # Boost documents younger than this
    boost_factor: float = 1.5  # Boost multiplier


class TimeDecayScorer:
    """
    Applies time-based decay to search results.

    Older documents get lower scores, newer documents get boosted.
    """

    def __init__(self, config: DecayConfig = None):
        """
        Initialize decay scorer.

        Args:
            config: Decay configuration
        """
        self.config = config or DecayConfig()

    def decay_score(self, score: float, timestamp: float, current_time: float = None) -> float:
        """
        Apply time-based decay to a score.

        Args:
            score: Original relevance score
            timestamp: Document timestamp (Unix timestamp)
            current_time: Current time (defaults to now)

        Returns:
            Decayed score
        """
        if current_time is None:
            current_time = time.time()

        # Calculate age in seconds
        age = current_time - timestamp
        age_hours = age / 3600.0

        # Apply decay based on type
        if self.config.decay_type == "exponential":
            decay_factor = self._exponential_decay(age)
        elif self.config.decay_type == "linear":
            decay_factor = self._linear_decay(age)
        elif self.config.decay_type == "logarithmic":
            decay_factor = self._logarithmic_decay(age)
        else:
            decay_factor = 1.0

        # Apply decay to score
        decayed_score = score * decay_factor

        # Ensure minimum score
        decayed_score = max(decayed_score, self.config.min_score)

        # Apply boost for recent documents
        if self.config.boost_recent and age_hours < self.config.boost_hours:
            decayed_score *= self.config.boost_factor

        return decayed_score

    def _exponential_decay(self, age_seconds: float) -> float:
        """
        Exponential decay: score * (1/2)^(age/half_life)

        Args:
            age_seconds: Document age in seconds

        Returns:
            Decay factor (0-1)
        """
        # Calculate number of half-lives
        half_lives = age_seconds / self.config.half_life

        # Exponential decay
        decay_factor = math.pow(0.5, half_lives)

        return max(decay_factor, self.config.min_score)

    def _linear_decay(self, age_seconds: float) -> float:
        """
        Linear decay: score * (1 - age/max_age)

        Args:
            age_seconds: Document age in seconds

        Returns:
            Decay factor (0-1)
        """
        # Max age before score reaches minimum
        max_age = self.config.half_life * 2

        # Linear decay
        decay_factor = 1.0 - (age_seconds / max_age)

        return max(decay_factor, self.config.min_score)

    def _logarithmic_decay(self, age_seconds: float) -> float:
        """
        Logarithmic decay: slower decay over time

        Args:
            age_seconds: Document age in seconds

        Returns:
            Decay factor (0-1)
        """
        # Logarithmic decay
        decay_factor = 1.0 - (math.log(1 + age_seconds / self.config.half_life) / 10)

        return max(decay_factor, self.config.min_score)

    def decay_results(self, results: List[Dict[str, Any]], current_time: float = None) -> List[Dict[str, Any]]:
        """
        Apply time-based decay to search results.

        Args:
            results: List of search results
            current_time: Current time (defaults to now)

        Returns:
            Decayed results with new scores
        """
        if current_time is None:
            current_time = time.time()

        decayed_results = []

        for result in results:
            # Get original score and timestamp
            original_score = result.get("score", 0.0)
            timestamp = result.get("timestamp", current_time)

            # Apply decay
            decayed_score = self.decay_score(original_score, timestamp, current_time)

            # Create new result with decayed score
            decayed_result = result.copy()
            decayed_result["original_score"] = original_score
            decayed_result["decayed_score"] = decayed_score
            decayed_result["score"] = decayed_score  # Update main score
            decayed_result["decay_factor"] = decayed_score / original_score if original_score > 0 else 1.0

            decayed_results.append(decayed_result)

        return decayed_results

    def get_decay_info(self, timestamp: float, current_time: float = None) -> Dict[str, Any]:
        """
        Get decay information for a document.

        Args:
            timestamp: Document timestamp
            current_time: Current time (defaults to now)

        Returns:
            Decay information dictionary
        """
        if current_time is None:
            current_time = time.time()

        age = current_time - timestamp
        age_hours = age / 3600.0
        age_days = age / 86400.0

        if self.config.decay_type == "exponential":
            decay_factor = self._exponential_decay(age)
        elif self.config.decay_type == "linear":
            decay_factor = self._linear_decay(age)
        elif self.config.decay_type == "logarithmic":
            decay_factor = self._logarithmic_decay(age)
        else:
            decay_factor = 1.0

        boost_applied = False
        if self.config.boost_recent and age_hours < self.config.boost_hours:
            boost_applied = True
            decay_factor *= self.config.boost_factor

        return {
            "age_seconds": age,
            "age_hours": age_hours,
            "age_days": age_days,
            "decay_factor": decay_factor,
            "boost_applied": boost_applied,
            "decay_type": self.config.decay_type,
        }


def demo_time_decay():
    """Demonstrate time-based decay."""
    print("\n=== Time-Based Decay Demo ===\n")

    # Test different decay types
    configs = [
        DecayConfig(decay_type="exponential", half_life=86400),  # 24 hours
        DecayConfig(decay_type="linear", half_life=86400),
        DecayConfig(decay_type="logarithmic", half_life=86400),
    ]

    # Sample documents with different ages
    current_time = time.time()
    documents = [
        {"id": 1, "score": 0.9, "timestamp": current_time - 0, "name": "Just now"},
        {"id": 2, "score": 0.9, "timestamp": current_time - 3600, "name": "1 hour ago"},  # 1 hour
        {"id": 3, "score": 0.9, "timestamp": current_time - 43200, "name": "12 hours ago"},  # 12 hours
        {"id": 4, "score": 0.9, "timestamp": current_time - 86400, "name": "24 hours ago"},  # 24 hours
        {"id": 5, "score": 0.9, "timestamp": current_time - 259200, "name": "3 days ago"},  # 72 hours
        {"id": 6, "score": 0.9, "timestamp": current_time - 604800, "name": "1 week ago"},  # 7 days
    ]

    print("1. Decay by type (original score: 0.9):")
    print(f"   {'Document':<15} {'Exponential':<12} {'Linear':<12} {'Logarithmic':<12}")
    print(f"   {'-'*15} {'-'*12} {'-'*12} {'-'*12}")

    for doc in documents:
        exp_scorer = TimeDecayScorer(configs[0])
        lin_scorer = TimeDecayScorer(configs[1])
        log_scorer = TimeDecayScorer(configs[2])

        exp_score = exp_scorer.decay_score(doc["score"], doc["timestamp"], current_time)
        lin_score = lin_scorer.decay_score(doc["score"], doc["timestamp"], current_time)
        log_score = log_scorer.decay_score(doc["score"], doc["timestamp"], current_time)

        print(f"   {doc['name']:<15} {exp_score:<12.3f} {lin_score:<12.3f} {log_score:<12.3f}")

    # Test boost for recent documents
    print("\n2. Boost recent documents:")
    boost_config = DecayConfig(
        decay_type="exponential",
        half_life=86400,
        boost_recent=True,
        boost_hours=24,
        boost_factor=1.5
    )
    scorer = TimeDecayScorer(boost_config)

    print(f"   {'Document':<15} {'Original':<12} {'Decayed':<12} {'Boosted':<12}")
    print(f"   {'-'*15} {'-'*12} {'-'*12} {'-'*12}")

    for doc in documents:
        no_boost_scorer = TimeDecayScorer(DecayConfig(decay_type="exponential", half_life=86400))
        decayed = no_boost_scorer.decay_score(doc["score"], doc["timestamp"], current_time)
        boosted = scorer.decay_score(doc["score"], doc["timestamp"], current_time)

        print(f"   {doc['name']:<15} {doc['score']:<12.3f} {decayed:<12.3f} {boosted:<12.3f}")

    # Test with search results
    print("\n3. Decay search results:")
    search_results = [
        {"doc_id": 1, "content": "Recent document", "score": 0.85, "timestamp": current_time - 1800},
        {"doc_id": 2, "content": "Older document", "score": 0.90, "timestamp": current_time - 86400},
        {"doc_id": 3, "content": "Very old document", "score": 0.95, "timestamp": current_time - 604800},
    ]

    scorer = TimeDecayScorer()
    decayed = scorer.decay_results(search_results, current_time)

    print(f"   {'Document':<20} {'Original':<12} {'Decayed':<12} {'Factor':<12}")
    print(f"   {'-'*20} {'-'*12} {'-'*12} {'-'*12}")

    for i, result in enumerate(decayed):
        print(f"   {result['content']:<20} {result['original_score']:<12.3f} "
              f"{result['decayed_score']:<12.3f} {result['decay_factor']:<12.3f}")

    # Decay info
    print("\n4. Decay information for documents:")
    for doc in documents[:3]:
        info = scorer.get_decay_info(doc["timestamp"], current_time)
        print(f"   {doc['name']}:")
        print(f"     Age: {info['age_hours']:.1f} hours ({info['age_days']:.1f} days)")
        print(f"     Decay factor: {info['decay_factor']:.3f}")
        print(f"     Boost applied: {info['boost_applied']}")

    print("\n✅ Time decay demo complete")


if __name__ == "__main__":
    demo_time_decay()
