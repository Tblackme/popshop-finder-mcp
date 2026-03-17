# Project Manager Agent Context

**Role:** Sprint parsing, task scheduling, multi-terminal orchestration, and conflict resolution

**Agent Type:** Orchestration Agent (coordinates all other agents)
**Primary Domain:** Autonomous sprint execution
**Pattern Prefix:** Pattern-PM-*

---

## Responsibilities

1. **Sprint Parsing** - Parse PHASE_X_IMPLEMENTATION.md, extract tasks with dependencies
2. **Dependency Analysis** - Build dependency graph, identify critical path, detect cycles
3. **Task Scheduling** - Assign tasks to specialized agents, maximize parallelization
4. **Terminal Management** - Spawn agent terminals, monitor progress, handle crashes
5. **IPC Coordination** - File-based IPC, progress tracking, completion detection
6. **Conflict Resolution** - Detect file conflicts, coordinate merges, escalate to human
7. **Progress Reporting** - Real-time dashboard, completion estimates, blocker detection

---

## Relevant Code

### **Primary Files:**
```
vscode-lumina/src/project_manager/
├── sprint_parser.ts (Parse phase docs)
├── dependency_graph.ts (Build DAG)
├── task_scheduler.ts (Assign tasks)
├── terminal_manager.ts (Spawn/monitor agents)
├── ipc_coordinator.ts (File-based IPC)
└── conflict_resolver.ts (Merge conflicts)
```

### **IPC Files:**
```
.lumina/tasks/
├── database-agent-task.json (Task assignment)
├── ui-agent-task.json
└── ... (one per agent)

.lumina/progress/
├── database-agent-progress.json (Progress updates)
├── ui-agent-progress.json
└── ... (one per agent)

.lumina/completions/
├── database-agent-complete.json (Completion signals)
└── ... (one per agent)
```

---

## Patterns

### **Orchestration Patterns:**
- **Pattern-PM-001: Dependency-Aware Scheduling**
  - Build DAG from task dependencies
  - Schedule leaf nodes first (no dependencies)
  - Launch parallel agents for independent tasks
  - Wait for dependencies before scheduling dependent tasks

- **Pattern-PM-002: Terminal Lifecycle Management**
  - Spawn terminal with unique name
  - Inject specialized context
  - Monitor for completion signal
  - Handle crashes with retry logic

- **Pattern-PM-003: File-Based IPC**
  - Write task to `.lumina/tasks/agent-task.json`
  - Agent reads task, executes, writes progress
  - Monitor `.lumina/progress/` for updates
  - Detect completion via `.lumina/completions/`

### **Conflict Resolution:**
- **Pattern-PM-004: Optimistic Concurrency**
  - Agents work on separate files (no conflicts)
  - If conflict detected, pause both agents
  - Analyze conflict (git diff)
  - Auto-resolve or escalate to human

- **Pattern-PM-005: Critical Path Optimization**
  - Identify longest dependency chain
  - Schedule critical path first
  - Parallelize non-critical tasks
  - Minimize makespan

---

## Performance Targets

- **Sprint parsing:** <5s for 30-task sprint ✅
- **Dependency graph:** <1s for 100 tasks ✅
- **Terminal spawn:** <2s per agent ✅
- **IPC latency:** <100ms (file polling) ✅
- **Conflict detection:** <5s after completion ✅
- **Total sprint time:** 50-70% faster than sequential ✅

---

## Workflow

### **Step 1: Parse Sprint Document**
```typescript
const sprint = await sprintParser.parse("PHASE_4_AUTONOMOUS_SPRINTS.md");

// sprint.tasks = [
//   { id: "AS-001", title: "Project Manager Foundation", dependencies: [] },
//   { id: "AS-002", title: "Database Agent", dependencies: ["AS-001"] },
//   ...
// ]
```

### **Step 2: Build Dependency Graph**
```typescript
const graph = dependencyGraph.build(sprint.tasks);
const criticalPath = graph.findCriticalPath();
const parallelizable = graph.findParallelizableTasks();

// Example output:
// criticalPath: ["AS-001", "AS-002", "AS-005"] (8 days)
// parallelizable: [["AS-003", "AS-004"], ["AS-006", "AS-007"]] (can run in parallel)
```

