# Pattern-TESTING-001: Manual Testing Methodology for VS Code Extensions

**CREATED:** 2025-11-01
**CATEGORY:** Quality Assurance + Testing
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 1.00
**APPLICABILITY:** General use
**STATUS:** Active (Required for v0.15.4+)
**RELATED:** PATTERN-UI-006, PATTERN-TERMINAL-001, PATTERN-VOICE-001, PATTERN-DOCUMENTATION-001

---




## Problem Statement

**Current State:**
- No automated tests for ÆtherLight VS Code extension
- Bug fixes deployed without systematic validation
- No test documentation or screenshots for proof
- Manual testing is ad-hoc, not repeatable
- Regressions slip through (bugs fixed then re-introduced)
- No checklist for release validation

**Example Failure:**
```
v0.15.3 Release (without Pattern-TESTING-001):
1. Fixed bug → deployed
2. No test documentation
3. No screenshots proving fix works
4. Bug reappeared in v0.15.4 (regression)
5. User reports same bug again
6. No way to verify original fix was correct

Audit Score: 15/80 (19%) - FAILED
Critical Bugs Found: 4 (all untested)
```

**ROOT CAUSE:**
- No testing pattern/methodology
- No test documentation standard
- No proof of testing (screenshots, logs)
- Manual testing not systematic

---

## Solution Pattern

**DESIGN DECISION:** Systematic manual testing with documentation + screenshots for proof

**WHY:**
- Automated testing for VS Code extensions is complex (requires Extension Development Host)
- Manual testing is faster to implement (no test infrastructure needed)
- Documentation prevents regressions (test steps captured)
- Screenshots provide proof (before/after visual evidence)
- Systematic approach = repeatable, thorough

**REASONING CHAIN:**
1. Bug identified (from audit or user report)
2. Document bug reproduction steps
3. Implement fix
4. Test fix systematically (reproduce → verify → edge cases)
5. Take before/after screenshots
6. Document test results in TESTING_LOG.md
7. Update KNOWN_ISSUES.md (mark bug as fixed)
8. Result: Verified fix + proof + documentation for future reference

---

## Core Components

### 1. Test Template (Per Bug/Feature)

**Location:** `TESTING_LOG.md` (root directory)

**Structure:**
```markdown
# Test: [BUG-ID or FEATURE-ID] - [Bug/Feature Name]

**Date:** 2025-11-01
**Tester:** BB_Aelor
**Version:** v0.15.4
**Status:** ✅ PASS / ❌ FAIL / ⚠️ PARTIAL

---

## Test Case: [Brief Description]

### Prerequisites
- VS Code version: 1.85.0+
- Extension installed: ÆtherLight v0.15.4
- Workspace: lumina-clean (or test workspace)
- Terminal: bash (or other shell)

### Reproduction Steps (Before Fix)
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:** [What should happen]
**Actual Behavior:** [What actually happens - THE BUG]

**Screenshot:** `screenshots/BUG-XXX-before.png`

---

### Test Steps (After Fix)
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:** [What should happen]
**Actual Behavior:** [What actually happens now]

**Result:** ✅ PASS

**Screenshot:** `screenshots/BUG-XXX-after.png`

---

### Edge Cases Tested
1. **Edge Case 1:** [Description]
   - Steps: [...]
   - Result: ✅ PASS

2. **Edge Case 2:** [Description]
   - Steps: [...]
   - Result: ✅ PASS

---

### Performance Validation
- **Metric 1:** [e.g., Record button latency] < 100ms ✅
- **Metric 2:** [e.g., Terminal list refresh] < 10ms ✅

---

### Regression Check
- **Related Feature 1:** [Still works] ✅
- **Related Feature 2:** [Still works] ✅

---

## Conclusion

**Status:** ✅ PASS
**Confidence:** High
**Notes:** [Any additional observations]
**Next Steps:** [Update KNOWN_ISSUES.md, close issue, etc.]

---
```

### 2. Testing Checklist (Per Release)

**Location:** `TESTING_CHECKLIST.md` (root directory)

