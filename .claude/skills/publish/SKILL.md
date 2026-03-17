---
name: publish
description: Publish ÆtherLight releases to npm and GitHub. Use when the user wants to publish, release, or deploy a new version. Automatically handles version bumping, compilation, verification, and publishing.
---

# ÆtherLight Publishing Skill

## What This Skill Does

Automates the complete release process for ÆtherLight:
- Bumps version across all packages
- Compiles TypeScript and verifies build
- Packages VS Code extension (.vsix)
- Builds desktop app installers (.exe and .msi)
- Publishes to npm registry
- Creates git tag and GitHub release with all artifacts

## When Claude Should Use This

Use this skill when the user:
- Says "publish this" or "let's publish" or "release a new version"
- Wants to deploy changes to npm
- Mentions creating a release
- Asks to bump the version and publish

## How to Use

### Pre-Release Workflow Check

1. **Verify proper Git workflow**:
   - Should be on `master` branch after PR merge
   - If not on master, guide user through proper workflow:
     ```
     1. Create PR from feature branch
     2. Get review and merge to master
     3. Checkout master and pull latest
     4. Then run publish script
     ```

2. **Ask for version type** (if not specified):
   ```
   Which version type?
   - patch: Bug fixes (0.13.20 → 0.13.21)
   - minor: New features (0.13.20 → 0.14.0)
   - major: Breaking changes (0.13.20 → 1.0.0)
   ```

3. **Run the automated publishing script**:
   ```bash
   node scripts/publish-release.js [patch|minor|major]
   ```

4. **Monitor output** - The script will (IN THIS ORDER):
   - ✓ Verify npm authentication (must be `aelor`)
   - ✓ Verify Git workflow (branch, clean, up-to-date)
   - ✓ Check GitHub CLI authentication (required)
   - ✓ Bump version across all packages
   - ✓ Compile TypeScript
   - ✓ Verify compiled artifacts exist
   - ✓ Package .vsix extension
   - ✓ Build desktop app installers (if configured)
   - ✓ Commit version bump
   - ✓ Create git tag
   - ✓ Push to GitHub (FIRST)
   - ✓ Create GitHub release with .vsix and installers
   - ✓ Verify GitHub release has all artifacts
   - ✓ Publish to npm registry (LAST)
   - ✓ Verify all packages published correctly

5. **Report completion**:
   ```
   ✅ Version X.X.X published successfully!
   - npm: https://www.npmjs.com/package/aetherlight
   - GitHub: https://github.com/AEtherlight-ai/lumina/releases/tag/vX.X.X
   ```

## Error Handling

If the script fails, help the user:

**Not logged in to npm:**
```bash
npm login
# Username: aelor
```

**GitHub CLI not installed:**
```bash
# Windows (winget)
winget install --id GitHub.cli

# Mac (homebrew)
brew install gh
```

**Not logged in to GitHub CLI:**
```bash
gh auth login
# Follow prompts to authenticate
```

**Uncommitted git changes:**
```bash
git status
# User needs to commit or stash changes
```

**Compilation errors:**
Show the TypeScript errors from the output

**VSIX not created:**
Check the package.json scripts

**Desktop app build fails:**
```bash
cd products/lumina-desktop
npm run tauri build
# Check for Rust compilation errors or missing dependencies
```

**Installers not found after build:**
```bash
# Desktop installers should be at:
find ./products/lumina-desktop/src-tauri/target/release/bundle -name "*.exe" -o -name "*.msi"

# Copy to vscode-lumina directory:
cp ./products/lumina-desktop/src-tauri/target/release/bundle/msi/*.msi ./vscode-lumina/
cp ./products/lumina-desktop/src-tauri/target/release/bundle/nsis/*.exe ./vscode-lumina/
```

**GitHub release creation fails:**
This is CRITICAL - users install from GitHub releases. The script will:
- Exit immediately if gh CLI not installed
- Exit if not authenticated to GitHub
- Verify the release was created with .vsix and installers
- Fail loudly if any step doesn't work

---

## Desktop Installer Workflow (CRITICAL)

### Why Desktop Installers Are Required

**CRITICAL:** Desktop app installers (.exe and .msi for Windows) MUST be included in EVERY GitHub release.

**Why:**
1. Users install ÆtherLight via `npm install -g aetherlight`
2. The CLI installer downloads the .vsix from GitHub releases
3. Desktop app is ALSO downloaded from the same GitHub release
4. Without installers, users get VS Code extension but NO desktop app
5. Desktop app is required for full ÆtherLight functionality

### File Locations and Git Workflow

