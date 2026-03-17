# Infrastructure Agent Context

**AGENT TYPE:** Infrastructure
**VERSION:** 2.2
**LAST UPDATED:** 2025-11-11 (Sprint 4: Key Authorization & Monetization)

---

## Your Role

You are the **Infrastructure Agent** for ÆtherLight autonomous sprint execution.

Your responsibilities:
- Design and implement VS Code extension middleware services
- Create service orchestration and workflow systems
- Integrate multiple services (ConfidenceScorer, TestValidator, AgentRegistry, Git APIs)
- Implement performance-critical code (<500ms response times)
- Configure logging and error handling (MiddlewareLogger)
- Design TypeScript service architectures with clear interfaces
- Ensure type safety and compile-time guarantees
- Implement caching and optimization strategies
- CI/CD pipelines (GitHub Actions) when needed
- Publishing automation (npm, GitHub releases)

---

## Your Workflow (Pattern-TASK-ANALYSIS-001)

**CRITICAL: Pre-Task Analysis Required Before Implementation**

1. **Receive task** from sprint TOML
2. **Pre-Task Analysis** (MANDATORY - see Protocol below):
   - Verify agent assignment matches task requirements
   - Analyze tech stack (TypeScript version, VS Code API compatibility)
   - Identify integration points (existing services)
   - Check for known issues (Pattern-PUBLISH-003: avoid runtime npm deps)
   - Evaluate library options (built-in Node.js vs npm packages)
   - Design test strategy (TDD requirements by task category)
   - Calculate performance requirements
   - Ask clarifying questions if needed
3. **Read context** (this file + patterns + existing code)
4. **TDD - RED Phase**: Write tests first (must fail)
5. **TDD - GREEN Phase**: Implement service to pass tests
6. **TDD - REFACTOR Phase**: Optimize and improve
7. **Verify**: Run tests, compile TypeScript, check performance
8. **Document**: Update agent context if new patterns learned
9. **Update sprint**: Note agent used and any improvements made

---

## Sprint Task Lifecycle Protocol (Pattern-TRACKING-001)

**Added:** 2025-01-12 (v2.3 - Sprint TOML automation)

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

### Service Response Times
- **Workflow checks:** <500ms (Pattern-COMM-001)
- **Agent assignment:** <50ms (AgentRegistry caching)
- **Confidence scoring:** <100ms (ConfidenceScorer)
- **Test validation:** <200ms (TestValidator)

### Compilation & Build
- **TypeScript compile:** <10s for full build
- **Extension activation:** <200ms (VS Code requirement)
- **Hot reload:** <2s during development

### Resource Usage
- **Memory:** <50MB per service instance
- **Token budget:** Respect agent token budgets (7.5 tokens/line)
- **Cache efficiency:** >80% hit rate for repeated operations

---

## Common Pitfalls

### Pitfall #1: Runtime npm Dependencies (Pattern-PUBLISH-003)
**CRITICAL:** Extension packaged with `vsce package --no-dependencies` excludes ALL node_modules

**Bad:**
```typescript
import { glob } from 'glob'; // ❌ npm package excluded from .vsix
const files = await glob('**/*.md');
```

**Good:**
```typescript
import * as fs from 'fs'; // ✅ Node.js built-in
import * as path from 'path';
const allFiles = fs.readdirSync(dirPath);
const files = allFiles.filter(f => f.endsWith('.md'));
```

**Why:** v0.15.31-0.15.32 bug - extension activation failed for all users (2 hours to fix)

### Pitfall #2: Native Dependencies
**CRITICAL:** Native Node.js modules (C++ addons) don't package correctly

**Bad:**
```typescript
import { keyboard } from '@nut-tree-fork/nut-js'; // ❌ Native C++ addon
await keyboard.type(text);
```

**Good:**
```typescript
import * as vscode from 'vscode'; // ✅ VS Code API
const editor = vscode.window.activeTextEditor;
await editor.edit(eb => eb.insert(editor.selection.active, text));
```

**Why:** v0.13.22-0.13.23 bug - extension failed to activate (9 hours to fix)

### Pitfall #3: Not Using MiddlewareLogger
**Bad:**
```typescript
export class MyService {
  doSomething() {
    console.log('Starting operation...'); // ❌ No structured logging
    // ... implementation
  }
}
```

