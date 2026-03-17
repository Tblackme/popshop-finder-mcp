# Pattern-CONTEXT-001: Hierarchical Context Organization

**CREATED:** 2025-10-04T21:59:45-05:00
**CATEGORY:** Information Architecture
**LANGUAGE:** Architecture
**QUALITY SCORE:** 0.75
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-FAILURE-001, PATTERN-TRACKING-001, PATTERN-NAPI-001, PATTERN-WHISPER-001, PATTERN-META-001

---




## Problem

Documentation scattered across repository without clear hierarchy. Phase-specific data mixed with global project memory. Agents unclear where to create/find documentation. Users confused by flat structure.

**Symptoms:**
- Execution reports at root directory
- Phase-specific data in global docs
- No clear separation of concerns
- Difficult to locate relevant information
- Documentation sprawl

---

## Solution

**DESIGN DECISION:** Organize documentation by context hierarchy
**WHY:** Information should live at appropriate specificity level

**REASONING CHAIN:**
1. Different information has different scope (global vs phase vs task)
2. Mixing scopes creates confusion and noise
3. Hierarchical organization improves discoverability
4. Clear structure guides agents and developers
5. Prevents documentation drift and duplication

---

## Context Levels

### Level 1: Global Context (CLAUDE.md)
**Scope:** Project-wide concerns

**Contains:**
- Project vision and goals
- Overall implementation status
- Cross-cutting patterns and principles
- Living Progress Log (high-level milestones only)
- Links to context-specific documentation

**DO NOT PUT HERE:**
- Phase-specific execution data
- Detailed bug analysis
- Task-level logs
- Agent-specific instructions

### Level 2: Phase Context (docs/execution/phase-N/)
**Scope:** Phase-specific execution

**Contains:**
- Phase execution reports (P{N}_EXECUTION_REPORT.md)
- Bug analysis and scoring (P{N}_BUG_ANALYSIS_AND_SCORING.md)
- Actual metrics (P{N}_ACTUAL_METRICS.md)
- Hallucination corrections
- Meta-analysis summaries

**DO NOT PUT HERE:**
- Global project status
- Reusable patterns (use docs/patterns/)
- Task-level logs (use logs/)

### Level 3: Pattern Context (docs/patterns/)
**Scope:** Reusable patterns extracted from any phase/task

**Contains:**
- Pattern-{TYPE}-{NNN}.md files
- Proven solutions to recurring problems
- Anti-patterns (Pattern-FAILURE-*)
- Cross-phase learnings

**DO NOT PUT HERE:**
- Phase-specific execution data
- One-off solutions (not yet proven reusable)
- Agent instructions

### Level 4: Agent Context (.claude/agents/)
**Scope:** Agent-specific instructions and memory

**Contains:**
- Agent system prompts
- Agent-specific patterns and validation rules
- Context scope definitions
- Documentation expectations for that agent

**DO NOT PUT HERE:**
- Global project memory
- Phase execution data
- Generic patterns (use docs/patterns/)

### Level 5: Task Context (logs/)
**Scope:** Individual task execution logs

**Contains:**
- P{N}-{TTT}.log files (e.g., P1-009.log)
- Real-time task execution output
- Command-by-command logs
- Task-specific debugging information

**DO NOT PUT HERE:**
- Phase summaries (use docs/execution/)
- Patterns (use docs/patterns/)
- Global status (use CLAUDE.md)

---

## Implementation

### Directory Structure

```
ÆtherLight_Lumina/
├── CLAUDE.md                          ← GLOBAL (Level 1)
├── README.md
├── PHASE_X_IMPLEMENTATION.md          ← Planning templates

├── .claude/
│   └── agents/                        ← AGENT CONTEXT (Level 4)
│       ├── rust-core-dev.md
│       ├── tauri-desktop-dev.md
│       ├── documentation-enforcer.md
│       └── commit-enforcer.md

├── docs/
│   ├── execution/                     ← PHASE CONTEXT (Level 2)
│   │   ├── README.md
│   │   ├── phase-1/
│   │   │   ├── P1_EXECUTION_REPORT.md
│   │   │   ├── P1_BUG_ANALYSIS_AND_SCORING.md
│   │   │   └── P1_ACTUAL_METRICS.md
│   │   └── phase-2/
│   │
│   ├── patterns/                      ← PATTERN CONTEXT (Level 3)
│   │   ├── README.md
│   │   ├── Pattern-FAILURE-001.md
│   │   ├── Pattern-TRACKING-001.md
│   │   └── ...
│   │
│   ├── vision/                        ← VISION & PHILOSOPHY
│   │   └── CHAIN_OF_THOUGHT_STANDARD.md
│   │
│   └── build/                         ← ARCHITECTURE & BUILD
│       └── AETHERLIGHT_TECHNICAL_ARCHITECTURE_2025.md

└── logs/                              ← TASK CONTEXT (Level 5)
    ├── README.md
    ├── P1-009.log
    └── ...
```

### Cross-Referencing Between Levels

**From Global to Phase:**
```markdown
# In CLAUDE.md
### **2025-10-04: Phase 1 Complete**
- Core library implemented
- VS Code extension shipped
- See: docs/execution/phase-1/P1_EXECUTION_REPORT.md
```

