# ÆtherLight Pattern Library Index

**VERSION:** 1.2 (Sprint 3 Complete - v0.17.0)
**LAST UPDATED:** 2025-11-08
**TOTAL PATTERNS:** 77+
**PATTERN:** Pattern-CONTEXT-002 (Hierarchical Context Loading)

---

## Pattern Categories

### Development Process Patterns (Sprint 3 - v0.17.0)
- **Pattern-CODE-001:** Code Development Workflow (8-step pre-code workflow with TDD enforcement)
- **Pattern-GIT-001:** Git Workflow Integration (pre-task git status check, workflow announcement)
- **Pattern-IMPROVEMENT-001:** Gap Detection & Self-Improvement (identifies missing patterns/skills/agents)
- **Pattern-PREFLIGHT-001:** Pre-Flight Checklist Workflow (mandatory checklist before critical operations)
- **Pattern-SPRINT-PLAN-001:** Sprint Planning Process (12-step workflow with template injection)
- **Pattern-TASK-ANALYSIS-001:** 8-Step Pre-Task Analysis (task analysis workflow with gap detection)

### Meta Patterns
- **Pattern-000:** Meta-Loop Development
- **Pattern-META-001:** Documentation Feedback Loop
- **Pattern-TRACKING-001:** Comprehensive Execution Tracking
- **Pattern-CLI-001:** OpenTelemetry Execution Tracking

### Business Patterns
- **Pattern-BUSINESS-001:** Zero-Marginal-Cost Network Effects

### Core Technical Patterns
- **Pattern-001:** Rust Core + Language Bindings
- **Pattern-005:** Multi-Dimensional Matching
- **Pattern-007:** Language Bindings via NAPI
- **Pattern-008:** IPC via WebSocket
- **Pattern-012:** Real-Time Status UI
- **Pattern-020:** Pattern Curation Workflow
- **Pattern-023:** Continuous Quality Assurance
- **Pattern-027:** Context Injection
- **Pattern-035:** Offline-First Architecture
- **Pattern-042:** Code Chunking Strategy
- **Pattern-060:** Local-First with Optional Cloud

### Failure Patterns (Anti-Patterns)
- **Pattern-FAILURE-001:** Memory Leak in Task Execution
- **Pattern-FAILURE-002:** Retroactive Timestamp Hallucinations
- **Pattern-FAILURE-003:** Premature Completion
- **Pattern-FAILURE-006:** Self-Fulfilling Negative Prophecy

### AdHub Production Patterns (13 patterns, quality 0.85-0.98)
- **Pattern-AGENT-ROUTING-001:** Multi-Agent Routing with Intent Classification
- **Pattern-AUTH-DUAL-SYNC-001:** Clerk + Supabase Dual Auth Sync
- **Pattern-API-CLIENT-001:** Centralized API Client
- **Pattern-SERVICE-LAYER-001:** Service Layer Field Classification
- **Pattern-REACT-WIZARD-001:** React Wizard with Debounced Filtering
- **Pattern-SQL-BUILDER-001:** Snowflake Query Builder
- **Pattern-FILTER-CATEGORIZATION-001:** Keyword-Based Filter Categorization
- **Pattern-RLS-DUAL-ID-001:** Supabase RLS with Dual ID Mapping
- **Pattern-LAMBDA-LAYERED-001:** AWS Lambda Layered Architecture
- **Pattern-PLAN-LIMITS-001:** Database-Driven Feature Flags
- **Pattern-ERROR-CODES-001:** Structured Error Handling
- **Pattern-ANALYTICS-STORY-001:** Story-Based Analytics Tracking
- **Pattern-IAC-AMPLIFY-001:** AWS Amplify CDK Infrastructure as Code

---

## How to Use This Index

**Load specific pattern:**
```
See: @docs/patterns/Pattern-META-001.md
```

**Browse by category:**
```
cd docs/patterns/
ls Pattern-BUSINESS-*.md  # Business patterns
ls Pattern-FAILURE-*.md   # Anti-patterns
```

**Search patterns:**
```
grep -r "DESIGN DECISION" docs/patterns/
```

---

## Pattern Template

All patterns follow this structure:

```markdown
# Pattern-XXX-YYY: [Name]

**CREATED:** YYYY-MM-DD
**SOURCE:** [Project/Context]
**CATEGORY:** [Category]
**QUALITY SCORE:** [0.0-1.0]
**APPLICABILITY:** [When to use]

## Context
[Problem description]

## Solution
[Implementation with code examples]

## Design Decision
**DESIGN DECISION:** [Key choice made]
**WHY:** [Reasoning behind decision]

**REASONING CHAIN:**
1. [Step with reasoning]
2. [Step with reasoning]
3. [Step with reasoning]

## When to Use / When Not to Use

## Performance
[Metrics and benchmarks]

## Related Patterns
[Pattern-XXX links]

**PATTERN STATUS:** [Production-Validated / In Development]
```

---

**See CLAUDE_ESSENTIAL.md for full project context.**
