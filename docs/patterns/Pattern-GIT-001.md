# Pattern-GIT-001: Git Workflow Integration Protocol

**CREATED:** 2025-11-08
**CATEGORY:** Workflow Protocol
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.83
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-CODE-001, PATTERN-TRACKING-001

---


## Problem

Starting workflows without checking git state leads to:
- Uncommitted changes blocking clean workflow execution
- Accidental pushes to main/master branch
- Merge conflicts discovered mid-workflow
- No visibility into git state during development
- Confusion about current branch and pending changes

**Without this protocol:**
- User doesn't know if working directory is clean
- Risk of losing uncommitted work
- Merge conflicts surprise user mid-task
- No context about what's ready to push

---

## Solution

**MANDATORY: Check git status BEFORE every workflow**

Every workflow check MUST include git status to provide visibility and prevent git-related issues from blocking development.

---

## When to Use

- Before code development workflow (Pattern-CODE-001)
- Before sprint planning workflow (Pattern-SPRINT-PLAN-001)
- Before commit and push operations
- Before branch creation or switching
- During task tracking updates (Pattern-TRACKING-001)

---

## Git Status Check Template

Every workflow check MUST include:

```
Git Status:
✅ Working directory: Clean (no uncommitted changes)
✅ Current branch: feature/proto-001 (not main/master)
✅ Merge conflicts: None
✅ Unpushed commits: 2 commits ahead of origin/master
```

---

## Git States and Actions

### 1. Clean Working Directory ✅

**Status:** No uncommitted changes

**Check:**
```bash
git status --porcelain
# Output: (empty)
```

**Action:** Proceed with workflow

**Remediation:** N/A

**Example:**
```
Git Status: Clean ✅
Working directory: No uncommitted changes
Current branch: feature/license-dashboard
Action: Ready to proceed with workflow
```

---

### 2. Uncommitted Changes ⚠️

**Status:** Modified files not staged/committed

**Check:**
```bash
git status --porcelain
# Output:
 M src/services/workflowCheck.ts
 M test/services/workflowCheck.test.ts
```

**Action:** Warn user (suboptimal but not blocking)

**Remediation:**
```bash
# Option 1: Commit changes
git add .
git commit -m "feat: Add workflow check service"

# Option 2: Stash changes
git stash push -m "WIP: workflow check implementation"

# Option 3: Proceed with caution (user's choice)
# Continue with uncommitted changes (not recommended)
```

**Example:**
```
Git Status: Uncommitted changes ⚠️
Working directory: 2 files modified
Files:
- src/services/workflowCheck.ts (modified)
- test/services/workflowCheck.test.ts (modified)

Recommendation: Commit or stash changes before proceeding
Remediation: git add . && git commit -m "..."

User choice: Proceed anyway OR commit first
```

---

### 3. On Main Branch ⚠️

**Status:** Current branch is main/master

**Check:**
```bash
git rev-parse --abbrev-ref HEAD
# Output: master
```

**Action:** Critical junction (ask user before push)

**Remediation:**
```bash
# Create feature branch
git checkout -b feature/license-dashboard

# OR continue on main (requires explicit user approval)
```

**Example:**
```
Git Status: On main branch ⚠️
Current branch: master
Warning: Direct commits to main branch

Recommendation: Create feature branch
Remediation: git checkout -b feature/my-feature

Critical Junction: YES
Action: Ask user before proceeding with push to main
```

---

### 4. Merge Conflicts ❌

**Status:** Unresolved merge conflicts

**Check:**
```bash
git ls-files -u
# Output: (files with conflicts)
```

**Action:** Block workflow

**Remediation:**
```bash
# View conflicts
git status

# Resolve conflicts manually in editor
# Then:
git add <resolved-files>
git commit -m "Merge: Resolve conflicts"
```

