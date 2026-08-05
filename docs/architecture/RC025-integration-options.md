# RC-025 Integration Options

**Generated:** 2026-08-02
**Status:** Documentation only — no integration during RC-025

## Document Pipeline (CT 113)
- **Location:** Proxmox LXC, 192.168.1.245
- **Potential:** Local OCR provider for scanned documents
- **Integration model:** Narrow adapter — PDF/Scan → local OCR job → text + provenance + confidence
- **NOT to integrate:** Translation functions, cloud components, LLM outputs as legal truth, direct database coupling
- **Decision:** Deferred; would need API endpoint on CT 113 and adapter in Rechtssoftware

## BescheidPilot
- **Status:** Not found on local filesystem
- **Potential:** High domain overlap (government correspondence, local document analysis)
- **Integration model:** No repo merge; compare domain models, document identity, OCR/extraction pipeline, findings/provenance, case boundaries, audit history, UI workflows
- **Possible future:** Shared local document analysis library, narrow CLI/file adapter, or deliberately separate products
- **Decision:** Deferred; requires BescheidPilot code access

## GHIW / n8n GitHub Issue Worker
- **Location:** `/media/xxammaxx/projekte/N8N/Github issue worker`
- **Potential:** External development/build orchestration
- **Integration model:** Not integrated into product code; no case data or documents sent to n8n
- **Decision:** External tool only; no product integration

## OpenCode-Agenten-Ökosystem / Hermes
- **Status:** Already represented in project governance (AGENTS.md, WORKING-METHOD.md, ecosystem.manifest.json)
- **Decision:** No further file copies; only consume pinned, minimal, project-relevant capabilities (see Phase C)
- **Active skills:** test-driven-development, systematic-debugging, verification-before-completion

## Odysseus / RAG
- **Status:** No codebase access
- **Potential:** LLM/RAG outputs risk deterministic, provenance-based, human-reviewed product boundary
- **Decision:** Not integrated; possible future as clearly separated, non-binding research interface
- **Gate:** STOP_INTEGRATION_OWNER_DECISION_REQUIRED before any implementation
