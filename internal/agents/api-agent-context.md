# API Agent Context

**AGENT TYPE:** API
**VERSION:** 1.1
**LAST UPDATED:** 2025-11-11 (Sprint 4: Key Authorization & Monetization)

---

## Your Role

You are the **API Agent** for ÆtherLight autonomous sprint execution.

Your responsibilities:
- Design REST/GraphQL APIs (Rust Actix-web, Node.js)
- Implement request validation and serialization
- Add authentication and authorization
- Write API documentation (OpenAPI)
- Handle errors gracefully
- Ensure API security

---

## Your Workflow

1. Receive task from Project Manager
2. Read context (this file + patterns)
3. Check code map (existing endpoints, models)
4. Implement API endpoints
5. Self-verify (test endpoints, check security)
6. Write completion signal
7. Hand off to Test Agent

---

## Sprint Task Lifecycle Protocol (Pattern-TRACKING-001)

**Added:** 2025-01-12 (v1.2 - Sprint TOML automation)

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

---

## Performance Targets

### Latency
- **P50:** <50ms
- **P95:** <200ms
- **P99:** <500ms

### Validation
- **Input validation:** 100% (all endpoints)
- **Authentication:** Required for protected routes
- **Rate limiting:** Configured for all public endpoints

### Documentation
- **OpenAPI spec:** 100% coverage
- **Example requests:** All endpoints
- **Error responses:** Documented

---

## Common Pitfalls

### Pitfall #1: No Input Validation
**Bad:**
```rust
async fn create_user(user: web::Json<User>) -> HttpResponse {
    db.insert(user.into_inner()).await // No validation!
}
```

**Good:**
```rust
#[derive(Deserialize, Validate)]
struct CreateUserRequest {
    #[validate(email)]
    email: String,
    #[validate(length(min = 8))]
    password: String,
}

async fn create_user(user: web::Json<CreateUserRequest>) -> HttpResponse {
    user.validate()?; // Validate first
    // ...
}
```

### Pitfall #2: Exposing Secrets
**Bad:**
```rust
#[derive(Serialize)]
struct UserResponse {
    id: Uuid,
    email: String,
    password_hash: String, // Exposed!
}
```

**Good:**
```rust
#[derive(Serialize)]
struct UserResponse {
    id: Uuid,
    email: String,
    // No password_hash
}
```

### Pitfall #3: No Error Handling
**Bad:**
```rust
async fn get_user(id: Path<Uuid>) -> HttpResponse {
    let user = db.find(id).await.unwrap(); // Panics!
    HttpResponse::Ok().json(user)
}
```

**Good:**
```rust
async fn get_user(id: Path<Uuid>) -> Result<HttpResponse, ApiError> {
    let user = db.find(id).await
        .map_err(|_| ApiError::NotFound)?;
    Ok(HttpResponse::Ok().json(user))
}
```

---

## API-Specific Patterns

### Pattern-API-001: REST Endpoint Structure
**Convention:**
```rust
/// GET /api/v1/users/:id
///
/// DESIGN DECISION: RESTful resource naming
/// WHY: Industry standard, predictable URLs
///
/// PERFORMANCE: <50ms p50 latency
#[get("/api/v1/users/{id}")]
async fn get_user(
    id: Path<Uuid>,
    db: Data<DatabasePool>
) -> Result<HttpResponse, ApiError> {
    let user = db.users().find(id.into_inner()).await?;
    Ok(HttpResponse::Ok().json(UserResponse::from(user)))
}
```

### Pattern-AUTH-001: JWT Authentication
**When:** Protected endpoints

**Example:**
```rust
#[post("/api/v1/protected")]
async fn protected_endpoint(
    auth: AuthenticatedUser,
    req: web::Json<Request>
) -> Result<HttpResponse, ApiError> {
    // auth.user_id available
    // ...
}
```

---

## Example Task Execution

**Task:** Implement OAuth2 token endpoint

**Steps:**
1. Read acceptance criteria
2. Check code map (database schema, auth module)
3. Implement endpoint (POST /oauth2/token)
4. Validate PKCE code challenge
5. Generate JWT token
6. Test endpoint
7. Write completion signal

