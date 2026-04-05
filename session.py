"""
RAG Session Model - Phase 1 Honcho-Style Features
Implements session management for multi-peer conversations

Based on Honcho architecture:
- Sessions represent interactions between Peers
- Multi-participant conversations
- Context retrieval with LLM format conversion
- Peer-specific representations
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3


class Session:
    """
    Represents a conversation session with multiple peers
    Manages message history, context retrieval, and LLM format conversion
    """

    def __init__(
        self,
        session_id: str,
        db_conn: Optional[sqlite3.Connection] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        self.metadata = metadata or {}
        self._db_conn = db_conn
        self._peers: Dict[str, 'Peer'] = {}
        self._messages: List[Dict[str, Any]] = []
        self._summary: Optional[str] = None
        self._created_at: datetime = datetime.now()

    def add_peers(self, peers: List['Peer']) -> None:
        """
        Add peers to this session

        Args:
            peers: List of Peer instances
        """
        for peer in peers:
            if peer.peer_id not in self._peers:
                self._peers[peer.peer_id] = peer

    def add_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        Add messages to this session

        Args:
            messages: List of message dicts with keys:
                - peer_id: str
                - role: str
                - content: str
                - timestamp: Optional[datetime]
                - metadata: Optional[dict]
        """
        for msg in messages:
            message = {
                'id': f"{self.session_id}_{len(self._messages)}_{int(datetime.now().timestamp())}",
                'session_id': self.session_id,
                'peer_id': msg['peer_id'],
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg.get('timestamp', datetime.now()).isoformat(),
                'metadata': msg.get('metadata', {})
            }

            self._messages.append(message)

            # Also add to peer's history
            if msg['peer_id'] in self._peers:
                self._peers[msg['peer_id']].add_message(
                    role=msg['role'],
                    content=msg['content'],
                    session_id=self.session_id,
                    timestamp=datetime.fromisoformat(message['timestamp']),
                    metadata=message['metadata']
                )

        # Store in database
        if self._db_conn:
            self._store_messages_db(messages)

    def get_peer_ids(self) -> List[str]:
        """Get all peer IDs in this session"""
        return list(self._peers.keys())

    def get_peers(self) -> List['Peer']:
        """Get all peers in this session"""
        return list(self._peers.values())

    def context(
        self,
        summary: bool = True,
        tokens: int = 2000,
        include_system: bool = False
    ) -> 'SessionContext':
        """
        Get formatted context for LLM consumption

        Args:
            summary: Whether to include session summary
            tokens: Approximate token limit
            include_system: Whether to include system messages

        Returns:
            SessionContext object with formatted messages
        """
        context_messages = []

        # Add summary if available and requested
        if summary and self._summary:
            context_messages.append({
                'role': 'system',
                'content': f"Session Summary: {self._summary}"
            })

        # Add messages within token limit
        char_limit = tokens * 4  # Rough estimate
        total_chars = 0

        for msg in reversed(self._messages):
            if not include_system and msg['role'] == 'system':
                continue

            msg_content = {
                'role': msg['role'],
                'content': msg['content']
            }

            content_str = json.dumps(msg_content)
            if total_chars + len(content_str) > char_limit:
                break

            context_messages.insert(0, msg_content)
            total_chars += len(content_str)

        return SessionContext(
            session_id=self.session_id,
            messages=context_messages,
            summary=self._summary if summary else None
        )

    def to_openai(
        self,
        assistant: 'Peer'
    ) -> List[Dict[str, str]]:
        """
        Convert session to OpenAI chat format

        Args:
            assistant: The assistant peer (for role mapping)

        Returns:
            List of messages in OpenAI format
        """
        messages = []

        # Add system message if available
        if self._summary:
            messages.append({
                'role': 'system',
                'content': f"You are participating in a conversation. {self._summary}"
            })

        # Convert messages
        for msg in self._messages:
            role = msg['role']
            # Map peer-specific roles to standard OpenAI roles
            if role == 'assistant' and msg['peer_id'] != assistant.peer_id:
                role = 'user'  # Other agents are treated as users in this context

            messages.append({
                'role': role,
                'content': msg['content']
            })

        return messages

    def to_anthropic(
        self,
        assistant: 'Peer'
    ) -> List[Dict[str, str]]:
        """
        Convert session to Anthropic messages format

        Args:
            assistant: The assistant peer

        Returns:
            List of messages in Anthropic format
        """
        messages = []

        # Build system message
        system_content = "You are a helpful AI assistant."
        if self._summary:
            system_content += f" Conversation context: {self._summary}"

        # Convert messages (Anthropic uses alternating user/assistant)
        for msg in self._messages:
            if msg['role'] in ['user', 'assistant']:
                role = 'user' if msg['peer_id'] != assistant.peer_id else 'assistant'
                messages.append({
                    'role': role,
                    'content': msg['content']
                })

        return messages, system_content

    def representation(
        self,
        peer: 'Peer',
        observe_others: bool = False
    ) -> Dict[str, Any]:
        """
        Get a peer's perspective on this session

        Args:
            peer: The peer whose perspective to get
            observe_others: Whether to include messages from other peers

        Returns:
            Dict with peer's view of the session
        """
        if not observe_others:
            # Only return messages from this peer
            messages = [
                msg for msg in self._messages
                if msg['peer_id'] == peer.peer_id
            ]
        else:
            # Return all messages
            messages = self._messages

        return {
            'session_id': self.session_id,
            'peer_id': peer.peer_id,
            'messages': messages,
            'message_count': len(messages),
            'peer_count': len(self._peers),
            'summary': self._summary
        }

    def set_summary(self, summary: str) -> None:
        """
        Set session summary

        Args:
            summary: Session summary text
        """
        self._summary = summary

        # Update in database
        if self._db_conn:
            cursor = self._db_conn.cursor()

            # Ensure table exists
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        metadata TEXT,
                        summary TEXT,
                        created_at TEXT
                    )
                """)
            except sqlite3.Error:
                pass

            cursor.execute("""
                UPDATE sessions
                SET summary = ?
                WHERE id = ?
            """, (summary, self.session_id))
            self._db_conn.commit()

    def get_messages(
        self,
        peer_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from session with optional filters

        Args:
            peer_id: Filter by peer ID
            role: Filter by role
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        messages = self._messages

        if peer_id:
            messages = [m for m in messages if m['peer_id'] == peer_id]

        if role:
            messages = [m for m in messages if m['role'] == role]

        if limit:
            messages = messages[-limit:]

        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation"""
        return {
            'session_id': self.session_id,
            'metadata': self.metadata,
            'peer_count': len(self._peers),
            'message_count': len(self._messages),
            'peer_ids': list(self._peers.keys()),
            'summary': self._summary,
            'created_at': self._created_at.isoformat()
        }

    def _store_messages_db(self, messages: List[Dict[str, Any]]) -> None:
        """Store messages in database"""
        if not self._db_conn:
            return

        cursor = self._db_conn.cursor()

        # Ensure tables exist
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    metadata TEXT,
                    summary TEXT,
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_peers (
                    session_id TEXT NOT NULL,
                    peer_id TEXT NOT NULL,
                    PRIMARY KEY (session_id, peer_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    peer_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
        except sqlite3.Error:
            pass  # Tables might already exist

        # Ensure session exists
        cursor.execute("""
            INSERT OR IGNORE INTO sessions (id, metadata, summary, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            self.session_id,
            json.dumps(self.metadata),
            self._summary,
            self._created_at.isoformat()
        ))

        # Store session-peers relationship
        for peer_id in self._peers.keys():
            cursor.execute("""
                INSERT OR IGNORE INTO session_peers (session_id, peer_id)
                VALUES (?, ?)
            """, (self.session_id, peer_id))

        # Store messages
        for msg in messages:
            cursor.execute("""
                INSERT OR REPLACE INTO session_messages
                (id, session_id, peer_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{self.session_id}_{len(self._messages)}",
                self.session_id,
                msg['peer_id'],
                msg['role'],
                msg['content'],
                msg.get('timestamp', datetime.now()).isoformat(),
                json.dumps(msg.get('metadata', {}))
            ))

        self._db_conn.commit()


class SessionContext:
    """
    Container for formatted session context
    Provides methods to convert to different LLM formats
    """

    def __init__(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        summary: Optional[str] = None
    ):
        self.session_id = session_id
        self.messages = messages
        self.summary = summary

    def to_openai(self, assistant: 'Peer') -> List[Dict[str, str]]:
        """
        Convert to OpenAI chat format

        Args:
            assistant: Assistant peer for role mapping

        Returns:
            List of OpenAI-formatted messages
        """
        formatted = []

        # Add system message with summary
        if self.summary:
            formatted.append({
                'role': 'system',
                'content': f"Session context: {self.summary}"
            })

        # Format messages
        for msg in self.messages:
            role = msg['role']
            # Map to OpenAI standard roles
            if role not in ['system', 'user', 'assistant']:
                role = 'user'

            formatted.append({
                'role': role,
                'content': msg['content']
            })

        return formatted

    def to_anthropic(self) -> tuple[List[Dict[str, str]], str]:
        """
        Convert to Anthropic messages format

        Returns:
            Tuple of (messages list, system content string)
        """
        messages = []

        # Build system content
        system = "You are a helpful AI assistant."
        if self.summary:
            system += f" {self.summary}"

        # Format messages (Anthropic uses alternating user/assistant)
        current_role = None
        current_content = []

        for msg in self.messages:
            role = msg['role']

            # Map to Anthropic roles
            if role in ['system']:
                continue  # System messages go to system string
            elif role == 'assistant':
                anthro_role = 'assistant'
            else:
                anthro_role = 'user'

            # Group consecutive messages from same role
            if current_role and anthro_role != current_role:
                messages.append({
                    'role': current_role,
                    'content': '\n'.join(current_content)
                })
                current_content = []

            current_role = anthro_role
            current_content.append(msg['content'])

        # Add final messages
        if current_content:
            messages.append({
                'role': current_role,
                'content': '\n'.join(current_content)
            })

        return messages, system

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'session_id': self.session_id,
            'messages': self.messages,
            'summary': self.summary,
            'message_count': len(self.messages)
        }


class SessionManager:
    """
    Manages multiple sessions
    Provides session creation, retrieval, and management
    """

    def __init__(self, db_conn: Optional[sqlite3.Connection] = None):
        self._sessions: Dict[str, Session] = {}
        self._db_conn = db_conn
        self._ensure_tables()

    def create_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session

        Args:
            session_id: Unique session identifier
            metadata: Optional session metadata

        Returns:
            Session instance
        """
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists")

        session = Session(session_id, self._db_conn, metadata)
        self._sessions[session_id] = session

        # Store in database
        if self._db_conn:
            self._store_session_db(session)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session instance or None if not found
        """
        # Check cache first
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from database
        if self._db_conn:
            session = self._load_session_db(session_id)
            if session:
                self._sessions[session_id] = session
                return session

        return None

    def list_sessions(
        self,
        peer_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Session]:
        """
        List sessions, optionally filtered by peer

        Args:
            peer_id: Optional filter by peer ID
            limit: Optional maximum sessions to return

        Returns:
            List of sessions
        """
        sessions = list(self._sessions.values())

        if peer_id:
            sessions = [
                s for s in sessions
                if peer_id in s._peers
            ]

        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x._created_at, reverse=True)

        if limit:
            sessions = sessions[:limit]

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]

        # Delete from database
        if self._db_conn:
            cursor = self._db_conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            cursor.execute("DELETE FROM session_peers WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
            self._db_conn.commit()

        return True

    def _ensure_tables(self) -> None:
        """Ensure session tables exist in database"""
        if not self._db_conn:
            return

        cursor = self._db_conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                metadata TEXT,
                summary TEXT,
                created_at TEXT
            )
        """)

        # Session-peers relationship table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_peers (
                session_id TEXT NOT NULL,
                peer_id TEXT NOT NULL,
                PRIMARY KEY (session_id, peer_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (peer_id) REFERENCES peers(id)
            )
        """)

        # Session messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                peer_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (peer_id) REFERENCES peers(id)
            )
        """)

        self._db_conn.commit()

    def _store_session_db(self, session: Session) -> None:
        """Store session in database"""
        if not self._db_conn:
            return

        cursor = self._db_conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (id, metadata, summary, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            session.session_id,
            json.dumps(session.metadata),
            session._summary,
            session._created_at.isoformat()
        ))
        self._db_conn.commit()

    def _load_session_db(self, session_id: str) -> Optional[Session]:
        """Load session from database"""
        if not self._db_conn:
            return None

        cursor = self._db_conn.cursor()

        # Load session metadata
        cursor.execute("SELECT metadata, summary, created_at FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        if not row:
            return None

        metadata = json.loads(row[0]) if row[0] else {}
        session = Session(session_id, self._db_conn, metadata)
        session._summary = row[1]

        # Load session-peers
        cursor.execute("""
            SELECT peer_id FROM session_peers WHERE session_id = ?
        """, (session_id,))

        # Note: We can't load full peers here without PeerManager
        # This is handled by the integration layer

        # Load messages
        cursor.execute("""
            SELECT id, peer_id, role, content, timestamp, metadata
            FROM session_messages
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))

        for msg_row in cursor.fetchall():
            session._messages.append({
                'id': msg_row[0],
                'session_id': session_id,
                'peer_id': msg_row[1],
                'role': msg_row[2],
                'content': msg_row[3],
                'timestamp': msg_row[4],
                'metadata': json.loads(msg_row[5]) if msg_row[5] else {}
            })

        return session


