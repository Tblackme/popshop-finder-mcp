# Pattern-COMM-001: Universal Communication Protocol

**ID:** Pattern-COMM-001
**Category:** Communication
**Status:** Production-Validated
**Created:** 2025-11-03
**Last Updated:** 2025-11-03

---

## Problem Statement

**Context:** Claude executes workflows (coding, sprint planning, publishing, testing, documentation) without announcing prerequisites, assumptions, or decision points.

**Pain Points:**
- User has no visibility into what Claude is checking before proceeding
- Assumptions remain hidden until something fails
- No confidence scoring → blind trust required
- Surprise failures appear without warning
- User can't verify Claude is following proper workflows
- Gaps (missing patterns, tests, agents) discovered too late

**Impact:**
- User distrust ("What is Claude actually doing?")
- Wasted time debugging ("Why did this fail?")
- Rework when gaps discovered after implementation
- No accountability (Claude makes decisions without explaining)
- Inability to audit workflow compliance

**Example - Before Protocol:**
```
User: "Implement PROTO-001"
Claude: *writes code without announcement*
Claude: *completes implementation*
Claude: "Done! Here's the code."

User: "Did you write tests?"
Claude: "Oh, I forgot tests. Let me add them now."
↑ Rework required, TDD violated, time wasted
```

---

## Solution

**Universal Workflow Check System:** Claude announces prerequisites, confidence, and plan BEFORE executing ANY workflow.

**Core Components:**

1. **Workflow Check Template** - Standard format for ALL workflows
2. **Prerequisites Display** - Show what's being checked (✅/❌/⚠️)
3. **Confidence Scoring** - Quantify readiness (0.0-1.0 scale)
4. **Gap Detection** - Identify missing patterns, tests, agents
5. **Critical Junction Detection** - Flag when user approval required
6. **Execution Plan** - Step-by-step workflow outline

**Workflow Types Supported:**
- `code` - Code development (features, bug fixes)
- `sprint` - Sprint planning and creation
- `publish` - Publishing releases
- `test` - Test workflow setup
- `docs` - Documentation creation
- `git` - Git operations (commit, push, merge)

**Standard Announcement Format:**
```
🔍 [Workflow Type] Workflow Check: [Task ID - Task Name]
================================================================

Prerequisites:
✅ Prerequisite 1: Details (status good)
⚠️ Prerequisite 2: Details (warning - suboptimal but not blocking)
❌ Prerequisite 3: Details (error - blocking issue)

Confidence: X.XX (HIGH/MEDIUM/LOW)
- Explanation of confidence score
- What factors contribute to score

Gaps: [List of missing items]
- Gap 1: Description
- Gap 2: Description

Critical Junction: YES/NO (requires user approval?)
- Explanation of why this is/isn't critical

Plan:
1. Step 1 with reasoning
2. Step 2 with reasoning
3. Step 3 with reasoning
...

Estimated time: X hours
Ready to proceed: YES ✅ / NO ❌
```

---

## Implementation

### 1. WorkflowCheck Service (PROTO-001)

**File:** `vscode-lumina/src/services/WorkflowCheck.ts`

**Key Methods:**
```typescript
export class WorkflowCheck {
  /**
   * Check workflow prerequisites
   *
   * @param workflowType - Type of workflow ('code', 'sprint', 'publish', etc.)
   * @param context - Workflow-specific context
   * @returns WorkflowCheckResult with prerequisites, confidence, gaps, plan
   */
  public async checkWorkflow(
    workflowType: WorkflowType,
    context: WorkflowContext
  ): Promise<WorkflowCheckResult>

  // Returns:
  // - prerequisites: PrerequisiteStatus[] (✅/❌/⚠️ with remediation)
  // - confidence: number (0.0-1.0)
  // - gaps: string[] (missing items)
  // - criticalJunction: boolean (requires approval?)
  // - plan: string[] (execution steps)
}
```

**Integration Points:**
- `ConfidenceScorer` - Calculate task confidence scores
- `TestValidator` - Validate tests exist and pass
- Git APIs (`child_process.exec`) - Check git status
- `MiddlewareLogger` - Log workflow checks for audit trail

**Performance:**
- Target: <500ms per workflow check
- Caching: >80% hit rate for repeated checks
- Timeout protection: 10s max per check

### 2. CLAUDE.md Protocol Sections (PROTO-002)

**File:** `.claude/CLAUDE.md`

