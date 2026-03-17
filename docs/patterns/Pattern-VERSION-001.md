# Pattern-VERSION-001: Production-Sprint-Feature-Enhancement Versioning

**CREATED:** 2025-10-19
**CATEGORY:** Development Process
**LANGUAGE:** JavaScript
**QUALITY SCORE:** 0.95
**APPLICABILITY:** All ÆtherLight projects
**STATUS:** Production-Validated (in use as of 2025-10-19)
**RELATED:** PATTERN-DOGFOOD-002, PATTERN-META-001, PATTERN-SPRINT-001

---




## Context

Need a clear versioning strategy that:
1. Tracks pre-production vs production releases
2. Shows which sprint a feature belongs to
3. Distinguishes major features from enhancements
4. Enables semantic understanding of version numbers

**Problem:** Traditional semantic versioning (X.Y.Z) doesn't capture sprint/feature context in multi-sprint projects.

---

## Solution

**Format:** `PRODUCTION.SPRINT.FEATURE.ENHANCEMENT`

### **Component Definitions:**

**PRODUCTION (X.0.0.0):**
- `0.x.x.x` = Pre-production (development, testing, validation)
- `1.x.x.x` = First production release (public, stable)
- `2.x.x.x` = Second production release (major version bump)

**SPRINT (0.X.0.0):**
- Increments with each sprint
- Example: Sprint 5 = `0.5.0.0`
- Sprint completion = `0.5.N.M` (where N is last feature)

**FEATURE (0.X.Y.0):**
- Major feature within sprint
- Example: Sprint Tab = `0.5.1.0` (Feature 1 of Sprint 5)
- Voice Tab Compact UI = `0.5.2.0` (Feature 2 of Sprint 5)

**ENHANCEMENT (0.X.Y.Z):**
- Enhancement or bug fix for feature
- Example: Sprint Tab UI integration = `0.5.1.1` (Enhancement 1 of Feature 1)
- Bug fix = `0.5.1.2` (Enhancement 2 of Feature 1)

---

## Design Decision

**DESIGN DECISION:** Four-component versioning (PRODUCTION.SPRINT.FEATURE.ENHANCEMENT)
**WHY:** Captures pre-production status, sprint context, feature granularity, and iterative improvements

**REASONING CHAIN:**
1. Need to distinguish pre-production (0.x.x.x) from production (1.x.x.x)
2. Need to track which sprint a feature was built in (0.5.x.x = Sprint 5)
3. Need to distinguish major features (0.5.1.0) from enhancements (0.5.1.1)
4. Traditional semantic versioning (X.Y.Z) loses sprint context
5. Four components provide full traceability (production status, sprint, feature, enhancement)
6. Result: Version number tells complete story

---

## Implementation

### **Version Bump Rules:**

**When to bump PRODUCTION:**
- `0.x.x.x → 1.0.0.0`: First production release (all sprints complete, fully tested)
- `1.x.x.x → 2.0.0.0`: Major breaking changes requiring new production version

**When to bump SPRINT:**
- `0.5.x.x → 0.6.0.0`: New sprint started
- Sprint baseline always ends in `.0.0` (e.g., `0.5.0.0`)

**When to bump FEATURE:**
- `0.5.1.x → 0.5.2.0`: New major feature within sprint
- Feature baseline always ends in `.0` (e.g., `0.5.1.0`)

**When to bump ENHANCEMENT:**
- `0.5.1.0 → 0.5.1.1`: Enhancement to existing feature
- `0.5.1.1 → 0.5.1.2`: Bug fix or another enhancement

---

## Examples

### **Sprint 5 Development (Voice Panel Redesign):**

```
0.5.0.0 → Sprint 5 baseline (sprint plan created)
0.5.1.0 → Feature 1: Sprint Tab foundation (SprintLoader.ts)
0.5.1.1 → Enhancement 1: Sprint Tab UI integration
0.5.1.2 → Enhancement 2: Add task filtering
0.5.2.0 → Feature 2: Voice Tab compact UI (icon bar)
0.5.2.1 → Enhancement 1: Add auto-terminal-selection
0.5.3.0 → Feature 3: Context-linked preview
... (continue through all 29 tasks)
0.5.11.0 → Feature 11: Edge cases & polish (last feature)
0.5.11.5 → Final enhancement before sprint complete
```

### **Production Release:**

```
0.5.11.5 → Sprint 5 complete, ready for production testing
1.0.0.0 → First production release (Voice Panel v0.5.0 fully tested)
```

### **Next Sprint:**

```
1.0.0.0 → Production baseline
0.6.0.0 → Sprint 6 started (new features for production users)
0.6.1.0 → Feature 1 of Sprint 6
1.1.0.0 → Sprint 6 features released to production
```

---

## Commit Message Format

