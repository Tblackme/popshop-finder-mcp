# Pattern-TASK-ANALYSIS-001: Pre-Task Analysis Protocol

**CREATED:** 2025-11-08
**CATEGORY:** Workflow Protocol
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.83
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-CODE-001, PATTERN-PUBLISH-003, PATTERN-COMM-001, PATTERN-TDD-001, PATTERN-IMPROVEMENT-001

---


## Problem

Starting code implementation without comprehensive context analysis leads to:
- Rework and costly bugs (2-9 hour fixes for missed issues)
- Suboptimal library selection (npm packages vs Node.js built-ins)
- Pattern violations discovered after implementation (Pattern-PUBLISH-003 native deps)
- Inappropriate test strategies for task type
- Missed integration issues with existing services

**Historical Impact:**
- v0.13.23: Native dependency added → 9 hours debugging
- v0.15.31-32: Runtime npm dependency → 2 hours debugging
- v0.16.15: Missing devDependencies → 2 hours manual bypass

**Total time wasted: 15+ hours that could have been prevented with pre-task analysis**

---

## Solution

**MANDATORY: Run comprehensive 8-step analysis BEFORE writing ANY code for ANY task**

This protocol ensures best-first-try outcomes through systematic context gathering, catching known issues before they become bugs, and making context-aware decisions about tech stack and integration.

---

## When to Use

- Starting ANY task from a sprint
- Before implementing ANY new feature
- When uncertain about implementation approach
- When multiple solution paths exist

---

## Required Analysis Steps

### 1. Agent Verification

**Purpose:** Ensure the right expert is assigned to the task

**Steps:**
```
1. Read assigned agent context file: internal/agents/{agent}-context.md
2. Verify agent expertise matches task requirements:
   - Infrastructure tasks → infrastructure-agent
   - API/endpoints → api-agent
   - UI/components → ui-agent
   - Documentation → docs-agent
3. If mismatch detected:
   - Update agent assignment in sprint TOML
   - Re-run analysis with correct agent context
4. If agent context incomplete:
   - Update agent context with new responsibilities
   - Document new expertise areas
```

**Example:**
```
Task: PROTO-001 - Universal Workflow Check System
Assigned: infrastructure-agent ✅
Expertise: Service orchestration, TypeScript services ✅
Match: YES ✅ → Proceed
```

---

### 2. Tech Stack Analysis

**Purpose:** Understand current stack and constraints

**Check:**
```
- TypeScript version: vscode-lumina/package.json → "typescript": "^5.x"
- VS Code API: vscode-lumina/package.json → engines.vscode
- Node.js version: .nvmrc or package.json → engines.node
- Compilation requirements: Special tsconfig settings needed?
```

**Questions:**
- Is this compatible with current VS Code API version?
- Does this require TypeScript features from specific version?
- Are there Node.js built-in APIs available for this task?

**Example:**
```
✅ TypeScript: 5.3.3 (vscode-lumina/package.json)
✅ VS Code API: ^1.80.0
✅ Node.js: >=18.0.0
✅ Special config: None needed
```

---

### 3. Integration Points

**Purpose:** Understand dependencies and coupling

**Identify:**
```
- What existing services does this integrate with?
- For each integration point, read source file to understand:
  * Interface/API surface
  * Error handling patterns
  * Performance characteristics
  * Dependencies and side effects
```

**Example:**
```
Task: WorkflowCheck service

Integration Points:
1. ConfidenceScorer.ts
   - scoreTask(task) → number (0.0-1.0)
   - Throws: Never (returns 0.0 on error)
   - Performance: <100ms (cached)

2. TestValidator.ts
   - validateTests(task) → ValidationResult
   - Throws: ValidationError
   - Performance: <200ms (runs test suite)

3. Git APIs (child_process.exec)
   - git status, git log commands
   - Throws: Error if git not installed
   - Performance: <50ms (cached)

4. MiddlewareLogger.ts
   - log(level, message, metadata)
   - Never throws
   - Performance: <10ms (async write)

✅ Action: Read all 4 files to understand interfaces
⚠️  Watch for: Git availability (graceful degradation needed)
```

**Check for:**
- Circular dependencies
- Tight coupling that should be loosened
- Missing error handling
- Performance bottlenecks

