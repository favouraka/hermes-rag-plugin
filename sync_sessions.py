"""
Background Session Synchronization
Periodically syncs new sessions from ~/.hermes/sessions/ to RAG database
"""

import os
import json
from pathlib import Path
from datetime import datetime
from rag_api_hardened import RAGHardened

def get_latest_sessions(limit=5):
    """Get the most recent session files"""
    sessions_dir = Path.home() / ".hermes" / "sessions"

    if not sessions_dir.exists():
        print(f"Sessions directory not found: {sessions_dir}")
        return []

    # Get all session files, sorted by modification time
    session_files = sorted(
        sessions_dir.glob("session_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return session_files[:limit]

def sync_new_sessions(limit=10, dry_run=False):
    """
    Sync new or updated sessions to RAG database

    Args:
        limit: Maximum number of sessions to sync
        dry_run: If True, just report what would be synced (don't actually sync)
    """
    print("=" * 60)
    print("Session Synchronization")
    print("=" * 60)

    rag = RAGHardened.get()

    # Get recent sessions
    session_files = get_latest_sessions(limit)

    if not session_files:
        print("No session files found.")
        return

    synced_count = 0
    skipped_count = 0

    for session_file in session_files:
        session_id = session_file.stem

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)

            # Check if session already in RAG (look for existing source_id)
            existing = rag.get_by_source_id(session_id)

            if existing:
                print(f"  ⊘ Skipping (already indexed): {session_id}")
                skipped_count += 1
                continue

            # Get session metadata
            title = data.get('title', 'Untitled')
            timestamp = data.get('created_at', datetime.now().isoformat())
            messages = data.get('messages', [])

            if not messages:
                print(f"  ⊘ Skipping (no messages): {session_id}")
                skipped_count += 1
                continue

            # Build content from messages
            content_parts = []
            for msg in messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if content:
                    content_parts.append(f"{role.upper()}: {content}")

            full_content = f"Session: {title}\nDate: {timestamp}\n\n" + "\n\n".join(content_parts)

            # Add to RAG (unless dry run)
            if not dry_run:
                rag.add_document(
                    namespace="sessions",
                    content=full_content,
                    source_id=session_id,
                    metadata={
                        "type": "session",
                        "title": title,
                        "created_at": timestamp,
                        "message_count": len(messages),
                        "auto_synced": True,
                        "synced_at": datetime.now().isoformat(),
                        "file_path": str(session_file)
                    }
                )

            print(f"  ✓ Synced: {session_id} ({len(messages)} messages)")
            synced_count += 1

        except Exception as e:
            print(f"  ✗ Error syncing {session_id}: {e}")

    print("\n" + "=" * 60)
    print(f"Sync complete: {synced_count} synced, {skipped_count} skipped")
    print("=" * 60)

    return synced_count

def full_sync(dry_run=False):
    """
    Perform a full sync of all sessions
    """
    print("=" * 60)
    print("Full Session Synchronization")
    print("=" * 60)

    sessions_dir = Path.home() / ".hermes" / "sessions"

    if not sessions_dir.exists():
        print(f"Sessions directory not found: {sessions_dir}")
        return

    # Get all session files
    session_files = list(sessions_dir.glob("session_*.json"))

    print(f"Found {len(session_files)} session files")

    if not session_files:
        return

    rag = RAGHardened.get()

    synced_count = 0
    skipped_count = 0

    for session_file in session_files:
        session_id = session_file.stem

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)

            # Check if already synced
            existing = rag.get_by_source_id(session_id)

            if existing:
                skipped_count += 1
                continue

            # Get session data
            title = data.get('title', 'Untitled')
            timestamp = data.get('created_at', datetime.now().isoformat())
            messages = data.get('messages', [])

            if not messages:
                skipped_count += 1
                continue

            # Build content
            content_parts = []
            for msg in messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if content:
                    content_parts.append(f"{role.upper()}: {content}")

            full_content = f"Session: {title}\nDate: {timestamp}\n\n" + "\n\n".join(content_parts)

            # Add to RAG
            if not dry_run:
                rag.add_document(
                    namespace="sessions",
                    content=full_content,
                    source_id=session_id,
                    metadata={
                        "type": "session",
                        "title": title,
                        "created_at": timestamp,
                        "message_count": len(messages),
                        "full_synced": True,
                        "synced_at": datetime.now().isoformat(),
                        "file_path": str(session_file)
                    }
                )

            synced_count += 1
            print(f"  ✓ Synced: {session_id}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            skipped_count += 1

    print(f"\nSynced: {synced_count}, Skipped: {skipped_count}")

    return synced_count

def sync_stats():
    """Show sync statistics"""
    rag = RAGHardened.get()
    stats = rag.get_stats()

    print("\n" + "=" * 60)
    print("RAG Database Statistics")
    print("=" * 60)
    print(f"Total documents: {stats['total_documents']}")
    print(f"Sessions: {stats['namespace_breakdown'].get('sessions', 0)}")
    print(f"Facts: {stats['namespace_breakdown'].get('facts', 0)}")
    print(f"Projects: {stats['namespace_breakdown'].get('projects', 0)}")
    print(f"Tools/Skills: {stats['namespace_breakdown'].get('tools_skills', 0)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Sync sessions to RAG')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Limit number of sessions to sync')
    parser.add_argument('--full', '-f', action='store_true', help='Perform full sync of all sessions')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Show what would be synced without syncing')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics')

    args = parser.parse_args()

    if args.stats:
        sync_stats()
    elif args.full:
        full_sync(dry_run=args.dry_run)
    else:
        sync_new_sessions(limit=args.limit, dry_run=args.dry_run)
