# Contributing to RAG System

Thank you for your interest in contributing to the RAG Memory System! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Title**: Clear and descriptive
- **Description**: Detailed explanation of the issue
- **Steps to reproduce**: Minimal reproduction case
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**:
  - Python version
  - OS version
  - Dependencies version (`pip list`)
- **Logs**: Relevant error messages or stack traces

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- Use a clear and descriptive title
- Provide a detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- List examples or use cases if applicable
- Consider including mock-ups or code snippets

### Pull Requests

#### Before You Start

1. Check the [roadmap](roadmap/INNOVATION_ROADMAP.md) for planned features
2. Search existing pull requests to avoid duplication
3. Discuss major changes in an issue first

#### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/rag-system.git
cd rag-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-benchmark pytest-cov black flake8 mypy
```

#### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. Make your changes following the code style guidelines

3. Write tests for your changes:
   ```bash
   pytest tests/
   ```

4. Ensure all tests pass:
   ```bash
   pytest tests/ -v --cov=. --cov-report=term-missing
   ```

5. Format your code:
   ```bash
   black .
   ```

6. Run linter:
   ```bash
   flake8 .
   ```

#### Commit Guidelines

- Use clear, descriptive commit messages
- Follow conventional commits format:
  ```
  <type>(<scope>): <subject>

  <body>

  <footer>
  ```

  Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

  Examples:
  ```
  feat(caching): add LRU cache with TTL support
  fix(database): resolve WAL mode concurrency issue
  docs(readme): update installation instructions
  ```

#### Submitting Your PR

1. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request with:
   - Clear title and description
   - Reference related issues (using `#issue-number`)
   - Screenshots for UI changes
   - Description of testing performed
   - Checklist items completed

#### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] PR description clearly describes changes
- [ ] Related issues referenced

## Code Style

### Python

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Maximum line length: 100 characters

### Naming Conventions

- Classes: `PascalCase` (e.g., `QueryCache`)
- Functions/variables: `snake_case` (e.g., `search_results`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_CACHE_SIZE`)
- Private methods: `_leading_underscore`

### Documentation

- Use Google-style docstrings
- Include examples in docstrings
- Keep docstrings up to date with code

## Testing

### Writing Tests

- Write tests for all new features
- Maintain test coverage above 80%
- Use descriptive test names
- Use fixtures for common test setup

### Test Structure

```python
# tests/test_feature.py
import pytest
from rag_feature import FeatureClass

def test_feature_basic():
    """Test basic functionality."""
    feature = FeatureClass()
    assert feature.do_something() == expected

def test_feature_edge_case():
    """Test edge case."""
    feature = FeatureClass()
    with pytest.raises(ValueError):
        feature.do_invalid_operation()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_feature.py

# Run specific test
pytest tests/test_feature.py::test_feature_basic

# Run with verbose output
pytest -v
```

## Performance Guidelines

This system is performance-critical. When contributing:

- Profile your changes: `python3 rag_profiler.py`
- Ensure search latency doesn't degrade (> 10% regression is a concern)
- Cache aggressively where appropriate
- Use connection pooling for database operations
- Benchmark before and after changes

## Security Guidelines

- Never commit secrets, API keys, or credentials
- Use environment variables for configuration
- Follow secure coding practices
- Report security issues privately (not in public issues)

## Project Structure

```
rag-system/
├── rag_*.py              # Core RAG modules
├── tests/                 # Test files
├── roadmap/               # Innovation roadmap
├── docs/                 # Documentation (future)
├── .github/              # GitHub workflows
├── requirements.txt       # Python dependencies
├── README.md            # Project documentation
├── LICENSE              # MIT License
└── CONTRIBUTING.md      # This file
```

## Getting Help

- Check existing [issues](https://github.com/YOUR_USERNAME/rag-system/issues)
- Read the [documentation](README.md)
- Join community discussions (if available)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
