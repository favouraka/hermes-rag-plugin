"""
Comprehensive tests for Namespace Isolation
Tests namespace scoping, validation, and isolation
"""

import unittest
import tempfile
import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_namespace_isolation import NamespaceIsolation, IsolatedSearch


class TestNamespaceIsolation(unittest.TestCase):
    """Test NamespaceIsolation class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.conn = sqlite3.connect(self.db_path)
        self.isolation = NamespaceIsolation(db_conn=self.conn)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_peer_namespace(self):
        """Test peer namespace generation"""
        namespace = self.isolation.get_peer_namespace("alice")

        self.assertEqual(namespace, "peer_alice")

    def test_session_namespace(self):
        """Test session namespace generation"""
        namespace = self.isolation.get_session_namespace("chat-1")

        self.assertEqual(namespace, "session_chat-1")

    def test_peer_session_namespace(self):
        """Test combined peer+session namespace"""
        namespace = self.isolation.get_peer_session_namespace("alice", "chat-1")

        self.assertEqual(namespace, "peer_alice_session_chat-1")

    def test_peer_isolation(self):
        """Test peer isolation check"""
        self.assertTrue(self.isolation.is_peer_isolated("alice"))

    def test_session_isolation(self):
        """Test session isolation check"""
        self.assertTrue(self.isolation.is_session_isolated("chat-1"))

    def test_namespace_validation_peer_match(self):
        """Test namespace validation with peer match"""
        valid = self.isolation.validate_namespace_access(
            peer_id="alice",
            session_id=None,
            target_namespace="peer_alice"
        )

        self.assertTrue(valid)

    def test_namespace_validation_peer_mismatch(self):
        """Test namespace validation with peer mismatch"""
        valid = self.isolation.validate_namespace_access(
            peer_id="alice",
            session_id=None,
            target_namespace="peer_bob"
        )

        self.assertFalse(valid)

    def test_namespace_validation_session_match(self):
        """Test namespace validation with session match"""
        valid = self.isolation.validate_namespace_access(
            peer_id=None,
            session_id="chat-1",
            target_namespace="session_chat-1"
        )

        self.assertTrue(valid)

    def test_namespace_validation_combined_match(self):
        """Test namespace validation with combined match"""
        valid = self.isolation.validate_namespace_access(
            peer_id="alice",
            session_id="chat-1",
            target_namespace="peer_alice_session_chat-1"
        )

        self.assertTrue(valid)

    def test_namespace_validation_no_context(self):
        """Test namespace validation with no context"""
        valid = self.isolation.validate_namespace_access(
            peer_id=None,
            session_id=None,
            target_namespace="peer_alice"
        )

        self.assertFalse(valid)

    def test_accessible_namespaces_peer_only(self):
        """Test accessible namespaces for peer only"""
        namespaces = self.isolation.get_accessible_namespaces(peer_id="alice")

        self.assertEqual(len(namespaces), 1)
        self.assertIn("peer_alice", namespaces)

    def test_accessible_namespaces_session_only(self):
        """Test accessible namespaces for session only"""
        namespaces = self.isolation.get_accessible_namespaces(session_id="chat-1")

        self.assertEqual(len(namespaces), 1)
        self.assertIn("session_chat-1", namespaces)

    def test_accessible_namespaces_both(self):
        """Test accessible namespaces for both peer and session"""
        namespaces = self.isolation.get_accessible_namespaces(
            peer_id="alice",
            session_id="chat-1"
        )

        self.assertEqual(len(namespaces), 3)
        self.assertIn("peer_alice", namespaces)
        self.assertIn("session_chat-1", namespaces)
        self.assertIn("peer_alice_session_chat-1", namespaces)

    def test_accessible_namespaces_none(self):
        """Test accessible namespaces with no context"""
        namespaces = self.isolation.get_accessible_namespaces()

        self.assertEqual(len(namespaces), 0)

    def test_filter_results(self):
        """Test filtering results by namespace"""
        results = [
            {'_namespace': 'peer_alice', 'content': 'Alice message'},
            {'_namespace': 'peer_bob', 'content': 'Bob message'},
            {'_namespace': 'session_chat-1', 'content': 'Chat message'}
        ]

        allowed = ['peer_alice', 'session_chat-1']
        filtered = self.isolation.filter_results_by_namespace(results, allowed)

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]['_namespace'], 'peer_alice')
        self.assertEqual(filtered[1]['_namespace'], 'session_chat-1')

    def test_filter_results_empty_allowed(self):
        """Test filtering with no allowed namespaces"""
        results = [
            {'_namespace': 'peer_alice', 'content': 'Alice message'},
        ]

        filtered = self.isolation.filter_results_by_namespace(results, [])

        self.assertEqual(len(filtered), 0)

    def test_filter_results_no_namespace_tag(self):
        """Test filtering results without namespace tags"""
        results = [
            {'content': 'Message without namespace'},
            {'_namespace': 'peer_alice', 'content': 'Alice message'},
        ]

        allowed = ['peer_alice']
        filtered = self.isolation.filter_results_by_namespace(results, allowed)

        # Only results with matching namespace should be included
        self.assertEqual(len(filtered), 1)


class TestIsolatedSearch(unittest.TestCase):
    """Test IsolatedSearch class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.conn = sqlite3.connect(self.db_path)
        self.isolation = NamespaceIsolation(db_conn=self.conn)

        # Mock RAG instance
        class MockRAG:
            def __init__(self):
                self.documents = []

            def search(self, namespace, query, limit=10, **kwargs):
                # Return mock results with namespace tag
                return [
                    {
                        'content': f'Result for {query} in {namespace}',
                        '_namespace': namespace,
                        'score': 0.9
                    }
                ] * min(limit, 5)

            def add_document(self, namespace, content, **kwargs):
                self.documents.append({
                    'namespace': namespace,
                    'content': content
                })
                return {'id': 'doc-1', 'namespace': namespace}

        self.mock_rag = MockRAG()
        self.isolated_search = IsolatedSearch(self.mock_rag, self.isolation)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_search_peer_namespace(self):
        """Test searching in peer namespace"""
        results = self.isolated_search.search(
            query="test",
            peer_id="alice",
            limit=5
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]['_namespace'], 'peer_alice')

    def test_search_session_namespace(self):
        """Test searching in session namespace"""
        results = self.isolated_search.search(
            query="test",
            session_id="chat-1",
            limit=5
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]['_namespace'], 'session_chat-1')

    def test_search_peer_session_namespace(self):
        """Test searching in combined peer+session namespace"""
        results = self.isolated_search.search(
            query="test",
            peer_id="alice",
            session_id="chat-1",
            limit=5
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]['_namespace'], 'peer_alice_session_chat-1')

    def test_cross_namespace_search(self):
        """Test searching across accessible namespaces"""
        results = self.isolated_search.search(
            query="test",
            peer_id="alice",
            session_id="chat-1",
            cross_namespace=True,
            limit=6
        )

        # Should get results from 3 namespaces
        # Each namespace gets limit // 3 = 2 results
        self.assertEqual(len(results), 6)

    def test_search_no_namespace(self):
        """Test search with no namespace specified"""
        results = self.isolated_search.search(
            query="test",
            limit=5
        )

        self.assertEqual(len(results), 0)

    def test_add_document_peer_namespace(self):
        """Test adding document to peer namespace"""
        result = self.isolated_search.add_document(
            content="Test document",
            peer_id="alice"
        )

        self.assertEqual(result['namespace'], 'peer_alice')
        self.assertEqual(len(self.mock_rag.documents), 1)

    def test_add_document_session_namespace(self):
        """Test adding document to session namespace"""
        result = self.isolated_search.add_document(
            content="Test document",
            session_id="chat-1"
        )

        self.assertEqual(result['namespace'], 'session_chat-1')

    def test_add_document_peer_session_namespace(self):
        """Test adding document to combined namespace"""
        result = self.isolated_search.add_document(
            content="Test document",
            peer_id="alice",
            session_id="chat-1"
        )

        self.assertEqual(result['namespace'], 'peer_alice_session_chat-1')

    def test_add_document_default_namespace(self):
        """Test adding document without peer/session"""
        result = self.isolated_search.add_document(
            content="Test document"
        )

        self.assertEqual(result['namespace'], 'default')


