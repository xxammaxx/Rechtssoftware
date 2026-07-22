# ADR-007 — Legal Source Provenance and Corpus Foundation (M7-A)

**Status:** Accepted

**Date:** 2026-07-22

**Deciders:** Architecture Agent (ADR-007)

## Context

M5 (deadline candidate extraction) and M6-A (confirmed reference events with calendar arithmetic)
established the document analysis pipeline: a user uploads a legal document, its text is
extracted, deadline candidates are detected, and reference dates are confirmed. However, the
system has no awareness of the *legal sources* that give meaning to these documents.

When a document cites "§ 70 VwGO" or "Art. 6 DSGVO", the system today cannot:
- Resolve the citation to the actual normative text
- Show which version of the law was in force at the time relevant to the case
- Trace the provenance of the legal text (was it from the official promulgation platform or a
  third-party consolidation?)
- Perform full-text search across legal provisions to help the user identify relevant norms

M7-A must establish the **legal source foundation**: a structured repository of legal norms
downloaded from publicly accessible sources, stored locally, with full provenance metadata,
version-awareness, and full-text search capability — all while maintaining the project's
constitutional constraints of local-only processing, no automated legal decisions, and
no cloud dependencies.

**Existing architecture that M7-A must integrate with:**

| Component | Role in M7-A |
|---|---|
| Modular monolith (ADR-001) | All legal source code extends existing layers: domain, application, infrastructure, api |
| SQLite database (`database.py`) | Legal source tables added to the existing `private_legal_navigator.db` |
| `Settings` (`config.py`) | Extended with legal source configuration paths |
| Layer isolation pattern | New domain entities, application ports, infrastructure adapters follow existing conventions |
| `pyproject.toml` | New dependency: `lxml >= 6.1.0` for secure XML processing |

**What does NOT yet exist** (from `m7a-reality-refresh.md`) and must be created:
- Legal source domain model (Source, Instrument, Provision, Expression, Snapshot)
- FTS5 full-text search table for provision texts
- Source synchronization pipeline (download → hash → store → parse → normalize)
- Secure XML parser with XXE/billion laughs protection
- HTTP client for fetching public legal materials (allowlist-restricted)
- Pluggable adapter interface for future legal source providers
- Authority tier classification system

**Key constraints from project constitution and prior ADRs:**
- All processing is local-only — no cloud OCR, no external runtime requests beyond the sources
- No automated legal decisions — the system retrieves and displays norms, never interprets them
- Human review is structurally enforced — norm relevance is user-confirmed, not machine-inferred
- All source data is public legal information — no personal data involved in sync
- Sync is a deliberate user action, not background processing
- Source authenticity metadata must be preserved at every pipeline stage

---

## Decision

We implement a **Legal Source Provenance and Corpus Foundation** built on ten architectural
sub-decisions, each grounded in the project's existing modular monolith architecture and
constitutional constraints.

---

### Decision 1: Modular Monolith Extension (No Microservices)

**All legal source code stays within the existing four-layer modular monolith.** No new
microservices, no separate databases, no additional processes.

**Components by layer:**

| Layer | New Modules |
|---|---|
| `domain/` | `legal_source.py` (Source, Instrument, Provision, Expression, Snapshot entities), `authority_tier.py` (AuthorityTier enum), `source_adapter.py` (LegalSourceAdapter protocol) |
| `application/` | `legal_source_service.py` (orchestration), `source_sync_service.py` (pipeline coordination), `legal_source_repository.py` (repository port / ABC) |
| `infrastructure/` | `sqlite_legal_source_repository.py`, `gii_adapter.py` (Gesetze im Internet), `gii_xml_parser.py`, `source_http_client.py` (allowlist-restricted), `snapshots_file_storage.py` |
| `api/` | `legal_source_routes.py` (search, browse, citation resolution) |

**Rationale:**
- ADR-001 established the modular monolith precisely to accommodate feature growth through
  layer extension. M7-A is a textbook case: new domain entities, new application services,
  new infrastructure adapters, new API routes — all within the proven four-layer pattern.
- The SQLite database is shared across modules (ADR-001, ADR-002, ADR-008). Legal source
  tables coexist with case, document, and reference event tables in `private_legal_navigator.db`,
  enabling direct joins between norms and case-legal links (ADR-008).
- No network overhead, no serialization costs, no distributed transaction complexity — all
  appropriate for a single-user local application.
- The app factory pattern (`app.py`) already supports dependency injection through
  `app.state`, making it straightforward to wire new services.

---

### Decision 2: SQLite as Primary Store with FTS5 Full-Text Search

**All legal source data is stored in the same SQLite database as cases.** The database schema
is extended with tables for sources, instruments, provisions, expressions, and snapshots.

**Full-text search uses SQLite FTS5** — a built-in SQLite module requiring no additional
dependencies. No Elasticsearch, no vector database, no Neo4j.

**Search priority order (strict):**

| Priority | Method | Cost | Latency |
|---|---|---|---|
| 1 (highest) | Exact citation resolution (`norm_citation` index lookup) | Indexed B-tree | <1ms |
| 2 | Exact abbreviation + paragraph match (`abbreviation` + `paragraph_marker` index) | Composite index | <1ms |
| 3 | Title search (`title` LIKE or FTS5) | FTS5 bm25 | ~2-10ms |
| 4 | Lexical full-text search (FTS5 on provision text) | FTS5 bm25 | ~5-20ms |
| 5 | Metadata filter fallback (authority tier, source, temporal range) | Indexed columns | <5ms |

