"""
Comprehensive tests for Peer Model
Tests all functionality including CRUD, search, context retrieval
"""

import unittest
import tempfile
import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_peer_model import Peer, PeerManager


class TestPeer(unittest.TestCase):
    """Test Peer class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self.temp_db.close()

        # Create test peer
        self.peer = Peer(
            peer_id="test-peer",
            metadata={"name": "Test User", "type": "human"},
            db_conn=self.conn
        )

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_peer_creation(self):
        """Test peer creation with metadata"""
        self.assertEqual(self.peer.peer_id, "test-peer")
        self.assertEqual(self.peer.metadata["name"], "Test User")
        self.assertEqual(self.peer.metadata["type"], "human")

    def test_add_message(self):
        """Test adding messages to peer"""
        message = self.peer.add_message(
            role="user",
            content="Hello, world!",
            session_id="session-1"
        )

        self.assertIn("peer_id", message)
        self.assertEqual(message["peer_id"], "test-peer")
        self.assertEqual(message["content"], "Hello, world!")
        self.assertEqual(message["session_id"], "session-1")
        self.assertEqual(len(self.peer._messages_cache), 1)

    def test_add_multiple_messages(self):
        """Test adding multiple messages"""
        self.peer.add_message("user", "Message 1", "session-1")
        self.peer.add_message("assistant", "Response 1", "session-1")
        self.peer.add_message("user", "Message 2", "session-1")

        self.assertEqual(len(self.peer._messages_cache), 3)

    def test_search_messages(self):
        """Test searching within peer messages"""
        self.peer.add_message("user", "The weather is nice today", "session-1")
        self.peer.add_message("assistant", "Yes, it is sunny", "session-1")
        self.peer.add_message("user", "What about tomorrow's weather?", "session-1")

        results = self.peer.search("weather", limit=10)
        self.assertEqual(len(results), 2)

    def test_search_with_session_filter(self):
        """Test searching with session filter"""
        self.peer.add_message("user", "Topic A discussion", "session-1")
        self.peer.add_message("user", "Topic B discussion", "session-2")

        results = self.peer.search("Topic", session_id="session-1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["session_id"], "session-1")

    def test_get_context(self):
        """Test getting conversation context"""
        self.peer.add_message("system", "You are helpful", "session-1")
        self.peer.add_message("user", "Hello", "session-1")
        self.peer.add_message("assistant", "Hi there!", "session-1")

        context = self.peer.get_context(tokens=1000)
        self.assertIsInstance(context, str)
        self.assertIn("system", context)
        self.assertIn("user", context)

    def test_set_metadata(self):
        """Test updating peer metadata"""
        self.peer.set_metadata({"location": "Nigeria"})

        self.assertEqual(self.peer.metadata["location"], "Nigeria")
        self.assertEqual(self.peer.metadata["name"], "Test User")  # Original preserved

    def test_merge_metadata(self):
        """Test deep merge of metadata"""
        self.peer.set_metadata({
            "preferences": {"theme": "dark"},
            "location": "Lagos"
        })

        self.peer.set_metadata({
            "preferences": {"notifications": True}
        })

        self.assertEqual(self.peer.metadata["preferences"]["theme"], "dark")
        self.assertEqual(self.peer.metadata["preferences"]["notifications"], True)

    def test_get_sessions(self):
        """Test retrieving peer sessions"""
        self.peer.add_message("user", "Msg 1", "session-1")
        self.peer.add_message("user", "Msg 2", "session-1")
        self.peer.add_message("user", "Msg 3", "session-2")

        sessions = self.peer.get_sessions()
        self.assertEqual(len(sessions), 2)

    def test_get_messages(self):
        """Test retrieving messages"""
        self.peer.add_message("user", "Msg 1", "session-1")
        self.peer.add_message("assistant", "Resp 1", "session-1")
        self.peer.add_message("user", "Msg 2", "session-2")

        messages = self.peer.get_messages(session_id="session-1")
        self.assertEqual(len(messages), 2)

    def test_get_messages_with_limit(self):
        """Test retrieving messages with limit"""
        for i in range(10):
            self.peer.add_message("user", f"Message {i}", "session-1")

        messages = self.peer.get_messages(limit=3)
        self.assertEqual(len(messages), 3)

    def test_to_dict(self):
        """Test peer dictionary conversion"""
        self.peer.add_message("user", "Test message", "session-1")
        peer_dict = self.peer.to_dict()

        self.assertEqual(peer_dict["peer_id"], "test-peer")
        self.assertIn("message_count", peer_dict)
        self.assertIn("sessions", peer_dict)


class TestPeerManager(unittest.TestCase):
    """Test PeerManager class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self.temp_db.close()

        self.manager = PeerManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_peer(self):
        """Test creating peers through manager"""
        peer = self.manager.create_peer(
            "alice",
            {"name": "Alice", "type": "human"}
        )

        self.assertEqual(peer.peer_id, "alice")
        self.assertEqual(len(self.manager._peers), 1)

    def test_duplicate_peer_raises_error(self):
        """Test that duplicate peer IDs raise error"""
        self.manager.create_peer("bob", {"name": "Bob"})

        with self.assertRaises(ValueError):
            self.manager.create_peer("bob", {"name": "Robert"})

    def test_get_peer(self):
        """Test retrieving peers"""
        self.manager.create_peer("charlie", {"name": "Charlie"})

        peer = self.manager.get_peer("charlie")
        self.assertIsNotNone(peer)
        self.assertEqual(peer.peer_id, "charlie")

    def test_get_nonexistent_peer(self):
        """Test retrieving non-existent peer"""
        peer = self.manager.get_peer("nonexistent")
        self.assertIsNone(peer)

    def test_list_peers(self):
        """Test listing all peers"""
        self.manager.create_peer("peer1", {"name": "Peer 1"})
        self.manager.create_peer("peer2", {"name": "Peer 2"})
        self.manager.create_peer("peer3", {"name": "Peer 3"})

        peers = self.manager.list_peers()
        self.assertEqual(len(peers), 3)

    def test_delete_peer(self):
        """Test deleting peers"""
        self.manager.create_peer("temp-peer", {"name": "Temp"})

        result = self.manager.delete_peer("temp-peer")
        self.assertTrue(result)

        peer = self.manager.get_peer("temp-peer")
        self.assertIsNone(peer)

    def test_delete_nonexistent_peer(self):
        """Test deleting non-existent peer"""
        result = self.manager.delete_peer("nonexistent")
        self.assertFalse(result)

    def test_search_peers_by_metadata(self):
        """Test searching peers by metadata"""
        self.manager.create_peer("alice", {"name": "Alice", "skill": "python"})
        self.manager.create_peer("bob", {"name": "Bob", "skill": "javascript"})
        self.manager.create_peer("charlie", {"name": "Charlie", "skill": "python"})

        results = self.manager.search_peers("python")
        self.assertEqual(len(results), 2)

    def test_search_peers_by_message_content(self):
        """Test searching peers by message content"""
        alice = self.manager.create_peer("alice", {"name": "Alice"})
        bob = self.manager.create_peer("bob", {"name": "Bob"})

        alice.add_message("user", "I love machine learning")
        bob.add_message("user", "I love web development")

        results = self.manager.search_peers("machine learning")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["peer_id"], "alice")

    def test_persistence(self):
        """Test that peers persist across manager instances"""
        # Create peer and add messages
        peer = self.manager.create_peer("persistent", {"name": "Persistent"})
        peer.add_message("user", "Test message", "session-1")

        # Create new manager with same DB
        self.conn.commit()
        new_manager = PeerManager(db_conn=self.conn)

        # Load peer
        loaded_peer = new_manager.get_peer("persistent")
        self.assertIsNotNone(loaded_peer)
        self.assertEqual(len(loaded_peer._messages_cache), 1)


