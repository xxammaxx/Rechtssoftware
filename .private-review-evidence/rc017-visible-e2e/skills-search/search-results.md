# Skills.sh Search Results — RC-017 Revision B

## Search Date
2026-07-31

## Search Terms
- "Playwright headed E2E testing" → skills.sh/topic/testing
- "accessibility axe testing" → skills.sh/topic/testing
- "visual regression playwright" → skills.sh/topic/testing
- "local web app testing" → skills.sh
- "user acceptance testing" → skills.sh

## Found Skills on skills.sh

### Official skills.sh Testing Category

| Skill | Repository | Status |
|-------|-----------|--------|
| test-driven-development | obra/superpowers | Available |
| webapp-testing | anthropics/skills | Available (Snyk warning — REJECTED) |
| verification-before-completion | obra/superpowers | Available |
| playwright-best-practices | currents-dev/playwright-best-practices-skill | Available |
| playwright-cli | microsoft/playwright-cli | Available |

## Candidate Matrix — Three RUNCARD Candidates

### Candidate A: playwright-pro
- **Repository**: borghei/Claude-Skills (confirmed exists, 436 stars)
- **Description**: Part of "Playwright Pro" deep-dive skill pack with 8 sub-skills
- **Repository status**: Active, 152 commits, MIT + Commons Clause license
- **Skill path**: Listed under `standards/` directory
- **SKILL.md**: Not directly accessible via raw.githubusercontent.com (different directory structure)
- **Security**: Repo has SECURITY.md
- **Network requirements**: None (skills are markdown/prompt files)
- **Decision**: READ-ONLY_EVALUATION — repo confirmed, full SKILL.md not reachable via raw URL

### Candidate B: a11y-testing
- **Repository**: yonatangross/orchestkit (confirmed exists, 210 stars)
- **Description**: Part of 105-skill plugin with axe-core, WCAG 2.2, keyboard navigation
- **Repository status**: Active, 1467 commits, MIT license
- **Skill path**: Not found at expected raw paths
- **SKILL.md**: Not directly accessible via raw.githubusercontent.com
- **Security**: Has CONTRIBUTING.md, SECURITY.md, gitleaks config
- **Network requirements**: Telemetry hooks exist but are opt-in (no default remote)
- **Decision**: READ-ONLY_EVALUATION — repo confirmed, skill file structure differs

### Candidate C: visual-regression-tester
- **Repository**: patricio0312rev/skills (confirmed exists, 52 stars)
- **Description**: Playwright/Chromatic visual regression with diff detection, CI integration
- **Repository status**: Active, 162 commits, MIT license
- **Skill path**: `testing/visual-regression-tester/SKILL.md` — CONFIRMED ACCESSIBLE
- **SKILL.md**: FULLY READ — contains Playwright config, component tests, responsive tests, dark mode, CI
- **Security**: No SECURITY.md, standard GitHub setup
- **Network requirements**: None in skill
- **Decision**: READ-ONLY_EVALUATED — full SKILL.md reviewed

## SKILL.md Content Summary — visual-regression-tester

Key capabilities documented:
- Playwright visual testing with `toHaveScreenshot()`
- Snapshot configuration (maxDiffPixels, maxDiffPixelRatio, threshold)
- Component-level visual tests (buttons, forms, inputs)
- Responsive multi-viewport testing
- Dark mode testing
- Animation disabling for stability
- CI integration (GitHub Actions)
- Baseline update workflow
- Chromatic integration
- Best practices: stable selectors, waitForLoadState, data-testid

## Security Audits

All three repositories are open-source on GitHub with permissive licenses:
- borghei/Claude-Skills: MIT + Commons Clause
- yonatangross/orchestkit: MIT
- patricio0312rev/skills: MIT

No Gen-Agent-Trust-Hub FAIL or Critical findings identified for the specific skill repositories. The orchestkit repo has opt-in telemetry that defaults to OFF.

## Installation Decision

**DO NOT INSTALL** — Read-only evaluation sufficient.

Rationale:
1. The project already has a complete local Playwright infrastructure (playwright.config.js, conftest.py, axe.min.js)
2. The visual-regression-tester SKILL.md content has been fully reviewed and its best practices can be applied
3. The other two skill SKILL.md files could not be directly accessed (repository structure differs)
4. No skill offers functionality that the existing project infrastructure doesn't already provide
5. Installation via `npx skills add` may introduce uncontrolled dependencies
6. Skills must not alter product dependencies or release artifacts

## Skill Integrity Manifest

```json
{
  "search_date": "2026-07-31",
  "searched_on": "skills.sh, github.com",
  "candidates_evaluated": 3,
  "skills_fully_read": 1,
  "skills_partially_evaluated": 2,
  "skills_installed": 0,
  "skills_rejected_for_installation": 3,
  "rejection_reasons": [
    "Existing local infrastructure sufficient",
    "SKILL.md not accessible for 2 of 3 candidates",
    "Installation scope unclear for npx skills add",
    "No additional capability beyond project's own tooling"
  ],
  "adopted_best_practices": [
    "Animation disabling for stable screenshots (from visual-regression-tester)",
    "Multi-viewport testing awareness",
    "Baseline snapshot naming convention",
    "Wait for network idle before screenshots"
  ]
}
```
