# Pattern-SPRINT-PLAN-001: Sprint Planning Protocol

**CREATED:** 2025-11-08
**CATEGORY:** Workflow Protocol
**LANGUAGE:** JavaScript
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-CODE-001, PATTERN-TRACKING-001, PATTERN-IMPROVEMENT-001

---


## Problem

Creating sprints without proper foundation leads to:
- Sprints created with incomplete context (missing workspace analysis)
- Git conflicts from uncommitted work blocking sprint start
- Missing agents causing task assignment failures
- Sprints that don't align with user expectations
- Rework due to unclear requirements

**Without this protocol:**
- No validation that workspace is analyzed
- No check that agents are available for assignment
- User doesn't review plan before creation → Misaligned expectations
- Time wasted on sprints that need immediate revision

---

## Solution

**MANDATORY: Run workflow check BEFORE creating ANY sprint**

This protocol ensures workspace analysis is complete, git state is clean, agents are available, and user approves the plan before committing to sprint implementation.

---

## When to Use

- Before creating new sprint TOML file
- Before modifying ACTIVE_SPRINT.toml
- When user requests "create sprint" or "plan sprint"

---

## Workflow Check Template

```
🔍 Sprint Planning Workflow Check
================================================================

Prerequisites:
✅ Workspace analyzed: Context gathered from codebase
✅ Git status: Clean working directory
✅ Agent Registry: 9 agents loaded from internal/agents/
✅ Patterns available: 15 patterns loaded from docs/patterns/
✅ Skill system: AgentRegistry initialized

Gaps: None

Critical Junction: YES (Always ask user to review sprint plan before creating)

Plan:
1. Analyze user requirements
2. Break down into phases and tasks
3. Assign agents to tasks based on expertise
4. Estimate time and complexity
5. Generate sprint TOML
6. Show plan to user for approval
7. Create feature branch (if approved)
8. Commit sprint file

Ready to proceed (will pause for user approval before creating sprint)
```

---

## Communication Template

Before creating sprint, Claude MUST announce:

### 1. Workspace Analysis Status
```
Workspace Analysis: COMPLETE ✅

Code Structure:
- Main extension: vscode-lumina/src/ (TypeScript)
- Sub-packages: packages/aetherlight-{analyzer,sdk,node}/
- Tests: vscode-lumina/test/ (Mocha/Chai)
- Patterns: docs/patterns/ (77 patterns)

Dependencies:
- VS Code API: ^1.80.0
- TypeScript: 5.3.3
- Node.js: >=18.0.0

Tech Stack Confirmed: TypeScript + VS Code Extension + Tauri Desktop
```

### 2. Git Repository Status
```
Git Status: Clean ✅

Current Branch: master
Uncommitted Changes: None
Unpushed Commits: None
Remote: origin (github.com/Ferret9/lumina-clean)

Ready to create feature branch: feature/license-dashboard
```

### 3. Available Agents and Skills
```
Agent Registry: 9 agents loaded ✅

Available Agents:
- infrastructure-agent (service orchestration, TypeScript)
- api-agent (endpoints, routes, middleware)
- ui-agent (components, views, interactions)
- docs-agent (patterns, guides, documentation)
- security-agent (auth, encryption, validation)
- performance-agent (optimization, caching)
- data-agent (database, schema, migrations)
- test-agent (TDD, coverage, integration tests)
- devops-agent (CI/CD, deployment, monitoring)

Skill System: AgentRegistry initialized ✅
Pattern Library: 77 patterns indexed ✅
```

### 4. Sprint Scope and Estimated Timeline
```
Sprint Scope: License Key Dashboard Implementation

Goal: Build web dashboard for license key generation and management

Phases:
1. Foundation (database, schema, API client) - 3-5 days
2. Backend API (endpoints, validation, security) - 4-6 days
3. Frontend UI (dashboard, components, forms) - 5-7 days
4. Testing & Deployment (integration, E2E, CI/CD) - 2-3 days

Total Estimated Duration: 14-21 days (2-3 weeks)

Success Criteria:
✅ Users can sign up and generate license keys
✅ License keys displayed with copy-to-clipboard
✅ Admin panel for key management
✅ Secure authentication and encryption
✅ Integration with VS Code + Desktop apps
```

### 5. **ASK USER** to Review Plan Before Proceeding

**CRITICAL:** Sprint planning is ALWAYS a critical junction

