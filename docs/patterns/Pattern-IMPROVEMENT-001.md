# Pattern-IMPROVEMENT-001: Gap Detection & Self-Improvement Protocol

**CREATED:** 2025-11-08
**CATEGORY:** Meta-Pattern (System Improvement)
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.98
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-CODE-001, PATTERN-DOCS-001, PATTERN-TDD-001, PATTERN-XYZ-001, PATTERN-GIT-001

---


## Problem

Systems degrade over time without self-improvement mechanisms:
- Missing patterns go undocumented (knowledge lost)
- Missing skills prevent task completion (workflow blocked)
- Missing agents leave tasks unassigned (no expert available)
- Missing tests allow bugs to slip through (Pattern-TDD-001 violations)
- Missing documentation leaves decisions unexplained (context lost)

**Without this protocol:**
- Workarounds become permanent (technical debt accumulates)
- Knowledge stays in chat logs (not reusable)
- System doesn't evolve (stagnation)
- User has no visibility or control (surprises)

---

## Solution

**MANDATORY: Propose creating missing patterns/skills/agents instead of working around**

When gaps are detected, propose filling them instead of silently working around. User has visibility and control over system improvements.

---

## Gap Types

### 1. Missing Pattern

**Detected:** Task references Pattern-XYZ-001 but it doesn't exist

**Impact:** Degraded (can work without pattern, but suboptimal)

**Proposal:** Create pattern document (estimated 2 hours)

**Example:**
```
Gap Detected: Missing Pattern-GIT-001

Gap Type: Pattern
Impact: Suboptimal (can work without, but less efficient)
Description: Git workflow integration pattern referenced but doesn't exist

Proposal: Create Pattern-GIT-001 document
  File: docs/patterns/Pattern-GIT-001-Git-Workflow.md
  Estimated time: 2 hours
  Benefit: Standardizes git workflow across all agents
  Reusability: HIGH (used in code, sprint, publish workflows)

Options:
1. Create now (add to current task, extend timeline)
2. Workaround (proceed without pattern, note for future)
3. Defer (create separate task, add to backlog)

Recommendation: Defer (don't block current task)
```

---

### 2. Missing Skill

**Detected:** Task requires "publish" skill but not available in AgentRegistry