---

### 4. Known Issues Check

**Purpose:** Avoid repeating historical bugs

**Mandatory Checks:**
```
1. Pattern-PUBLISH-003: Will this add runtime npm dependencies?
   - ❌ FORBIDDEN: glob, lodash, moment, axios, chalk
   - ✅ ALLOWED: Node.js built-ins (fs, path, child_process)
   - ✅ ALLOWED: Sub-packages (aetherlight-analyzer, aetherlight-sdk, aetherlight-node)
   - ✅ ALLOWED: Whitelisted (@iarna/toml, form-data, node-fetch, ws)

2. Native Dependencies: Will this require C++ addons?
   - ❌ FORBIDDEN: @nut-tree-fork/nut-js, robotjs, node-gyp
   - ✅ ALLOWED: VS Code APIs (vscode.window, vscode.workspace)

3. Review KNOWN_ISSUES.md for past bugs in similar areas

4. Check agent "Common Pitfalls" section for category-specific issues
```

**If ANY forbidden dependency needed:**
- STOP immediately
- Find alternative using Node.js built-ins
- Reconsider design approach
- Ask user if truly necessary

**Example:**
```
✅ Pattern-PUBLISH-003: No runtime npm deps planned
✅ Native deps: None required
✅ Past bugs: Reviewed - no relevant patterns
✅ Agent pitfalls: None for this task type
```

---

### 5. Library Selection

**Purpose:** Choose optimal implementation approach

**Decision Tree:**
```
Can this be done with Node.js built-in modules?
├─ YES → Use built-ins (fs, path, child_process, crypto, https)
└─ NO → Can this use VS Code APIs?
    ├─ YES → Use vscode.* APIs (vscode.window, vscode.workspace)
    └─ NO → Is this a whitelisted exception?
        ├─ YES → Use whitelisted package (@iarna/toml, form-data, node-fetch, ws)
        └─ NO → STOP - Reconsider design or ask user
```

**Common Patterns:**
```
Task: File globbing
❌ BAD: import { glob } from 'glob'
✅ GOOD: fs.readdirSync() + .filter()

Task: HTTP requests
❌ BAD: import axios from 'axios'
✅ GOOD: import https from 'https' (built-in)

Task: Text insertion in editor
❌ BAD: Native keyboard library
✅ GOOD: editor.edit(editBuilder => ...)

Task: Git operations
❌ BAD: npm package 'simple-git'
✅ GOOD: child_process.exec('git status')
```

**Always Ask:** "Can this be done with built-ins?"
- If YES → Use built-ins
- If NO → Reconsider design

**Example:**
```
Task: Check git status

✅ Git operations: child_process.exec() (built-in)
✅ File operations: fs, path (built-ins)
✅ No npm packages needed ✅
```

---

### 6. Performance Requirements

**Purpose:** Design for performance from the start

**Calculate target based on task type:**
```
- Workflow checks: <500ms (Pattern-COMM-001)
- Agent assignment: <50ms (caching required)
- Confidence scoring: <100ms
- Test validation: <200ms
- Extension activation: <200ms (VS Code requirement)
- File operations: <100ms (user-facing)
- Background tasks: <5s (can be async)
```

**Design caching strategy if needed:**
```
- Cache hit rate target: >80%
- Cache invalidation: Time-based (TTL) or event-based
- Cache size limits: Memory-aware (don't exceed 50MB)
```

**Add timeout protection:**
```
- Operations >1s: Add timeout parameter
- Long-running tasks: Make async with progress indication
- Network operations: 10s timeout (configurable)
```

**Example:**
```
Task: WorkflowCheck.checkWorkflow()

✅ Target: <500ms (workflow check)
✅ Caching: Required (>80% hit rate)
   - Cache key: workflow type + task ID
   - TTL: 5 minutes (git status changes)
✅ Timeout: 10s max per check (network operations)
✅ Progress: Show spinner for >500ms operations
```

---

### 7. TDD Strategy Design

**Purpose:** Plan test approach BEFORE implementation

