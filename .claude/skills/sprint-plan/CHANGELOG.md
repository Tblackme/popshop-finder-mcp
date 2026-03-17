# Sprint Planning Skill Changelog

All notable changes to the sprint-plan skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2025-01-14 - Sprint 17.1 Enhancements

### Added

- **Sprint-aware naming convention** (Pattern-DOCS-002):
  - Format: `{SPRINT_ID}_{TASK_ID}_{TYPE}.md`
  - Prevents collisions across sprints (Sprint 3 BUG-001 vs Sprint 17.1 BUG-001)
  - Examples: `17.1-BUGS_BUG-011_ENHANCED_PROMPT.md`, `3_PROTECT-001_TEST_PLAN.md`
  - Automated enforcement via pre-commit hook (INFRA-003)
  - See: `docs/patterns/Pattern-DOCS-002-TaskDocumentLinking.md`

- **Agent Validation Workflow** (Step 3.5):
  - MANDATORY checklist before task creation
  - Prevents UI tasks assigned to infrastructure-agent
  - Query Agent Selection Guide (SKILL.md lines 470-482)
  - Verify agent context file capabilities
  - Historical bugs prevented: UI tasks wrongly assigned in Sprint 17.1

- **Skill Assignment Workflow** (Step 3.6):
  - MANDATORY checklist for autonomous execution opportunities
  - Identifies automated workflows (publish, code-analyze, sprint-plan, etc.)
  - Adds `skill` field to TOML for autonomous tasks
  - Omits `skill` field for manual tasks
  - Example: Publishing task → `skill = "publish"`

### Changed

- **ENHANCE Mode Workflow**: Updated to use sprint-aware naming for generated documents
- **Examples**: All examples now use sprint-aware format (17.1-BUGS_ prefix)
- **Template Task Injection**: Improved clarity on REQUIRED vs SUGGESTED vs CONDITIONAL tasks

### Fixed

- Agent assignment mistakes: UI tasks no longer assigned to infrastructure-agent
- Document collision risk: Sprint-aware naming prevents filename conflicts
- Orphaned documents: Pre-commit hook ensures TOML linking (INFRA-003)

---

## [1.0.0] - 2024-12-15 - Initial Release

### Added

- CREATE Mode workflow for new sprints
- ENHANCE Mode workflow for adding tasks to existing sprints
- Template task injection from SPRINT_TEMPLATE.toml
- Git branch creation automation
- Sprint TOML generation with 5 required fields
- Agent assignment suggestions
- Error handling requirements for all tasks

### Features

- Automated sprint structure generation
- Phase-based task organization
- Dependency management
- Complexity estimation
- Pattern integration (Pattern-SPRINT-PLAN-001, Pattern-SPRINT-TEMPLATE-001)