**Impact:** Blocking (can't complete task without skill)

**Proposal:** Create skill definition (estimated 1 hour)

**Example:**
```
Gap Detected: Missing "publish" skill

Gap Type: Skill
Impact: Blocking (can't complete publish task without skill)
Description: Task POST-005 requires publish skill, but it's not in AgentRegistry

Proposal: Create publish skill
  File: .claude/skills/publish/SKILL.md
  Estimated time: 1 hour
  Benefit: Automated publishing workflow (Pattern-PUBLISH-002)
  Reusability: HIGH (every release uses this)

Options:
1. Create now (required to proceed)
2. Manual workaround (run commands manually - NOT RECOMMENDED)
3. Skip task (defer to later)

Recommendation: Create now (blocking gap)
```

---

### 3. Missing Agent

**Detected:** Task assigned to "security-agent" but agent not in registry

**Impact:** Blocking (no agent to handle task)

**Proposal:** Create agent context file (estimated 2-3 hours)

**Example:**
```
Gap Detected: Missing security-agent

Gap Type: Agent
Impact: Blocking (no agent to handle security tasks)
Description: Sprint assigns tasks to security-agent, but agent doesn't exist

Proposal: Create security-agent context
  File: internal/agents/security-agent-context.md
  Estimated time: 2-3 hours
  Sections:
    - Agent identity and expertise
    - Responsibilities (auth, encryption, validation)
    - Tools and techniques
    - Common pitfalls
    - Related patterns (Pattern-AUTH-001, Pattern-RLS-001)
  Benefit: Proper agent for security-critical tasks
  Reusability: HIGH (all security tasks need this agent)

Options:
1. Create now (required for sprint execution)
2. Reassign to different agent (infrastructure-agent - suboptimal)
3. Skip security tasks (NOT RECOMMENDED)

Recommendation: Create now (blocking gap, security-critical)
```

---

### 4. Missing Test

**Detected:** Production code without test file (Pattern-TDD-001 enforcement)

**Impact:** Blocking (Pattern-TDD-001 enforcement)

**Proposal:** Write tests first (TDD RED phase)

**Example:**
```
Gap Detected: Missing test file for WorkflowCheck.ts

Gap Type: Test
Impact: Blocking (Pattern-TDD-001: TDD required for all production code)
Description: WorkflowCheck.ts exists but no test file found

Proposal: Write tests first (TDD RED phase)
  File: vscode-lumina/test/services/workflowCheck.test.ts
  Estimated time: 1-2 hours
  Coverage: 90% (infrastructure task requirement)
  Test cases:
    - checkWorkflow('code') → validates TDD, tests, sprint task
    - checkWorkflow('sprint') → validates workspace, git, skills
    - checkWorkflow('publish') → validates tests, artifacts, git
    - Error cases (service unavailable, git failure)
    - Performance benchmarks (<500ms)

Options:
1. Write tests now (TDD RED phase) ✅ REQUIRED
2. Skip tests (FORBIDDEN - Pattern-TDD-001 violation)

Recommendation: Write tests now (blocking, mandatory)
```

---

### 5. Missing Documentation

**Detected:** High-reusability knowledge not documented (Pattern-DOCS-001)

**Impact:** Suboptimal (knowledge lost if not documented)

**Proposal:** Create pattern or update docs (estimated 1-2 hours)

**Example:**
```
Gap Detected: Pre-task analysis process not documented

Gap Type: Documentation
Impact: Suboptimal (knowledge lost, not reusable)
Description: 8-step pre-task analysis used in multiple workflows but not documented

Reusability Assessment: HIGH
- Referenced in: code workflow, sprint workflow, agent contexts (3+ places)
- Core process used across all development
- Permanent architecture decision

Proposal: Create Pattern-TASK-ANALYSIS-001
  File: docs/patterns/Pattern-TASK-ANALYSIS-001.md
  Estimated time: 2 hours
  Sections:
    - Problem (why this exists)
    - Solution (8-step analysis process)
    - When to use
    - Required steps (detailed)
    - Example output
    - Benefits (quantified)
  Benefit: Reusable process, prevents 2-9 hour debugging sessions
  Reusability: HIGH (all agents use this)

Options:
1. Create pattern now (high reusability)
2. Leave in chat (SUBOPTIMAL - knowledge lost)
3. Defer (create later when referenced again)

Recommendation: Create pattern now (high reusability)
```

---

## Gap Detection Workflow

### Step 1: Detect Gap

During workflow execution, detect gaps:

```typescript
// Example: Detecting missing pattern
if (task.references.includes('Pattern-GIT-001')) {
  const patternExists = await checkPatternExists('Pattern-GIT-001');
  if (!patternExists) {
    // Gap detected!
    this.reportGap({
      type: 'pattern',
      name: 'Pattern-GIT-001',
      impact: 'suboptimal',
      description: 'Git workflow pattern referenced but missing'
    });
  }
}
```

### Step 2: Assess Impact

Determine impact level:

- **Blocking:** Can't proceed without filling gap (missing skill, agent, test)
- **Degraded:** Can proceed but suboptimal (missing pattern, outdated docs)
- **Informational:** Nice to have but not critical (optional optimization)

### Step 3: Generate Proposal

Create structured proposal:

```
Gap Detected: [Name]

Gap Type: [Pattern/Skill/Agent/Test/Documentation]
Impact: [Blocking/Degraded/Informational]
Description: [What's missing and why it matters]

Proposal: [What to create]
  File: [Path to new file]
  Estimated time: [Hours]
  Benefit: [Why this matters]
  Reusability: [HIGH/MEDIUM/LOW]

Options:
1. Create now (add to current task)
2. Workaround (continue with degraded functionality)
3. Defer (create separate task)

Recommendation: [Suggested option with reasoning]
```

### Step 4: User Approval

Use AskUserQuestion tool:

```typescript
await askUserQuestion({
  questions: [{
    question: "I detected a gap: Missing Pattern-GIT-001. How should I proceed?",
    header: "Gap Detected",
    multiSelect: false,
    options: [
      {
        label: "Create now",
        description: "Add to current task (extends timeline by 2 hours)"
      },
      {
        label: "Workaround",
        description: "Continue without pattern (suboptimal but faster)"
      },
      {
        label: "Defer",
        description: "Create separate task for later (add to backlog)"
      }
    ]
  }]
});
```

### Step 5: Execute Decision

Based on user choice:

**Option 1: Create Now**
```
✅ User approved: Create now
📝 Adding Pattern-GIT-001 to current task
⏱️  Extending timeline by 2 hours
🔄 Updating todo list with new subtask
```

**Option 2: Workaround**
```
⚠️  User chose: Workaround
📝 Proceeding without Pattern-GIT-001 (degraded functionality)
📋 Noted for future: Create Pattern-GIT-001 when time permits
💡 Logged gap in MiddlewareLogger for retrospective
```

**Option 3: Defer**
```
⏭️  User chose: Defer
📋 Created backlog task: Create Pattern-GIT-001
🗓️  Estimated: 2 hours
📝 Added to sprint backlog for future sprint
```

---

## Gap Tracking

### Logging

All gaps logged in MiddlewareLogger:

```typescript
logger.log('gap-detected', {
  type: 'pattern',
  name: 'Pattern-GIT-001',
  impact: 'suboptimal',
  taskId: 'PROTO-001',
  decision: 'defer',
  timestamp: Date.now()
});
```

### Retrospective Analysis

Gap log reviewed during sprint retrospectives:

```
Sprint Retrospective: 2025-01-06

Gaps Detected (5 total):
1. Pattern-GIT-001 (deferred) - Git workflow pattern
2. security-agent (created) - Security task agent
3. Test for API-003 (created) - TDD enforcement
4. Pattern-IMPROVEMENT-001 (created) - Gap detection protocol
5. KNOWN_ISSUES.md (created) - Historical bug reference

Patterns Emerging:
- Missing patterns: 2 (need to document more workflows)
- Missing agents: 1 (security coverage needed improvement)
- Missing tests: 1 (TDD enforcement working)

Actions:
- Create Pattern-GIT-001 in next sprint
- Review agent coverage for remaining domains
- Continue TDD enforcement (1 gap acceptable)
```

### Pattern Recognition

Recurring gaps indicate systematic improvement needed:

```
Recurring Gap Pattern: Documentation

Observed: 4 sprints, 12 gaps total
Pattern: Documentation gaps recurring (8 of 12)
Root Cause: Not documenting workflows as they're created
Solution: Proactive Pattern-DOCS-001 enforcement

Action: When creating new workflow, immediately assess:
  - Is this reusable? (3+ uses)
  - Should this be a pattern?
  - Document NOW vs. defer?
```

---

## Self-Improvement Cycle

```
┌──────────────────────────────────────────────┐
│ Gap Detected During Workflow                  │
│ (Pattern, Skill, Agent, Test, Documentation) │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Proposal Generated                            │
│ - Type, Impact, Description                   │
│ - Options (Create/Workaround/Defer)          │
│ - Recommendation with reasoning               │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ User Approval (AskUserQuestion)               │
│ - Create now (extend timeline)                │
│ - Workaround (degraded functionality)         │
│ - Defer (backlog task)                        │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Gap Filled (if approved)                      │
│ - Pattern created                             │
│ - Skill added                                 │
│ - Agent context written                       │
│ - Tests written                               │
│ - Documentation updated                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ System Improved                               │
│ - Gap no longer exists                        │
│ - Future workflows benefit                    │
│ - Knowledge preserved                         │
│ - Retrospective data collected                │
└───────────────────────────────────────────────┘
```

---

## Benefits

1. **System improves itself over time**
   - Gaps get filled systematically
   - Knowledge accumulates in patterns
   - Workflows become more efficient

2. **Missing patterns get documented**
   - Reusable knowledge preserved
   - Future work references existing patterns
   - Token usage decreases (patterns vs. re-explaining)

3. **Missing agents get created**
   - Task coverage improves
   - Expertise matched to tasks
   - Better outcomes

4. **User has visibility and control**
   - No silent workarounds
   - User decides create vs. defer
   - Budget and timeline transparency

5. **Retrospective analysis identifies trends**
   - Recurring gaps indicate systemic issues
   - Pattern recognition drives improvement
   - Resource allocation optimized

---

## Enforcement

### Self-Accountability

Claude MUST propose gap filling (not work around silently)

**Bad (Silent Workaround):**
```
// Missing Pattern-GIT-001, but continue without mention
// User has no visibility, gap never filled
```

**Good (Propose Gap Filling):**
```
Gap Detected: Missing Pattern-GIT-001

[Structured proposal with options]

Asking user for decision...
```

### User Control

User ALWAYS has final decision:
- Create now (extend timeline)
- Workaround (degraded, note for future)
- Defer (backlog task)

### Tracking

Gaps tracked in MiddlewareLogger for retrospective analysis

---

## Related Patterns

- **Pattern-TASK-ANALYSIS-001:** Pre-Task Analysis (detects gaps in step 8)
- **Pattern-CODE-001:** Code Development (checks for gaps before coding)
- **Pattern-DOCS-001:** Documentation Protocol (assesses reusability)
- **Pattern-TDD-001:** Test-Driven Development (enforces test existence)

---

## Version History

- **v1.0.0** (2025-01-06): Initial extraction from CLAUDE.md
  - Formalized 5 gap types with examples
  - Added gap detection workflow (5 steps)
  - Integrated with AskUserQuestion tool
  - Added gap tracking and retrospective analysis
  - Documented self-improvement cycle
