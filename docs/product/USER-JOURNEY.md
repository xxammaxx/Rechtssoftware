# User Journey — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**Source:** Live application exploration

## Primary Journey: "I received an official letter with a deadline"

### 1. Landing & Orientation
- User arrives at case list (Fälle)
- Sees brand, "Nur lokale Verarbeitung" badge, and legal disclaimer
- **Observation:** Clear trust signals immediately visible. No cognitive load.

### 2. Case Creation
- Clicks "+ Neuen Fall anlegen"
- Fills case title (only field shown)
- Saves — redirected to case detail
- **Observation:** Minimal friction. Good for quick capture.

### 3. Document Upload
- On case detail, uses PDF upload form
- Selects file from local filesystem
- Clicks "Hochladen"
- Sees document appear in list
- **Observation:** File type and size constraints clearly displayed (20 MB limit, PDF only)

### 4. Document Review
- Clicks document in list
- Sees extracted text, deadline candidates (2 found)
- Warning box clearly states: no legal calculation performed, human review required
- **Observation:** Warning hierarchy very effective. User cannot miss the disclaimer.

### 5. Deadline Candidate Inspection
- Clicks candidate (e.g., "15. Juli 2026")
- Sees: recognized date, source provenance, full confirmation history
- Table shows all previous actions (confirmed, corrected, revoked)
- Can confirm, correct, or revoke the date
- **Observation:** History tracking is excellent. Full audit trail.

### 6. Legal Context (Optional)
- Navigates to legal sources via breadcrumbs/search
- Searches for relevant norms
- Links norms to case on legal situation page
- **Observation:** This path is not well-connected to the case workflow. User must discover it.

### 7. Timeline & Evidence
- Views legal timeline — sees events and candidates
- Opens evidence pack — sees structured case summary
- **Observation:** Evidence pack is comprehensive but all sections empty without data.

### Key Friction Points

1. **No main navigation** — User navigates via breadcrumbs and back links only. Hard to discover legal sources, timeline, evidence pack from case view.
2. **Disconnected sections** — Case, documents, legal sources, and timeline feel like separate apps.
3. **Empty states lack guidance** — Legal sources, timeline, evidence pack show empty headings without onboarding text.
4. **No case-level navigation tabs** — Must use breadcrumbs to move between case sections.