**Template:**
```
<type>(<scope>): v<VERSION> - <short description>

VERSION: <PRODUCTION>.<SPRINT>.<FEATURE>.<ENHANCEMENT>

DESIGN DECISION: <What was decided>
WHY: <Reasoning behind decision>

REASONING CHAIN:
1. <Step with reasoning>
2. <Step with reasoning>
3. <Step with reasoning>

DELIVERABLES:
- <File 1> (<lines> lines) - <description>
- <File 2> (<lines> lines) - <description>

KEY FEATURES:
- <Feature 1>
- <Feature 2>

NEXT: <NEXT_VERSION> - <next feature/enhancement>

PATTERN: Pattern-VERSION-001, Pattern-XXX-YYY
RELATED: <related files/tasks>
PERFORMANCE: <performance metrics if applicable>
```

**Example:**
```
feat(sprint): v0.5.1.0 - Sprint Tab foundation with TOML loader

VERSION: 0.5.1.0 (Sprint 5, Feature 1)

DESIGN DECISION: Build Sprint Tab FIRST for meta-dogfooding
WHY: Use Sprint Tab to track building Voice Panel v0.5.0

REASONING CHAIN:
1. User requested immediate Sprint Tab for dogfooding
2. Created SprintLoader.ts to parse TOML
3. Loads all 29 tasks with metadata
4. Result: Sprint Tab ready for immediate usage

DELIVERABLES:
- SprintLoader.ts (251 lines) - TOML parser
- VERSION.md - Versioning documentation

NEXT: 0.5.1.1 - Sprint Tab UI integration

PATTERN: Pattern-VERSION-001, Pattern-DOGFOOD-002
```

---

## When to Use / When Not to Use

### **When to Use:**
- ✅ Multi-sprint projects with clear feature boundaries
- ✅ Pre-production development requiring sprint tracking
- ✅ Projects with frequent feature iterations (enhancements)
- ✅ Teams needing full traceability (which sprint? which feature?)

### **When Not to Use:**
- ❌ Single-sprint projects (three-component versioning sufficient)
- ❌ Production-only projects (no pre-production phase)
- ❌ Projects with infrequent releases (traditional semantic versioning sufficient)

---

## Integration with CI/CD

**VERSION.md File:**
- Keep `VERSION.md` in repository root or project directory
- Update `CURRENT VERSION` line with every commit
- Automated scripts can parse this for version bumping

**package.json (VS Code Extension):**
```json
{
  "version": "0.5.1.0",
  "name": "aetherlight-voice-panel"
}
```

**Automated Version Bump Script:**
```bash
#!/bin/bash
# bump-version.sh

CURRENT_VERSION=$(grep "CURRENT VERSION:" VERSION.md | cut -d' ' -f3)
IFS='.' read -r PROD SPRINT FEATURE ENH <<< "$CURRENT_VERSION"

case "$1" in
  production)
    NEW_VERSION="$((PROD + 1)).0.0.0"
    ;;
  sprint)
    NEW_VERSION="$PROD.$((SPRINT + 1)).0.0"
    ;;
  feature)
    NEW_VERSION="$PROD.$SPRINT.$((FEATURE + 1)).0"
    ;;
  enhancement)
    NEW_VERSION="$PROD.$SPRINT.$FEATURE.$((ENH + 1))"
    ;;
  *)
    echo "Usage: bump-version.sh [production|sprint|feature|enhancement]"
    exit 1
    ;;
esac

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION"
sed -i "s/CURRENT VERSION: $CURRENT_VERSION/CURRENT VERSION: $NEW_VERSION/" VERSION.md
sed -i "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
```

---

## Performance

**Version Comparison:** O(1) (simple string comparison)
**Version Parsing:** O(1) (split by dots, 4 components)
**Storage:** 10-15 bytes per version string

---

## Related Patterns

- **Pattern-DOGFOOD-002:** Minimal Viable Feature for Immediate Dogfooding
- **Pattern-META-001:** Documentation Feedback Loop
- **Pattern-SPRINT-001:** Sprint Plan with Dependency Graph

---

## Pattern Status

**STATUS:** Production-Validated (in use as of 2025-10-19)
**CONFIDENCE:** 95% (clear, unambiguous, easy to understand)
**USAGE:** All ÆtherLight projects use this versioning system

---

## Examples in Practice

### **Sprint 5 Voice Panel Redesign:**
- Started: `0.5.0.0` (2025-10-19)
- First feature: `0.5.1.0` (Sprint Tab foundation)
- Current: `0.5.1.0`
- Target completion: `0.5.11.x` (11 features, unknown enhancements)
- Production: `1.0.0.0` (after full testing)

### **Previous Sprints:**
- Sprint 4 (Autonomous Sprints): `0.4.x.x`
- Sprint 3.10 (Terminal Middleware): `0.3.10.x`
- Sprint 3.9 (Real-Time Sync): `0.3.9.x`
- Sprint 0 (Code Analyzer): `0.0.x.x`

---

**PATTERN COMPLETE** ✅
