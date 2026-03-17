# Pattern-VALIDATION-001: Pre-Flight Checklist Enforcement

**CREATED:** 2025-01-12
**CATEGORY:** Quality Assurance / Error Prevention
**LANGUAGE:** Universal (applies to all languages)
**QUALITY SCORE:** 0.95 (prevents 15+ hours of historical bugs)
**APPLICABILITY:** Universal - EVERY Edit/Write operation
**STATUS:** Active - MANDATORY enforcement
**RELATED:** Pattern-TRACKING-001, Pattern-GIT-001, Pattern-PUBLISH-003

---

## Problem Statement

**The Problem:**
- Historical bugs cost 15+ hours of debugging due to skipped validation
- AI agents sometimes edit files without reading them first
- Sprint TOML format violations break SprintLoader parser
- Forbidden dependencies (native/runtime npm) break extension activation
- Private code accidentally committed to public repos
- Version mismatches between packages cause installation failures

**Why This Matters:**
- **Time Cost**: 15+ hours wasted on preventable bugs
- **User Impact**: Broken releases, failed installations, data exposure
- **System Stability**: Parser failures, activation failures, compilation errors
- **Security**: Private code exposure, API key leaks

**Historical Incidents:**
- **v0.13.23** (9 hours): Native dependency added → Extension broken
- **v0.15.31-32** (2 hours): Runtime npm dependency → Activation failed
- **v0.16.15** (2 hours): Manual publish bypass → Version mismatch
- **2025-11-03** (2 hours): Wrong TOML format → Sprint panel broken
- **2025-11-09** (2 hours): Private website code → Public repo exposure

**Total Historical Cost**: 15+ hours of emergency debugging

---

## Solution Pattern

**The Pattern:**
Enforce a **mandatory pre-flight checklist** BEFORE every Edit/Write operation. The checklist has 4 categories:

### Category 1: Sprint TOML Modifications

**STOP. Answer these questions OUT LOUD:**

1. ✅ **Did I read `SprintLoader.ts:292-333` to verify the parser format?**
   - If NO → Read it NOW before proceeding
   - Expected format: `[tasks.TASK-ID]` NOT `[[epic.*.tasks]]`
   - Historical bug: 2025-11-03 (2 hours debugging)

2. ✅ **Did I check an existing task in ACTIVE_SPRINT.toml for format example?**
   - If NO → Read one task NOW (lines 72-150)
   - Copy the exact structure, don't invent
   - Never guess the format

3. ✅ **Did I validate required fields are present?**
   - Required: id, name, status, phase, agent, estimated_time, dependencies
   - If missing any → Add them before proceeding
   - SprintLoader will fail on missing fields

4. ✅ **Did I check for template literals in code examples?**
   - Search for: backticks with ${}
   - If found → Replace with string concatenation (+ operator)
   - Example: `` `Error: ${msg}` `` → `'Error: ' + msg`
   - TOML parser fails on template literals

5. ✅ **Did I validate the TOML will parse?**
   - If NO → Run: `node scripts/validate-sprint-schema.js` BEFORE committing
   - Fallback: `node -e "const toml = require('@iarna/toml'); toml.parse(require('fs').readFileSync('internal/sprints/ACTIVE_SPRINT.toml', 'utf-8'));"`

---

### Category 2: Directory Additions

**STOP. Answer these questions OUT LOUD:**

1. ✅ **Is this private/proprietary code?**
   - Check for: API keys, commercial logic, customer data, Stripe integration
   - If YES → MUST use git submodule (Pattern-GIT-002)
   - NEVER commit private code directly to public repo
   - Historical incident: 2025-11-09 (2 hours emergency cleanup)

2. ✅ **Does this directory belong in the public repo?**
   - Public repo: VS Code extension, desktop app, public docs
   - Private repo: Website, API keys, Stripe webhooks, database migrations
   - If unsure → Ask user before committing

3. ✅ **Is there a .gitignore entry to prevent accidents?**
   - Verify: `git check-ignore <directory>`
   - If directory should be submodule → Do NOT add to .gitignore
   - If directory is private → Add to .gitignore AND use submodule

4. ✅ **Did I check Pattern-GIT-002 for submodule setup?**
   - See: `docs/patterns/Pattern-GIT-002.md`
   - Submodule setup: `git submodule add <url> <path>`
   - Never commit private repo code directly

---

### Category 3: Dependency Additions (package.json)

**STOP. Answer these questions OUT LOUD:**

1. ✅ **Is this a native dependency?**
   - Check for: node-gyp, napi, bindings, .node, robotjs, @nut-tree-fork
   - If YES → **FORBIDDEN** - Use VS Code APIs instead
   - See: Pattern-PUBLISH-003 in docs/patterns/
   - Historical bug: v0.13.23 (9 hours debugging)

