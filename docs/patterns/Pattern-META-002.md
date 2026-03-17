# Pattern-META-002: Commit-Level Documentation Impact Analysis

**CREATED:** 2025-11-02
**CATEGORY:** Meta-Learning / Process Enforcement
**LANGUAGE:** JavaScript
**QUALITY SCORE:** 0.83
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-META-001

---




## Problem Statement

**The Problem:**
- Commits often update code but miss related documentation
- Code changes in one area duplicate functionality elsewhere
- Documentation references become outdated after commits
- Pricing, timelines, metrics get out of sync across multiple files
- Each commit risks introducing drift between code and docs

**Real Example (Your Recent Experience):**
You made a commit updating Business Model V2 across 16 files in systematic audit. Then discovered 5 MORE files (README, pattern index) were outdated with old pricing, old timeline, old pattern counts. Had to do a follow-up commit to fix drift.

**Why This Matters:**
- **Documentation drift compounds:** Each commit adds small drift, becomes big drift over time
- **Code duplication wastes time:** Reimplementing what exists elsewhere
- **AI hallucinations increase:** Outdated docs = bad training data = wrong recommendations
- **Maintenance burden grows:** More versions of "truth" = more places to update

---

## Solution Pattern

**The Pattern:**
BEFORE every commit, run a systematic analysis:

```
┌──────────────────────────────────────────────────────────────────┐
│ PRE-COMMIT DOCUMENTATION IMPACT ANALYSIS                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ STEP 1: Code Duplication Check                                   │
│ ❓ "Does this code duplicate existing functionality?"            │
│    → Search codebase for similar patterns                        │
│    → Check if we can REFACTOR instead of DUPLICATE              │
│    → Consider extracting shared utility/component                │
│                                                                   │
│ STEP 2: Direct Documentation Impact                              │
│ ❓ "What docs directly reference this code?"                     │
│    → README files in same directory                              │
│    → API documentation for changed functions                     │
│    → Integration guides that use this code                       │
│    → Test documentation                                           │
│                                                                   │
│ STEP 3: Indirect Documentation Impact                            │
│ ❓ "What docs have related concepts/metrics/references?"         │
│    → Search for OLD values being changed (pricing, metrics)      │
│    → Find all docs mentioning related features                   │
│    → Check for broken cross-references                           │
│    → Look for outdated examples using old API                    │
│                                                                   │
│ STEP 4: Knowledge Organization Impact                            │
│ ❓ "Does this change how knowledge is organized?"                │
│    → Are we creating duplicate documentation?                    │
│    → Should we consolidate existing docs?                        │
│    → Do we need to update doc hierarchy/structure?               │
│    → Should we deprecate old docs and point to new ones?         │
│                                                                   │
│ STEP 5: Cross-Repository Impact (if applicable)                  │
│ ❓ "Do changes affect other repos/products?"                     │
│    → Check if lumina-web changes affect lumina-desktop docs      │
│    → Check if core library changes affect SDK documentation      │
│    → Consider if public docs need updating                       │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### **Automated Analysis Script**

```bash
#!/bin/bash
# scripts/pre-commit-doc-analysis.sh

echo "🔍 Running Pre-Commit Documentation Impact Analysis..."

# STEP 1: Code Duplication Check
echo ""
echo "STEP 1: Checking for code duplication..."
# Get changed functions/classes
git diff --cached --name-only | while read file; do
    if [[ $file == *.ts || $file == *.tsx || $file == *.rs ]]; then
        # Extract function names from diff
        FUNCTIONS=$(git diff --cached $file | grep "^+.*function\|^+.*fn " | sed 's/^+//' | awk '{print $2}')

        for func in $FUNCTIONS; do
            # Search for similar function names in codebase
            MATCHES=$(grep -r "$func" --include="*.ts" --include="*.tsx" --include="*.rs" | grep -v "$file" | wc -l)
            if [ $MATCHES -gt 0 ]; then
                echo "⚠️  Function '$func' found in $MATCHES other files - check for duplication"
            fi
        done
    fi
done

# STEP 2 & 3: Documentation Impact Analysis
echo ""
echo "STEP 2-3: Analyzing documentation impact..."

# Check for pricing changes
PRICING_CHANGE=$(git diff --cached | grep -E "(\$[0-9]+\.[0-9]{2}|[0-9]+/month)")
if [ ! -z "$PRICING_CHANGE" ]; then
    echo "💰 PRICING CHANGED - Check these files:"
    grep -r "\$4.99\|\$14.99\|\$49" --include="*.md" | cut -d: -f1 | sort -u