### **Step 3: Schedule Tasks**
```typescript
const schedule = taskScheduler.schedule(graph, {
  maxParallelAgents: 5,
  prioritizeCriticalPath: true
});

// schedule = [
//   { day: 1, agents: ["database-agent: AS-001"] },
//   { day: 2, agents: ["database-agent: AS-002", "ui-agent: AS-003", "api-agent: AS-004"] },
//   ...
// ]
```

### **Step 4: Spawn Agents**
```typescript
for (const task of schedule.today) {
  const agent = await terminalManager.spawn({
    agentType: task.agentType,
    taskId: task.id,
    contextFiles: [
      "CLAUDE.md",
      `docs/agents/${task.agentType}-context.md`,
      ...task.relevantPatterns
    ]
  });

  agents.set(task.id, agent);
}
```

### **Step 5: Monitor Progress**
```typescript
const progressMonitor = new ProgressMonitor();

setInterval(async () => {
  for (const [taskId, agent] of agents) {
    const progress = await progressMonitor.read(`.lumina/progress/${agent.name}-progress.json`);

    console.log(`${taskId}: ${progress.percent}% complete`);

    if (progress.blockers.length > 0) {
      await handleBlockers(taskId, progress.blockers);
    }
  }
}, 5000); // Poll every 5 seconds
```

### **Step 6: Detect Completion**
```typescript
async function waitForCompletion(taskId: string): Promise<CompletionSignal> {
  while (true) {
    const completionFile = `.lumina/completions/${taskId}-complete.json`;

    if (await fs.exists(completionFile)) {
      const signal = await fs.readJSON(completionFile);
      return signal;
    }

    await sleep(1000); // Check every second
  }
}
```

### **Step 7: Resolve Conflicts**
```typescript
const conflicts = await conflictResolver.detect(completedTasks);

for (const conflict of conflicts) {
  const resolution = await conflictResolver.resolve(conflict);

  if (resolution.autoResolved) {
    console.log(`✅ Auto-resolved conflict in ${conflict.file}`);
  } else {
    await escalateToHuman(conflict);
  }
}
```

### **Step 8: Report Progress**
```typescript
const report = {
  sprint: "AS Sprint 1",
  totalTasks: 10,
  completed: 7,
  inProgress: 2,
  pending: 1,
  blockers: ["AS-005: Waiting for database schema"],
  estimatedCompletion: "2 days"
};

await dashboard.update(report);
```

---

## Common Pitfalls

### **1. Circular Dependencies**
**Problem:** Task A depends on Task B, Task B depends on Task A
**Detection:** Topological sort fails
**Solution:** Manual intervention, restructure tasks

### **2. Agent Crashes**
**Problem:** Agent crashes mid-task, leaves incomplete work
**Solution:** Retry logic (max 3 attempts), then escalate to human

### **3. File Conflicts**
**Problem:** Two agents modify same file simultaneously
**Prevention:** Schedule agents on different files
**Detection:** Git merge conflict after completion
**Resolution:** Pattern-PM-004 (Optimistic Concurrency)

### **4. IPC Latency**
**Problem:** Polling `.lumina/progress/` every 1s is slow
**Solution:** Use file system watchers (fs.watch) for instant updates

### **5. Terminal Saturation**
**Problem:** Spawning 10 terminals overwhelms VS Code
**Solution:** Limit to 5 parallel agents, queue remainder

---

## Integration with Phase 3.6 Infrastructure

### **AI-001: Code Map**
- Query code map before assigning tasks
- Assign agents to files with low impact radius first
- Detect potential conflicts (same module)

### **AI-002: Verification System**
- Verify agent claims before marking task complete
- Re-assign task if verification fails

### **AI-004: Session Handoff**
- Use handoff files to resume crashed agents
- Load previous progress, continue from checkpoint

### **AI-005: Pattern Index**
- Query relevant patterns for each task
- Inject patterns into agent context

### **AI-007: Shared Knowledge**
- Query discoveries before assigning tasks
- Warn agents about known pitfalls

### **AI-008: Uncertainty Quantification**
- If agent confidence <0.7, increase monitoring frequency
- Escalate low-confidence tasks to human review

### **AI-009: Agent Context Architecture**
- Inject specialized context when spawning agents
- Reduce token usage by 60%

---

## Example Sprint Execution

**Sprint:** Phase 4 Sprint 1 (10 tasks, 5 agents)

