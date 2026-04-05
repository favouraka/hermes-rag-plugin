"""
Comprehensive tests for Auto Peer Capture
Tests automatic peer tracking, session management, and integration
"""

import unittest
import tempfile
import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path
plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, plugin_dir)

# Import using absolute imports when running tests directly
from core.auto_capture import AutoPeerCapture
from models.peer import Peer, PeerManager
from models.session import Session, SessionManager


class TestAutoPeerCapture(unittest.TestCase):
    """Test AutoPeerCapture class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.auto = AutoPeerCapture(db_path=self.db_path)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            self.auto.end_session()
        except:
            pass

        try:
            if self.auto.conn:
                self.auto.conn.close()
        except:
            pass

        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_initialization(self):
        """Test auto capture initialization"""
        self.assertIsNotNone(self.auto.peer_manager)
        self.assertIsNotNone(self.auto.session_manager)
        self.assertIsNotNone(self.auto.conn)

    def test_capture_message_creates_peer(self):
        """Test that capturing message auto-creates peer"""
        self.auto.capture_message("new-peer", "user", "Hello!")

        peer = self.auto.peer_manager.get_peer("new-peer")
        self.assertIsNotNone(peer)
        self.assertEqual(peer.peer_id, "new-peer")

    def test_capture_message_returns_info(self):
        """Test that capture_message returns complete info"""
        result = self.auto.capture_message("test-peer", "user", "Test message")

        self.assertIn('peer_id', result)
        self.assertIn('session_id', result)
        self.assertIn('peer', result)
        self.assertIn('session', result)
        self.assertEqual(result['content'], "Test message")

    def test_multiple_captures_same_peer(self):
        """Test capturing multiple messages from same peer"""
        self.auto.capture_message("test-peer", "user", "Message 1")
        self.auto.capture_message("test-peer", "user", "Message 2")
        self.auto.capture_message("test-peer", "user", "Message 3")

        peer = self.auto.peer_manager.get_peer("test-peer")
        self.assertEqual(len(peer._messages_cache), 3)

    def test_buffer_flushing(self):
        """Test automatic buffer flushing"""
        # Set low threshold for testing
        self.auto._buffer_flush_threshold = 3

        self.auto.capture_message("test-peer", "user", "Msg 1")
        self.assertEqual(len(self.auto._message_buffer), 1)

        self.auto.capture_message("test-peer", "user", "Msg 2")
        self.assertEqual(len(self.auto._message_buffer), 2)

        self.auto.capture_message("test-peer", "user", "Msg 3")
        # Buffer should be flushed
        self.assertEqual(len(self.auto._message_buffer), 0)

    def test_start_session(self):
        """Test starting a session with multiple peers"""
        session = self.auto.start_session(
            session_id="test-session",
            peer_ids=["alice", "bob", "assistant"]
        )

        self.assertEqual(session.session_id, "test-session")
        self.assertEqual(len(session._peers), 3)
        self.assertIn("alice", session._peers)
        self.assertIn("bob", session._peers)
        self.assertIn("assistant", session._peers)

    def test_start_session_creates_peers(self):
        """Test that start_session auto-creates peers"""
        self.auto.start_session(
            session_id="test-session",
            peer_ids=["new-peer-1", "new-peer-2"]
        )

        peer1 = self.auto.peer_manager.get_peer("new-peer-1")
        peer2 = self.auto.peer_manager.get_peer("new-peer-2")

        self.assertIsNotNone(peer1)
        self.assertIsNotNone(peer2)

    def test_end_session(self):
        """Test ending a session"""
        self.auto.start_session(
            session_id="test-session",
            peer_ids=["alice"]
        )

        self.auto.capture_message("alice", "user", "Hello!")
        self.auto.end_session("test-session")

        # Buffer should be flushed
        self.assertEqual(len(self.auto._message_buffer), 0)

    def test_get_peer_context(self):
        """Test getting peer context"""
        self.auto.capture_message("test-peer", "user", "Message 1")
        self.auto.capture_message("test-peer", "assistant", "Response 1")

        context = self.auto.get_peer_context("test-peer", tokens=500)

        self.assertIsInstance(context, str)
        self.assertIn("user", context)
        self.assertIn("assistant", context)

    def test_get_session_context(self):
        """Test getting session context"""
        session = self.auto.start_session(
            session_id="test-session",
            peer_ids=["alice", "assistant"]
        )

        self.auto.capture_message("alice", "user", "Hello!")
        self.auto.capture_message("assistant", "assistant", "Hi!")

        context = self.auto.get_session_context("test-session")

        self.assertEqual(context.session_id, "test-session")
        self.assertEqual(len(context.messages), 2)

    def test_search_peer(self):
        """Test searching within peer messages"""
        self.auto.capture_message("test-peer", "user", "The weather is nice")
        self.auto.capture_message("test-peer", "user", "I like programming")

        results = self.auto.search_peer("test-peer", "weather")

        self.assertEqual(len(results), 1)
        self.assertIn("weather", results[0]['content'])

    def test_list_peers(self):
        """Test listing all peers"""
        self.auto.capture_message("peer1", "user", "Msg 1")
        self.auto.capture_message("peer2", "user", "Msg 2")
        self.auto.capture_message("peer3", "user", "Msg 3")

        peers = self.auto.list_peers()

        self.assertEqual(len(peers), 3)

    def test_list_peers_with_limit(self):
        """Test listing peers with limit"""
        for i in range(10):
            self.auto.capture_message(f"peer-{i}", "user", f"Msg {i}")

        peers = self.auto.list_peers(limit=5)

        self.assertEqual(len(peers), 5)

    def test_list_sessions(self):
        """Test listing sessions"""
        self.auto.start_session("session-1", ["alice"])
        self.auto.start_session("session-2", ["bob"])
        self.auto.start_session("session-3", ["charlie"])

        sessions = self.auto.list_sessions()

        self.assertEqual(len(sessions), 3)

    def test_list_sessions_filtered_by_peer(self):
        """Test listing sessions filtered by peer"""
        self.auto.start_session("session-1", ["alice", "bob"])
        self.auto.start_session("session-2", ["alice"])

        alice_sessions = self.auto.list_sessions(peer_id="alice")

        self.assertEqual(len(alice_sessions), 2)

    def test_get_active_session(self):
        """Test getting active session"""
        session = self.auto.start_session("active-session", ["alice"])

        active = self.auto.get_active_session()

        self.assertIsNotNone(active)
        self.assertEqual(active['session_id'], "active-session")

    def test_set_active_session(self):
        """Test setting active session"""
        self.auto.start_session("session-1", ["alice"])
        self.auto.start_session("session-2", ["bob"])

        self.auto.set_active_session("session-1")
        active = self.auto.get_active_session()

        self.assertEqual(active['session_id'], "session-1")

    def test_get_peer_stats(self):
        """Test getting peer statistics"""
        self.auto.start_session("test-session", ["alice"])

        # Add multiple messages
        for i in range(5):
            self.auto.capture_message("alice", "user", f"Message {i}")

        stats = self.auto.get_peer_stats("alice")

        self.assertEqual(stats['peer_id'], "alice")
        self.assertEqual(stats['total_messages'], 5)
        self.assertEqual(stats['total_sessions'], 1)
        self.assertIn('metadata', stats)
        self.assertIn('recent_sessions', stats)

    def test_flush_buffer(self):
        """Test flushing buffer"""
        self.auto.capture_message("test-peer", "user", "Msg 1")
        self.auto.capture_message("test-peer", "user", "Msg 2")

        flushed = self.auto.flush_buffer()

        self.assertEqual(len(flushed), 2)
        self.assertEqual(len(self.auto._message_buffer), 0)

    def test_empty_flush(self):
        """Test flushing empty buffer"""
        flushed = self.auto.flush_buffer()

        self.assertEqual(len(flushed), 0)

    def test_capture_with_session_id(self):
        """Test capturing with explicit session ID"""
        self.auto.start_session("explicit-session", ["alice"])

        self.auto.capture_message("alice", "user", "Message", session_id="explicit-session")

        session = self.auto.session_manager.get_session("explicit-session")
        self.assertEqual(len(session._messages), 1)

    def test_capture_with_metadata(self):
        """Test capturing message with metadata"""
        metadata = {"source": "test", "importance": "high"}

        result = self.auto.capture_message(
            "test-peer",
            "user",
            "Test message",
            metadata=metadata
        )

        self.assertEqual(result['metadata'], metadata)


class TestIntegration(unittest.TestCase):
    """Integration tests for AutoPeerCapture with RAG system"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.auto = AutoPeerCapture(db_path=self.db_path)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            self.auto.end_session()
        except:
            pass

        try:
            if self.auto.conn:
                self.auto.conn.close()
        except:
            pass

        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_full_conversation_flow(self):
        """Test complete conversation flow"""
        # Start session
        session = self.auto.start_session(
            session_id="conversation-1",
            peer_ids=["user", "assistant"]
        )

        # Simulate conversation
        messages = [
            ("user", "user", "I need help with Python"),
            ("assistant", "assistant", "What do you need help with?"),
            ("user", "user", "How do I read a file?"),
            ("assistant", "assistant", "Use open() function"),
        ]

        for peer_id, role, content in messages:
            self.auto.capture_message(peer_id, role, content)

        # Get user context
        user_context = self.auto.get_peer_context("user")
        self.assertIn("Python", user_context)

        # Get session context
        session_context = self.auto.get_session_context("conversation-1")
        self.assertEqual(len(session_context.messages), 4)

        # Get user stats
        user_stats = self.auto.get_peer_stats("user")
        self.assertEqual(user_stats['total_messages'], 2)

        # Search for specific topic
        results = self.auto.search_peer("user", "file")
        self.assertEqual(len(results), 1)

    def test_multi_party_conversation(self):
        """Test multi-party conversation with multiple peers"""
        # Start session with 4 peers
        session = self.auto.start_session(
            session_id="group-chat",
            peer_ids=["alice", "bob", "charlie", "assistant"]
        )

        # Each peer sends messages
        for i in range(3):
            self.auto.capture_message("alice", "user", f"Alice message {i}")
            self.auto.capture_message("bob", "user", f"Bob message {i}")
            self.auto.capture_message("charlie", "user", f"Charlie message {i}")
            self.auto.capture_message("assistant", "assistant", f"Assistant response {i}")

        # Verify each peer has 3 messages
        alice = self.auto.peer_manager.get_peer("alice")
        bob = self.auto.peer_manager.get_peer("bob")
        charlie = self.auto.peer_manager.get_peer("charlie")
        assistant = self.auto.peer_manager.get_peer("assistant")

        self.assertEqual(len(alice._messages_cache), 3)
        self.assertEqual(len(bob._messages_cache), 3)
        self.assertEqual(len(charlie._messages_cache), 3)
        self.assertEqual(len(assistant._messages_cache), 3)

        # Verify session has 12 messages
        self.assertEqual(len(session._messages), 12)