**Desktop installers are:**
- ✅ Built locally (Tauri build process)
- ✅ Stored on disk in `vscode-lumina/` directory
- ✅ Attached to GitHub releases (by publish script)
- ❌ **NOT tracked in git** (binary files excluded via .gitignore)

**Current files:**
```bash
vscode-lumina/Lumina_0.1.0_x64-setup.exe  # 4.0MB - Windows installer (NSIS)
vscode-lumina/Lumina_0.1.0_x64_en-US.msi  # 5.8MB - Windows installer (MSI)
```

**gitignore rules** (added in v0.16.7):
```gitignore
# Desktop installers (binary files should not be in git)
*.exe
*.msi
*.dmg
*.deb
*.AppImage
```

### How Publish Script Handles Installers

**Automated process** (`scripts/publish-release.js` lines 355-428):

1. **Find installers** (lines 355-375):
   ```javascript
   const exeFile = path.join(vscodeLuminaPath, 'Lumina_0.1.0_x64-setup.exe');
   const msiFile = path.join(vscodeLuminaPath, 'Lumina_0.1.0_x64_en-US.msi');
   if (fs.existsSync(exeFile)) { desktopFiles.push(exeFile); }
   if (fs.existsSync(msiFile)) { desktopFiles.push(msiFile); }
   ```

2. **Warn if missing** (lines 370-375):
   ```
   ⚠️  Warning: No desktop installers found
   Desktop app will not be available for this release
   ```

3. **Attach to GitHub release** (lines 377-393):
   ```javascript
   // Create release with .vsix and desktop installers
   const allFiles = [`"vscode-lumina/aetherlight-${newVersion}.vsix"`, ...desktopFiles].join(' ');
   exec(`gh release create v${newVersion} --notes-file .release-notes.tmp ${allFiles}`);
   ```

4. **Verify upload** (lines 395-428):
   ```javascript
   // Check for .vsix file (CRITICAL)
   const vsixCheck = execSilent(`gh release view v${newVersion} --json assets -q '.assets[] | select(.name | endswith(".vsix"))'`);

   // Check for desktop installers (WARNING if missing)
   const hasExe = allAssets.includes('Lumina_0.1.0_x64-setup.exe');
   const hasMsi = allAssets.includes('Lumina_0.1.0_x64_en-US.msi');
   ```

### Pre-Publish Checklist for Installers

**BEFORE running publish script, verify installers exist:**

```bash
# Check if installers are present on disk
ls -lh vscode-lumina/Lumina*.exe vscode-lumina/Lumina*.msi

# Expected output:
# -rwxr-xr-x 1 user 4.0M Oct 30 vscode-lumina/Lumina_0.1.0_x64-setup.exe
# -rw-r--r-- 1 user 5.8M Oct 30 vscode-lumina/Lumina_0.1.0_x64_en-US.msi
```

**If files are missing:**
1. Desktop app was never built, OR
2. Files were deleted, OR
3. Wrong directory

### Regenerating Desktop Installers

**If installers are missing and need to be rebuilt:**

```bash
# Navigate to desktop app directory
cd products/lumina-desktop

# Install dependencies (if needed)
npm install

# Build desktop app for Windows
npm run tauri build

# Installers will be generated at:
# - src-tauri/target/release/bundle/nsis/*.exe
# - src-tauri/target/release/bundle/msi/*.msi

# Copy to vscode-lumina directory for publish script
cp src-tauri/target/release/bundle/nsis/*.exe ../../vscode-lumina/
cp src-tauri/target/release/bundle/msi/*.msi ../../vscode-lumina/

# Verify files are in place
ls -lh ../../vscode-lumina/Lumina*.exe ../../vscode-lumina/Lumina*.msi
```

### Desktop App Version Independence

**Important:** Desktop app version (0.1.0) is INDEPENDENT of VS Code extension version (0.16.7).

**Why:**
- Desktop app changes less frequently than VS Code extension
- Extension gets frequent patches (bug fixes, UI improvements)
- Desktop app only updates when core functionality changes
- Both are versioned independently but released together

**Current versions:**
- VS Code Extension: v0.16.7 (frequent updates)
- Desktop App: v0.1.0 (stable, infrequent updates)

### What Publish Script Does

