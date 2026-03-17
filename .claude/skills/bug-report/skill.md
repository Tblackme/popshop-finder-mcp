# Bug Report Skill

**Version:** 1.0.0
**Purpose:** Create properly formatted GitHub bug report issues following ÆtherLight SOP

## SOP: Bug Report Creation

### Step 1: Gather Information

Ask the user clarifying questions if description is insufficient:
- What were you trying to do?
- What actually happened?
- What did you expect to happen?
- Can you reproduce it consistently?
- What version of ÆtherLight are you using?
- What OS and VS Code version?

### Step 2: Check for Duplicates

Search existing issues to avoid duplicates:
```bash
gh issue list --repo AEtherlight-ai/lumina --label bug --search "<keywords from description>"
```

If duplicate found:
- Inform user: "This bug may already be reported in issue #X"
- Ask if they want to add a comment instead

### Step 3: Determine Severity

Based on description, classify severity:
- **Critical:** Extension crashes, data loss, security vulnerability
- **High:** Major feature broken, affects most users
- **Medium:** Feature partially broken, workaround exists
- **Low:** Minor issue, cosmetic, edge case

### Step 4: Create Issue

Use `gh` CLI to create properly formatted issue:

```bash
gh issue create \
  --repo AEtherlight-ai/lumina \
  --title "Bug: <concise title>" \
  --label bug,<severity> \
  --body "$(cat <<'EOF'
## Bug Description
<User's description>

## Steps to Reproduce
1. Step one
2. Step two
3. ...

## Expected Behavior
<What should happen>

## Actual Behavior
<What actually happens>

## Environment
- ÆtherLight Version: <version>
- VS Code Version: <version>
- OS: <OS and version>
- Node Version: <version if relevant>

## Additional Context
<Screenshots, logs, error messages>

---
🐛 Reported via ÆtherLight Bug Report Skill
EOF
)"
```

### Step 5: Confirm and Return URL

After issue creation:
1. Capture issue URL from `gh` output
2. Inform user: "✅ Bug report created: <URL>"
3. Suggest: "You can track this issue at the URL above"

## Parameters

- `--description`: Brief bug description (required)
- `--severity`: critical|high|medium|low (optional, default: medium)
- `--component`: Affected component (optional)

## Example Usage

```bash
/bug-report --description="Voice recording fails after VS Code reload" --severity=high --component="voice-capture"
```

## Error Handling

If `gh` CLI not installed:
- Error: "GitHub CLI (gh) not found. Please install: https://cli.github.com"
- Stop execution

If not authenticated:
- Error: "Not authenticated with GitHub. Run: gh auth login"
- Stop execution

If issue creation fails:
- Show error message from `gh` CLI
- Suggest manual reporting via web interface

## Success Criteria

✅ Issue created with proper formatting
✅ Correct labels applied (bug + severity)
✅ URL returned to user
✅ No duplicates created (checked first)
✅ All required information collected

## Notes

- Always be polite when asking clarifying questions
- If user provides minimal info, gather more before creating issue
- Check duplicates to keep issue tracker clean
- Use consistent title format: "Bug: <concise description>"