**Schema design (core tables):**

```sql
-- Authority tier classification
CREATE TABLE IF NOT EXISTS legal_sources (
    source_id TEXT PRIMARY KEY,             -- UUID
    source_type TEXT NOT NULL,              -- 'gesetze_im_internet', 'bundesgesetzblatt', 'eur_lex', 'court_api'
    name TEXT NOT NULL,                     -- Human-readable source name
    authority_tier TEXT NOT NULL,           -- OFFICIAL_PROMULGATION, OFFICIAL_EU_PUBLICATION, etc.
    base_url TEXT NOT NULL,                 -- Root URL of the legal source
    last_synced_at TEXT,                    -- ISO datetime of last successful sync
    sync_status TEXT NOT NULL DEFAULT 'never_synced', -- never_synced, syncing, synced, error
    created_at TEXT NOT NULL
);

-- Individual legal instruments (laws, regulations, directives)
CREATE TABLE IF NOT EXISTS legal_instruments (
    instrument_id TEXT PRIMARY KEY,         -- UUID
    source_id TEXT NOT NULL REFERENCES legal_sources(source_id),
    abbreviation TEXT NOT NULL,             -- e.g., 'VwGO', 'BGB', 'DSGVO'
    full_title TEXT NOT NULL,               -- e.g., 'Verwaltungsgerichtsordnung'
    jurisdiction TEXT NOT NULL DEFAULT 'DE', -- ISO country code
    instrument_type TEXT NOT NULL,          -- 'federal_law', 'regulation', 'directive', 'treaty'
    official_citation TEXT,                 -- e.g., 'BGBl. I S. 686'
    first_published_at TEXT,               -- Date of first official publication
    created_at TEXT NOT NULL
);

-- Specific versions of an instrument (one instrument has many expressions)
CREATE TABLE IF NOT EXISTS instrument_expressions (
    expression_id TEXT PRIMARY KEY,         -- UUID
    instrument_id TEXT NOT NULL REFERENCES legal_instruments(instrument_id),
    version_label TEXT NOT NULL,            -- e.g., '2025-01-01', 'Neufassung 2024'
    published_at TEXT NOT NULL,             -- When this version was officially published
    valid_from TEXT,                        -- temporal validity start (may be NULL if unknown)
    valid_to TEXT,                          -- temporal validity end (NULL = currently in force)
    retrieved_at TEXT NOT NULL,             -- when WE downloaded it (ISO datetime UTC)
    snapshot_id TEXT NOT NULL REFERENCES raw_snapshots(snapshot_id),
    temporal_confidence TEXT NOT NULL DEFAULT 'best_effort', -- exact, inferred, best_effort, unknown
    authority_tier TEXT NOT NULL,           -- per-expression tier (may differ from source default)
    created_at TEXT NOT NULL
);

-- Individual provisions (paragraphs, articles)
CREATE TABLE IF NOT EXISTS legal_provisions (
    provision_id TEXT PRIMARY KEY,          -- UUID
    expression_id TEXT NOT NULL REFERENCES instrument_expressions(expression_id),
    norm_citation TEXT NOT NULL,            -- e.g., '§ 70', 'Art. 6', 'Abs. 1 Nr. 2'
    paragraph_marker TEXT NOT NULL,         -- parsed paragraph identifier for index lookup
    section_title TEXT NOT NULL DEFAULT '', -- e.g., 'Verwaltungsrechtsweg'
    provision_text TEXT NOT NULL,           -- full normative text
    sort_order INTEGER NOT NULL DEFAULT 0,  -- for maintaining structural order within expression
    created_at TEXT NOT NULL
);

-- The FTS5 virtual table for full-text search on provision texts
CREATE VIRTUAL TABLE IF NOT EXISTS provisions_fts USING fts5(
    provision_text,
    section_title,
    norm_citation,
    content='legal_provisions',
    content_rowid='rowid'
);
```

**Rationale:**
- SQLite is the established persistence layer for the entire project (ADR-001). Adding legal
  source tables to the same database enables direct SQL joins between norms and case-legal
  links (ADR-008, `case_legal_links.norm_id`), between snapshots and instruments, and
  between expressions and provisions. A separate database would require cross-database
  references that SQLite does not natively support well.
- FTS5 is built into SQLite — zero additional dependencies, zero operational complexity. For
  a single-user local application, FTS5's BM25 ranking is more than sufficient. It supports
  prefix queries, phrase queries, boolean operators, and snippet generation.
- The strict search priority ensures that exact citation lookups (the most common use case)
  never touch the FTS index — they resolve via B-tree index lookups in under a millisecond.
- Semantic/vector search is explicitly deferred to M7-E+ (if ever). Current M7-A scope is
  lexical search only. The architecture does not preclude adding a vector index later, but
  there is no justification for its complexity at this stage.
- FTS5 is synchronous by default — no index staleness, no separate sync process.

---

### Decision 3: Immutable Raw Snapshots with SHA-256 Hashing

**Every downloaded legal source file is stored unmodified before any parsing or
normalization.** A SHA-256 hash is computed at download time and stored alongside the
snapshot.

