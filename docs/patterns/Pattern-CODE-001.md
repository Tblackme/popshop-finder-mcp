# Pattern-CODE-001: Code Development Protocol

**CREATED:** 2025-11-08
**CATEGORY:** Workflow Protocol
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.95
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-TDD-001, PATTERN-TRACKING-001, PATTERN-PUBLISH-003, PATTERN-IMPROVEMENT-001

---


## Problem

Starting code implementation without workflow validation leads to:
- Code written without tests (TDD violations)
- Orphan code not tracked in sprint tasks
- Low confidence discovered after implementation (missing patterns, agents, context)
- No transparency for user (blind coding)
- Rework and debugging after the fact

**Without this protocol:**
- User doesn't see prerequisites → No confidence in approach
- No confidence score → Blind coding with unknown risks
- Gaps missed → Rework later (2-9 hour fixes)
- No transparency → User distrust

---

## Solution

**MANDATORY: Run workflow check BEFORE writing ANY production code**

This protocol ensures sprint task tracking, test-driven development, and transparent communication with the user before starting implementation.

---

## When to Use

- Before implementing ANY feature
- Before fixing ANY bug (except typos - see Edge Cases)
- When starting ANY coding session

---

## Workflow Check Template

Before writing code, Claude MUST announce using this template:

```
🔍 Code Workflow Check: [Task ID - Task Name]
================================================================

Prerequisites:
✅ Sprint task: PROTO-001 - Universal Workflow Check System
✅ Tests exist: test/services/workflowCheck.test.ts (15 tests written - TDD RED phase)
✅ Git status: Clean working directory
✅ Confidence: 0.90 (HIGH) - All criteria met

Gaps: None

Critical Junction: NO (high confidence ≥0.80)

Plan:
1. Implement WorkflowCheck.ts service (TDD GREEN phase)
2. Compile TypeScript
3. Run tests - verify they PASS
4. Refactor and optimize (TDD REFACTOR phase)
5. Commit changes

Ready to proceed ✅
```

---

## Communication Template

Before writing code, Claude MUST announce:

### 1. What task is being worked on (with ID)
```
Task: PROTO-001 - Universal Workflow Check System
Sprint: internal/sprints/ACTIVE_SPRINT.toml
Agent: infrastructure-agent
```

### 2. Prerequisites checked (✅/❌ with details)
```
✅ Sprint task exists: PROTO-001 in ACTIVE_SPRINT.toml
✅ Tests written: vscode-lumina/test/services/workflowCheck.test.ts (15 tests)
✅ Git status: Clean (no uncommitted changes)
✅ Agent match: infrastructure-agent matches task category
✅ Pre-task analysis: Completed (Pattern-TASK-ANALYSIS-001)
```

### 3. Confidence score (percentage + HIGH/MEDIUM/LOW)
```
Confidence: 0.90 (HIGH)

Breakdown:
- Task completeness: 0.90 (all fields present)
- Pre-task analysis: COMPLETE ✅
- Test files: EXISTS (15 tests written)
- Agent match: YES ✅
- Known issues reviewed: Pattern-PUBLISH-003 checked

Formula: (0.85 + 0.05 + 0.10 + 0.05 + 0.05) / 5 = 0.90
```

**Confidence Levels:**
- **HIGH (≥0.80):** Proceed with confidence, no approval needed
- **MEDIUM (0.60-0.79):** Caution advised, consider asking user
- **LOW (<0.60):** STOP - Fill gaps OR ask user for guidance

### 4. Any gaps identified
```
Gaps: None ✅

OR if gaps exist:

Gaps Detected:
⚠️  Missing test file: vscode-lumina/test/services/myService.test.ts
⚠️  No agent assigned: Task not assigned in sprint TOML
⚠️  Integration unclear: How does this integrate with ConfidenceScorer?

Action: Fill gaps before proceeding (see Pattern-IMPROVEMENT-001)
```

### 5. Whether this is a critical junction (requires approval)
```
Critical Junction: NO (high confidence, routine task)

OR if critical:

Critical Junction: YES
Reason: High-impact change to core workflow system
Action: Asking user for approval before proceeding
```

**Critical Junctions:**
- High-impact changes (affects core systems)
- Low confidence (<0.60) with unclear path forward
- Multiple valid approaches (user decision needed)
- Potentially breaking changes