class TestNamespaceScenarios(unittest.TestCase):
    """Test real-world namespace scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.conn = sqlite3.connect(self.db_path)
        self.isolation = NamespaceIsolation(db_conn=self.conn)

    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_multi_user_isolation(self):
        """Test isolation between multiple users"""
        users = ['alice', 'bob', 'charlie']

        for user in users:
            # Each user should have their own namespace
            namespace = self.isolation.get_peer_namespace(user)
            self.assertTrue(namespace.startswith(f'peer_{user}'))

            # Users should not be able to access each other's namespaces
            for other_user in users:
                if user != other_user:
                    other_namespace = self.isolation.get_peer_namespace(other_user)
                    can_access = self.isolation.validate_namespace_access(
                        peer_id=user,
                        session_id=None,
                        target_namespace=other_namespace
                    )
                    self.assertFalse(can_access, f"{user} should not access {other_user}'s namespace")

    def test_multi_session_isolation(self):
        """Test isolation between multiple sessions"""
        sessions = ['chat-1', 'chat-2', 'chat-3']

        for session in sessions:
            # Each session should have its own namespace
            namespace = self.isolation.get_session_namespace(session)
            self.assertTrue(namespace.startswith(f'session_{session}'))

            # Sessions should be isolated
            for other_session in sessions:
                if session != other_session:
                    other_namespace = self.isolation.get_session_namespace(other_session)
                    can_access = self.isolation.validate_namespace_access(
                        peer_id=None,
                        session_id=session,
                        target_namespace=other_namespace
                    )
                    self.assertFalse(can_access, f"{session} should not access {other_session}'s namespace")

    def test_cross_session_access_for_same_user(self):
        """Test that same user can access their data across sessions"""
        user = 'alice'
        sessions = ['chat-1', 'chat-2']

        # User should be able to access their peer namespace across sessions
        peer_namespace = self.isolation.get_peer_namespace(user)
        for session in sessions:
            can_access = self.isolation.validate_namespace_access(
                peer_id=user,
                session_id=session,
                target_namespace=peer_namespace
            )
            self.assertTrue(can_access, f"{user} should access their namespace from {session}")

    def test_combined_namespace_hierarchy(self):
        """Test combined namespace hierarchy"""
        # Combined namespace should be more specific than peer or session alone
        peer_namespace = self.isolation.get_peer_namespace('alice')
        session_namespace = self.isolation.get_session_namespace('chat-1')
        combined_namespace = self.isolation.get_peer_session_namespace('alice', 'chat-1')

        # Combined should contain both peer and session info
        self.assertIn('alice', combined_namespace)
        self.assertIn('chat-1', combined_namespace)

        # Combined should be different from individual namespaces
        self.assertNotEqual(combined_namespace, peer_namespace)
        self.assertNotEqual(combined_namespace, session_namespace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
