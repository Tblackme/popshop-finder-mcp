# Pattern-GIT-002: Git Submodule Architecture for Public/Private Repos

**Category:** Git Workflow & Repository Management
**Status:** Active
**Created:** 2025-11-09
**Last Updated:** 2025-11-09
**Related Incident:** REPO_LEAK_2025-11-09

---

## Context

When building products with public open-source components and private commercial components, proper repository architecture is critical for security. A single mistake can expose proprietary code, API keys, or business logic to the public.

**Real-World Impact:** The 2025-11-09 incident exposed 58 files (17k+ lines) of private API code to the public repository, requiring a 2-hour emergency cleanup with BFG Repo-Cleaner.

---

## Problem

### Common Mistake

Developers may accidentally commit private code to public repositories when:
- Repository architecture isn't clearly documented
- Team members don't understand public/private boundaries
- Directory structure makes it easy to confuse which code goes where
- No automated checks prevent sensitive commits

### Consequences

**If private code leaks into public repo:**
- ❌ API implementations exposed (business logic visible to competitors)
- ❌ Database schemas revealed (security through obscurity lost)
- ❌ Potential key/secret exposure (if .gitignore fails)
- ❌ History rewrite required (2+ hour emergency response)
- ❌ All team members must re-clone (workflow disruption)

---

## Solution: Git Submodules

Use git submodules to safely reference private repositories from public repositories.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Public Repository (github.com/org/public-repo)              │
│                                                               │
│ ├── src/                    ✅ Public code                   │
│ ├── docs/                   ✅ Public documentation          │
│ ├── tests/                  ✅ Public tests                  │
│ └── private-integration/    🔗 Git submodule                 │
│     └── (points to private repo commit SHA)                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                             │
                             │ git submodule reference
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Private Repository (github.com/org/private-repo)            │
│                                                               │
│ ├── api/                    🔒 Private API routes            │
│ ├── config/                 🔒 API keys, secrets             │
│ ├── business-logic/         🔒 Proprietary algorithms        │
│ └── integration-docs/       📖 Exposed via submodule         │
│     └── .integration/       ✅ Safe to reference publicly    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### How It Works

**Submodule Pointer:**
- Public repo contains `.gitmodules` file
- References specific **commit SHA** of private repo (not branch)
- Only the commit SHA is visible in public repo
- Private repo content stays private

**Access Control:**
- Users with access to both repos → Can initialize submodule
- Users with only public repo access → See submodule reference, can't access content
- Private repo permissions enforced by GitHub

---

## When to Use Submodules

### ✅ Use Submodules When:

1. **Private commercial code referenced from public repo**
   - Example: Open-source CLI tool that needs enterprise features
   - Public: CLI framework, docs, tests
   - Private: Enterprise features, licensing, analytics

2. **Integration documentation needs to bridge repos**
   - Example: ÆtherLight public extensions + private website dashboard
   - Public: VS Code extension, desktop app
   - Private: Website dashboard, API keys
   - Submodule: Integration docs for coordinating releases

3. **Read-only access to subset of private repo**
   - Example: Shared configuration or schemas
   - Public repo needs to read schemas from private repo
   - Submodule exposes only `/schemas/` directory

4. **Version pinning required**
   - Submodule references specific commit SHA
   - Public repo won't break if private repo changes
   - Explicit updates required (controlled dependency)

### ❌ Do NOT Use Submodules When:

1. **Small helper utilities**
   - Solution: Copy the utility code to public repo (with license)
   - Submodules add complexity for small code sharing

2. **Public dependencies**
   - Solution: Use package managers (npm, pip, cargo, etc.)
   - Submodules are NOT a replacement for package management

3. **Temporary integrations**
   - Solution: Use build scripts or CI/CD workflows
   - Submodules are permanent architectural choices

4. **Frequent bidirectional changes**
   - Problem: Submodules make this workflow painful
   - Solution: Consider monorepo or proper package separation

---

## Implementation Guide

### Step 1: Repository Setup

**Create Repositories:**
```bash
# Create public repository
gh repo create org/public-repo --public

# Create private repository
gh repo create org/private-repo --private
```