**Storage layout:**

```
PLN_DATA_DIR/
└── snapshots/
    └── {source_type}/           -- e.g., 'gesetze_im_internet', 'bundesgesetzblatt'
        └── {hash[:2]}/          -- Two-char hash prefix for directory sharding
            └── {hash}.xml       -- Full SHA-256 hash as filename
```

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS raw_snapshots (
    snapshot_id TEXT PRIMARY KEY,           -- UUID
    source_id TEXT NOT NULL REFERENCES legal_sources(source_id),
    storage_path TEXT NOT NULL,             -- relative path within PLN_DATA_DIR/snapshots/
    sha256_hash TEXT NOT NULL UNIQUE,       -- SHA-256 of the file content
    file_size_bytes INTEGER NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'application/xml',
    original_url TEXT NOT NULL,             -- the exact URL fetched
    downloaded_at TEXT NOT NULL,            -- ISO datetime UTC of download
    download_duration_ms INTEGER,           -- how long the fetch took
    http_status INTEGER,                    -- HTTP status code of the response
    http_etag TEXT,                         -- ETag header if provided
    http_last_modified TEXT,                -- Last-Modified header if provided
    is_normalized INTEGER NOT NULL DEFAULT 0, -- 1 = successfully normalized into corpus
    normalization_error TEXT,               -- error message if normalization failed
    created_at TEXT NOT NULL
);
```

**Invariant enforced at the service layer:** No code path exists that updates, deletes,
or truncates a raw snapshot file after download. The `raw_snapshots` table has no `UPDATE`
operations — only `INSERT`. Deletion is only through the user's right to erasure (via
`CASCADE` on source deletion).

**Rationale:**
- The raw snapshot is the **evidence** that a particular legal text was available at a
  particular URL on a particular date. Without it, the normalized corpus is an
  unverifiable claim.
- SHA-256 provides content-addressable storage: identical content produces identical hashes,
  enabling deduplication (the `UNIQUE` constraint on `sha256_hash` prevents storing the
  same file twice).
- The hash-as-filename pattern ensures that a file's identity is cryptographically bound to
  its content — tampering is detectable without a separate manifest.
- Directory sharding (first two hex characters of hash) prevents filesystem bottlenecks in
  the unlikely event of thousands of snapshots.
- The `is_normalized` flag is set to 1 **after** successful normalization (Decision 4).
  A snapshot with `is_normalized = 0` and a non-null `normalization_error` represents a
  parse failure that does not corrupt the corpus.

---

### Decision 4: Separate Normalization Pipeline Stages

**The pipeline from download to searchable corpus has four distinct stages, each with its
own failure boundary:**

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Download   │ ──► │   Parse     │ ──► │  Normalize   │ ──► │   Index     │
│  (fetch)    │     │  (XML→DOM)  │     │ (DOM→entities)│     │ (→FTS5)    │
└──────┬──────┘     └──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                   │                    │
       ▼                   ▼                   ▼                    ▼
  raw_snapshots        parser error       normalization          FTS5 rows
  (immutable)        logged, retryable    error logged,          committed
                                          raw snapshot          atomically
                                          preserved
```

**Stage 1 — Download:**
- HTTP GET from the source URL via the allowlist-restricted HTTP client
- Response body written directly to disk under `data_dir/snapshots/`
- SHA-256 hash computed on the saved file (not just the response bytes)
- `raw_snapshots` row INSERTed with `is_normalized = 0`

**Stage 2 — Parse:**
- Read raw snapshot from disk
- Apply secure XML parsing (Decision 8)
- Produce an in-memory DOM representation
- On parse failure: set `raw_snapshots.normalization_error`, log the error, do NOT modify
  the raw snapshot. Parsing can be retried with updated parser later.

**Stage 3 — Normalize:**
- Walk the DOM to extract instruments, expressions, provisions
- Apply normalization rules (whitespace collapse, structural hierarchy inference,
  citation extraction)
- Produce domain entity instances ready for persistence
- On normalization failure: set `raw_snapshots.normalization_error`, log the error, do NOT
  modify the raw snapshot. Normalization logic can be updated and retried.

**Stage 4 — Index:**
- INSERT normalized entities into `legal_instruments`, `instrument_expressions`,
  `legal_provisions`
- Trigger FTS5 index update (SQLite FTS5 is synchronous — content table changes
  automatically update the FTS index)
- Set `raw_snapshots.is_normalized = 1`
- All INSERTs happen in a single transaction — either all entities land or none do

**Rationale:**
- Each stage has a clean failure boundary. A parse error in Stage 2 does not prevent the
  raw snapshot from being preserved (Stage 1 already succeeded). A normalization error in
  Stage 3 does not corrupt the parsed DOM (Stage 2 succeeded). The index is only populated
  when all three prior stages complete without error.
- The raw snapshot is the source of truth for all downstream stages. If normalization logic
  is improved (e.g., better citation extraction regex), Stage 3 can be re-run against
  existing snapshots without re-downloading.
- The transactional unit at Stage 4 ensures that a partially-normalized corpus is never
  visible to queries — the FTS5 index is either complete or absent for a given snapshot.

---

### Decision 5: Authority Tier Classification System

**Every legal source and every instrument expression carries an authority tier.** The tier
is displayed prominently in the UI next to every provision citation.

**Tier definitions (StrEnum):**

