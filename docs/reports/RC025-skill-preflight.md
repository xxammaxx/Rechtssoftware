# RC-025 Skill Preflight Report

**Generated:** 2026-08-02
**Skills CLI:** 1.5.21 (vercel-labs/skills@1164afa5f0e21ebd01e6fc11249759353f494ad1)
**Source:** obra/superpowers@44c9b2d6e889982ac18c27d05a19fefe335194e1

## C1. Skill Inventory

### Pre-Installation State
| Location | Status |
|----------|--------|
| `.agents/skills/` | Did not exist |
| `.opencode/skills/` | Did not exist |
| `.hermes/skills/` | Did not exist (project-local) |
| `skills-lock.json` | Did not exist |
| Global Hermes skills | `~/.hermes/skills/` — 20 skill bundles (read-only, not relevant) |
| N8N project skills | `.agents/skills/` — byte-identical copies of same source |

### Kollisionsprüfung
No collisions detected. No pre-existing project-local skills in Rechtssoftware.

## C2. Gepinnter Installer
- CLI version: 1.5.21 ✓
- Node runtime: v22.22.0 ✓ (≥22.20.0)
- Source verified: `vercel-labs/skills@1164afa5f0e21ebd01e6fc11249759353f494ad1`
- Note: The `npx skills@1.5.21 add` command failed to clone by commit hash (treated as branch name). Manual installation via clone+copy was performed instead, with byte-identical verification against the source.

## C3. Installierte Skills

| Skill | Source | Files | Status |
|-------|--------|-------|--------|
| test-driven-development | obra/superpowers@44c9b2d | 2 (SKILL.md, writing-good-tests.md) | ✓ |
| systematic-debugging | obra/superpowers@44c9b2d | 12 (SKILL.md + 11 support files) | ✓ |
| verification-before-completion | obra/superpowers@44c9b2d | 1 (SKILL.md) | ✓ |

## C4. Installationsverifikation

### 4.1 File listing
All 15 files across 3 skill directories accounted for. ✓

### 4.2-4.3 SHA-256 / Byte Identity
All 15 files match source at `44c9b2d6e889982ac18c27d05a19fefe335194e1` with 100% byte identity. See `skills-lock.json` for complete hash listing. ✓

### 4.4 YAML Frontmatter
All three SKILL.md files contain valid YAML frontmatter with `name` and `description` fields. ✓

### 4.5 Discovery
Skills are discovered by Hermes (loaded at session start) and accessible via `skill_view()`. ✓

### 4.6 Activation
All three skills loaded successfully and their content verified against source. ✓

### 4.7 Resource Resolution
Support files (writing-good-tests.md, root-cause-tracing.md, etc.) are present and resolve correctly relative to their SKILL.md. ✓

### 4.8 Collision Exclusion
No naming collisions with existing project skills (none existed). ✓

### 4.9 skills-lock.json
Created with source, commit, path, and SHA-256 for every file. ✓

## C5. Nicht installierte Skills

| Skill | Reason |
|-------|--------|
| web-design-guidelines | Lädt Remote-URL bei jeder Nutzung — widerspricht gepinnter, offline-reproduzierbarer Basis |
| requesting-code-review | Unabhängiger Review-Agent bereits vorhanden; zusätzliche Anleitung ersetzt keine technische Trennung Builder/Verifier |

## Classification: `GREEN_SKILL_INSTALLED_AND_VERIFIED`