**Initialize Public Repo:**
```bash
mkdir public-repo && cd public-repo
git init
echo "# Public Project" > README.md
git add README.md
git commit -m "init: Initial commit"
git remote add origin https://github.com/org/public-repo.git
git push -u origin main
```

### Step 2: Add Submodule

**IMPORTANT:** Add submodule **BEFORE** accidentally committing private code!

```bash
cd public-repo

# Add private repo as submodule
git submodule add https://github.com/org/private-repo integration/

# Initialize submodule
git submodule update --init --recursive

# Commit submodule reference
git add .gitmodules integration/
git commit -m "feat: Add private-repo submodule for integration"
git push
```

**What This Creates:**

`.gitmodules` file:
```toml
[submodule "integration"]
    path = integration
    url = https://github.com/org/private-repo
```

**Directory structure:**
```
public-repo/
├── .gitmodules          # Submodule configuration
├── integration/         # Submodule directory (tracked as single commit)
│   └── (private repo content - not stored in public repo)
└── README.md
```

### Step 3: Update .gitignore (Prevention)

**CRITICAL:** Add .gitignore entries to prevent accidental commits:

```gitignore
# NEVER commit private code directly (use submodule)
# Private repo is at integration/ (submodule)
# DO NOT copy files from integration/ to other directories

# Block common mistake patterns
/private-code/           # If someone creates this
/api-keys/               # If someone adds this
.env*                    # Always block .env files
secrets/                 # Block secrets directory
```

### Step 4: Team Onboarding

**Document Clone Process:**

Update `README.md`:
```markdown
## Installation

### Clone with Submodules

```bash
# Clone repository with submodules
git clone --recurse-submodules https://github.com/org/public-repo.git
cd public-repo
```

**Note:** The `--recurse-submodules` flag initializes the `integration/` submodule,
which contains integration documentation from our private repository.

### If You Forgot --recurse-submodules

```bash
# Initialize submodules after cloning
git submodule update --init --recursive
```

### Verify Setup

```bash
# Check submodule status
git submodule status
# Should show: <commit-sha> integration (heads/main)

# Verify integration docs
ls integration/.integration/
# Should show integration documentation
```

### Troubleshooting

**Authentication Required:**
If you see "fatal: could not read Username", you need access to the private repository.
Contact the team lead for access to `org/private-repo`.
```

---

## Maintenance Workflows

### Updating Submodule (When Private Repo Changes)

**Scenario:** Private repo added new integration docs, public repo needs to reference them.

```bash
cd public-repo

# Enter submodule directory
cd integration/

# Pull latest changes from private repo
git pull origin main

# Return to public repo root
cd ..

# Stage the submodule update (commit SHA change)
git add integration/

# Commit the update
git commit -m "chore: Update integration submodule to latest"

# Push to public repo
git push
```

**What This Does:**
- Updates the commit SHA that public repo points to
- Other team members will see the new commit when they pull
- They must run `git submodule update` to sync

### Team Member Syncing Submodule

**Scenario:** Another team member pulls the public repo and sees submodule update.

```bash
cd public-repo

# Pull latest changes
git pull

# Sync submodules to match commit SHAs
git submodule update --recursive

# Verify
git submodule status
```

### Checking Submodule Status

```bash
# See which commit submodule is on
git submodule status

# See if submodule has uncommitted changes
cd integration/
git status

# See if submodule is behind remote
git fetch
git log HEAD..origin/main --oneline
```

---

## Real-World Example: ÆtherLight

### Architecture

**Public Repository:** `github.com/AEtherlight-ai/lumina`
- VS Code extension (`vscode-lumina/`)
- Desktop app (`products/lumina-desktop/`)
- Public documentation (`docs/`)
- **Submodule:** `website/` → Integration docs only

**Private Repository:** `github.com/AEtherlight-ai/website`
- Next.js dashboard (`app/`)
- API routes with keys (`app/api/`)
- Supabase integration (`lib/supabase/`)
- **Exposed via submodule:** `.integration/` directory

### What's Exposed Publicly