fi

# Check for timeline changes
TIMELINE_CHANGE=$(git diff --cached | grep -E "([0-9]+ weeks|Week [0-9]+|Phase [0-9]+)")
if [ ! -z "$TIMELINE_CHANGE" ]; then
    echo "📅 TIMELINE CHANGED - Check these files:"
    grep -r "Week [0-9]\+\|Phase [0-9]" --include="*.md" | cut -d: -f1 | sort -u
fi

# Check for metric changes
METRIC_CHANGE=$(git diff --cached | grep -E "([0-9]+% |[0-9]+ MTok|[0-9]+ patterns)")
if [ ! -z "$METRIC_CHANGE" ]; then
    echo "📊 METRICS CHANGED - Check these files:"
    grep -r "[0-9]\+% \|MTok\|patterns" --include="*.md" | cut -d: -f1 | sort -u
fi

# STEP 4: Knowledge Organization Check
echo ""
echo "STEP 4: Checking knowledge organization..."
NEW_DOCS=$(git diff --cached --name-only | grep "\.md$")
if [ ! -z "$NEW_DOCS" ]; then
    echo "📄 NEW DOCUMENTATION FILES:"
    echo "$NEW_DOCS"
    echo ""
    echo "⚠️  Check if these duplicate existing documentation:"
    for doc in $NEW_DOCS; do
        BASENAME=$(basename "$doc" .md)
        SIMILAR=$(find . -name "*$BASENAME*.md" | grep -v "$doc")
        if [ ! -z "$SIMILAR" ]; then
            echo "   Similar: $SIMILAR"
        fi
    done
fi

echo ""
echo "✅ Pre-commit analysis complete. Review warnings above."
echo "💡 TIP: Run 'git diff --cached --stat' to see what you're committing."
```

### **Integration with commit-enforcer Agent**

Update `.claude/agents/commit-enforcer.md` to include this analysis:

```markdown
### Pre-Commit Analysis (NEW - Pattern-META-002)

Before validating commit message, run documentation impact analysis:

1. **Code Duplication Check**
   - Search for similar function/class names
   - Flag potential duplicates
   - Suggest refactoring if found

2. **Documentation Impact Analysis**
   - Identify direct documentation (same dir README, API docs)
   - Find indirect documentation (related concepts, metrics)
   - Check for broken cross-references

3. **Knowledge Organization Check**
   - Flag duplicate documentation
   - Suggest consolidation
   - Check if deprecation needed

4. **Cross-Repository Impact**
   - Check if changes affect other products
   - Flag need for multi-repo updates

**Report Format:**
```
🔍 Documentation Impact Analysis:

CODE DUPLICATION:
⚠️  Function 'calculatePrice' found in 3 other files:
   - src/utils/pricing.ts
   - src/components/PricingCard.tsx
   - Consider: Extract to shared utility?

DIRECT DOCUMENTATION IMPACT:
📄 README.md (same directory) - mentions this API
📄 INTEGRATION_GUIDE.md - has examples using old API

INDIRECT DOCUMENTATION IMPACT:
💰 Pricing changed - 8 files reference old pricing
📊 Metrics changed - 5 files have outdated counts

KNOWLEDGE ORGANIZATION:
⚠️  Creating new PRICING_GUIDE.md - similar to BUSINESS_MODEL.md
   Consider: Merge into single document?

RECOMMENDATION: Update 13 files before committing
```
```

---

## Examples

### **Example 1: Your Business Model V2 Commit**

**Scenario:**
You updated Business Model V2 pricing across 16 files. Later discovered 5 MORE files with old pricing.

**What Should Have Happened (Pattern-META-002):**

```bash
# Before committing Business Model V2 changes:
$ scripts/pre-commit-doc-analysis.sh

🔍 Running Pre-Commit Documentation Impact Analysis...

STEP 2-3: Analyzing documentation impact...
💰 PRICING CHANGED - Check these files:
   docs/README.md - has old pricing ($15, $50)
   docs/patterns/README.md - references old business model doc
   SIMPLE_DEPLOYMENT_ARCHITECTURE.md - pricing table outdated
   docs/build/STANDARD_OPERATING_PROCEDURES.md - old doc reference
   docs/build/MULTI_MODEL_ROUTING.md - old doc reference
   BUSINESS_MODEL_V2.md - NEW (being updated) ✅
   VIRAL_GROWTH_STRATEGY.md - NEW (being updated) ✅
   [... 14 more files ...]