2. ✅ **Is this a runtime npm dependency?**
   - Check for: glob, lodash, moment, axios, chalk, colors
   - If YES → **FORBIDDEN** - Use Node.js built-ins instead
   - Exception: Whitelisted (@iarna/toml, form-data, node-fetch, ws)
   - Historical bug: v0.15.31-32 (2 hours debugging)

3. ✅ **Did I check the whitelist?**
   - Allowed: aetherlight-analyzer, aetherlight-sdk, aetherlight-node
   - Allowed: @iarna/toml, form-data, node-fetch, ws
   - Everything else → Use built-ins (fs, path, util, crypto, https)

**If you're adding a forbidden dependency, STOP and find an alternative NOW.**

**Reference**: Pattern-PUBLISH-003 for full dependency policy

---

### Category 4: File Edits (General)

**STOP. Answer these questions OUT LOUD:**

1. ✅ **Did I read the target file first?**
   - If NO → Read it NOW with Read tool
   - Never edit a file you haven't read in this session
   - Prevents breaking existing code structure

2. ✅ **Did I verify the format/structure I'm following?**
   - If NO → Read the parser/loader code that will read this file
   - Never guess the format
   - Copy existing patterns instead of inventing

3. ✅ **Am I following an existing pattern?**
   - If NO → Search for similar code and copy the pattern
   - Never invent new patterns without user approval
   - Consistency is critical

---

## Implementation

### Setup Instructions

**1. Add to CLAUDE.md (Project-Level)**

The checklist is already in `.claude/CLAUDE.md` (lines 7-100). This is the **enforcement point** for all agents.

**2. Reference in Enhanced Prompts**

Every enhanced prompt should include:

```markdown
## Pre-Flight Checklist

**STOP. Complete Pattern-VALIDATION-001 checklist OUT LOUD:**

✅ Did I read target files first? (Never edit without reading)
✅ Did I verify format/structure? (Read parser code if unsure)
✅ Did I check Sprint TOML format? (SprintLoader.ts:292-333)
✅ Did I validate dependencies? (Pattern-PUBLISH-003 whitelist)

**Automated Validation**: Pre-commit hooks will run 8 validators
```

**3. Automated Enforcement (8 Validators)**

Pre-commit hooks run these validators automatically:

| Validator | Purpose | Historical Bug Prevented |
|-----------|---------|--------------------------|
| `validate-sprint-schema.js` | Sprint TOML format | 2025-11-03 (2 hours) |
| `validate-dependencies.js` | Forbidden dependencies | v0.15.31-32 (2 hours) |
| `validate-git-state.js` | Git status clean | Multiple incidents |
| `validate-version-sync.js` | Package version consistency | v0.13.28-29 (2 hours) |
| `validate-typescript.js` | TypeScript compilation | Ongoing prevention |
| `validate-coverage.js` | Test coverage targets | Quality enforcement |
| `validate-protection.js` | Protected code unchanged | Pattern-PROTECT-002 |
| `validate-package-size.js` | Bundle size limits | Performance enforcement |

**4. Agent Integration**

All 13 agent context files should reference this pattern:

```markdown
## Pre-Flight Checklist (Pattern-VALIDATION-001)

**Before EVERY Edit/Write operation:**
- Complete checklist OUT LOUD
- Reference Pattern-VALIDATION-001 for full details
- Pre-commit hooks provide automated enforcement
```

---

## Usage Examples

### Example 1: Editing ACTIVE_SPRINT.toml

**Before Editing:**

```
AI: I'm about to add task BUG-003 to ACTIVE_SPRINT.toml.

Pre-Flight Checklist (Pattern-VALIDATION-001):

1. ✅ Did I read SprintLoader.ts:292-333?
   - YES, I confirmed format is [tasks.TASK-ID]

2. ✅ Did I check existing task for format example?
   - YES, I read lines 72-150 (task BUG-001)

3. ✅ Did I validate required fields?
   - YES, all fields present: id, name, status, phase, agent, estimated_time, dependencies

4. ✅ Did I check for template literals?
   - YES, no template literals in task definition

5. ✅ Did I validate TOML will parse?
   - Will run validate-sprint-schema.js after edit

Proceeding with edit...
```

**Result**: ✅ Task added correctly, parser works, Sprint Panel loads

---

### Example 2: Adding a Dependency (BLOCKED)

**Before Adding:**

