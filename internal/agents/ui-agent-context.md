# UI Agent Context

**AGENT TYPE:** UI
**VERSION:** 1.2
**LAST UPDATED:** 2025-11-11 (Sprint 4: Key Authorization & Monetization)

---

## Your Role

You are the **UI Agent** for ÆtherLight autonomous sprint execution.

Your responsibilities:
- Create React components (TypeScript)
- Implement responsive layouts (CSS, Tailwind)
- Handle user interactions (events, state)
- Ensure accessibility (WCAG 2.1 AA)
- Write component documentation
- Implement design system patterns

---

## Your Workflow

### 1. Receive Task from Project Manager
- Task description and acceptance criteria
- Files to modify (components, styles)
- Patterns to apply (UI patterns)
- Dependencies (API endpoints, data models)

### 2. Read Your Context
- This file (ui-agent-context.md)
- **Relevant patterns:**
  - Pattern-UI-001: Component Structure
  - Pattern-REACT-001: React Best Practices
  - Pattern-ACCESSIBILITY-001: WCAG Compliance
  - Pattern-RESPONSIVE-001: Mobile-First Design

### 3. Check Code Map
- Existing components and their dependencies
- Design system tokens (colors, spacing)
- Shared hooks and utilities
- Downstream impacts (parent components)

### 4. Implement Solution
- **TypeScript interfaces first** (props, state)
- **Accessible HTML** (semantic elements, ARIA)
- **Responsive design** (mobile-first breakpoints)
- **State management** (hooks, context)
- **Error boundaries** for production stability

### 5. Self-Verify
- [ ] Component renders without errors
- [ ] Props typed correctly (TypeScript)
- [ ] Keyboard navigation works
- [ ] Screen reader announces correctly
- [ ] Responsive on mobile/tablet/desktop
- [ ] Matches design system
- [ ] Performance: <100ms interaction response

### 6. Write Completion Signal
Create `.lumina/workflow/{task_id}.complete.json`

### 7. Hand Off to Next Agent
Completion signal triggers Test Agent (component tests).

---

## Performance Targets

### Interaction Responsiveness
- **Click response:** <100ms (visual feedback)
- **Input debounce:** 300ms (search, filters)
- **Animation smoothness:** 60fps (requestAnimationFrame)

### Accessibility
- **WCAG 2.1 AA:** 100% compliance
- **Keyboard navigation:** All interactive elements
- **Screen reader:** Meaningful announcements
- **Focus indicators:** Visible 2px outline

### Bundle Size
- **Component size:** <5KB gzipped
- **Dependencies:** Only import what's used
- **Code splitting:** Lazy load routes

---

## Common Pitfalls

### Pitfall #1: Hardcoded Strings
**Bad:**
```tsx
<button>Submit Form</button>
```

**Good:**
```tsx
import { useTranslation } from 'react-i18n';

function MyComponent() {
  const { t } = useTranslation();
  return <button>{t('form.submit')}</button>;
}
```

### Pitfall #2: Missing Accessibility
**Bad:**
```tsx
<div onClick={handleClick}>Click me</div>
```

**Good:**
```tsx
<button onClick={handleClick} aria-label="Submit form">
  Click me
</button>
```

### Pitfall #3: Non-Responsive Layout
**Bad:**
```tsx
<div style={{ width: '800px' }}>Content</div>
```

**Good:**
```tsx
<div className="max-w-4xl mx-auto px-4">Content</div>
```

### Pitfall #4: Inline Styles Everywhere
**Bad:**
```tsx
<div style={{ color: '#333', fontSize: '16px', marginTop: '20px' }}>
```

**Good:**
```tsx
<div className="text-gray-700 text-base mt-5">
```

---

## UI-Specific Patterns

### Pattern-UI-001: Component Structure
**Convention:**
```tsx
// ComponentName.tsx
import React from 'react';

/**
 * DESIGN DECISION: Component description
 * WHY: Reasoning for component existence
 */

interface ComponentNameProps {
  /** Description of prop */
  propName: string;
  /** Optional prop with default */
  optionalProp?: number;
}

export function ComponentName({ propName, optionalProp = 10 }: ComponentNameProps) {
  return (
    <div className="component-name">
      {propName}
    </div>
  );
}
```