| Tier | Value | Description | Examples |
|---|---|---|---|
| T0 | `OFFICIAL_PROMULGATION` | Official gazette — the authoritative publication with legal force | Bundesgesetzblatt (BGBl), Amtsblatt der EU |
| T1 | `OFFICIAL_EU_PUBLICATION` | Primary EU legal portal with official status | EUR-Lex (Official Journal) |
| T2 | `OFFICIAL_COURT_PUBLICATION` | Official court decision database | BVerfG, BGH, BVerwG official sites |
| T3 | `CONSOLIDATED_NON_OFFICIAL` | Consolidated text from an official provider, not the promulgation itself, may contain editorial changes | **Gesetze im Internet** (www.gesetze-im-internet.de), dejure.org |
| T4 | `SECONDARY_SOURCE` | Third-party legal commentary, database, or textbook | beck-online, juris commentary |
| T5 | `UNKNOWN` | Unverifiable or user-supplied source with no provenance metadata | User-uploaded norm text, undocumented source |

**Gesetze im Internet (GII) tier assignment:**
GII is the German federal government's free legal information service, operated jointly by
the Bundesministerium der Justiz and juris GmbH. Its "Impressum" explicitly states that
the texts are **non-authoritative consolidations** — only the Bundesgesetzblatt (BGBl)
carries legal force.

Therefore, GII receives **`CONSOLIDATED_NON_OFFICIAL` (T3)**. This is NOT a mark of
unreliability — GII is maintained diligently — but it is a truthful reflection of its
legal status: the consolidated text may contain editorial corrections and does not
constitute an official promulgation. Users must be aware that for legally binding
interpretation, the Bundesgesetzblatt is the authoritative source.

**Per-expression tier override:**
The `instrument_expressions.authority_tier` column allows per-expression overrides.
A source may default to T3, but a specific expression retrieved from that source could
be marked T0 if the source also hosts the official promulgation scan. The expression-level
tier takes precedence over the source-level tier in all UI displays.

**Rationale:**
- In legal work, the provenance of a text is as important as its content. A user citing
  § 70 VwGO must know whether they are reading the Bundesgesetzblatt promulgation (T0)
  or a consolidated version from GII (T3). The latter is fine for orientation but not
  necessarily identical to the official text.
- Displaying the tier next to every citation is a **product safety feature**: it prevents
  the user from unknowingly relying on a non-authoritative source.
- The six-tier system is deliberately coarse — fine-grained reputation scores or
  crowdsourced trust ratings are out of scope for M7-A and introduce complexity without
  clear benefit for a single-user tool.
- Future source adapters (Bundesgesetzblatt, EUR-Lex) will have different tier assignments,
  and the system handles this uniformly through the `authority_tier` column.

---

### Decision 6: No Claim of Historical Completeness

**The system CANNOT and MUST NOT claim to hold all historical versions of any legal
instrument. It stores only what was retrieved, with temporal metadata.**

**Temporal metadata model (`instrument_expressions`):**

| Field | Meaning | Source | Reliability |
|---|---|---|---|
| `published_at` | Date this version was officially published | Extracted from source metadata | **High** — usually explicit in the source |
| `valid_from` | Date this version became/will become legally effective | Extracted from source metadata if available | **Medium** — often explicit, sometimes implicit |
| `valid_to` | Date this version was superseded (NULL = currently in force) | Inferred from successor expression or NULL | **Low** — rarely explicit; usually inferred |
| `retrieved_at` | When WE downloaded this snapshot | System timestamp at download | **Absolute** — under our control |
| `temporal_confidence` | How reliable the temporal window is | Computed from metadata completeness | `exact`, `inferred`, `best_effort`, `unknown` |

**The `temporal_confidence` field enables honest UI display:**

| Confidence | UI Badge | Meaning |
|---|---|---|
| `exact` | "Version vom 01.01.2025" | Both valid_from and valid_to are explicit in the source |
| `inferred` | "Version vom 01.01.2025 (erschlossen)" | valid_from is explicit, valid_to is inferred from a successor |
| `best_effort` | "Version ca. 01.01.2025 (geschätzt)" | Dates are estimated from context (e.g., "letzte Änderung") |
| `unknown` | "Version unbekannt, abgerufen am 22.07.2026" | No temporal metadata available; only retrieved_at is reliable |

**Specifically prohibited:**
- No UI text saying "All versions available" or "Complete version history"
- No API response field implying version completeness
- No automated version gap detection (that would require knowing what versions *should* exist,
  which the system cannot know from consolidated sources alone)

**Rationale:**
- Consolidated sources like GII typically provide only the current version plus, optionally,
  a limited set of past versions. They do not provide a guaranteed complete version history.
- Claiming completeness when the source does not guarantee it is legally misleading and
  could cause a user to rely on incomplete information.
- The `temporal_confidence` field is the architecture's "honesty mechanism" — it forces
  every temporal claim to carry a confidence qualifier that the UI must display.
- `retrieved_at` is always available and always reliable (system timestamp). Even when all
  other temporal metadata is absent, the system can truthfully say "this text was the version
  available at the source on 2026-07-22."
- Future builds may add official Bundesgesetzblatt integration (T0), which would improve
  `temporal_confidence` for those sources. The architecture supports this without schema
  changes.

---

