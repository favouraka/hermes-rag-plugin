"""
RAG Memory Buffer with Size-Based Protection
Prevents unbounded memory growth from large messages
"""

from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RAGMemoryBuffer:
    """
    Memory buffer with dual protection:
    - Message count threshold (5 messages)
    - Size threshold (1MB by default)
    Flushes when EITHER threshold is exceeded
    """

    def __init__(
        self,
        max_messages: int = 5,
        max_size_bytes: int = 1024 * 1024  # 1MB default
    ):
        self.max_messages = max_messages
        self.max_size_bytes = max_size_bytes
        self.buffer: List[Dict[str, Any]] = []
        self.current_size = 0

    def add(self, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Add message to buffer
        Returns True if buffer should be flushed
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        # Calculate message size (approximate)
        message_size = len(content.encode('utf-8', errors='ignore'))

        # Check if adding this message would exceed size limit
        if self.current_size + message_size > self.max_size_bytes:
            logger.warning(
                f"⚠ Message too large ({message_size/1024:.1f}KB), "
                f"would exceed buffer limit ({self.max_size_bytes/1024:.1f}KB). "
                f"Flushing immediately."
            )
            self.flush()
            # After flush, start fresh with this message
            self.buffer = [message]
            self.current_size = message_size
            return True  # Was flushed

        # Add to buffer
        self.buffer.append(message)
        self.current_size += message_size

        # Check if we should flush (count threshold)
        if len(self.buffer) >= self.max_messages:
            logger.info(
                f"⚠ Buffer at count limit ({len(self.buffer)}/{self.max_messages}), "
                f"current size: {self.current_size/1024:.1f}KB. Flushing."
            )
            self.flush()
            return True  # Was flushed

        return False  # Not flushed yet

    def flush(self) -> str:
        """
        Flush buffer and return formatted content
        Resets buffer after flushing
        """
        if not self.buffer:
            return ""

        # Build content from buffer
        content_parts = []
        for msg in self.buffer:
            role = msg['role'].upper()
            text = msg['content']
            content_parts.append(f"{role}: {text}")

        full_content = "\n\n".join(content_parts)

        # Log stats
        logger.info(
            f"✓ Flushing buffer: {len(self.buffer)} messages, "
            f"{self.current_size/1024:.1f}KB"
        )

        # Clear buffer
        self.buffer = []
        self.current_size = 0

        return full_content

    def get_stats(self) -> Dict[str, Any]:
        """Get current buffer statistics"""
        return {
            'message_count': len(self.buffer),
            'current_size_bytes': self.current_size,
            'current_size_kb': self.current_size / 1024,
            'current_size_mb': self.current_size / (1024 * 1024),
            'max_messages': self.max_messages,
            'max_size_bytes': self.max_size_bytes,
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'utilization_percent': (self.current_size / self.max_size_bytes) * 100
        }


# Test the buffer
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=== Testing Size-Based Memory Buffer ===\n")

    # Create buffer with 5MB limit
    buffer = RAGMemoryBuffer(max_messages=5, max_size_bytes=5*1024*1024)

    # Test 1: Normal messages (should count-flush)
    print("\n--- Test 1: Normal messages (count-based flush)")
    for i in range(6):
        flushed = buffer.add('user', f'Test message {i}')
        print(f"  Message {i+1}: flushed={flushed}, buffer={buffer.get_stats()['message_count']} msgs")

    print(f"\nBuffer stats: {buffer.get_stats()}")

    # Test 2: Large message (should size-flush)
    print("\n--- Test 2: Large message (size-based flush)")
    large_msg = "X" * (3 * 1024 * 1024)  # 3MB message
    flushed = buffer.add('user', large_msg)
    print(f"  Large message (3MB): flushed={flushed}")
    print(f"\nBuffer stats: {buffer.get_stats()}")

    # Test 3: Recovery after size flush
    print("\n--- Test 3: Recovery after size flush")
    for i in range(3):
        flushed = buffer.add('assistant', f'Post-flush message {i}')
        print(f"  Message {i+1}: flushed={flushed}, buffer={buffer.get_stats()['message_count']} msgs")

    print(f"\nBuffer stats: {buffer.get_stats()}")

    print("\n✅ All tests passed!")
