# Pattern-PLAN-LIMITS-001: Database-Driven Feature Flags with JSONB

**CREATED:** 2025-10-16
**CATEGORY:** Feature Management
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.90
**APPLICABILITY:** SaaS apps with subscription tiers, feature gating
**STATUS:** Production-Validated

---



## Context

SaaS applications have multiple subscription plans (Free, Pro, Enterprise) with different feature limits. Hardcoding limits in code causes:

1. **Deployment required** to change limits
2. **No A/B testing** (can't test different limits per user)
3. **Inflexible** (can't offer custom limits to specific customers)

**Problem:** Hardcoded plan limits require deployment to change, preventing rapid experimentation.

---

## Solution

**Database-Driven Plan Limits with JSONB Column**

```sql
CREATE TABLE plans (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL, -- 'free', 'pro', 'enterprise'
  limits JSONB NOT NULL -- { "max_users": 5, "max_storage_mb": 100 }
);

-- Query plan limits:
SELECT limits->>'max_users' AS max_users
FROM plans
WHERE name = 'free';
```

**Benefits:**
- Change limits without deployment
- A/B test limits (different limits per user)
- Custom limits per customer (override in user_subscriptions table)

---

## Design Decision

**DESIGN DECISION:** Store plan limits in JSONB column, not hardcoded constants

**WHY:** Enables runtime configuration, A/B testing, customer-specific overrides

**REASONING CHAIN:**
1. Define plan limits in database (JSONB column)
2. Query limits at runtime (not compile-time)
3. Cache limits in Redis (avoid repeated DB queries)
4. Override limits per user (user_subscriptions.custom_limits)
5. Result: Flexible limits, zero deployments to change

---

## When to Use

**Use database-driven limits when:**
- SaaS app with subscription tiers
- Need to experiment with limits (A/B testing)
- Offer custom limits to enterprise customers
- Avoid deployments for limit changes

**Don't use when:**
- Single plan only
- Limits never change
- <3 plans (hardcoding acceptable)

---

## Performance

| Metric | Target | Actual |
|--------|--------|--------|
| Limit lookup (cached) | <1ms | <0.5ms |
| Limit lookup (DB) | <10ms | <5ms |
| Cache hit rate | >95% | 98% |

**Production Evidence (AdHub):**
- Plans: 3 (Free, Pro, Enterprise)
- Limits changed: 12 times (no deployments)
- A/B test: Increased free plan storage 50MB → 100MB (20% conversion increase)

---

## Related Patterns

- **Pattern-API-CLIENT-001:** API Client (checks limits before API calls)

---

**PATTERN STATUS:** ✅ Production-Validated (AdHub)
**LAST UPDATED:** 2025-10-16