**Why:**
- High-impact operation (affects entire sprint workflow)
- User needs to review and approve plan
- May need adjustments based on priorities
- Prevents wasted work on misaligned sprints

**Use AskUserQuestion tool:**
```javascript
AskUserQuestion({
  questions: [{
    question: "Review this sprint plan. Does it match your expectations?",
    header: "Sprint Review",
    multiSelect: false,
    options: [
      {
        label: "Approve and create",
        description: "Plan looks good. Create sprint TOML and feature branch."
      },
      {
        label: "Modify plan",
        description: "Plan needs adjustments. Let's revise before creating."
      },
      {
        label: "Cancel",
        description: "Not ready for this sprint yet. Skip for now."
      }
    ]
  }]
})
```

---

## Prerequisites Checklist

### 1. Workspace Analyzed ✅

**Check:**
```
- Code structure mapped (directories, files, patterns)
- Dependencies identified (package.json analyzed)
- Existing patterns cataloged (docs/patterns/ indexed)
- Tech stack confirmed (TypeScript, VS Code API, Node.js versions)
```

**How to Verify:**
```bash
# Check workspace structure
ls -la vscode-lumina/src/
ls -la packages/

# Check dependencies
cat vscode-lumina/package.json | grep -A 10 "dependencies"

# Check patterns
ls docs/patterns/ | wc -l  # Should show pattern count

# Check tech stack
cat vscode-lumina/package.json | grep "typescript"
cat vscode-lumina/package.json | grep "engines"
```

**If Incomplete:**
- Run workspace analysis
- Index pattern library
- Catalog dependencies

### 2. Git Clean ✅

**Check:**
```
- No uncommitted changes (git status --porcelain)
- Current branch identified (git rev-parse --abbrev-ref HEAD)
- Remote status checked (git fetch && git status)
```

**How to Verify:**
```bash
# Check for uncommitted changes
git status --porcelain
# Output should be empty

# Check current branch
git rev-parse --abbrev-ref HEAD
# Output: master (or current branch name)

# Check remote status
git fetch
git status
# Output: "Your branch is up to date with 'origin/master'"
```

**If Not Clean:**
- Commit pending changes: `git add . && git commit -m "..."`
- Stash changes: `git stash` (if work-in-progress)
- Resolve conflicts: `git mergetool` (if merge conflicts)

### 3. Agent Registry Loaded ✅

**Check:**
```
- Agents loaded from internal/agents/ directory
- Agent capabilities mapped to task categories
- No missing agent definitions
```

**How to Verify:**
```bash
# Check agent files exist
ls internal/agents/*-agent-context.md

# Verify agent count matches registry
# Expected: 9 agents (infrastructure, api, ui, docs, security, performance, data, test, devops)
```

**Agent Expertise Map:**
```
infrastructure-agent → Services, middleware, orchestration
api-agent → REST endpoints, routes, controllers
ui-agent → React components, views, interactions
docs-agent → Patterns, guides, documentation
security-agent → Auth, encryption, validation
performance-agent → Optimization, caching, profiling
data-agent → Database, schema, migrations
test-agent → TDD, coverage, integration tests
devops-agent → CI/CD, deployment, monitoring
```

**If Missing Agents:**
- Create agent context file: `internal/agents/{name}-agent-context.md`
- Document agent expertise and responsibilities
- Add to AgentRegistry

### 4. User Requirements Clear ✅

**Check:**
```
- Sprint goal defined (what is being built)
- Success criteria specified (how to know when done)
- Timeline confirmed (how long it should take)
- Constraints identified (dependencies, blockers)
```

**How to Gather:**
```
Ask User Questions:
1. What is the goal of this sprint?
2. What are the success criteria?
3. What is the target timeline?
4. Are there any dependencies or blockers?
5. What is the priority level (critical, high, medium, low)?
```

**If Unclear:**
- Use AskUserQuestion tool to clarify
- Review existing documentation
- Check product roadmap
- Ask about priorities

---

## Sprint TOML Generation Process

### 1. Analyze User Requirements
```
Input: User request (e.g., "Build license key dashboard")

Process:
1. Extract goal: License key generation and management
2. Identify scope: Web dashboard, API, database
3. Determine tech stack: Next.js, React, Vercel
4. List integrations: VS Code extension, Desktop app
5. Note constraints: Must work with existing auth system
```