### Decision 7: Strict Isolation — No Case Data During Source Sync

**The source synchronization pipeline is architecturally isolated from all case-related
data. At no point during sync does the system read or transmit case IDs, document text,
personal data, or search queries from cases.**

**Concrete isolation measures:**

1. **Separate application service:** `SourceSyncService` is a dedicated service that
   orchestrates only the sync pipeline. It does not depend on `CaseService`,
   `DocumentService`, or any case-related repository. Its constructor receives only:
   - `LegalSourceRepository` (for legal source persistence)
   - `SourceHttpClient` (for fetching from allowlisted URLs)
   - `SnapshotsFileStorage` (for writing raw snapshots)

2. **No cross-joining during sync:** The SQL queries executed during sync reference only
   `legal_sources`, `raw_snapshots`, `legal_instruments`, `instrument_expressions`, and
   `legal_provisions`. They never JOIN with `cases`, `documents`, `deadline_candidates`,
   or `confirmed_reference_events`.

3. **HTTP requests contain zero case context:** The `SourceHttpClient` sends HTTP GET
   requests with only standard headers (User-Agent, Accept). No cookies, no case IDs in
   query parameters, no document metadata in headers. The URL is constructed purely from
   source configuration, never from user content.

4. **Log isolation:** Sync operations use a separate log prefix
   (`[SOURCE_SYNC]` vs `[CASES]`) and never include personal data in log messages.
   The `safe_log_event` pattern (from M6-A) is applied.

5. **No user search term retrieval from source:** When a user searches for a provision
   (e.g., "§ 70 VwGO"), the search is executed against the *local* SQLite database —
   the source server is never contacted during a search operation. The sync runs
   independently and on a different schedule.

**Rationale:**
- This is a **privacy-by-design** decision. Source synchronization is a bulk download of
  public legal materials — there is no conceivable reason for case data to enter the sync
  pipeline. Making the isolation structural (separate service, no shared query paths)
  prevents accidental leakage and makes the boundary auditable.
- The isolation also simplifies operational reasoning: sync can be debugged, tested, and
  verified without any case data present. A developer can run sync in a fresh database with
  no cases and get identical results.
- This decision directly supports the project's DSGVO posture (local-only, data minimization).
  Even though legal source data is public, the *act of fetching it* must not reveal anything
  about the user's cases.

---

### Decision 8: Secure XML Processing with Defense-in-Depth

**All XML from "Gesetze im Internet" and any future XML source must be parsed with a
layered security configuration that prevents XXE attacks, entity expansion bombs, and
denial-of-service through oversized input.**

**Parser configuration (`lxml`):**

```python
import lxml.etree as ET

def secure_parser() -> ET.XMLParser:
    """Return an lxml XMLParser configured for secure parsing of legal XML."""
    return ET.XMLParser(
        resolve_entities=False,          # No external entity resolution (XXE protection)
        no_network=True,                 # Prevent any network access during parsing
        dtd_validation=False,            # No DTD validation (avoids DTD-based attacks)
        load_dtd=False,                  # Do not load external DTD
        huge_tree=False,                 # Disable huge_tree to prevent billion laughs
        remove_blank_text=False,         # Preserve whitespace for legal text fidelity
    )

def parse_legal_xml(xml_bytes: bytes) -> ET._Element:
    """Parse legal XML with defense-in-depth protections."""
    if len(xml_bytes) > MAX_XML_SIZE_BYTES:  # 50 MB limit
        raise LegalXmlError(f"XML exceeds maximum size of {MAX_XML_SIZE_BYTES} bytes")
    try:
        return ET.fromstring(xml_bytes, parser=secure_parser())
    except ET.XMLSyntaxError as e:
        raise LegalXmlError(f"XML parse error: {e}") from e
```

**Security layers:**

| Layer | Protection | Attack Vector Blocked |
|---|---|---|
| `resolve_entities=False` | No entity resolution at all | XXE (XML External Entity) — arbitrary file read, SSRF |
| `no_network=True` | lxml blocks all network access during parsing | XXE-based SSRF, external DTD fetch for entity expansion |
| `load_dtd=False` | No external DTD loading | DTD-based entity definition injection |
| `huge_tree=False` | Limits parser memory by disabling deep tree optimizations | Billion laughs / XML bomb (exponential entity expansion) |
| Size limit (50 MB) | Hard cap on input before parsing starts | Resource exhaustion from oversized payloads |
| `dtd_validation=False` | No DTD-based validation | DTD-triggered parser behavior exploitation |

**DTD handling (when needed):**
If a future source requires DTD for structural validation, the DTD file must be:
1. Fetched once through the allowlist HTTP client (not during parsing)
2. SHA-256 hashed and pinned in source configuration
3. Stored locally in `data_dir/dtd/`
4. Loaded from the local copy using `etree.DTD(local_path)`, not referenced from XML
5. Validated at test time to ensure the pinned hash matches the current DTD content

**Rationale:**
- XML from government sources is generally well-formed and trustworthy, but the parser
  configuration is defense-in-depth — it must be secure against a compromised or
  misconfigured source server, a man-in-the-middle (despite HTTPS), or a maliciously
  crafted file placed in the snapshots directory.
- `lxml` is the standard Python XML library for production use. It wraps `libxml2`, which
  has had XXE vulnerabilities in the past. The `resolve_entities=False` flag is the
  recommended mitigation and is effective against all known XXE vectors when combined
  with `no_network=True`.