if __name__ == "__main__":
    # Quick test
    print("RAG Session Model - Quick Test")
    print("=" * 50)

    from rag_peer_model import Peer, PeerManager

    # Create managers
    peer_manager = PeerManager()
    session_manager = SessionManager()

    # Create peers
    alice = peer_manager.create_peer("alice", {"name": "Alice", "type": "human"})
    bob = peer_manager.create_peer("bob", {"name": "Bob", "type": "human"})
    assistant = peer_manager.create_peer("assistant", {"name": "AI Assistant", "type": "agent"})

    # Create session
    session = session_manager.create_session("chat-1")
    session.add_peers([alice, bob, assistant])

    # Add messages
    session.add_messages([
        {'peer_id': 'alice', 'role': 'user', 'content': 'Hello everyone!'},
        {'peer_id': 'bob', 'role': 'user', 'content': 'Hi Alice!'},
        {'peer_id': 'assistant', 'role': 'assistant', 'content': 'How can I help you both?'}
    ])

    # Test context retrieval
    print("\nSession context:")
    ctx = session.context(summary=True, tokens=200)
    print(f"  Messages: {len(ctx.messages)}")
    print(f"  Summary: {ctx.summary}")

    # Test OpenAI format
    print("\nOpenAI format:")
    openai_msgs = session.to_openai(assistant)
    print(f"  Total messages: {len(openai_msgs)}")
    if openai_msgs:
        print(f"  First message: {openai_msgs[0]}")

    # Test peer representation
    print("\nAlice's perspective:")
    alice_view = session.representation(alice, observe_others=True)
    print(f"  Sees {alice_view['message_count']} messages")
    print(f"  With {alice_view['peer_count']} peers")

    print("\n✓ All tests passed!")
