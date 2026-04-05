#!/usr/bin/env python3
"""
Index all workspace files into RAG
This finds and indexes markdown/text files from the workspace
"""

import os
import sys
from pathlib import Path
from rag_api import RAG

def find_files_to_index(workspace_path):
    """Find all indexable files in workspace"""
    extensions = ['.md', '.txt', '.rst', '.org']
    exclude_dirs = {'node_modules', '.git', 'venv', '__pycache__', '.venv', 'dist', 'build'}
    files = []

    for ext in extensions:
        for file_path in Path(workspace_path).glob(f'**/*{ext}'):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            files.append(file_path)

    return sorted(files)

def index_file(rag, file_path, workspace_root):
    """Index a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Skip empty or very small files
        if len(content.strip()) < 50:
            return None

        # Create relative path as source_id
        rel_path = str(file_path.relative_to(workspace_root))

        # Add as a project document
        result = rag.add_document(
            namespace='projects',
            content=content,
            source_id=rel_path,
            metadata={
                'file_type': file_path.suffix,
                'size_bytes': len(content),
                'indexed_at': 'manual_index'
            }
        )

        return {
            'file': rel_path,
            'success': result is not None,
            'size': len(content)
        }
    except Exception as e:
        return {
            'file': str(file_path.relative_to(workspace_root)),
            'success': False,
            'error': str(e)
        }

def main():
    workspace_path = Path.home() / '.openclaw' / 'workspace'

    if not workspace_path.exists():
        print(f"Workspace not found: {workspace_path}")
        sys.exit(1)

    print(f"Workspace: {workspace_path}")
    print()

    # Find all files
    files = find_files_to_index(workspace_path)
    print(f"Found {len(files)} markdown/text files")

    if len(files) == 0:
        print("No files to index")
        return

    print()

    # Initialize RAG
    rag = RAG.get()

    # Index files
    indexed = []
    failed = []
    skipped = []

    for file_path in files:
        result = index_file(rag, file_path, workspace_path)

        if result is None:
            skipped.append(str(file_path.relative_to(workspace_path)))
        elif result['success']:
            indexed.append(result)
            print(f"✓ {result['file']} ({result['size']} bytes)")
        else:
            failed.append(result)
            print(f"✗ {result['file']}: {result.get('error', 'Unknown error')}")

    # Summary
    print()
    print("=" * 60)
    print("Indexing Summary:")
    print(f"  Indexed: {len(indexed)}")
    print(f"  Failed:  {len(failed)}")
    print(f"  Skipped: {len(skipped)}")

    if failed:
        print()
        print("Failed files:")
        for f in failed:
            print(f"  - {f['file']}: {f.get('error', 'Unknown error')}")

    # Get updated stats
    stats = rag.get_stats()
    print()
    print("Current RAG stats:")
    print(f"  Total documents: {stats.get('total_documents', 0)}")
    for ns, count in stats.get('namespaces', {}).items():
        print(f"  {ns}: {count}")

if __name__ == '__main__':
    main()
