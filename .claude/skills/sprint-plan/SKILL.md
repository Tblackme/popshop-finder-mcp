---
name: sprint-plan
version: 1.1.0
description: Create structured sprint plans with automated Git workflow. Generates TOML sprints, creates feature branches, and enforces proper development workflow.
---

# Sprint Planning Skill

## What This Skill Does

Automates sprint planning with Git workflow enforcement:
- Analyzes user requirements and generates sprint structure
- Creates TOML sprint definitions with phases and tasks
- Automatically creates Git branches for features/epics
- Enforces proper branch naming and workflow
- Integrates user context with standardized processes

## ⚠️ CRITICAL: Sprint Format Requirements

**REQUIRED task format:** `[tasks.TASK-ID]` (flat structure)
**OBSOLETE format:** `[[epic.*.tasks]]` (will break SprintLoader)

**5 Required fields per task:**
1. `id` - Task identifier
2. `name` - Task name (NOT "title")
3. `status` - Current status (pending, in_progress, completed)
4. `phase` - Phase name
5. `agent` - Agent assignment

**All other fields are OPTIONAL** - Use minimal format for quick tasks, rich format for complex features.

**Backward compatible:** Old sprints with minimal fields continue to work. New sprints can use rich metadata.

## ⚠️ CRITICAL: Sprint-Aware Naming Convention (Pattern-DOCS-002)

**REQUIRED naming format:** `{SPRINT_ID}_{TASK_ID}_{TYPE}.md`

**Why Sprint ID?** Prevents collisions when multiple sprints have the same task ID (e.g., Sprint 3 BUG-001 vs Sprint 17.1 BUG-001).

**Examples:**
- `17.1-BUGS_BUG-011_ENHANCED_PROMPT.md` (Sprint 17.1, enhanced prompt)
- `17.1-BUGS_BUG-011_QUESTIONS.md` (Sprint 17.1, questions document)
- `3_PROTECT-001_TEST_PLAN.md` (Sprint 3, test plan)
- `4_KEY-002_DESIGN.md` (Sprint 4, design document)

**Sprint ID Extraction:**
- From TOML filename: `ACTIVE_SPRINT_17.1_BUGS.toml` → Sprint ID = `17.1-BUGS`
- Replace underscores with hyphens: `17.1_BUGS` → `17.1-BUGS`

**Document Types:**
- `ENHANCED_PROMPT` - MVP-003 enhanced task prompt
- `QUESTIONS` - Q&A document for task clarification
- `TEST_PLAN` - Test plan and validation criteria
- `DESIGN` - Design document and architecture
- `RETROSPECTIVE` - Post-task retrospective

**Enforcement:**
- Automated via pre-commit hook (INFRA-003)
- Validates naming convention + TOML linking
- See: `docs/patterns/Pattern-DOCS-002-TaskDocumentLinking.md`

**Migration:**
- Old format still works (backward compatible)
- New documents MUST use sprint-aware naming

## When Claude Should Use This

Use this skill when the user:
- Says "plan a sprint" or "create a sprint"
- Wants to organize development work
- Needs to break down features into tasks
- Mentions sprint planning or agile development
- Requests to "add tasks to sprint", "enhance sprint", or "update sprint"

## Invocation Decision: CREATE vs ENHANCE

When this skill is invoked, FIRST determine the mode:

**CREATE Mode** - Creating a new sprint from scratch
- User says: "plan a sprint", "create a sprint", "start new sprint"
- Starting a new feature or project phase
- No existing sprint file to modify
- Workflow: Full sprint creation (Steps 1-6 in CREATE Workflow below)

**ENHANCE Mode** - Adding tasks to existing sprint
- User says: "add tasks to sprint", "enhance sprint", "update current sprint"
- Sprint in progress, needs additional tasks
- Existing `ACTIVE_SPRINT_*.toml` file to modify
- Workflow: Sprint enhancement (see ENHANCE Workflow section after CREATE workflow)

**How to decide:**
1. Check if user mentions "add", "enhance", "update" → ENHANCE mode
2. Check if `internal/sprints/ACTIVE_SPRINT*.toml` exists → Ask user which mode
3. If user explicitly says "create" or "new" → CREATE mode
4. Default: CREATE mode (new sprint)

---

## CREATE Mode Workflow

**Use this workflow when creating a new sprint from scratch.**

### Workflow Process

### 1. Gather Requirements
```
Ask the user:
1. Sprint duration? (1 week, 2 weeks, etc.)
2. Main features/goals?
3. Team size and roles?
4. Priority order?
```

### 2. Analyze and Structure
The skill will:
- Parse user requirements
- Identify epics and features
- Break down into phases
- Create task dependencies
- Assign complexity estimates
- **CRITICAL: Add error handling requirements for EVERY task**
  - Identify potential failure points
  - Require try-catch for all parsing/IO operations
  - Add validation criteria for error boundaries
  - Include error recovery strategies

### 2.5: Inject Template Tasks (Pattern-SPRINT-TEMPLATE-001)

**CRITICAL: After generating feature tasks, automatically inject normalized template tasks.**

This step ensures every sprint includes quality assurance, documentation, and retrospective tasks.

#### Template Injection Process

**Step 1: Load Template**
```javascript
// Load SPRINT_TEMPLATE.toml
const fs = require('fs');
const toml = require('@iarna/toml');

const templatePath = 'internal/sprints/SPRINT_TEMPLATE.toml';
const templateContent = fs.readFileSync(templatePath, 'utf-8');
const template = toml.parse(templateContent);

// Template structure:
// - template.metadata (version, task counts)
// - template.required.* (14 tasks - always include)
// - template.suggested.* (4 tasks - include with skip option)
// - template.conditional.* (8 tasks - condition-based)
// - template.retrospective.* (2 tasks - always include)
```

**Step 2: Detect Conditions**

Analyze sprint requirements to determine which conditional tasks to include:

```javascript
// Condition detection logic
const sprintName = metadata.sprint_name || "";
const sprintDescription = userRequirements || "";
const combinedText = (sprintName + " " + sprintDescription).toLowerCase();

// Publishing condition
const isPublishing = combinedText.includes("publish") ||
                     combinedText.includes("release") ||
                     combinedText.includes("version bump") ||
                     combinedText.includes("v1.0") ||
                     combinedText.includes("deploy");

// User-facing changes condition
const isUserFacing = combinedText.includes("ui") ||
                     combinedText.includes("ux") ||
                     combinedText.includes("user experience") ||
                     combinedText.includes("interface") ||
                     combinedText.includes("component") ||
                     combinedText.includes("breaking change");
```

**Condition Keywords:**

**Publishing Keywords** (triggers PUB-001 to PUB-005):
- "publish", "release", "version bump", "v1.0", "v2.0", "deploy", "distribution"
- Example: "Release v1.0 with authentication" → Publishing tasks included

**User-Facing Keywords** (triggers UX-001 to UX-003):
- "ui", "ux", "user experience", "interface", "component", "breaking change", "migration"
- Example: "Redesign authentication UI" → UX tasks included

**Step 3: Extract Template Tasks**

