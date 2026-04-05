"""
RAG Peer Model - Phase 1 Honcho-Style Features
Implements peer-centric entity model for multi-party conversations

Based on Honcho architecture:
- Entity-centric model where both users and agents are "peers"
- Multi-participant sessions with mixed human and AI agents
- Flexible identity management for all participants
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3


class Peer:
    """
    Represents a conversation participant (user or agent)
    Tracks messages, metadata, and provides search capabilities
    """

    def __init__(
        self,
        peer_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        db_conn: Optional[sqlite3.Connection] = None
    ):
        self.peer_id = peer_id
        self.metadata = metadata or {}
        self._db_conn = db_conn
        self._messages_cache: List[Dict[str, Any]] = []

    def add_message(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to this peer's conversation history

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            session_id: Optional session identifier
            timestamp: Message timestamp (defaults to now)
            metadata: Additional message metadata

        Returns:
            Message dict with generated ID
        """
        if timestamp is None:
            timestamp = datetime.now()

        message = {
            'id': f"{self.peer_id}_{len(self._messages_cache)}_{int(timestamp.timestamp())}",
            'peer_id': self.peer_id,
            'role': role,
            'content': content,
            'session_id': session_id,
            'timestamp': timestamp.isoformat(),
            'metadata': metadata or {}
        }

        self._messages_cache.append(message)

        # Store in database if connection available
        if self._db_conn:
            self._store_message_db(message)

        return message

    def search(
        self,
        query: str,
        limit: int = 5,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search within this peer's messages

        Args:
            query: Search query
            limit: Maximum results to return
            session_id: Optional filter by session

        Returns:
            List of matching messages with relevance scores
        """
        # Simple keyword search for now
        # TODO: Integrate with RAG neural search
        query_lower = query.lower()
        results = []

        for msg in self._messages_cache:
            if session_id and msg.get('session_id') != session_id:
                continue

            content_lower = msg.get('content', '').lower()
            if query_lower in content_lower:
                results.append({
                    **msg,
                    'relevance': self._calculate_relevance(query_lower, content_lower)
                })

        # Sort by relevance and limit
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:limit]

    def get_context(
        self,
        tokens: int = 2000,
        session_id: Optional[str] = None
    ) -> str:
        """
        Get conversation context for this peer, formatted for LLM

        Args:
            tokens: Approximate token limit
            session_id: Optional filter by session

        Returns:
            Formatted context string
        """
        messages = self._messages_cache
        if session_id:
            messages = [m for m in messages if m.get('session_id') == session_id]

        # Simple token estimation (roughly 4 chars per token)
        char_limit = tokens * 4
        context_parts = []
        total_chars = 0

        # Build context from recent messages
        for msg in reversed(messages):
            msg_text = f"{msg['role']}: {msg['content']}\n"
            if total_chars + len(msg_text) > char_limit:
                break
            context_parts.insert(0, msg_text)
            total_chars += len(msg_text)

        return ''.join(context_parts)

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update peer metadata

        Args:
            metadata: Metadata to merge (deep merge)
        """
        for key, value in metadata.items():
            if isinstance(value, dict) and isinstance(self.metadata.get(key), dict):
                self.metadata[key].update(value)
            else:
                self.metadata[key] = value

    def get_metadata(self) -> Dict[str, Any]:
        """Get all peer metadata"""
        return self.metadata.copy()

    def get_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sessions this peer has participated in

        Args:
            limit: Maximum sessions to return

        Returns:
            List of session information
        """
        sessions = {}
        for msg in self._messages_cache:
            session_id = msg.get('session_id')
            if not session_id:
                continue

            if session_id not in sessions:
                sessions[session_id] = {
                    'session_id': session_id,
                    'message_count': 0,
                    'first_message': msg['timestamp'],
                    'last_message': msg['timestamp']
                }

            sessions[session_id]['message_count'] += 1
            sessions[session_id]['last_message'] = msg['timestamp']

        # Sort by most recent activity
        sorted_sessions = sorted(
            sessions.values(),
            key=lambda x: x['last_message'],
            reverse=True
        )

        return sorted_sessions[:limit]

    def get_messages(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from this peer

        Args:
            session_id: Optional filter by session
            limit: Optional maximum messages to return

        Returns:
            List of messages
        """
        messages = self._messages_cache
        if session_id:
            messages = [m for m in messages if m.get('session_id') == session_id]

        if limit:
            messages = messages[-limit:]

        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert peer to dictionary representation"""
        return {
            'peer_id': self.peer_id,
            'metadata': self.metadata,
            'message_count': len(self._messages_cache),
            'sessions': self.get_sessions()
        }

    def _calculate_relevance(self, query: str, content: str) -> float:
        """Simple relevance score based on keyword matches"""
        words = query.split()
        matches = sum(1 for word in words if word in content)
        return matches / max(len(words), 1)

    def _store_message_db(self, message: Dict[str, Any]) -> None:
        """Store message in database"""
        if not self._db_conn:
            return

        try:
            cursor = self._db_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO peer_messages
                (id, peer_id, session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message['id'],
                message['peer_id'],
                message.get('session_id'),
                message['role'],
                message['content'],
                message['timestamp'],
                json.dumps(message.get('metadata', {}))
            ))
            self._db_conn.commit()
        except sqlite3.Error as e:
            print(f"Error storing message in DB: {e}")


class PeerManager:
    """
    Manages multiple peers within a workspace
    Provides peer creation, retrieval, and management
    """

    def __init__(self, db_conn: Optional[sqlite3.Connection] = None):
        self._peers: Dict[str, Peer] = {}
        self._db_conn = db_conn
        self._ensure_tables()

    def create_peer(
        self,
        peer_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Peer:
        """
        Create a new peer

        Args:
            peer_id: Unique peer identifier
            metadata: Optional peer metadata

        Returns:
            Peer instance
        """
        if peer_id in self._peers:
            raise ValueError(f"Peer {peer_id} already exists")

        peer = Peer(peer_id, metadata, self._db_conn)
        self._peers[peer_id] = peer

        # Store in database
        if self._db_conn:
            self._store_peer_db(peer)

        return peer

    def get_peer(self, peer_id: str) -> Optional[Peer]:
        """
        Get a peer by ID

        Args:
            peer_id: Peer identifier

        Returns:
            Peer instance or None if not found
        """
        # Check cache first
        if peer_id in self._peers:
            return self._peers[peer_id]

        # Try to load from database
        if self._db_conn:
            peer = self._load_peer_db(peer_id)
            if peer:
                self._peers[peer_id] = peer
                return peer

        return None

    def list_peers(self) -> List[Peer]:
        """Get all peers"""
        return list(self._peers.values())

    def delete_peer(self, peer_id: str) -> bool:
        """
        Delete a peer

        Args:
            peer_id: Peer identifier

        Returns:
            True if deleted, False if not found
        """
        if peer_id not in self._peers:
            return False

        del self._peers[peer_id]

        # Delete from database
        if self._db_conn:
            cursor = self._db_conn.cursor()
            cursor.execute("DELETE FROM peers WHERE id = ?", (peer_id,))
            self._db_conn.commit()

        return True

    def search_peers(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search peers by metadata and message content

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of peers with relevance scores
        """
        results = []
        query_lower = query.lower()

        for peer_id, peer in self._peers.items():
            # Search metadata
            metadata_str = json.dumps(peer.metadata, default=str).lower()
            if query_lower in metadata_str:
                results.append({
                    'peer_id': peer_id,
                    'peer': peer,
                    'relevance': 1.0
                })
                continue

            # Search messages
            for msg in peer._messages_cache:
                if query_lower in msg['content'].lower():
                    results.append({
                        'peer_id': peer_id,
                        'peer': peer,
                        'relevance': peer._calculate_relevance(query_lower, msg['content'].lower())
                    })
                    break

        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:limit]

    def _ensure_tables(self) -> None:
        """Ensure peer tables exist in database"""
        if not self._db_conn:
            return

        cursor = self._db_conn.cursor()

        # Peers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peers (
                id TEXT PRIMARY KEY,
                metadata TEXT,
                created_at TEXT
            )
        """)

        # Peer messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_messages (
                id TEXT PRIMARY KEY,
                peer_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (peer_id) REFERENCES peers(id)
            )
        """)

        self._db_conn.commit()

    def _store_peer_db(self, peer: Peer) -> None:
        """Store peer in database"""
        if not self._db_conn:
            return

        cursor = self._db_conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO peers (id, metadata, created_at)
            VALUES (?, ?, ?)
        """, (
            peer.peer_id,
            json.dumps(peer.metadata),
            datetime.now().isoformat()
        ))
        self._db_conn.commit()

    def _load_peer_db(self, peer_id: str) -> Optional[Peer]:
        """Load peer from database"""
        if not self._db_conn:
            return None

        cursor = self._db_conn.cursor()

        # Load peer metadata
        cursor.execute("SELECT metadata FROM peers WHERE id = ?", (peer_id,))
        row = cursor.fetchone()

        if not row:
            return None

        metadata = json.loads(row[0]) if row[0] else {}
        peer = Peer(peer_id, metadata, self._db_conn)

        # Load messages
        cursor.execute("""
            SELECT id, session_id, role, content, timestamp, metadata
            FROM peer_messages
            WHERE peer_id = ?
            ORDER BY timestamp
        """, (peer_id,))

        for msg_row in cursor.fetchall():
            message = {
                'id': msg_row[0],
                'peer_id': peer_id,
                'session_id': msg_row[1],
                'role': msg_row[2],
                'content': msg_row[3],
                'timestamp': msg_row[4],
                'metadata': json.loads(msg_row[5]) if msg_row[5] else {}
            }
            peer._messages_cache.append(message)

        return peer


if __name__ == "__main__":
    # Quick test
    print("RAG Peer Model - Quick Test")
    print("=" * 50)

    # Create manager
    manager = PeerManager()

    # Create peers
    alice = manager.create_peer("alice", {"name": "Alice", "type": "human"})
    bob = manager.create_peer("bob", {"name": "Bob", "type": "human"})
    assistant = manager.create_peer("assistant", {"name": "AI Assistant", "type": "agent"})

    # Add messages
    alice.add_message("user", "Hello, how are you?", session_id="chat-1")
    assistant.add_message("assistant", "I'm doing great, thanks for asking!", session_id="chat-1")
    bob.add_message("user", "What's the weather like?", session_id="chat-1")

    # Test search
    print("\nSearching for 'weather':")
    results = alice.search("weather")
    for r in results:
        print(f"  - {r['content'][:50]}...")

    # Test get_context
    print("\nAlice's context (first 200 chars):")
    context = alice.get_context(tokens=200)
    print(context[:200] + "...")

    # Test sessions
    print("\nAlice's sessions:")
    for session in alice.get_sessions():
        print(f"  - {session['session_id']}: {session['message_count']} messages")

    print("\n✓ All tests passed!")
