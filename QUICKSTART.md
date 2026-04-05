# Auto-RAG Quickstart Guide

## What's Ready

✅ **Fully automated RAG system** with:
- 71 documents indexed (sessions, facts, projects, skills)
- Auto-capture of conversations
- Auto-retrieval of context
- Auto-sync every 2 hours
- Tool usage tracking

## How It Works (80/15/5 Hybrid)

### 80% Automatic (No code needed)
- Every message buffered automatically
- Every 5 messages → auto-flush to database
- New sessions synced every 2 hours (cron job)
- Duplicates skipped automatically

### 15% Semi-Auto (Simple function calls)
- `auto_retrieve_context()` - Get context before responding
- `auto_capture_message()` - Capture messages
- `auto_track_tool()` - Track tool usage
- `auto_flush()` - Flush buffer

### 5% Manual (Important events only)
- `capture_decision()` - Explicit decisions
- `capture_correction()` - User corrections
- `capture_important()` - Critical information

## Quick Start

### 1. Import (First thing in any conversation)
```python
import sys
sys.path.insert(0, '/home/aka/rag-system')
from rag_auto import (
    auto_retrieve_context,
    auto_capture_message,
    auto_flush,
    get_rag_auto
)
```

### 2. Before Responding (Get Context)
```python
# User just asked something
context = auto_retrieve_context(
    query=user_message,
    limit=5,
    namespaces=['facts', 'sessions']
)

# Use context to inform your response
facts = context['results'].get('facts', [])
```

### 3. During Conversation (Capture Messages)
```python
# Capture user message
auto_capture_message('user', user_message)

# Capture your response
auto_capture_message('assistant', your_response)
```

### 4. On Decisions (Capture Important Events)
```python
rag_auto = get_rag_auto()

# Capture decisions
rag_auto.capture_decision(
    decision='Use MariaDB for new project',
    reason='User agreed with recommendation',
    metadata={'importance': 'high'}
)

# Capture corrections
rag_auto.capture_correction(
    correction='User prefers NGN format for BTC price',
    old_fact='BTC price in USD'
)

# Capture task completion
rag_auto.capture_task_completion(
    task='Set up Adminer',
    outcome='Deployed on http://100.110.80.75:5056'
)
```

### 5. After Tools (Track Usage)
```python
from rag_auto import auto_track_tool

auto_track_tool('terminal', success=True, metadata={'command': 'apt install'})
auto_track_tool('incus', success=False, metadata={'error': 'timeout'})
```

### 6. End of Conversation (Flush)
```python
auto_flush()  # Save conversation to database
```

## Testing

### Run Demo
```bash
cd ~/rag-system && python3 demo_auto_rag.py
```

### Run Tests
```bash
cd ~/rag-system && python3 test_auto.py
```

### Check Stats
```bash
cd ~/rag-system && python3 sync_sessions.py --stats
```

## Manual Operations

### Sync New Sessions
```bash
cd ~/rag-system && python3 sync_sessions.py --limit 10
```

### Full Sync All Sessions
```bash
cd ~/rag-system && python3 sync_sessions.py --full
```

### Search Database
```bash
cd ~/rag-system && python3 rag_query.py "search query"
cd ~/rag-system && python3 rag_query.py "BTC price" --namespace facts
cd ~/rag-system && python3 rag_query.py --stats
```

## Database Location

```
~/rag-system/
├── rag_data.db              # SQLite database (15MB)
├── models/
│   └── all-MiniLM-L6-v2/   # Embedding model (80MB)
├── rag_auto.py             # Auto-capture system ⭐
├── sync_sessions.py        # Background sync
├── rag_query.py            # CLI search
└── demo_auto_rag.py        # Demo script
```

## Current Stats

```
Total Documents: 71
├── Sessions: 43 (conversations)
├── Facts: 16 (decisions, preferences, corrections)
├── Projects: 9 (documentation)
└── Tools/Skills: 3 (skill definitions)

Tool Uses Tracked: 6
```

## Skill Available

The system is saved as a skill for future sessions:
```bash
skill_view(name="rag-auto-capture")
```

## Cron Job

Auto-sync runs every 2 hours (Job ID: 23628994e317)

## Performance

- Query: ~0.5-1s (CPU)
- Memory: ~200MB
- Database: 15MB (71 docs)

## What's Next?

**Immediate:**
1. Test: `python3 demo_auto_rag.py`
2. Check stats: `python3 sync_sessions.py --stats`
3. Read guide: `cat AUTO_RAG_GUIDE.md`

**Ongoing:**
1. Before responding → `auto_retrieve_context()`
2. During chat → `auto_capture_message()`
3. On decisions → `capture_decision()`
4. On corrections → `capture_correction()`
5. After tools → `auto_track_tool()`
6. End of convo → `auto_flush()`

## Example: Full Conversation Flow

```python
# 1. Import
import sys
sys.path.insert(0, '/home/aka/rag-system')
from rag_auto import auto_retrieve_context, auto_capture_message, auto_flush, get_rag_auto

# 2. User asks: "What database should I use?"
user_message = "What database should I use for the new project?"

# 3. Get context
context = auto_retrieve_context(user_message, limit=5)

# 4. Capture user message
auto_capture_message('user', user_message)

# 5. Generate response using context
response = "Based on your preferences, I'd recommend MariaDB..."

# 6. Capture assistant response
auto_capture_message('assistant', response)

# 7. User confirms: "Great, let's go with MariaDB"
user_decision = "Great, let's go with MariaDB"

# 8. Capture user decision
auto_capture_message('user', user_decision)
rag_auto = get_rag_auto()
rag_auto.capture_decision(
    decision='Use MariaDB for new project',
    reason='User agreed with recommendation'
)

# 9. Flush buffer
auto_flush()
```

---

**That's it!** The system does the heavy lifting. Just add a few function calls and it's automatic.

**Questions?** Check `AUTO_RAG_GUIDE.md` for detailed documentation.