### 2. Break Down into Phases and Tasks
```
Phase 1: Foundation
- DATABASE-001: Design Supabase schema for license keys
- DATABASE-002: Create RLS policies for security
- API-CLIENT-001: Create API client for frontend

Phase 2: Backend API
- API-001: POST /api/license/generate endpoint
- API-002: GET /api/license/list endpoint
- API-003: DELETE /api/license/revoke endpoint
- SECURITY-001: Implement key encryption

Phase 3: Frontend UI
- UI-001: Create dashboard layout component
- UI-002: Build license key display component
- UI-003: Add copy-to-clipboard functionality
- UI-004: Create admin panel

Phase 4: Testing & Deployment
- TEST-001: Integration tests for API
- TEST-002: E2E tests for UI flow
- DEPLOY-001: Vercel deployment configuration
```

### 3. Assign Agents to Tasks
```
Task → Agent Mapping:

DATABASE-001 → data-agent (schema design)
DATABASE-002 → security-agent (RLS policies)
API-CLIENT-001 → api-agent (client implementation)

API-001 → api-agent (endpoint implementation)
API-002 → api-agent (endpoint implementation)
API-003 → api-agent (endpoint implementation)
SECURITY-001 → security-agent (encryption)

UI-001 → ui-agent (component development)
UI-002 → ui-agent (component development)
UI-003 → ui-agent (component development)
UI-004 → ui-agent (component development)

TEST-001 → test-agent (integration testing)
TEST-002 → test-agent (E2E testing)
DEPLOY-001 → devops-agent (deployment)
```

### 4. Estimate Time and Complexity
```
Estimation Factors:
- Task complexity (simple, moderate, complex)
- Agent expertise (high, medium, low)
- Dependencies (blocked, ready, parallel)
- Historical data (past similar tasks)

Example:
DATABASE-001: Design Supabase schema
- Complexity: Moderate (3-4 tables, RLS policies)
- Agent: data-agent (high expertise)
- Dependencies: None (can start immediately)
- Historical: Similar schema took 3-4 hours
- Estimate: 4 hours
```

### 5. Generate Sprint TOML
```toml
[sprint.metadata]
name = "License Key Dashboard Implementation"
version = "1.0.0"
created = "2025-01-06"
sprint_type = "feature"
estimated_duration = "2-3 weeks"
total_tasks = 12

[sprint.description]
overview = """
Build web dashboard for license key generation and management.
Users will sign up, generate license keys, copy/paste into VS Code + Desktop apps.
"""

success_criteria = [
    "Users can sign up and generate license keys",
    "License keys displayed with copy-to-clipboard",
    "Admin panel for key management",
    "Secure authentication and encryption"
]

[tasks.DATABASE-001]
id = "DATABASE-001"
name = "Design Supabase schema for license keys"
status = "pending"
phase = "foundation"
agent = "data-agent"
estimated_time = "4 hours"
dependencies = []

# ... (remaining tasks)
```

### 6. Show Plan to User for Approval
```
Sprint Plan Preview:

Name: License Key Dashboard Implementation
Duration: 2-3 weeks (14-21 days)
Total Tasks: 12

Phase 1: Foundation (3 tasks) - 3-5 days
Phase 2: Backend API (4 tasks) - 4-6 days
Phase 3: Frontend UI (4 tasks) - 5-7 days
Phase 4: Testing & Deployment (3 tasks) - 2-3 days

Agents:
- data-agent (2 tasks)
- api-agent (4 tasks)
- ui-agent (4 tasks)
- security-agent (2 tasks)
- test-agent (2 tasks)
- devops-agent (1 task)

[User reviews and approves OR requests modifications]
```

### 7. Create Feature Branch (if Approved)
```bash
# Create feature branch
git checkout -b feature/license-dashboard

# Verify branch created
git branch
# Output: * feature/license-dashboard

# Confirm with user
echo "Feature branch created: feature/license-dashboard"
```

### 8. Commit Sprint File
```bash
# Create sprint file
cat > internal/sprints/SPRINT_LICENSE_DASHBOARD.toml << EOF
[sprint.metadata]
name = "License Key Dashboard Implementation"
...
EOF

# Add and commit
git add internal/sprints/SPRINT_LICENSE_DASHBOARD.toml
git commit -m "feat: Add license dashboard sprint plan

Sprint: License Key Dashboard Implementation
Duration: 2-3 weeks
Total tasks: 12
Phases: Foundation, Backend API, Frontend UI, Testing & Deployment

Pattern-SPRINT-PLAN-001 followed ✅"

# Confirm commit
git log -1 --oneline
```