**Structure:**
```markdown
# ÆtherLight v0.15.4 Testing Checklist

**Release Date:** 2025-11-01
**Tester:** BB_Aelor
**Status:** 🟡 In Progress / ✅ Complete

---

## Critical Bug Fixes (Phase 0)

- [ ] **BUG-008:** Record button triggers voice capture
  - Test: Click record button → recording starts
  - Screenshot: `screenshots/BUG-008-fixed.png`
  - Status: ✅ PASS

- [ ] **BUG-009:** Enhancement button enhances text in-place
  - Test: Type text → click ✨ → text enhanced
  - Screenshot: `screenshots/BUG-009-fixed.png`
  - Status: ✅ PASS

- [ ] **BUG-010:** Send to terminal executes command
  - Test: Send command → command executes in terminal
  - Screenshot: `screenshots/BUG-010-fixed.png`
  - Status: ✅ PASS

- [ ] **BUG-011:** Cursor returns to textarea after send
  - Test: Send command → cursor stays in textarea
  - Screenshot: `screenshots/BUG-011-fixed.png`
  - Status: ✅ PASS

---

## UI Layout Validation (Phase 1-2)

- [ ] **UI-ARCH-001:** No Voice tab in tab bar
- [ ] **UI-ARCH-002:** Only 2 tabs (Default, Settings)
- [ ] **UI-ARCH-003:** Voice section at top
- [ ] **TERM-001:** Multi-row terminal list
- [ ] **TERM-002:** Terminal icons (busy/idle)
- [ ] **TERM-003:** Smart terminal selection

---

## E2E Workflow Test (Phase 3)

- [ ] **Voice Capture:** Speak → transcribe → insert
- [ ] **Enhancement:** Type → enhance → send to terminal
- [ ] **Multi-Terminal:** Send to Review → Deploy → Test
- [ ] **Sprint Loader:** Load sprint → view tasks
- [ ] **Settings:** Update config → settings persist

---

## Performance Benchmarks

- [ ] **Voice Panel Load:** < 500ms
- [ ] **Sprint TOML Parse:** < 5ms
- [ ] **Terminal List Refresh:** < 10ms
- [ ] **Tab Switch:** < 50ms
- [ ] **HTML Generation:** < 200ms

---

## Regression Tests

- [ ] **v0.15.3 Features:** All still work
- [ ] **Hotkeys:** All keyboard shortcuts functional
- [ ] **File Watchers:** Sprint TOML auto-refresh works
- [ ] **Terminal Events:** Create/close/rename terminal updates UI

---

## Sign-Off

**All Tests Pass:** ✅ YES / ❌ NO
**Ready for Release:** ✅ YES / ❌ NO
**Blocker Issues:** [None or list issues]

**Tester Signature:** BB_Aelor
**Date:** 2025-11-01

---
```

### 3. Screenshot Naming Convention

**Location:** `screenshots/` (root directory)

**Naming Pattern:**
```
[TASK-ID]-[state]-[description].png

Examples:
✅ BUG-008-before.png (shows bug)
✅ BUG-008-after.png (shows fix)
✅ BUG-009-before-no-enhancement.png
✅ BUG-009-after-enhanced-text.png
✅ UI-ARCH-001-new-layout.png
✅ TERM-001-multi-row-terminals.png

❌ screenshot1.png (ambiguous)
❌ fixed.png (no context)
❌ test.png (no context)
```

**Screenshot Standards:**
- Resolution: 1920x1080 (or actual VS Code window size)
- Format: PNG (lossless, good for text)
- Annotations: Use red boxes/arrows for important areas
- Timestamp: Visible in screenshot or filename metadata

### 4. Test Execution Workflow

**Step 1: Setup Test Environment**
```bash
# Clean VS Code profile (no other extensions)
code --profile "ÆtherLight Testing" --disable-extensions

# Install extension under test
cd vscode-lumina
npm run compile
vsce package
code --install-extension aetherlight-0.15.4.vsix

# Reload VS Code
# Ctrl+Shift+P → Developer: Reload Window
```