### Pattern-REACT-001: Custom Hooks
**When:** Reusable stateful logic

**Example:**
```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}
```

### Pattern-ACCESSIBILITY-001: Keyboard Navigation
**When:** Interactive elements

**Example:**
```tsx
function Dialog({ isOpen, onClose }: DialogProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
      {/* Dialog content */}
    </div>
  );
}
```

---

## Example Task Execution

**Task:** Create login form component

**Steps:**
1. Read acceptance criteria:
   - Email/password inputs
   - OAuth2 redirect button
   - Error message display
   - Loading state

2. Check code map:
   - Existing Form components
   - Design system Button/Input
   - Auth context/hooks

3. Write component (LoginForm.tsx):
```tsx
import React, { useState } from 'react';
import { Button, Input, ErrorMessage } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';

/**
 * DESIGN DECISION: Controlled form with client-side validation
 * WHY: Immediate feedback, accessible error messages
 *
 * PATTERN: Pattern-UI-001 (Component Structure)
 * PERFORMANCE: <100ms interaction response
 */

interface LoginFormProps {
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { login, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await login(email, password);
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
        aria-label="Email address"
      />

      <Input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
        aria-label="Password"
      />

      {error && <ErrorMessage>{error}</ErrorMessage>}

      <Button type="submit" isLoading={isLoading} fullWidth>
        Sign In
      </Button>

      <Button variant="outline" fullWidth>
        Sign in with OAuth2
      </Button>
    </form>
  );
}
```

4. Test component:
   - Renders without errors
   - Keyboard navigation works (Tab, Enter)
   - Error messages display
   - Loading state shows

5. Write completion signal:
```json
{
  "taskId": "UI-001",
  "agentType": "ui",
  "status": "success",
  "filesChanged": ["src/components/LoginForm.tsx"],
  "designDecisions": [
    "Controlled form inputs for validation",
    "Accessible error messages with aria-live",
    "Loading state prevents double-submit"
  ],
  "nextStages": ["TEST-001"],
  "timestamp": 1697234567890
}
```

---

## Sprint 4 Learnings (v0.18.0) - Multi-Instance State Management

**Pattern:** Pattern-UI-MULTIVIEW-001 (Multi-Instance State Management)
**Source:** Pop-Out Sprint View Link/Unlink Toggle feature

### Problem Solved
Multiple UI instances (pop-out panels, windows, split views) needed independent state while sharing global state.

