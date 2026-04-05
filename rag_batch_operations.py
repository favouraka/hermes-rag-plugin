"""
Batch operations for RAG system.
Supports batch indexing, batch search, and batch flush operations.
"""

from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class BatchOperations:
    """Batch operations for RAG system."""

    def __init__(self, rag_db, max_workers: int = 4):
        """
        Initialize batch operations.

        Args:
            rag_db: RAG database instance (RAGDatabaseHardened)
            max_workers: Maximum number of concurrent workers
        """
        self.rag_db = rag_db
        self.max_workers = max_workers

    def batch_index(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 10,
        show_progress: bool = False
    ) -> Dict[str, Any]:
        """
        Index multiple documents in batches.

        Args:
            documents: List of documents to index (each with namespace, content, source_id, metadata)
            batch_size: Number of documents per batch
            show_progress: Show progress information

        Returns:
            Dictionary with results
        """
        if not documents:
            return {
                "total": 0,
                "indexed": 0,
                "failed": 0,
                "errors": [],
                "duration": 0,
            }

        start_time = time.time()
        indexed = 0
        failed = 0
        errors = []

        # Process in batches
        num_batches = (len(documents) + batch_size - 1) // batch_size

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i // batch_size + 1

            if show_progress:
                print(f"Processing batch {batch_num}/{num_batches} ({len(batch)} documents)...")

            # Index each document in batch
            for doc in batch:
                try:
                    self.rag_db.add_document(
                        namespace=doc.get("namespace", "default"),
                        content=doc.get("content", ""),
                        source_id=doc.get("source_id"),
                        metadata=doc.get("metadata", {}),
                    )
                    indexed += 1
                except Exception as e:
                    failed += 1
                    errors.append({
                        "source_id": doc.get("source_id", "unknown"),
                        "error": str(e),
                    })
                    if show_progress:
                        print(f"  ✗ Failed to index doc {doc.get('source_id', 'unknown')}: {e}")

            if show_progress:
                print(f"  ✓ Batch {batch_num} complete: {len(batch)} processed")

        duration = time.time() - start_time

        return {
            "total": len(documents),
            "indexed": indexed,
            "failed": failed,
            "errors": errors[:10],  # Limit errors to first 10
            "duration": round(duration, 2),
            "docs_per_second": round(len(documents) / duration, 2) if duration > 0 else 0,
        }

    def batch_search(
        self,
        queries: List[str],
        limit: int = 5,
        namespace: str = None,
        use_parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for multiple queries.

        Args:
            queries: List of queries to search
            limit: Number of results per query
            namespace: Namespace to search (or None for all)
            use_parallel: Use parallel execution for multiple queries

        Returns:
            List of search results, one per query
        """
        if not queries:
            return []

        results = []

        if not use_parallel or len(queries) == 1:
            # Sequential processing
            for query in queries:
                try:
                    result = self.rag_db.search(query, limit=limit, namespace=namespace)
                    results.append({
                        "query": query,
                        "results": result,
                        "success": True,
                    })
                except Exception as e:
                    results.append({
                        "query": query,
                        "results": [],
                        "success": False,
                        "error": str(e),
                    })
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(queries))) as executor:
                futures = {
                    executor.submit(
                        self.rag_db.search,
                        query,
                        limit=limit,
                        namespace=namespace
                    ): query for query in queries
                }

                for future in as_completed(futures):
                    query = futures[future]
                    try:
                        search_results = future.result()
                        results.append({
                            "query": query,
                            "results": search_results,
                            "success": True,
                        })
                    except Exception as e:
                        results.append({
                            "query": query,
                            "results": [],
                            "success": False,
                            "error": str(e),
                        })

        return results

    def batch_flush_sessions(
        self,
        sessions: List[str],
        show_progress: bool = False
    ) -> Dict[str, Any]:
        """
        Flush multiple sessions.

        Args:
            sessions: List of session IDs to flush
            show_progress: Show progress information

        Returns:
            Dictionary with results
        """
        if not sessions:
            return {
                "total": 0,
                "flushed": 0,
                "failed": 0,
                "errors": [],
                "duration": 0,
            }

        start_time = time.time()
        flushed = 0
        failed = 0
        errors = []

        for session_id in sessions:
            try:
                # Get session data
                session_data = self.rag_db.get_session_data(session_id)

                if session_data:
                    # Add session as a document
                    self.rag_db.add_document(
                        content=session_data.get("content", ""),
                        metadata={
                            "type": "session",
                            "session_id": session_id,
                            "messages": session_data.get("message_count", 0),
                            "timestamp": session_data.get("timestamp", time.time()),
                        },
                        namespace="sessions",
                    )
                    flushed += 1

                    if show_progress:
                        print(f"✓ Flushed session {session_id}")
                else:
                    failed += 1
                    errors.append({
                        "session_id": session_id,
                        "error": "Session data not found",
                    })

            except Exception as e:
                failed += 1
                errors.append({
                    "session_id": session_id,
                    "error": str(e),
                })
                if show_progress:
                    print(f"✗ Failed to flush session {session_id}: {e}")

        duration = time.time() - start_time

        return {
            "total": len(sessions),
            "flushed": flushed,
            "failed": failed,
            "errors": errors[:10],
            "duration": round(duration, 2),
        }

    def batch_delete(
        self,
        source_ids: List[str],
        show_progress: bool = False
    ) -> Dict[str, Any]:
        """
        Delete multiple documents by source_id.

        Note: This requires database-level delete functionality.
        Current implementation marks documents as deleted via metadata.

        Args:
            source_ids: List of source IDs to delete
            show_progress: Show progress information

        Returns:
            Dictionary with results
        """
        # Note: RAGDatabaseHardened doesn't have delete_document method
        # This is a placeholder for future implementation
        if not source_ids:
            return {
                "total": 0,
                "deleted": 0,
                "failed": 0,
                "errors": [],
                "duration": 0,
            }

        start_time = time.time()
        deleted = 0
        failed = 0
        errors = []

        # For now, we can only get documents by source_id
        # True deletion would require database schema changes
        for source_id in source_ids:
            try:
                # Try to get the document
                doc = self.rag_db.get_by_source_id(source_id)
                if doc:
                    # Document exists but we can't delete it yet
                    failed += 1
                    errors.append({
                        "source_id": source_id,
                        "error": "Delete not implemented yet - document would need schema update",
                    })
                    if show_progress:
                        print(f"⚠ Delete not implemented for {source_id}")
                else:
                    # Document doesn't exist
                    failed += 1
                    errors.append({
                        "source_id": source_id,
                        "error": "Document not found",
                    })
            except Exception as e:
                failed += 1
                errors.append({
                    "source_id": source_id,
                    "error": str(e),
                })
                if show_progress:
                    print(f"✗ Failed to delete document {source_id}: {e}")

        duration = time.time() - start_time

        return {
            "total": len(source_ids),
            "deleted": deleted,
            "failed": failed,
            "errors": errors[:10],
            "duration": round(duration, 2),
            "note": "Delete not fully implemented - requires database schema changes",
        }

    def batch_get_stats(
        self,
        namespaces: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for multiple namespaces.

        Args:
            namespaces: List of namespaces (None = all)

        Returns:
            Dictionary with statistics
        """
        if not namespaces:
            # Get all namespaces
            stats = self.rag_db.get_stats()
            return {
                "overall": stats,
                "namespaces": {},
            }

        namespace_stats = {}
        for namespace in namespaces:
            try:
                namespace_stats[namespace] = self.rag_db.get_stats(namespace=namespace)
            except Exception as e:
                namespace_stats[namespace] = {
                    "error": str(e),
                }

        return {
            "overall": self.rag_db.get_stats(),
            "namespaces": namespace_stats,
        }


def demo_batch_operations():
    """Demonstrate batch operations."""
    print("\n=== Batch Operations Demo ===\n")

    from rag_database_hardened import RAGDatabaseHardened

    # Create test database
    db = RAGDatabaseHardened(":memory:")  # In-memory for demo
    db.connect()  # Need to connect first
    batch_ops = BatchOperations(db, max_workers=2)

    # Sample documents (using correct API format)
    documents = [
        {
            "content": "Document 1: Database setup guide",
            "metadata": {"type": "guide"},
            "namespace": "guides",
            "source_id": "doc1",
        },
        {
            "content": "Document 2: API design patterns",
            "metadata": {"type": "guide"},
            "namespace": "guides",
            "source_id": "doc2",
        },
        {
            "content": "Document 3: Memory management best practices",
            "metadata": {"type": "best_practices"},
            "namespace": "best_practices",
            "source_id": "doc3",
        },
        {
            "content": "Document 4: User authentication flow",
            "metadata": {"type": "flow"},
            "namespace": "flows",
            "source_id": "doc4",
        },
        {
            "content": "Document 5: Error handling strategies",
            "metadata": {"type": "guide"},
            "namespace": "guides",
            "source_id": "doc5",
        },
    ]

    # Batch index
    print("1. Batch Index:")
    result = batch_ops.batch_index(documents, batch_size=2, show_progress=True)
    print(f"   Indexed {result['indexed']}/{result['total']} documents in {result['duration']}s")
    print(f"   Speed: {result['docs_per_second']} docs/sec")

    # Batch search
    print("\n2. Batch Search:")
    queries = ["database", "API", "memory"]
    results = batch_ops.batch_search(queries, limit=2, use_parallel=True)
    for r in results:
        print(f"   Query: '{r['query']}' → {len(r['results'])} results")
        if r['results'] and len(r['results']) > 0:
            print(f"      Top: {r['results'][0].get('content', 'N/A')[:50]}")

    # Stats
    print("\n3. Get Stats:")
    stats = db.get_stats()
    print(f"   Total documents: {stats.get('total_documents', 0)}")
    print(f"   Namespaces: {list(stats.get('namespace_counts', {}).keys())}")

    # Get by namespace
    print("\n4. Get by Namespace:")
    guides = db.get_by_namespace("guides")
    print(f"   Found {len(guides)} documents in 'guides' namespace")

    # Batch stats by namespace
    print("\n5. Batch Stats:")
    batch_stats = batch_ops.batch_get_stats(namespaces=["guides", "best_practices"])
    for ns, ns_stats in batch_stats['namespaces'].items():
        print(f"   Namespace '{ns}': {ns_stats.get('total_documents', 0)} documents")


if __name__ == "__main__":
    demo_batch_operations()
