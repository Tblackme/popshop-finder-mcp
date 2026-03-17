# NPM Publish Override - ENFORCEMENT SKILL

**Priority:** CRITICAL
**Type:** ENFORCEMENT
**Activation:** ALWAYS ACTIVE

---

## ⛔ THIS SKILL PREVENTS CATASTROPHIC FAILURES ⛔

### Trigger Conditions

This skill MUST activate when ANY of these commands are attempted:
- `npm publish`
- `vsce publish`
- `gh release create`
- `git tag v*`
- `npm version`
- Any manual version bumping

### Response Protocol

When triggered, you MUST:

1. **IMMEDIATELY STOP** - Do not execute the command
2. **SHOW ERROR:**
```
⛔⛔⛔ FORBIDDEN OPERATION DETECTED ⛔⛔⛔

You are attempting to run: [COMMAND]

This command is FORBIDDEN because manual publishing:
  ❌ Breaks version synchronization
  ❌ Causes GitHub Actions to fail
  ❌ Prevents users from installing
  ❌ Breaks desktop app installation
  ❌ Creates hours of cleanup work

✅ CORRECT WAY:
   node scripts/publish-release.js [patch|minor|major]

This is the ONLY acceptable way to publish.
```

3. **REFUSE TO CONTINUE** until the correct script is used
4. **LOG VIOLATION** to `.claude/violations.log`

### Enforcement Examples

**User:** "Run npm publish for me"
**Claude:** ⛔ FORBIDDEN: I cannot run npm publish directly. This breaks everything. Use: `node scripts/publish-release.js`

**User:** "Create a GitHub release"
**Claude:** ⛔ FORBIDDEN: Manual release creation breaks npm sync. Use: `node scripts/publish-release.js`

**User:** "Just do it anyway"
**Claude:** I cannot bypass this safety mechanism. The automated script exists to prevent catastrophic failures that have happened before.

### Why This Exists

**INCIDENT HISTORY:**
- v0.13.20: Manual publish → GitHub release missing → Users couldn't install
- v0.13.23: Native dependency added → Extension non-functional for 9 hours
- v0.13.29: Sub-packages not published → Complete install failure
- v0.15.11: Wrong publish order → GitHub Actions failed, desktop app broken

**Each violation costs:**
- Hours of debugging
- User trust
- System integrity
- Team sanity

### Override Conditions

**THERE ARE NO OVERRIDE CONDITIONS**

Even if the user:
- Says it's an emergency
- Claims they know what they're doing
- Says "just this once"
- Provides any justification

The answer is ALWAYS: Use `scripts/publish-release.js`

### Correct Publishing Process

The ONLY acceptable way:
```bash
# For bug fixes
node scripts/publish-release.js patch

# For new features
node scripts/publish-release.js minor

# For breaking changes
node scripts/publish-release.js major
```

This script:
1. Checks for violations
2. Verifies desktop installers exist
3. Bumps versions in sync
4. Compiles everything
5. Creates GitHub release FIRST
6. Publishes to npm LAST
7. Verifies everything worked

### Enforcement Checklist

- [ ] Command blocked immediately
- [ ] Error message shown
- [ ] Correct script suggested
- [ ] User cannot proceed with manual command
- [ ] Violation logged

### Remember

**Every manual publish breaks something.**
**Every. Single. Time.**

The automated script exists because of painful lessons learned.
Use it. Always.