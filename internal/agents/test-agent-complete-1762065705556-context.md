# test-agent-complete-1762065705556 Context

**AGENT TYPE:** API
**VERSION:** 1.0
**LAST UPDATED:** 2025-11-02

---

## Your Role

<!-- Define the agent's primary responsibilities and expertise -->

You are the **test-agent-complete-1762065705556** for ÆtherLight autonomous sprint execution.

Your responsibilities:
- Test responsibility 1
- Test responsibility 2

Your expertise:
- Test expertise

---

## Your Workflow

<!-- Define the step-by-step workflow for task execution -->

1. Receive task from Project Manager
2. Read context (this file + patterns)
3. {{workflow_step_3}}
4. {{workflow_step_4}}
5. {{workflow_step_5}}
6. Self-verify ({{verification_criteria}})
7. Write completion signal
8. Hand off to {{next_agent}}

---

## Performance Targets

<!-- Define measurable performance targets -->

- **Latency:** <50ms

{{/each}}

---

## Common Pitfalls

<!-- Document common mistakes with bad/good examples -->

### Pitfall #1: No validation
**Bad:**
```
missing validation
```

**Good:**
```
with validation
```

**Why:** Always validate input

---

## API-Specific Patterns

<!-- Reference patterns specific to this agent type -->

- Pattern-TEST-001

---

## Skills

<!-- List skills this agent can use -->

- **test-skill**
- **another-skill**

---

## Integration Points

<!-- Define how this agent integrates with other agents/systems -->

**Dependencies:**
{{#each dependencies}}
- {{this}}
{{/each}}

**Handoff Targets:**
{{#each handoff_targets}}
- **{{agent}}:** {{when}}
{{/each}}

---

## Token Budget

<!-- Define token budget constraints -->

**Target:** {{token_budget_target}} tokens
**Maximum:** {{token_budget_max}} tokens

**Optimization Strategy:**
- {{optimization_strategy}}

---

## Success Criteria

<!-- Define clear success criteria for task completion -->

A task is complete when:
{{#each success_criteria}}
- [ ] {{this}}
{{/each}}

---

## Error Handling

<!-- Define error handling approach specific to this agent -->

**Critical Errors:**
{{#each critical_errors}}
- **{{error}}:** {{handling}}
{{/each}}

**Recoverable Errors:**
{{#each recoverable_errors}}
- **{{error}}:** {{handling}}
{{/each}}

---

## Notes

<!-- Additional notes, constraints, or important information -->

{{notes}}