### 6. Execution plan (step-by-step)
```
Plan:
1. TDD RED: Verify tests FAIL (implementation doesn't exist yet)
2. TDD GREEN: Implement WorkflowCheck.ts to make tests pass
3. Compile TypeScript: npm run compile
4. TDD REFACTOR: Optimize for performance (<500ms target)
5. Run tests: npm test (verify all pass)
6. Commit changes: git commit with detailed message

Estimated time: 4-5 hours
```

---

## Edge Case Guidelines

### 1. Typo Fix (Non-Feature Code)

**Skip workflow check** for:
- Typo in comment/documentation
- Typo in variable name (cosmetic only)
- Typo in string literal

**WHY:** Typos don't require tests, sprint tasks, or patterns

**Example:**
```typescript
// BEFORE: "Calulate confidence score"
// AFTER: "Calculate confidence score"
// ✅ Skip workflow check - comment typo fix
```

### 2. Bug Fix (Production Code)

**Always run workflow check** for production code bug fixes

**Process:**
1. Run workflow check
2. Write test FIRST (TDD RED phase) that reproduces bug
3. Fix bug (TDD GREEN phase) to make test pass
4. Verify all tests still pass
5. Commit with bug reproduction test

**WHY:** Bug fixes are production code changes requiring tests to prevent regression

**Example:**
```typescript
// Bug: ConfidenceScorer returns NaN for empty task
// 1. Workflow check ✅
// 2. Write test: expect(scoreTask({})).toBe(0.0) ✅
// 3. Test FAILS (returns NaN) ✅ TDD RED
// 4. Fix: return isNaN(score) ? 0.0 : score ✅ TDD GREEN
// 5. Test PASSES ✅
// 6. Commit with test ✅
```

### 3. Experimental Code (Spike/POC)

**Run workflow check** even for experiments

**Process:**
1. Run workflow check
2. Mark as experimental in commit message
3. Create sprint task OR note as "spike"
4. Document findings for future reference

**WHY:** Even experiments benefit from context tracking and prevent orphan code

**Example:**
```
Task: SPIKE-001 - Evaluate SQLite vs JSON for local storage
Sprint: internal/sprints/ACTIVE_SPRINT.toml (experimental task)
Deliverable: Performance comparison document
```

### 4. Refactoring (No Behavior Change)

**Run workflow check** for all refactoring

**Process:**
1. Run workflow check
2. Verify existing tests still pass (no new tests needed)
3. Refactor code (behavior unchanged)
4. Run tests again (verify still passing)
5. Commit with "refactor:" prefix

**WHY:** Refactoring can introduce subtle bugs even with no intended behavior change

**Example:**
```
Task: Refactor ConfidenceScorer for clarity
Tests: Existing tests (no new tests needed)
Verification: npm test (all 15 tests still pass)
Commit: "refactor: Extract scoring logic into separate methods"
```

---

## Integration with TodoWrite

After workflow check, Claude MUST use TodoWrite to track task steps:

```javascript
TodoWrite({
  todos: [
    {
      content: "Pre-Task Analysis (8 steps)",
      status: "completed", // If already done
      activeForm: "Completed pre-task analysis"
    },
    {
      content: "TDD RED: Write tests first",
      status: "in_progress",
      activeForm: "Writing 15 tests for WorkflowCheck"
    },
    {
      content: "TDD GREEN: Implement to pass tests",
      status: "pending",
      activeForm: "Implementing WorkflowCheck.ts"
    },
    {
      content: "TDD REFACTOR: Optimize code",
      status: "pending",
      activeForm: "Refactoring for performance"
    },
    {
      content: "Compile TypeScript",
      status: "pending",
      activeForm: "Compiling TypeScript"
    },
    {
      content: "Commit changes",
      status: "pending",
      activeForm: "Committing implementation"
    }
  ]
})
```

**Mark each step `completed` immediately after finishing** (see Pattern-TRACKING-001)

---

## Enforcement Mechanism

### Self-Accountability
Claude follows this protocol voluntarily as part of professional development culture

### User Visibility
User sees workflow check announcement BEFORE any code is written, providing transparency and confidence

### Pattern Reference
This protocol is Pattern-CODE-001 and should be referenced in:
- Agent context files (workflow section)
- Sprint task descriptions
- Commit messages (Pattern-CODE-001 followed)

### Audit Trail
Workflow checks logged in MiddlewareLogger for retrospective analysis:
```typescript
logger.log('workflow-check', {
  taskId: 'PROTO-001',
  confidence: 0.90,
  gaps: [],
  criticalJunction: false,
  timestamp: Date.now()
});
```

---

## Failure Modes