**Step 2: Execute Test Cases**
```markdown
1. Open TESTING_LOG.md
2. For each test case:
   a. Read prerequisites
   b. Follow reproduction steps (capture "before" state)
   c. Take "before" screenshot
   d. Verify bug exists
   e. Apply fix (if not already applied)
   f. Follow test steps
   g. Take "after" screenshot
   h. Test edge cases
   i. Document results (PASS/FAIL)
   j. Move to next test case
```

**Step 3: Validate Performance**
```bash
# Check VS Code Developer Tools for timing
# Ctrl+Shift+P → Developer: Toggle Developer Tools
# Console tab → measure performance

console.time('voicePanelLoad');
// Open voice panel
console.timeEnd('voicePanelLoad');
// Expected: < 500ms
```

**Step 4: Check for Regressions**
```markdown
Test all features from previous version:
1. Voice capture (v0.15.0 feature) - Still works?
2. Sprint loader (v0.15.1 feature) - Still works?
3. Auto-update (v0.15.3 feature) - Still works?
4. Desktop app integration (v0.15.2) - Still works?

If any regression found → FAIL → fix before release
```

**Step 5: Document Results**
```bash
# Update TESTING_LOG.md with all test results
# Update TESTING_CHECKLIST.md (check boxes)
# Commit screenshots to git
git add screenshots/*.png
git add TESTING_LOG.md TESTING_CHECKLIST.md
git commit -m "test: validate v0.15.4 bug fixes (all pass)"
```

---

## Usage Examples

### Example 1: Testing BUG-008 (Record Button)

```markdown
# Test: BUG-008 - Fix Record Button

**Date:** 2025-11-01
**Tester:** BB_Aelor
**Version:** v0.15.4
**Status:** ✅ PASS

---

## Test Case: Record button triggers voice capture

### Prerequisites
- VS Code version: 1.85.0
- Extension installed: ÆtherLight v0.15.4
- Workspace: lumina-clean
- Desktop app: Running on localhost:3001

### Reproduction Steps (Before Fix)
1. Open Voice Panel (click ÆtherLight icon in Activity Bar)
2. Click red record button (🔴)
3. Observe behavior

**Expected Behavior:** Recording starts, button shows "Recording..."
**Actual Behavior:** Nothing happens (bug: button calls openVoicePanel instead of startRecording)

**Screenshot:** `screenshots/BUG-008-before.png`
**Code Reference:** `voicePanel.ts:1061-1070`

---

### Test Steps (After Fix)
1. Open Voice Panel
2. Click red record button (🔴)
3. Observe behavior

**Expected Behavior:** Recording starts, button shows "Recording..."
**Actual Behavior:** Recording starts immediately, button shows "Recording...", audio capture begins

**Result:** ✅ PASS

**Screenshot:** `screenshots/BUG-008-after.png`

---

### Edge Cases Tested
1. **Multiple clicks:** Click record button twice rapidly
   - Steps: Click → Click → Wait
   - Result: ✅ PASS (debounced, only one recording starts)

2. **Stop during recording:** Start recording → stop immediately
   - Steps: Record → Stop (< 1 second)
   - Result: ✅ PASS (recording stops, no transcription sent)

3. **Record without desktop app:** Desktop app not running
   - Steps: Stop desktop app → Click record
   - Result: ✅ PASS (error message: "Desktop app not available")

---

### Performance Validation
- **Record button click → recording starts:** 85ms ✅ (target: < 100ms)
- **WebSocket connection:** 42ms ✅ (target: < 100ms)

---

### Regression Check
- **Backtick key (`) still works:** ✅ PASS (opens voice panel)
- **Voice panel opens on first install:** ✅ PASS (no errors)
- **Settings persist across sessions:** ✅ PASS (selected terminal saved)

---

## Conclusion

**Status:** ✅ PASS
**Confidence:** High
**Notes:** Fix confirmed working, all edge cases handled correctly
**Next Steps:** Update KNOWN_ISSUES.md, mark BUG-008 as fixed

---
```

### Example 2: Testing UI Layout (TEST-002)

```markdown
# Test: TEST-002 - UI Layout Validation