RECOMMENDATION: Update 21 files total (not just 16)

⚠️  WARNING: 5 files NOT in your staged changes:
   - docs/README.md
   - docs/patterns/README.md
   - SIMPLE_DEPLOYMENT_ARCHITECTURE.md
   - docs/build/STANDARD_OPERATING_PROCEDURES.md
   - docs/build/MULTI_MODEL_ROUTING.md

💡 Run: git add [these files] before committing
```

**Result:**
All 21 files updated in ONE commit, not two.

### **Example 2: Code Duplication Prevention**

**Scenario:**
Implementing a pricing calculator function.

**Analysis Output:**

```bash
🔍 Running Pre-Commit Documentation Impact Analysis...

STEP 1: Checking for code duplication...
⚠️  Function 'calculatePrice' found in 3 other files:
   src/utils/pricing.ts (line 45) - EXACT match
   src/components/PricingCard.tsx (line 23) - Similar logic
   src/lib/subscriptions.ts (line 67) - Calls similar function

RECOMMENDATION:
❌ Don't duplicate. Instead:
   1. Use existing calculatePrice() from src/utils/pricing.ts
   2. OR: Refactor both into shared utility
   3. OR: Explain in commit WHY duplication is necessary

⛔ BLOCKING COMMIT until resolved.
```

**Result:**
Developer discovers existing function, imports instead of duplicating.

### **Example 3: Cross-Repository Impact**

**Scenario:**
Updating API response format in core library.

**Analysis Output:**

```bash
🔍 Running Pre-Commit Documentation Impact Analysis...

STEP 5: Cross-repository impact detected...
⚠️  Changes to src/api/types.ts affect:
   - lumina-desktop: Uses this API format
   - lumina-web: TypeScript types need updating
   - SDK documentation: Examples show old format

RECOMMENDATION:
📋 Create multi-repo update plan:
   1. Update aetherlight-core (this repo)
   2. Update lumina-desktop/src/types/api.ts
   3. Update lumina-web/lib/api-client.ts
   4. Update docs/SDK_REFERENCE.md examples
   5. Consider: Breaking change? Version bump needed?

💡 Document in commit message: "BREAKING: API response format changed"
```

**Result:**
Coordinated update across all affected repositories.

---

## Benefits

**1. Prevents Documentation Drift**
- All related docs updated in same commit
- No follow-up "oops, missed this file" commits
- Single source of truth maintained

**2. Eliminates Code Duplication**
- Discovers existing implementations before coding
- Encourages refactoring over reimplementation
- Reduces maintenance burden

**3. Maintains Knowledge Organization**
- Flags duplicate documentation
- Suggests consolidation
- Keeps doc hierarchy clean

**4. Enables Confident Commits**
- Know you've updated everything affected
- No anxiety about what you might have missed
- Commit message documents full impact

**5. Compounds Quality Over Time**
- Each commit improves organization
- No technical debt accumulation
- Clean knowledge graph maintained

---

## Integration with commit-enforcer

**Enhanced Commit Validation Flow:**

```
1. Developer stages changes: git add .

2. Pre-commit hook runs: scripts/pre-commit-doc-analysis.sh

3. Analysis identifies impacts:
   - Code duplication: WARN or BLOCK
   - Documentation drift: LIST affected files
   - Knowledge organization: SUGGEST improvements
   - Cross-repo impact: CREATE update plan

4. Developer reviews analysis:
   - Add missing files to staging
   - Refactor instead of duplicate
   - Consolidate documentation
   - Document multi-repo changes

5. commit-enforcer validates:
   - Conventional commit format ✅
   - Chain of Thought reasoning ✅
   - Pattern references ✅
   - Documentation completeness ✅ (NEW)

6. Commit created with full impact documented
```

---

## Metrics

**Track these to measure effectiveness:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Follow-up "doc update" commits | 0 per phase | Count commits with "docs:" after code changes |
| Code duplication incidents | <5% of commits | Flag similar code patterns in reviews |
| Documentation drift rate | 0% | % of docs with references to deprecated values |
| Cross-file consistency | 100% | Automated checks (pricing, metrics, timelines match) |
| Knowledge consolidation | +10% per phase | Count of redundant docs removed |

---

## Tools & Automation

### **Grep Patterns for Common Drift**

```bash
# Find all pricing references
grep -r "\$[0-9]\+\.[0-9][0-9]" --include="*.md" | cut -d: -f1 | sort -u

