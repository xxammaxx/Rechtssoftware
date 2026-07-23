# Architektur — PrivateLegalNavigator

## Zielbild

```
┌────────────────────────────────────┐
│  Web Browser / Client              │
└──────────┬─────────────────────────┘
           │ HTTP (127.0.0.1)
┌──────────▼─────────────────────────┐
│  FastAPI API-Schicht               │
│  - Routen (/api/v1/cases, etc.)    │
│  - M7-A Routen (/ui/legal-sources) │
│  - Pydantic-Schemas                │
│  - Fehlerbehandlung                │
│  - Middleware: HostValidation,     │
│    SecurityHeaders, CSRF           │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│  Application Services              │
│  - CaseService                     │
│  - DocumentService                 │
│  - DeadlineService (M5)            │
│  - ReferenceEventService (M6-A)    │
│  - CalculationService (M6-A)       │
│  - WorkspaceService (M6-UI)        │
│  ────────────────────────────      │
│  - LegalSourceService (M7-A)       │
│  - CaseTimelineService (M7-A)      │
│  - CitationResolver (M7-A)         │
│  - Repository Ports (ABCs)         │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│  Domain Model                      │
│  - Case, Document, Status          │
│  - ClassificationResult (M4)       │
│  - DeadlineCandidate (M5)          │
│  - ReferenceEvent (M6-A)           │
│  ────────────────────────────      │
│  - LegalSource, SourceSnapshot     │
│  - LegalInstrument, Expression     │
│  - LegalProvision, Citation (M7-A) │
│  - CaseLegalEvent, EventRelation   │
│  - CaseLegalLink, LegalIssue       │
│  - EvidencePack, Claim (M7-A)      │
│  - AuthorityTier (StrEnum)         │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│  Infrastructure                    │
│  - SqliteCaseRepository            │
│  - SqliteDocumentRepository        │
│  - SqliteRefEventRepository        │
│  ────────────────────────────      │
│  - SqliteLegalSourceRepository     │
│  - SqliteCaseTimelineRepository    │
│  - GiiAdapter (GII sync)           │
│  - SourceClient (Safe HTTP)        │
│  - CitationResolver (det.)         │
│  - database.py (Schema, 11 Tab.)   │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│  SQLite-Datenbank                  │
│  (private_legal_navigator.db)      │
│  - cases, documents (M1-M3)        │
│  - deadline_candidates (M5)        │
│  - confirmed_ref_events (M6-A)     │
│  - legal_sources (M7-A)            │
│  - legal_source_snapshots (M7-A)   │
│  - legal_instruments (M7-A)        │
│  - legal_expressions (M7-A)        │
│  - legal_provisions (M7-A)         │
│  - legal_citations (M7-A)          │
│  - case_legal_events (M7-A)        │
│  - event_relations (M7-A)          │
│  - case_legal_links (M7-A)         │
│  - legal_issues (M7-A)             │
│  - legal_provisions_fts (FTS5)     │
└────────────────────────────────────┘

Filesystem (M7-A):
  PLN_DATA_DIR/snapshots/
    └── {source_type}/{hash[:2]}/{sha256_hash}.xml
```

## Komponenten

### API (FastAPI)
- Routen in `api/routes.py`, `api/document_routes.py`, `api/reference_event_routes.py`
- M7-A UI-Routen in `api/m7a_ui_routes.py` (Legal Sources, Timeline, Evidence Pack)
- Request/Response-Schemas in `api/schemas.py`
- Fehlerbehandlung in `api/errors.py`
- App Factory in `app.py`
- Dependency Injection über `app.state` + FastAPI `Depends`
- Middleware: HostValidation (`middleware/host_validation.py`), SecurityHeaders (`middleware/security_headers.py`), CSRF (`middleware/csrf.py`)

