# Product Context — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**Candidate:** 6a62460aaa798ede5784f07ac39a51953db5a0dd
**Source:** Live application exploration + RC-017 visible E2E evidence

## What is PrivateLegalNavigator?

A local, privacy-first legal assistance tool for German law. Server-side rendered web application
(FastAPI + Jinja2) running entirely on the user's machine. No cloud, no telemetry, no external
dependencies at runtime.

## Core Capabilities

1. **Case Management** — Create and track legal cases locally
2. **Document Processing** — Upload PDFs, extract text, detect deadline candidates
3. **Reference Events** — Confirm, correct, revoke extracted dates; full history
4. **Legal Sources** — Import and search German federal law (Gesetze im Internet)
5. **Legal Timeline** — Track legal events per case (document received, objection filed, etc.)
6. **Evidence Pack** — Export a structured overview of a case's legal state
7. **Calendar Arithmetic** — Calculate deadlines from reference events (preview)

## Target Users (Inferred)

- **Citizens** navigating administrative/legal processes independently
- **Small practitioners** needing a structured case tracker without cloud risk
- **Self-represented parties** who need to understand deadlines and legal context

## Privacy & Trust Model

- Local SQLite storage — no data leaves the machine
- No authentication (single local user)
- No telemetry, analytics, or external calls at runtime
- "Nur lokale Verarbeitung" badge visible on every page
- Legal disclaimer on every page: "Rechtliche Gültigkeit nicht bewertet"

## Technical Architecture

- FastAPI application with Jinja2 server-side templates
- Application-layer orchestrator pattern (no direct DB from routes)
- CSRF protection on all mutating operations
- Input validation and size limits on uploads
- SQLite with FTS5 for legal text search
- Wheel-based distribution with Windows scripts
