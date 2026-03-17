# Code Analyzer Template Skill

**Version:** 1.0.0
**Purpose:** Generate structured code analysis templates for ÆtherLight Prompt Terminal workflow
**Type:** Template Generator

---

## What This Skill Does

Generates comprehensive code analysis templates with:
- User-provided analysis scope (languages, frameworks, focus areas)
- Architecture review checklist
- Code quality checklist
- Best practices checklist
- Git history analysis steps
- Pattern references
- Enhancement instructions for Claude Code

**Output:** Markdown template ready for text area → Prompt Terminal → Claude Code enhancement

---

## When to Use This Skill

**Invocation Methods:**

1. **Via Enhancement Button** (Primary)
   - User clicks "Code Analyzer" toolbar button
   - Modal opens with form fields
   - User fills form, clicks "✨ Enhance"
   - voicePanel.ts invokes this skill with form data

2. **Direct Command** (User-invoked)
   - User types: `/code-analyzer-template --focusArea="Security audit" --complexity=Complex`
   - Skill generates template immediately

---

## Template Generation Logic

### Input Parameters

**Required:** None (all optional with defaults)

**Optional:**
- `languages` (array): Programming languages (default: ["TypeScript", "JavaScript"])
- `frameworks` (array): Frameworks used
- `focus` (string): What to analyze (architecture, performance, security, testing, documentation, refactoring, general)
- `complexity` (string): Simple|Moderate|Complex|Very Complex (default: Moderate)
- `concerns` (string): Specific concerns or areas to focus on

### Output Structure

```markdown
# Code Analysis Request

**Languages**: [languages joined]
**Frameworks**: [frameworks joined or "Not specified"]
**Complexity**: [complexity]
**Requested**: [ISO timestamp]

## Focus Area
[focus or "General code analysis"]

## Specific Concerns
[concerns or "No specific concerns provided"]

---

## Analysis Checklist

### Architecture Review
1. [ ] Identify main components and their responsibilities
2. [ ] Map dependencies between modules
3. [ ] Check for circular dependencies
4. [ ] Review architectural patterns used
5. [ ] Identify potential architectural improvements

### Code Quality
1. [ ] Check for code smells (long functions, duplicated code)
2. [ ] Review error handling patterns
3. [ ] Assess test coverage
4. [ ] Check for security vulnerabilities (OWASP Top 10)
5. [ ] Review performance bottlenecks

### Best Practices
1. [ ] Naming conventions consistency
2. [ ] Documentation completeness
3. [ ] Type safety (if TypeScript/Rust)
4. [ ] Dead code detection
5. [ ] Technical debt identification

### Git History Analysis
1. [ ] Check recent changes (`git log --since="2 weeks ago"`)
2. [ ] Identify frequently changed files (hotspots)
3. [ ] Review commit message quality
4. [ ] Check for large commits (potential refactoring candidates)

### ÆtherLight-Specific Context (if available)
1. [ ] Check for relevant patterns in `docs/patterns/` (if missing: note that patterns could improve code quality)
2. [ ] Review agent context files in `internal/agents/` (if missing: skip this step)
3. [ ] Check sprint files in `internal/sprints/` for related tasks (if missing: skip this step)
4. [ ] Verify `.claude/` configuration (skills, commands, settings) (if missing: suggest creating it)
5. [ ] Check CLAUDE.md for project-specific rules (if missing: ask user if they want one created)

## Patterns to Apply
- **Pattern-CODE-001**: Code development workflow
- **Pattern-TASK-ANALYSIS-001**: Pre-task analysis
- **Pattern-GIT-001**: Git history integration

## Output Format
- Summary of findings (2-3 paragraphs)
- Top 5 issues/improvements (prioritized)
- Code examples (before/after)
- Action items with estimated effort

---

💡 **TO ENHANCE THIS PROMPT**:
1. Review the template above (in text area)
2. Press Ctrl+Enter to send to Claude Code
3. Ask Claude: "Please enhance this code analysis with specific findings, code examples, and save to `.aetherlight/prompts/code-analyzer_enhanced_[timestamp].md`"
4. ÆtherLight will auto-load the enhanced prompt when created

📋 **INSTRUCTIONS FOR CLAUDE CODE**:
When directories are missing, take these actions:
- **Missing `docs/patterns/`**: Recommend creating it if code quality issues are found
- **Missing `internal/agents/`**: Skip agent analysis (project may not use agent system)
- **Missing `internal/sprints/`**: Skip sprint analysis (project may not use sprint system)
- **Missing `.claude/`**: Use `AskUserQuestion` tool to ask if they want to initialize ÆtherLight structure
- **Missing `CLAUDE.md`**: Use `AskUserQuestion` tool to ask if they want a project instructions file created
- If user says yes to any missing files, CREATE TEMPLATES based on project needs using Write tool

🤖 Generated with ÆtherLight Code Analyzer Template
```

---

## Enforcement & Consistency

### Standardized Sections (ALWAYS INCLUDED):

✅ Architecture Review (5 steps)
✅ Code Quality (5 steps)
✅ Best Practices (5 steps)
✅ Git History Analysis (4 steps)
✅ ÆtherLight-Specific Context (5 steps)
✅ Pattern References
✅ Output Format Guidelines
✅ Enhancement Instructions

---

## Success Criteria

✅ Template generated with all required sections
✅ User-provided data properly substituted
✅ Fallbacks applied for missing optional fields
✅ Template loads into text area
✅ Prompt Terminal opens with instructions
✅ Template is actionable