---

## Critical Junction: ALWAYS ASK USER

Sprint planning is **ALWAYS** a critical junction because:

1. **High-impact operation:** Affects entire sprint workflow and team focus
2. **User needs to review:** Plan may not match user's mental model
3. **May need adjustments:** Priorities, scope, timeline may need revision
4. **Prevents wasted work:** 5 minutes review prevents days of misaligned work

**Never proceed without user approval** even if confidence is high

---

## Example: Complete Sprint Planning Flow

```
User: "Create a sprint to build a license key dashboard"

Claude: "Running Sprint Planning Workflow Check (Pattern-SPRINT-PLAN-001)..."

🔍 Sprint Planning Workflow Check
================================================================

Prerequisites:
✅ Workspace analyzed: Code structure mapped, 77 patterns indexed
✅ Git status: Clean working directory (master branch)
✅ Agent Registry: 9 agents loaded from internal/agents/
✅ Patterns available: 77 patterns loaded from docs/patterns/
✅ Skill system: AgentRegistry initialized

Gaps: None

Critical Junction: YES (Sprint planning always requires user approval)

Plan:
1. Analyze requirements: License key dashboard for web
2. Break down into phases: Foundation, Backend, Frontend, Testing
3. Assign agents: data-agent, api-agent, ui-agent, security-agent, test-agent, devops-agent
4. Estimate time: 2-3 weeks (12 tasks)
5. Generate sprint TOML: SPRINT_LICENSE_DASHBOARD.toml
6. Show plan to user for approval
7. Create feature branch: feature/license-dashboard (if approved)
8. Commit sprint file

Claude: [Analyzes requirements and generates sprint plan]

Sprint Plan Generated:
================================================================

Name: License Key Dashboard Implementation
Duration: 2-3 weeks (14-21 days)
Total Tasks: 12

Phase 1: Foundation (3 tasks) - 3-5 days
- DATABASE-001: Design Supabase schema (data-agent, 4h)
- DATABASE-002: Create RLS policies (security-agent, 3h)
- API-CLIENT-001: Create API client (api-agent, 4h)

Phase 2: Backend API (4 tasks) - 4-6 days
- API-001: POST /api/license/generate (api-agent, 6h)
- API-002: GET /api/license/list (api-agent, 4h)
- API-003: DELETE /api/license/revoke (api-agent, 4h)
- SECURITY-001: Implement key encryption (security-agent, 5h)

Phase 3: Frontend UI (4 tasks) - 5-7 days
- UI-001: Create dashboard layout (ui-agent, 6h)
- UI-002: Build license key display (ui-agent, 5h)
- UI-003: Add copy-to-clipboard (ui-agent, 3h)
- UI-004: Create admin panel (ui-agent, 8h)

Phase 4: Testing & Deployment (3 tasks) - 2-3 days
- TEST-001: Integration tests (test-agent, 6h)
- TEST-002: E2E tests (test-agent, 8h)
- DEPLOY-001: Vercel deployment (devops-agent, 4h)

Success Criteria:
✅ Users can generate license keys
✅ Keys displayed with copy-to-clipboard
✅ Admin panel for key management
✅ Secure authentication and encryption

Claude: [Uses AskUserQuestion to get approval]

Question: "Review this sprint plan. Does it match your expectations?"
Options:
1. Approve and create
2. Modify plan
3. Cancel

User: [Selects "Approve and create"]

Claude: "Creating feature branch and sprint file..."

✅ Feature branch created: feature/license-dashboard
✅ Sprint file created: internal/sprints/SPRINT_LICENSE_DASHBOARD.toml
✅ Committed: feat: Add license dashboard sprint plan

Ready to start sprint! 🚀
```

---

## Related Patterns

- **Pattern-TASK-ANALYSIS-001:** Pre-Task Analysis Protocol (used for each sprint task)
- **Pattern-CODE-001:** Code Development Protocol (used during sprint execution)
- **Pattern-TRACKING-001:** Task Tracking & Pre-Commit Protocol (tracks sprint progress)
- **Pattern-IMPROVEMENT-001:** Gap Detection (identifies missing agents or patterns)

---

## Version History

- **v1.0.0** (2025-01-06): Initial extraction from CLAUDE.md
  - Formalized sprint planning workflow check
  - Added prerequisites checklist
  - Documented sprint TOML generation process
  - Added critical junction enforcement
  - Provided complete example flow
