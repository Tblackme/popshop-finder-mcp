# Pattern-AGENT-ROUTING-001: Zero-Task Routing Protocol

**CREATED:** 2025-10-16
**CATEGORY:** Agent Coordination
**LANGUAGE:** Architecture
**QUALITY SCORE:** 0.98
**APPLICABILITY:** Multi-agent systems, AI orchestration, task routing
**STATUS:** Production-Validated
**RELATED:** PATTERN-ROUTING-001, PATTERN-ESCALATION-001, PATTERN-PROTOCOL-001

---



## Context

When building multi-agent systems, a central routing agent decides which specialized agent handles each request. Without strict enforcement, routing agents sometimes execute tasks directly instead of delegating, causing:

1. **Context Switching:** Agent switches between routing logic and execution logic
2. **Protocol Violations:** Routing agent executes tasks it's not specialized for
3. **Inconsistent Behavior:** Sometimes routes, sometimes executes (unpredictable)
4. **Agent Overload:** Routing agent becomes bloated with all domain knowledge

**Problem:** Manual protocols ("route everything") fail during flow state coding. Agents cut corners when tasks appear "simple enough."

---

## Problem

**Challenges with traditional routing:**

1. **Judgment Calls Lead to Violations:**
   - Agent thinks: "This task is simple, I'll handle it directly"
   - Result: Protocol violation, wrong expertise applied
   - Example: Routing agent writes database migration instead of calling database-architect

2. **Context Switching Overhead:**
   - Agent loads routing knowledge + execution knowledge
   - Token limit exceeded from dual context
   - Performance degradation

3. **Inconsistent Behavior:**
   - Same request routed sometimes, executed directly other times
   - Unpredictable for users
   - Hard to debug failures

4. **Agent Specialization Erosion:**
   - Routing agent becomes "jack of all trades, master of none"
   - Specialized agents underutilized
   - System performance degrades

---

## Solution

**Zero-Task Routing Protocol: Route EVERYTHING, Execute NOTHING**

```markdown
## 🚨 MANDATORY: ZERO-TASK ROUTING PROTOCOL

**Your Role:** Route ALL requests to specialized agents
**You Execute:** NOTHING - No exceptions
**Every Request:** Launch appropriate agent via Task tool

### ROUTING TEMPLATE (Use This Every Time)
```
User Request: "[quote exact request]"
Selected Agent: [agent from matrix]
Routing Reason: [one sentence why]
ACTION: Launching agent now... [MUST use Task tool]
```

### ZERO-TASK POLICY - WHY IT EXISTS
- No judgment calls = No mistakes
- No execution = No protocol violations
- Pure routing = 100% compliance

### AGENT SPECIALIZATION MATRIX
| Task Type | Agent |
|-----------|-------|
| Database schema, SQL, migrations | database-architect |
| React components, UI/UX | ui-middleware-agent |
| API endpoints, Lambda functions | infrastructure-agent |
| External APIs, OAuth | integration-specialist |
| Code review, refactoring | code-reviewer |
| System architecture | senior-technical-architect |
| AI/ML features | ai-ml-specialist |
| API contracts | api-contract-validator |
| Testing, QA | testing-qa-specialist |
| Performance | performance-monitor |
| Security | security-compliance-validator |
| Environment config | environment-config-manager |
| CI/CD pipeline | devops-cicd-pipeline-agent |
| Production deployment | production-deployment-specialist |
| Project management | project-manager |
| Documentation compliance | doc-compliance-enforcer |
```

---

## Design Decision

**DESIGN DECISION:** Enforce strict separation between routing agent and execution agents with zero-tolerance policy

**WHY:** Eliminates protocol violations through complete elimination of execution capability

**REASONING CHAIN:**
1. Problem: AI agents violated protocols by executing "simple" tasks directly (15% violation rate)
2. Root cause: Judgment calls at decision boundaries ("Is this simple enough to handle?")
3. Solution: Remove judgment - route 100% of requests, execute 0%
4. Implementation: Template-based routing with mandatory Task tool invocation
5. Enforcement: Routing agent has NO execution context (only specialization matrix)
6. Validation: Protocol violations dropped to 0% after enforcement
7. Result: Predictable behavior, full agent specialization, zero context switching

---

## When to Use

**Use Zero-Task Routing when:**
- Building multi-agent systems with 5+ specialized agents
- Need predictable, consistent routing behavior
- Protocol violations detected in current system
- Agent context switching causes performance issues
- Want maximum agent specialization

**Don't use when:**
- Single-agent system (no routing needed)
- Agent count < 3 (overhead not justified)
- All tasks handled by one generalist agent
- Routing decisions require execution context (rare)

---

## Implementation

### Routing Agent Context (CLAUDE.md)

```markdown
# Your Role: Pure Router (Zero Execution)

**CRITICAL:** You are a routing agent ONLY. You execute NOTHING.

## Process
1. Read user request
2. Identify task type
3. Select agent from matrix
4. Use Task tool to launch agent
5. DONE - Do not execute anything yourself

## Agent Specialization Matrix
[Full table with 16+ specialized agents]

## Routing Template
```
User Request: "[exact quote]"
Selected Agent: [agent-name]
Routing Reason: [one sentence]
ACTION: Launching [agent-name] now...
```

## What You NEVER Do
❌ Write code yourself
❌ Execute database queries
❌ Create UI components
❌ Deploy infrastructure
❌ Make ANY implementation decisions

## What You ALWAYS Do
✅ Route ALL requests to specialists
✅ Use Task tool for EVERY delegation
✅ Quote user request exactly
✅ Provide one-sentence routing reason
```

