# GitHub Setup Instructions

This file provides step-by-step instructions for pushing the RAG system to GitHub.

## Prerequisites

- GitHub account
- Git configured locally (username, email)
- SSH key set up (recommended) or HTTPS authentication token

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Fill in repository details:
   - **Repository name**: `rag-system` (or your preferred name)
   - **Description**: "Production-grade RAG memory system with performance optimization"
   - **Visibility**: Public (recommended for open source)
   - **Initialize**: Leave all checkboxes unchecked (we'll push existing code)

3. Click **Create repository**

## Step 2: Push to GitHub

### Option A: Using SSH (Recommended)

```bash
cd ~/rag-system

# Add remote repository (replace YOUR_USERNAME)
git remote add origin git@github.com:YOUR_USERNAME/rag-system.git

# Push to GitHub
git push -u origin main
```

### Option B: Using HTTPS

```bash
cd ~/rag-system

# Add remote repository (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/rag-system.git

# Push to GitHub (will prompt for credentials)
git push -u origin main
```

## Step 3: Verify Deployment

1. Visit your repository URL: `https://github.com/YOUR_USERNAME/rag-system`
2. Verify all files are present:
   - ✅ README.md
   - ✅ LICENSE
   - ✅ CHANGELOG.md
   - ✅ CONTRIBUTING.md
   - ✅ requirements.txt
   - ✅ .github/workflows/ (3 workflow files)
   - ✅ roadmap/INNOVATION_ROADMAP.md
   - ✅ All `rag_*.py` files

## Step 4: Configure GitHub Settings

### Enable GitHub Actions

1. Go to **Settings** → **Actions** → **General**
2. Under **Actions permissions**, select:
   - ✅ Allow all actions and reusable workflows
3. Click **Save**

### Enable Security Features

1. Go to **Settings** → **Security** → **Code security and analysis**
2. Enable:
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Code scanning (CodeQL) - optional but recommended
3. Click **Save**

### Enable Branch Protection (Recommended)

1. Go to **Settings** → **Branches**
2. Click **Add branch protection rule**
3. Set **Branch name pattern**: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
5. Select required checks:
   - ✅ Nightly Security Scan
   - ✅ Nightly Performance Tests
6. Click **Create**

## Step 5: Test GitHub Actions

### Manually Trigger Workflows

1. Go to **Actions** tab in your repository
2. Select a workflow:
   - **Nightly Security Scan**
   - **Nightly Performance Tests**
   - **Weekly Dependency Updates**
3. Click **Run workflow** button (top right)
4. Select branch: `main`
5. Click **Run workflow**

### Verify Workflow Results

1. Wait for workflows to complete (2-3 minutes)
2. Click on each workflow run to view:
   - Security scan results
   - Performance benchmarks
   - Dependency reports
3. Check **Summary** tab for generated reports

## Step 6: Create Initial Release

1. Go to **Releases** → **Create a new release**
2. Fill in:
   - **Tag version**: `v1.0.0`
   - **Release title**: `v1.0.0 - Production-Grade RAG Memory System`
   - **Description**:
     ```
     ## Initial Release

     Production-grade RAG memory system with comprehensive hardening and performance optimization.

     ### Features
     - Phase 1: Infrastructure Hardening (WAL mode, file locks, auto-backups)
     - Phase 2: Plugin Integration (hooks, tools, auto-capture)
     - Phase 3: Performance Optimization (caching, batch, async)
     - Phase 4: Performance Features (connection pooling, profiling, metrics)

     ### Performance
     - Cached search: 150ms → < 1ms (150x faster)
     - 3 parallel queries: 450ms → 50ms (9x faster)
     - 3 cached queries: 450ms → < 1ms (450x faster)

     ### Security
     - Resolved 6 critical vulnerabilities (-100%)
     - Resolved 4 high-risk issues (-100%)

     See [CHANGELOG.md](https://github.com/YOUR_USERNAME/rag-system/blob/main/CHANGELOG.md) for details.
     ```
3. Click **Publish release**

## Step 7: Add Badges to README

Update the badges in README.md with your repository URL:

```markdown
[![GitHub Actions](https://github.com/YOUR_USERNAME/rag-system/actions/workflows/security-nightly.yml/badge.svg)](https://github.com/YOUR_USERNAME/rag-system/actions)
```

Commit and push:

```bash
git add README.md
git commit -m "docs: update badges with repository URL"
git push
```

## Step 8: Create PyPI Package (Optional)

To publish to PyPI for easy installation:

```bash
# Install build tools
pip install build twine

# Build package
cd ~/rag-system
python -m build

# Upload to PyPI
twine upload dist/*
```

## Step 9: Set Up Automation

### Dependabot for Dependencies

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
```

### Issue Templates

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment**
- Python version: [e.g. 3.11]
- OS: [e.g. Ubuntu 22.04]
- RAG version: [e.g. 1.0.0]

**Additional context**
Add any other context about the problem here.
```

## Maintenance Tasks

### Daily (Automated)

- ✅ Nightly security scan (2 AM UTC)
- ✅ Nightly performance test (3 AM UTC)

### Weekly (Automated)

- ✅ Dependency updates (6 AM UTC, Monday)

### Manual

- Review and merge dependency PRs
- Check performance regression reports
- Monitor security alerts
- Respond to issues and PRs
- Update roadmap based on feedback

## Troubleshooting

### Push Fails with "Permission Denied"

**SSH:**
```bash
# Check SSH key
ssh -T git@github.com

# If fails, set up SSH key:
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub  # Add to GitHub SSH keys
```

**HTTPS:**
```bash
# Use personal access token
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/rag-system.git
```

### Workflows Fail

1. Check **Actions** tab for error logs
2. Verify Python version is 3.9+
3. Ensure dependencies install correctly
4. Check for missing files (especially requirements.txt)

### Branch Protection Blocks Push

```bash
# Create new branch for changes
git checkout -b feature/my-change
# Make changes
git push origin feature/my-change
# Create PR in GitHub UI
```

## Next Steps

1. ✅ Repository created and code pushed
2. ✅ GitHub Actions verified
3. ✅ v1.0.0 release published
4. 🔄 Implement features from [INNOVATION_ROADMAP.md](roadmap/INNOVATION_ROADMAP.md)
5. 🔄 Build community engagement
6. 🔄 Monitor metrics and performance

---

**Repository:** https://github.com/YOUR_USERNAME/rag-system
**License:** MIT
**Version:** 1.0.0