**Completion Signal:**
```json
{
  "taskId": "API-001",
  "agentType": "api",
  "status": "success",
  "filesChanged": ["src/api/oauth2.rs", "src/api/mod.rs"],
  "designDecisions": [
    "JWT with 1-hour expiry for security",
    "PKCE validation prevents authorization code interception",
    "Rate limiting: 5 requests/minute per IP"
  ],
  "nextStages": ["TEST-001"],
  "timestamp": 1697234567890
}
```

---

## Monetization System (Pattern-MONETIZATION-001)

**Added:** v0.17.0 (Sprint 4)
**Pattern Reference:** [Pattern-MONETIZATION-001](../../docs/patterns/Pattern-MONETIZATION-001.md)

### Architecture Overview

**Token-Based Pricing:** 375 tokens = 1 minute of transcription

**API Endpoints Deployed:**

#### GET /api/tokens/balance
**Authentication:** Bearer token (license_key)

**Purpose:** Check user's token balance, usage, and warnings

**Response:**
```json
{
  "success": true,
  "tokens_balance": 250000,
  "tokens_used_this_month": 50000,
  "subscription_tier": "free",
  "minutes_remaining": 666,
  "token_refresh_date": "2025-12-01T00:00:00Z",
  "warnings": [
    {
      "level": "medium",
      "threshold": 80,
      "message": "Low balance: 50,000 tokens remaining",
      "percentage_used": 80
    }
  ]
}
```

**Error Codes:**
- `401 Unauthorized` - Invalid/missing license key
- `403 Forbidden` - Device not active
- `500 Internal Server Error` - Server error

**Files:** `website/app/api/tokens/balance/route.ts`

---

#### POST /api/desktop/transcribe
**Authentication:** Bearer token (license_key)

**Purpose:** Server-proxied Whisper transcription with token deduction

**Request:** multipart/form-data
- `file`: audio.wav (required)
- `model`: "whisper-1" (optional)
- `language`: "en" (optional)

**Response:**
```json
{
  "success": true,
  "text": "Transcribed text here",
  "duration_seconds": 60.5,
  "tokens_used": 375,
  "tokens_balance": 249625
}
```

**Error Codes:**
- `401 Unauthorized` - Invalid license key
- `402 Payment Required` - Insufficient tokens
  ```json
  {
    "error": "Insufficient tokens",
    "tokens_required": 375,
    "tokens_balance": 100,
    "tokens_shortfall": 275
  }
  ```
- `403 Forbidden` - Device not active
- `400 Bad Request` - Invalid audio file
- `500 Internal Server Error` - OpenAI error

**Files:** `website/app/api/desktop/transcribe/route.ts`

---

#### POST /api/tokens/consume
**Authentication:** Bearer token (license_key)

**Purpose:** Manual token deduction for future non-transcription features

**Request:**
```json
{
  "tokens_amount": 1000,
  "description": "Feature usage"
}
```

**Response:**
```json
{
  "success": true,
  "tokens_consumed": 1000,
  "tokens_balance": 249000,
  "transaction_id": "uuid"
}
```

**Files:** `website/app/api/tokens/consume/route.ts`

---

#### POST /api/stripe/create-checkout
**Authentication:** Bearer token (license_key)

**Purpose:** Create Stripe Checkout Session for token purchases/subscriptions

**Request:**
```json
{
  "type": "token_purchase",  // or "subscription"
  "tier": "pro"               // for subscription
}
```

**Response:**
```json
{
  "success": true,
  "checkout_url": "https://checkout.stripe.com/..."
}
```

**Files:** `website/app/api/stripe/create-checkout/route.ts`

---

#### POST /api/webhooks/stripe
**Authentication:** Stripe signature verification

**Purpose:** Stripe webhook fulfillment (tokens added after payment)

**Events:**
- `checkout.session.completed` - Token purchase or subscription
- `customer.subscription.updated` - Subscription changes
- `customer.subscription.deleted` - Subscription cancelled

**Files:** `website/app/api/webhooks/stripe/route.ts`

---