**If Claude skips workflow check:**

❌ **User doesn't see prerequisites**
- No visibility into what's being checked
- Can't validate approach before implementation starts

❌ **No confidence score → blind coding**
- Unknown risk level
- No way to assess if gaps need filling

❌ **Gaps missed → rework later**
- Pattern violations discovered after implementation
- 2-9 hour debugging sessions (see KNOWN_ISSUES.md)

❌ **No transparency → user distrust**
- User doesn't know what Claude is doing
- Can't course-correct early if wrong approach

---

## Complete Example: Full Code Development Flow

```
User: "Implement PROTO-001 - Universal Workflow Check System"

Claude: "Running Pre-Task Analysis (Pattern-TASK-ANALYSIS-001)..."

[8-step analysis completed - see Pattern-TASK-ANALYSIS-001.md for details]

Claude: "Pre-Task Analysis COMPLETE ✅

Now running Code Workflow Check (Pattern-CODE-001)..."

🔍 Code Workflow Check: PROTO-001 - Universal Workflow Check System
================================================================

Prerequisites:
✅ Sprint task: PROTO-001 assigned to infrastructure-agent
✅ Tests exist: NO - Will write tests first (TDD RED phase)
✅ Git status: Clean working directory
✅ Agent match: infrastructure-agent v2.0 (service orchestration) ✅
✅ Pre-task analysis: COMPLETE (see above)

Confidence: 0.85 (HIGH)

Breakdown:
- Task completeness: 0.85 (all required fields present)
- Pre-task analysis: COMPLETE ✅
- Known issues reviewed: Pattern-PUBLISH-003 (no runtime npm deps) ✅
- Agent match: YES ✅
- Integration points: 4 services identified and analyzed ✅

Gaps: None

Critical Junction: NO (high confidence, routine infrastructure task)

Plan:
1. Write 15 comprehensive tests (TDD RED phase) - 1 hour
   - Happy path: checkWorkflow('code'), checkWorkflow('sprint'), checkWorkflow('publish')
   - Error cases: Invalid workflow, service unavailable, git failure
   - Integration: Mock ConfidenceScorer, TestValidator, Git APIs
   - Performance: Benchmark <500ms target

2. Implement WorkflowCheck.ts service (TDD GREEN phase) - 2 hours
   - Implement checkWorkflow() method
   - Integrate with ConfidenceScorer, TestValidator
   - Add git status checking with child_process.exec()
   - Add caching layer for performance

3. Compile TypeScript - 5 minutes
   - npm run compile
   - Fix any type errors

4. Verify tests PASS - 5 minutes
   - npm test
   - Verify all 15 tests pass
   - Check coverage ≥90%

5. Refactor for performance (TDD REFACTOR phase) - 1 hour
   - Optimize caching strategy
   - Reduce redundant git calls
   - Benchmark against <500ms target

6. Commit changes - 5 minutes
   - git add vscode-lumina/src/services/WorkflowCheck.ts
   - git add vscode-lumina/test/services/workflowCheck.test.ts
   - git commit -m "feat: Add WorkflowCheck service (Pattern-CODE-001)"

Estimated time: 4-5 hours
Ready to proceed ✅

Claude: [Uses TodoWrite to create tactical task list]

✅ Pre-Task Analysis (8 steps)
🔄 TDD RED: Write 15 tests for WorkflowCheck
⏳ TDD GREEN: Implement WorkflowCheck.ts
⏳ TDD REFACTOR: Optimize performance
⏳ Compile TypeScript
⏳ Commit changes

Claude: "Starting TDD RED phase - writing 15 tests..."

[Proceeds with implementation following the plan]
```

---

## Related Patterns

- **Pattern-TASK-ANALYSIS-001:** Pre-Task Analysis Protocol (run BEFORE this)
- **Pattern-TDD-001:** Test-Driven Development Ratchet (enforces RED-GREEN-REFACTOR)
- **Pattern-TRACKING-001:** Task Tracking & Pre-Commit Protocol (tracks progress)
- **Pattern-IMPROVEMENT-001:** Gap Detection (handles gaps found during workflow check)
- **Pattern-SPRINT-PLAN-001:** Sprint Planning Protocol (creates sprint tasks)

---

## Version History

- **v1.0.0** (2025-01-06): Initial extraction from CLAUDE.md
  - Formalized workflow check template
  - Added communication requirements
  - Integrated with TodoWrite tracking
  - Added edge case guidelines
  - Documented failure modes and enforcement