**Date:** 2025-11-01
**Tester:** BB_Aelor
**Version:** v0.15.4
**Status:** ✅ PASS

---

## Test Case: Verify UI layout matches user requirements

### Prerequisites
- VS Code version: 1.85.0
- Extension installed: ÆtherLight v0.15.4
- Reference: User screenshots from v0.15.3_AUDIT_RESULTS.md

### Validation Checklist

**Layout Order (Top → Bottom):**
1. ✅ Terminal List (multi-row, with icons)
2. ✅ Toolbar (Enhance ✨, Send to Terminal)
3. ✅ Textarea (voice input)
4. ✅ Tab Bar (Default | Settings)
5. ✅ Tab Content (current tab)
6. ✅ Bug Toolbar (bottom, floating)

**Screenshot:** `screenshots/TEST-002-layout.png`

**Comparison with User Screenshot:**
- ✅ No "Voice" tab in tab bar
- ✅ Voice section always visible at top
- ✅ Terminal list shows 4 terminals (Review, Deploy, Test, Cleanup)
- ✅ Terminal icons show busy/idle state
- ✅ Toolbar above textarea (not below)
- ✅ 2 tabs only (Default, Settings)

---

## Responsive Behavior

**Test: Narrow sidebar (200px width)**
- Result: ✅ PASS (tab buttons show icons only)
- Screenshot: `screenshots/TEST-002-narrow.png`

**Test: Wide sidebar (600px width)**
- Result: ✅ PASS (tab buttons show icons + text)
- Screenshot: `screenshots/TEST-002-wide.png`

---

## Conclusion

**Status:** ✅ PASS
**Confidence:** High
**Layout matches user vision:** 100%
**Deviations:** None

---
```

---

## Implementation Specification

### Step 1: Create Testing Directory Structure

```bash
mkdir -p screenshots
touch TESTING_LOG.md
touch TESTING_CHECKLIST.md
```

### Step 2: Initialize TESTING_LOG.md

```markdown
# ÆtherLight Testing Log

**Project:** ÆtherLight VS Code Extension
**Pattern:** Pattern-TESTING-001 (Manual Testing Methodology)

---

## Test Sessions