**Day 1:**
```
09:00 - Parse PHASE_4_AUTONOMOUS_SPRINTS.md
09:05 - Build dependency graph (10 tasks, 15 dependencies)
09:06 - Critical path: AS-001 → AS-002 → AS-005 (8 days)
09:07 - Spawn database-agent (AS-001: Project Manager Foundation)
09:10 - AS-001 started (database schema for task tracking)
12:00 - AS-001 progress: 60% (schema designed, migration written)
15:00 - AS-001 complete ✅ (tests passing, verified)
15:05 - Spawn 3 agents in parallel:
        - database-agent (AS-002: Database Agent Core)
        - ui-agent (AS-003: UI Agent Core)
        - api-agent (AS-004: API Agent Core)
```

**Day 2:**
```
09:00 - AS-002 complete ✅ (database agent operational)
09:00 - AS-003 progress: 80% (UI components done, testing)
09:00 - AS-004 complete ✅ (API endpoints operational)
11:00 - AS-003 complete ✅ (all 3 parallel tasks done)
11:05 - Spawn 2 agents:
        - infrastructure-agent (AS-005: Infrastructure Agent)
        - test-agent (AS-006: Test Agent)
15:00 - AS-005 progress: 50% (Docker setup, CI/CD config)
17:00 - AS-006 complete ✅ (test agent operational)
```

**Day 3:**
```
09:00 - AS-005 complete ✅ (infrastructure agent operational)
09:05 - Spawn remaining agents:
        - documentation-agent (AS-007)
        - review-agent (AS-008)
15:00 - AS-007 complete ✅
16:00 - AS-008 complete ✅
16:05 - Sprint 1 COMPLETE ✅ (10 tasks, 3 days, 70% faster than sequential)
```

---

## Summary

The Project Manager Agent orchestrates autonomous sprint execution:
- ✅ Parses sprint documents, extracts tasks
- ✅ Builds dependency graph, identifies critical path
- ✅ Schedules tasks, maximizes parallelization
- ✅ Spawns/monitors specialized agents
- ✅ Detects conflicts, resolves or escalates
- ✅ Reports progress, estimates completion

**Primary Goal:** 50-70% faster sprint execution with zero missed tasks

**Success Metric:** Sprint completion time, task completion rate (100%), conflict resolution rate

---

## Sprint Task Lifecycle Protocol (Pattern-TRACKING-001)

**Added:** 2025-01-12 (v1.1 - Sprint TOML automation)

### Before Starting ANY Task

**Update Sprint TOML status to "in_progress"**:

**Option 1 - Automated (Preferred)**:
```bash
/sprint-task-lifecycle start {TASK-ID}
```

**Option 2 - Manual (if skill unavailable)**:
1. Find task: `grep -n "^\[tasks.{TASK-ID}\]" internal/sprints/ACTIVE_SPRINT.toml`
2. Read task section (use Read tool)
3. Edit: `status = "pending"` → `status = "in_progress"`
4. Validate: `grep -A 1 "^\[tasks.{TASK-ID}\]" ... | grep status`

**Integration with TodoWrite**:
- Add Sprint TOML update as first TodoWrite item (Step 0A)
- Mark in_progress AFTER Sprint TOML updated
- Ensures Sprint Panel UI reflects current work

---

### After Completing ANY Task

**Update Sprint TOML status to "completed"**:

**Option 1 - Automated (Preferred)**:
```bash
/sprint-task-lifecycle complete {TASK-ID}
```

**Option 2 - Manual (if skill unavailable)**:
1. Read task section
2. Edit:
   ```
   old_string: status = "in_progress"
   new_string: status = "completed"
   completed_date = "2025-01-12"
   ```
3. Validate: Check both status and completed_date present

**Integration with TodoWrite**:
- Add Sprint TOML update as final TodoWrite item (Step N)
- Mark completed AFTER Sprint TOML updated
- Ensures Sprint Panel UI reflects task completion

---

### If Blocked/Deferred

**Update Sprint TOML status to "deferred"**:

**Option 1 - Automated (Preferred)**:
```bash
/sprint-task-lifecycle defer {TASK-ID} "Reason for deferral"
```

**Option 2 - Manual (if skill unavailable)**:
1. Edit:
   ```
   old_string: status = "in_progress"
   new_string: status = "deferred"
   deferred_reason = "{REASON}"
   ```
2. Document blocker, notify user, move to next task

---

**Full Protocol**: See Pattern-TRACKING-001 (Sprint TOML Lifecycle Management section)

**Validation**: Pre-commit hook runs `validate-sprint-schema.js` automatically
