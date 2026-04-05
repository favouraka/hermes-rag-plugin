"""
Comprehensive tests for Session Model
Tests all functionality including multi-peer support, context retrieval, LLM format conversion
"""

import unittest
import tempfile
import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.session import Session, SessionManager, SessionContext
from models.peer import Peer, PeerManager


class TestSession(unittest.TestCase):
    """Test Session class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self.temp_db.close()

        # Create test peers
        self.peer_manager = PeerManager(db_conn=self.conn)
        self.alice = self.peer_manager.create_peer("alice", {"name": "Alice", "type": "human"})
        self.bob = self.peer_manager.create_peer("bob", {"name": "Bob", "type": "human"})
        self.assistant = self.peer_manager.create_peer("assistant", {"name": "AI", "type": "agent"})

        # Create test session
        self.session = Session("test-session", db_conn=self.conn)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_session_creation(self):
        """Test session creation"""
        self.assertEqual(self.session.session_id, "test-session")
        self.assertEqual(len(self.session._peers), 0)

    def test_add_peers(self):
        """Test adding peers to session"""
        self.session.add_peers([self.alice, self.bob, self.assistant])

        self.assertEqual(len(self.session._peers), 3)
        self.assertIn("alice", self.session._peers)
        self.assertIn("bob", self.session._peers)
        self.assertIn("assistant", self.session._peers)

    def test_add_messages(self):
        """Test adding messages to session"""
        self.session.add_peers([self.alice, self.bob])

        messages = [
            {'peer_id': 'alice', 'role': 'user', 'content': 'Hello Bob!'},
            {'peer_id': 'bob', 'role': 'user', 'content': 'Hi Alice!'}
        ]

        self.session.add_messages(messages)

        self.assertEqual(len(self.session._messages), 2)
        # Messages should also be added to peer history
        self.assertEqual(len(self.alice._messages_cache), 1)
        self.assertEqual(len(self.bob._messages_cache), 1)

    def test_get_peer_ids(self):
        """Test getting peer IDs"""
        self.session.add_peers([self.alice, self.bob, self.assistant])

        peer_ids = self.session.get_peer_ids()
        self.assertEqual(len(peer_ids), 3)
        self.assertIn("alice", peer_ids)
        self.assertIn("bob", peer_ids)
        self.assertIn("assistant", peer_ids)

    def test_get_peers(self):
        """Test getting peers"""
        self.session.add_peers([self.alice, self.bob])

        peers = self.session.get_peers()
        self.assertEqual(len(peers), 2)

    def test_context_retrieval(self):
        """Test context retrieval"""
        self.session.add_peers([self.alice, self.assistant])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'Hello!'},
            {'peer_id': 'assistant', 'role': 'assistant', 'content': 'Hi there!'}
        ])

        context = self.session.context(summary=True, tokens=1000)

        self.assertIsInstance(context, SessionContext)
        self.assertEqual(len(context.messages), 2)

    def test_context_with_summary(self):
        """Test context with summary"""
        self.session.set_summary("This is a test session about greetings")

        context = self.session.context(summary=True, tokens=1000)

        self.assertEqual(context.summary, "This is a test session about greetings")

    def test_context_without_system_messages(self):
        """Test context without system messages"""
        self.session.add_peers([self.alice, self.assistant])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'system', 'content': 'System message'},
            {'peer_id': 'alice', 'role': 'user', 'content': 'User message'}
        ])

        context = self.session.context(include_system=False)

        # Should only have user message
        self.assertEqual(len(context.messages), 1)
        self.assertEqual(context.messages[0]['role'], 'user')

    def test_to_openai_format(self):
        """Test OpenAI format conversion"""
        self.session.add_peers([self.alice, self.assistant])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'Hello'},
            {'peer_id': 'assistant', 'role': 'assistant', 'content': 'Hi!'}
        ])

        openai_msgs = self.session.to_openai(self.assistant)

        self.assertIsInstance(openai_msgs, list)
        self.assertEqual(len(openai_msgs), 2)

    def test_to_anthropic_format(self):
        """Test Anthropic format conversion"""
        self.session.add_peers([self.alice, self.assistant])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'Hello'},
            {'peer_id': 'assistant', 'role': 'assistant', 'content': 'Hi!'}
        ])

        messages, system = self.session.to_anthropic(self.assistant)

        self.assertIsInstance(messages, list)
        self.assertIsInstance(system, str)
        self.assertIn("AI assistant", system)

    def test_representation_peer_view(self):
        """Test peer-specific representation"""
        self.session.add_peers([self.alice, self.bob])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'My message'},
            {'peer_id': 'bob', 'role': 'user', 'content': 'Your message'}
        ])

        # Alice's view without observing others
        alice_view = self.session.representation(self.alice, observe_others=False)
        self.assertEqual(alice_view['message_count'], 1)

        # Alice's view observing others
        alice_view_all = self.session.representation(self.alice, observe_others=True)
        self.assertEqual(alice_view_all['message_count'], 2)

    def test_set_summary(self):
        """Test setting session summary"""
        self.session.set_summary("Test summary")

        self.assertEqual(self.session._summary, "Test summary")

    def test_get_messages_filter_by_peer(self):
        """Test getting messages filtered by peer"""
        self.session.add_peers([self.alice, self.bob])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'Msg 1'},
            {'peer_id': 'bob', 'role': 'user', 'content': 'Msg 2'},
            {'peer_id': 'alice', 'role': 'user', 'content': 'Msg 3'}
        ])

        alice_msgs = self.session.get_messages(peer_id='alice')
        self.assertEqual(len(alice_msgs), 2)

    def test_get_messages_filter_by_role(self):
        """Test getting messages filtered by role"""
        self.session.add_peers([self.alice, self.assistant])

        self.session.add_messages([
            {'peer_id': 'alice', 'role': 'user', 'content': 'Msg 1'},
            {'peer_id': 'assistant', 'role': 'assistant', 'content': 'Resp 1'},
            {'peer_id': 'alice', 'role': 'user', 'content': 'Msg 2'}
        ])

        user_msgs = self.session.get_messages(role='user')
        self.assertEqual(len(user_msgs), 2)

    def test_get_messages_with_limit(self):
        """Test getting messages with limit"""
        self.session.add_peers([self.alice])

        for i in range(10):
            self.session.add_messages([
                {'peer_id': 'alice', 'role': 'user', 'content': f'Msg {i}'}
            ])

        messages = self.session.get_messages(limit=3)
        self.assertEqual(len(messages), 3)


class TestSessionContext(unittest.TestCase):
    """Test SessionContext class functionality"""

    def test_context_creation(self):
        """Test SessionContext creation"""
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ]

        context = SessionContext("session-1", messages, "Test summary")

        self.assertEqual(context.session_id, "session-1")
        self.assertEqual(len(context.messages), 2)
        self.assertEqual(context.summary, "Test summary")

    def test_to_openai(self):
        """Test SessionContext to OpenAI format"""
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi!'}
        ]

        context = SessionContext("session-1", messages)
        openai_msgs = context.to_openai(None)

        self.assertEqual(len(openai_msgs), 2)

    def test_to_anthropic(self):
        """Test SessionContext to Anthropic format"""
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi!'}
        ]

        context = SessionContext("session-1", messages)
        messages, system = context.to_anthropic()

        self.assertIsInstance(messages, list)
        self.assertIsInstance(system, str)


class TestSessionManager(unittest.TestCase):
    """Test SessionManager class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.conn = sqlite3.connect(self.db_path)
        self.temp_db.close()

        self.peer_manager = PeerManager(db_conn=self.conn)
        self.session_manager = SessionManager(db_conn=self.conn)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_session(self):
        """Test creating sessions"""
        session = self.session_manager.create_session("session-1")

        self.assertEqual(session.session_id, "session-1")
        self.assertEqual(len(self.session_manager._sessions), 1)

    def test_duplicate_session_raises_error(self):
        """Test that duplicate session IDs raise error"""
        self.session_manager.create_session("session-1")

        with self.assertRaises(ValueError):
            self.session_manager.create_session("session-1")

    def test_get_session(self):
        """Test retrieving sessions"""
        self.session_manager.create_session("session-1")

        session = self.session_manager.get_session("session-1")
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "session-1")

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session"""
        session = self.session_manager.get_session("nonexistent")
        self.assertIsNone(session)

    def test_list_sessions(self):
        """Test listing all sessions"""
        self.session_manager.create_session("session-1")
        self.session_manager.create_session("session-2")
        self.session_manager.create_session("session-3")

        sessions = self.session_manager.list_sessions()
        self.assertEqual(len(sessions), 3)

    def test_list_sessions_filtered_by_peer(self):
        """Test listing sessions filtered by peer"""
        # Create peers
        alice = self.peer_manager.create_peer("alice")
        bob = self.peer_manager.create_peer("bob")

        # Create sessions
        session1 = self.session_manager.create_session("session-1")
        session1.add_peers([alice, bob])

        session2 = self.session_manager.create_session("session-2")
        session2.add_peers([alice])

        # List sessions for Alice
        alice_sessions = self.session_manager.list_sessions(peer_id="alice")
        self.assertEqual(len(alice_sessions), 2)

    def test_delete_session(self):
        """Test deleting sessions"""
        self.session_manager.create_session("temp-session")

        result = self.session_manager.delete_session("temp-session")
        self.assertTrue(result)

        session = self.session_manager.get_session("temp-session")
        self.assertIsNone(session)


class TestPerformance(unittest.TestCase):
    """Performance tests for Session model"""

    def setUp(self):
        """Set up test fixtures"""
        self.peer_manager = PeerManager()
        self.session_manager = SessionManager()

        # Create peers
        self.peers = []
        for i in range(10):
            peer = self.peer_manager.create_peer(
                f"peer-{i}",
                {"name": f"Peer {i}", "type": "human"}
            )
            self.peers.append(peer)

    def test_many_sessions_creation(self):
        """Test creating many sessions efficiently"""
        import time

        start = time.time()
        for i in range(100):
            session = self.session_manager.create_session(f"session-{i}")
            session.add_peers(self.peers[:3])
        elapsed = time.time() - start

        # Should be fast (< 1 second for 100 sessions)
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(self.session_manager.list_sessions()), 100)

    def test_many_messages_per_session(self):
        """Test adding many messages to a session"""
        import time

        session = self.session_manager.create_session("busy-session")
        session.add_peers(self.peers)

        start = time.time()
        for i in range(1000):
            peer_id = f"peer-{i % 10}"
            session.add_messages([
                {'peer_id': peer_id, 'role': 'user', 'content': f'Message {i}'}
            ])
        elapsed = time.time() - start

        # Should be fast (< 1 second for 1000 messages)
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(session._messages), 1000)

    def test_context_retrieval_performance(self):
        """Test context retrieval performance"""
        import time

        session = self.session_manager.create_session("test-context")
        session.add_peers(self.peers)

        # Add messages
        for i in range(1000):
            peer_id = f"peer-{i % 10}"
            session.add_messages([
                {'peer_id': peer_id, 'role': 'user', 'content': f'Message {i}'}
            ])

        # Measure context retrieval time
        start = time.time()
        context = session.context(summary=True, tokens=5000)
        elapsed = time.time() - start

        # Should be very fast (< 50ms)
        self.assertLess(elapsed, 0.05)
        self.assertIsNotNone(context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