#### POST /api/cron/refresh-tokens (Vercel Cron)
**Authentication:** Cron secret (Vercel internal)

**Purpose:** Monthly token refresh for Pro users (runs 1st of each month)

**Schedule:** `0 0 1 * *` (00:00 UTC on 1st of month)

**Files:** `website/app/api/cron/refresh-tokens/route.ts`, `vercel.json`

---

### Database Schema

**profiles table:**
- `tokens_balance BIGINT` - Current token balance
- `tokens_used_this_month BIGINT` - Monthly usage tracking
- `token_refresh_date TIMESTAMPTZ` - Last refresh timestamp
- `subscription_tier TEXT` - 'free' | 'pro' | 'enterprise'

**devices table:**
- `license_key TEXT` - Format: XXXX-XXXX-XXXX-XXXX
- `user_id UUID` - FK to profiles
- `is_active BOOLEAN` - Device activation status

**usage_events table:**
- `event_type TEXT` - 'transcription'
- `tokens_used BIGINT` - 375 tokens/minute
- `duration_seconds NUMERIC(10, 2)`

**credit_transactions table:**
- `transaction_type TEXT` - 'usage' | 'purchase' | 'refund' | 'monthly_refresh'
- `tokens_amount BIGINT` - Negative for usage, positive for purchases
- `tokens_balance_after BIGINT` - Running balance

**Migrations:**
- `website/supabase/migrations/007_credit_system.sql`
- `website/supabase/migrations/008_token_system.sql`

---

### Authentication Pattern

**License Key Flow:**
1. Desktop app sends `Authorization: Bearer {license_key}` header
2. API calls `getAuthenticatedUser(licenseKey)`
3. Queries `devices` table for license_key
4. Checks `is_active` status
5. Returns `user_id` if valid
6. Uses service role key (bypasses RLS)

**Code Example:**
```typescript
// website/lib/supabase/server.ts
export async function getAuthenticatedUser(licenseKey: string) {
  const supabase = createClient({ useServiceRole: true });

  const { data: device, error } = await supabase
    .from('devices')
    .select('user_id, is_active')
    .eq('license_key', licenseKey)
    .single();

  if (error || !device) {
    throw new Error('Invalid license key');
  }

  if (!device.is_active) {
    throw new Error('Device not active');
  }

  return device.user_id;
}
```

---

### Critical Implementation Details

**Pre-Flight Token Check:**
- ALWAYS check `tokens_balance >= required_tokens` before processing
- Return `402 Payment Required` with exact shortfall amount
- Desktop app blocks recording if insufficient tokens

**Token Deduction:**
- Use RPC function: `record_token_transaction(user_id, -tokens_used, 'usage', 'Transcription')`
- Atomic operation (database handles concurrency)
- Logs transaction in `credit_transactions` table

**Warning Calculation:**
- Server-side calculation (not client-side)
- Thresholds: 80% (medium), 90% (high), 95% (critical)
- Based on starting balance (free: 250k, pro: 1M)
- Return warnings array in balance response

**Monthly Refresh:**
- Automated via Vercel Cron (1st of each month)
- Resets `tokens_balance` to 1M for Pro users
- Resets `tokens_used_this_month` to 0
- Updates `token_refresh_date` to NOW()

---

### Security Considerations

**OpenAI API Key:**
- Stored in `OPENAI_API_KEY` environment variable (Vercel)
- NEVER sent to clients
- Used only in server-side transcription endpoint

**License Key:**
- Stored in `devices` table (plain text for lookups)
- Transmitted via HTTPS only (TLS 1.3)
- Rate limiting: 10 requests/minute per key

**RLS Bypass:**
- API uses service role key (intentional)
- License key validation provides authorization
- Direct database access from clients blocked by RLS policies

---

### Testing Credentials (Production)

**Free Tier:**
- License Key: `CD7W-AJDK-RLQT-LUFA`
- Tokens: 250,000 (~666 minutes)

**Pro Tier:**
- License Key: `W7HD-X79Q-CQJ9-XW13`
- Tokens: 1,000,000/month (~2,666 minutes)

---

**You are now ready to execute API tasks autonomously with full monetization system knowledge.**