`.gitmodules`:
```toml
[submodule "website"]
    path = website
    url = https://github.com/AEtherlight-ai/website
```

Public repo references: `76fe41848715dd82bef12937874b4f2fc5ecdcca`

**That's it!** Just a commit SHA. No private code visible.

### What's Accessible (With Auth)

If you have access to both repos:
```bash
git clone --recurse-submodules https://github.com/AEtherlight-ai/lumina.git
cd lumina/website/.integration/

# You can read integration docs
cat LUMINA_REPO_ONBOARDING.md
ls specs/
ls tasks/
```

If you only have public repo access:
```bash
git clone https://github.com/AEtherlight-ai/lumina.git
cd lumina/

# Submodule init will fail (private repo, auth required)
git submodule update --init
# Error: Authentication required
```

### Incident Prevention

**Before Pattern-GIT-002 (WRONG):**
```
lumina/
├── products/
│   ├── lumina-desktop/   ✅ Public
│   └── lumina-web/       ❌ Private code committed directly!
```

**After Pattern-GIT-002 (CORRECT):**
```
lumina/
├── products/
│   └── lumina-desktop/   ✅ Public
└── website/              🔗 Submodule (commit SHA only)
    └── .integration/     ✅ Integration docs (with auth)
```

---

## Decision Tree

Use this flowchart when adding new code:

```
┌─────────────────────────────────────┐
│ I have code to add to the project  │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ Is it private/   │  YES
        │ proprietary?     ├──────────┐
        └──────┬───────────┘          │
               │ NO                   │
               ▼                      ▼
        ┌──────────────────┐   ┌─────────────────────┐
        │ Add to public    │   │ Does private repo   │  YES
        │ repo directly    │   │ already exist?      ├────────┐
        └──────────────────┘   └──────┬──────────────┘        │
                                      │ NO                    │
                                      ▼                       ▼
                               ┌──────────────────┐   ┌──────────────────┐
                               │ Create private   │   │ Is it already    │ YES
                               │ repo first       │   │ a submodule?     ├──────┐
                               └──────┬───────────┘   └──────┬───────────┘      │
                                      │                      │ NO               │
                                      │                      ▼                  ▼
                                      │               ┌──────────────────┐  ┌────────────────┐
                                      └───────────────▶ Add as submodule │  │ Add to private │
                                                      └──────────────────┘  │ repo, update   │
                                                                            │ submodule SHA  │
                                                                            └────────────────┘
```

**Key Questions:**
1. **Is this private/proprietary?** → If YES, it belongs in private repo
2. **Does private repo exist?** → If NO, create it first
3. **Is it already a submodule?** → If NO, add as submodule; If YES, update SHA

---

## Emergency Recovery (If You Committed Private Code)

**If you accidentally committed private code to public repo:**

### Step 1: STOP Immediately
```bash
# Do NOT push if you haven't pushed yet!
git reset --soft HEAD~1   # Undo commit, keep changes
# Move files to correct location, then commit properly
```

### Step 2: If Already Pushed (History Rewrite Required)

**Use BFG Repo-Cleaner** (10-720x faster than git filter-branch):

```bash
# 1. Install BFG
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# 2. Clone mirror
git clone --mirror https://github.com/org/public-repo.git repo-mirror.git

# 3. Run BFG to delete folder from ALL history
java -jar bfg.jar --delete-folders private-folder repo-mirror.git

# 4. Clean up
cd repo-mirror.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Force push (IRREVERSIBLE - coordinate with team!)
git push --force --all
git push --force --tags
```

**IMPORTANT:**
- Force push rewrites public history
- All team members must re-clone
- Coordinate before executing
- See incident report: `docs/incidents/REPO_LEAK_2025-11-09.md`

### Step 3: Setup Proper Submodule

```bash
# Remove from local
git rm -rf private-folder

# Update .gitignore
echo "private-folder/" >> .gitignore

# Add as submodule
git submodule add https://github.com/org/private-repo integration/

# Commit and push
git add .gitmodules .gitignore integration/
git commit -m "fix: Remove leaked private code, add proper submodule"
git push
```

---

## Prevention Checklist

Use this checklist **BEFORE committing ANY new directory:**

