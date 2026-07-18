# Security Requirements Quality Checklist — M2 Document Import

**Purpose:** Validate that security requirements in the M2 spec/plan are complete, clear, consistent, measurable, and cover all relevant attack surfaces.
**Created:** 2026-07-18

## Requirement Completeness

- [ ] CHK001 - Are magic bytes MIME validation requirements specified for both the API routing layer AND the domain entity validation? [Completeness, Spec §FR-M2-003] — Spec mentions magic bytes (FR-M2-003, US1) but does not clarify which layer(s) perform the check. Gap: layer responsibility undefined.
- [ ] CHK002 - Are file storage security requirements (filesystem permissions, access control to the documents directory) explicitly documented? [Completeness, Gap] — Plan mentions "Keine Ausführung von Uploads" and research suggests chmod 0o644. Spec does not address filesystem permissions for documents/ directory.
- [ ] CHK003 - Are input sanitization requirements for filenames (special characters, length limits, extension stripping) documented? [Completeness, Gap] — Data model says max 255 chars. FR-M2-013 prevents path traversal. No spec requirement for special chars, Unicode, or double extensions.
- [ ] CHK004 - Are requirements for orphan file cleanup or periodic garbage collection defined for failure scenarios beyond the compensating delete? [Completeness, Gap] — FR-M2-016 covers compensating delete for upload flow. No periodic cleanup or GC for other failure modes.
- [ ] CHK005 - Are requirements for error message content (no sensitive data leakage, no internal paths in error responses) specified? [Completeness, Gap] — FR-M2-017 covers logging but not API error response content. Contracts show codes like CASE_NOT_FOUND but no spec requirement about error safety.
- [ ] CHK006 - Are download endpoint security requirements (path traversal prevention during file retrieval) explicitly specified? [Completeness, Gap] — Download reuses same LocalFileStorage with path traversal prevention (FR-M2-013, T006). No download-specific security requirements documented.
- [x] CHK007 - Are requirements for secure deletion of files when a case is removed (future-proofing) documented? [Completeness, Gap] — "Löschen von Dokumenten" is explicitly excluded in Abgrenzung. Intentional out-of-scope for M2.

## Requirement Clarity

- [ ] CHK008 - Is "Dateien nicht ausführbar speichern" (FR-M2-014) specified with a concrete mechanism (e.g., file mode 0644, no execution bits, storage format without executable headers)? [Clarity, Spec §FR-M2-014] — Research mentions chmod 0o644 on POSIX. Plan says "Keine Ausführung von Uploads" without mechanism. Spec FR only states the goal.
- [ ] CHK009 - Is "Kein In-Path-Traversal" (FR-M2-013) specified with the exact sanitization mechanism (e.g., `Path(name).name` extraction, denial of path separators)? [Clarity, Spec §FR-M2-013] — Research details `Path(name).name` approach. Plan says "UUID-basierte Speicherpfade". Spec FR only states the constraint.
- [x] CHK010 - Is "Metadata-only Logging" (FR-M2-017) clearly scoped — which fields are explicitly excluded (filename, storage_path) vs. allowed (document_id, case_id, status, duration)? [Clarity, Spec §FR-M2-017] — FR-M2-017 explicitly lists allowed fields and explicitly excludes filenames, paths, PII. Clarify session confirms. Well-scoped.
- [ ] CHK011 - Is the 20 MB size limit specified as a pre-upload check (Content-Length header) or a post-upload check (actual bytes read)? [Clarity, Spec §FR-M2-004] — Research mentions both domain-level and API-level checks. Spec does not specify timing of the size check.
- [ ] CHK012 - Is "UUID-basierte Speicherpfade (kein Path Traversal)" in the plan Sicherheit section specified with the exact implementation pattern? [Clarity, Plan §Sicherheit] — Plan states UUID-based paths prevent traversal. Research gives exact pattern `Path(name).name`. Not in spec or plan explicitly.
- [ ] CHK013 - Is the MIME validation order clarified — is the magic bytes check performed BEFORE or AFTER the Content-Type header check? [Clarity, Spec §FR-M2-003] — Spec requires magic bytes per clarify session. No order relative to Content-Type header is defined.
- [ ] CHK014 - Is the compensating delete (FR-M2-016) scoped to clarify which specific error conditions trigger the file deletion (all DB exceptions vs. specific ones)? [Clarity, Spec §FR-M2-016] — Spec says "bei DB-Fehler" which is broad. Not scoped to specific exception types.