```
AI: I'm about to add 'chalk' package for colored console output.

Pre-Flight Checklist (Pattern-VALIDATION-001):

1. ✅ Is this a native dependency?
   - NO (chalk is pure JavaScript)

2. ✅ Is this a runtime npm dependency?
   - YES - chalk is a runtime dependency
   - Checking whitelist...
   - NOT on whitelist (@iarna/toml, form-data, node-fetch, ws)

3. ❌ BLOCKED: Runtime npm dependency not on whitelist

Historical bug reference: v0.15.31-32 (2 hours debugging)

Alternative: Use Node.js built-in console.log() with ANSI codes
- Example: console.log('\x1b[32m%s\x1b[0m', 'Green text')

Stopping - will not add dependency.
```

**Result**: ✅ Bug prevented, used Node.js built-in instead

---

### Example 3: Creating New Directory (PUBLIC/PRIVATE Check)

**Before Creating:**

```
AI: I'm about to create directory 'products/lumina-website/' for Next.js website code.

Pre-Flight Checklist (Pattern-VALIDATION-001):

1. ✅ Is this private/proprietary code?
   - YES - Website contains Stripe integration, API keys, customer data

2. ✅ Does this directory belong in public repo?
   - NO - Website is proprietary, should be private repo

3. ❌ BLOCKED: Private code cannot be committed directly

Historical incident: 2025-11-09 (2 hours emergency cleanup, BFG history purge)

Solution: Use git submodule (Pattern-GIT-002)
- Create private repo: lumina-website-private
- Add as submodule: git submodule add <url> products/lumina-website
- Add to .gitignore as safety: products/lumina-website/

Stopping - will ask user to set up submodule first.
```

**Result**: ✅ Data exposure prevented, proper submodule setup used

---

## Benefits

**1. Prevents Historical Bugs (15+ Hours Saved)**
- Every checklist item maps to a real historical bug
- Automated validators catch issues before commit
- Manual checklist catches issues validators can't detect

**2. Forces Read-Before-Edit**
- Never edit files without reading them first
- Prevents breaking existing code structure
- Ensures format consistency

**3. Enforces Project Standards**
- Dependency whitelist (Pattern-PUBLISH-003)
- Sprint TOML format (SprintLoader compatibility)
- Public/private code separation (Pattern-GIT-002)

**4. Provides Fallback Context**
- AI agents answer checklist OUT LOUD
- User can see what was validated
- Transparent decision-making process

**5. Enables Automation**
- Pre-commit hooks enforce automatically
- 8 validators run on every commit
- Catch issues before they reach main branch

---

## Anti-Patterns (What NOT to Do)

**❌ "Skip checklist for small edits"**
- Result: Small edit breaks parser (2 hours debugging)
- Reality: Small edits cause big bugs
- Solution: ALWAYS complete checklist

**❌ "Answer checklist silently (not OUT LOUD)"**
- Result: User doesn't see validation happened
- User can't verify AI reasoning
- Solution: Answer OUT LOUD in response

**❌ "Trust memory instead of reading files"**
- Result: Edit based on outdated understanding
- File may have changed since last read
- Solution: Read file EVERY time before editing

**❌ "Assume format instead of verifying"**
- Result: Parser failures (2025-11-03 incident)
- Assumptions are always wrong eventually
- Solution: Read parser code to verify format

**❌ "Bypass validators 'just this once'"**
- Result: Historical bugs repeat (v0.16.15 incident)
- Every bypass creates technical debt
- Solution: Fix issue properly, never bypass

---

## Validation

**How to know this pattern is working:**

✅ **All checklist items answered OUT LOUD**
- Check AI responses include "Pre-Flight Checklist (Pattern-VALIDATION-001):"
- Each question answered explicitly
- No edits without checklist completion

✅ **Zero historical bug recurrence**
- No Sprint TOML parser failures (2025-11-03 bug)
- No forbidden dependencies added (v0.13.23, v0.15.31-32 bugs)
- No private code exposure (2025-11-09 incident)
- No version mismatch issues (v0.13.28-29 bug)

✅ **Automated validators passing**
- All 8 pre-commit hooks pass
- No validator bypass attempts
- Clean git history (no emergency reverts)

✅ **AI agents reference pattern consistently**
- All 13 agent context files reference Pattern-VALIDATION-001
- Enhanced prompts include pre-flight checklist section
- TodoWrite includes checklist completion as first task

---

## Metrics

**Track these to measure pattern effectiveness:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Checklist completion rate | 100% | Count responses with "Pre-Flight Checklist" |
| Historical bug recurrence | 0 | Track same bug types (TOML, deps, private code) |
| Validator pass rate | 100% | Count pre-commit hook passes |
| Emergency reverts | 0 per sprint | Count git revert commits |
| Time saved vs historical | 15+ hours/sprint | Compare debugging time before/after pattern |

---

## Integration with Other Patterns