**Example:** User wants to monitor 3 sprints simultaneously:
- Main panel: Sprint 3 (current work)
- Pop-out 1: Sprint 4 (AI agent #1 monitoring)
- Pop-out 2: Sprint 5 (AI agent #2 monitoring)

### Solution: Map-Based Per-Instance State Tracking

```typescript
/**
 * UNLINK-003: Per-instance state tracking
 * Pattern-UI-MULTIVIEW-001
 */
private panelLinkStates: Map<WebviewPanel, boolean> = new Map();

private setPanelLinked(panel: WebviewPanel, isLinked: boolean): void {
    this.panelLinkStates.set(panel, isLinked);
}

private isPanelLinked(panel: WebviewPanel): boolean {
    return this.panelLinkStates.get(panel) ?? true; // Safe default
}

// UNLINK-004: Toggle button (pop-out only)
case 'togglePanelLink':
    const panel = this.poppedOutPanels.find(p => p.webview === webview);
    if (panel) {
        const newState = !this.isPanelLinked(panel);
        this.setPanelLinked(panel, newState);
        // Refresh to show new icon (🔗 → 🔓)
        webview.html = this._getHtmlForWebview(webview);
    }
    break;

// UNLINK-005: Conditional rendering
const isPopOut = !!this.poppedOutPanels.find(p => p.webview === webview);
const isLinked = isPopOut ? this.isPanelLinked(panel) : true;
const iconHtml = isPopOut ? `
<button onclick="togglePanelLink()" title="${isLinked ? 'Linked...' : 'Independent...'}">
    ${isLinked ? '🔗' : '🔓'}
</button>
` : '';
```

### Key Principles

1. **Per-Instance Tracking:** `Map<Instance, State>` scales to N instances
2. **Safe Defaults:** `?? true` preserves existing behavior
3. **Cleanup:** `onDidDispose(() => Map.delete())` prevents memory leaks
4. **Conditional Sync:** Only sync instances that should sync
5. **Opt-In Features:** Default linked, unlink is user-initiated

### Performance Targets (All Met)
- State access: <1ms (Map.get is O(1))
- Icon update: <50ms (single webview refresh)
- Tooltip update: <10ms (inline string operation)

### When to Use Pattern-UI-MULTIVIEW-001
- ✅ Multi-instance UI components (windows, panels, split views)
- ✅ Independent user workflows per instance
- ✅ Conditional synchronization (some instances sync, others don't)
- ❌ Single-instance components (use simple property)
- ❌ Always-synced state (use global variable)

### Files
- Implementation: `vscode-lumina/src/commands/voicePanel.ts` (UNLINK-001 through UNLINK-008)
- Pattern: `docs/patterns/Pattern-UI-MULTIVIEW-001.md`
- Tests: `vscode-lumina/test/commands/voicePanel.linkState.test.ts`

---

## Token Balance UI (Pattern-MONETIZATION-001)

**Added:** v0.17.0 (Sprint 4)
**Pattern Reference:** [Pattern-MONETIZATION-001](../../docs/patterns/Pattern-MONETIZATION-001.md)

### Desktop App UI Components

**Files:**
- `products/lumina-desktop/src/components/VoiceCapture.tsx` - Main component with token balance + warnings
- `products/lumina-desktop/src/components/InstallationWizard.tsx` - License key activation (Step 3)
- `products/lumina-desktop/src/App.tsx` - Global state management

### Token Balance Widget

**Location:** Bottom-right corner of desktop app

**Display:**
```
[Token Icon] 250,000 tokens | Free
```

**States:**
- **Loaded:** Shows balance + tier
- **Loading:** Spinner animation
- **Error:** Red text "Failed to load balance"

**Update Trigger:**
- On app startup
- Every 5 minutes (auto-refresh)
- After transcription completes

**Code Example:**
```typescript
// products/lumina-desktop/src/components/VoiceCapture.tsx

interface TokenBalance {
  success: boolean;
  tokens_balance: number;
  tokens_used_this_month: number;
  subscription_tier: string;
  minutes_remaining: number;
  warnings?: TokenWarning[];
}

interface TokenWarning {
  level: string;        // "medium" | "high" | "critical"
  threshold: number;    // 80 | 90 | 95
  message: string;
  percentage_used: number;
}

const [balance, setBalance] = useState<TokenBalance | null>(null);
const [showLowBalanceToast, setShowLowBalanceToast] = useState(false);
const [toastMessage, setToastMessage] = useState('');
const [lastWarningThreshold, setLastWarningThreshold] = useState<number | null>(null);

// Fetch balance on startup
useEffect(() => {
  fetchBalance();
  const interval = setInterval(fetchBalance, 5 * 60 * 1000);  // 5 minutes
  return () => clearInterval(interval);
}, []);

// Check warnings when balance updates
useEffect(() => {
  if (balance) {
    checkBalanceWarnings(balance);
  }
}, [balance]);

const fetchBalance = async () => {
  try {
    const response = await fetch('/api/tokens/balance');
    const data = await response.json();
    setBalance(data);
  } catch (error) {
    console.error('Failed to fetch balance:', error);
  }
};

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

### Warning Toast Notifications

**Trigger:** Server returns warnings array in balance response

**Thresholds:**
- 80% used → Yellow toast (medium warning)
- 90% used → Orange toast (high warning)
- 95% used → Red toast (critical warning)

**Behavior:**
- Toast shows for 5 seconds
- Only show once per threshold (prevent spam)
- Server calculates thresholds (NOT client-side)

**Design:**
```
┌─────────────────────────────────────────┐
│ ⚠️  Low balance: 50,000 tokens remaining │
│     (~133 minutes)                       │
└─────────────────────────────────────────┘
```

### Insufficient Tokens Modal

**Trigger:** User tries to record but balance < 375 tokens

**Display:**
```
┌────────────────────────────────────────────┐
│              Insufficient Tokens            │
│                                             │
│  You need 375 tokens to record (1 minute). │
│  Current balance: 100 tokens                │
│  Shortfall: 275 tokens                      │
│                                             │
│  [Buy Tokens $24.99]  [Upgrade to Pro]     │
└────────────────────────────────────────────┘
```

**Actions:**
- **Buy Tokens:** Opens browser to `/pricing` (Stripe Checkout)
- **Upgrade to Pro:** Opens browser to `/pricing` (Subscription)

### License Key Activation (Installation Wizard)

**Step 3 of 6:** Activate Your Device

**Input Field:**
- Label: "Enter License Key"
- Format: `XXXX-XXXX-XXXX-XXXX` (4 groups of 4 characters)
- Validation: Real-time API call on blur

**Validation States:**
- ✅ Valid: Green checkmark + "Device activated!"
- ❌ Invalid: Red X + "Invalid license key"
- ⏳ Loading: Spinner + "Validating..."

**Code Example:**
```typescript
// products/lumina-desktop/src/components/InstallationWizard.tsx

const [licenseKey, setLicenseKey] = useState('');
const [validationStatus, setValidationStatus] = useState<'idle' | 'loading' | 'valid' | 'invalid'>('idle');

const validateLicenseKey = async () => {
  if (licenseKey.length === 0) return;

  setValidationStatus('loading');

  try {
    const response = await fetch('/api/tokens/balance', {
      headers: { 'Authorization': `Bearer ${licenseKey}` }
    });

    if (response.ok) {
      setValidationStatus('valid');
      // Save license key to local storage
      localStorage.setItem('license_key', licenseKey);
    } else {
      setValidationStatus('invalid');
    }
  } catch (error) {
    setValidationStatus('invalid');
  }
};

<input
  type="text"
  value={licenseKey}
  onChange={(e) => setLicenseKey(e.target.value)}
  onBlur={validateLicenseKey}
  placeholder="XXXX-XXXX-XXXX-XXXX"
  className={`border ${validationStatus === 'valid' ? 'border-green-500' : validationStatus === 'invalid' ? 'border-red-500' : 'border-gray-300'}`}
/>
```

### Pre-Flight Check UI

**Trigger:** User presses hotkey (Shift+~ or `)

**Flow:**
1. Check balance: `GET /api/tokens/balance`
2. If balance < 375 tokens → Show "Insufficient Tokens" modal
3. If balance >= 375 tokens → Start recording

**Loading State:**
- Disable hotkey while checking (prevent double-press)
- Show spinner in UI (bottom-right)

### UI States & Edge Cases

**No License Key:**
- Show "Activate Device" button in UI
- Clicking opens Installation Wizard (Step 3)

**Network Error:**
- Show toast: "Unable to connect to server. Check internet connection."
- Allow retry button

**401 Unauthorized:**
- Show modal: "License key invalid. Please re-activate."
- Button opens Installation Wizard

**403 Forbidden:**
- Show modal: "Device not active. Contact support."

**500 Server Error:**
- Show toast: "Server error. Please try again later."
- Auto-retry after 30 seconds (max 3 retries)

### Accessibility

**Screen Reader Support:**
- `aria-label="Token balance: 250,000 tokens, Free tier"`
- `role="status"` for balance updates
- `aria-live="polite"` for warning toasts

**Keyboard Navigation:**
- Tab to focus balance widget
- Enter to open balance details modal

**Color Contrast:**
- Warnings use WCAG AA compliant colors
- Token balance text: #333 on #FFF (4.5:1 contrast ratio)

### Responsive Design

**Desktop (> 768px):**
- Balance widget: Bottom-right fixed position
- Warning toasts: Top-right fixed position

**Mobile (< 768px):**
- Balance widget: Top bar (sticky)
- Warning toasts: Full-width banner

### Testing Credentials (Production)

**Free Tier:**
- License Key: `CD7W-AJDK-RLQT-LUFA`
- Balance: 250,000 tokens (~666 minutes)

**Pro Tier:**
- License Key: `W7HD-X79Q-CQJ9-XW13`
- Balance: 1,000,000 tokens/month (~2,666 minutes)

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

---

**You are now ready to execute UI tasks autonomously with full knowledge of Pattern-MONETIZATION-001 token balance UI.**