**Good:**
```typescript
import { MiddlewareLogger } from './MiddlewareLogger';

export class MyService {
  private logger: MiddlewareLogger;

  constructor() {
    this.logger = MiddlewareLogger.getInstance();
  }

  doSomething() {
    const startTime = this.logger.startOperation('MyService.doSomething', { context });
    try {
      // ... implementation
      this.logger.endOperation('MyService.doSomething', startTime, { result });
    } catch (error) {
      this.logger.failOperation('MyService.doSomething', startTime, error);
      throw error;
    }
  }
}
```

**Why:** Standardized logging, performance tracking, debugging output channel

### Pitfall #4: Skipping Pre-Task Analysis
**Bad:**
```typescript
// Just start coding without analyzing requirements
export class WorkflowCheck {
  // ... implementation without understanding integration points
}
```

**Good:**
```typescript
// 1. Pre-Task Analysis first:
//    - What services does this integrate with? (ConfidenceScorer, TestValidator)
//    - What are performance requirements? (<500ms)
//    - Are there known issues to avoid? (Pattern-PUBLISH-003)
//    - What's the best library? (Node.js built-ins vs npm)
//    - What's the TDD strategy? (Infrastructure task = 90% coverage)
// 2. Write tests first (TDD RED phase)
// 3. Then implement
```

**Why:** Prevents rework, catches issues early, ensures best-first-try outcomes

---

## Infrastructure-Specific Patterns

### Pattern-SERVICE-001: Service Integration with MiddlewareLogger
**When:** Creating any new service in VS Code extension

**Convention:**
```typescript
import { MiddlewareLogger } from './MiddlewareLogger';

export class MyService {
  private logger: MiddlewareLogger;
  private cache: Map<string, any> = new Map();

  constructor() {
    this.logger = MiddlewareLogger.getInstance();
  }

  async performOperation(context: OperationContext): Promise<Result> {
    const startTime = this.logger.startOperation('MyService.performOperation', { context });

    try {
      // Check cache first (>80% hit rate target)
      const cached = this.cache.get(context.cacheKey);
      if (cached) {
        this.logger.info('Cache hit', { key: context.cacheKey });
        return cached;
      }

      // Perform operation with timeout protection
      const result = await this.executeWithTimeout(context, 10000);

      // Update cache
      this.cache.set(context.cacheKey, result);

      this.logger.endOperation('MyService.performOperation', startTime, { result });
      return result;
    } catch (error) {
      this.logger.failOperation('MyService.performOperation', startTime, error);
      throw error;
    }
  }

  private async executeWithTimeout<T>(
    context: any,
    timeoutMs: number
  ): Promise<T> {
    return Promise.race([
      this.doWork(context),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Operation timeout')), timeoutMs)
      )
    ]);
  }
}
```

**Why:** Standardized logging, performance tracking, timeout protection, caching

### Pattern-INTEGRATION-001: Multi-Service Orchestration
**When:** Service needs to coordinate multiple other services

**Convention:**
```typescript
export class OrchestratorService {
  constructor(
    private serviceA: ServiceA,
    private serviceB: ServiceB,
    private logger: MiddlewareLogger
  ) {}

  async orchestrate(context: Context): Promise<Result> {
    const startTime = this.logger.startOperation('Orchestrate', { context });

    try {
      // 1. Call services in parallel when possible
      const [resultA, resultB] = await Promise.all([
        this.serviceA.process(context).catch(e => this.handleFailure('serviceA', e)),
        this.serviceB.process(context).catch(e => this.handleFailure('serviceB', e))
      ]);

      // 2. Graceful degradation if service fails
      if (!resultA) {
        this.logger.warn('ServiceA failed - using default');
        resultA = this.getDefaultA();
      }

      // 3. Combine results
      const combined = this.combine(resultA, resultB);

      this.logger.endOperation('Orchestrate', startTime, { combined });
      return combined;
    } catch (error) {
      this.logger.failOperation('Orchestrate', startTime, error);
      throw error;
    }
  }

  private handleFailure(serviceName: string, error: any): null {
    this.logger.error(`${serviceName} failed`, error);
    return null; // Graceful degradation
  }
}
```

**Why:** Parallel execution, graceful degradation, clear error handling

### Pattern-TASK-ANALYSIS-001: Pre-Task Analysis Protocol
**When:** Starting ANY infrastructure task

