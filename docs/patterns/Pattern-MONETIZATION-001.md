# Pattern-MONETIZATION-001: Server-Side Key Management

**CREATED:** 2025-11-11
**CATEGORY:** Architecture
**LANGUAGE:** TypeScript, Rust
**QUALITY SCORE:** 95/100
**APPLICABILITY:** SaaS platforms with API key management, usage tracking, monetization
**STATUS:** Active (v0.17.0+)
**RELATED:** Pattern-API-001
**DEPENDENCIES:** Supabase, Stripe, Vercel Cron

---

## Problem Statement

**Previous State (BYOK - Bring Your Own Key):**
- Users provided their own OpenAI API keys
- No usage tracking or monetization
- Security risk (API keys in config files)
- Complex setup (requires OpenAI account + API key configuration)
- Support burden (API key troubleshooting)

**Need:** Move to server-managed OpenAI keys for monetization, simpler setup, and better security.

---

## Solution Overview

**Architecture:** Extension → Desktop App → Server API → OpenAI Whisper API

**Key Principles:**
1. Server holds single OpenAI API key (not users)
2. Users authenticate with license keys (format: `XXXX-XXXX-XXXX-XXXX`)
3. Token-based pricing: 375 tokens = 1 minute of transcription
4. Server tracks usage, enforces limits, deducts tokens
5. Desktop app displays balance and warnings
6. No OpenAI account needed for end users

---

## Architecture

### Data Flow

```
┌─────────────┐
│  Extension  │  (VS Code / Cursor / Claude Code)
│  (TypeScript│
└──────┬──────┘
       │
       │ WebSocket (audio data)
       ▼
┌─────────────┐
│ Desktop App │  (Tauri - Rust + TypeScript)
│  - Captures │  - Hotkey: Shift+~ or `
│    audio    │  - Pre-flight: Check tokens >= 375
│  - Types    │  - Display: Token balance widget
│    text     │  - Warnings: Toast at 80%, 90%, 95%
└──────┬──────┘
       │
       │ HTTPS (Bearer token auth)
       ▼
┌─────────────┐
│ Server API  │  (Vercel - Next.js + Supabase)
│  - Auth:    │  - License key → device validation
│    License  │  - Pre-flight: Check tokens
│    key      │  - Transcribe: OpenAI Whisper API
│  - Track:   │  - Deduct: Tokens from balance
│    Usage    │  - Log: usage_events, credit_transactions
│  - Enforce: │  - Calculate: Warnings (80%, 90%, 95%)
│    Limits   │
└──────┬──────┘
       │
       │ HTTPS (OpenAI API key in env)
       ▼
┌─────────────┐
│   OpenAI    │  (Whisper API)
│   Whisper   │  - Model: whisper-1
│   API       │  - Returns: Transcribed text
└─────────────┘
```

### Component Responsibilities

**Extension (vscode-lumina/):**
- ❌ NO OpenAI API calls (removed in v0.17.0)
- ✅ Audio sent to desktop app via WebSocket
- ✅ Receives transcribed text from desktop app

**Desktop App (products/lumina-desktop/):**
- ✅ Captures audio via hotkey (Shift+~ or `)
- ✅ Pre-flight check: `GET /api/tokens/balance` (needs >= 375 tokens)
- ✅ Sends audio: `POST /api/desktop/transcribe` with Bearer token
- ✅ Displays token balance (bottom-right widget)
- ✅ Shows warnings (toast notifications)
- ✅ Types transcription at cursor position (OS-level keyboard simulation)

