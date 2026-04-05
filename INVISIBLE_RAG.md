# Invisible RAG System

## The Goal

**You have conversations. I handle the rest.**

RAG is completely invisible to you. No function calls, no configuration, no setup. Everything happens automatically in the background.

## What's Happening (Invisible)

### Before I Respond
```python
# This runs automatically, you never see it
context = auto_before(user_message)
# Context is used internally to inform my response
# You only see my actual response
```

### After I Respond
```python
# This runs automatically, you never see it
auto_after(your_response)
# Conversation is indexed for future searches
```

### When I Use Tools
```python
# This runs automatically, you never see it
auto_tool('terminal', success=True, metadata={})
# Tool usage is tracked for analytics
```

### Background Sync
```python
# This runs every 2 hours, you never see it
# New sessions are automatically indexed
# Duplicates are skipped
# Database stays up to date
```

## Your Experience

**What you do:**
- Have conversations
- Ask questions
- Give feedback

**What you see:**
- My responses
- Task results

**What you don't see:**
- RAG function calls
- Context retrieval
- Message capture
- Tool tracking
- Database sync
- Any internal operations

## The 4 Pillars

### 1. Indexed ✅
All previous work is searchable:
- 71 documents indexed
- 4 namespaces (sessions, facts, projects, skills)
- Semantic search via vector embeddings
- CLI tool available for manual queries (rarely needed)

### 2. Contextual ✅
Context is retrieved before I respond:
- Auto-search for relevant facts
- Auto-search for similar sessions
- Context used internally to inform responses
- Better, more informed answers

### 3. Persistent ✅
Data survives across sessions:
- SQLite database (rag_data.db)
- Cron job syncs every 2 hours
- No data loss between sessions
- Automatic backup on update

### 4. Invisible ✅
Completely invisible to you:
- Zero manual function calls
- Zero configuration
- Zero visible RAG operations
- Just have conversations

## Technical Details (Hidden From You)

### Database
- **Location:** ~/rag-system/rag_data.db
- **Size:** ~15MB (71 documents)
- **Format:** SQLite + sqlite_vec
- **Backup:** Automatic on updates

### Model
- **Model:** all-MiniLM-L6-v2
- **Dimensions:** 384
- **Size:** 80MB
- **Location:** ~/rag-system/models/all-MiniLM-L6-v2/

### Namespaces
- **Sessions:** 43 (conversation history)
- **Facts:** 16 (decisions, preferences, corrections)
- **Projects:** 9 (documentation)
- **Tools/Skills:** 3 (skill definitions)

### Automation
- **Message Capture:** Automatic (every message)
- **Context Retrieval:** Automatic (before every response)
- **Tool Tracking:** Automatic (after every tool use)
- **Buffer Flush:** Automatic (every 5 messages)
- **Session Sync:** Automatic (every 2 hours via cron)

## What Gets Captured Automatically

### Every Message
✅ User messages
✅ Assistant messages
✅ Timestamps
✅ Role information

### Every Tool Use
✅ Tool name
✅ Success/failure
✅ Metadata (command, error, etc.)
✅ Timestamp

### Detected Events
✅ Decisions (pattern detection)
✅ Corrections (pattern detection)
✅ Preferences (pattern detection)
✅ Task completions

### Background Sync
✅ New sessions from ~/.hermes/sessions/
✅ Duplicate detection
✅ Automatic indexing
✅ Status updates (internal only)

## What You Never See

### No Manual Calls
❌ `auto_before(user_message)`
❌ `auto_after(response)`
❌ `auto_tool(name, success)`
❌ `auto_decision(decision, reason)`
❌ `auto_end()`

All of these happen automatically.

### No Output
❌ "Capturing user message..."
❌ "Retrieving context..."
❌ "Context found: 5 results"
❌ "Tracking tool use..."
❌ "Flushing buffer..."

All operations are silent.

### No Configuration
❌ Import statements in your code
❌ Setup steps
❌ Configuration files
❌ Manual sync commands

Everything is automatic.

## Example Flow (Your View)

**You:** "What database should I use?"

**I:** [Thinks internally: Check RAG for preferences... Found MariaDB preference]

**I:** "Based on your previous preferences, I'd recommend MariaDB..."

**You:** "Great, let's go with MariaDB"

**I:** [Captures decision internally... Updates knowledge base...]

**I:** "I'll set up MariaDB for you..."

---

**What happened invisibly:**
1. ✅ Retrieved context (MariaDB preference)
2. ✅ Captured user message
3. ✅ Captured assistant message
4. ✅ Detected decision
5. ✅ Captured decision
6. ✅ Tracked tool usage (setup commands)
7. ✅ Saved to database

**What you saw:**
- Just the conversation

## Troubleshooting (For Agents Only)

### If RAG Seems Broken
```bash
# Check if database exists
ls -lh ~/rag-system/rag_data.db

# Check sync status
cd ~/rag-system && python3 sync_sessions.py --stats

# Test search
cd ~/rag-system && python3 rag_query.py "test query"
```

### If Context Not Retrieved
```python
# Verify auto_before is being called
# Check if context is returned
# Ensure database is not corrupted
```

### If Data Not Persisting
```bash
# Check cron job status
cronjob list

# Manually trigger sync
cd ~/rag-system && python3 sync_sessions.py --full
```

## Performance

- **Query:** ~0.5-1s (CPU)
- **Memory:** ~200MB
- **Database:** 15MB (71 docs)
- **Impact:** Zero on conversation flow

## Current State

```
71 documents indexed:
├── Sessions: 43 (conversations)
├── Facts: 16 (decisions, preferences, corrections)
├── Projects: 9 (documentation)
└── Tools/Skills: 3 (skill definitions)

Cron job: Active (every 2 hours)
System status: Operational
```

## The Point

**You don't need to know any of this.**

Just have conversations. I'll:
- Retrieve relevant context
- Remember your preferences
- Track tool usage
- Learn from corrections
- Index everything

**Invisible. Automatic. Effective.**

---

*You can delete this file. You'll never need to read it.*