### Application
- `CaseService`: Orchestriert Use Cases (create, get, list)
- `DocumentService`: Dokument-Upload, Text-Extraktion (M2-M3)
- `DeadlineService`: Fristkandidaten-Erkennung (M5)
- `ReferenceEventService`: Bezugsereignis-Bestätigung (M6-A)
- `CalculationService`: Calendar-Arithmetic (M6-A)
- `WorkspaceService`: M6-UI Koordination (M6-UI)
- **`LegalSourceService` (M7-A)**: Orchestriert GII-Import, Source-Registry, Suche, Snapshot-Verifikation
- **`CaseTimelineService` (M7-A)**: Orchestriert Rechtsereignisse, Normlinks, Evidence Pack
- **`CitationResolver` (M7-A)**: Deterministische Auflösung von Zitaten ("§ 48 SGB X")
- `CaseRepository` (ABC): Port für Persistenz
- Keine direkte SQL-Abhängigkeit

### Domain
- `Case`: Entität mit UUID, Titel, Status, Zeitstempeln
- `CaseStatus`: StrEnum (`open` in M1)
- Validierung: Titel 1–200 Zeichen, getrimmt, nicht leer
- **`LegalSource`, `SourceSnapshot`, `LegalInstrument`, `LegalExpression`, `LegalProvision`, `LegalCitation` (M7-A)**: Domain-Entitäten des Rechtsquellen-Korpus
- **`AuthorityTier` (M7-A)**: StrEnum mit 6 Stufen (OFFICIAL_PROMULGATION bis UNKNOWN)
- **`CaseLegalEvent`, `EventRelation`, `CaseLegalLink`, `LegalIssue`, `LegalClaim`, `EvidencePack` (M7-A)**: Domain-Entitäten der Fall-Rechts-Timeline

### Infrastructure
- `database.py`: `get_connection()` mit PRAGMA foreign_keys, `initialize_schema()`
- `SqliteCaseRepository`: Implementiert `CaseRepository` mit parametrisierten Queries
- **`SqliteLegalSourceRepository` (M7-A)**: Persistenz für Rechtsquellen, Snapshot-Import (atomic batch)
- **`SqliteCaseTimelineRepository` (M7-A)**: Persistenz für Timeline-Events und Normlinks
- **`GiiAdapter` (M7-A)**: Adapter für Gesetze im Internet (GII) — Katalogabfrage, Download, XML-Parsing
- **`SourceClient` (M7-A)**: Sicherer HTTP-Client mit Host-Allowlist, HTTPS-Only, Redirect-Validierung
- SQLite-Verbindung pro Operation (kein globaler State)

## Datenfluss (M1-M6)

1. `POST /api/v1/cases` → `CreateCaseRequest` (Pydantic) → `CaseService.create_case()` → `Case(title=...)` → `repository.save(case)` → SQLite
2. `GET /api/v1/cases` → `CaseService.list_cases()` → `repository.list_all()` → SQLite → `CaseListResponse`
3. `GET /api/v1/cases/{id}` → `CaseService.get_case(uuid)` → `repository.get_by_id(uuid)` → SQLite → `CaseResponse` oder 404

## Datenfluss (M7-A — Legal Source Foundation)

### GII Sync Pipeline (4-stufig)

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  1. Fetch   │ ──► │  2. Parse   │ ──► │  3. Persist  │ ──► │  4. Index   │
│  (SourceCl.)│     │  (lxml)     │     │  (SQLite)    │     │  (FTS5)     │
└──────┬──────┘     └──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                    │                    │
       ▼                   ▼                    ▼                    ▼
  raw_snapshots         parser error        atomic batch          FTS5 rows
  (immutable,          logged, retryable    (all-or-nothing)      committed
  SHA-256 hash)                              on failure:
                                             snapshot→FAILED
