# Bug Report Template Skill

**Version:** 1.0.0
**Purpose:** Generate structured bug report templates for ÆtherLight Prompt Terminal workflow
**Type:** Template Generator

---

## What This Skill Does

Generates comprehensive bug report templates with:
- User-provided bug details (title, severity, description, steps)
- Investigation workflow checklist
- Testing checklist
- Pattern references (TDD, bug fix, git integration)
- Enhancement instructions for Claude Code

**Output:** Markdown template ready for text area → Prompt Terminal → Claude Code enhancement

---

## When to Use This Skill

**Invocation Methods:**

1. **Via Enhancement Button** (Primary)
   - User clicks "Bug Report" toolbar button
   - Modal opens with form fields
   - User fills form, clicks "✨ Enhance"
   - voicePanel.ts invokes this skill with form data

2. **Direct Command** (User-invoked)
   - User types: `/bug-report-template --title="Login fails" --severity=High`
   - Skill generates template immediately
   - Template loads into text area

---

## Template Generation Logic

### Input Parameters

**Required:**
- `title` (string): Bug title/summary

**Optional:**
- `severity` (string): Critical|High|Medium|Low (default: Medium)
- `component` (string): Affected component/module
- `description` (string): Detailed bug description
- `stepsToReproduce` (string): Steps to reproduce
- `expectedBehavior` (string): What should happen
- `actualBehavior` (string): What actually happens
- `context` (string): Additional context, logs, screenshots

### Output Structure

```markdown
# Bug Report: [title]

**Severity**: [severity]
**Component**: [component or "Not specified"]
**Reported**: [ISO timestamp]

## Description
[description or "No description provided"]

## Steps to Reproduce
[stepsToReproduce or "Not provided"]

## Expected Behavior
[expectedBehavior or "Not provided"]

## Actual Behavior
[actualBehavior or "Not provided"]

## Additional Context
[context or "No additional context"]

---

## Investigation Steps

1. [ ] Read the error message and stack trace
2. [ ] Check recent changes (`git log` for related commits)
3. [ ] Add logging to narrow down the issue
4. [ ] Identify root cause
5. [ ] Write a failing test that reproduces the bug
6. [ ] Fix the bug
7. [ ] Verify the test passes
8. [ ] Check for similar bugs elsewhere in codebase

## Testing Checklist

- [ ] Unit tests added for the fix
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Edge cases considered
- [ ] Regression testing done

## Patterns to Apply

- **Pattern-TDD-001**: Write test first to reproduce bug
- **Pattern-BUG-FIX-001**: Root cause analysis workflow
- **Pattern-GIT-001**: Check git history for context

---

💡 **TO ENHANCE THIS PROMPT**:
1. Review the template above (in text area)
2. Press Ctrl+Enter to send to Claude Code
3. Ask Claude: "Please enhance this bug report with more details, specific investigation steps, and save to `.aetherlight/prompts/bug-report_enhanced_[timestamp].md`"
4. ÆtherLight will auto-load the enhanced prompt when created

🤖 Generated with ÆtherLight Bug Report Template
```

---

## Implementation Details

### When Invoked from voicePanel.ts:

```typescript
// voicePanel.ts enhancement handler
case 'enhanceBugReport':
    const template = await generateBugReportTemplate({
        title: message.data.title,
        severity: message.data.severity,
        component: message.data.component,
        description: message.data.description,
        stepsToReproduce: message.data.stepsToReproduce,
        expectedBehavior: message.data.expectedBehavior,
        actualBehavior: message.data.actualBehavior,
        context: message.data.context
    });

    // Populate text area
    webview.postMessage({ type: 'populateTextArea', text: template });

    // Show Prompt Terminal
    PromptTerminalManager.showPromptTerminal();
    PromptTerminalManager.sendWelcomeMessage('bug-report');
    break;
```

### When Invoked Directly by User:

```bash
/bug-report-template --title="Authentication fails on login" --severity=High --component="Auth Module"
```

**Result:**
- Template generates immediately
- Loads into text area
- Prompt Terminal opens with instructions
- User can review and enhance with Claude Code

---

## Skill Output Format

Returns object:
```json
{
  "template": "# Bug Report: ...\n\n[full template]",
  "filename": "bug-report_enhanced_1705528800000.md",
  "metadata": {
    "type": "bug-report",
    "severity": "High",
    "timestamp": "2025-01-17T20:00:00.000Z"
  }
}
```

---

## Enforcement & Consistency

### Standardized Sections (ALWAYS INCLUDED):

✅ Investigation Steps (8-step checklist)
✅ Testing Checklist (5 items)
✅ Pattern References (TDD-001, BUG-FIX-001, GIT-001)
✅ Enhancement Instructions (how to use with Claude Code)

### Variable Sections (User-provided):

- Bug details (title, severity, component)
- Description
- Steps to Reproduce
- Expected/Actual Behavior
- Additional Context

### Fallbacks:

If user doesn't provide optional fields:
- `description` → "No description provided"
- `stepsToReproduce` → "Not provided"
- `component` → "Not specified"

**This ensures template is ALWAYS complete and actionable.**

---

## Pattern Integration

This skill enforces:

1. **Pattern-TDD-001**: "Write a failing test that reproduces the bug" (Investigation Step 5)
2. **Pattern-BUG-FIX-001**: Root cause analysis before fixing (Investigation Steps 1-4)
3. **Pattern-GIT-001**: Check git history for context (Investigation Step 2)
4. **Pattern-CODE-001**: Comprehensive workflow integration (referenced in Testing Checklist)

---

## Success Criteria

Skill succeeds when:

✅ Template generated with all required sections
✅ User-provided data properly substituted
✅ Fallbacks applied for missing optional fields
✅ Template loads into text area
✅ Prompt Terminal opens with instructions
✅ Template is actionable (user can send to Claude Code immediately)

---

## Example Usage

### Via Enhancement Button:

```
1. User clicks "🐛 Bug Report" toolbar button
2. Modal opens with form
3. User fills:
   - Title: "Login fails with valid credentials"
   - Severity: High
   - Component: Auth Module
   - Description: "User unable to log in..."
   - Steps: "1. Navigate to /login 2. Enter valid..."
4. User clicks "✨ Enhance"
5. This skill generates template
6. Template loads in text area
7. Prompt Terminal opens
8. User reviews, presses Ctrl+Enter
9. User asks Claude Code to enhance and save
10. Extension auto-loads enhanced .md file
```

### Direct Command:

```bash
/bug-report-template --title="Voice recording fails after reload" --severity=Critical --component="Voice Capture"
```

**Result:** Template immediately generated and loaded (same workflow as button, but faster)

---

## Future Enhancements

**Phase 2: Auto-enhancement** (Optional)
- Automatically send template to Claude Code API (if available)
- Pre-fill save path for enhanced .md file
- Skip manual "ask Claude to enhance" step

**Phase 3: Custom Templates** (Optional)
- Allow users to save custom bug report templates
- Template library in `.aetherlight/templates/bug-report/`
- Dropdown to select template variant before generation

---

**Note:** This skill is the first of 5 template generation skills:
- bug-report-template ← THIS SKILL
- feature-request-template
- code-analyzer-template
- sprint-planner-template
- start-task-template