class TestPerformance(unittest.TestCase):
    """Performance tests for Peer model"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = PeerManager()

    def test_many_peers_creation(self):
        """Test creating many peers efficiently"""
        import time

        start = time.time()
        for i in range(1000):
            self.manager.create_peer(
                f"peer-{i}",
                {"name": f"Peer {i}", "index": i}
            )
        elapsed = time.time() - start

        # Should be fast (< 1 second for 1000 peers)
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(self.manager.list_peers()), 1000)

    def test_many_messages_per_peer(self):
        """Test adding many messages to a peer"""
        import time

        peer = self.manager.create_peer("chatty-peer", {"name": "Chatty"})

        start = time.time()
        for i in range(1000):
            peer.add_message("user", f"Message {i}", "session-1")
        elapsed = time.time() - start

        # Should be fast (< 0.5 seconds for 1000 messages)
        self.assertLess(elapsed, 0.5)
        self.assertEqual(len(peer._messages_cache), 1000)

    def test_search_performance(self):
        """Test search performance with many messages"""
        import time

        peer = self.manager.create_peer("search-peer", {"name": "Search Test"})

        # Add messages
        for i in range(1000):
            peer.add_message("user", f"This is message {i} about testing", "session-1")

        # Measure search time
        start = time.time()
        results = peer.search("testing", limit=10)
        elapsed = time.time() - start

        # Should be very fast (< 50ms)
        self.assertLess(elapsed, 0.05)
        self.assertEqual(len(results), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