```javascript
// Extract task categories from template
const requiredTasks = Object.entries(template.required).map(([key, task]) => ({
  ...task,
  category: "REQUIRED",
  canSkip: false
}));

const suggestedTasks = Object.entries(template.suggested).map(([key, task]) => ({
  ...task,
  category: "SUGGESTED",
  canSkip: true,
  skipJustification: ""  // Prompt user for justification if skipping
}));

const conditionalTasks = [];
if (isPublishing) {
  // Include publishing tasks (PUB-001 to PUB-005)
  Object.entries(template.conditional)
    .filter(([key, task]) => task.id.startsWith("PUB-"))
    .forEach(([key, task]) => {
      conditionalTasks.push({
        ...task,
        category: "CONDITIONAL-PUBLISHING",
        condition: "Sprint includes publishing/release"
      });
    });
}

if (isUserFacing) {
  // Include UX tasks (UX-001 to UX-003)
  Object.entries(template.conditional)
    .filter(([key, task]) => task.id.startsWith("UX-"))
    .forEach(([key, task]) => {
      conditionalTasks.push({
        ...task,
        category: "CONDITIONAL-UX",
        condition: "Sprint has user-facing changes"
      });
    });
}

const retrospectiveTasks = Object.entries(template.retrospective).map(([key, task]) => ({
  ...task,
  category: "RETROSPECTIVE",
  canSkip: false
}));

// Total template tasks to inject
const allTemplateTasks = [
  ...requiredTasks,     // 14 tasks
  ...suggestedTasks,    // 4 tasks
  ...conditionalTasks,  // 0-8 tasks (condition-dependent)
  ...retrospectiveTasks // 2 tasks
];
```

**Step 4: Task ID Collision Avoidance**

Template tasks use category prefixes that won't collide with feature tasks:

**Template Task ID Prefixes** (reserved, never use for features):
- `DOC-*` - Documentation tasks (CHANGELOG, README, patterns)
- `QA-*` - Quality assurance tasks (tests, coverage, audits)
- `AGENT-*` - Agent synchronization tasks (context updates)
- `INFRA-*` - Infrastructure tasks (git hooks, validation)
- `CONFIG-*` - Configuration tasks (settings schema)
- `PERF-*` - Performance tasks (regression testing)
- `SEC-*` - Security tasks (vulnerability scans)
- `COMPAT-*` - Compatibility tasks (cross-platform, backwards compat)
- `PUB-*` - Publishing tasks (pre-publish, artifacts, verification)
- `UX-*` - User experience tasks (upgrade docs, screenshots)
- `RETRO-*` - Retrospective tasks (sprint retrospective, pattern extraction)

**Feature Task ID Prefixes** (use for generated tasks):
- `FEAT-*` - New features
- `AUTH-*` - Authentication features
- `API-*` - API endpoints
- `UI-*` - UI components (not to be confused with UX-* template tasks)
- `BUG-*` - Bug fixes
- `REFACTOR-*` - Refactoring tasks
- `[CUSTOM]-*` - Domain-specific prefixes (e.g., VOICE-*, DATA-*, SYNC-*)

**Validation:** Before adding feature tasks, ensure none use reserved template prefixes.

**Step 5: Merge Tasks**

```javascript
// Merge feature tasks with template tasks
const allTasks = {
  // Feature tasks (generated from requirements)
  ...featureTasks,

  // Template tasks (injected from SPRINT_TEMPLATE.toml)
  ...allTemplateTasks.reduce((acc, task) => {
    acc[task.id] = task;
    return acc;
  }, {})
};

// Example merged task list:
// - FEAT-001: Implement user authentication (feature)
// - FEAT-002: Add password reset flow (feature)
// - DOC-001: Update CHANGELOG.md (template-required)
// - DOC-002: Update README.md (template-required)
// - QA-001: Run ripple analysis (template-required)
// - PUB-001: Pre-publish validation (template-conditional, if publishing)
// - RETRO-001: Sprint retrospective (template-retrospective)
```

**Step 6: Generate Sprint TOML with Merged Tasks**

The final sprint TOML includes both feature and template tasks:

```toml
[metadata]
version = "1.0.0"
sprint_number = 1
status = "active"
# ... rest of metadata

# Feature tasks (from requirements)
[tasks.FEAT-001]
id = "FEAT-001"
name = "Implement user authentication"
status = "pending"
phase = "feature-development"
agent = "infrastructure-agent"
# ... rich format fields

[tasks.FEAT-002]
id = "FEAT-002"
name = "Add password reset flow"
status = "pending"
phase = "feature-development"
agent = "infrastructure-agent"
# ... rich format fields

# Template tasks (injected automatically)
[tasks.DOC-001]
id = "DOC-001"
name = "Update CHANGELOG.md with sprint changes"
status = "pending"
phase = "documentation"
agent = "documentation-agent"
# ... full template task definition

[tasks.QA-001]
id = "QA-001"
name = "Run ripple analysis for breaking changes"
status = "pending"
phase = "quality-assurance"
agent = "testing-agent"
# ... full template task definition

# ... all other template tasks (DOC-002 through DOC-005, QA-002 through QA-004, etc.)
# NOTE: DOC-005 is a REFACTORING task (context optimization, -500 lines estimated)

[tasks.RETRO-001]
id = "RETRO-001"
name = "Sprint retrospective"
status = "pending"
phase = "retrospective"
agent = "documentation-agent"
# ... full template task definition
```

#### Template Injection Summary

**Before Template Injection:**
- Feature tasks only: 5-10 tasks
- No quality assurance built in
- Easy to forget documentation, tests, retrospectives

**After Template Injection:**
- Feature tasks: 5-10 tasks
- Template tasks: 20-28 tasks (depending on conditions)
- Total: 25-38 tasks per sprint
- Quality assurance guaranteed
- Consistent sprint structure

**Benefits:**
- ✅ Never forget CHANGELOG updates
- ✅ Never skip test coverage checks
- ✅ Always include dependency audits
- ✅ Consistent retrospectives
- ✅ Automatic publishing checklists (when releasing)
- ✅ Built-in quality ratchet (prevents regression)

**Historical Bug Prevention:**
- DOC-001 (CHANGELOG) prevents undocumented releases (v0.13.29 issue)
- QA-003 (dependency audit) prevents native dep bugs (v0.13.23 issue)
- PUB-001 (pre-publish checklist) prevents version mismatch (v0.13.28 issue)
- INFRA-002 (sprint validation) prevents TOML format bugs (2025-11-03 issue)

**Total Time Saved:** 15+ hours of historical debugging prevented per sprint.

#### Example: Feature-Only Sprint

User: "Plan a sprint to build API endpoints for user management"

**Generated Feature Tasks:**
- API-001: Design user endpoints architecture
- API-002: Implement GET /users
- API-003: Implement POST /users
- API-004: Implement PUT /users/:id
- API-005: Implement DELETE /users/:id

**Injected Template Tasks (23 tasks):**
- REQUIRED (13): DOC-001 to DOC-004, QA-001 to QA-004, AGENT-001 to AGENT-002, INFRA-001 to INFRA-002, CONFIG-001
- SUGGESTED (4): PERF-001, SEC-001, COMPAT-001, COMPAT-002
- CONDITIONAL (0): No publishing keywords detected, no PUB-* tasks
- RETROSPECTIVE (2): RETRO-001, RETRO-002

**Total: 5 feature + 19 template = 24 tasks**

**Condition Detection:**
- isPublishing: false (no "release" or "publish" keywords)
- isUserFacing: false (API-only, no UI keywords)

