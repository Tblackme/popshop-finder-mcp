# Feature Request Template Skill

**Version:** 1.0.0
**Purpose:** Generate structured feature request templates for ÆtherLight Prompt Terminal workflow
**Type:** Template Generator

---

## What This Skill Does

Generates comprehensive feature request templates with:
- User-provided feature details (title, priority, user story, acceptance criteria)
- 4-phase implementation plan (Analysis → Development → Testing → Documentation)
- Architecture review checklist
- Pattern references (TDD, CODE, TASK-ANALYSIS)
- Enhancement instructions for Claude Code

**Output:** Markdown template ready for text area → Prompt Terminal → Claude Code enhancement

---

## When to Use This Skill

**Invocation Methods:**

1. **Via Enhancement Button** (Primary)
   - User clicks "Feature Request" toolbar button
   - Modal opens with form fields
   - User fills form, clicks "✨ Enhance"
   - voicePanel.ts invokes this skill with form data

2. **Direct Command** (User-invoked)
   - User types: `/feature-request-template --title="Add dark mode" --priority=High`
   - Skill generates template immediately

---

## Template Generation Logic

### Input Parameters

**Required:**
- `title` (string): Feature title/summary

**Optional:**
- `priority` (string): Critical|High|Medium|Low (default: Medium)
- `category` (string): Feature category
- `userStory` (string): User story or use case
- `description` (string): Detailed feature description
- `acceptanceCriteria` (string): Acceptance criteria
- `technicalNotes` (string): Technical implementation notes

### Output Structure

```markdown
# Feature Request: [title]

**Priority**: [priority]
**Category**: [category or "Not specified"]
**Requested**: [ISO timestamp]

## User Story
[userStory or "Not provided"]

## Description
[description or "No description provided"]

## Acceptance Criteria
[acceptanceCriteria or "Not provided"]

## Technical Notes
[technicalNotes or "No technical notes"]

---

## Implementation Plan

### Phase 1: Analysis & Design
1. [ ] Review similar features in codebase
2. [ ] Identify affected components/files
3. [ ] Check for architectural impacts
4. [ ] Design API/interface contracts
5. [ ] Identify potential breaking changes

### Phase 2: Development
1. [ ] Write failing tests (TDD)
2. [ ] Implement core functionality
3. [ ] Add error handling
4. [ ] Update documentation
5. [ ] Add integration tests

### Phase 3: Testing & Validation
1. [ ] Unit test coverage (≥85%)
2. [ ] Integration tests pass
3. [ ] Manual testing (happy path + edge cases)
4. [ ] Performance testing (if applicable)
5. [ ] Accessibility check (if UI changes)

### Phase 4: Documentation
1. [ ] Update CHANGELOG.md
2. [ ] Update API documentation
3. [ ] Add code comments (Chain of Thought)
4. [ ] Create user-facing docs (if needed)

## Patterns to Apply
- **Pattern-TDD-001**: Test-driven development
- **Pattern-CODE-001**: Code development workflow
- **Pattern-TASK-ANALYSIS-001**: Pre-task analysis
- **Pattern-GIT-001**: Git workflow integration

## Questions to Consider
- How does this integrate with existing features?
- What are the performance implications?
- Are there backwards compatibility concerns?
- What happens if this fails gracefully?

---

💡 **TO ENHANCE THIS PROMPT**:
1. Review the template above (in text area)
2. Press Ctrl+Enter to send to Claude Code
3. Ask Claude: "Please enhance this feature request with architecture details, specific implementation steps, and save to `.aetherlight/prompts/feature-request_enhanced_[timestamp].md`"
4. ÆtherLight will auto-load the enhanced prompt when created

🤖 Generated with ÆtherLight Feature Request Template
```

---

## Enforcement & Consistency

### Standardized Sections (ALWAYS INCLUDED):

✅ 4-Phase Implementation Plan (20 steps)
✅ Pattern References (TDD-001, CODE-001, TASK-ANALYSIS-001, GIT-001)
✅ Questions to Consider (4 key questions)
✅ Enhancement Instructions (how to use with Claude Code)

### Variable Sections (User-provided):

- Feature details (title, priority, category)
- User story
- Description
- Acceptance criteria
- Technical notes

---

## Success Criteria

Skill succeeds when:

✅ Template generated with all required sections
✅ User-provided data properly substituted
✅ Fallbacks applied for missing optional fields
✅ Template loads into text area
✅ Prompt Terminal opens with instructions
✅ Template is actionable (user can send to Claude Code immediately)
