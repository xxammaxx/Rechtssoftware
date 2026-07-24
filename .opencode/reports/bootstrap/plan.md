# Bootstrap Plan

- Classification: `AMBER_REVIEW`
- Apply requested: yes
- Remote CI requested: no

## Files

- `opencode.jsonc` (merge-config)
- `AGENTS.md` (merge-doc)
- `CONTRIBUTING.md` (merge-doc)
- `SECURITY.md` (merge-doc)
- `.hermes.md` (create-doc)
- `.hermes\README.md` (create-doc)
- `.hermes\skills\README.md` (merge-doc)
- `.hermes\bundles\project-bootstrap.json` (write-json)
- `.hermes\mcp\opencode-gateway.md` (create-doc)
- `.opencode\agents\architecture-agent.md` (sync-tree)
- `.opencode\agents\compliance-agent.md` (sync-tree)
- `.opencode\agents\documentation-agent.md` (sync-tree)
- `.opencode\agents\issue-orchestrator.md` (sync-tree)
- `.opencode\agents\migration-agent.md` (sync-tree)
- `.opencode\agents\playwright-agent.md` (sync-tree)
- `.opencode\agents\research-agent.md` (sync-tree)
- `.opencode\agents\review-agent.md` (sync-tree)
- `.opencode\agents\security-agent.md` (sync-tree)
- `.opencode\agents\ux-review-agent.md` (sync-tree)
- `.opencode\skills\anti-fake-execution\SKILL.md` (sync-tree)
- `.opencode\skills\architecture-review\SKILL.md` (sync-tree)
- `.opencode\skills\audit-trail-enforcer\SKILL.md` (sync-tree)
- `.opencode\skills\checkpoint-and-rollback\SKILL.md` (sync-tree)
- `.opencode\skills\context-engineering\SKILL.md` (sync-tree)
- `.opencode\skills\funding-document-generator\SKILL.md` (sync-tree)
- `.opencode\skills\github-source-of-truth\SKILL.md` (sync-tree)
- `.opencode\skills\hermes-handoff\SKILL.md` (sync-tree)
- `.opencode\skills\living-truth-mirror\SKILL.md` (sync-tree)
- `.opencode\skills\mcp-selection\SKILL.md` (sync-tree)
- `.opencode\skills\migration-review\SKILL.md` (sync-tree)
- `.opencode\skills\owner-approval-gate\SKILL.md` (sync-tree)
- `.opencode\skills\playwright-visual-review\SKILL.md` (sync-tree)
- `.opencode\skills\privacy-data-minimization\SKILL.md` (sync-tree)
- `.opencode\skills\project-bootstrap\SKILL.md` (sync-tree)
- `.opencode\skills\project-reality-refresh\SKILL.md` (sync-tree)
- `.opencode\skills\provider-neutral-config\SKILL.md` (sync-tree)
- `.opencode\skills\read-before-sketch\SKILL.md` (sync-tree)
- `.opencode\skills\remote-ci-approval-gate\SKILL.md` (sync-tree)
- `.opencode\skills\risk-tier-routing\SKILL.md` (sync-tree)
- `.opencode\skills\run-card\SKILL.md` (sync-tree)
- `.opencode\skills\security-evidence-gate\SKILL.md` (sync-tree)
- `.opencode\skills\spec-driven-development\SKILL.md` (sync-tree)
- `.opencode\skills\test-enforcement\SKILL.md` (sync-tree)
- `.opencode\skills\tierheim-compliance\SKILL.md` (sync-tree)
- `.opencode\skills\ui-design-system-review\SKILL.md` (sync-tree)
- `.opencode\skills\ux-flow-review\SKILL.md` (sync-tree)
- `.opencode\skills\verification-contract\SKILL.md` (sync-tree)
- `.opencode\skills\worktree-safety\SKILL.md` (sync-tree)
- `.opencode\policies\data-retention.json` (sync-tree)
- `.opencode\policies\evidence-gates.json` (sync-tree)
- `.opencode\policies\mcp-trust-tiers.json` (sync-tree)
- `.opencode\policies\model-routing.json` (sync-tree)
- `.opencode\policies\working-method.json` (sync-tree)
- `.opencode\policies\write-protection.json` (sync-tree)
- `.opencode\templates\adr-template.md` (sync-tree)
- `.opencode\templates\funding-proposal-template.md` (sync-tree)
- `.opencode\templates\issue-task-template.md` (sync-tree)
- `.opencode\templates\migration-template.sql` (sync-tree)
- `.opencode\templates\release-notes-template.md` (sync-tree)
- `.opencode\templates\security-report-template.md` (sync-tree)
- `.opencode\validation\schema-validators\ecosystem-manifest-schema.json` (sync-tree)
- `.opencode\validation\schema-validators\migration-schema.json` (sync-tree)
- `.opencode\validation\schema-validators\security-report-schema.json` (sync-tree)
- `.opencode\validation\schema-validators\speckit-spec-schema.json` (sync-tree)
- `.opencode\prompts\compliance-check.txt` (sync-tree)
- `.opencode\prompts\funding-generator.txt` (sync-tree)
- `.opencode\prompts\migration-review.txt` (sync-tree)
- `.opencode\prompts\security-review.txt` (sync-tree)
- `.opencode\prompts\spec-constitution.txt` (sync-tree)
- `.opencode\prompts\spec-implement.txt` (sync-tree)
- `.opencode\prompts\spec-plan.txt` (sync-tree)
- `.opencode\prompts\spec-specify.txt` (sync-tree)
- `.opencode\prompts\spec-tasks.txt` (sync-tree)
- `.opencode\prompts\visual-review.txt` (sync-tree)
- `.opencode\hooks\audit-log.sh` (sync-tree)
- `.opencode\hooks\post-commit.sh` (sync-tree)
- `.opencode\hooks\post-edit.sh` (sync-tree)
- `.opencode\hooks\pre-commit.sh` (sync-tree)
- `.opencode\hooks\pre-edit.sh` (sync-tree)
- `.opencode\hooks\pre-task.sh` (sync-tree)