```

1. `GET /ui/legal-sources` → `LegalSourceService.get_source_status()` → `SqliteLegalSourceRepository.list_sources()` → SQLite `legal_sources`
2. `GET /ui/legal-sources/search?q=§+70+VwGO` → `LegalSourceService.search()` → `SqliteLegalSourceRepository.search_provisions_fts()` → FTS5 → `LegalProvision`-Ergebnisse
3. `GET /ui/legal-sources/norm/{id}` → `SqliteLegalSourceRepository.get_provision()` → JOIN über `legal_expressions`, `legal_instruments`, `legal_source_snapshots`

### Citation Resolution

```
"§ 48 SGB X"
   → CitationResolver.parse_citation()
   → CitationResolver.resolve()
      1. Parse citation string (regex)
      2. Find instrument by abbreviation ('SGB X')
      3. Find current expression
      4. Find provision by number ('48')
      5. Return ResolvedCitation (status, instrument, provision)
```

## Datenfluss (M7-A — Case Legal Timeline)

### Legal Event Lifecycle

```
CANDIDATE ──(user confirms)──► CONFIRMED ──(user corrects)──► CORRECTED (new record)
   │              │                  │
   │              │                  └──(user revokes)──► REVOKED
   │              │
   └──(user rejects)──► REJECTED