### Pre-Commit Questions

**STOP. Answer these questions OUT LOUD:**

1. ✅ **Is this private/proprietary code?**
   - Check for: API keys, commercial logic, customer data, auth secrets
   - If YES → **MUST use git submodule** (this pattern)
   - If NO → Can commit directly (public code only)

2. ✅ **Does this directory belong in the public repo?**
   - Public repo: Open-source code, public docs, community features
   - Private repo: API keys, commercial features, customer data
   - If unsure → **Ask team lead before committing**

3. ✅ **Is there a .gitignore entry to prevent accidents?**
   - Private directories should be gitignored **AND** submoduled
   - Verify: `git check-ignore <directory>`
   - If not ignored → Add to .gitignore immediately

4. ✅ **Have I set up the submodule correctly?**
   - Verify: `git submodule status` shows the directory
   - Verify: `.gitmodules` contains correct URL
   - Verify: Can clone with `--recurse-submodules`

### Automated Checks (Recommended)

**Pre-commit Hook:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Block commits to private directories
if git diff --cached --name-only | grep -q "^private-code/"; then
    echo "ERROR: Cannot commit to private-code/ directly"
    echo "Use submodule: git submodule add <url> integration/"
    exit 1
fi
```

**CI/CD Check:**
```yaml
# .github/workflows/validate.yml
name: Validate Repository Structure
on: [push, pull_request]

jobs:
  check-submodules:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Verify no private code in public repo
        run: |
          if [ -d "private-code" ]; then
            echo "ERROR: private-code/ directory found"
            echo "This should be a submodule"
            exit 1
          fi

      - name: Verify submodule structure
        run: |
          git submodule status
          # Verify .gitmodules exists and is valid
```

---

## Common Pitfalls

### Pitfall 1: Copying Files from Submodule

**WRONG:**
```bash
cd integration/
cp -r api-docs/ ../public-docs/   # ❌ Copying private files!
```

**Reason:** This defeats the purpose of the submodule. Files are now in public repo.

**CORRECT:**
- Keep files in submodule
- Reference them with relative paths in docs
- Use symlinks if absolutely necessary (with caution)

### Pitfall 2: Committing .env Files

**WRONG:**
```bash
cp integration/.env .env   # ❌ Copying secrets!
git add .env               # ❌ Committing secrets!
```

**CORRECT:**
```bash
# .gitignore should block this
echo ".env*" >> .gitignore
git add .gitignore

# Use .env.example for documentation
cp .env .env.example
# Remove all secrets from .env.example
git add .env.example
```

### Pitfall 3: Forgetting to Update Submodule

**Problem:** Private repo changes, but public repo still references old commit.

**Symptom:**
```bash
cd integration/
git status
# Output: HEAD detached at <old-commit>
```

**Solution:**
```bash
cd integration/
git pull origin main
cd ..
git add integration/
git commit -m "chore: Update integration submodule"
git push
```

### Pitfall 4: Submodule in Submodule (Nested)

**Scenario:** Private repo has its own submodule.

**Problem:** `git clone --recurse-submodules` may not initialize nested submodules.

**Solution:**
```bash
git clone --recurse-submodules https://github.com/org/public-repo.git
cd public-repo/integration/
git submodule update --init --recursive   # Explicitly init nested
```

---

## Related Patterns

- **Pattern-GIT-001:** Git Workflow Integration
- **Pattern-SECURITY-001:** Defense in Depth
- **Pattern-DOCS-001:** Documentation Philosophy

---

## References

- **Incident Report:** `docs/incidents/REPO_LEAK_2025-11-09.md`
- **Git Documentation:** https://git-scm.com/book/en/v2/Git-Tools-Submodules
- **BFG Repo-Cleaner:** https://rtyley.github.io/bfg-repo-cleaner/
- **GitHub Submodules Guide:** https://github.blog/2016-02-01-working-with-submodules/

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-11-09 | Initial version (created after REPO_LEAK incident) | BB_Aelor |

---

**Pattern Status:** ✅ Active
**Adoption:** Required for all public/private repo architectures
**Last Review:** 2025-11-09
