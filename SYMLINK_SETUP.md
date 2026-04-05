# Symlink Setup - Plugin Directory Structure

## Setup

Instead of git worktree (which conflicted), created a symlink for simplicity.

## Directory Structure

```
~/.hermes/plugins/rag-memory/  →  ~/rag-system-phase1/
     (symlink)                      (actual git repo)
```

### Symlink Details

```bash
~/.hermes/plugins/rag-memory -> /home/aka/rag-system-phase1
```

## How It Works

1. **Hermes loads from:** `~/.hermes/plugins/rag-memory/`
2. **But this is a symlink to:** `~/rag-system-phase1/`
3. **All changes in either directory are the same file**

## Benefits

- ✅ No duplication (single source of truth)
- ✅ Git repo accessible in familiar location
- ✅ Plugin loads from correct path
- ✅ Changes sync automatically (same files)
- ✅ Simple and clean

## Git Worktrees

Current worktrees:
```bash
~/rag-system         [main]
~/rag-system-phase1 [feature/hermes-plugin-integration]
```

`~/rag-system-phase1` is the active worktree with the plugin code.

## Updating Plugin

Make changes in either directory:

```bash
# Via symlink (Hermes location)
cd ~/.hermes/plugins/rag-memory/
# Make changes...

# Via git repo (development location)
cd ~/rag-system-phase1
# Make changes...
```

Both are the same files!

## Verification

```bash
# Check symlink
ls -lh ~/.hermes/plugins/ | grep rag-memory
# Output: rag-memory -> /home/aka/rag-system-phase1

# Test imports
cd ~/.hermes/plugins/rag-memory
python3 -c "
from peer_model import Peer, PeerManager
from session import Session, SessionManager
from auto_capture import AutoPeerCapture
from namespace import NamespaceIsolation
from rag_core import RAGCore
print('✓ Symlink working')
"
```

## Git Workflow

1. Make changes in `~/rag-system-phase1`
2. Commit and push
3. Hermes sees changes automatically (symlink points to same files)

## Clean Up

If you ever want to remove the symlink:

```bash
rm ~/.hermes/plugins/rag-memory
```

(Does NOT delete the git repo, just the symlink)

## Summary

**One repo, two names:**
- `~/rag-system-phase1` = Git repo (development)
- `~/.hermes/plugins/rag-memory/` = Symlink (Hermes loads here)

Both point to the same files. Changes in one are changes in both.