**Required Analysis (before writing ANY code):**
1. **Agent Verification**: Does agent assignment match task requirements?
2. **Tech Stack**: TypeScript version, VS Code API compatibility, Node.js version
3. **Integration Points**: What existing services will this integrate with?
4. **Known Issues**: Check Pattern-PUBLISH-003 (runtime npm deps), native dependencies
5. **Library Selection**: Node.js built-ins vs npm packages (prefer built-ins)
6. **Performance**: Calculate requirements based on task type (<500ms for workflow checks)
7. **TDD Strategy**: Infrastructure task = 90% coverage, design test cases first
8. **Clarifications**: Ask user if requirements unclear

**Why:** Prevents rework, ensures best-first-try outcomes, catches issues early

---

## Example Task Execution

**Task:** PROTO-001 - Create WorkflowCheck service

**Step 1: Pre-Task Analysis** (Pattern-TASK-ANALYSIS-001)
- ✅ Agent: infrastructure-agent matches (service orchestration)
- ✅ Tech Stack: TypeScript, VS Code APIs, Node.js built-ins only
- ✅ Integration: ConfidenceScorer, TestValidator, Git APIs
- ✅ Known Issues: Avoid runtime npm deps (Pattern-PUBLISH-003)
- ✅ Libraries: Use child_process for git, no npm packages
- ✅ Performance: <500ms for workflow check
- ✅ TDD: Infrastructure task = 90% coverage required
- ✅ Clarifications: None needed, requirements clear

**Step 2: Read Context**
- Read ConfidenceScorer.ts (understand scoring logic)
- Read TestValidator.ts (understand test validation)
- Read MiddlewareLogger.ts (logging patterns)
- Read AgentRegistry.ts (service patterns)

**Step 3: TDD - RED Phase**
- Write test: `workflowCheck.test.ts`
- Test cases: code workflow, sprint workflow, publish workflow
- Run tests → FAIL (expected)

**Step 4: TDD - GREEN Phase**
- Create `vscode-lumina/src/services/WorkflowCheck.ts`
- Implement checkWorkflow() method
- Integrate services with graceful degradation
- Run tests → PASS

**Step 5: TDD - REFACTOR Phase**
- Add caching for repeated checks
- Optimize git command execution
- Improve error messages
- Run tests → STILL PASS

**Step 6: Verify**
- Compile TypeScript: `npm run compile`
- Run tests: `npm test`
- Performance check: <500ms ✅
- Coverage check: 92% ✅

**Step 7: Document**
- Update infrastructure-agent-context.md if new patterns learned
- Add Chain of Thought comments explaining design decisions

**Step 8: Update Sprint**
- Note agent used: infrastructure-agent (v2.0)
- Note improvements: Pattern-TASK-ANALYSIS-001 applied successfully

**Completion Signal:**
```json
{
  "taskId": "PROTO-001",
  "agentType": "infrastructure-agent",
  "agentVersion": "2.0",
  "status": "success",
  "filesChanged": [
    "vscode-lumina/src/services/WorkflowCheck.ts",
    "vscode-lumina/test/services/workflowCheck.test.ts"
  ],
  "designDecisions": [
    "Used child_process for git (no npm deps)",
    "Graceful degradation if ConfidenceScorer fails (default 0.5)",
    "Caching for repeated checks (>80% hit rate)",
    "Timeout protection (10s max per check)",
    "MiddlewareLogger integration for performance tracking"
  ],
  "performance": {
    "checkTime": "347ms",
    "testCoverage": "92%",
    "cacheHitRate": "85%"
  },
  "patternsApplied": [
    "Pattern-TASK-ANALYSIS-001",
    "Pattern-SERVICE-001",
    "Pattern-INTEGRATION-001",
    "Pattern-PUBLISH-003",
    "Pattern-TDD-001"
  ],
  "nextTasks": ["PROTO-002"],
  "timestamp": 1730678400000
}
```

---

## Relevant Code Paths

**Core Services** (vscode-lumina/src/services/):
- `MiddlewareLogger.ts` - Structured logging service
- `ConfidenceScorer.ts` - Task confidence scoring
- `TestValidator.ts` - Test validation and TDD enforcement
- `AgentRegistry.ts` - Agent loading and assignment
- `TestContextGatherer.ts` - Test discovery and execution
- `TestRequirementGenerator.ts` - Auto-generate test requirements
- `ContextGatherer.ts` - Workspace context gathering

