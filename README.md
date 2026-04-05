# RAG Memory Plugin for Hermes Agent

Production-grade RAG (Retrieval-Augmented Generation) memory system for Hermes Agent with peer/session tracking and namespace isolation.

## Features

- **Hybrid Retrieval**: TF-IDF + Neural search for optimal performance
- **Peer/Session Tracking**: Multi-party conversation management
- **Namespace Isolation**: Scoped searches per peer, session, or global
- **Auto-Capture**: Automatic message capture and storage
- **Context Injection**: Pre-LLM hook for relevant context injection
- **Production Ready**: SQLite hardening, connection pooling, error handling

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Plugin is located at:
~/.hermes/plugins/rag-memory/src/

# Hermes will automatically load it on startup
```

## Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md) - Detailed setup instructions
- [Quick Start](docs/QUICKSTART.md) - Get started in 5 minutes
- [API Documentation](docs/) - Complete API reference
- [Contributing](docs/CONTRIBUTING.md) - How to contribute

## Project Structure

```
.
├── src/              # Plugin source code (loaded by Hermes)
│   ├── models/       # Peer & Session models
│   ├── core/         # RAG core, namespace, auto-capture
│   └── tools/        # Schemas & handlers
├── tests/            # Test suite
├── scripts/          # Utility scripts
├── docs/             # Documentation
├── roadmap/          # Roadmap files
└── .github/          # GitHub workflows
```

## Running Tests

```bash
cd ~/.hermes/plugins/rag-memory
python3 -m pytest tests/ -v
```

Or run individual test files:
```bash
python3 tests/test_peer_model.py
python3 tests/test_session.py
python3 tests/test_auto_capture_peer.py
python3 tests/test_namespace_isolation.py
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Roadmap

See [roadmap/](roadmap/) directory for upcoming features.