- The 50 MB size limit is generous for legal texts (the entire BGB as XML is well under
  10 MB) but prevents resource exhaustion from accidental or malicious oversized inputs.
- `remove_blank_text=False` preserves whitespace in legal provisions, which is semantically
  meaningful — line breaks and paragraph indentation in German legal texts often carry
  structural significance (Absatz, Satz, Nummer).

---

### Decision 9: Pluggable Adapter Interface for Future Legal Sources

**The architecture defines a `LegalSourceAdapter` protocol (ABC) that all source-specific
implementations must satisfy.** M7-A implements one adapter — `GIIAdapter` (Gesetze im
Internet). Future adapters for Bundesgesetzblatt, EUR-Lex, and court decision APIs are
explicitly designed for but NOT implemented.

**Protocol definition (`domain/source_adapter.py`):**

```python
from abc import ABC, abstractmethod
from pathlib import Path

class LegalSourceAdapter(ABC):
    """Protocol for legal source adapters. All source-specific logic lives here."""

    @property
    @abstractmethod
    def source_identifier(self) -> str: ...

    @property
    @abstractmethod
    def authority_tier(self) -> AuthorityTier: ...

    @abstractmethod
    async def discover_instruments(self) -> list[InstrumentMetadata]:
        """Return metadata for all instruments available from this source."""
        ...

    @abstractmethod
    async def fetch_instrument(
        self, metadata: InstrumentMetadata, target_dir: Path
    ) -> RawSnapshotResult:
        """Download the instrument's XML. Returns snapshot metadata (hash, path, etc.)."""
        ...

    @abstractmethod
    def parse_to_entities(
        self, snapshot: RawSnapshot
    ) -> tuple[LegalInstrument, list[InstrumentExpression], list[LegalProvision]]:
        """Parse a raw snapshot into domain entities. Raises on parse failure."""
        ...

    @abstractmethod
    def normalize_provisions(
        self, provisions: list[LegalProvision]
    ) -> list[LegalProvision]:
        """Apply source-specific normalization rules (whitespace, citation extraction)."""
        ...
```

**Adapter registry (application layer):**

The `SourceSyncService` maintains a registry of adapters keyed by `source_identifier`.
When a sync is triggered for a specific source, the service resolves the adapter and
calls its methods in sequence. The registry is populated at application startup via
the app factory:

```python
# In app.py
from private_legal_navigator.infrastructure.gii_adapter import GIIAdapter

app.state.source_adapters = {
    "gesetze_im_internet": GIIAdapter(
        http_client=app.state.source_http_client,
        parser=secure_xml_parser,
    )
}
```

**Future adapters (NOT in M7-A):**

| Adapter | Source | Authority Tier | Status |
|---|---|---|---|
| `GIIAdapter` | www.gesetze-im-internet.de | CONSOLIDATED_NON_OFFICIAL (T3) | **M7-A** |
| `BGBlAdapter` | Bundesgesetzblatt (official PDFs/XML) | OFFICIAL_PROMULGATION (T0) | Future |
| `EURLEXAdapter` | EUR-Lex (EU law) | OFFICIAL_EU_PUBLICATION (T1) | Future |
| `CourtAPIAdapter` | ECLI-based court decision APIs | OFFICIAL_COURT_PUBLICATION (T2) | Future |

**Rationale:**
- The adapter protocol is the architecture's **extension point**. Any new legal source
  can be integrated by implementing the five methods — no changes to the domain model,
  the sync pipeline, or the repository layer.
- The protocol enforces the pipeline stages (Decision 4) at the interface level: `fetch` →
  `parse` → `normalize`. An adapter that tries to skip a stage (e.g., normalizing during
  parsing) would violate the protocol and fail type checking.
- The registry pattern (dict keyed by identifier) is simpler than a plugin system with
  dynamic discovery and is appropriate for a project that currently targets three to four
  adapters. If adapter count grows significantly, a setuptools entry-point-based discovery
  can be added without changing the protocol.
- The `source_identifier` property enables the sync service to be source-agnostic: it
  loads configuration by identifier, resolves the adapter, and delegates.

---

### Decision 10: lxml Dependency Added to Project

**`lxml >= 6.1.0` is added to the project's core dependencies in `pyproject.toml`.**

```toml
dependencies = [
    "fastapi>=0.115.0",
    "lxml>=6.1.0",              # Secure XML parsing for legal XML sources
    "pymupdf>=1.24.0",
    "python-multipart>=0.0.9",
    "uvicorn[standard]>=0.30.0",
]
```

**Rationale:**
- `lxml` is the de facto standard for production XML processing in Python. It provides
  the `resolve_entities=False` and `no_network=True` flags needed for the secure parsing
  configuration (Decision 8).
- Version 6.1.0 is a stable, well-tested release with the full security API surface.
- Python's stdlib `xml.etree.ElementTree` does NOT support `no_network=True` and has
  documented XXE vulnerabilities that are mitigated differently (and less reliably)
  via `defusedxml`. `lxml`'s security flags are more comprehensive and more actively
  maintained.
- The dependency is small (~5 MB installed), pure C extension, and has no transitive
  dependencies. It builds from wheel on all supported platforms.
