#!/usr/bin/env python3
"""
Cron job: Sync new sessions to RAG database
Run this periodically (e.g., every hour) to keep RAG up to date
"""

import sys
import os

# Add rag-system to path
sys.path.insert(0, os.path.expanduser('~/rag-system'))

from sync_sessions import sync_new_sessions, sync_stats

def main():
    """Run session sync"""

    # Sync last 10 sessions (only new ones)
    synced = sync_new_sessions(limit=10, dry_run=False)

    # Show stats
    sync_stats()

    return 0 if synced > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
