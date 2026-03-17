# Feature Request Skill

**Version:** 1.0.0
**Purpose:** Create properly formatted GitHub feature request issues following ÆtherLight SOP

## SOP: Feature Request Creation

### Step 1: Understand the Request

Ask clarifying questions to understand the feature:
- What problem does this feature solve?
- Who would benefit from this feature?
- What is the expected behavior?
- Are there any examples of similar features elsewhere?
- How urgent is this request?

### Step 2: Check for Existing Requests

Search for duplicate or related feature requests:
```bash
gh issue list --repo AEtherlight-ai/lumina --label enhancement --search "<keywords from description>"
```

If similar request found:
- Inform user: "A similar feature was requested in issue #X"
- Ask: "Would you like to add your use case there instead?"

### Step 3: Categorize Feature

Identify the feature category:
- **Voice:** Voice capture, transcription, audio features
- **Sprint:** Sprint planning, tracking, management
- **Patterns:** Pattern matching, context detection
- **UI:** User interface, UX improvements
- **Skills:** Skill system, metadata, management
- **Performance:** Speed, optimization, efficiency
- **Other:** Doesn't fit above categories

### Step 4: Assess Priority

Based on user needs and impact:
- **Critical:** Blocking workflows, must-have for core functionality
- **High:** Significantly improves user experience
- **Medium:** Nice to have, quality of life improvement
- **Low:** Minor enhancement, edge case

### Step 5: Create Issue

Use `gh` CLI to create properly formatted feature request:

```bash
gh issue create \
  --repo AEtherlight-ai/lumina \
  --title "Feature: <concise title>" \
  --label enhancement,<priority>,<category> \
  --body "$(cat <<'EOF'
## Feature Request

### Problem Statement
<What problem does this solve?>

### Proposed Solution
<Describe the desired feature>

### Use Case
<How would you use this feature?>

### Expected Behavior
<What should happen when using this feature?>

### Alternatives Considered
<What other solutions did you think about?>

### Additional Context
<Mockups, examples, links to similar features>

### Priority Justification
<Why is this priority level appropriate?>

---
✨ Requested via ÆtherLight Feature Request Skill
EOF
)"
```

### Step 6: Confirm and Return URL

After issue creation:
1. Capture issue URL from `gh` output
2. Inform user: "✅ Feature request created: <URL>"
3. Encourage: "The team will review this and may reach out for clarification"

## Parameters

- `--description`: Brief feature description (required)
- `--priority`: critical|high|medium|low (optional, default: medium)
- `--category`: voice|sprint|patterns|ui|skills|performance|other (optional)

## Example Usage

```bash
/feature-request --description="Add keyboard shortcuts for sprint navigation" --priority=medium --category=ui
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
- Suggest manual request via web interface

## Success Criteria

✅ Issue created with proper formatting
✅ Correct labels applied (enhancement + priority + category)
✅ URL returned to user
✅ No duplicates created (checked first)
✅ All context gathered (problem, solution, use case)

## Best Practices

### Asking Questions

Be conversational and helpful:
- "What problem are you trying to solve?"
- "Can you describe how you'd use this feature?"
- "Have you seen this implemented elsewhere?"

### Avoiding Duplicates

Always search before creating:
- Use relevant keywords from description
- Check both open and closed issues
- Suggest adding to existing issue if similar

### Setting Expectations

After creating:
- "The team will review this request"
- "You can track progress at the URL above"
- "Feel free to add more details if you think of them"

## Notes

- Features should solve real problems, not just "nice to have"
- Gather enough context to understand the use case
- Categorization helps team prioritize and assign
- Use consistent title format: "Feature: <concise description>"
- Encourage users to include mockups or examples if relevant