**Determine coverage requirement by task category:**
```
Infrastructure tasks: 90% coverage
  - Core services, critical paths
  - Example: WorkflowCheck, ConfidenceScorer, TestValidator

API tasks: 85% coverage
  - All endpoints, error cases
  - Example: REST API routes, GraphQL resolvers

UI tasks: 70% coverage
  - Components, interactions
  - Example: React components, VS Code webviews

Documentation tasks: 0% coverage
  - Manual validation
  - Example: README, patterns, guides
```

**Design test cases BEFORE implementation:**
```
1. Happy path scenarios
   - Normal input → expected output
   - All success cases covered

2. Error cases and edge cases
   - Invalid input → appropriate error
   - Boundary conditions (null, undefined, empty, max size)
   - Concurrent access (if applicable)

3. Integration with other services
   - Mock external services
   - Test failure modes (service unavailable)
   - Test timeout scenarios

4. Performance benchmarks
   - Measure against performance targets
   - Identify bottlenecks before optimization
```

**Identify test dependencies:**
```
- Mocks: What services need mocking?
- Fixtures: What test data is needed?
- Test data: Can we use real data or need synthetic?
- Setup/teardown: What cleanup is needed?
```

**Example:**
```
Task: WorkflowCheck.checkWorkflow()

✅ Category: Infrastructure → 90% coverage required

✅ Test cases:
   Happy path:
   - checkWorkflow('code') → validates TDD, tests, sprint task
   - checkWorkflow('sprint') → validates workspace, git, skills
   - checkWorkflow('publish') → validates tests, artifacts, git

   Error cases:
   - checkWorkflow('invalid') → throws InvalidWorkflowError
   - ConfidenceScorer unavailable → graceful degradation (log warning)
   - Git not installed → returns {gitAvailable: false}

   Integration:
   - Mock ConfidenceScorer.scoreTask() → test scoring logic
   - Mock TestValidator.validateTests() → test validation logic
   - Mock git commands → test status parsing

   Performance:
   - Benchmark against <500ms target
   - Test cache hit rate (>80% expected)

✅ Test file: vscode-lumina/test/services/workflowCheck.test.ts

✅ Test dependencies:
   - Mock: ConfidenceScorer, TestValidator
   - Fixture: Sample task TOML
   - Test data: Git status output samples
```

---

### 8. Clarification Questions

**Purpose:** Resolve ambiguity before implementation

**If ANY of the above is unclear or ambiguous → ASK USER**

**Use AskUserQuestion tool for:**
```
- Multiple valid implementation approaches
  Example: "Should I use SQLite or JSON for local storage?"

- Unclear requirements or acceptance criteria
  Example: "What should happen if user cancels during upload?"

- Trade-offs that need user decision
  Example: "Fast + less accurate OR slow + more accurate?"

- Missing information about integration points
  Example: "Should this API be authenticated or public?"
```

**DO NOT proceed with uncertain assumptions**

Guessing leads to rework. 5 minutes asking = 2 hours saved debugging.

**Example:**
```
Task: WorkflowCheck.checkWorkflow()

✅ No clarifications needed - requirements clear
✅ Implementation approach: Single obvious solution
✅ Integration points: Well-documented APIs
✅ Trade-offs: None requiring user decision
```

---

## Workflow Diagram

```
┌─────────────────────────────────────┐
│ 1. Read sprint task from TOML      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Run Pre-Task Analysis (8 steps) │
│    ✅ Agent verification             │
│    ✅ Tech stack analysis            │
│    ✅ Integration points             │
│    ✅ Known issues check             │
│    ✅ Library selection              │
│    ✅ Performance requirements       │
│    ✅ TDD strategy design            │
│    ✅ Clarification questions        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Document analysis results        │
│    (in chat for user visibility)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Update agent/sprint if needed    │
│    - Update agent context           │
│    - Update task in sprint TOML     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Proceed to TDD implementation    │
│    - RED: Write tests first         │
│    - GREEN: Implement to pass       │
│    - REFACTOR: Optimize             │
└─────────────────────────────────────┘
```

---

## Example Pre-Task Analysis Output