**Server API (website/):**
- ✅ Authenticates license key (devices table)
- ✅ Checks token balance (profiles table)
- ✅ Calls OpenAI Whisper API (server's API key)
- ✅ Deducts tokens (375 tokens/minute)
- ✅ Logs usage (usage_events, credit_transactions tables)
- ✅ Calculates warnings (server-side threshold logic)
- ✅ Returns: Transcription + tokens used + balance + warnings

**OpenAI Whisper API:**
- ✅ Receives audio file (WAV format)
- ✅ Returns transcribed text
- ✅ Cost: ~$0.006/minute

---

## Database Schema

### profiles table (Supabase)

```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,

  -- Token-based pricing system (Sprint 4)
  tokens_balance BIGINT DEFAULT 250000 NOT NULL,        -- Free tier: 250k tokens
  tokens_used_this_month BIGINT DEFAULT 0 NOT NULL,
  token_refresh_date TIMESTAMPTZ DEFAULT NOW(),
  subscription_tier TEXT DEFAULT 'free' NOT NULL,       -- 'free' | 'pro' | 'enterprise'

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Subscription Tiers:**
- `free`: 250,000 tokens one-time (~666 minutes)
- `pro`: 1,000,000 tokens/month (~2,666 minutes) - $29.99/month
- `enterprise`: Custom token allocation

### devices table (Supabase)

```sql
CREATE TABLE devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  license_key TEXT UNIQUE NOT NULL,  -- Format: XXXX-XXXX-XXXX-XXXX
  device_name TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### usage_events table (Supabase)

```sql
CREATE TABLE usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,              -- 'transcription'
  tokens_used BIGINT NOT NULL,           -- 375 tokens/minute
  duration_seconds NUMERIC(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### credit_transactions table (Supabase)

```sql
CREATE TABLE credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  transaction_type TEXT NOT NULL,        -- 'usage' | 'purchase' | 'refund' | 'monthly_refresh'
  tokens_amount BIGINT NOT NULL,         -- Negative for usage, positive for purchases
  tokens_balance_after BIGINT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

### GET /api/tokens/balance

**Authentication:** Bearer token (license_key)

**Response (200):**
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
      "message": "Low balance: 50,000 tokens remaining (~133 minutes)",
      "percentage_used": 80
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or missing license key
- `403 Forbidden` - Device not active
- `500 Internal Server Error` - Server error

**Used by:** Desktop app (on startup, every 5 minutes, after transcription)

---

### POST /api/desktop/transcribe

**Authentication:** Bearer token (license_key)

**Request Body (multipart/form-data):**
```
file: audio.wav (required)
model: "whisper-1" (optional, defaults to whisper-1)
language: "en" (optional, improves accuracy)
```

**Response (200):**
```json
{
  "success": true,
  "text": "This is the transcribed text from the audio file.",
  "duration_seconds": 60.5,
  "tokens_used": 375,
  "tokens_balance": 249625
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or missing license key
- `402 Payment Required` - Insufficient tokens
  ```json
  {
    "error": "Insufficient tokens",
    "tokens_required": 375,
    "tokens_balance": 100,
    "tokens_shortfall": 275,
    "message": "Need 375 tokens, you have 100 tokens, shortfall: 275 tokens"
  }
  ```
- `403 Forbidden` - Device not active
- `400 Bad Request` - Invalid audio file
- `500 Internal Server Error` - OpenAI API error or server error

**Used by:** Desktop app (when user presses hotkey after recording)

---

### POST /api/tokens/consume

**Authentication:** Bearer token (license_key)

**Request Body (JSON):**
```json
{
  "tokens_amount": 1000,
  "description": "Feature usage"
}
```

**Response (200):**
```json
{
  "success": true,
  "tokens_consumed": 1000,
  "tokens_balance": 249000,
  "transaction_id": "uuid-here"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid license key
- `402 Payment Required` - Insufficient tokens

**Used by:** Future non-transcription features (NOT used for transcription)

---

### POST /api/stripe/create-checkout

**Authentication:** Bearer token (license_key)

**Request Body (JSON):**
```json
{
  "type": "token_purchase",  // or "subscription"
  "tier": "pro"               // for subscription
}
```

**Response (200):**
```json
{
  "success": true,
  "checkout_url": "https://checkout.stripe.com/..."
}
```

**User Flow:**
1. Desktop app calls this endpoint
2. Opens browser to Stripe Checkout Session
3. User completes payment on Stripe
4. Stripe webhook calls `/api/webhooks/stripe`
5. Tokens added to user account

---

### POST /api/webhooks/stripe

**Authentication:** Stripe signature verification

**Webhook Events:**
- `checkout.session.completed` - Token purchase or subscription
- `customer.subscription.updated` - Subscription changes
- `customer.subscription.deleted` - Subscription cancelled

**Actions:**
- Calls `record_token_transaction` RPC to add tokens
- Updates `subscription_tier` in profiles table
- Logs transaction in credit_transactions table

---

### POST /api/cron/refresh-tokens (Vercel Cron)

**Authentication:** Cron secret (Vercel internal)

**Schedule:** 1st of each month (00:00 UTC)

**Action:**
```sql
UPDATE profiles
SET
  tokens_balance = 1000000,
  tokens_used_this_month = 0,
  token_refresh_date = NOW()
WHERE
  subscription_tier = 'pro'
  AND (token_refresh_date IS NULL OR token_refresh_date < NOW() - INTERVAL '30 days');
```

**Configuration:** `vercel.json`
```json
{
  "crons": [
    {
      "path": "/api/cron/refresh-tokens",
      "schedule": "0 0 1 * *"
    }
  ]
}
```

---

## Token Pricing Model

### Conversion Rate
**375 tokens = 1 minute of transcription**

**Reasoning:**
- OpenAI Whisper API cost: ~$0.006/minute
- 50% margin target
- User cost: ~$0.012/minute
- Token cost: $24.99 for 1M tokens = $0.00002499/token
- 1 minute = 375 tokens × $0.00002499 = $0.0094/minute (~$0.012 with rounding)

### Pricing Tiers

| Tier | Tokens | Minutes | Cost | Expiration |
|------|--------|---------|------|------------|
| Free | 250,000 | ~666 | $0 | Never |
| Token Purchase | 1,000,000 | ~2,666 | $24.99 one-time | Never |
| Pro Subscription | 1,000,000/month | ~2,666/month | $29.99/month | Monthly refresh |

---

## Warning System

### Server-Side Threshold Calculation

**Warning Levels:**
- `medium` (80% used) - Yellow warning toast
- `high` (90% used) - Orange warning toast
- `critical` (95% used) - Red warning toast

**Calculation (Server-Side):**
```typescript
// website/app/api/tokens/balance/route.ts
const startingBalance = tier === 'pro' ? 1000000 : 250000;
const percentageUsed = ((startingBalance - tokensBalance) / startingBalance) * 100;

const warnings: TokenWarning[] = [];

if (percentageUsed >= 95) {
  warnings.push({
    level: 'critical',
    threshold: 95,
    message: `Critical: Only ${tokensBalance} tokens remaining (~${minutesRemaining} minutes)`,
    percentage_used: Math.round(percentageUsed)
  });
} else if (percentageUsed >= 90) {
  warnings.push({
    level: 'high',
    threshold: 90,
    message: `Warning: Only ${tokensBalance} tokens remaining (~${minutesRemaining} minutes)`,
    percentage_used: Math.round(percentageUsed)
  });
} else if (percentageUsed >= 80) {
  warnings.push({
    level: 'medium',
    threshold: 80,
    message: `Low balance: ${tokensBalance} tokens remaining (~${minutesRemaining} minutes)`,
    percentage_used: Math.round(percentageUsed)
  });
}

return { warnings };
```

**Desktop App Display:**
```typescript
// products/lumina-desktop/src/components/VoiceCapture.tsx
const checkBalanceWarnings = (balance: TokenBalance) => {
  if (!balance.warnings || balance.warnings.length === 0) {
    return;
  }

  const highestWarning = balance.warnings[0];

  // Prevent duplicate warnings for same threshold
  if (lastWarningThreshold === highestWarning.threshold) {
    return;
  }

  setLastWarningThreshold(highestWarning.threshold);
  setToastMessage(highestWarning.message);
  setShowLowBalanceToast(true);
  setTimeout(() => setShowLowBalanceToast(false), 5000);
};
```

**Why Server-Side?**
- Consistent calculation across all clients
- No client-side logic drift
- Easier to update thresholds (single location)
- Backend controls business logic

---

## Code Examples

### Desktop App: Pre-Flight Check

```rust
// products/lumina-desktop/src-tauri/src/transcription.rs

pub async fn check_token_balance(
    license_key: &str,
    api_url: &str,
) -> Result<TokenBalanceResponse> {
    if license_key.is_empty() {
        anyhow::bail!("License key not configured. Please activate device first.");
    }

    let balance_endpoint = format!("{}/api/tokens/balance", api_url);

    println!("📊 Checking token balance...");
    let client = reqwest::Client::new();
    let response = client
        .get(&balance_endpoint)
        .header("Authorization", format!("Bearer {}", license_key))
        .send()
        .await
        .context("Failed to send balance request to server API")?;

    let status = response.status();

    if !status.is_success() {
        let error_text = response.text().await.unwrap_or_default();
        anyhow::bail!("Balance check failed ({}): {}", status, error_text);
    }

    let balance_response: TokenBalanceResponse = response
        .json()
        .await
        .context("Failed to parse balance response")?;

    println!("✅ Balance: {} tokens (~{} minutes remaining)",
             balance_response.tokens_balance,
             balance_response.minutes_remaining);

    Ok(balance_response)
}
```

### Desktop App: Server-Proxied Transcription

```rust
// products/lumina-desktop/src-tauri/src/transcription.rs

pub async fn transcribe_audio(
    audio_samples: &[f32],
    sample_rate: u32,
    license_key: &str,
    api_url: &str,
) -> Result<String> {
    if license_key.is_empty() {
        anyhow::bail!("License key not configured. Please activate device first.");
    }

    // Convert audio to WAV format
    let wav_bytes = audio_to_wav(audio_samples, sample_rate)?;

    // Create multipart form with audio file
    let form = multipart::Form::new()
        .part(
            "file",
            multipart::Part::bytes(wav_bytes)
                .file_name("audio.wav")
                .mime_str("audio/wav")?,
        )
        .text("model", "whisper-1")
        .text("language", "en");

    // Send request to server API
    let transcription_endpoint = format!("{}/api/desktop/transcribe", api_url);

    let client = reqwest::Client::new();
    let response = client
        .post(&transcription_endpoint)
        .header("Authorization", format!("Bearer {}", license_key))
        .multipart(form)
        .send()
        .await
        .context("Failed to send request to server API")?;

    let status = response.status();

    if !status.is_success() {
        let error_text = response.text().await.unwrap_or_default();

        // Handle 402 Insufficient Tokens
        if status == 402 {
            anyhow::bail!("Insufficient tokens: {}", error_text);
        }

        anyhow::bail!("Server API error ({}): {}", status, error_text);
    }

    let transcription_response: TranscriptionResponse = response
        .json()
        .await
        .context("Failed to parse server API response")?;

    println!("✅ Transcription received: {} characters", transcription_response.text.len());
    println!("💰 Tokens used: {}, Balance: {}",
             transcription_response.tokens_used,
             transcription_response.tokens_balance);

    Ok(transcription_response.text)
}
```

### Server API: License Key Authentication

```typescript
// website/lib/supabase/server.ts

export async function getAuthenticatedUser(licenseKey: string) {
  const supabase = createClient({ useServiceRole: true }); // Bypass RLS

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

### Server API: Token Deduction

```typescript
// website/app/api/desktop/transcribe/route.ts

export async function POST(req: Request) {
  const licenseKey = req.headers.get('authorization')?.replace('Bearer ', '');

  if (!licenseKey) {
    return NextResponse.json({ error: 'Missing license key' }, { status: 401 });
  }

  const userId = await getAuthenticatedUser(licenseKey);

  const formData = await req.formData();
  const audioFile = formData.get('file') as File;

  // Estimate tokens from file size
  const estimatedDurationSeconds = audioFile.size / 32000; // Rough estimate
  const requiredTokens = Math.ceil(estimatedDurationSeconds / 60) * 375;

  // Pre-flight check
  const { data: profile } = await supabase
    .from('profiles')
    .select('tokens_balance')
    .eq('id', userId)
    .single();

  if (profile.tokens_balance < requiredTokens) {
    return NextResponse.json({
      error: 'Insufficient tokens',
      tokens_required: requiredTokens,
      tokens_balance: profile.tokens_balance,
      tokens_shortfall: requiredTokens - profile.tokens_balance
    }, { status: 402 });
  }

  // Call OpenAI Whisper API
  const formDataOpenAI = new FormData();
  formDataOpenAI.append('file', audioFile);
  formDataOpenAI.append('model', 'whisper-1');

  const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`
    },
    body: formDataOpenAI
  });

  const transcription = await response.json();

  // Deduct tokens
  const actualDurationSeconds = transcription.duration || estimatedDurationSeconds;
  const tokensUsed = Math.ceil(actualDurationSeconds / 60) * 375;

  const { data: updatedProfile } = await supabase.rpc('record_token_transaction', {
    p_user_id: userId,
    p_tokens_amount: -tokensUsed,
    p_transaction_type: 'usage',
    p_description: 'Transcription'
  });

  return NextResponse.json({
    success: true,
    text: transcription.text,
    duration_seconds: actualDurationSeconds,
    tokens_used: tokensUsed,
    tokens_balance: updatedProfile.tokens_balance
  });
}
```

---

## Related Patterns

- **Pattern-AUTH-DUAL-SYNC-001**: Dual authentication system (extension + desktop app)
- **Pattern-WHISPER-001**: OpenAI Whisper API integration
- **Pattern-KEYBOARD-001**: OS-level keyboard simulation for typing transcripts

---

## Future Considerations

### Phase 1 (Current - v0.17.0)
- ✅ Token-based pricing (375 tokens/minute)
- ✅ Three tiers: Free, Pro ($29.99/month), Token Purchase ($24.99)
- ✅ Server-side key management
- ✅ License key authentication
- ✅ Token balance display and warnings
- ✅ Monthly token refresh automation (Vercel Cron)

### Phase 2 (Future)
- Team billing (team admin pays, members use shared pool)
- Usage analytics dashboard (charts, graphs, trends)
- Token transfer between users
- Referral program (earn tokens)

### Phase 3 (Future)
- Enterprise tier (custom pricing, dedicated support)
- White-label licensing (companies rebrand ÆtherLight)
- API access (developers integrate via REST API)
- Webhooks (usage events → external systems)

### Phase 4 (Future)
- Feature flags (enable/disable features per tier)
- A/B testing (test pricing models)
- Dynamic pricing (adjust based on OpenAI costs)
- Volume discounts (more tokens = lower per-token cost)

---

## Testing

### Manual Testing Checklist
- ✅ Free tier user: 250,000 tokens → 0 tokens (voice disabled)
- ✅ Pro tier user: 1M tokens/month → auto-refresh on 1st
- ✅ Token purchase: $24.99 → 1M tokens added
- ✅ Warnings: 80%, 90%, 95% thresholds trigger toasts
- ✅ 402 error: Shows clear message with exact shortfall
- ✅ License key activation: Wizard step works
- ✅ Cross-device: Same license key works on multiple devices

### Automated Testing
- API endpoint tests: `website/app/api/__tests__/`
- Desktop app tests: `products/lumina-desktop/src-tauri/tests/`
- Integration tests: End-to-end flow (desktop → server → OpenAI)

---

## Deployment

### Production Environment Variables
```
OPENAI_API_KEY=sk-...
NEXT_PUBLIC_SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
CRON_SECRET=...
```

### Deployment Checklist
- ✅ Set environment variables in Vercel dashboard
- ✅ Deploy Supabase migrations (007, 008)
- ✅ Configure Vercel Cron job (vercel.json)
- ✅ Test API endpoints with production license keys
- ✅ Verify Stripe webhooks receive events

---

## Monitoring & Observability

### Key Metrics
- Token usage per user (daily, weekly, monthly)
- Average transcription duration
- 402 error rate (insufficient tokens)
- Stripe payment success rate
- Monthly refresh success rate

### Alerts
- OpenAI API key about to expire
- Stripe webhook failures
- Database connection errors
- High 402 error rate (> 5%)
- Cron job failures

---

## Security Considerations

### License Key Security
- License keys stored in devices table (hashed? NO - needed for lookups)
- Use HTTPS only (no plain HTTP)
- Rate limiting on API endpoints (10 requests/minute per key)

### OpenAI API Key Security
- Stored in Vercel environment variables (encrypted at rest)
- Never sent to clients (server-side only)
- Rotate regularly (every 90 days)

### Row Level Security (RLS)
- API uses service role key to bypass RLS (intentional)
- RLS policies prevent direct database access from clients
- License key validates device ownership before granting access

---

## Migration from BYOK (v0.16.x)

See [MIGRATION_GUIDE.md](../../MIGRATION_GUIDE.md) for complete user-facing migration instructions.

**Technical Changes:**
- Extension: Removed all OpenAI API calls
- Desktop: Added server API integration
- Server: Added all API endpoints + database schema
- Breaking change: Both extension and desktop MUST upgrade to v0.17.0 together

---

**Pattern Status:** ✅ IMPLEMENTED (v0.17.0)
**Last Updated:** 2025-11-11
**Maintained by:** Infrastructure & API teams