**Example:**
```
Git Status: Merge conflicts ❌
Working directory: Conflicts detected
Files with conflicts:
- src/services/workflowCheck.ts
- vscode-lumina/package.json

Action: BLOCK workflow
Remediation: Resolve conflicts before proceeding
  1. Open files in editor
  2. Resolve <<<<<<< markers
  3. git add <files>
  4. git commit -m "Merge: Resolve conflicts"
```

---

### 5. Git Not Available ❌

**Status:** Git command failed (git not installed OR not a git repo)

**Check:**
```bash
git status
# Output: Error: git: command not found
# OR: Error: not a git repository
```

**Action:** Warn user (degraded functionality, not blocking)

**Remediation:**
```bash
# If git not installed
# Windows: Download from git-scm.com
# Mac: brew install git
# Linux: apt-get install git

# If not a git repo
git init
git remote add origin <repo-url>
```

**Example:**
```
Git Status: Not available ❌
Error: Git command failed
Reason: git not found in PATH (OR not a git repository)

Action: Warn user (degraded functionality)
Workflow: Continue without git integration (some features disabled)
Remediation:
- Install git: https://git-scm.com
- OR initialize repo: git init
```

---

## Git Commands Used

### Check Status
```bash
# Porcelain format (machine-readable)
git status --porcelain

# Example output:
 M src/file.ts          # Modified, not staged
M  src/file2.ts         # Modified, staged
?? src/file3.ts         # Untracked
```

### Check Current Branch
```bash
# Get current branch name
git rev-parse --abbrev-ref HEAD

# Example output: feature/proto-001
```

### Check Unpushed Commits
```bash
# Show commits ahead of origin
git log origin/HEAD..HEAD --oneline

# Example output:
abc123 feat: Add workflow check
def456 fix: Update confidence scoring
```

### Check Merge Conflicts
```bash
# List files with unresolved conflicts
git ls-files -u

# Example output:
100644 abc123... 1  src/services/workflowCheck.ts
100644 def456... 2  src/services/workflowCheck.ts
100644 ghi789... 3  src/services/workflowCheck.ts
```

### Check Remote Status
```bash
# Fetch latest from remote
git fetch

# Check if branch is up to date
git status

# Example output:
Your branch is ahead of 'origin/master' by 2 commits.
```

---

## Integration with WorkflowCheck.ts

Git status checking is implemented in `WorkflowCheck.ts`:

```typescript
// vscode-lumina/src/services/WorkflowCheck.ts

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface GitStatus {
  clean: boolean;
  branch: string;
  conflicts: boolean;
  unpushedCommits: number;
  available: boolean;
  error?: string;
}

export class WorkflowCheck {

  /**
   * Check git status
   * Pattern-GIT-001: Git Workflow Integration Protocol
   */
  async checkGitStatus(): Promise<GitStatus> {
    try {
      // Check if git is available
      const { stdout: gitVersion } = await execAsync('git --version');

      // Get current branch
      const { stdout: branch } = await execAsync('git rev-parse --abbrev-ref HEAD');

      // Check working directory status
      const { stdout: status } = await execAsync('git status --porcelain');

      // Check for merge conflicts
      const { stdout: conflicts } = await execAsync('git ls-files -u');

      // Check unpushed commits
      const { stdout: unpushed } = await execAsync('git log origin/HEAD..HEAD --oneline');

      return {
        available: true,
        clean: status.trim().length === 0,
        branch: branch.trim(),
        conflicts: conflicts.trim().length > 0,
        unpushedCommits: unpushed.trim().split('\n').filter(l => l).length
      };

    } catch (error) {
      // Git not available or command failed
      return {
        available: false,
        clean: false,
        branch: 'unknown',
        conflicts: false,
        unpushed Commits: 0,
        error: error.message
      };
    }
  }
}
```

**Performance Optimization:**
- **Caching:** Cache git status for 5 seconds (reduces redundant calls)
- **Target:** <50ms on cache hit, <200ms on cache miss
- **Graceful degradation:** Continues workflow if git unavailable (warns user)

