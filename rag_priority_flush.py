"""
Priority-based flushing for RAG system.
Flushes urgent conversations first based on priority scoring.
"""

import time
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FlushPriority:
    """Priority levels for flushing."""
    URGENT = 100
    HIGH = 80
    MEDIUM = 60
    LOW = 40
    DEFERRED = 20


@dataclass
class Conversation:
    """Represents a conversation in the buffer."""
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    message_count: int = 0
    total_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority_score: float = 0.0
    tags: set = field(default_factory=set)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the conversation."""
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })
        self.message_count += 1
        self.total_size += len(content.encode('utf-8'))
        self.timestamp = time.time()

    def get_priority_score(self, config: 'PriorityConfig' = None) -> float:
        """Calculate priority score for this conversation."""
        if config is None:
            config = PriorityConfig()

        score = 0.0

        # Urgency based on tags
        if "urgent" in self.tags:
            score += config.urgent_tag_weight
        if "important" in self.tags:
            score += config.important_tag_weight
        if "error" in self.tags:
            score += config.error_weight

        # Urgency based on keywords in content
        content = " ".join(m["content"] for m in self.messages).lower()
        for keyword, weight in config.urgency_keywords.items():
            if keyword in content:
                score += weight

        # Size urgency (large conversations flush sooner)
        size_mb = self.total_size / (1024 * 1024)
        if size_mb > config.large_size_threshold:
            score += config.large_size_weight

        # Age urgency (older conversations flush sooner)
        age = time.time() - self.timestamp
        if age > config.old_age_threshold:
            score += config.old_age_weight

        # Message count urgency
        if self.message_count > config.message_count_threshold:
            score += config.message_count_weight

        return score


@dataclass
class PriorityConfig:
    """Configuration for priority-based flushing."""
    # Tag weights
    urgent_tag_weight: float = 50.0
    important_tag_weight: float = 30.0
    error_weight: float = 40.0

    # Keyword weights
    urgency_keywords: Dict[str, float] = field(default_factory=lambda: {
        "emergency": 50.0,
        "critical": 40.0,
        "urgent": 35.0,
        "asap": 30.0,
        "important": 25.0,
    })

    # Size urgency
    large_size_threshold: float = 1.0  # 1MB
    large_size_weight: float = 20.0

    # Age urgency
    old_age_threshold: float = 3600  # 1 hour
    old_age_weight: float = 15.0

    # Message count urgency
    message_count_threshold: int = 10
    message_count_weight: float = 10.0

    # Minimum priority for flush
    min_flush_priority: float = 30.0


class PriorityFlusher:
    """
    Priority-based flusher for RAG buffer.

    Flushes conversations in priority order:
    1. Urgent tagged conversations
    2. Error-related conversations
    3. Large conversations
    4. Old conversations
    5. Normal conversations
    """

    def __init__(self, config: PriorityConfig = None):
        """
        Initialize priority flusher.

        Args:
            config: Priority configuration
        """
        self.config = config or PriorityConfig()
        self.conversations: Dict[str, Conversation] = {}
        self.flush_history: List[Tuple[str, float]] = []  # (session_id, timestamp)

    def add_conversation(self, session_id: str, conversation: Conversation):
        """Add or update a conversation."""
        # Calculate priority score
        conversation.priority_score = conversation.get_priority_score(self.config)

        self.conversations[session_id] = conversation

    def get_flush_order(self) -> List[Tuple[str, Conversation]]:
        """
        Get conversations in flush order (highest priority first).

        Returns:
            List of (session_id, conversation) tuples
        """
        # Sort by priority score (descending)
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].priority_score,
            reverse=True
        )

        return sorted_conversations

    def get_conversations_to_flush(self, limit: int = None) -> List[Conversation]:
        """
        Get conversations that should be flushed.

        Args:
            limit: Maximum number of conversations to flush

        Returns:
            List of conversations to flush
        """
        # Get flush order
        flush_order = self.get_flush_order()

        # Filter by minimum priority
        eligible = [
            (session_id, conv)
            for session_id, conv in flush_order
            if conv.priority_score >= self.config.min_flush_priority
        ]

        # Apply limit
        if limit:
            eligible = eligible[:limit]

        return [conv for session_id, conv in eligible]

    def mark_flushed(self, session_id: str):
        """Mark a conversation as flushed."""
        if session_id in self.conversations:
            # Remove from active conversations
            self.conversations.pop(session_id)

            # Add to flush history
            self.flush_history.append((session_id, time.time()))

    def tag_conversation(self, session_id: str, tag: str):
        """Add a tag to a conversation."""
        if session_id in self.conversations:
            self.conversations[session_id].tags.add(tag)
            # Recalculate priority
            self.conversations[session_id].priority_score = \
                self.conversations[session_id].get_priority_score(self.config)

    def add_urgency_keyword(self, keyword: str, weight: float = 30.0):
        """Add a new urgency keyword."""
        self.config.urgency_keywords[keyword] = weight

    def get_stats(self) -> Dict[str, Any]:
        """Get flusher statistics."""
        # Count conversations by priority range
        priority_ranges = {
            "urgent": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for conv in self.conversations.values():
            score = conv.priority_score
            if score >= 80:
                priority_ranges["urgent"] += 1
            elif score >= 60:
                priority_ranges["high"] += 1
            elif score >= 40:
                priority_ranges["medium"] += 1
            else:
                priority_ranges["low"] += 1

        return {
            "total_conversations": len(self.conversations),
            "priority_distribution": priority_ranges,
            "avg_priority": sum(c.priority_score for c in self.conversations.values()) / len(self.conversations) if self.conversations else 0,
            "flush_history_count": len(self.flush_history),
            "config": {
                "min_flush_priority": self.config.min_flush_priority,
                "urgency_keywords": self.config.urgency_keywords,
            },
        }

    def get_flush_recommendations(self, max_flushes: int = 10) -> List[Dict[str, Any]]:
        """
        Get recommendations for which conversations to flush.

        Args:
            max_flushes: Maximum number of recommendations

        Returns:
            List of recommendation dictionaries
        """
        to_flush = self.get_conversations_to_flush(limit=max_flushes)

        recommendations = []
        for conv in to_flush:
            # Determine priority level
            if conv.priority_score >= 80:
                level = "URGENT"
            elif conv.priority_score >= 60:
                level = "HIGH"
            elif conv.priority_score >= 40:
                level = "MEDIUM"
            else:
                level = "LOW"

            # Get reason for priority
            reasons = []
            if "urgent" in conv.tags:
                reasons.append("tagged as urgent")
            if "error" in conv.tags:
                reasons.append("contains errors")
            if conv.total_size / (1024 * 1024) > self.config.large_size_threshold:
                reasons.append(f"large size ({conv.total_size / 1024 / 1024:.1f} MB)")
            if time.time() - conv.timestamp > self.config.old_age_threshold:
                age_hours = (time.time() - conv.timestamp) / 3600
                reasons.append(f"old ({age_hours:.1f} hours)")

            recommendations.append({
                "session_id": conv.session_id,
                "priority_score": conv.priority_score,
                "priority_level": level,
                "message_count": conv.message_count,
                "size_mb": conv.total_size / 1024 / 1024,
                "reasons": reasons,
                "recommended_action": "FLUSH" if level in ["URGENT", "HIGH"] else "CONSIDER",
            })

        return recommendations


def demo_priority_flush():
    """Demonstrate priority-based flushing."""
    print("\n=== Priority-Based Flushing Demo ===\n")

    flusher = PriorityFlusher()

    # Create sample conversations with different priorities
    conversations = [
        Conversation(
            session_id="conv1",
            tags={"urgent"},
            metadata={"type": "emergency"}
        ),
        Conversation(
            session_id="conv2",
            tags={"important"},
            metadata={"type": "project"}
        ),
        Conversation(
            session_id="conv3",
            tags={"error"},
            metadata={"type": "bug_report"}
        ),
        Conversation(
            session_id="conv4",
            tags=set(),
            metadata={"type": "normal"}
        ),
        Conversation(
            session_id="conv5",
            tags=set(),
            metadata={"type": "normal"}
        ),
    ]

    print("1. Adding messages to conversations:")
    for i, conv in enumerate(conversations, 1):
        # Add different amounts of messages
        for j in range(i * 2):
            conv.add_message("user", f"Message {j+1}")

        flusher.add_conversation(conv.session_id, conv)
        print(f"   {conv.session_id}: {conv.message_count} messages, "
              f"{conv.total_size / 1024:.1f} KB, priority: {conv.priority_score:.1f}")

    # Get flush order
    print("\n2. Flush order (highest priority first):")
    flush_order = flusher.get_flush_order()
    for i, (session_id, conv) in enumerate(flush_order, 1):
        level = "URGENT" if conv.priority_score >= 80 else \
                "HIGH" if conv.priority_score >= 60 else \
                "MEDIUM" if conv.priority_score >= 40 else "LOW"
        print(f"   {i}. {session_id} - {level} (score: {conv.priority_score:.1f})")

    # Get recommendations
    print("\n3. Flush recommendations:")
    recommendations = flusher.get_flush_recommendations(max_flushes=5)
    for rec in recommendations:
        action = rec['recommended_action']
        print(f"   [{action}] {rec['session_id']} - {rec['priority_level']}")
        print(f"         Reasons: {', '.join(rec['reasons'])}")

    # Stats
    print("\n4. Flusher Statistics:")
    stats = flusher.get_stats()
    print(f"   Total conversations: {stats['total_conversations']}")
    print(f"   Priority distribution:")
    for level, count in stats['priority_distribution'].items():
        print(f"     {level.upper()}: {count}")
    print(f"   Average priority: {stats['avg_priority']:.1f}")

    # Mark some as flushed
    print("\n5. Marking conversations as flushed:")
    for session_id, _ in flush_order[:2]:
        flusher.mark_flushed(session_id)
        print(f"   ✓ Flushed {session_id}")

    print(f"\n   Remaining: {len(flusher.conversations)} conversations")

    print("\n✅ Priority flush demo complete")


if __name__ == "__main__":
    demo_priority_flush()