## Selected Skills

- `project-reality-refresh`
- `context-engineering`
- `run-card`
- `risk-tier-routing`
- `verification-contract`
- `anti-fake-execution`
- `worktree-safety`
- `checkpoint-and-rollback`
- `owner-approval-gate`
- `privacy-data-minimization`
- `living-truth-mirror`
- `provider-neutral-config`
- `project-bootstrap`
- `mcp-selection`
- `hermes-handoff`
- `playwright-visual-review`
- `migration-review`

## Selected MCPs

- `github` (0_readonly) - disabled
- `context7` (0_readonly) - disabled
- `playwright` (1_sandboxed) - disabled
- `sqlite` (1_sandboxed) - disabled

## Backup

- Backup root: `C:\Rechtssoftware\.opencode\backups\bootstrap-2026-07-24T09-26-23-762Z`
- Rollback command: `node scripts/bootstrap-project.mjs --target "C:\\Rechtssoftware" --rollback "C:\\Rechtssoftware\\.opencode\\backups\\bootstrap-2026-07-24T09-26-23-762Z"`

## Conflicts

- existing file will be merged: opencode.jsonc (OpenCode config)
- existing file preserved: AGENTS.md (AGENTS.md managed section)
- existing file preserved: CONTRIBUTING.md (CONTRIBUTING.md managed section)
- existing file preserved: SECURITY.md (SECURITY.md managed section)
- existing file preserved: .hermes.md (Hermes handoff)
- existing file preserved: .hermes\README.md (Hermes README)
- existing file preserved: .hermes\skills\README.md (Hermes skills README)
- existing file preserved: .hermes\bundles\project-bootstrap.json (Hermes bundle)
- existing file preserved: .hermes\mcp\opencode-gateway.md (Hermes MCP gateway note)
- existing file preserved: .opencode\agents\issue-orchestrator.md
- existing file preserved: .opencode\skills\anti-fake-execution\SKILL.md
- existing file preserved: .opencode\skills\architecture-review\SKILL.md
- existing file preserved: .opencode\skills\audit-trail-enforcer\SKILL.md
- existing file preserved: .opencode\skills\context-engineering\SKILL.md
- existing file preserved: .opencode\skills\funding-document-generator\SKILL.md
- existing file preserved: .opencode\skills\github-source-of-truth\SKILL.md
- existing file preserved: .opencode\skills\migration-review\SKILL.md
- existing file preserved: .opencode\skills\owner-approval-gate\SKILL.md
- existing file preserved: .opencode\skills\playwright-visual-review\SKILL.md
- existing file preserved: .opencode\skills\privacy-data-minimization\SKILL.md
- existing file preserved: .opencode\skills\risk-tier-routing\SKILL.md
- existing file preserved: .opencode\skills\security-evidence-gate\SKILL.md
- existing file preserved: .opencode\skills\spec-driven-development\SKILL.md
- existing file preserved: .opencode\skills\test-enforcement\SKILL.md
- existing file preserved: .opencode\skills\tierheim-compliance\SKILL.md
- existing file preserved: .opencode\skills\verification-contract\SKILL.md