class TestPerformance(unittest.TestCase):
    """Performance tests for AutoPeerCapture"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.auto = AutoPeerCapture(db_path=self.db_path)

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            self.auto.end_session()
        except:
            pass

        try:
            if self.auto.conn:
                self.auto.conn.close()
        except:
            pass

        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_bulk_message_capture(self):
        """Test capturing many messages efficiently"""
        import time

        # Create session
        self.auto.start_session("bulk-test", ["user", "assistant"])

        start = time.time()
        for i in range(100):  # Reduced from 1000 for faster testing
            peer_id = "user" if i % 2 == 0 else "assistant"
            role = "user" if i % 2 == 0 else "assistant"
            self.auto.capture_message(peer_id, role, f"Message {i}")
        elapsed = time.time() - start

        # Should complete in reasonable time (< 10 seconds for 100 messages)
        self.assertLess(elapsed, 10.0)

    def test_many_peers_performance(self):
        """Test managing many peers efficiently"""
        import time

        start = time.time()
        for i in range(50):  # Reduced from 100 for faster testing
            self.auto.capture_message(f"peer-{i}", "user", "Initial message")
        elapsed = time.time() - start

        # Should complete in reasonable time (< 10 seconds for 50 peers)
        self.assertLess(elapsed, 10.0)

        peers = self.auto.list_peers()
        self.assertEqual(len(peers), 50)

    def test_context_retrieval_speed(self):
        """Test context retrieval performance"""
        import time

        self.auto.start_session("perf-test", ["user"])

        # Add messages
        for i in range(200):  # Reduced from 500 for faster testing
            self.auto.capture_message("user", "user", f"Message {i}")

        # Measure context retrieval time
        start = time.time()
        context = self.auto.get_peer_context("user", tokens=5000)
        elapsed = time.time() - start

        # Should be fast (< 1s for 200 messages)
        self.assertLess(elapsed, 1.0)
        self.assertIsNotNone(context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