- This is the first external XML dependency in the project. The `pymupdf` dependency
  handles PDF (not XML). The stdlib `sqlite3` handles the database. No other XML
  library is needed.

---

## Alternatives Considered

### Alternative A: defusedxml + stdlib ElementTree (Rejected)

**Approach:** Use Python's built-in `xml.etree.ElementTree` with `defusedxml` monkey-patching
for XXE protection.

| Advantage | Disadvantage |
|---|---|
| No additional C extension dependency | `defusedxml` provides only XXE protection — not `no_network`, not entity expansion limits |
| Smaller dependency footprint | `defusedxml` is less actively maintained than `lxml` |
| Stdlib parser is always available | `ElementTree` lacks XPath support needed for complex legal XML structures |
| | No `huge_tree` flag — billion laughs protection requires custom entity expansion counter |

**Rejected:** `lxml` provides defense-in-depth (XXE + network prevention + tree size limits)
in a single, well-maintained library. Legal XML from GII uses moderately complex XML
structures (nested `norm` elements, `aendb` cross-references, `fussnote` elements) that
benefit from lxml's XPath and namespace support.

---

### Alternative B: Separate SQLite Database for Legal Sources (Rejected)

**Approach:** Store legal source data in a separate SQLite database file, isolated from
case data.

| Advantage | Disadvantage |
|---|---|
| Cleaner physical separation of concerns | Cannot JOIN between `legal_provisions` and `case_legal_links` (ADR-008) |
| Independent backup/restore of legal corpus | SQLite's ATTACH DATABASE is possible but adds complexity |
| Easier to ship a pre-built legal corpus | Two database connections, two transaction scopes |
| | Schema migrations must be coordinated across databases |

**Rejected:** The ability to JOIN norms with case-legal links is a core architectural
requirement (ADR-008, Decision 9). A single database provides this trivially. The operational
simplicity of one database connection, one backup file, and one migration sequence outweighs
the conceptual separation benefit. The tables themselves are clearly namespaced (`legal_*`
prefix) for logical separation within the shared database.

---

### Alternative C: Document Database (Elasticsearch/OpenSearch) for Search (Rejected)

**Approach:** Use a separate search engine for provision text search, synchronized from
SQLite.

| Advantage | Disadvantage |
|---|---|
| Powerful full-text features (stemming, synonyms, relevance tuning) | External service dependency — violates local-only constraint |
| Horizontal scalability for search queries | Massive overengineering for single-user workload |
| Faceted search, aggregations | Requires separate process, port management, memory allocation |
| | Data synchronization between SQLite and search index |
| | Additional operational complexity (startup order, health checks, backups) |

**Rejected:** FTS5 provides everything M7-A needs: BM25 ranking, phrase queries, prefix
queries, boolean operators, and snippet generation. For a single-user application searching
a corpus of at most a few hundred legal instruments, FTS5 is not merely "good enough" — it
is the architecturally correct choice. Elasticsearch would add a Java runtime dependency,
a separate process, network configuration, and index synchronization code — all for search
performance benefits that are irrelevant at this scale.

---

### Alternative D: Flat File Corpus (No Database) (Rejected)

**Approach:** Store parsed provisions as plain text or JSON files in the filesystem, with
grep-based search.

| Advantage | Disadvantage |
|---|---|
| No schema to maintain | No structured queries — cannot filter by instrument, authority tier, or temporal range |
| Human-readable on disk | Cannot JOIN with case-legal links |
| Trivial backup (copy directory) | FTS5 full-text search not available — grep is linear and slow |
| | Citation resolution requires custom indexing (reinventing a database) |
| | Concurrent access issues if frontend queries during sync |

**Rejected:** The filesystem is appropriate for raw snapshots (immutable, content-addressed).
It is NOT appropriate for the normalized corpus, which needs structured queries, transactional
updates during sync, FTS5 full-text search, and JOIN capability with case data. SQLite is the
right tool for the normalized layer, and the filesystem is the right tool for the snapshot
layer.

---

### Alternative E: Vector Embeddings for Semantic Search (Deferred, Not Rejected)

**Approach:** Generate embedding vectors for provision texts and use cosine similarity
for "find provisions similar to this document" queries.

| Advantage | Disadvantage |
|---|---|
| Semantic matching ("Widerspruch" matches "Rechtsbehelf") | Requires embedding model (local or external) |
| Concept-level search beyond keyword matching | Model must run locally (constitutional constraint) |
| | Vectors consume significant storage |
| | Results are non-deterministic without model version pinning |
| | Overengineering for M7-A scope |

**Deferred to M7-E+:** This is explicitly NOT rejected — it is deferred to a future
milestone. The architecture does not preclude adding a `provision_embeddings` table and
a local embedding model later. FTS5 covers M7-A's search requirements. When and if
semantic search becomes a priority, the `legal_provisions` table provides a natural
source for embedding generation. This is documented in the search priority order
(Decision 2): semantic/vector search is explicitly listed as "deferred (M7-E+)".

---

## Consequences

### Positive

1. **Provenance transparency:** Every legal text displayed to the user carries its
   authority tier, retrieval timestamp, temporal confidence, and source URL. The user
   always knows where their legal information came from and how authoritative it is.

2. **Content-addressable integrity:** SHA-256 hashing of raw snapshots provides
   cryptographic verification that the normalized corpus is derived from authentic
   source material. A user (or auditor) can recompute the hash of a stored snapshot
   and compare it to the database record.