#### Example: Release Sprint

User: "Plan a sprint to release v2.0 with UI redesign"

**Generated Feature Tasks:**
- UI-001: Redesign dashboard layout
- UI-002: Update theme system
- UI-003: Implement responsive design

**Injected Template Tasks (28 tasks):**
- REQUIRED (14): DOC-001 to DOC-005, QA-001 to QA-004, AGENT-001 to AGENT-002, INFRA-001 to INFRA-002, CONFIG-001
- SUGGESTED (4): PERF-001, SEC-001, COMPAT-001, COMPAT-002
- CONDITIONAL (8):
  - PUB-001 to PUB-005 (publishing detected: "release v2.0")
  - UX-001 to UX-003 (user-facing detected: "UI redesign")
- RETROSPECTIVE (2): RETRO-001, RETRO-002

**Total: 3 feature + 28 template = 31 tasks**

**Condition Detection:**
- isPublishing: true ("release" + "v2.0" keywords detected)
- isUserFacing: true ("UI" + "redesign" keywords detected)

#### SUGGESTED Task Handling

SUGGESTED tasks are included by default but can be skipped with written justification:

**User Prompt (during sprint creation):**
```
Template includes 4 SUGGESTED tasks:
- PERF-001: Performance regression testing
- SEC-001: Security vulnerability scan
- COMPAT-001: Cross-platform testing (Windows/Mac/Linux)
- COMPAT-002: Backwards compatibility check

These tasks are recommended but optional. Would you like to:
1. Include all suggested tasks (recommended)
2. Skip some tasks with justification

If skipping, please provide justification for each (e.g., "No performance-critical changes this sprint").
```

**If user skips with justification:**
```toml
# Add skip justification to sprint notes
[notes]
template_task_justifications = """
SUGGESTED Tasks Skipped:
- PERF-001: No performance-critical changes (API-only sprint)
- COMPAT-001: No platform-specific code changes
"""
```

**Justification examples:**
- "No performance-critical changes this sprint" (skip PERF-001)
- "Internal-only changes, no security risk" (skip SEC-001)
- "Pure TypeScript, no platform-specific code" (skip COMPAT-001)
- "No VS Code API changes, backwards compatible" (skip COMPAT-002)

### 3. Git Workflow Setup

#### For Each Epic/Feature:
```bash
# Create feature branch from master
git checkout master
git pull origin master
git checkout -b feature/[epic-name]

# Create sub-branches for phases
git checkout -b feature/[epic-name]/phase-1
```

#### Branch Naming Convention:
- `feature/[epic-name]` - Main feature branch
- `feature/[epic-name]/phase-[n]` - Phase branches
- `fix/[issue-name]` - Bug fix branches
- `refactor/[component-name]` - Refactoring branches

### 4. Generate Sprint Files

**CRITICAL: Sprint File Naming Convention**

Sprint files MUST follow this pattern to appear in the Sprint dropdown:

**Format:** `ACTIVE_SPRINT_[DESCRIPTOR].toml`