## Requirement Consistency

- [x] CHK015 - Is MIME validation consistently specified between User Story 1 acceptance criteria ("Magic-Bytes-Prüfung: %PDF-Header in ersten 5 Bytes") and FR-M2-003? [Consistency, Spec §US-1] — Both reference magic bytes inspection consistently. No conflict.
- [x] CHK016 - Are security requirements in the plan's "Sicherheit" section consistent with the functional requirements in the spec (no contradictions, no duplicates with different wording)? [Consistency, Spec §Sicherheit vs. Plan §Sicherheit] — Plan Sicherheit (7 bullets) maps to FR-M2-003/004/005/006/013/014/016/017. Consistent.
- [x] CHK017 - Does the spec's "Abgrenzung" section consistently exclude all security mechanisms not implemented (e.g., encryption, authentication) without contradicting other sections? [Consistency, Spec §Abgrenzung] — Abgrenzung excludes OCR, classification, previews, delete, batch, non-PDF. No contradictions with FRs or plan.

## Acceptance Criteria Quality

- [ ] CHK018 - Does User Story 1 include an acceptance criterion for path traversal resistance, or is this only specified in the FR table? [Acceptance Criteria, Spec §US-1] — Path traversal (FR-M2-013) is NOT in US1 acceptance criteria. Only in FR table. Gap.
- [x] CHK019 - Are acceptance criteria for security failure scenarios (MIME rejection, size rejection, path traversal attempt) objectively measurable rather than relying on ambiguous terms? [Acceptance Criteria, Spec §US-1] — "Nicht-PDF abgelehnt" → HTTP 400 measurable. "20 MB begrenzt" → measurable. Terms are concrete.
- [ ] CHK020 - Is there a measurable acceptance criterion for logging compliance (e.g., "logs must contain operation type and IDs but never filenames")? [Acceptance Criteria, Gap] — FR-M2-017 exists as a spec requirement but is not an acceptance criterion in any user story. No testable logging criterion.
- [x] CHK021 - Can "Dateien nicht ausführbar speichern" be objectively verified in acceptance tests? [Acceptance Criteria, Spec §FR-M2-014] — On POSIX: check file mode (no +x). On Windows: inherently no-op. Verifiable.

## Scenario Coverage

- [x] CHK022 - Are security requirements specified for the download endpoint equivalent to those for upload (path traversal prevention, access control)? [Coverage, Gap] — Download reuses LocalFileStorage with same path traversal protection. Access control not applicable (single-user, no auth in M2 scope). Covered by FR-M2-013.
- [x] CHK023 - Are security requirements for the list endpoint specified (e.g., no information disclosure of file paths via list responses)? [Coverage, Gap] — List returns metadata (IDs, names, types, sizes, timestamps). No storage paths exposed. Single-user tool. Covered by design.
- [ ] CHK024 - Are requirements defined for handling files whose content-type header is missing or `application/octet-stream`? [Coverage, Gap] — Spec does not define what happens when Content-Type is missing, null, or application/octet-stream. The clarify session specifies magic bytes as primary check, but the handling of Content-Type absence is not addressed.
- [ ] CHK025 - Are requirements defined for cases where magic bytes indicate PDF but Content-Type header does not? [Coverage, Gap] — No requirements for this conflict scenario. Which check takes precedence? Not specified.

## Edge Case Coverage

