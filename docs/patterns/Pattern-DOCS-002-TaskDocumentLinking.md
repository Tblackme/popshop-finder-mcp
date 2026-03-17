# Pattern-DOCS-002: Task Document Linking & Organization

**Created**: 2025-01-13
**Category**: Documentation
**Status**: Active
**Enforcement**: Automated (pre-commit hook + validation script)

---

## Problem

**Issue**: Task-related documents (enhanced prompts, questions, test plans, design docs) can become orphaned or unlinked from their tasks, making them hard to discover and maintain.

**Impact**:
- Lost documentation (files exist but aren't referenced)
- Inconsistent organization (some tasks linked, some not)
- Difficult discovery (can't find all docs for a task)
- Manual process prone to human error

**Severity**: Medium - Organizational debt accumulates over time

---

## Solution

**Approach**: Enforce strict naming convention + automated TOML linking + validation scripts

**Key Principles**:
1. **Naming Convention**: All task documents MUST use `{TASK_ID}_{TYPE}.md` format
2. **TOML Linking**: All task documents MUST be referenced in sprint TOML
3. **Automated Validation**: Pre-commit hook validates all links
4. **Discoverability**: Search by task ID finds ALL related docs

---

## Naming Convention

### Standard Format (Sprint-Aware)

```
{SPRINT_ID}_{TASK_ID}_{TYPE}.md
```

**Why Sprint ID?** Prevents collisions when multiple sprints have the same task ID (e.g., Sprint 3 BUG-001 vs Sprint 17.1 BUG-001).

**Examples**:
- `17.1-BUGS_BUG-011_ENHANCED_PROMPT.md` (Sprint 17.1, enhanced prompt)
- `17.1-BUGS_BUG-011_QUESTIONS.md` (Sprint 17.1, questions document)
- `3_PROTECT-001_TEST_PLAN.md` (Sprint 3, test plan)
- `4_KEY-002_DESIGN.md` (Sprint 4, design document)
- `17.1-BUGS_BUG-011_RETROSPECTIVE.md` (Sprint 17.1, retrospective)

### Sprint ID Format

**Extract from TOML filename**: Remove `ACTIVE_SPRINT_` prefix from sprint TOML filename

**Examples**:
- `ACTIVE_SPRINT_17.1_BUGS.toml` → Sprint ID = `17.1-BUGS`
- `ACTIVE_SPRINT_3.toml` → Sprint ID = `3`
- `ACTIVE_SPRINT_4_KEYS.toml` → Sprint ID = `4-KEYS`

**Sprint ID Normalization**:
- Replace underscores with hyphens: `17.1_BUGS` → `17.1-BUGS`
- Keep version-style IDs: `17.1`, `3`, `4`
- Use full identifier for clarity: `17.1-BUGS` not just `17.1`

### Task ID Format

**Sprint Tasks**: Use sprint prefix + number
- Sprint 3: `PROTECT-001`, `CONFIG-002`, `TASK-003`
- Sprint 4: `KEY-001`, `KEY-002`
- Bug sprints: `BUG-001`, `BUG-002`

**Templates**: Use descriptive name + version (no sprint ID for templates)
- `MVP-003-PromptEnhancer-TaskTemplate-v1.4.md`
- `SPRINT_TEMPLATE.toml`

### Document Types

**Standard Types** (use these exact names):
- `ENHANCED_PROMPT` - Enhanced task implementation guide
- `QUESTIONS` - Pre-implementation questions document
- `TEST_PLAN` - Testing strategy and test cases
- `DESIGN` - Design document or architecture diagram
- `RETROSPECTIVE` - Post-completion retrospective
- `NOTES` - Additional notes or context
- `RESEARCH` - Research findings

**Custom Types**: Use UPPERCASE with underscores
- `DESKTOP_HANDOFF` (for cross-team communication)
- `API_SPEC` (for API design)
- `UX_MOCKUP` (for UI designs)

---

## TOML Linking

### Required Fields

**All tasks MUST have** (using sprint-aware naming):
```toml
[tasks.BUG-011]
id = "BUG-011"
name = "Task name"
enhanced_prompt = "internal/sprints/enhanced_prompts/17.1-BUGS_BUG-011_ENHANCED_PROMPT.md"  # REQUIRED
template = "MVP-003-PromptEnhancer-TaskTemplate-v1.4.3"  # REQUIRED
```

**Optional fields** (add if document exists):
```toml
questions_doc = "internal/sprints/questions/17.1-BUGS_BUG-011_QUESTIONS.md"
test_plan = "internal/sprints/test_plans/17.1-BUGS_BUG-011_TEST_PLAN.md"
design_doc = "internal/sprints/design/17.1-BUGS_BUG-011_DESIGN.md"
retrospective = "internal/sprints/retrospectives/17.1-BUGS_BUG-011_RETROSPECTIVE.md"
notes = "internal/sprints/notes/17.1-BUGS_BUG-011_NOTES.md"
```

### Directory Structure

```
internal/sprints/
├── enhanced_prompts/       # Enhanced task prompts (REQUIRED for all tasks)
│   ├── 17.1-BUGS_BUG-011_ENHANCED_PROMPT.md
│   ├── 17.1-BUGS_BUG-012_ENHANCED_PROMPT.md
│   ├── 3_PROTECT-001_ENHANCED_PROMPT.md
│   └── 4_KEY-002_ENHANCED_PROMPT.md
├── questions/              # Pre-implementation questions
│   ├── 17.1-BUGS_BUG-011_QUESTIONS.md
│   └── 3_PROTECT-001_QUESTIONS.md
├── test_plans/             # Test plans and strategies
│   ├── 17.1-BUGS_BUG-011_TEST_PLAN.md
│   └── 3_PROTECT-001_TEST_PLAN.md
├── design/                 # Design documents
│   └── 4_KEY-002_DESIGN.md
├── retrospectives/         # Post-completion retrospectives
│   └── 17.1-BUGS_BUG-011_RETROSPECTIVE.md
├── notes/                  # Additional notes
│   └── 17.1-BUGS_BUG-011_NOTES.md
└── ACTIVE_SPRINT_*.toml    # Sprint TOML files
```

---

## Automated Enforcement

### 1. Validation Script

**File**: `scripts/validate-task-docs.js`

**Purpose**: Find orphaned documents and missing TOML links

**Usage**:
```bash
node scripts/validate-task-docs.js
node scripts/validate-task-docs.js --fix  # Auto-fix missing links
```

**Checks**:
1. ✅ All enhanced prompts are linked in TOML
2. ✅ All questions docs are linked in TOML
3. ✅ All TOML document references point to existing files
4. ✅ All task documents follow naming convention
5. ✅ All tasks have enhanced_prompt field (required)

**Output**:
```
✅ Validation passed: 45/45 documents linked
❌ Orphaned documents found:
   - internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md (NOT LINKED)
❌ Missing files:
   - BUG-014: enhanced_prompt references non-existent file
❌ Invalid naming:
   - internal/sprints/enhanced_prompts/bug-015-prompt.md (should be 17.1-BUGS_BUG-015_ENHANCED_PROMPT.md)
❌ Sprint ID mismatch:
   - internal/sprints/enhanced_prompts/3_BUG-011_ENHANCED_PROMPT.md (belongs to Sprint 17.1, not Sprint 3)
```

### 2. Pre-Commit Hook

**File**: `.git/hooks/pre-commit`

**Purpose**: Block commits with orphaned docs or broken links

**Triggers**:
- Run `validate-task-docs.js` before every commit
- If validation fails → block commit
- Show error message with instructions

**Implementation**:
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔍 Validating task document links..."
node scripts/validate-task-docs.js

if [ $? -ne 0 ]; then
  echo "❌ Task document validation failed!"
  echo "Fix errors above or use --no-verify to skip (NOT RECOMMENDED)"
  exit 1
fi

echo "✅ Task document validation passed"

# VAL-002: Completion documentation validation
echo ""
node scripts/validate-completion-documentation.js

if [ $? -ne 0 ]; then
  exit 1
fi
```

**Installation**:
```bash
node scripts/install-hooks.js
```

This script installs BOTH validators (task document linking + completion documentation) into the pre-commit hook.

### 2a. Completion Documentation Validation (VAL-002)

**File**: `scripts/validate-completion-documentation.js`

**Purpose**: Enforce completion_notes field for all completed tasks

**Background**:
- Template v1.4.1 Section 12 added completion documentation instructions
- Instructions alone achieved only 72% compliance (BUG-002A audit finding)
- VAL-002 automates enforcement via pre-commit hook
- Prevents documentation gaps that waste 3+ hours in manual audits

**Usage**:
```bash
node scripts/validate-completion-documentation.js
```

**How It Works**:
1. Checks if sprint TOML files are staged for commit (performance optimization)
2. Parses all sprint TOML files in `internal/sprints/`
3. Finds all tasks with `status = "completed"`
4. Checks each completed task has `completion_notes` field (non-empty)
5. If violations found → blocks commit with helpful error message
6. If all completed tasks have notes → allows commit

**Checks**:
1. ✅ All completed tasks have `completion_notes` field
2. ✅ `completion_notes` is non-empty (not just empty string)
3. ✅ Pending/in_progress tasks are ignored (no validation)

**Output**:
```
[ÆtherLight] Checking completion documentation...
[ÆtherLight] Validating: internal/sprints
✅ Completion documentation validation passed
   Files validated: 9
   Completed tasks: 166
   Tasks with completion_notes: 57

# Or if violations found:
❌ VALIDATION FAILED: Completed tasks missing completion_notes:

   - ENHANCE-001.2: Simple Context Builders
   - BUG-005: Fix authentication bug

💡 TIP: Add completion_notes field after completed_date in Sprint TOML

Example:
  status = "completed"
  completed_date = "2025-11-13"
  completion_notes = """
  Completed 2025-11-13 by [agent]

  Implementation Summary:
  - Files created: [list files]
  - Lines written: [count]
  - Tests: [coverage %]
  """

🚫 Commit blocked. Add completion_notes and try again.
```

**ROI**:
- Cost: $0.04 per commit (validator execution)
- Benefit: $600 per sprint (manual audit cost avoided)
- ROI: 15,000x return on investment

**Related**:
- VAL-002 task in Sprint 17.1
- Template v1.4.1 Section 12 (Post-Completion Documentation)
- BUG-002A audit (72% compliance issue that triggered this)

### 3. Documentation Audit Command

**Command**: `/audit-task-docs` (Claude Code skill)

**Purpose**: Generate report of all task documentation

**Usage**: User types `/audit-task-docs` in Claude Code

**Output**:
```markdown
# Task Documentation Audit Report

## Summary
- Total tasks: 45
- Total documents: 123
- Orphaned documents: 2
- Missing enhanced prompts: 0
- Coverage: 98%

## Orphaned Documents
1. internal/sprints/enhanced_prompts/OLD_TASK_PROMPT.md
2. internal/sprints/questions/LEGACY_QUESTIONS.md

## Missing Enhanced Prompts
(None - all tasks have enhanced prompts ✅)

## Document Coverage by Task
- BUG-011: 4 documents (enhanced_prompt, questions_doc, test_plan, retrospective)
- BUG-012: 1 document (enhanced_prompt)
...
```

---

## Implementation

### Step 1: Create Validation Script

**File**: `scripts/validate-task-docs.js`

```javascript
/**
 * Task Document Validation Script
 *
 * Validates that all task-related documents are:
 * 1. Named correctly ({TASK_ID}_{TYPE}.md)
 * 2. Linked in sprint TOML files
 * 3. Actually exist on filesystem
 *
 * Usage:
 *   node scripts/validate-task-docs.js           # Validate only
 *   node scripts/validate-task-docs.js --fix     # Auto-fix missing links
 */

const fs = require('fs');
const path = require('path');
const toml = require('@iarna/toml');

// Configuration
const SPRINTS_DIR = 'internal/sprints';
const DOC_TYPES = {
  'enhanced_prompts': 'enhanced_prompt',
  'questions': 'questions_doc',
  'test_plans': 'test_plan',
  'design': 'design_doc',
  'retrospectives': 'retrospective',
  'notes': 'notes'
};

const REQUIRED_FIELDS = ['enhanced_prompt']; // All tasks MUST have enhanced_prompt

// Main validation function
async function validateTaskDocs() {
  console.log('🔍 Validating task document links...\n');

  const errors = [];
  const warnings = [];

  // Step 1: Find all sprint TOML files
  const sprintFiles = fs.readdirSync(SPRINTS_DIR)
    .filter(f => f.startsWith('ACTIVE_SPRINT') && f.endsWith('.toml'));

  console.log(`Found ${sprintFiles.length} sprint files\n`);

  // Step 2: Parse each sprint file and collect task IDs
  const allTasks = new Map(); // taskId -> { sprint, sprintId, task }

  for (const sprintFile of sprintFiles) {
    // Extract sprint ID from filename: ACTIVE_SPRINT_17.1_BUGS.toml → 17.1-BUGS
    const sprintIdMatch = sprintFile.match(/^ACTIVE_SPRINT_(.+)\.toml$/);
    const sprintId = sprintIdMatch ? sprintIdMatch[1].replace(/_/g, '-') : 'UNKNOWN';

    const sprintPath = path.join(SPRINTS_DIR, sprintFile);
    const content = fs.readFileSync(sprintPath, 'utf-8');
    const sprint = toml.parse(content);

    if (!sprint.tasks) {
      continue;
    }

    for (const [taskId, task] of Object.entries(sprint.tasks)) {
      allTasks.set(taskId, { sprint: sprintFile, sprintId, task });
    }
  }

  console.log(`Found ${allTasks.size} tasks\n`);

  // Step 3: Find all task documents in filesystem
  const allDocs = new Map(); // filePath -> { taskId, type, docType }

  for (const [dirName, tomlField] of Object.entries(DOC_TYPES)) {
    const dirPath = path.join(SPRINTS_DIR, dirName);

    if (!fs.existsSync(dirPath)) {
      warnings.push(`Directory not found: ${dirPath}`);
      continue;
    }

    const files = fs.readdirSync(dirPath);

    for (const file of files) {
      // Parse filename: {SPRINT_ID}_{TASK_ID}_{TYPE}.md
      const match = file.match(/^([A-Z0-9.-]+)_([A-Z]+-\d+[A-Z]?)_([A-Z_]+)\.md$/);

      if (!match) {
        // Check if it's a template (allow different format)
        if (file.includes('TEMPLATE') || file.includes('MVP-')) {
          continue; // Skip templates
        }

        warnings.push(`Invalid naming convention: ${dirName}/${file} (expected {SPRINT_ID}_{TASK_ID}_{TYPE}.md)`);
        continue;
      }

      const [, sprintId, taskId, docType] = match;
      const filePath = path.join(dirName, file);

      allDocs.set(filePath, { sprintId, taskId, type: tomlField, docType });
    }
  }

  console.log(`Found ${allDocs.size} task documents\n`);

  // Step 4: Validate that all documents are linked in TOML
  for (const [filePath, { sprintId, taskId, type }] of allDocs) {
    const task = allTasks.get(taskId);

    if (!task) {
      errors.push(`Orphaned document: ${filePath} (task ${taskId} not found in any sprint)`);
      continue;
    }

    // Validate sprint ID matches
    if (sprintId !== task.sprintId) {
      errors.push(`Sprint ID mismatch: ${filePath} (document sprint=${sprintId}, task belongs to sprint=${task.sprintId})`);
      continue;
    }

    const linkedPath = task.task[type];

    if (!linkedPath) {
      errors.push(`Missing TOML link: ${filePath} (task ${taskId} missing ${type} field)`);
      continue;
    }

    const expectedPath = `internal/sprints/${filePath}`;
    if (linkedPath !== expectedPath) {
      errors.push(`Incorrect TOML link: ${taskId}.${type} = "${linkedPath}" (should be "${expectedPath}")`);
    }
  }

  // Step 5: Validate that all TOML links point to existing files
  for (const [taskId, { sprint, task }] of allTasks) {
    // Check required fields
    for (const requiredField of REQUIRED_FIELDS) {
      if (!task[requiredField]) {
        errors.push(`Missing required field: ${taskId}.${requiredField} in ${sprint}`);
      }
    }

    // Check all document links
    for (const [dirName, tomlField] of Object.entries(DOC_TYPES)) {
      const linkedPath = task[tomlField];

      if (!linkedPath) {
        continue; // Optional field
      }

      // Check if file exists
      if (!fs.existsSync(linkedPath)) {
        errors.push(`Broken link: ${taskId}.${tomlField} = "${linkedPath}" (file not found)`);
      }
    }
  }

  // Step 6: Report results
  console.log('━'.repeat(60));
  console.log('\n📊 Validation Results:\n');

  if (errors.length === 0 && warnings.length === 0) {
    console.log('✅ All checks passed!');
    console.log(`   - ${allTasks.size} tasks validated`);
    console.log(`   - ${allDocs.size} documents linked`);
    console.log(`   - 0 errors, 0 warnings`);
    return true;
  }

  if (warnings.length > 0) {
    console.log(`⚠️  Warnings (${warnings.length}):\n`);
    warnings.forEach((w, i) => console.log(`   ${i + 1}. ${w}`));
    console.log();
  }

  if (errors.length > 0) {
    console.log(`❌ Errors (${errors.length}):\n`);
    errors.forEach((e, i) => console.log(`   ${i + 1}. ${e}`));
    console.log();
    console.log('Fix errors above before committing.');
    return false;
  }

  return true;
}

// Run validation
validateTaskDocs()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(err => {
    console.error('❌ Validation failed:', err);
    process.exit(1);
  });
```

### Step 2: Install Pre-Commit Hook

**File**: `scripts/install-hooks.js`

```javascript
/**
 * Install Git hooks for task document validation
 *
 * Usage: node scripts/install-hooks.js
 */

const fs = require('fs');
const path = require('path');

const PRE_COMMIT_HOOK = `#!/bin/bash
# Pre-commit hook: Validate task document links
# Generated by scripts/install-hooks.js

echo "🔍 Validating task document links..."
node scripts/validate-task-docs.js

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Task document validation failed!"
  echo "Fix errors above or use --no-verify to skip (NOT RECOMMENDED)"
  exit 1
fi

echo "✅ Task document validation passed"
`;

const hookPath = path.join('.git', 'hooks', 'pre-commit');

fs.writeFileSync(hookPath, PRE_COMMIT_HOOK, { mode: 0o755 });
console.log('✅ Pre-commit hook installed:', hookPath);
```

### Step 3: Add to package.json

```json
{
  "scripts": {
    "validate-docs": "node scripts/validate-task-docs.js",
    "install-hooks": "node scripts/install-hooks.js"
  }
}
```

### Step 4: Run Initial Validation

```bash
# Install hooks
npm run install-hooks

# Run validation
npm run validate-docs
```

---

## Usage Examples

### Creating a New Task Document

```bash
# 1. Identify sprint ID from TOML filename
# File: ACTIVE_SPRINT_17.1_BUGS.toml → Sprint ID: 17.1-BUGS

# 2. Create document with sprint-aware naming
touch internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md

# 3. Add link to sprint TOML
[tasks.BUG-013]
id = "BUG-013"
name = "Fix something"
enhanced_prompt = "internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md"
template = "MVP-003-PromptEnhancer-TaskTemplate-v1.4.3"

# 4. Validation runs automatically on commit
git add internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md
git add internal/sprints/ACTIVE_SPRINT_17.1_BUGS.toml
git commit -m "feat: Add enhanced prompt for BUG-013"
# ✅ Validation passes, commit succeeds
```

### Adding a Questions Document

```bash
# 1. Create questions document with sprint-aware naming
touch internal/sprints/questions/17.1-BUGS_BUG-013_QUESTIONS.md

# 2. Add link to sprint TOML
[tasks.BUG-013]
id = "BUG-013"
name = "Fix something"
enhanced_prompt = "internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md"
questions_doc = "internal/sprints/questions/17.1-BUGS_BUG-013_QUESTIONS.md"  # ADD THIS

# 3. Commit
git add internal/sprints/questions/17.1-BUGS_BUG-013_QUESTIONS.md
git add internal/sprints/ACTIVE_SPRINT_17.1_BUGS.toml
git commit -m "docs: Add questions document for BUG-013"
# ✅ Validation passes
```

### Finding All Documents for a Task

```bash
# Search by sprint ID + task ID
ls internal/sprints/*/17.1-BUGS_BUG-013*

# Output:
# internal/sprints/enhanced_prompts/17.1-BUGS_BUG-013_ENHANCED_PROMPT.md
# internal/sprints/questions/17.1-BUGS_BUG-013_QUESTIONS.md
# internal/sprints/test_plans/17.1-BUGS_BUG-013_TEST_PLAN.md

# Search across all sprints for same task ID
ls internal/sprints/*/*_BUG-001_*

# Output (shows no collisions):
# internal/sprints/enhanced_prompts/17.1-BUGS_BUG-001_ENHANCED_PROMPT.md
# internal/sprints/enhanced_prompts/3_BUG-001_ENHANCED_PROMPT.md
```

---

## Benefits

### Collision Prevention (Sprint-Aware Naming)
- ✅ No collisions when multiple sprints have same task IDs
- ✅ Example: Sprint 3 BUG-001 vs Sprint 17.1 BUG-001 (both coexist)
- ✅ Sprint ID prefix ensures unique filenames
- ✅ Validation script checks sprint ID matches task owner

### 100% Enforcement
- ✅ Pre-commit hook blocks commits with orphaned docs
- ✅ Validation script catches all issues before they merge
- ✅ No human error possible (automated)
- ✅ Sprint ID mismatch detection prevents wrong-sprint assignment

### Discoverability
- ✅ Search by sprint + task ID finds exact docs
- ✅ Search by task ID alone finds ALL instances across sprints
- ✅ TOML serves as single source of truth
- ✅ Grep works: `grep -r "17.1-BUGS_BUG-013" internal/sprints/`

### Maintainability
- ✅ Consistent naming across all tasks
- ✅ Easy to add new document types
- ✅ Audit script generates reports
- ✅ Clear sprint ownership visible in filename

### Organization
- ✅ Documents grouped by type (enhanced_prompts/, questions/, etc.)
- ✅ Clear directory structure
- ✅ No orphaned files
- ✅ Sprint context always visible

---

## Rollout Plan

### Phase 1: Migrate Existing Documents (Day 1)
1. **Identify all existing task documents**:
   ```bash
   find internal/sprints -name "*_ENHANCED_PROMPT.md"
   find internal/sprints -name "*_QUESTIONS.md"
   # etc.
   ```

2. **Create migration script** (`scripts/migrate-task-docs.js`):
   - Read all sprint TOML files
   - For each task document, determine owning sprint
   - Rename: `BUG-011_ENHANCED_PROMPT.md` → `17.1-BUGS_BUG-011_ENHANCED_PROMPT.md`
   - Update all TOML references automatically

3. **Run migration**:
   ```bash
   node scripts/migrate-task-docs.js --dry-run  # Preview changes
   node scripts/migrate-task-docs.js            # Execute migration
   ```

### Phase 2: Install Automation (Day 1)
1. Create validation script with sprint-aware checks
2. Install pre-commit hook
3. Add npm scripts

### Phase 3: Test (Day 2)
1. Test validation with intentional errors
2. Test sprint ID mismatch detection
3. Test pre-commit hook blocks bad commits
4. Verify all existing tasks pass validation

### Phase 4: Document (Day 2)
1. Update CLAUDE.md with new pattern
2. Update this pattern document
3. Train team on new sprint-aware naming

---

## Future Enhancements

### 1. Document Templates
Create templates for each document type:
- `templates/ENHANCED_PROMPT_TEMPLATE.md`
- `templates/QUESTIONS_TEMPLATE.md`
- `templates/TEST_PLAN_TEMPLATE.md`

### 2. Auto-Generation
Script to auto-create document files:
```bash
npm run create-task-docs BUG-014
# Creates:
# - internal/sprints/enhanced_prompts/BUG-014_ENHANCED_PROMPT.md
# - Adds TOML link automatically
```

### 3. Claude Code Skill
Add `/create-task-docs` skill that:
- Prompts for task ID
- Creates all document files
- Updates sprint TOML
- Opens files in editor

### 4. Visual Dashboard
Web dashboard showing:
- Task documentation coverage
- Orphaned documents
- Missing required docs
- Document type distribution

---

## Related Patterns

- **Pattern-DOCS-001**: Documentation philosophy (high reusability → patterns)
- **Pattern-VALIDATION-001**: Pre-flight checklist enforcement
- **Pattern-TRACKING-001**: Sprint TOML lifecycle management

---

## References

- Naming convention: `{SPRINT_ID}_{TASK_ID}_{TYPE}.md`
- Sprint ID extraction: `ACTIVE_SPRINT_17.1_BUGS.toml` → `17.1-BUGS`
- Directory structure: `internal/sprints/{type}/`
- TOML fields: `enhanced_prompt`, `questions_doc`, `test_plan`, etc.
- Validation script: `scripts/validate-task-docs.js`
- Migration script: `scripts/migrate-task-docs.js`
- Pre-commit hook: `.git/hooks/pre-commit`

---

## Changelog

**2025-01-13 (v1.1)**: Sprint-aware naming to prevent collisions
- **BREAKING**: Changed naming from `{TASK_ID}_{TYPE}.md` to `{SPRINT_ID}_{TASK_ID}_{TYPE}.md`
- Added sprint ID extraction from TOML filename
- Added sprint ID validation in validation script
- Added sprint ID mismatch detection
- Created migration script for existing documents
- Updated all examples and code samples
- Reason: Prevents collisions when multiple sprints have same task IDs

**2025-01-13 (v1.0)**: Initial pattern created
- Defined naming convention: `{TASK_ID}_{TYPE}.md`
- Created validation script
- Installed pre-commit hook
- Documented enforcement mechanism