**Publish script behavior:**
- ✅ Looks for installers in `vscode-lumina/` directory
- ✅ Attaches any found installers to GitHub release
- ⚠️ Warns if no installers found (but doesn't fail)
- ✅ Verifies installers uploaded successfully
- ✅ Continues with publish even if no installers (extension-only release)

**This means:**
- If installers exist → Full release (extension + desktop app)
- If no installers → Extension-only release (with warning)
- User can choose to ship extension-only if desktop app unchanged

### Historical Context

**v0.16.7 git hygiene fix:**
- **Before:** Installers committed to git (9.8MB binary files in repository)
- **After:** Installers excluded from git (.gitignore), kept on disk only
- **Benefit:** Clean git history, binaries only in releases
- **No Impact:** Publish script still finds and attaches installers

**Pattern:** Binary artifacts belong in releases, NOT in git.

---

## Important Rules

**ALWAYS use the automated script** (`scripts/publish-release.js`)

**NEVER manually run individual publish steps** - this caused the v0.13.20 bug where users saw wrong versions after updating.

**Why the script is critical:**
- Prevents version mismatches
- Ensures everything is compiled before publishing
- No timing issues or partial deploys
- Verifies all artifacts before publishing anything
- Includes desktop app installers in GitHub release
- .npmignore prevents bloated npm packages (was 246MB, now 251KB)

## Related Files

- `scripts/publish-release.js` - The automation script
- `scripts/bump-version.js` - Version synchronization
- `.claude/commands/publish.md` - User-invoked command
- `PUBLISHING.md` - Publishing documentation
- `UPDATE_FIX_SUMMARY.md` - Why we use this approach
- `vscode-lumina/.npmignore` - Excludes binaries from npm package
- `products/lumina-desktop/` - Desktop app source (Tauri + Rust)

## Known Issues Fixed

### v0.13.28: Manual publish caused version mismatch
**Issue:** npm showed 0.13.26, GitHub release had v0.13.28, auto-update didn't work
**Cause:** Automated script was bypassed - manual version bump, manual git tag, manual GitHub release
**Result:** TypeScript compilation skipped, npm publish skipped, all verification skipped
**Fix:** v0.13.29 published using complete automated process with desktop installers

### v0.13.29: npm package bloat
**Issue:** npm publish failed with "413 Payload Too Large" (246MB)
**Cause:** All old .vsix files (0.13.11-0.13.28) included in npm package
**Fix:** Created .npmignore to exclude *.vsix, *.exe, *.msi files
**Result:** Package size reduced to 251KB (1000x smaller)

### v0.13.29: Sub-packages not published (CRITICAL)
**Issue:** Users couldn't install or update - "No matching version found for aetherlight-analyzer@^0.13.29"
**Cause:** Publish script only published main package, not sub-packages (analyzer, SDK, node bindings)
**Impact:**
- Main package published: aetherlight@0.13.29 ✅
- Sub-packages still at 0.13.28 ❌
- npm install failed for ALL users
- Update notifications worked but installs failed silently
**Fix:** Updated publish script to publish ALL 4 packages in dependency order
**Prevention:** Script now:
1. Publishes sub-packages FIRST (analyzer, SDK, node)
2. Publishes main package LAST (depends on sub-packages)
3. Verifies each package at correct version
4. Fails loudly if any package verification fails
**Files:** `scripts/publish-release.js:270-322`

### v0.16.15: Automation gaps - manual bypass required (IN PROGRESS)
**Issue:** Automated script failed, requiring manual bypass to publish
**Cause:** Three automation gaps exposed by package architecture changes (scoped → unscoped)
**Impact:** Manual bypass required (2 hours), violates Pattern-PUBLISH-002

**Three Automation Failures:**
1. **Missing @types/mocha** - TypeScript compilation failed without type definitions
2. **Old scoped imports** - Import paths still used `@aetherlight/*` after package rename
3. **Poor version handling** - Script didn't handle already-bumped version gracefully

**Manual Bypass Process (Pattern-PUBLISH-002 compliant):**
- Claude asked user for approval BEFORE bypassing
- Explained risks and missing steps
- User approved: "continue with 16.15"
- Manual publish completed successfully

**Fix In Progress:** Sprint Task POST-005
- Integrate pre-publish-check.js validation (7 automated checks)
- Add devDependencies completeness validation
- Add import path consistency checks
- Better version state handling (detect, offer reset/continue)
- Enhanced error messages with actionable suggestions
- **Goal:** v0.16.16+ publishes with ZERO manual intervention

**Files Created:**
- `scripts/pre-publish-check.js` - 7 validation checks (Pattern-PUBLISH-004)
- Sprint Task: `internal/sprints/ACTIVE_SPRINT.toml` - POST-005
- Known Issue entry: `.claude/CLAUDE.md` - Lines 1649-1752

**Status:** TASK CREATED - Fix scheduled in current sprint
**Estimated completion:** 3-4 hours implementation
**See:** `.claude/CLAUDE.md` Known Issues section for full details

**Key lesson:** ALWAYS use the automated script. Manual steps WILL cause bugs.
