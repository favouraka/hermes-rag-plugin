"""
Query interface for RAG system
Usage: python3 rag_query.py "search query" [--namespace <name>] [--limit <n>]
"""

import sys
import argparse
import json
from rag_database import RAGDatabase

def format_result(result):
    """Format a search result for display"""
    namespace = result['namespace']
    content = result['content'][:200]
    distance = result['distance']
    metadata = result.get('metadata')

    meta_str = ""
    if metadata:
        # Parse JSON metadata
        try:
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            elif metadata is None:
                metadata = {}

            meta_parts = []
            for key, value in list(metadata.items())[:3]:  # Show top 3 metadata items
                if value:
                    meta_parts.append(f"{key}={value}")
            if meta_parts:
                meta_str = f" [{', '.join(meta_parts)}]"
        except json.JSONDecodeError:
            pass

    return f"[{namespace.upper()}] {content}... (dist: {distance:.3f}){meta_str}"

def main():
    parser = argparse.ArgumentParser(description='Query RAG database')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--namespace', '-n', help='Filter by namespace (sessions, projects, facts, tools_skills)')
    parser.add_argument('--limit', '-l', type=int, default=5, help='Number of results (default: 5)')
    parser.add_argument('--list-namespaces', action='store_true', help='List all namespaces')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')

    args = parser.parse_args()

    # If using --stats or --list-namespaces, query is not required
    if not args.query and not args.stats and not args.list_namespaces:
        parser.error("query is required unless using --stats or --list-namespaces")

    rag = RAGDatabase()
    rag.connect()

    try:
        if args.stats:
            stats = rag.get_stats()
            print("=" * 50)
            print("RAG Database Statistics")
            print("=" * 50)
            print(f"Total documents: {stats['total_documents']}")
            print(f"\nNamespace breakdown:")
            for ns, count in stats['namespace_breakdown'].items():
                print(f"  {ns}: {count}")
            print(f"\nProjects: {stats['total_projects']}")
            print(f"Tools tracked: {stats['total_tools_tracked']}")
            print(f"Total tool uses: {stats['total_tool_uses']}")

        elif args.list_namespaces:
            stats = rag.get_stats()
            print("Available namespaces:")
            for ns in stats['namespace_breakdown'].keys():
                count = stats['namespace_breakdown'][ns]
                print(f"  - {ns} ({count} documents)")

        else:
            # Perform search
            results = rag.search(args.query, namespace=args.namespace, limit=args.limit)

            print(f"\n{'=' * 60}")
            print(f"Search: {args.query}")
            if args.namespace:
                print(f"Namespace: {args.namespace}")
            print(f"{'=' * 60}\n")

            if not results:
                print("No results found.")
            else:
                for i, result in enumerate(results, 1):
                    print(f"{i}. {format_result(result)}")
                    print()

    finally:
        rag.close()

if __name__ == "__main__":
    main()