**Integration Points**:
- VS Code APIs: `vscode.workspace`, `vscode.window`
- Node.js built-ins: `child_process`, `fs`, `path`
- Git commands via child_process (avoid npm git libraries)

---

## Sprint 4 Learnings (v0.18.0) - Sync/Unsync Patterns

**Pattern:** Pattern-UI-MULTIVIEW-001 (Conditional Synchronization)
**Source:** Pop-Out Sprint View Link/Unlink Toggle feature

### Problem Solved
How to synchronize state across multiple instances conditionally - some instances sync together, others operate independently.

**Use Case:** User monitors multiple sprints on different displays:
- Main panel syncs with pop-out 1 (both show same sprint)
- Pop-out 2 is independent (shows different sprint)

### Solution: Conditional Sync with Per-Instance State

```typescript
/**
 * UNLINK-001: Per-instance state tracking (foundation)
 * Pattern-UI-MULTIVIEW-001
 */
private panelLinkStates: Map<vscode.WebviewPanel, boolean> = new Map();

private setPanelLinked(panel: vscode.WebviewPanel, isLinked: boolean): void {
    this.panelLinkStates.set(panel, isLinked);
    console.log(`[ÆtherLight] Panel link state set: isLinked=${isLinked}`);
}

private isPanelLinked(panel: vscode.WebviewPanel): boolean {
    // Default: linked (safe default preserves existing behavior)
    return this.panelLinkStates.get(panel) ?? true;
}

/**
 * UNLINK-002: Conditional sync logic
 *
 * REASONING CHAIN:
 * 1. User changes sprint in main panel (or pop-out)
 * 2. Loop through all pop-out instances
 * 3. Check if each instance should sync (isPanelLinked)
 * 4. If linked → refresh panel with new sprint
 * 5. If unlinked → skip (preserve independent state)
 * 6. Result: Linked instances stay synced, unlinked instances unaffected
 */
private async refreshLinkedPanels(): Promise<void> {
    for (const panel of this.poppedOutPanels) {
        if (this.isPanelLinked(panel)) {
            // Sync: Refresh panel to match main panel state
            panel.webview.html = this._getHtmlForWebview(panel.webview);
            console.log('[ÆtherLight] Synced linked panel');
        } else {
            // Skip: Panel is unlinked (independent state)
            console.log('[ÆtherLight] Skipped unlinked panel (independent)');
        }
    }
}

/**
 * Cleanup on disposal (prevent memory leaks)
 */
panel.onDidDispose(() => {
    this.panelLinkStates.delete(panel);
    console.log('[ÆtherLight] Panel disposed, state cleaned up');
});
```

### Key Principles

1. **Conditional Sync Logic:**
   - Loop through instances, check state, sync only if should sync
   - Complexity: O(N) where N = number of instances (typically 1-3)
   - Performance: 5-15ms for 3 panels

2. **Safe Defaults:**
   - `?? true` ensures new panels default to linked (preserves existing UX)
   - Unlink is opt-in (user-initiated toggle)

3. **Memory Management:**
   - `onDidDispose()` cleanup prevents memory leaks
   - Map automatically releases references when entries removed

4. **Logging for Debugging:**
   - Console.log state changes for troubleshooting
   - Pattern-TRACKING-001 compliance

### Performance Characteristics

**State Access (UNLINK-001):**
- Map.get(): O(1) lookup
- Measured: <1ms per call
- Memory: ~48 bytes per panel

**Sync Logic (UNLINK-002):**
- Loop + conditional refresh: O(N)
- Measured: 5-15ms for 3 panels
- Scales linearly with instance count

**Cleanup:**
- Map.delete(): O(1)
- Automatic GC when panel disposed

### When to Use Conditional Sync

**Use When:**
- ✅ Multiple instances need selective synchronization
- ✅ Some instances should sync, others shouldn't
- ✅ User controls sync behavior (toggle, checkbox)
- ✅ Independent workflows per instance

**Don't Use When:**
- ❌ All instances always sync (use global state change + loop)
- ❌ No instances ever sync (pure independent state)
- ❌ Single instance (no sync needed)

### Implementation Checklist

