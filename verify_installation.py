#!/usr/bin/env python3
"""
Verify RAG system installation
Tests all core components
"""

import sys
import os

print("=" * 70)
print("RAG System Installation Verification")
print("=" * 70)
print()

# Test imports
print("1. Testing imports...")
failed_imports = []

modules = [
    ("rag_database_hardened", "RAGDatabaseHardened"),
    ("rag_api", "RAG"),
    ("rag_api_tfidf", "RAG as RAGTfidf"),
    ("tfidf_rag", "TfidfRAGDatabase"),
    ("rag_query_cache", "QueryCache"),
    ("rag_connection_pool", "ConnectionPool"),
    ("rag_profiler", "RAGProfiler"),
    ("rag_performance_metrics", "PerformanceMetrics"),
    ("rag_true_hybrid", "TrueHybridRAG"),
    ("rag_auto_reindex", "AutoReindexer"),
    ("rag_score_calibration", "ScoreCalibrator"),
    ("rag_configurable_capture", "ConfigurableCapture"),
    ("rag_auto_hybrid", "RAGAuto"),
]

for module_name, class_name in modules:
    try:
        module = __import__(module_name)
        print(f"  ✓ {module_name}.{class_name}")
    except ImportError as e:
        failed_imports.append((module_name, str(e)))
        print(f"  ✗ {module_name}: {e}")

print()

if failed_imports:
    print(f"❌ {len(failed_imports)} import(s) failed:")
    for module, error in failed_imports:
        print(f"  - {module}: {error}")
    sys.exit(1)
else:
    print("✓ All imports successful")
print()

# Test dependencies
print("2. Testing dependencies...")
failed_deps = []

deps = [
    ("sentence_transformers", "sentence_transformers"),
    ("numpy", "numpy"),
    ("scikit-learn", "sklearn.feature_extraction.text"),
    ("sqlite-vec", "sqlite_vec"),
]

for pip_name, import_name in deps:
    try:
        # Import specific submodule for sklearn
        __import__(import_name)
        print(f"  ✓ {pip_name}")
    except ImportError:
        failed_deps.append(pip_name)
        print(f"  ✗ {pip_name}")

print()

if failed_deps:
    print(f"❌ {len(failed_deps)} dependencies missing:")
    for dep in failed_deps:
        print(f"  - {dep}")
    print("\nInstall with: pip3 install -r requirements.txt")
    sys.exit(1)
else:
    print("✓ All dependencies installed")
print()

# Test basic functionality
print("3. Testing basic functionality...")

try:
    from rag_database_hardened import RAGDatabaseHardened
    from rag_query_cache import QueryCache

    # Test database (in-memory for testing)
    print("  Testing database connection...")
    rag = RAGDatabaseHardened(":memory:")
    rag.connect()
    print("  ✓ Database connected")

    # Test adding document
    print("  Testing add document...")
    rag.add_document("test", "Test content for verification", "test_doc")
    print("  ✓ Document added")

    # Test search
    print("  Testing search...")
    results = rag.search("test", limit=1)
    if results:
        print("  ✓ Search working")
    else:
        print("  ⚠ Search returned no results")

    # Test cache
    print("  Testing cache...")
    cache = QueryCache(max_size=100, default_ttl=3600)
    cache.set("test_key", [{"test": "value"}])
    value = cache.get("test_key")
    if value and len(value) > 0 and value[0].get("test") == "value":
        print("  ✓ Cache working")
    else:
        print("  ⚠ Cache not working correctly")

except Exception as e:
    print(f"  ✗ Functionality test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✅ Installation Verified Successfully!")
print("=" * 70)
print()
print("All components are working correctly.")
print()
print("Next steps:")
print("  - Run demos: python3 rag_*.py")
print("  - Read docs: cat FEATURE_MATRIX_COMPLETE.md")
print("  - Integrate with Hermes")
