"""
Configurable Capture Thresholds for RAG Auto-Capture
Controls when to flush conversation buffers based on message count and size limits
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class CaptureConfig:
    """Configuration for auto-capture thresholds."""

    # Message-based thresholds
    min_messages_to_capture: int = 3  # Minimum messages before capture
    max_messages_before_flush: int = 10  # Flush after N messages
    urgent_flush_messages: int = 20  # Force flush after N messages

    # Size-based thresholds
    min_content_size_bytes: int = 100  # Minimum content size to capture
    max_buffer_size_bytes: int = 50000  # Max buffer size before forced flush
    max_document_size_bytes: int = 10000  # Max size per document

    # Time-based thresholds
    max_buffer_age_seconds: int = 3600  # Flush after 1 hour
    max_idle_time_seconds: int = 1800  # Flush after 30 min idle

    # Content filters
    min_word_count: int = 3  # Minimum words per message
    ignore_empty: bool = True  # Ignore empty/whitespace messages
    ignore_duplicates: bool = True  # Ignore duplicate messages in same session

    # Priority-based flushing
    enable_priority_flush: bool = False  # Flush high-priority messages first
    priority_keywords: List[str] = field(default_factory=list)  # Keywords that trigger priority

    # Callbacks
    on_flush: Optional[Callable] = None  # Called when buffer is flushed
    on_capture: Optional[Callable] = None  # Called when message is captured

    # Storage
    state_file: str = "capture_state.json"  # File to store capture state


@dataclass
class CaptureState:
    """State of auto-capture system."""
    total_messages_captured: int = 0
    total_buffers_flushed: int = 0
    total_bytes_captured: int = 0
    last_flush_time: str = ""
    last_message_time: str = ""
    captured_hashes: List[str] = field(default_factory=list)  # For duplicate detection

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage."""
        return {
            'total_messages_captured': self.total_messages_captured,
            'total_buffers_flushed': self.total_buffers_flushed,
            'total_bytes_captured': self.total_bytes_captured,
            'last_flush_time': self.last_flush_time,
            'last_message_time': self.last_message_time,
            'captured_hashes': self.captured_hashes[-1000:],  # Keep last 1000
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaptureState':
        """Create from dict."""
        return cls(
            total_messages_captured=data.get('total_messages_captured', 0),
            total_buffers_flushed=data.get('total_buffers_flushed', 0),
            total_bytes_captured=data.get('total_bytes_captured', 0),
            last_flush_time=data.get('last_flush_time', ''),
            last_message_time=data.get('last_message_time', ''),
            captured_hashes=data.get('captured_hashes', []),
        )


class ConfigurableCapture:
    """
    Configurable auto-capture system with thresholds.

    Features:
    - Message count thresholds (min, max, urgent)
    - Size thresholds (buffer size, document size)
    - Time thresholds (buffer age, idle time)
    - Content filters (word count, duplicates, empty)
    - Priority-based flushing (urgent keywords)
    """

    def __init__(self, config: CaptureConfig = None, state_file: str = None):
        """
        Initialize configurable capture.

        Args:
            config: CaptureConfig with thresholds
            state_file: Path to store capture state
        """
        self.config = config or CaptureConfig()
        self.state_file = Path(state_file) if state_file else Path(self.config.state_file)
        self.state = self._load_state()
        self.buffer: List[Dict[str, Any]] = []
        self.rag_db = None  # Will be set via set_database()

        logger.info("Configurable capture initialized")

    def _load_state(self) -> CaptureState:
        """Load capture state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return CaptureState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load capture state: {e}")
        return CaptureState()

    def _save_state(self):
        """Save capture state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save capture state: {e}")

    def set_database(self, rag_db):
        """Set the RAG database instance."""
        self.rag_db = rag_db

    def _hash_content(self, content: str) -> str:
        """Generate hash for content (for duplicate detection)."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _should_capture(self, content: str) -> tuple[bool, str]:
        """
        Check if message should be captured.

        Returns:
            (should_capture, reason)
        """
        # Check empty
        if self.config.ignore_empty and not content.strip():
            return False, "Empty message"

        # Check size
        content_size = len(content.encode('utf-8'))
        if content_size < self.config.min_content_size_bytes:
            return False, f"Content too small ({content_size} < {self.config.min_content_size_bytes})"

        if content_size > self.config.max_document_size_bytes:
            return False, f"Content too large ({content_size} > {self.config.max_document_size_bytes})"

        # Check word count
        word_count = len(content.split())
        if word_count < self.config.min_word_count:
            return False, f"Too few words ({word_count} < {self.config.min_word_count})"

        # Check duplicates
        if self.config.ignore_duplicates:
            content_hash = self._hash_content(content)
            if content_hash in self.state.captured_hashes:
                return False, "Duplicate message"

        return True, "OK"

    def _should_flush(self, reason: str = "") -> tuple[bool, str]:
        """
        Check if buffer should be flushed.

        Returns:
            (should_flush, reason)
        """
        # Check message count
        if len(self.buffer) >= self.config.urgent_flush_messages:
            return True, f"Urgent: {len(self.buffer)} messages >= {self.config.urgent_flush_messages}"

        if len(self.buffer) >= self.config.max_messages_before_flush:
            return True, f"Max messages: {len(self.buffer)} >= {self.config.max_messages_before_flush}"

        # Check buffer size
        buffer_size = sum(len(msg.get('content', '').encode('utf-8')) for msg in self.buffer)
        if buffer_size >= self.config.max_buffer_size_bytes:
            return True, f"Buffer too large: {buffer_size} >= {self.config.max_buffer_size_bytes}"

        # Check buffer age
        if self.buffer:
            oldest_time = datetime.fromisoformat(self.buffer[0]['timestamp'])
            age_seconds = (datetime.now() - oldest_time).total_seconds()
            if age_seconds >= self.config.max_buffer_age_seconds:
                return True, f"Buffer too old: {age_seconds:.0f}s >= {self.config.max_buffer_age_seconds}s"

        # Check idle time
        if self.state.last_message_time:
            last_msg_time = datetime.fromisoformat(self.state.last_message_time)
            idle_seconds = (datetime.now() - last_msg_time).total_seconds()
            if idle_seconds >= self.config.max_idle_time_seconds:
                return True, f"Idle too long: {idle_seconds:.0f}s >= {self.config.max_idle_time_seconds}s"

        return False, reason or "Thresholds OK"

    def capture(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Capture a message to the buffer.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Additional metadata

        Returns:
            Dict with capture result
        """
        # Check if should capture
        should_capture, reason = self._should_capture(content)

        if not should_capture:
            return {
                "captured": False,
                "reason": reason,
                "buffer_size": len(self.buffer),
            }

        # Add to buffer
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
        }
        self.buffer.append(message)

        # Update state
        self.state.total_messages_captured += 1
        self.state.total_bytes_captured += len(content.encode('utf-8'))
        self.state.last_message_time = message['timestamp']

        # Track hash for duplicate detection
        if self.config.ignore_duplicates:
            content_hash = self._hash_content(content)
            self.state.captured_hashes.append(content_hash)
            # Keep only last 1000 hashes
            if len(self.state.captured_hashes) > 1000:
                self.state.captured_hashes = self.state.captured_hashes[-1000:]

        # Check for priority
        is_priority = False
        if self.config.enable_priority_flush:
            for keyword in self.config.priority_keywords:
                if keyword.lower() in content.lower():
                    is_priority = True
                    break

        # Callback
        if self.config.on_capture:
            self.config.on_capture(message)

        # Check if should flush
        should_flush, flush_reason = self._should_flush()

        result = {
            "captured": True,
            "reason": reason,
            "buffer_size": len(self.buffer),
            "is_priority": is_priority,
            "should_flush": should_flush,
            "flush_reason": flush_reason if should_flush else "",
        }

        # Auto-flush if needed
        if should_flush or (is_priority and len(self.buffer) >= self.config.min_messages_to_capture):
            self.flush(reason=flush_reason or "Priority flush")

        # Save state
        self._save_state()

        return result

    def flush(self, reason: str = "") -> Dict[str, Any]:
        """
        Flush buffer to RAG database.

        Args:
            reason: Reason for flush

        Returns:
            Dict with flush result
        """
        if not self.buffer:
            return {
                "flushed": False,
                "reason": "Empty buffer",
            }

        # Check minimum threshold
        if len(self.buffer) < self.config.min_messages_to_capture:
            return {
                "flushed": False,
                "reason": f"Buffer too small ({len(self.buffer)} < {self.config.min_messages_to_capture})",
            }

        # Build content from buffer
        content_parts = []
        for msg in self.buffer:
            role = msg['role'].upper()
            text = msg['content']
            content_parts.append(f"{role}: {text}")

        full_content = "\n\n".join(content_parts)

        # Add to RAG
        if self.rag_db:
            try:
                session_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.rag_db.add_document(
                    namespace="Sessions",
                    content=full_content,
                    source_id=session_id,
                    metadata={
                        "message_count": len(self.buffer),
                        "buffer_size_bytes": len(full_content.encode('utf-8')),
                        "flush_reason": reason,
                    }
                )
                logger.info(f"Flushed {len(self.buffer)} messages to RAG")
            except Exception as e:
                logger.error(f"Failed to flush to RAG: {e}")
                return {
                    "flushed": False,
                    "reason": f"Flush failed: {str(e)}",
                }

        # Clear buffer
        buffer_size = len(self.buffer)
        self.buffer.clear()

        # Update state
        self.state.total_buffers_flushed += 1
        self.state.last_flush_time = datetime.now().isoformat()
        self._save_state()

        # Callback
        if self.config.on_flush:
            self.config.on_flush(buffer_size, reason)

        return {
            "flushed": True,
            "reason": reason,
            "messages_flushed": buffer_size,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        buffer_size = sum(len(msg.get('content', '').encode('utf-8')) for msg in self.buffer)
        should_flush, flush_reason = self._should_flush()

        return {
            "buffer_size": len(self.buffer),
            "buffer_size_bytes": buffer_size,
            "total_messages_captured": self.state.total_messages_captured,
            "total_buffers_flushed": self.state.total_buffers_flushed,
            "total_bytes_captured": self.state.total_bytes_captured,
            "last_flush_time": self.state.last_flush_time or "Never",
            "last_message_time": self.state.last_message_time or "Never",
            "should_flush": should_flush,
            "flush_reason": flush_reason if should_flush else "",
            "config": {
                "min_messages": self.config.min_messages_to_capture,
                "max_messages": self.config.max_messages_before_flush,
                "urgent_messages": self.config.urgent_flush_messages,
                "max_buffer_size": self.config.max_buffer_size_bytes,
                "max_buffer_age": self.config.max_buffer_age_seconds,
            },
        }


def demo_configurable_capture():
    """Demonstrate configurable capture."""

    print("=" * 70)
    print("Configurable Capture Demo")
    print("=" * 70)

    # Create config with thresholds
    config = CaptureConfig(
        min_messages_to_capture=3,  # Flush after 3 messages
        max_messages_before_flush=5,  # Force flush after 5
        min_content_size_bytes=10,
        min_word_count=2,
        ignore_empty=True,
        ignore_duplicates=True,
        max_buffer_age_seconds=60,  # 1 minute
        enable_priority_flush=True,
        priority_keywords=['urgent', 'important', 'critical'],
    )

    print("\n✓ Configured thresholds:")
    print(f"  Min messages to capture: {config.min_messages_to_capture}")
    print(f"  Max messages before flush: {config.max_messages_before_flush}")
    print(f"  Urgent flush messages: {config.urgent_flush_messages}")
    print(f"  Min content size: {config.min_content_size_bytes} bytes")
    print(f"  Min word count: {config.min_word_count}")
    print(f"  Ignore empty: {config.ignore_empty}")
    print(f"  Ignore duplicates: {config.ignore_duplicates}")
    print(f"  Max buffer age: {config.max_buffer_age_seconds}s")
    print(f"  Priority keywords: {config.priority_keywords}")

    # Create capture system
    capture = ConfigurableCapture(config=config)

    print("\n" + "=" * 70)
    print("Capturing Messages")
    print("=" * 70)

    # Test messages
    messages = [
        ("user", "Hello, how are you?"),
        ("assistant", "I'm doing well, thanks for asking!"),
        ("user", "I need help with something important"),
        ("assistant", "Sure, what do you need help with?"),
        ("user", "This is a test message"),
        ("user", "Duplicate message"),  # Will be captured first
        ("user", "Duplicate message"),  # Will be ignored as duplicate
        ("user", "   "),  # Will be ignored as empty
        ("user", "x"),  # Will be ignored as too short
    ]

    for role, content in messages:
        result = capture.capture(role, content)

        print(f"\n[{role.upper()}]: {content}")
        print(f"  Captured: {result['captured']}")
        if not result['captured']:
            print(f"  Reason: {result['reason']}")
        else:
            print(f"  Buffer size: {result['buffer_size']}")
            print(f"  Priority: {result['is_priority']}")
            if result['should_flush']:
                print(f"  Flushed: YES ({result['flush_reason']})")

    # Check status
    print("\n" + "=" * 70)
    print("Status")
    print("=" * 70)

    status = capture.get_status()
    print(f"\nBuffer size: {status['buffer_size']} messages")
    print(f"Buffer size: {status['buffer_size_bytes']} bytes")
    print(f"Total captured: {status['total_messages_captured']} messages")
    print(f"Total flushed: {status['total_buffers_flushed']} buffers")
    print(f"Total bytes captured: {status['total_bytes_captured']}")
    print(f"Last flush: {status['last_flush_time']}")
    print(f"Should flush: {status['should_flush']}")
    if status['should_flush']:
        print(f"Reason: {status['flush_reason']}")

    # Manual flush
    print("\n" + "=" * 70)
    print("Manual Flush")
    print("=" * 70)

    if capture.buffer:
        result = capture.flush(reason="Manual flush")
        print(f"\nFlushed: {result['flushed']}")
        if result['flushed']:
            print(f"Messages: {result['messages_flushed']}")
        else:
            print(f"Reason: {result['reason']}")

    # Final status
    status = capture.get_status()
    print(f"\nFinal buffer size: {status['buffer_size']} messages")
    print(f"Total flushed: {status['total_buffers_flushed']} buffers")

    print("\n✅ Configurable capture demo complete!")


if __name__ == "__main__":
    demo_configurable_capture()