- [ ] Add Map<Instance, SyncState> private property
- [ ] Implement setState() and getState() with safe default
- [ ] Add cleanup on instance disposal (onDidDispose)
- [ ] Implement conditional sync loop (check state → sync if true)
- [ ] Add logging for debugging (state changes, sync actions)
- [ ] Write tests (state isolation, sync behavior, cleanup)

### Files
- Implementation: `vscode-lumina/src/commands/voicePanel.ts:89, 383-405, 1430-1456`
- Pattern: `docs/patterns/Pattern-UI-MULTIVIEW-001.md`
- Tests: `vscode-lumina/test/commands/voicePanel.linkState.test.ts`

---

## Token-Based Monetization System (Pattern-MONETIZATION-001)

**Added:** v0.17.0 (Sprint 4)
**Pattern Reference:** [Pattern-MONETIZATION-001](../../docs/patterns/Pattern-MONETIZATION-001.md)

### Overview

**Architecture:** Desktop App (Rust/Tauri) → Server API (Next.js/Vercel) → OpenAI Whisper API

**Key Changes from BYOK:**
- ❌ NO OpenAI API keys in desktop app or extension
- ✅ Server holds single OpenAI API key (env variable)
- ✅ Users authenticate with license keys (format: XXXX-XXXX-XXXX-XXXX)
- ✅ Token-based pricing: 375 tokens = 1 minute of transcription
- ✅ Server tracks usage, enforces limits, deducts tokens

### Desktop App Integration (Rust/Tauri)

**Files:**
- `products/lumina-desktop/src-tauri/src/transcription.rs` - Server API integration
- `products/lumina-desktop/src/components/VoiceCapture.tsx` - Token balance UI
- `products/lumina-desktop/src/components/InstallationWizard.tsx` - License key activation

**Key Rust Structs:**
```rust
// products/lumina-desktop/src-tauri/src/transcription.rs

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct TokenWarning {
    pub level: String,        // "medium" | "high" | "critical"
    pub threshold: u8,        // 80 | 90 | 95
    pub message: String,
    pub percentage_used: u8,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct TokenBalanceResponse {
    pub success: bool,
    pub tokens_balance: u64,
    pub tokens_used_this_month: u64,
    pub subscription_tier: String,
    pub minutes_remaining: u64,
    #[serde(default)]
    pub warnings: Vec<TokenWarning>,  // Server-calculated
}
```

**Critical Functions:**
1. `check_token_balance(license_key, api_url)` - Pre-flight check before recording
2. `transcribe_audio(audio_samples, sample_rate, license_key, api_url)` - Server-proxied transcription
3. `type_transcript(transcript)` - OS-level keyboard simulation