**Sections Added:**
1. **Code Development Protocol (Pattern-CODE-001)**
   - Mandatory workflow check before ANY production code
   - TDD enforcement (write tests first)
   - Edge cases (typo vs bug fix vs feature)

2. **Sprint Planning Protocol (Pattern-SPRINT-PLAN-001)**
   - Workspace analysis prerequisite
   - Agent registry loading
   - Always critical junction (user approval)

3. **Testing Protocol (Pattern-TEST-001)**
   - TDD workflow (RED-GREEN-REFACTOR)
   - Coverage requirements by task type (90%/85%/70%/0%)

4. **Documentation Protocol (Pattern-DOCS-001)**
   - Reusability assessment (High/Medium/Low/Ephemeral)
   - Pattern vs ephemeral summary rules

5. **Git Workflow Integration**
   - Git status checks (clean, uncommitted, conflicts, branch)
   - Branch safety (warn if on main/master)

6. **Gap Detection & Self-Improvement**
   - Propose creating missing patterns/skills/agents
   - User approval with AskUserQuestion tool

### 3. Enforcement Mechanism

**Self-Accountability Model:**
- Claude follows protocol voluntarily
- Protocol documented in CLAUDE.md (Claude's instruction manual)
- User visibility creates accountability
- Audit trail via MiddlewareLogger

**Critical Junctions:**
- Confidence < 0.80 → Ask user approval
- High-impact operations (publish, sprint) → Always ask
- Missing prerequisites → Block or warn

---

## Examples

### Example 1: Code Development Workflow Check

```
User: "Implement PROTO-001 - Universal Workflow Check System"

Claude: "Running Pre-Task Analysis (Pattern-TASK-ANALYSIS-001)..."

[8-step analysis completed - see Pattern-TASK-ANALYSIS-001]

Claude: "Pre-Task Analysis COMPLETE ✅

Now running Code Workflow Check..."

🔍 Code Workflow Check: PROTO-001 - Universal Workflow Check System
================================================================

Prerequisites:
✅ Sprint task: PROTO-001 assigned to infrastructure-agent
✅ Tests exist: NO - Will write tests first (TDD RED phase)
✅ Git status: Clean working directory
✅ Agent match: infrastructure-agent v2.0 (service orchestration) ✅
✅ Tech stack: TypeScript 5.3.0, VS Code API ^1.99.0
✅ Known issues reviewed: Pattern-PUBLISH-003 (no runtime npm deps)

Confidence: 0.85 (HIGH)
- Task completeness: 0.85 (all criteria met)
- Pre-task analysis: COMPLETE
- Tech stack verified: ✅
- Integration points identified: ConfidenceScorer, TestValidator, Git

Gaps: None

Critical Junction: NO (high confidence, routine task)

Plan:
1. Write 15 comprehensive tests (TDD RED phase) - 1 hour
   - Cover all 6 workflow types
   - Test error handling (service failures)
   - Performance benchmarks (<500ms)
2. Implement WorkflowCheck.ts service (TDD GREEN phase) - 2 hours
   - Rich status objects (Option 2 - user requested)
   - Graceful degradation on failures
   - Caching for >80% hit rate
3. Compile and verify tests pass - 15 min
4. Refactor for performance (<500ms target) - 30 min
5. Commit with detailed message - 15 min

Estimated time: 4-5 hours
Ready to proceed: YES ✅

[Claude proceeds with implementation following TDD workflow]
```

### Example 2: Sprint Planning Workflow Check

```
User: "Create sprint for v0.16.0 - Communication Protocol implementation"

Claude: "Running Sprint Planning Workflow Check..."

🔍 Sprint Planning Workflow Check
================================================================

Prerequisites:
✅ Workspace analyzed: Context gathered from codebase
   - 77 pattern files found
   - 9 agent context files loaded
   - Tech stack: TypeScript, Rust, Node.js
✅ Git status: Clean working directory
✅ Agent Registry: 9 agents loaded
   - infrastructure-agent, api-agent, ui-agent, etc.
✅ Patterns available: 77 patterns loaded
✅ Skill system: AgentRegistry initialized

Confidence: 0.90 (HIGH)
- Workspace fully analyzed
- All agents available
- No blocking issues

Gaps: None

Critical Junction: YES (Always ask user to review sprint plan)
- Sprint planning is high-impact operation
- User needs to approve plan before creation
- May need adjustments based on priorities

Plan:
1. Analyze user requirements - 15 min
   - Break down into phases
   - Identify dependencies
2. Assign agents to tasks - 15 min
   - Match agent expertise to task categories
3. Estimate time and complexity - 10 min
4. Generate sprint TOML - 10 min
5. **PAUSE: Show plan to user for approval** ⏸️
6. Create feature branch (if approved) - 2 min
7. Commit sprint file - 2 min

Estimated time: 1 hour (includes user review time)
Ready to proceed: YES ✅ (will pause for user approval before creating)

[Claude generates sprint plan and shows to user]

Claude: "Here's the proposed sprint plan. Please review:

- Phase 0: Communication Protocol (6 tasks, 18-22 hours)
- Phase 1: UI Redesign (11 tasks, 30-35 hours)
...

Do you approve this plan, or should I make adjustments?"

[User approves, Claude creates sprint]
```

### Example 3: Publish Workflow Check

```
User: "Publish v0.16.0"

Claude: "Running Publish Workflow Check..."

🔍 Publish Workflow Check: v0.16.0
================================================================

Prerequisites:
✅ All tests passing: Test suite passed (124 tests, 0 failures)
✅ Artifacts compiled: TypeScript compiled successfully
✅ Git tag ready: v0.16.0 tag created
✅ Version synced: All package.json files match v0.16.0
✅ GitHub release prepared: Release notes drafted
⚠️ Desktop installers: Not yet built (will build during publish)

Confidence: 0.95 (HIGH)
- All critical prerequisites met
- Automated script will handle remaining steps

Gaps: None

Critical Junction: YES (ALWAYS for publish - high-impact operation)
- Publishing affects all users
- Irreversible operation (can't un-publish)
- Requires explicit user approval

Plan:
1. Run full test suite (verify all pass) - 2 min
2. Compile all packages - 3 min
3. Build desktop installers - 5 min
4. Publish to npm (4 packages) - 2 min
5. Create GitHub release - 1 min
6. Upload artifacts (.vsix, installers) - 2 min
7. Verify all packages published - 1 min

Estimated time: 15-20 min
Ready to proceed: PAUSED ⏸️ (awaiting user approval)

Do you want to proceed with publishing v0.16.0? This will:
- Publish 4 npm packages
- Create GitHub release
- Upload artifacts for user download

Type 'yes' to proceed or 'no' to cancel.
```

### Example 4: Test Workflow Check

```
User: "Set up testing for WorkflowCheck service"

Claude: "Running Test Workflow Check..."

🔍 Test Workflow Check: WorkflowCheck Service
================================================================

Prerequisites:
✅ Test runner configured: Mocha with TDD UI
✅ Test files location: vscode-lumina/test/services/
✅ Test framework: Mocha + Sinon for mocking
⚠️ Coverage tool available: Not configured (optional for now)

Confidence: 0.85 (HIGH)
- Test infrastructure ready
- Can proceed without coverage tool (add later)

Gaps:
- Coverage tool not configured (suboptimal but not blocking)

Critical Junction: NO (routine test setup)

Plan:
1. Create test file: workflowCheck.test.ts - 5 min
2. Write test cases (TDD RED phase) - 45 min
   - 15 tests covering all workflow types
   - Error handling tests
   - Performance benchmarks
3. Run tests - verify they FAIL - 2 min
4. Implement WorkflowCheck to pass tests (GREEN phase) - 2 hours
5. Refactor and optimize (REFACTOR phase) - 30 min

Estimated time: 3-4 hours
Ready to proceed: YES ✅

[Claude proceeds with TDD workflow]
```

### Example 5: Documentation Workflow Check

```
User: "Document the Communication Protocol pattern"

Claude: "Running Documentation Workflow Check..."

🔍 Documentation Workflow Check: Pattern-COMM-001
================================================================

Reusability Assessment: HIGH

Reasoning:
- Referenced in: WorkflowCheck.ts, CLAUDE.md, agent contexts (3+ places)
- Core workflow process used across all development
- Will be reused by all future agents and developers

Recommendation: Create Pattern Document ✅
  File: docs/patterns/Pattern-COMM-001-Universal-Communication.md
  Sections: Problem, Solution, Implementation, Examples, Related Patterns
  Estimated time: 2 hours

Alternative: In-chat explanation only (NOT RECOMMENDED for high reusability)

Prerequisites:
✅ Pattern template exists: docs/patterns/ directory with 77 patterns
✅ Pattern-DOCUMENTATION-001: Style guide available
✅ Examples available: WorkflowCheck.ts implementation complete

Confidence: 0.90 (HIGH)
- Clear requirements
- Implementation already complete (can document)
- Examples readily available

Gaps: None

Critical Junction: NO (routine documentation)

Plan:
1. Create pattern file - 5 min
2. Write Problem Statement - 15 min
3. Write Solution section - 15 min
4. Document Implementation (WorkflowCheck, CLAUDE.md) - 20 min
5. Write Examples (5 workflow types) - 40 min
6. List Related Patterns - 10 min
7. Add Chain of Thought - 15 min
8. Document Performance Metrics - 10 min
9. Document Edge Cases - 10 min

Estimated time: 2 hours
Ready to proceed: YES ✅

[Claude proceeds with pattern creation]
```

---

## Related Patterns

### Primary Related Patterns:

1. **Pattern-TASK-ANALYSIS-001 (Pre-Task Analysis Protocol)**
   - Runs BEFORE workflow check
   - 8-step analysis: agent verification, tech stack, integration, known issues, libraries, performance, TDD strategy, clarifications
   - Feeds context INTO workflow check

2. **Pattern-CODE-001 (Code Development Protocol)**
   - Uses workflow check for code development
   - Enforces TDD (tests first)
   - Defines edge cases (typo vs bug fix)

3. **Pattern-SPRINT-PLAN-001 (Sprint Planning Protocol)**
   - Uses workflow check for sprint creation
   - Always critical junction (user approval)
   - Verifies workspace analysis complete

4. **Pattern-TEST-001 (Testing Protocol)**
   - Uses workflow check for test setup
   - TDD workflow enforcement (RED-GREEN-REFACTOR)
   - Coverage requirements by task type

5. **Pattern-DOCS-001 (Documentation Protocol)**
   - Uses workflow check for documentation
   - Reusability assessment (High/Medium/Low/Ephemeral)
   - Pattern vs summary decision

### Supporting Patterns:

6. **Pattern-PUBLISH-002 (Publishing Enforcement)**
   - Publish workflow always critical junction
   - Automated script enforcement
   - Pre-publish checklist

7. **Pattern-TDD-001 (Test-Driven Development Ratchet)**
   - Testing protocol enforcement
   - Test requirements by task category
   - Pre-commit hook integration

8. **Pattern-CONFIDENCE-001 (Confidence-Based Analysis)**
   - Confidence scoring logic
   - Gap detection
   - Action recommendations (accept/fill_gaps/regenerate)

9. **Pattern-TRACKING-001 (Task Tracking & Pre-Commit Protocol)**
   - Strategic + tactical todo system
   - Pre-commit quality checklist
   - Artifact consolidation

10. **Pattern-SERVICE-001 (Service Integration with MiddlewareLogger)**
    - WorkflowCheck service architecture
    - Logging and performance tracking
    - Graceful degradation patterns

---

## Chain of Thought

### Why This Pattern Exists

**Problem Recognition:**
1. Users reported frustration: "I don't know what Claude is checking"
2. Surprise failures appeared without warning
3. Assumptions remained hidden until things broke
4. No way to verify Claude following workflows
5. Trust issues: "Is Claude actually doing TDD?"

**Solution Evolution:**
1. Initially: No announcements, blind execution
2. Evolution: Add simple status messages
3. Problem: Messages inconsistent, no standard format
4. Solution: Universal workflow check template
5. Enhancement: Rich status objects with remediation
6. Final: Integrated with confidence scoring and gap detection

### Design Decisions with Reasoning

**1. Standard Template for ALL Workflows**

**Decision:** Use same announcement format regardless of workflow type

**Why:**
- Consistency builds user trust (predictable format)
- Easier for Claude to follow (one pattern, not six)
- Easier to audit (same structure everywhere)
- Reduces cognitive load (user knows what to expect)

**Trade-off:** Some workflows have unique needs → solved with workflow-specific prerequisites

**2. Rich Status Objects (✅/❌/⚠️ + Remediation)**

**Decision:** Prerequisites include status, details, remediation, impact

**Why:**
- Vibe coders need context (not just pass/fail)
- Engineers need transparency (details + reasoning)
- Actionable guidance (remediation = "here's how to fix")
- Impact clarity (blocking vs degraded vs suboptimal)

**Trade-off:** More verbose output → accepted for transparency benefit

**3. Confidence Scoring (0.0-1.0)**

**Decision:** Quantify readiness with numerical score

**Why:**
- Objective measure of preparedness
- Critical junction threshold (< 0.80 = ask user)
- Integrates with ConfidenceScorer service
- Visible progress toward readiness

**Trade-off:** Score calculation complexity → abstracted into service

**4. Critical Junction Detection**

**Decision:** Some workflows always require user approval

**Why:**
- High-impact operations (publish, sprint) need oversight
- Low confidence (< 0.80) indicates risk
- User control over major decisions
- Prevents surprise actions

**Trade-off:** Extra user interaction → worth it for control

**5. Execution Plan Display**

**Decision:** Show step-by-step plan BEFORE executing

**Why:**
- User sees what will happen (transparency)
- Opportunity to object before action
- Claude explains reasoning (accountability)
- Time estimates help planning

**Trade-off:** Slightly longer announcements → accepted for visibility

**6. Graceful Degradation**

**Decision:** Workflow check continues even if services fail

**Why:**
- ConfidenceScorer unavailable → default confidence 0.5
- TestValidator fails → show error, suggest manual check
- Git command fails → warn but don't crash
- Always return SOMETHING useful

**Trade-off:** Partial results less accurate → better than no results

### Trade-Offs Considered

**Verbosity vs Transparency:**
- Could make announcements shorter
- Chose transparency (full details) over brevity
- User can skim if experienced

**Performance vs Thoroughness:**
- Could skip some checks to be faster
- Chose thoroughness (all prerequisites)
- Mitigated with caching (>80% hit rate)

**Automation vs Control:**
- Could auto-proceed for simple workflows
- Chose user control (critical junctions)
- Balances efficiency with oversight

---

## Performance Metrics

### Workflow Check Performance:

**Target:** <500ms per workflow check

**Breakdown:**
- Git commands: <100ms (status, branch check)
- ConfidenceScorer: <100ms (if includeTestValidation=false)
- TestValidator: <200ms (if included)
- Aggregation & logic: <100ms

**Caching:**
- Target hit rate: >80% for repeated checks
- Cache key: workflow type + context hash
- Cache invalidation: On context change

**Timeout Protection:**
- Max duration: 10s per workflow check
- Timeout behavior: Return partial result with warning
- Prevents hanging operations

### Token Efficiency:

**Cost per workflow check:** ~300-500 tokens
- Template structure: ~100 tokens
- Prerequisites display: ~100-200 tokens
- Plan generation: ~100-200 tokens

**ROI:**
- Prevents 2-9 hour debugging sessions (2000+ tokens)
- Catches issues before implementation
- Token investment: 10-20x return

### Success Metrics:

**User Trust:**
- Measured by: User can explain what Claude is checking
- Target: 100% transparency (user sees all decisions)

**Workflow Compliance:**
- Measured by: TDD followed, tests written first
- Target: 100% compliance (enforced by protocol)

**Bug Prevention:**
- Measured by: Issues caught before commit
- Target: 80% of potential bugs caught early

---

## Edge Cases

### Edge Case 1: Typo Fix (Skip Workflow Check)

**Scenario:** User asks "Fix typo in comment on line 42"

**Behavior:** Skip workflow check

**Why:**
- Typo doesn't require tests
- Typo doesn't require sprint task
- Typo doesn't affect production behavior
- Overhead not justified

**Implementation:**
```typescript
// Check if trivial change (typo, comment, whitespace)
if (isTrivialChange(context)) {
  return createMinimalResult(workflowType, context);
}
```

### Edge Case 2: Emergency Hotfix

**Scenario:** Production is down, need immediate fix

**Behavior:**
- Run workflow check (shows prerequisites)
- Note emergency context
- Ask user: "Skip tests for emergency deploy?"
- Document decision in commit message

**Why:**
- Transparency still important (what's being skipped)
- User makes conscious decision
- Documented for retrospective
- Can't skip workflow check entirely (need git status, etc.)

### Edge Case 3: Documentation-Only Change

**Scenario:** Update README, no code changes

**Behavior:**
- Run documentation workflow check
- Reusability assessment
- No tests required (0% coverage for docs)
- Simplified prerequisites

**Why:**
- Documentation has different quality criteria
- No code = no tests needed
- Still need workflow check (reusability, git status)

### Edge Case 4: Refactoring (No Behavior Change)

**Scenario:** Refactor code, behavior unchanged

**Behavior:**
- Run code workflow check
- Prerequisites: existing tests must still pass
- No NEW tests required (behavior unchanged)
- Warning if tests fail (behavior did change!)

**Why:**
- Refactoring shouldn't break behavior
- Existing tests validate behavior unchanged
- If tests fail → not a true refactor

### Edge Case 5: Experimental Code (Spike/POC)

**Scenario:** "Let's try this approach, just exploring"

**Behavior:**
- Run code workflow check
- Mark as experimental in commit message
- Lower quality bar (tests optional)
- Must document findings

**Why:**
- Experiments still benefit from workflow visibility
- Different quality criteria (learning vs production)
- Findings documented for future reference

### Edge Case 6: Workflow Check Service Unavailable

**Scenario:** WorkflowCheck.ts itself is broken

**Behavior:**
- Fallback to manual workflow check
- Claude announces: "WorkflowCheck unavailable, using manual protocol"
- Follow CLAUDE.md protocol manually
- Self-healing: Fix WorkflowCheck before proceeding

**Why:**
- System must work even when tools broken
- Protocol > tooling (protocol is source of truth)
- Dogfooding: Fix tools using the protocol

---

## Usage Guidelines

### When to Use This Pattern:

✅ **Always:**
- Before writing ANY production code
- Before creating ANY sprint
- Before publishing ANY release
- Before setting up ANY test workflow
- Before creating ANY documentation

❌ **Skip for:**
- Typo fixes in comments/documentation
- Whitespace changes
- Trivial formatting adjustments

### How to Use This Pattern:

**Step 1:** Identify workflow type
- Code, sprint, publish, test, docs, or git?

**Step 2:** Gather context
- What information does this workflow need?
- Task ID, git status, files, configuration, etc.

**Step 3:** Call WorkflowCheck service
```typescript
const result = await workflowCheck.checkWorkflow(workflowType, context);
```

**Step 4:** Announce results to user
```
🔍 [Workflow Type] Workflow Check: ...
```

**Step 5:** Handle critical junctions
```typescript
if (result.criticalJunction) {
  const approval = await askUserApproval(result);
  if (!approval) return; // Don't proceed
}
```

**Step 6:** Execute workflow
- Follow the plan from workflow check
- Use TodoWrite for progress tracking

---

## Validation

### Pattern Effectiveness Metrics:

**1. User Transparency** (Target: 100%)
- Can user explain what's being checked? YES/NO
- Does user understand confidence score? YES/NO
- Are prerequisites clear? YES/NO

**2. Workflow Compliance** (Target: 100%)
- TDD followed? (tests first) YES/NO
- Sprint tasks created? YES/NO
- Git status checked? YES/NO

**3. Bug Prevention** (Target: 80%)
- Issues caught before commit? Count
- Rework avoided? Count
- Confidence scores accurate? YES/NO

**4. Performance** (Target: <500ms)
- Workflow check time: XXXms
- Cache hit rate: XX%
- Timeout rate: <1%

### Audit Questions:

1. **Does Claude announce workflow checks consistently?**
   - Review MiddlewareLogger output
   - Check for workflow check messages before actions

2. **Are prerequisites accurate?**
   - Do ✅ statuses match reality?
   - Are ❌ statuses caught and fixed?

3. **Are critical junctions respected?**
   - Does Claude always ask approval when required?
   - Does user have opportunity to object?

4. **Are plans followed?**
   - Does execution match announced plan?
   - Are deviations explained?

---

## Future Enhancements

**V1.1 - UI Integration:**
- Display workflow check in modal/panel (not just chat)
- Interactive prerequisites (click to fix)
- Visual confidence meter

**V1.2 - Workflow Recording:**
- Record all workflow checks to database
- Generate workflow compliance reports
- Trend analysis (confidence over time)

**V1.3 - Automated Remediation:**
- Some prerequisites auto-fixable (git clean → stash)
- Suggest fix commands (clickable buttons)

**V1.4 - Learning Mode:**
- Track which prerequisites frequently fail
- Suggest improvements to workflow setup
- Pattern emergence detection

---

## See Also

- **Implementation:** `vscode-lumina/src/services/WorkflowCheck.ts`
- **Protocol:** `.claude/CLAUDE.md` (6 protocol sections)
- **Tests:** `vscode-lumina/test/services/workflowCheck.test.ts`
- **Related:** Pattern-TASK-ANALYSIS-001, Pattern-CODE-001, Pattern-SPRINT-PLAN-001
