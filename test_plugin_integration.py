#!/usr/bin/env python3
"""
Integration test for RAG Memory Plugin.
Tests the full registration flow and tool functionality.
"""

import sys
import os
import tempfile
import sqlite3
import importlib.util

# Add plugin to path
plugin_path = os.path.expanduser("~/.hermes/plugins/rag-memory")
sys.path.insert(0, plugin_path)

print("RAG Memory Plugin Integration Test")
print("=" * 60)

# Load plugin directly
spec = importlib.util.spec_from_file_location("rag_memory", os.path.join(plugin_path, "__init__.py"))
rag_memory = importlib.util.module_from_spec(spec)

# Load dependencies first
for module_name in ['peer_model', 'session', 'auto_capture', 'namespace', 'rag_core', 'schemas', 'tools']:
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(plugin_path, f"{module_name}.py")
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)

# Load __init__.py
spec.loader.exec_module(rag_memory)

# Mock context object (simulates Hermes context)
class MockContext:
    def __init__(self):
        self.tools = []
        self.hooks = []

    def register_tool(self, name, schema, handler):
        print(f"   ✓ Registered tool: {name}")
        self.tools.append({'name': name, 'schema': schema, 'handler': handler})

    def register_hook(self, hook_name, callback):
        print(f"   ✓ Registered hook: {hook_name}")
        self.hooks.append({'name': hook_name, 'callback': callback})

# Test 1: Import plugin
print("\n1. Importing plugin...")
print("   ✓ Plugin imported successfully")

# Test 2: Call register() function
print("\n2. Testing plugin registration...")
try:
    ctx = MockContext()
    rag_memory.register(ctx)

    print(f"\n   Registered {len(ctx.tools)} tools")
    print(f"   Registered {len(ctx.hooks)} hooks")

    # Verify tools
    expected_tools = [
        'rag_search', 'rag_add_document', 'rag_get_peer_context',
        'rag_get_session_context', 'rag_start_session', 'rag_end_session',
        'rag_capture_message', 'rag_list_peers', 'rag_list_sessions'
    ]

    tool_names = [t['name'] for t in ctx.tools]
    for tool in expected_tools:
        if tool in tool_names:
            print(f"   ✓ {tool}")
        else:
            print(f"   ✗ {tool} - NOT REGISTERED!")
            sys.exit(1)

    # Verify hooks
    hook_names = [h['name'] for h in ctx.hooks]
    if 'pre_llm_call' in hook_names:
        print(f"   ✓ pre_llm_call hook")
    else:
        print(f"   ✗ pre_llm_call hook - NOT REGISTERED!")
        sys.exit(1)

    if 'post_tool_call' in hook_names:
        print(f"   ✓ post_tool_call hook")
    else:
        print(f"   ✗ post_tool_call hook - NOT REGISTERED!")
        sys.exit(1)

except Exception as e:
    print(f"   ✗ Registration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test tool handlers
print("\n3. Testing tool handlers...")
try:
    # Get managers
    peer_manager = rag_memory.get_peer_manager()
    session_manager = rag_memory.get_session_manager()
    auto_capture = rag_memory.get_auto_capture()
    isolation = rag_memory.get_isolation()
    rag_core = rag_memory.get_rag_core()

    print(f"   ✓ Peer manager initialized")
    print(f"   ✓ Session manager initialized")
    print(f"   ✓ Auto capture initialized")
    print(f"   ✓ Namespace isolation initialized")
    print(f"   ✓ RAG core initialized")

    # Test: Start session
    print("\n   Testing session management...")
    session = auto_capture.start_session(
        session_id="test-session",
        peer_ids=["test-user", "assistant"]
    )
    print(f"   ✓ Started session: {session.session_id}")

    # Test: Capture message
    print("\n   Testing message capture...")
    result = auto_capture.capture_message(
        peer_id="test-user",
        role="user",
        content="Hello, this is a test message"
    )
    print(f"   ✓ Captured message from: {result.get('peer_id')}")

    # Test: Get peer context
    print("\n   Testing peer context...")
    peer = peer_manager.get_peer("test-user")
    context = peer.get_context(tokens=100)
    print(f"   ✓ Got peer context: {len(context)} chars")

    # Test: Get session context
    print("\n   Testing session context...")
    session_context = auto_capture.get_session_context("test-session")
    print(f"   ✓ Got session context: {len(session_context.messages)} messages")

    # Test: Add document to RAG
    print("\n   Testing RAG add document...")
    doc_result = rag_core.add_document(
        content="Test document for RAG",
        namespace="test"
    )
    print(f"   ✓ Added document: {doc_result.get('id')}")

    # Test: Search RAG
    print("\n   Testing RAG search...")
    search_results = rag_core.search(
        query="test document",
        namespace="test",
        limit=5
    )
    print(f"   ✓ Found {len(search_results)} results")

    # Test: List peers
    print("\n   Testing list peers...")
    peers = auto_capture.list_peers()
    print(f"   ✓ Listed {len(peers)} peers")

    # Test: List sessions
    print("\n   Testing list sessions...")
    sessions = auto_capture.list_sessions()
    print(f"   ✓ Listed {len(sessions)} sessions")

except Exception as e:
    print(f"   ✗ Handler test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test hooks
print("\n4. Testing hooks...")
try:
    # Get hook callbacks
    pre_llm_hook = None
    post_tool_hook = None

    for hook in ctx.hooks:
        if hook['name'] == 'pre_llm_call':
            pre_llm_hook = hook['callback']
        elif hook['name'] == 'post_tool_call':
            post_tool_hook = hook['callback']

    if pre_llm_hook:
        # Test pre_llm_call hook
        print("\n   Testing pre_llm_call hook...")
        result = pre_llm_hook(ctx)
        print(f"   ✓ pre_llm_call executed, returned: {type(result)}")
    else:
        print("   ✗ pre_llm_call hook not found")
        sys.exit(1)

    if post_tool_hook:
        # Test post_tool_call hook
        print("\n   Testing post_tool_call hook...")
        result = post_tool_hook(ctx, "test_tool", {}, "test_result")
        print(f"   ✓ post_tool_call executed")
    else:
        print("   ✗ post_tool_call hook not found")
        sys.exit(1)

except Exception as e:
    print(f"   ✗ Hook test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Cleanup
print("\n5. Testing cleanup...")
try:
    auto_capture.end_session("test-session")
    print("   ✓ Session ended")

    rag_memory.cleanup()
    print("   ✓ Plugin cleaned up")

except Exception as e:
    print(f"   ✗ Cleanup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL INTEGRATION TESTS PASSED!")
print("=" * 60)
print("\nPlugin is fully functional and ready for Hermes.")
print("\nTo test with Hermes:")
print("  1. Start Hermes")
print("  2. Type /plugins")
print("  3. Should see: rag-memory v2.0.0 (9 tools, 2 hooks)")
print("\nTo test tools:")
print("  1. Ask: 'Search RAG for test'")
print("  2. Ask: 'Start a session with alice and bob'")
print("  3. Ask: 'List all peers'")