- [x] CHK026 - Are requirements defined for handling files at the exact boundary size (20 MB, 0 bytes, 1 byte)? [Edge Case, Spec §FR-M2-004] — Document entity validates >0 and ≤20MB. All common boundary cases covered.
- [x] CHK027 - Are requirements defined for filenames containing path traversal sequences (e.g., `../../etc/passwd`, `..\\..\\file`)? [Edge Case, Gap] — FR-M2-013 + Plan: UUID-based paths + `Path(name).name` extraction inherently prevents traversal. Covered implicitly.
- [ ] CHK028 - Are requirements defined for files with no filename extension or with double extensions (e.g., `document.pdf.exe`)? [Edge Case, Gap] — Filename is stored as-is per FR-M2-007. No requirements for extension validation or stripping.
- [ ] CHK029 - Are requirements defined for the storage directory (`PLN_DATA_DIR/documents/`) not being writable or missing? [Edge Case, Gap] — Plan says mkdir on init (T006). No error handling for write failures specified.
- [x] CHK030 - Are requirements defined for zero-byte file uploads? [Edge Case, Gap] — Document entity validates size_bytes > 0. Zero-byte uploads are rejected. Covered.
- [x] CHK031 - Are requirements defined for concurrent upload attempts to the same case? [Edge Case, Gap] — Single-user local app. UUID-based filenames prevent collisions. Risk documented in plan §Risiken. Covered.
- [ ] CHK032 - Are requirements defined for files with Unicode or control characters in the filename? [Edge Case, Gap] — No requirements for Unicode normalization, control character filtering, or encoding handling in filenames.
- [ ] CHK033 - Are requirements defined for the server running out of disk space during a file write? [Edge Case, Gap] — No requirements for disk-full scenario handling or graceful error reporting.

## Non-Functional Security Requirements

- [x] CHK034 - Are data-at-rest security requirements specified (disk encryption expectation for PLN_DATA_DIR)? [Non-Functional, Gap] — Constitution §1 (local-only) and §2 (privacy by design) imply local storage security. M2 features document storage, not encryption. Encryption is out of scope for M2 per architecture.
- [x] CHK035 - Are compliance requirements for stored legal document retention and integrity specified? [Non-Functional, Gap] — Out of scope for M2. M2 covers storage and retrieval only. Compliance (retention, integrity) would be addressed in later milestones.
- [ ] CHK036 - Are availability requirements for the document storage defined (e.g., what happens if disk is full)? [Non-Functional, Gap] — No availability or disk-space requirements for the document storage subsystem.

## Dependencies & Assumptions

- [x] CHK037 - Is the assumption that `PLN_DATA_DIR` resides on a locally secured filesystem documented? [Assumption, Gap] — Project architecture (modular monolith, local-only) and Constitution §1/§2 establish the local-security context. Implicitly documented.
- [ ] CHK038 - Is the dependency on sufficient disk space for document storage documented? [Dependency, Gap] — No documentation of disk space requirements or assumptions for document storage.
- [x] CHK039 - Is the assumption that only a single user accesses the system (no concurrency threats) explicitly stated in security context? [Assumption, Gap] — Single-user tool per project scope. Plan §Risiken mentions "Single-User-Szenario" for concurrency risks. Documented.

## Ambiguities & Conflicts

- [ ] CHK040 - Does the spec clarify whether MIME validation happens at the API layer (FastAPI route) or the domain layer (Document entity) or both? [Ambiguity, Spec §FR-M2-003] — Spec mentions magic bytes validation (FR-M2-003, US1) but does not assign responsibility to a specific architectural layer. Both layers are plausible.
- [ ] CHK041 - Is "Keine Ausführung von Uploads" (Plan §Sicherheit) implementable without specifying the mechanism (e.g., noexec mount, file mode, AV scanning)? [Ambiguity, Plan §Sicherheit] — Plan states the constraint. Research clarifies with chmod 0o644 (POSIX). Not in spec or plan explicitly. Gap between plan and verifiable mechanism.
- [x] CHK042 - Is there a potential conflict between "Dateien außerhalb der DB speichern" and future data integrity requirements (backup, export)? [Conflict, Spec §FR-M2-005] — Intentional design decision documented in research (file storage outside DB for performance, no blobs in DB). Not a conflict — backup strategies can handle both DB + filesystem.