**From Phase to Pattern:**
```markdown
# In P1_EXECUTION_REPORT.md
**Pattern Extraction:** See Pattern-NAPI-001 (NAPI-RS Integration)
```

**From Pattern to Phase:**
```markdown
# In Pattern-NAPI-001.md
**Examples in Codebase:**
- Phase 1 implementation: docs/execution/phase-1/P1_EXECUTION_REPORT.md
```

### Agent Behavior

**When creating documentation, agents should:**

1. **Identify context level:** Is this global, phase, pattern, agent, or task data?
2. **Create in correct location:** Use hierarchical structure
3. **Use consistent naming:** P{N}_EXECUTION_REPORT.md format
4. **Cross-reference:** Link between levels appropriately
5. **Update indices:** Keep README.md files current

**Example (rust-core-dev completing Phase 2):**

```markdown
# Agent creates:
- docs/execution/phase-2/P2_EXECUTION_REPORT.md (phase context)
- docs/patterns/Pattern-WHISPER-001.md (extracted pattern)
- logs/P2-007.log (task log already exists)

# Agent updates:
- CLAUDE.md Living Progress Log (high-level summary + link)
- docs/execution/README.md (add phase-2 to structure)
- docs/patterns/README.md (add new pattern)
```

---

## When to Use

**Use this pattern when:**
- Organizing new documentation
- Creating execution reports after phase completion
- Extracting patterns from implementation
- Updating project memory
- Onboarding new agents or developers

**Signs you need this pattern:**
- Documentation at wrong context level (P1 reports at root)
- Can't find relevant information
- CLAUDE.md getting too large with phase details
- Agents creating docs in inconsistent locations
- Broken cross-references

---

## Alternatives Considered

### Alternative 1: Flat Structure (All docs at root)
**Rejected because:**
- Doesn't scale beyond ~20 documents
- No clear separation of concerns
- Difficult to navigate
- Mixes global with local context

### Alternative 2: Type-Based Organization (docs/reports/, docs/metrics/, docs/analysis/)
**Rejected because:**
- Splits related phase information across directories
- Harder to find all phase-related docs
- Doesn't reflect context hierarchy
- Obscures relationships

### Alternative 3: Date-Based Organization (docs/2025-10-04/, docs/2025-10-05/)
**Rejected because:**
- Phases span multiple dates
- Chronological order != logical grouping
- Difficult to find related content
- No clear context separation

---

## Edge Cases

### Case 1: Pattern Applies to Multiple Phases
**Solution:** Create pattern in docs/patterns/, reference from all relevant phase reports

### Case 2: Global Change Triggered by Phase Execution
**Solution:**
- Document detailed change in phase report
- Update CLAUDE.md with high-level summary + link

### Case 3: Agent-Specific Pattern
**Solution:**
- If reusable across agents: docs/patterns/
- If agent-specific only: .claude/agents/{agent-name}.md

### Case 4: Cross-Phase Analysis
**Solution:** Create in docs/execution/ at root level (not in phase-N/), name descriptively (e.g., CROSS_PHASE_ANALYSIS.md)

---

## Related Patterns

- **Pattern-META-001:** Documentation Feedback Loop
- **Pattern-TRACKING-001:** Comprehensive Execution Tracking
- **Pattern-TRACKING-002:** Honest Execution Metrics
- **Pattern-FAILURE-001:** Memory Leak in Task Execution

---

## Examples in Codebase

### Before (Flat Structure)
```
ÆtherLight_Lumina/
├── CLAUDE.md
├── P1_EXECUTION_REPORT.md              ← Wrong location
├── P1_BUG_ANALYSIS_AND_SCORING.md      ← Wrong location
├── HALLUCINATION_CORRECTION_SUMMARY.md ← Wrong location
└── docs/
    └── patterns/
```

### After (Hierarchical Structure)
```
ÆtherLight_Lumina/
├── CLAUDE.md                           ← Global context only
├── docs/
│   ├── execution/
│   │   └── phase-1/
│   │       ├── P1_EXECUTION_REPORT.md      ← Correct location
│   │       └── P1_BUG_ANALYSIS_AND_SCORING.md
│   └── patterns/
│       └── Pattern-CONTEXT-001.md      ← This file
```

---

## Future Improvements

1. **Automated validation:** Script to detect documentation at wrong level
2. **Index generation:** Auto-generate README.md files from structure
3. **Cross-reference checker:** Validate all links between context levels
4. **Template generator:** CLI tool to create properly-structured docs
5. **Agent prompts:** Embed this pattern in all agent system prompts

---

## Metrics

**Success indicators:**
- Zero phase-specific docs at root (after reorganization)
- All agents consistently use correct locations
- Users can find information in <30 seconds
- No duplicate documentation
- Clean git history (no file moves after initial organization)

---

**PATTERN:** Information Architecture
**PREVENTS:** Documentation sprawl, context confusion, broken cross-references
**ENABLES:** Scalable documentation, clear agent behavior, efficient navigation

**LAST UPDATED:** 2025-10-04T21:59:45-05:00