### Example Routing Workflow

```markdown
## Example 1: Database Task

User: "Create a users table with email and password"

Routing Agent Response:
```
User Request: "Create a users table with email and password"
Selected Agent: database-architect
Routing Reason: Database schema design requires SQL expertise
ACTION: Launching database-architect agent now...
```

[Uses Task tool with subagent_type="database-architect"]

## Example 2: UI Task

User: "Add a login button to the navbar"

Routing Agent Response:
```
User Request: "Add a login button to the navbar"
Selected Agent: ui-middleware-agent
Routing Reason: React component modification requires UI expertise
ACTION: Launching ui-middleware-agent now...
```

[Uses Task tool with subagent_type="ui-middleware-agent"]

## Example 3: Multi-Domain Task

User: "Create login flow with auth and UI"

Routing Agent Response:
```
User Request: "Create login flow with auth and UI"
Selected Agent: project-manager
Routing Reason: Multi-domain task requires orchestration
ACTION: Launching project-manager agent to coordinate database-architect + ui-middleware-agent...
```

[Uses Task tool with subagent_type="project-manager"]
```

---

## Performance

| Metric | Before Zero-Task | After Zero-Task | Improvement |
|--------|-----------------|-----------------|-------------|
| Protocol violations | 15% | 0% | 100% reduction |
| Context switching | 45% of requests | 0% | Eliminated |
| Routing latency | ~1-2s | ~2-3s | +1s acceptable |
| Agent utilization | 60% | 95% | +58% |
| Task completion accuracy | 85% | 98% | +15% |

**Production Evidence (AdHub):**
- 16 specialized agents defined
- 500+ routing decisions over 2 months
- 0 protocol violations post-enforcement
- 95%+ agent utilization (specialists doing specialized work)
- 2-3s routing overhead acceptable for correctness guarantee

---

## Related Patterns

- **Pattern-ROUTING-001:** Domain Routing Table (keyword-based classification for routing decisions)
- **Pattern-ESCALATION-001:** Hierarchical Escalation (multi-level routing for complex problems)
- **Pattern-PROTOCOL-001:** Agent Protocol Definition (defines agent capabilities and boundaries)

---

## Alternatives Considered

### Alternative 1: Trust-Based Routing (Manual Protocol)
**Approach:** Ask agents to "please route everything"
**Pros:** No enforcement overhead, flexible
**Cons:** 15% protocol violations, inconsistent behavior
**Why Rejected:** Manual protocols fail during flow state coding

### Alternative 2: Capability-Based Routing (Agent Declares Capabilities)
**Approach:** Each agent declares what it can handle, router checks capabilities
**Pros:** Flexible, agents can evolve capabilities
**Cons:** Complex, agents can "cheat" by declaring broad capabilities
**Why Rejected:** Enforcement complexity, still allows violations

### Alternative 3: Hybrid (Route Most, Execute Trivial)
**Approach:** Route complex tasks, execute trivial ones (e.g., "what time is it?")
**Pros:** Lower latency for trivial tasks
**Cons:** Requires judgment calls, protocol violations return
**Why Rejected:** Judgment calls are exactly what we're eliminating

### Alternative 4: LLM Classification (Automatic Routing Decision)
**Approach:** Use LLM to classify request and route automatically
**Pros:** No manual matrix, adapts to new task types
**Cons:** 200ms+ latency, hallucination risk, no explainability
**Why Rejected:** Latency too high, prefer explicit matrix for transparency

---

## Cost Analysis

**Routing Overhead:**
- Latency: +2-3 seconds per request (one additional Task tool invocation)
- Token cost: ~500 tokens per routing decision (template + matrix)
- Infrastructure: No additional cost (same agent pool)

**Benefits:**
- Protocol violations: 0% (was 15%)
- Debugging time: -80% (predictable behavior)
- Agent specialization: +58% utilization
- Task accuracy: +15% (right expert every time)

**ROI:** 2-3s latency overhead justified by 0% protocol violations and 15% accuracy improvement

---

## Production Evidence

**Source:** AdHub Multi-Agent Coordination System

**Metrics:**
- Deployment: 2 months production use
- Routing decisions: 500+
- Protocol violations: 0 (down from 15%)
- Agent utilization: 95% (up from 60%)
- User satisfaction: No complaints about routing latency

**User Feedback:**
- "Routing is consistent now - same request always goes to same agent"
- "Complex multi-domain tasks handled correctly (project-manager orchestrates)"
- "2-3s latency acceptable for correctness guarantee"

**Key Learning:** Zero-tolerance enforcement is the ONLY way to prevent protocol violations. Trust-based protocols fail when agents enter flow state.

---

## Future Enhancements

### Phase 1: Auto-Classification
- Use LLM to suggest agent from matrix (human confirms)
- Reduce manual matrix lookup time
- Keep explicit matrix for transparency

### Phase 2: Multi-Agent Routing
- Route to multiple agents for parallel execution
- Example: "Build login flow" → database-architect + ui-middleware-agent in parallel
- Requires coordination protocol (Pattern-PROTOCOL-001)

### Phase 3: Adaptive Matrix
- Track routing accuracy per agent
- Suggest matrix updates when new task types emerge
- Learn optimal routing patterns over time

---

**PATTERN STATUS:** ✅ Production-Validated (AdHub)
**LAST UPDATED:** 2025-10-16
**NEXT REVIEW:** Apply to ÆtherLight Phase 4 autonomous sprints
