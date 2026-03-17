# Pattern-RLS-DUAL-ID-001: Supabase RLS with Dual ID Mapping

**CREATED:** 2025-10-16
**CATEGORY:** Database Security
**LANGUAGE:** Architecture
**QUALITY SCORE:** 0.88
**APPLICABILITY:** Supabase apps with external auth (Clerk, Auth0), Row Level Security
**STATUS:** Production-Validated

---



## Context

Supabase Row Level Security (RLS) uses `auth.uid()` to identify users. When using external auth providers (Clerk, Auth0), you have TWO user IDs:

1. **Clerk User ID** - External auth provider ID
2. **Supabase User ID** - Internal database ID

**Problem:** RLS policies can't reference Clerk IDs directly. Requires mapping layer.

---

## Solution

**Dual ID Mapping: Store Clerk ID in user_subscriptions table, reference in RLS policies**

```sql
-- user_subscriptions table
CREATE TABLE user_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_user_id TEXT UNIQUE NOT NULL,
  supabase_user_id UUID REFERENCES auth.users(id),
  organization_id UUID REFERENCES organizations(id),
  -- other fields...
);

-- RLS policy using Clerk ID
CREATE POLICY organizations_select_policy ON organizations
  FOR SELECT
  USING (
    clerk_org_id IN (
      SELECT organization_id
      FROM user_subscriptions
      WHERE clerk_user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );
```

---

## Design Decision

**DESIGN DECISION:** Map Clerk ID to Supabase ID in user_subscriptions table

**WHY:** RLS policies can query user_subscriptions to resolve Clerk → Supabase ID mapping

**REASONING CHAIN:**
1. Clerk provides JWT with `sub` claim (Clerk User ID)
2. Supabase RLS can't use Clerk ID directly
3. Store Clerk ID in user_subscriptions table
4. RLS policy: SELECT where clerk_user_id = JWT sub claim
5. Result: RLS works with external auth

---

## When to Use

**Use dual ID mapping when:**
- Using Supabase + external auth (Clerk, Auth0, Firebase)
- Need Row Level Security policies
- External user ID != Supabase user ID

**Don't use when:**
- Supabase Auth only (no external provider)
- No RLS needed
- Single-user app

---

## Related Patterns

- **Pattern-AUTH-DUAL-SYNC-001:** Clerk + Supabase Dual-Sync (syncs Clerk IDs to Supabase)
- **Pattern-SQL-BUILDER-001:** Query Builder (used for user_subscriptions queries)

---

**PATTERN STATUS:** ✅ Production-Validated (AdHub)
**LAST UPDATED:** 2025-10-16
