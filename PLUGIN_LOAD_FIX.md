# Plugin Load Fix - Import Issues Resolved

## Issue

When loading the plugin with Hermes, got error:
```
Failed to load plugin 'rag-memory': No module named 'rag_peer_model'
```

## Root Cause

The migrated files (`auto_capture.py` and `session.py`) still referenced old module names:
- `rag_peer_model` → should be `peer_model`
- `rag_session` → should be `session`

## Fix Applied

Updated all imports in the plugin files:

### auto_capture.py
```python
# Before:
from rag_peer_model import Peer, PeerManager
from rag_session import Session, SessionManager
# Later:
from rag_session import SessionContext

# After:
from peer_model import Peer, PeerManager
from session import Session, SessionManager
# Later:
from session import SessionContext
```

### session.py
```python
# Before:
from rag_peer_model import Peer, PeerManager

# After:
from peer_model import Peer, PeerManager
```

## Verification

```bash
cd ~/.hermes/plugins/rag-memory
python3 -c "
import sys
sys.path.insert(0, '.')
from peer_model import Peer, PeerManager
from session import Session, SessionManager
from auto_capture import AutoPeerCapture
from namespace import NamespaceIsolation
from rag_core import RAGCore
print('✓ All modules imported successfully')
"
```

Output:
```
✓ All modules imported successfully
✓ Plugin should now load with Hermes
```

## Commit

Commit: `c22975b` - Fix imports in migrated files
Branch: `feature/hermes-plugin-integration`
Pushed to remote ✓

## Testing

Plugin should now load correctly:

```bash
hermes
/plugins
```

Expected output:
```
Plugins (1): rag-memory v2.0.0 (9 tools, 2 hooks)
```

## Files Updated

- `~/.hermes/plugins/rag-memory/auto_capture.py` ✓
- `~/.hermes/plugins/rag-memory/session.py` ✓
- `~/rag-system-phase1/auto_capture.py` ✓
- `~/rag-system-phase1/session.py` ✓

All imports now use correct module names.
