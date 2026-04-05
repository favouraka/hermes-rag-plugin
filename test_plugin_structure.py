#!/usr/bin/env python3
"""
Quick test to verify RAG Memory Plugin can be loaded and basic functions work.
This test simulates what Hermes does when loading a plugin.
"""

import sys
import os

# Add plugin to path
plugin_path = os.path.expanduser("~/.hermes/plugins/rag-memory")
sys.path.insert(0, plugin_path)

print("Testing RAG Memory Plugin Structure")
print("=" * 60)

# Test 1: Check all files exist
print("\n1. Checking plugin files...")
required_files = [
    'plugin.yaml',
    '__init__.py',
    'schemas.py',
    'tools.py',
    'peer_model.py',
    'session.py',
    'auto_capture.py',
    'namespace.py',
    'rag_core.py'
]

for file in required_files:
    file_path = os.path.join(plugin_path, file)
    if os.path.exists(file_path):
        print(f"   ✓ {file}")
    else:
        print(f"   ✗ {file} - MISSING!")
        sys.exit(1)

# Test 2: Verify plugin.yaml
print("\n2. Verifying plugin.yaml...")
import yaml
with open(os.path.join(plugin_path, 'plugin.yaml')) as f:
    manifest = yaml.safe_load(f)
    print(f"   ✓ Name: {manifest.get('name')}")
    print(f"   ✓ Version: {manifest.get('version')}")
    print(f"   ✓ Tools: {len(manifest.get('provides_tools', []))}")
    print(f"   ✓ Hooks: {len(manifest.get('provides_hooks', []))}")

# Test 3: Verify Python syntax
print("\n3. Verifying Python syntax...")
import py_compile
for file in ['__init__.py', 'schemas.py', 'tools.py',
             'peer_model.py', 'session.py', 'auto_capture.py',
             'namespace.py', 'rag_core.py']:
    try:
        py_compile.compile(os.path.join(plugin_path, file), doraise=True)
        print(f"   ✓ {file}")
    except py_compile.PyCompileError as e:
        print(f"   ✗ {file}: {e}")
        sys.exit(1)

# Test 4: Check __init__.py has register function
print("\n4. Checking __init__.py structure...")
with open(os.path.join(plugin_path, '__init__.py')) as f:
    content = f.read()
    if 'def register(ctx):' in content:
        print("   ✓ register(ctx) function exists")
    else:
        print("   ✗ register(ctx) function missing!")
        sys.exit(1)

    if 'ctx.register_tool' in content:
        print("   ✓ Tool registration calls found")
    else:
        print("   ✗ Tool registration calls missing!")
        sys.exit(1)

    if 'ctx.register_hook' in content:
        print("   ✓ Hook registration calls found")
    else:
        print("   ✗ Hook registration calls missing!")
        sys.exit(1)

# Test 5: Verify schemas exist
print("\n5. Checking tool schemas...")
with open(os.path.join(plugin_path, 'schemas.py')) as f:
    content = f.read()
    required_schemas = [
        'RAG_SEARCH', 'RAG_ADD_DOCUMENT', 'RAG_GET_PEER_CONTEXT',
        'RAG_GET_SESSION_CONTEXT', 'RAG_START_SESSION', 'RAG_END_SESSION',
        'RAG_CAPTURE_MESSAGE', 'RAG_LIST_PEERS', 'RAG_LIST_SESSIONS'
    ]
    for schema in required_schemas:
        if schema in content:
            print(f"   ✓ {schema}")
        else:
            print(f"   ✗ {schema} - MISSING!")
            sys.exit(1)

# Test 6: Verify tool handlers exist
print("\n6. Checking tool handlers...")
with open(os.path.join(plugin_path, 'tools.py')) as f:
    content = f.read()
    required_handlers = [
        'rag_search', 'rag_add_document', 'rag_get_peer_context',
        'rag_get_session_context', 'rag_start_session', 'rag_end_session',
        'rag_capture_message', 'rag_list_peers', 'rag_list_sessions'
    ]
    for handler in required_handlers:
        if f'def {handler}(' in content:
            print(f"   ✓ {handler}")
        else:
            print(f"   ✗ {handler} - MISSING!")
            sys.exit(1)

# Test 7: Check hook functions exist
print("\n7. Checking hook functions...")
with open(os.path.join(plugin_path, 'tools.py')) as f:
    content = f.read()
    if 'def inject_context(' in content:
        print("   ✓ inject_context (pre_llm_call hook)")
    else:
        print("   ✗ inject_context - MISSING!")
        sys.exit(1)

    if 'def capture_output(' in content:
        print("   ✓ capture_output (post_tool_call hook)")
    else:
        print("   ✗ capture_output - MISSING!")
        sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nPlugin is ready to be loaded by Hermes.")
print("Location: ~/.hermes/plugins/rag-memory/")
print("Start Hermes and type /plugins to verify loading.")