---

## Workflow Integration Examples

### Example 1: Code Development Workflow

```
🔍 Code Workflow Check: PROTO-001 - Universal Workflow Check System
================================================================

Prerequisites:
✅ Sprint task: PROTO-001 assigned to infrastructure-agent
✅ Tests exist: test/services/workflowCheck.test.ts

Git Status: ✅ Clean
✅ Working directory: Clean (no uncommitted changes)
✅ Current branch: feature/proto-001 (not main/master)
✅ Merge conflicts: None
✅ Unpushed commits: 0 (up to date with origin)

✅ Confidence: 0.90 (HIGH)

Ready to proceed ✅
```

### Example 2: Sprint Planning Workflow

```
🔍 Sprint Planning Workflow Check
================================================================

Prerequisites:
✅ Workspace analyzed: Context gathered from codebase
✅ Agent Registry: 9 agents loaded

Git Status: ⚠️  Uncommitted changes
⚠️  Working directory: 1 file modified
    - internal/sprints/ACTIVE_SPRINT.toml (modified)
⚠️  Current branch: master
✅ Merge conflicts: None
✅ Unpushed commits: 0

Recommendation: Commit ACTIVE_SPRINT.toml before creating new sprint
Remediation: git add internal/sprints/ACTIVE_SPRINT.toml && git commit

Critical Junction: YES (on master + uncommitted changes)
Action: Ask user to commit OR stash before proceeding
```

### Example 3: Pre-Commit Workflow

```
🔍 Pre-Commit Checklist: PROTO-001
================================================================

Git Status: ✅ Ready to commit
✅ Working directory: 2 files staged
    - src/services/WorkflowCheck.ts (staged)
    - test/services/workflowCheck.test.ts (staged)
✅ Current branch: feature/proto-001
✅ Merge conflicts: None
✅ Unpushed commits: 3 (will be 4 after commit)

Ready to commit ✅
Command: git commit -m "feat: Add WorkflowCheck service"
```

---

## Error Handling

### Git Command Timeout
```typescript
// Set timeout for git commands (10 seconds)
const { stdout } = await execAsync('git status --porcelain', {
  timeout: 10000
});
```

### Network Issues (Checking Remote)
```typescript
// Gracefully handle fetch failures
try {
  await execAsync('git fetch', { timeout: 5000 });
} catch (error) {
  // Continue without remote status check
  logger.warn('Git fetch failed - continuing without remote status', error);
}
```

### Permission Errors
```typescript
// Handle permission denied errors
try {
  await execAsync('git status');
} catch (error) {
  if (error.message.includes('Permission denied')) {
    return {
      available: false,
      error: 'Git permission denied - check repository permissions'
    };
  }
  throw error;
}
```

---

## Benefits

1. **Prevents git-related workflow blocks**
   - Know git state before starting work
   - Avoid surprises mid-workflow

2. **Visibility for user**
   - Always see current branch
   - Know if changes are committed
   - Understand remote sync status

3. **Prevents accidental main pushes**
   - Critical junction when on main branch
   - User approves before push to main

4. **Catches conflicts early**
   - Detect merge conflicts before starting work
   - Resolve conflicts before implementation

5. **Graceful degradation**
   - Continues workflow if git unavailable
   - Warns user but doesn't block

---

## Related Patterns

- **Pattern-CODE-001:** Code Development Protocol (uses git status check)
- **Pattern-SPRINT-PLAN-001:** Sprint Planning Protocol (uses git status check)
- **Pattern-TRACKING-001:** Task Tracking & Pre-Commit Protocol (uses git status check)

---

## Version History

- **v1.0.0** (2025-01-06): Initial extraction from CLAUDE.md
  - Formalized git status checking across all workflows
  - Added 5 git states with remediation steps
  - Integrated with WorkflowCheck.ts implementation
  - Added caching and performance optimization
  - Documented error handling patterns