**Examples:**
- `ACTIVE_SPRINT_v0.15.4_UI_REFACTOR.toml` ✓ (version-based)
- `ACTIVE_SPRINT_2025-10-31.toml` ✓ (date-based)
- `ACTIVE_SPRINT_PHASE_1.toml` ✓ (phase-based)
- `ACTIVE_SPRINT_AUTH_FEATURE.toml` ✓ (feature-based)
- `ACTIVE_SPRINT.toml` ✓ (legacy format, still works)
- `sprint.toml` ✗ (won't appear in dropdown)

**Why:** The `ACTIVE_SPRINT` prefix is the identifier that makes it discoverable.
The descriptor after the underscore helps users identify which sprint is which.

**Location:** Place in `internal/sprints/` (ÆtherLight dev) or `sprints/` (user projects)

Create `sprints/ACTIVE_SPRINT_[DESCRIPTOR].toml`:

**CRITICAL: Use `[tasks.ID]` format (NOT `[[epic.*.tasks]]`)**
The SprintLoader expects flat task structure: `data.tasks[taskId]`

```toml
[meta]
sprint_name = "Sprint [Number]"
version = "[version]"
created = "YYYY-MM-DD"
status = "active"

# Tasks use flat structure: [tasks.TASK-ID]
[tasks.AUTH-001]
# REQUIRED FIELDS (5 fields - enforced by SprintSchemaValidator)
id = "AUTH-001"                    # Task ID (must match section key)
name = "Implement JWT tokens"      # Task name (NOT "title")
status = "pending"                 # Status: pending, in_progress, completed
phase = "authentication"           # Phase name
agent = "infrastructure-agent"     # Agent assignment (from AgentRegistry)

# COMMON OPTIONAL FIELDS (recommended for most tasks)
skill = "publish"                  # Optional: Automated workflow to use (see Step 3.6)
                                    # Only for tasks with automated workflows (publish, code-analyze, protect, etc.)
                                    # Omit for manual work (most tasks)
description = "Add JWT token generation and validation"
estimated_time = "4-6 hours"
estimated_lines = 300
dependencies = []                  # Array of task IDs this depends on
assigned_engineer = "engineer_1"
required_expertise = ["typescript", "security"]
deliverables = [
    "JWT token generation function",
    "Token validation middleware",
    "Unit tests for token operations"
]

# ERROR HANDLING (optional but strongly recommended - see template below)
error_handling = """
- Wrap JWT parsing in try-catch
- Handle expired token errors gracefully
- Validate token format before parsing
- Return clear error messages to user
"""
validation_criteria = [
    "All token operations have error boundaries",
    "Invalid tokens don't crash the app",
    "Clear error messages for auth failures"
]
```

### Minimal Valid Sprint (Backward Compatible)

For quick sprints or simple tasks, you only need the **5 required fields**:

```toml
[meta]
sprint_name = "Quick Bug Fix Sprint"
version = "1.0"
status = "active"
created = "2025-11-05"

[tasks.BUG-001]
id = "BUG-001"
name = "Fix login redirect"
status = "pending"
phase = "bugfix"
agent = "general-purpose"
```

This minimal format is **fully compatible** with the sprint system.

### Rich Sprint Format (Recommended for Complex Features)

For complex features, sprint tasks can include **rich metadata** for better context and tracking:

```toml
[tasks.FEATURE-001]
# REQUIRED FIELDS (always needed)
id = "FEATURE-001"
name = "Implement Enhanced Prompt Display"
status = "pending"
phase = "feature-development"
agent = "ui-agent"

# NARRATIVE FIELDS (helps understand WHY and context)
why = """
User expectation: Enhancement button should enhance text in-place.
Current state: Button disabled, function is empty stub.
Users frustrated by missing core feature.
"""

context = """
Feature was removed during v0.16.x refactoring to fix layout bugs.
PromptEnhancer.ts exists but not integrated with UI.
Pattern-UX-001 emphasizes real-time feedback for user actions.
"""

reasoning_chain = [
    "1. User types minimal prompt in text area",
    "2. Clicks ✨ enhancement button",
    "3. PromptEnhancer analyzes and enriches prompt with context",
    "4. Enhanced prompt replaces text in textarea (in-place)",
    "5. User reviews enhanced prompt before sending"
]

pattern_context = "Pattern-UX-001: Real-time feedback improves user experience by 50%"

success_impact = """
After FEATURE-001 complete:
✅ Enhancement button fully functional
✅ Users write better prompts with less effort
✅ Pattern-driven development workflow enabled
✅ User satisfaction increased (feature restoration)
"""

# TESTING FIELDS (TDD integration)
test_requirements = """
TDD Requirements (UI Task - 70% coverage):

RED Phase - Write tests FIRST:
1. enhancePrompt() called when ✨ button clicked
2. Original text replaced with enhanced text (in-place)
3. Enhancement completes in < 3 seconds
4. Error handling: API failures show user-friendly message
5. Keyboard shortcut: Ctrl+Shift+E triggers enhancement

GREEN Phase - Implement to pass tests
REFACTOR Phase - Optimize performance
"""

test_files = [
    "vscode-lumina/test/commands/enhancePrompt.test.ts",
    "vscode-lumina/test/services/PromptEnhancer.test.ts"
]

test_coverage_requirement = 0.7  # 70% for UI tasks

validation_criteria = [
    "✨ button enabled and clickable",
    "Click triggers PromptEnhancer.enhanceWithPatterns()",
    "Enhanced text replaces original in textarea",
    "Success notification shown",
    "Keyboard shortcut Ctrl+Shift+E works"
]

# PERFORMANCE & PATTERNS
performance_target = "Enhancement completes < 3 seconds"

patterns = [
    "Pattern-UX-001",       # Real-time feedback
    "Pattern-CONTEXT-002"   # Context enrichment
]

# FILE & DELIVERABLE TRACKING
estimated_lines = 150
estimated_time = "2-3 hours"

files_to_modify = [
    "vscode-lumina/src/commands/voicePanel.ts (line 1088-1112 - enhance button handler)"
]

files_to_create = [
    "vscode-lumina/test/commands/enhancePrompt.test.ts"
]

deliverables = [
    "Enable ✨ enhancement button (remove disabled attribute)",
    "Implement enhanceWithPatterns() function",
    "Show success notification after enhancement",
    "Add keyboard shortcut Ctrl+Shift+E",
    "Unit tests with 70% coverage"
]

# ERROR HANDLING (strongly recommended)
error_handling = """
- Wrap PromptEnhancer.enhance() in try-catch
- Handle API timeout errors (show "Enhancement timed out" message)
- Handle network errors gracefully
- Preserve original text on error (don't lose user input)
- Show actionable error messages with retry option
"""

# DEPENDENCIES (task ordering)
dependencies = []  # No dependencies, can start immediately
```

### Field Categories & When to Use

#### Required Fields (ALWAYS include)
- `id` - Task identifier
- `name` - Task name
- `status` - Current status (pending, in_progress, completed)
- `phase` - Phase name
- `agent` - Agent assignment (query AgentRegistry for available agents)

#### Narrative Fields (Use for: Complex features, team onboarding, architectural decisions)
- `why` - User pain point or business justification
- `context` - Background information, related systems, history
- `reasoning_chain` - Step-by-step logic flow (array)
- `pattern_context` - Link to architectural patterns
- `success_impact` - Measurable benefits after completion

#### Testing Fields (Use for: ALL production code)
- `test_requirements` - TDD requirements with RED/GREEN/REFACTOR phases
- `test_files` - Test file paths (array)
- `test_coverage_requirement` - Coverage percentage (0.7-0.9 by task type)
- `validation_criteria` - Acceptance criteria (array)

#### Performance & Pattern Fields (Use for: Infrastructure tasks, performance-critical features)
- `performance_target` - Target completion time or throughput
- `patterns` - Referenced patterns (array)

#### File & Deliverable Tracking (Use for: All tasks with concrete outputs)
- `estimated_lines` - Lines of code estimate
- `estimated_time` - Time estimate (e.g., "2-3 hours", "1-2 days")
- `files_to_modify` - Files to change (with line numbers for precision)
- `files_to_create` - New files (array)
- `deliverables` - Specific deliverables (array)

#### Error Handling (Use for: ALL tasks - learned from BUG-012)
- `error_handling` - Error boundaries and recovery strategies
- `validation_criteria` - Error validation checklist

#### Dependencies (Use for: Tasks with ordering requirements)
- `dependencies` - Array of task IDs that must complete first

### Enhanced Metadata Section

The `[metadata]` section can include rich sprint-level information:

```toml
[metadata]
# Basic metadata (always include)
version = "0.16.0"
sprint_number = 2
start_date = "2025-11-03"
target_completion = "2025-11-04"
status = "active"

# Focus areas (helps prioritize work)
[metadata.focus]
primary = "Fix critical UI bugs from v0.16.0 release"
secondary = "Stabilize voice panel and control panel"
tertiary = "Address console errors"

# Priority order (phase-by-phase priorities)
[metadata.priority_order]
phase_1 = "Bug Fixes - CRITICAL (blocks all features)"
phase_2 = "UI Architecture - Restructure layout hierarchy"
phase_3 = "Documentation - Update patterns and guides"

# Sprint progression (links to related sprints)
[metadata.progression]
previous_sprint = "archive/SPRINT_v0.15.4_UI_REFACTOR.toml"
next_sprint = "DOGFOODING_SPRINT.toml"
triggers_hotfix_release = true
git_branch = "feature/v0.16.1-ui-bugfix"

# Audit context (if sprint follows an audit)
[metadata.audit_context]
audit_file = "v0.16.0_AUDIT_RESULTS.md"
audit_score = "15/80 (19%)"
critical_bugs_found = 4

# Team information
[metadata.team]
team_size = 1
default_engineer = "engineer_1"

[[metadata.team.engineers]]
id = "engineer_1"
name = "BB_Aelor"
expertise = ["typescript", "vscode-extensions", "ui-ux"]
available_agents = ["infrastructure-agent", "ui-agent", "documentation-agent"]
max_parallel_tasks = 2
daily_capacity_hours = 8
```

### Progress Tracking Section

Add a `[progress]` section for sprint health monitoring:

```toml
[progress]
total_tasks = 22
completed_tasks = 5
in_progress_tasks = 1
pending_tasks = 16
completion_percentage = 23
```

**Note:** Progress fields can be auto-calculated or manually updated as sprint progresses.

### Notes Section

Add a `[notes]` section for strategic documentation:

```toml
[notes]
dogfooding_strategy = """
Release early, fix fast via patches.
- v0.16.0: Initial release with SYNC-001
- v0.16.1: UI bug fixes (this sprint)
- v0.16.2: Enhancement restoration
"""

priority_order = """
1. UI-001, UI-002 (button functionality - blocking workflow)
2. UI-003 (resize - UX issue)
3. UI-004, UI-005 (visual cleanup)
"""

retrospective = """
Lessons learned:
- Pattern-based refactoring works but needs careful testing
- UI changes require comprehensive visual validation
- Dogfooding catches bugs early
"""
```

### Task Category Coverage Requirements

Different task categories have different test coverage requirements:

| Task Category | Coverage Required | Test Type |
|---------------|-------------------|-----------|
| Infrastructure | 90% | Unit tests, integration tests |
| API | 85% | Endpoint tests, error case tests |
| UI | 70% | Component tests, user interaction tests |
| Documentation | 0% | Manual review only |

**When generating sprints:**
- Set `test_coverage_requirement` based on task category
- Infrastructure tasks: Focus on performance (<500ms targets)
- API tasks: Include all error scenarios (400, 401, 404, 500)
- UI tasks: Include visual validation criteria
- Documentation tasks: No automated tests, manual validation

### Agent Selection Guide

Choose appropriate agents based on task type:

| Task Type | Recommended Agent | Expertise |
|-----------|------------------|-----------|
| Service architecture, middleware | `infrastructure-agent` | TypeScript services, orchestration |
| UI components, layouts, styling | `ui-agent` | React, HTML/CSS, user experience |
| REST APIs, GraphQL, endpoints | `api-agent` | API design, error handling |
| Patterns, guides, README | `documentation-agent` | Technical writing, examples |
| Native desktop features | `tauri-desktop-agent` | Rust, Tauri, OS integration |
| Bug fixes (any category) | `general-purpose` | Cross-functional debugging |

**How to query available agents:**
- Agents defined in `internal/agents/[agent]-context.md`
- AgentRegistry loads agents at runtime
- Check agent expertise before assigning complex tasks

### When to Use Rich vs Minimal Format

**Use Minimal Format (5 required fields)** when:
- ✅ Quick bug fixes (< 1 hour)
- ✅ Simple documentation updates
- ✅ Experimental/spike work
- ✅ Personal learning exercises
- ✅ Prototyping without production intent

**Use Rich Format (all metadata)** when:
- ✅ Complex features (> 4 hours)
- ✅ Team collaboration (multiple engineers)
- ✅ Architectural changes
- ✅ Production code requiring tests
- ✅ Features with user-facing impact
- ✅ Work requiring future maintenance

**Rich format benefits:**
- 📚 Context preserved for future developers
- 🎯 Clear success criteria and validation
- 🔗 Links to patterns and architecture
- 📊 Performance targets defined upfront
- 🧪 TDD integrated from the start
- 📝 Deliverables explicitly tracked

### Complete Sprint Example

Here's a complete example showing both minimal and rich tasks:

```toml
[metadata]
version = "1.0.0"
sprint_number = 1
start_date = "2025-11-05"
target_completion = "2025-11-12"
status = "active"

[metadata.focus]
primary = "Launch core authentication feature"
secondary = "Stabilize user management"
tertiary = "Documentation updates"

[metadata.team]
team_size = 2
default_engineer = "engineer_1"

[[metadata.team.engineers]]
id = "engineer_1"
expertise = ["typescript", "react", "node"]
available_agents = ["infrastructure-agent", "ui-agent"]
max_parallel_tasks = 2

# MINIMAL TASK (quick bug fix)
[tasks.BUG-001]
id = "BUG-001"
name = "Fix login redirect loop"
status = "pending"
phase = "bugfix"
agent = "general-purpose"

# RICH TASK (complex feature)
[tasks.AUTH-001]
id = "AUTH-001"
name = "Implement JWT Authentication"
status = "pending"
phase = "authentication"
agent = "infrastructure-agent"

why = """
Users need secure authentication to access protected resources.
Current state: No authentication system, all endpoints public.
Security risk: Data exposure without access control.
"""

context = """
Industry standard: JWT tokens for stateless authentication.
Pattern-SECURITY-001 emphasizes defense in depth.
Integration required with existing user database.
"""

reasoning_chain = [
    "1. User submits credentials (email + password)",
    "2. Server validates against database (bcrypt hash)",
    "3. Generate JWT token with user ID and roles",
    "4. Return token to client (httpOnly cookie)",
    "5. Client includes token in subsequent requests",
    "6. Middleware validates token on protected routes"
]

pattern_context = "Pattern-SECURITY-001: Defense in depth, Pattern-AUTH-002: JWT best practices"

success_impact = """
After AUTH-001 complete:
✅ Secure authentication system protecting user data
✅ Token-based access control for all endpoints
✅ Password hashing with bcrypt (industry standard)
✅ XSS protection via httpOnly cookies
"""

test_requirements = """
TDD Requirements (Infrastructure Task - 90% coverage):

RED Phase - Write tests FIRST:
1. generateToken(userId) returns valid JWT
2. validateToken(token) returns user object
3. validateToken(expiredToken) throws error
4. validateToken(invalidToken) throws error
5. Password hashing with bcrypt (verify salt rounds >= 10)
6. Login endpoint returns 401 for invalid credentials
7. Protected endpoint returns 403 without token

GREEN Phase - Implement to pass tests
REFACTOR Phase - Optimize token generation performance
"""

test_files = [
    "backend/test/auth/jwt.test.ts",
    "backend/test/middleware/auth.test.ts"
]

test_coverage_requirement = 0.9

validation_criteria = [
    "All auth operations have error boundaries",
    "Tokens expire after 24 hours",
    "Password never stored in plain text",
    "Login endpoint rate-limited (5 attempts/min)",
    "Protected endpoints require valid token"
]

performance_target = "Token validation < 50ms"

patterns = ["Pattern-SECURITY-001", "Pattern-AUTH-002"]

estimated_lines = 500
estimated_time = "8-10 hours"

files_to_create = [
    "backend/src/auth/jwt.ts",
    "backend/src/middleware/auth.ts",
    "backend/test/auth/jwt.test.ts"
]

files_to_modify = [
    "backend/src/routes/user.ts (lines 15-30 - add auth middleware)"
]

deliverables = [
    "JWT token generation function",
    "Token validation middleware",
    "Password hashing utility (bcrypt)",
    "Login endpoint (/api/auth/login)",
    "Protected route example",
    "Unit tests (90% coverage)"
]

error_handling = """
- Wrap JWT operations in try-catch
- Handle malformed tokens gracefully
- Handle expired tokens with 401 status
- Rate limit login attempts (prevent brute force)
- Log authentication failures for security audit
"""

dependencies = []

[progress]
total_tasks = 2
completed_tasks = 0
in_progress_tasks = 0
pending_tasks = 2
completion_percentage = 0
```

### 5. Enforce Workflow Rules

#### Development Flow:
1. **Work in feature branch** (never in master)
2. **Commit frequently** with semantic messages
3. **Create PR** when phase complete
4. **Review required** before merge
5. **Merge to master** only after approval
6. **Tag releases** after sprint completion

### 6. Integration with User Context

The skill combines:
- **User Intent**: What they describe wanting
- **Codebase Analysis**: Current state and patterns
- **Best Practices**: Enforced workflows
- **Team Context**: Roles and capabilities

## Command Execution

```bash
# 1. Initialize sprint structure
mkdir -p sprints
cd sprints

# 2. Create sprint file
cat > SPRINT_$(date +%Y%m%d).toml << 'EOF'
[Generated TOML content]
EOF

# 3. Create Git branches
git checkout -b feature/[epic-name]
git push -u origin feature/[epic-name]

# 4. Create phase branches
for phase in 1 2 3; do
  git checkout -b feature/[epic-name]/phase-$phase
  git push -u origin feature/[epic-name]/phase-$phase
done

# 5. Switch back to first phase
git checkout feature/[epic-name]/phase-1
```

## Sprint Lifecycle

### Phase 1: Planning (This Skill)
- Requirements gathering
- Sprint file generation
- Branch creation
- Task assignment

### Phase 2: Development
- Work in phase branches
- Regular commits
- Progress tracking

### Phase 3: Review
- PR creation
- Code review
- Testing

### Phase 4: Merge
- Merge to feature branch
- Integration testing
- Merge to master

### Phase 5: Release
- Use `/publish` skill
- Tag release
- Deploy

## Protection Rules

### What Can Be Modified:
- **New files** in feature branches
- **New functions** in existing files
- **Tests** for new features
- **Documentation** updates

### What Cannot Be Modified (in master):
- **Existing function signatures**
- **Core algorithms**
- **API contracts**
- **Database schemas**

### Refactoring Rules:
- Must create `refactor/[name]` branch
- Must maintain existing interfaces
- Must pass all existing tests
- Must be reviewed before merge

## Example Usage

User: "Plan a 2-week sprint for adding voice commands to our app"

Claude:
1. Creates `SPRINT_20251030.toml` with voice feature epic
2. Creates branches:
   - `feature/voice-commands`
   - `feature/voice-commands/phase-1` (setup)
   - `feature/voice-commands/phase-2` (implementation)
   - `feature/voice-commands/phase-3` (testing)
3. Generates tasks with assignments
4. Sets up PR templates
5. Configures branch protection

## Integration Points

- **Code Analyzer**: Runs on each PR
- **Initialize**: Sets up new repos
- **Publish**: Releases completed sprints
- **Voice Panel**: Captures requirements

## Success Criteria

Sprint planning succeeds when:
- [ ] Sprint file created with clear structure
- [ ] All branches created and pushed
- [ ] Tasks assigned with estimates
- [ ] Workflow documented
- [ ] Team understands process
- [ ] **ERROR HANDLING VERIFIED:**
  - [ ] Every task includes error_handling section
  - [ ] All parsing operations have try-catch requirements
  - [ ] File operations have error boundaries defined
  - [ ] API calls have timeout and retry logic
  - [ ] User-facing errors have clear messages
  - [ ] No task can crash the entire application

## Error Handling Template for Tasks

**STRONGLY RECOMMENDED** (optional field, but critical for production code):

```toml
[tasks.TASK-ID]
id = "TASK-ID"
name = "Task Name"
# ... other required fields ...

# ERROR HANDLING (optional but strongly recommended)
error_handling = """
Best practices for ALL production tasks:
1. Identify failure points:
   - [ ] List all parsing operations
   - [ ] List all file I/O operations
   - [ ] List all API/network calls
   - [ ] List all user input validations

2. Implement error boundaries:
   - [ ] Wrap in try-catch blocks
   - [ ] Log errors appropriately
   - [ ] Show user-friendly messages
   - [ ] Provide recovery options

3. Prevent cascade failures:
   - [ ] Errors isolated to component
   - [ ] Application continues functioning
   - [ ] No corruption of state
"""

validation_criteria = [
    "No unhandled exceptions possible",
    "All errors logged with context",
    "User sees actionable error messages",
    "Application remains stable after errors"
]
```

## Reference: BUG-012 Incident

**NEVER AGAIN:** A simple duplicate ID crashed entire VS Code for 9+ hours.

Requirements added after BUG-012:
- Every TOML parse MUST have try-catch
- Every file read MUST handle missing files
- Every JSON parse MUST validate structure
- Extension MUST work without config files
- Errors MUST NOT propagate to VS Code core

---

## ENHANCE Mode Workflow

**Use this workflow when adding tasks to an existing sprint.**

### Step 1: Identify Target Sprint

If multiple sprint files exist:
```bash
ls internal/sprints/ACTIVE_SPRINT*.toml
```

Ask user which sprint to enhance (if multiple exist).

**Target:** `internal/sprints/ACTIVE_SPRINT_[DESCRIPTOR].toml`

### Step 2: Read Existing Sprint

Read the target sprint file to understand:
- Current task IDs and naming pattern
- Existing phases
- Current [progress] section
- Metadata (version, status, etc.)

```bash
cat internal/sprints/ACTIVE_SPRINT_v0.16.0.toml
```

**Critical:** Understand the ID pattern:
- RELEASE-001, RELEASE-002 → Release tasks
- UI-001, UI-002 → UI tasks
- BUG-001, BUG-002 → Bug fixes
- REFACTOR-001, REFACTOR-002 → Refactoring tasks

### Step 3: Generate New Tasks

Based on user requirements, generate new tasks following the sprint's existing patterns:

**Required fields (MANDATORY - 5 fields):**
- `id` - Continue the ID pattern (e.g., if RELEASE-007 exists, next is RELEASE-008)
- `name` - Task name
- `status` - Usually "pending" for new tasks
- `phase` - Match existing phases or create new one
- `agent` - Appropriate agent from AgentRegistry

**Optional fields** (use rich format for complex tasks):
- `description`, `why`, `context`, `reasoning_chain`
- `test_requirements`, `test_files`, `test_coverage_requirement`
- `estimated_time`, `estimated_lines`
- `deliverables`, `files_to_create`, `files_to_modify`
- `error_handling`, `validation_criteria`
- `dependencies` - Reference existing task IDs if dependent

**Example new task:**
```toml
[tasks.RELEASE-001]
id = "RELEASE-001"
name = "Verify sprint-plan skill enhancements"
status = "pending"
phase = "release"
agent = "infrastructure-agent"
estimated_time = "1-2 hours"
dependencies = []
deliverables = [
    "Sprint-plan skill has ENHANCE mode",
    "ENHANCE mode tested with current sprint",
    "Documentation updated"
]
```

### Step 3.5: MANDATORY Agent Validation (CRITICAL - DO NOT SKIP)

**STOP. Before proceeding to Step 4, you MUST validate agent assignments.**

**Why this is critical:**
- Wrong agent = Wrong context loaded = Wrong patterns applied = Bugs
- Historical evidence: UX tasks wrongly assigned to infrastructure-agent (this conversation)
- Impact: Agent can't execute task properly with mismatched expertise

**Validation Process (Answer OUT LOUD):**

For EACH new task, complete this checklist:

```
Task: [TASK-ID] - [Task Name]

1. ✅ What is the task category?
   - [ ] UI/UX (components, layouts, styling, state management, user interactions)
   - [ ] Infrastructure (middleware, services, orchestration, CI/CD)
   - [ ] API (REST endpoints, GraphQL, error handling)
   - [ ] Documentation (patterns, guides, README)
   - [ ] Database (schemas, migrations, queries)
   - [ ] Testing (test infrastructure, test patterns)

2. ✅ What are the key task indicators?
   Extract keywords from task name + description:
   - UI keywords: "component", "layout", "CSS", "state", "resize", "focus", "click", "paste", "persistence", "text area", "button", "modal", "webview"
   - Infrastructure keywords: "service", "middleware", "orchestration", "pipeline", "publishing", "deployment"
   - API keywords: "endpoint", "REST", "GraphQL", "HTTP", "authentication"

3. ✅ Query Agent Selection Guide (line 470-482):
   | Task Type | Recommended Agent |
   |-----------|------------------|
   | Service architecture, middleware | infrastructure-agent |
   | UI components, layouts, styling | ui-agent |
   | REST APIs, GraphQL, endpoints | api-agent |
   | Patterns, guides, README | documentation-agent |
   | Native desktop features | tauri-desktop-agent |
   | Bug fixes (any category) | general-purpose |

4. ✅ Verify agent context file (internal/agents/{agent}-context.md):
   Read the agent's responsibilities section to confirm capability match.

   Example:
   - ui-agent-context.md line 14-19:
     * Create React components (TypeScript)
     * Implement responsive layouts (CSS, Tailwind)
     * Handle user interactions (events, state)
     * Ensure accessibility (WCAG 2.1 AA)

   Does the agent have the required capabilities? YES/NO

5. ✅ Final verification:
   - Task category matches agent specialization? YES/NO
   - Agent context confirms capability? YES/NO
   - If NO to either: CORRECT THE AGENT NOW
```

**Common Agent Assignment Mistakes:**

❌ **DON'T assign to infrastructure-agent:**
- UI state management (localStorage persistence) → ui-agent
- CSS changes (resize handles, layouts) → ui-agent
- User interaction handlers (click, paste, focus) → ui-agent
- Webview rendering logic → ui-agent
- Component state (React hooks, context) → ui-agent

❌ **DON'T assign to ui-agent:**
- VS Code API middleware services → infrastructure-agent
- Service orchestration (multi-service workflows) → infrastructure-agent
- Publishing automation → infrastructure-agent
- CI/CD pipelines → infrastructure-agent
- Backend API logic → api-agent

**Example Validation (UX Task):**

```
Task: UX-014 - Make Ctrl+Enter work globally (not just in text area)

1. Task category: UI/UX (user interaction, keyboard shortcut)
2. Keywords: "Ctrl+Enter", "keyboard", "focus", "text area", "send to terminal"
3. Agent Selection Guide: UI components/layouts/styling → ui-agent
4. Agent context (ui-agent-context.md): "Handle user interactions (events, state)" ✓
5. Final verification:
   - UI category matches ui-agent? YES ✓
   - Agent has keyboard event handling capability? YES ✓
   - Assigned agent: ui-agent ✓
```

**If you skip this step, you WILL assign wrong agents (proven by this conversation).**

### Step 3.6: MANDATORY Skill Assignment (Autonomous Execution)

**STOP. Before proceeding to Step 4, you MUST check if tasks need skill assignments.**

**Why this is critical:**
- Agent = Expertise/context (WHO has the knowledge to execute)
- Skill = Automated workflow (WHAT workflow/automation to use)
- Without skill: Task is manual, agent must implement from scratch
- With skill: Task uses built-in automation (e.g., Pattern-PUBLISH-001 for publishing)

**Validation Process (Answer OUT LOUD):**

For EACH new task, complete this checklist:

```
Task: [TASK-ID] - [Task Name]

1. ✅ Does this task match an automated workflow?
   Check task name and description for keywords:
   - Publishing/releasing keywords: "publish", "release", "npm", "GitHub release", "version bump"
   - Code analysis keywords: "analyze", "audit", "scan", "complexity", "technical debt"
   - Protection keywords: "protect", "annotate", "@protected", "@immutable"
   - Sprint planning keywords: "sprint plan", "create sprint", "enhance sprint"
   - Validation keywords: "validate protection", "pre-commit", "hook"

2. ✅ Query Available Skills (from .claude/skills/):

   | Skill Name | Purpose | When to Use |
   |-----------|---------|-------------|
   | `publish` | Publishing releases (npm + GitHub) | Task involves version bumping, npm publish, or GitHub releases |
   | `code-analyze` | Codebase analysis and pattern detection | Task involves analyzing code, detecting patterns, or complexity metrics |
   | `protect` | Code protection annotation | Task involves annotating code with @protected/@immutable |
   | `protection-audit` | Protection system audit | Task involves auditing protection system, generating reports |
   | `sprint-plan` | Sprint creation and enhancement | Task involves creating new sprints or adding tasks to existing sprints |
   | `validate-protection` | Protection enforcement validation | Task involves validating protection enforcement via pre-commit hooks |

3. ✅ Decision Tree:
   - Does task name contain "Publish" or "Release"? → skill = "publish"
   - Does task involve code analysis or audit? → skill = "code-analyze"
   - Does task involve protecting code? → skill = "protect"
   - Does task involve sprint planning? → skill = "sprint-plan"
   - Does task involve protection validation? → skill = "validate-protection" or "protection-audit"
   - No match? → Omit skill field (most tasks are manual work)

4. ✅ Verify skill exists:
   Skill file location: .claude/skills/{skill-name}/SKILL.md
   - Does the skill file exist? YES/NO
   - Does the skill description match the task? YES/NO

5. ✅ Final verification:
   - Task matches automated workflow pattern? YES/NO
   - Skill exists and matches task? YES/NO
   - If YES to both: Add `skill = "{skill-name}"` to task
   - If NO: Omit skill field (manual task, agent implements from scratch)
```

**Common Skill Assignment Patterns:**

✅ **DO assign skill for automated workflows:**
- "Publish v0.16.7" → skill = "publish" (uses Pattern-PUBLISH-001)
- "Analyze codebase for complexity" → skill = "code-analyze"
- "Annotate passing code with @protected" → skill = "protect"
- "Create sprint for Phase 4" → skill = "sprint-plan"
- "Validate protection enforcement" → skill = "validate-protection"

❌ **DON'T assign skill for manual work:**
- "Fix bug in TaskStarter.ts" → No skill (manual coding)
- "Implement new UI component" → No skill (manual React development)
- "Write unit tests for ConfigGenerator" → No skill (manual test writing)
- "Update documentation for config schema" → No skill (manual documentation)

**Example Validation (Publishing Task):**

```
Task: PATCH-001 - Publish v0.16.7

1. Automated workflow match: YES ✓
   Keywords: "Publish", "v0.16.7" (version number)

2. Available Skills: Check "publish" skill
   - Purpose: Publishing releases (npm + GitHub)
   - When to Use: Task involves version bumping, npm publish, or GitHub releases
   - Match? YES ✓

3. Decision Tree: Task name contains "Publish" → skill = "publish" ✓

4. Verify skill exists:
   - .claude/skills/publish/SKILL.md exists? YES ✓
   - Skill description matches task? YES ✓ (automates npm publish + GitHub release)

5. Final verification:
   - Task matches automated workflow? YES ✓ (publishing is automated)
   - Skill exists and matches? YES ✓
   - Assigned skill: skill = "publish" ✓
```

**Example Validation (Manual Task):**

```
Task: PROTECT-000C - Implement 'Start This Task' with prompt generation

1. Automated workflow match: NO ✗
   Keywords: "Implement", "prompt generation" (custom coding)

2. Available Skills: No match
   - Not publishing (no skill = "publish")
   - Not analyzing (no skill = "code-analyze")
   - Not protecting (no skill = "protect")
   - Custom feature development

3. Decision Tree: No automated workflow match → Omit skill field ✓

4. Verify: Manual coding task, agent implements from scratch

5. Final verification:
   - Task matches automated workflow? NO ✗
   - Omit skill field: YES ✓ (manual work, no automation)
   - agent = "infrastructure-agent" (has expertise)
   - skill = (omitted) (manual implementation)
```

**Key Distinction:**

```toml
# Example 1: Automated workflow (has skill)
[tasks.PATCH-001]
id = "PATCH-001"
name = "Publish v0.16.7"
agent = "infrastructure-agent"  # WHO: Has publishing expertise
skill = "publish"                # WHAT: Use automated publish workflow
```

```toml
# Example 2: Manual work (no skill)
[tasks.PROTECT-000C]
id = "PROTECT-000C"
name = "Implement 'Start This Task' with prompt generation"
agent = "infrastructure-agent"  # WHO: Has infrastructure expertise
# skill = (omitted)              # WHAT: Manual implementation (no automation)
```

**If you skip this step, tasks won't know which automated workflow to use (incomplete autonomous execution).**

### Step 4: Update [progress] Section

Recalculate progress based on ALL tasks (existing + new):

```toml
[progress]
total_tasks = 30  # Old total (23) + new tasks (7)
completed_tasks = 22  # Keep existing completed count
in_progress_tasks = 1  # Update if changed
pending_tasks = 7  # Old pending (1) + new tasks (7)
completion_percentage = 73  # (22 / 30) * 100
```

**Formula:** `completion_percentage = (completed_tasks / total_tasks) * 100`

**CRITICAL:** The [progress] section must reflect actual task counts, not stale values.

### Step 5: Update Metadata (if needed)

Update version if sprint version changed:
```toml
[metadata]
version = "0.16.7"  # Update if user specified new version
# ... rest of metadata stays the same
```

**Note:** Only update metadata if user explicitly requests version change. Otherwise, preserve existing metadata.

### Step 6: Update Task Dependencies

If new tasks depend on existing tasks, update the dependencies array:

```toml
[tasks.PATCH-001]
id = "PATCH-001"
name = "Publish v0.16.7"
status = "pending"
phase = "release"
agent = "infrastructure-agent"
dependencies = ["RELEASE-001", "RELEASE-002", "RELEASE-003", "RELEASE-004", "RELEASE-005", "RELEASE-006", "RELEASE-007"]
```

**Validation:** Ensure no circular dependencies (A depends on B, B depends on A).

### Step 7: Validate TOML

Before writing, validate the enhanced TOML:

**Required checks:**
1. ✅ All new tasks use `[tasks.TASK-ID]` format (NOT `[[epic.*.tasks]]`)
2. ✅ All 5 required fields present (id, name, status, phase, agent)
3. ✅ Task IDs unique (no duplicates with existing tasks)
4. ✅ Dependencies reference valid task IDs
5. ✅ No circular dependencies
6. ✅ Progress calculations correct
7. ✅ TOML syntax valid (no template literals `${}` in strings)
8. ✅ ID consistency: `[tasks.FOO-001]` must have `id = "FOO-001"`

**Validation command:**
```bash
node scripts/validate-sprint-schema.js
```

If validation script doesn't exist, use manual TOML parse:
```bash
node -e "const toml = require('@iarna/toml'); toml.parse(require('fs').readFileSync('internal/sprints/ACTIVE_SPRINT.toml', 'utf-8')); console.log('✅ TOML valid');"
```

### Step 8: Write Enhanced Sprint

Write the enhanced sprint TOML to the same file:

**CRITICAL:** Follow Pre-Flight Checklist from CLAUDE.md before editing ACTIVE_SPRINT.toml:
1. ✅ Read SprintLoader.ts:292-333 to verify parser format
2. ✅ Check existing task in sprint for format example
3. ✅ Validate required fields present
4. ✅ Check for template literals in code examples (replace with string concatenation)
5. ✅ Validate TOML will parse

```bash
# Backup original (safety)
cp internal/sprints/ACTIVE_SPRINT_v0.16.0.toml internal/sprints/ACTIVE_SPRINT_v0.16.0.toml.bak

# Use Edit tool to add new tasks to existing sprint file
# Preserve ALL existing tasks and metadata
# Add new tasks at appropriate location (usually at end, or in logical phase grouping)
```

**Important:** Use Edit tool, NOT Write tool, to preserve existing content.

### Step 9: Git Workflow

**If on master branch:**
- Warn user (should be on feature branch)
- Ask if they want to create feature branch

**If on feature branch:**
- Commit enhanced sprint with descriptive message

```bash
git add internal/sprints/ACTIVE_SPRINT_v0.16.0.toml
git commit -m "enhance(sprint): add 7 release validation tasks

- RELEASE-001: Verify sprint-plan skill enhancements
- RELEASE-002: Document Sprint Planner UI state
- RELEASE-003: Verify sub-package publication
- RELEASE-004: Update repository README
- RELEASE-005: Update npm package docs
- RELEASE-006: Update CHANGELOG
- RELEASE-007: Pre-publish audit

Updated PATCH-001 dependencies to include all RELEASE tasks.
Updated progress: 22/30 complete (73%).
"
```

### Step 10: Output Summary

Show user what was added:

```
✅ Sprint Enhanced Successfully

Target: internal/sprints/ACTIVE_SPRINT_v0.16.0.toml

New Tasks Added:
- RELEASE-001: Verify sprint-plan skill enhancements (pending)
- RELEASE-002: Document Sprint Planner UI state (pending)
- RELEASE-003: Verify sub-package publication (pending)
- RELEASE-004: Update repository README (pending)
- RELEASE-005: Update npm package documentation (pending)
- RELEASE-006: Update CHANGELOG and release notes (pending)
- RELEASE-007: Pre-publish audit (pending)

Updated Existing Tasks:
- PATCH-001: Added dependencies on RELEASE-001 through RELEASE-007

Progress:
- Before: 22/23 tasks (95.7%)
- After: 22/30 tasks (73.3%)
- Status: 7 new pending tasks added

Next Steps:
1. Review the enhanced sprint file
2. Start working on RELEASE-001
3. Use TodoWrite to track release tasks
```

## ENHANCE Mode Success Criteria

Sprint enhancement succeeds when:
- [ ] Existing tasks preserved exactly (no modifications unless explicitly requested)
- [ ] New tasks follow existing ID pattern
- [ ] All 5 required fields present in new tasks
- [ ] [progress] section recalculated correctly
- [ ] No TOML validation errors (run validation script)
- [ ] Git commit includes clear change summary
- [ ] User sees summary of what was added
- [ ] Sprint remains loadable by SprintLoader.ts
- [ ] SprintLoader.findAvailableSprints() still finds the sprint
- [ ] No duplicate task IDs between existing and new tasks

---

## Mode Comparison

| Aspect | CREATE Mode | ENHANCE Mode |
|--------|-------------|--------------|
| **When to use** | New sprint from scratch | Add tasks to existing sprint |
| **User says** | "plan sprint", "create sprint" | "add tasks", "enhance sprint" |
| **Input** | User requirements, goals | Existing sprint + new tasks |
| **Output** | New `ACTIVE_SPRINT_*.toml` file | Updated existing sprint file |
| **Git workflow** | Create feature branch + commit | Commit to current branch |
| **Validation** | Standard TOML validation | + Check for duplicate IDs |
| **Progress** | Calculate from new tasks | Recalculate with existing + new |
| **Complexity** | Higher (full sprint structure) | Lower (add tasks only) |

---

## Tips for Both Modes

1. **Always validate TOML** before committing (prevents BUG-012 style crashes)
2. **Follow existing patterns** when adding tasks (consistency matters)
3. **Use rich format for complex tasks** (>4 hours, production code)
4. **Use minimal format for quick tasks** (<1 hour, simple changes)
5. **Assign appropriate agents** (query AgentRegistry for expertise match)
6. **Add error handling** to every task (learned from BUG-012)
7. **Update [progress] accurately** (users rely on this for sprint health)
8. **Git commit with clear messages** (future debugging depends on this)