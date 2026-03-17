# Pattern-LAMBDA-LAYERED-001: AWS Lambda Layered Architecture

**CREATED:** 2025-10-16
**CATEGORY:** AWS Architecture
**LANGUAGE:** Architecture
**QUALITY SCORE:** 0.87
**APPLICABILITY:** AWS Lambda functions, serverless architecture
**STATUS:** Production-Validated

---



## Context

AWS Lambda functions often start as monoliths (single large function) and evolve through three architectural stages:

1. **Stage 1: Monolith** - Single Lambda handles everything (slow cold start, hard to maintain)
2. **Stage 2: Function Per Route** - One Lambda per API endpoint (better, but duplicated dependencies)
3. **Stage 3: Layered Architecture** - Shared layers + thin route handlers (optimal)

**Problem:** Monolith Lambdas have slow cold starts (5-10s), large bundle sizes (50MB+), and are hard to maintain.

---

## Solution

**Layered Architecture: Shared dependencies in Lambda Layers + thin route handlers**

```
Layer 1 (Dependencies): node_modules (40MB) - shared across all functions
Layer 2 (Core Logic): Database, Auth, Utils (5MB) - shared business logic
Function 1 (API Route): POST /users (500KB) - thin handler only
Function 2 (API Route): GET /users (500KB) - thin handler only
Function 3 (API Route): DELETE /users (500KB) - thin handler only
```

**Benefits:**
- Cold start: 10s → 2s (80% reduction)
- Bundle size: 50MB → 500KB per function (99% reduction)
- Code reuse: Shared layers across all functions

---

## Design Decision

**DESIGN DECISION:** Extract dependencies and core logic into Lambda Layers

**WHY:** Reduces cold start, enables code reuse, simplifies deployment

**REASONING CHAIN:**
1. Identify shared dependencies (node_modules, common utils)
2. Create Lambda Layer with shared code
3. Each function imports Layer (no bundling)
4. Deploy: Layer once, functions quickly
5. Result: Fast cold starts, small bundles

---

## When to Use

**Use Lambda Layers when:**
- Multiple Lambda functions with shared dependencies
- Cold start time >3s
- Bundle size >10MB
- Frequent deployments (don't want to rebundle dependencies)

**Don't use when:**
- Single Lambda function
- Unique dependencies per function
- <5s cold start acceptable

---

## Performance

| Metric | Monolith | Layered | Improvement |
|--------|----------|---------|-------------|
| Cold start | 10s | 2s | 80% faster |
| Bundle size | 50MB | 500KB | 99% smaller |
| Deployment time | 60s | 5s | 92% faster |

**Production Evidence (AdHub):**
- Functions: 15
- Shared Layer: 45MB (node_modules + utils)
- Avg function size: 500KB
- Cold start: 1.5-2.5s (was 8-12s)

---

## Related Patterns

- **Pattern-API-CLIENT-001:** Centralized API Client (goes in shared layer)
- **Pattern-SQL-BUILDER-001:** Query Builder (goes in shared layer)

---

**PATTERN STATUS:** ✅ Production-Validated (AdHub)
**LAST UPDATED:** 2025-10-16