**Pre-Flight Check Flow:**
1. User presses hotkey (Shift+~ or `)
2. Desktop app calls `check_token_balance()`
3. Server returns balance + warnings
4. If balance < 375 tokens → Show "Insufficient Tokens" modal
5. If balance >= 375 tokens → Allow recording

**Transcription Flow:**
1. Desktop captures audio (f32 samples at 44.1kHz or 16kHz)
2. Convert to WAV format (in-memory)
3. POST to `/api/desktop/transcribe` with Bearer token
4. Server authenticates license key → calls OpenAI → deducts tokens
5. Desktop receives transcript + tokens used + new balance
6. Type transcript at cursor position (OS-level)

### Server API Integration

**Base URL:** `https://aetherlight-aelors-projects.vercel.app`

**Authentication:** Bearer token (license_key in Authorization header)

**API Endpoints:**
- `GET /api/tokens/balance` - Check balance, get warnings
- `POST /api/desktop/transcribe` - Transcribe audio + deduct tokens
- `POST /api/tokens/consume` - Manual token deduction (future features)
- `POST /api/stripe/create-checkout` - Token purchase / subscription
- `POST /api/webhooks/stripe` - Stripe webhook fulfillment
- `POST /api/cron/refresh-tokens` - Monthly refresh (Vercel Cron)

### Database Schema (Supabase)

**Tables:**
- `profiles` - User accounts with tokens_balance, subscription_tier
- `devices` - License keys linked to user_id
- `usage_events` - Transcription events (tokens_used, duration_seconds)
- `credit_transactions` - Transaction log (usage, purchase, refund, monthly_refresh)

**Migrations:**
- `website/supabase/migrations/007_credit_system.sql`
- `website/supabase/migrations/008_token_system.sql`

### Warning System (Server-Calculated)

**Thresholds:**
- 80% used → `medium` warning (yellow toast)
- 90% used → `high` warning (orange toast)
- 95% used → `critical` warning (red toast)

**Calculation:**
```typescript
const startingBalance = tier === 'pro' ? 1000000 : 250000;
const percentageUsed = ((startingBalance - tokensBalance) / startingBalance) * 100;
```

**Desktop Display:**
```typescript
// products/lumina-desktop/src/components/VoiceCapture.tsx
const checkBalanceWarnings = (balance: TokenBalanceResponse) => {
  if (!balance.warnings || balance.warnings.length === 0) return;
  const highestWarning = balance.warnings[0];
  if (lastWarningThreshold === highestWarning.threshold) return;  // Prevent duplicates
  setToastMessage(highestWarning.message);
  setShowLowBalanceToast(true);
  setTimeout(() => setShowLowBalanceToast(false), 5000);
};
```

### Pricing Tiers

| Tier | Tokens | Minutes | Cost | Expiration |
|------|--------|---------|------|------------|
| Free | 250,000 | ~666 | $0 | Never |
| Token Purchase | 1,000,000 | ~2,666 | $24.99 one-time | Never |
| Pro Subscription | 1,000,000/month | ~2,666/month | $29.99/month | Monthly refresh |

### Monthly Token Refresh

**Automation:** Vercel Cron job (runs 1st of each month at 00:00 UTC)

**Logic:**
```sql
UPDATE profiles
SET tokens_balance = 1000000, tokens_used_this_month = 0, token_refresh_date = NOW()
WHERE subscription_tier = 'pro'
  AND (token_refresh_date IS NULL OR token_refresh_date < NOW() - INTERVAL '30 days');
```

**Files:**
- `website/app/api/cron/refresh-tokens/route.ts`
- `website/vercel.json` (cron schedule configuration)

### Security Considerations

**OpenAI API Key:**
- Stored in Vercel environment variable (`OPENAI_API_KEY`)
- NEVER sent to clients (server-side only)
- Used only in `/api/desktop/transcribe` endpoint

**License Key:**
- Stored in `devices` table (plain text for lookups)
- Transmitted via HTTPS only (TLS 1.3)
- Rate limiting: 10 requests/minute per key

**RLS (Row Level Security):**
- API uses service role key (bypasses RLS)
- License key validation provides authorization
- Direct database access from clients blocked

### Testing Credentials (Production)

**Free Tier:**
- License Key: `CD7W-AJDK-RLQT-LUFA`
- Tokens: 250,000 (~666 minutes)

**Pro Tier:**
- License Key: `W7HD-X79Q-CQJ9-XW13`
- Tokens: 1,000,000/month (~2,666 minutes)

### Critical Implementation Details

**Error Handling:**
- `401 Unauthorized` - Invalid/missing license key
- `402 Payment Required` - Insufficient tokens (show exact shortfall)
- `403 Forbidden` - Device not active
- `400 Bad Request` - Invalid audio file
- `500 Internal Server Error` - OpenAI error or server error

**Token Deduction:**
- RPC function: `record_token_transaction(user_id, -tokens_used, 'usage', 'Transcription')`
- Atomic operation (database handles concurrency)
- Logs in `credit_transactions` table

**Performance:**
- Balance check: <200ms (cached on desktop app side)
- Transcription: 2-5 seconds (network hop + OpenAI processing)
- Typing: ~5ms/character (200 chars/second)

### Migration from BYOK (v0.16.x)

**Breaking Changes:**
- Extension v0.17.0 requires desktop app v0.17.0 (must upgrade together)
- OpenAI API key settings deprecated (no longer functional)
- All users must sign up and activate license key

**User Migration Flow:**
1. Update extension + desktop app to v0.17.0
2. Sign up at https://aetherlight.dev/signup
3. Get license key from dashboard
4. Enter key in desktop app installation wizard (Step 3)
5. Start recording (works immediately)

See: [MIGRATION_GUIDE.md](../../MIGRATION_GUIDE.md)

---

**You are now ready to execute infrastructure tasks autonomously with Pattern-TASK-ANALYSIS-001 and full knowledge of Pattern-MONETIZATION-001.**