# Find all timeline references
grep -r "Week [0-9]\+\|Phase [0-9]" --include="*.md" | cut -d: -f1 | sort -u

# Find all metric references
grep -r "[0-9]\+%\|[0-9]\+ MTok\|[0-9]\+ patterns" --include="*.md" | cut -d: -f1 | sort -u

# Find deprecated document references
grep -r "BUSINESS_MODEL_AND_LICENSING.md" --include="*.md"

# Find duplicate function names
find . -name "*.ts" -o -name "*.rs" | xargs grep "^function\|^fn " | cut -d: -f2 | sort | uniq -d
```

### **VS Code Extension (Future)**

```json
{
  "aetherlight.preCommit.documentationAnalysis": true,
  "aetherlight.preCommit.codeDuplicationCheck": true,
  "aetherlight.preCommit.crossRepoImpact": true,
  "aetherlight.preCommit.blockOnDuplication": true
}
```

---

## Anti-Patterns (What NOT to Do)

**❌ "I'll update docs in next commit"**
- Result: Documentation drift accumulates
- Next commit never comes
- Knowledge organization degrades

**❌ "Only update docs I directly changed"**
- Result: Indirect impacts missed
- Metrics/pricing out of sync across files
- Broken cross-references

**❌ "Skip duplication check, this is different"**
- Result: Very similar code in multiple places
- Maintenance burden grows
- Bugs fixed in one place but not others

**❌ "This is a small change, skip analysis"**
- Result: Death by a thousand cuts
- Many small drifts = big inconsistency
- Compound effect over time

---

## Success Criteria

**This pattern is working when:**

✅ **Zero follow-up doc commits**
- No "docs: fix missed references" after code changes
- First commit is complete commit

✅ **Code duplication caught early**
- Developer discovers existing impl before coding
- Refactoring suggested, not duplication

✅ **Cross-file consistency maintained**
- All pricing references match
- All timeline references match
- All metrics synchronized

✅ **Knowledge organization improves**
- Redundant docs identified and consolidated
- Clear single source of truth
- Doc hierarchy stays clean

✅ **Commit confidence high**
- Developer knows they've covered everything
- No anxiety about what might be missed
- Commit message documents full impact

---

## Related Patterns

- **Pattern-META-001**: Documentation Feedback Loop (systematic post-change doc updates)
- **Pattern-META-002**: THIS PATTERN (pre-commit doc impact analysis)
- **Pattern-000**: Meta-Loop Development (both patterns contribute to)
- **SOP-007**: Git Workflow Standards (enforced by this pattern)

**Key Difference from Pattern-META-001:**
- **META-001**: Post-change ("What docs need updating NOW?")
- **META-002**: Pre-commit ("What WILL need updating BEFORE I commit?")
- **META-002**: Adds code duplication check + cross-repo awareness

---

## Adoption Strategy

### **Phase 1: Manual Process (Immediate)**
1. Developer runs `scripts/pre-commit-doc-analysis.sh` manually
2. Reviews output, updates files
3. Stages additional files
4. Commits with full impact documented

### **Phase 2: Pre-Commit Hook (Week 2)**
1. Install hook: `.git/hooks/pre-commit`
2. Automatically runs analysis before commit
3. Blocks commit if critical issues found
4. Outputs recommendations

### **Phase 3: IDE Integration (Month 2)**
1. VS Code extension shows analysis in real-time
2. Highlights affected files in explorer
3. Suggests files to stage
4. One-click "add all affected docs"

### **Phase 4: AI-Powered Analysis (Month 6)**
1. Use Claude to analyze semantic relationships
2. Detect conceptual duplication (not just naming)
3. Suggest consolidation strategies
4. Generate update plans automatically

---

## Meta-Realization

**This pattern was discovered by APPLYING Pattern-META-001:**

1. You made a commit (Business Model V2 sync)
2. You discovered drift (README, pattern index outdated)
3. You asked: "How do I prevent this next time?"
4. You identified: Need pre-commit analysis, not just post-change
5. I documented this as Pattern-META-002
6. **This is recursive pattern discovery in action**

**Pattern-META-001 (post-change) + Pattern-META-002 (pre-commit) = Complete documentation lifecycle**

---

**PATTERN STATUS:** ✅ Active - Implement immediately
**NEXT STEP:** Create `scripts/pre-commit-doc-analysis.sh`
**OWNER:** commit-enforcer agent + core team
**LAST UPDATED:** 2025-10-06

---

*"The best time to find documentation drift is BEFORE it enters the codebase."*