3. **Resilience to normalization errors:** The pipeline architecture means that a bug
   in the GII XML parser or normalizer never corrupts the raw snapshots. A fix can be
   deployed and normalization re-run against existing snapshots without re-downloading.

4. **Single database, simple operations:** Legal source tables coexist with case data
   in the same SQLite database, enabling direct JOINs for case-legal links (ADR-008).
   One backup covers everything. One migration sequence covers everything.

5. **Zero operational dependencies for search:** FTS5 is built into SQLite. No separate
   search process, no index synchronization, no additional memory allocation. Full-text
   search works wherever SQLite works.

6. **Extensible source ecosystem:** The adapter protocol enables Bundesgesetzblatt (T0),
   EUR-Lex (T1), and court decision APIs (T2) to be added without changing the domain
   model or sync pipeline. Each new source is a new adapter implementation.

7. **Honest temporal representation:** The `temporal_confidence` field and the explicit
   prohibition on historical completeness claims prevent the system from misleading users.
   The architecture forces humility about what it knows and what it does not.

8. **Privacy-preserving sync:** The structural isolation between sync and case data
   (Decision 7) ensures that even a bug in the sync pipeline cannot leak case information
   to external servers.

### Negative

1. **New external dependency:** `lxml >= 6.1.0` adds a C extension dependency. It is
   small and well-maintained, but it is a compiled component that must be available for
   the target platform. PyPI provides wheels for Windows, macOS, and Linux — this is
   unlikely to be a practical issue, but it is a new dependency class in a project that
   previously relied on pure-Python or Python-stdlib-only packages.

2. **FTS5 maintenance overhead:** FTS5 virtual tables require trigger-based synchronization
   with their content tables (unless using the `content=` parameter, which we do). Schema
   migrations must account for FTS5 rebuilds when the content table schema changes.

3. **Flat file storage for snapshots:** The filesystem-based snapshot storage adds a second
   data location to manage alongside the SQLite database. Snapshots must be backed up
   separately from the database, and path consistency must be maintained. A future
   operational improvement could be a `data_dir` integrity check that verifies every
   snapshot referenced in `raw_snapshots` exists on disk with the correct hash.

4. **XML parsing is brittle by nature:** Legal XML from government sources evolves over
   time (schema changes, namespace additions, structural reorganization). The GII XML
   format has changed in the past. The pipeline architecture isolates this brittleness
   (parse failures don't corrupt snapshots), but the normalizer will need maintenance
   when source formats change.

5. **Citation resolution is source-specific:** Extracting structured citations (norm,
   paragraph, sentence, number) from free text varies by legal tradition. The GII adapter's
   normalizer must handle German legal citation patterns (§ 70 Abs. 1 Satz 2 VwGO).
   Future EUR-Lex adapter must handle EU citation patterns (Art. 6(1)(a) DSGVO). Citation
   parsing logic is a per-adapter concern and must be maintained per adapter.

6. **No incremental sync initially:** The first M7-A sync downloads the entire GII corpus
   (hundreds of XML files, potentially 500+ MB). Incremental sync (fetching only changed
   instruments) requires either a `Last-Modified` header comparison or a sitemap-based
   change detection — both of which require source server support that may not be available.
   Full re-sync is the initial implementation; incremental sync is a future optimization.

### Neutral

1. **Database size growth:** The legal corpus will add significant data to the SQLite
   database. A rough estimate: ~200 instruments × ~100 provisions each × ~500 bytes per
   provision text = ~10 MB for provision texts, plus metadata and FTS5 index overhead =
   ~20-30 MB total. This is negligible for modern storage but represents the first
   substantial data volume beyond case records.

2. **Search uses English tokenizer:** FTS5's default tokenizer (unicode61) handles
   German text adequately but does not support German-specific stemming (e.g., "Gesetze"
   not matching "Gesetz"). This is acceptable for M7-A — prefix search
   (`provision_text: Gesetz*`) compensates partially. A German tokenizer can be
   configured later if needed.

3. **Adapter protocol is synchronous:** The `LegalSourceAdapter` methods are defined
   as synchronous for the parse and normalize stages (CPU-bound work). Download is
   async (I/O-bound). This mirrors the existing pattern in the codebase and is appropriate
   for a single-user application where sync is a foreground operation.

---

## References

- [ADR-001 — Local Modular Monolith](adr-001-local-modular-monolith.md)
- [ADR-002 — Confirmed Reference Events and Calendar Arithmetic](adr-002-confirmed-reference-events.md)
- [ADR-008 — Case Legal Timeline and Case-Legal Links](ADR-008-case-legal-timeline.md)
- [M7-A Reality Refresh](m7a-reality-refresh.md)
- [Architecture Overview](architecture.md)
- [Settings Configuration](../../src/private_legal_navigator/config.py)
- [Database Schema](../../src/private_legal_navigator/infrastructure/database.py)
- [Project Dependencies](../../pyproject.toml)
- [Project Constitution](../../.specify/memory/constitution.md)
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)
- [lxml Security Documentation](https://lxml.de/parsing.html#parser-options)
- [Gesetze im Internet — Impressum](https://www.gesetze-im-internet.de/impressum.html)

---

Verdict: APPROVED