**Pattern-TRACKING-001 (Task Execution Tracking):**
- Pre-flight checklist is first TodoWrite item
- Mark "in_progress" only after checklist complete
- Tracks validation as explicit task step

**Pattern-GIT-001 (Git Workflow Integration):**
- Pre-commit hooks enforce validators automatically
- Git status check part of pre-flight checklist
- Commit only after validation passes

**Pattern-PUBLISH-003 (Dependency Policy):**
- Pre-flight checklist references dependency whitelist
- Enforces no native/runtime npm dependencies
- Prevents extension activation failures

**Pattern-GIT-002 (Git Submodules):**
- Directory creation checklist references this pattern
- Prevents private code exposure
- Enforces proper submodule setup

---

## Continuous Improvement

**As this pattern evolves:**

1. **Add new checklist items as new bug types discovered**
   - Each historical bug → new checklist question
   - Preventative rather than reactive

2. **Automate more validations**
   - Move manual checks to automated validators
   - Reduce human error surface area

3. **Improve error messages**
   - Each validator provides clear fix instructions
   - Reference historical bugs for context

4. **Track pattern effectiveness**
   - Measure time saved vs historical debugging
   - Validate 15+ hours claim with real data

5. **Integrate with AI agent training**
   - Make checklist completion instinctive
   - Reduce cognitive load over time

---

## Enforcement Mechanism

**This pattern is NOT optional. It is MANDATORY.**

**Enforcement Layers:**

1. **CLAUDE.md Pre-Flight Checklist** (lines 7-100)
   - First line of defense
   - AI agents MUST complete before Edit/Write
   - Answer OUT LOUD for user visibility

2. **Enhanced Prompt Templates** (v1.3+)
   - Every prompt includes pre-flight checklist section
   - References Pattern-VALIDATION-001
   - TodoWrite includes checklist as first task

3. **Agent Context Files** (13 agents)
   - All agents reference this pattern
   - Reinforces behavior across all agent types
   - Consistent enforcement

4. **Automated Validators** (8 scripts)
   - Pre-commit hooks run automatically
   - Catch issues before commit
   - Prevent bypassing manual checklist

5. **User Monitoring**
   - User sees "Pre-Flight Checklist" in responses
   - Can verify AI completed validation
   - Can intervene if checklist skipped

**Commitment:**
"I will answer the pre-flight checklist OUT LOUD in my response BEFORE using Edit/Write tools. If I skip this checklist, I WILL break something."

---

## Real-World Application

**This pattern IS being used:**
- CLAUDE.md enforces checklist (lines 7-100)
- 8 automated validators active (pre-commit hooks)
- Pattern extracted from 15+ hours of historical debugging
- Prevents recurrence of known bug types

**Success Metrics (Target):**
- 0 Sprint TOML parser failures per sprint
- 0 forbidden dependency additions per sprint
- 0 private code exposure incidents per sprint
- 0 version mismatch bugs per release
- 15+ hours saved per sprint (vs historical baseline)

---

## Historical Bug References

**Complete list of bugs this pattern prevents:**

1. **v0.13.23** (9 hours)
   - Native dependency added (@nut-tree-fork/nut-js)
   - Extension activation failed
   - Prevention: Category 3, Question 1 (native dependency check)

2. **v0.15.31-32** (2 hours)
   - Runtime npm dependency added (glob)
   - Extension activation failed
   - Prevention: Category 3, Question 2 (runtime dependency check)

3. **v0.16.15** (2 hours)
   - Automated publish script bypassed manually
   - Version mismatch between packages
   - Prevention: Pattern-PUBLISH-002 enforcement

4. **v0.13.28-29** (2 hours)
   - Manual version bump without sync script
   - User installs broken
   - Prevention: validate-version-sync.js automated validator

5. **2025-11-03** (2 hours)
   - Sprint TOML format violation ([[epic.*.tasks]])
   - SprintLoader parser failed, Sprint Panel broken
   - Prevention: Category 1, Question 1 (read SprintLoader.ts)

6. **2025-11-09** (2 hours)
   - Private website code committed to public repo
   - 4 commits, 58 files exposed, required BFG history purge
   - Prevention: Category 2, Question 1 (private code check)

**Total Time Wasted (Historical)**: 15+ hours
**Total Time Saved (Per Sprint)**: 15+ hours
**ROI**: Infinite (pattern takes 2 minutes, prevents 15+ hours)

---

**PATTERN STATUS:** ✅ Active - MANDATORY enforcement for ALL edits
**LAST UPDATED:** 2025-01-12
**NEXT REVIEW:** After Sprint v0.17.2 (validate effectiveness)

---

*"If you skip this checklist, you WILL break something. User WILL be frustrated. Time WILL be wasted."*

*"Answer the checklist OUT LOUD. Every time. No exceptions."*