```

1. `POST /ui/cases/{id}/legal-timeline/event` → CSRF-Validierung → `CaseTimelineService.create_event()` → `CaseLegalEvent` (CANDIDATE) → SQLite
2. `POST .../legal-timeline/confirm` → CSRF-Validierung → `CaseTimelineService.confirm_event()` → review_status=CONFIRMED
3. `POST .../legal-timeline/correct` → CSRF-Validierung → `CaseTimelineService.correct_event()` → neues `CaseLegalEvent` mit `previous_event_id`
4. `GET /ui/cases/{id}/legal-timeline` → `CaseTimelineService.get_timeline()` → `list_active_events()` → SQL-Query mit Filter (CONFIRMED, revoked_at IS NULL, not superseded)

### Norm Link Lifecycle (identisch zu Events)

```
CANDIDATE → CONFIRMED → CORRECTED → REVOKED
```

### Evidence Pack

`GET /ui/cases/{id}/evidence-pack` → `CaseTimelineService.build_evidence_pack()` → Deterministic Query aller bestätigten Daten → `EvidencePack` (Value Object, kein LLM)

## Fehlerfluss

- Validierungsfehler → 422 (FastAPI/Pydantic)
- Nicht gefunden → 404 mit `{"error": {"code": "CASE_NOT_FOUND", ...}}`
- Konflikt (Status-Transition) → 409 bei ungültigen Lifecycle-Übergängen
- Datenbankfehler → 500 mit `{"error": {"code": "DATABASE_ERROR", ...}}`
- Keine Stacktraces, keine SQL, keine Dateipfade in Antworten

## Sicherheitsgrenzen

### M1-M6
- Bindung: `127.0.0.1` (kein Netzwerkzugriff von außen)
- Keine CORS-Konfiguration (kein Cross-Origin-Zugriff)
- Keine externen Requests im Code
- Parametrisierte SQL-Queries (kein Injection-Risiko)
- Kein Request-Body-Logging
- Keine `.env`-Datei, keine Secrets

### M7-A — Secure Source Client (SEC-001)
- Host-Allowlist: nur `*.gesetze-im-internet.de` (konfigurierbar)
- HTTPS-Only: keine Plain-HTTP-Verbindungen zu externen Hosts
- Redirect-Validierung: jeder Redirect-Hop gegen Allowlist geprüft
- HTTPS→HTTP-Weiterleitung zu externen Hosts blockiert
- Response-Size-Limit: 200 MB (konfigurierbar)
- Timeouts: Connect 10s, Read 30s
- TLS-Verifikation erzwungen
- Keine Cookies, keine Credentials, keine Fall-Daten in Requests (Privacy-by-Design)

### M7-A — Sicheres XML-Parsing (SEC-015)
- `resolve_entities=False`: XXE-Schutz
- `no_network=True`: Kein Netzwerk während des Parsings
- `huge_tree=False`: Schutz vor Billion-Laughs-Angriff
- 50 MB Input-Limit
- `load_dtd=False`, `dtd_validation=False`

### M7-A — Atomic Import (SEC-015)
- Alle INSERTs in einer Transaktion: Alles oder Nichts
- Snapshot verbleibt mit `import_status=FAILED` bei Fehler
- Raw-Snapshot bleibt unverändert (immutable)

## M7-A — Legal Source Foundation

### Domain-Modell

| Entität | Zweck | Schlüsselfelder |
|---------|-------|-----------------|
| `LegalSource` | Registrierte Rechtsquelle (Publisher) | source_key, authority_tier, jurisdiction |
| `SourceSnapshot` | Immutabler Roh-Download | sha256 (64-Char), storage_path, import_status |
| `LegalInstrument` | Gesetz/Verordnung (z.B. VwGO) | abbreviation, official_title, instrument_type |
| `LegalExpression` | Version eines Instruments | published_at, valid_from/valid_to, temporal_confidence |
| `LegalProvision` | Einzelne Norm (Paragraph/Artikel) | provision_number, heading, text_content |
| `LegalCitation` | Aufgelöstes Zitat | citation_text, resolution_status, resolved_provision |

### Architekturprinzipien (ADR-007)

1. **Modular Monolith Extension** — Alle M7-A-Komponenten in bestehenden 4 Schichten
2. **SQLite + FTS5** — Keine separate Suchmaschine; FTS5 in SQLite built-in
3. **Immutable Snapshots** — SHA-256-Hash als Dateiname; kein UPDATE-Pfad
4. **4-stufige Pipeline** — Download → Parse → Normalize → Index (isolierte Fehlergrenzen)
5. **Authority Tier System** — 6-stufige Vertrauensklassifikation (T0–T5)
6. **Keine historische Vollständigkeit** — `temporal_confidence` ehrlich ausweisen
7. **Keine Fall-Daten im Sync** — Privacy-by-Design isoliert
8. **Sicheres XML** — lxml mit Defense-in-Depth
9. **Pluggable Adapter** — `LegalSourceAdapter`-Protokoll für BGBl, EUR-Lex (zukünftig)
10. **lxml-Dependency** — `lxml >= 6.1.0` für sicheres XML

## M7-A — Case Legal Timeline

### Domain-Modell

| Entität | Zweck | Lifecycle |
|---------|-------|-----------|
| `CaseLegalEvent` | Rechtsereignis (Bescheid, Widerspruch, etc.) | CANDIDATE→CONFIRMED→CORRECTED/REVOKED |
| `EventRelation` | Beziehung zwischen Ereignissen (AMENDS, CHALLENGES) | CANDIDATE→CONFIRMED |
| `CaseLegalLink` | Normverknüpfung (Fall ↔ Provision) | CANDIDATE→CONFIRMED→CORRECTED/REVOKED |
| `LegalIssue` | Offene Rechtsfrage im Fall | OPEN→UNDER_REVIEW→RESOLVED/DEFERRED |
| `LegalClaim` | Rechtshypothese/-behauptung | DRAFT→UNDER_REVIEW→CONFIRMED/REJECTED |
| `EvidencePack` | Deterministisches Beweisbündel | Read-only Projektion (kein Lifecycle) |

### Architekturprinzipien (ADR-008)

1. **Append-Only Events** — Kein UPDATE, nur INSERT; Korrekturen = neue Records
2. **Drei Zeitdimensionen** — `occurred_at`, `known_at`, `recorded_at`
3. **Geschlossener Event-Typen** — 11 Event-Typen als StrEnum
4. **Explizite Relationen** — dedicated `event_relations`-Tabelle (Many-to-Many)
5. **Human-Review-Lifecycle** — Identisch zu ADR-002 (CANDIDATE→CONFIRMED)
6. **History Preservation** — `previous_event_id`-Kette
7. **Derived Timeline** — Timeline = SQL-Query (keine materialisierte Tabelle)
8. **Integration M6-A** — `DEADLINE_STARTED`-Events referenzieren `confirmed_reference_events`
9. **Case-Legal Links** — `case_legal_links` (Norm→Fall) mit gleichem Lifecycle
10. **Keine automatische Rechtswirkung** — Event-Typen sind deskriptive Labels

## Neue Datenbank-Tabellen (M7-A)

### Legal Source Provenance (6 Tabellen)

| Tabelle | Typ | Beschreibung |
|---------|-----|-------------|
| `legal_sources` | Real | Registrierte Rechtsquellen mit Authority Tier |
| `legal_source_snapshots` | Real | Immutable Raw-Downloads (SHA-256, Größe, Status) |
| `legal_instruments` | Real | Gesetze/Verordnungen (Abkürzung, Titel, Typ) |
| `legal_expressions` | Real | Versionierte Fassungen (gültig ab/bis, Confidence) |
| `legal_provisions` | Real | Einzelnormen (Paragraphen, Artikel, Text) |
| `legal_citations` | Real | Aufgelöste Zitate (Status, Confidence, Ziel) |

### Case Legal Timeline (4 Tabellen)

| Tabelle | Typ | Beschreibung |
|---------|-----|-------------|
| `case_legal_events` | Real | Append-only Rechtsereignisse (11 Typen, 3 Zeitdimensionen) |
| `event_relations` | Real | Many-to-Many-Ereignisbeziehungen (AMENDS, CHALLENGES, etc.) |
| `case_legal_links` | Real | Norm-zu-Fall-Verknüpfungen (Lifecycle: CANDIDATE→CONFIRMED) |
| `legal_issues` | Real | Offene/erledigte Rechtsfragen pro Fall |

### Full-Text Search (1 Virtual Table)

| Tabelle | Typ | Beschreibung |
|---------|-----|-------------|
| `legal_provisions_fts` | FTS5 | Volltextindex über `legal_provisions` |

### Neu: 30 Indexes für M7-A-Operationen

Alle M7-A-Tabellen haben B-Tree-Indexes auf den wichtigsten Query-Pfaden (case_id, abbreviation, sha256, review_status, etc.).

## Teststrategie

| Schicht | Testtyp | Technik |
|---------|---------|---------|
| Domain | Unit | Direkte Instanziierung |
| Repository | Integration | Temporäre SQLite-DB |
| Service | Unit | Mocked Repository |
| API | Integration | ASGI-Transport (httpx) |
| M7-A Citation | Unit/Integration | CitationResolver mit Test-Zitaten |
| M7-A GII | Integration | Test-server (localhost) + Mock-Client |
| M7-A SourceClient | Unit | Mocked httpx-Transport |

## Erweiterbarkeit

- Neue API-Endpunkte → Neue Routen im `api/`-Layer
- Neue Domänen-Entitäten → Neue Module in `domain/`
- Neue Persistenz → Neuer Adapter für Repository-Port
- Neue Rechtsquellen → Neuer `LegalSourceAdapter` (M7-A Protocol)
- Frontend → Nutzt bestehende `/api/v1/`- und `/ui/`-Endpunkte

## ADR-Referenzen

- [ADR-001 — Local Modular Monolith](adr-001-local-modular-monolith.md)
- [ADR-002 — Confirmed Reference Events & Calendar Arithmetic](adr-002-confirmed-reference-events.md)
- [ADR-003 — Local Confirmation Workspace](../specs/006-local-confirmation-workspace/spec.md)
- [ADR-007 — Legal Source Provenance and Corpus Foundation](ADR-007-legal-source-provenance.md)
- [ADR-008 — Case Legal Timeline and Case-Legal Links](ADR-008-case-legal-timeline.md)