- [2025-11-01: v0.15.4 Critical Bugs](#session-2025-11-01)
- [2025-11-05: v0.15.5 UI Layout](#session-2025-11-05)

---

<a name="session-2025-11-01"></a>
## Session: 2025-11-01 - v0.15.4 Critical Bugs

**Sprint:** ACTIVE_SPRINT_v0.15.4_UI_REFACTOR
**Tests:** BUG-008, BUG-009, BUG-010, BUG-011
**Status:** ✅ All Pass

---

[Individual test cases follow...]
```

### Step 3: Create Screenshot Tool (Optional)

```typescript
// vscode-lumina/src/utils/screenshotHelper.ts
import * as vscode from 'vscode';
import * as path from 'path';

/**
 * Helper to capture screenshots during testing
 *
 * USAGE:
 * 1. Press hotkey (Ctrl+Shift+S)
 * 2. Prompt for filename
 * 3. Save to screenshots/ directory
 */
export function registerScreenshotCommand(context: vscode.ExtensionContext): void {
    const disposable = vscode.commands.registerCommand('aetherlight.captureScreenshot', async () => {
        const filename = await vscode.window.showInputBox({
            prompt: 'Enter screenshot filename (e.g., BUG-008-after)',
            placeHolder: 'BUG-XXX-description'
        });

        if (!filename) return;

        const fullPath = path.join(
            vscode.workspace.workspaceFolders?.[0].uri.fsPath || '',
            'screenshots',
            `${filename}.png`
        );

        vscode.window.showInformationMessage(
            `Screenshot saved: ${fullPath}`
        );

        // Note: VS Code extensions cannot capture screenshots programmatically
        // User must use OS screenshot tool (Windows: Win+Shift+S, Mac: Cmd+Shift+4)
        // This command just prompts for filename and shows path
    });

    context.subscriptions.push(disposable);
}
```

---

## Benefits

### 1. Systematic Testing
- Repeatable test steps (not ad-hoc)
- Documented test cases (future reference)
- Checklist ensures nothing missed

### 2. Proof of Testing
- Screenshots = visual evidence
- TESTING_LOG.md = written record
- Commit history = timestamp proof

### 3. Regression Prevention
- Test previous features after changes
- Document what should still work
- Catch regressions before release

### 4. Knowledge Transfer
- New testers can follow documented steps
- Test cases = implicit documentation
- Screenshots show expected behavior

### 5. Release Confidence
- TESTING_CHECKLIST.md = release gate
- All boxes checked = ready to ship
- Evidence for stakeholders

---

## Alternatives Considered

### Alternative 1: Automated Unit Tests
**Rejected because:**
- VS Code extension testing requires Extension Development Host
- Complex setup (launch.json, test runner, etc.)
- Slow feedback loop (compile → launch → test)
- Manual testing faster for current needs

### Alternative 2: No Testing Pattern
**Rejected because:**
- Caused v0.15.3 audit failure (15/80 score)
- Regressions slip through
- No proof of testing
- No repeatable process

### Alternative 3: User Acceptance Testing Only
**Rejected because:**
- Users find bugs in production (too late)
- No pre-release validation
- Damages reputation

---

## Edge Cases

### Case 1: Test Fails
**Problem:** Bug fix doesn't work as expected

**Solution:** Document failure, iterate on fix
```markdown
**Status:** ❌ FAIL
**Reason:** Record button still doesn't trigger recording
**Next Steps:**
1. Debug voicePanel.ts:1061-1070
2. Check message handler for 'startRecording'
3. Re-test after fix
```

### Case 2: Cannot Reproduce Bug
**Problem:** Bug described in audit cannot be reproduced

**Solution:** Document inability to reproduce, seek clarification
```markdown
**Status:** ⚠️ CANNOT REPRODUCE
**Reason:** Bug may have been fixed in previous version
**Next Steps:**
1. Check git history for related commits
2. Ask user for more reproduction steps
3. Close issue if confirmed fixed
```

### Case 3: Performance Regression
**Problem:** New fix is slower than old code

**Solution:** Document performance, optimize if needed
```markdown
**Performance:** 250ms (target: < 100ms) ❌
**Reason:** Added synchronous file read in hot path
**Next Steps:**
1. Refactor to async file read
2. Cache results
3. Re-test performance
```

---

## Related Patterns

- **Pattern-UI-006:** Tabbed Multi-Feature Sidebar (UI test subject)
- **Pattern-TERMINAL-001:** Terminal Management (terminal test subject)
- **Pattern-VOICE-001:** Voice Capture (voice test subject)
- **Pattern-DOCUMENTATION-001:** Documentation Standards (test documentation format)

---

## Validation Criteria

**How to know this pattern is working:**

✅ **Test documentation:** All tests documented in TESTING_LOG.md
✅ **Screenshots:** Before/after screenshots for all bug fixes
✅ **Checklist:** TESTING_CHECKLIST.md completed for each release
✅ **No regressions:** Previous features still work after changes
✅ **Release confidence:** All tests pass before publishing
✅ **Audit improvement:** v0.15.4 audit score > v0.15.3 (15/80)

---

## Conclusion

**Pattern-TESTING-001 establishes systematic manual testing:**
- Repeatable test cases (documented)
- Visual proof (screenshots)
- Release gate (checklist)
- Regression prevention (test old features)
- Fast feedback (no test infrastructure needed)

**This pattern prevents the v0.15.3 audit failure from recurring.**

---

**PATTERN STATUS:** ✅ Active - Required for v0.15.4+
**IMPLEMENTATION:** `TESTING_LOG.md`, `TESTING_CHECKLIST.md`, `screenshots/`
**REFERENCED BY:** 6 sprint tasks (TEST-001/002/003, TEST-UI, E-006)
**LAST UPDATED:** 2025-11-01

---

*"Test systematically. Document thoroughly. Ship confidently."*