```
Pre-Task Analysis: PROTO-001 - Universal Workflow Check System
================================================================

1. Agent Verification
   ✅ Assigned: infrastructure-agent
   ✅ Match: Service orchestration, TypeScript services
   ✅ Action: None needed

2. Tech Stack
   ✅ TypeScript: 5.3.3 (vscode-lumina/package.json)
   ✅ VS Code API: ^1.80.0
   ✅ Node.js: >=18.0.0
   ✅ Special config: None needed

3. Integration Points
   ✅ ConfidenceScorer.ts (scoring logic)
   ✅ TestValidator.ts (test validation)
   ✅ Git APIs (child_process.exec)
   ✅ MiddlewareLogger.ts (structured logging)
   Action: Read all 4 files to understand interfaces

4. Known Issues Check
   ✅ Pattern-PUBLISH-003: No runtime npm deps planned
   ✅ Native deps: None required
   ✅ Past bugs: Reviewed - no relevant patterns

5. Library Selection
   ✅ Git operations: child_process.exec() (built-in)
   ✅ File operations: fs, path (built-ins)
   ✅ No npm packages needed ✅

6. Performance Requirements
   ✅ Target: <500ms (workflow check)
   ✅ Caching: Required (>80% hit rate)
   ✅ Timeout: 10s max per check

7. TDD Strategy
   ✅ Category: Infrastructure → 90% coverage required
   ✅ Test cases:
      - checkWorkflow('code') → validates TDD, tests, sprint task
      - checkWorkflow('sprint') → validates workspace, git, skills
      - checkWorkflow('publish') → validates tests, artifacts, git
      - Service integration failures (graceful degradation)
      - Performance benchmarks (<500ms)
   ✅ Test file: vscode-lumina/test/services/workflowCheck.test.ts

8. Clarifications
   ✅ No clarifications needed - requirements clear

Ready to proceed: YES ✅
Estimated time: 4-5 hours
Confidence: HIGH (0.90)
```

---

## Benefits

**Quantified Impact:**

1. **Reduces rework:** 57% token savings vs debugging after implementation
   - WITHOUT analysis: Bug → Debug (8k tokens) → Regression (8k tokens) = 21k total
   - WITH analysis: Analysis (2k) → Implement (5k) → Fix (1k) = 9k total

2. **Catches issues early:** Known pattern violations detected before coding
   - v0.13.23: Would have caught native dependency BEFORE 9-hour debug
   - v0.15.31-32: Would have caught npm dependency BEFORE 2-hour debug
   - v0.16.15: Would have caught missing devDependencies BEFORE manual bypass

3. **Optimizes decisions:** Best library/approach chosen with full context
   - fs.readdirSync() instead of glob package
   - VS Code APIs instead of native libraries
   - Node.js built-ins instead of npm packages

4. **Improves outcomes:** Best-first-try through comprehensive analysis
   - Confidence score ≥0.90 for well-analyzed tasks
   - Confidence score ≤0.70 for poorly-analyzed tasks
   - 30% of total confidence score comes from analysis quality

5. **Documents decisions:** Clear reasoning for future reference
   - Why this library was chosen
   - What alternatives were considered
   - What trade-offs were made

---

## Enforcement

**Self-Accountability:**
- Agents document this protocol in workflow section
- Sprint tasks should note which agent was used
- Update agent context if new patterns learned during task
- This protocol becomes part of the development culture

**Pattern Reference in Code:**
```typescript
// Pattern-TASK-ANALYSIS-001: Pre-task analysis completed
// Agent: infrastructure-agent
// Integration points: ConfidenceScorer, TestValidator, Git
// Performance target: <500ms with caching
// TDD strategy: 90% coverage, 15 tests
```

**Audit Trail:**
- Analysis results logged in chat (user visibility)
- Confidence score reflects analysis quality
- Missing analysis = lower confidence = fill_gaps action

---

## Related Patterns

- **Pattern-CODE-001:** Code Development Protocol (uses this analysis)
- **Pattern-SPRINT-PLAN-001:** Sprint Planning Protocol (uses this analysis)
- **Pattern-PUBLISH-003:** Avoid Runtime npm Dependencies (checked in step 4)
- **Pattern-TDD-001:** Test-Driven Development Ratchet (informs step 7)
- **Pattern-IMPROVEMENT-001:** Gap Detection (identifies missing patterns in step 8)

---

## Version History

- **v1.0.0** (2025-01-06): Initial extraction from CLAUDE.md
  - Formalized 8-step analysis process
  - Added historical bug impact data
  - Integrated with existing patterns
