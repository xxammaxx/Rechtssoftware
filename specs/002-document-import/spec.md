# Spec — M2 Lokaler Dokumentimport und sichere Dateiverwaltung

## Feature
M2 — Lokaler Dokumentimport und sichere Dateiverwaltung

## Status
Draft

## User Stories

### User Story 1 — Dokument zu einem Fall hochladen (P1)
Als Nutzer möchte ich ein PDF-Dokument zu einem bestehenden Fall hochladen,
damit ich alle relevanten Unterlagen an einem Ort sammeln kann.

**Akzeptanzkriterien:**
- PDF-Upload über die API möglich
- Das Dokument wird einem existierenden Fall zugeordnet
- Nicht-PDF-Dateien werden abgelehnt (MIME-Type-Prüfung)
- Dateigröße ist auf 20 MB begrenzt
- Die Datei wird außerhalb der Datenbank im Datenverzeichnis gespeichert
- Eine eindeutige Document-ID wird serverseitig generiert
- Originaldateiname und MIME-Type werden gespeichert

### User Story 2 — Dokumente eines Falls auflisten (P1)
Als Nutzer möchte ich alle zu einem Fall gehörenden Dokumente sehen.

### User Story 3 — Dokument herunterladen (P1)
Als Nutzer möchte ich ein hochgeladenes Dokument wieder herunterladen können.

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-M2-001 | PDF-Upload muss möglich sein |
| FR-M2-002 | Upload muss einem existierenden Case zugeordnet sein |
| FR-M2-003 | Nicht-PDF MIME-Types müssen abgelehnt werden |
| FR-M2-004 | Dateigröße auf 20 MB begrenzen |
| FR-M2-005 | Dateien außerhalb der DB im PLN_DATA_DIR speichern |
| FR-M2-006 | Serverseitig generierte Document-ID (UUIDv4) |
| FR-M2-007 | Originaldateiname und MIME-Type speichern |
| FR-M2-008 | Dokumente eines Falls auflisten |
| FR-M2-009 | Dokument per ID herunterladen |
| FR-M2-010 | Upload für nicht-existierenden Case = 404 |
| FR-M2-011 | Download für nicht-existierendes Document = 404 |
| FR-M2-012 | Metadaten in der cases-Tabelle oder neuer documents-Tabelle |
| FR-M2-013 | Kein In-Path-Traversal (keine relativen Pfade ausnutzbar) |
| FR-M2-014 | Dateien nicht ausführbar speichern |
| FR-M2-015 | Test-PDFs synthetisch generieren (keine echten Dokumente) |

## Abgrenzung

Dieses Feature umfasst **nicht**:
- OCR oder Textextraktion aus PDFs (M3)
- Dokumentklassifikation (M4)
- Vorschau/Thumbnails
- Löschen von Dokumenten
- Mehrere Dateien gleichzeitig
- Nicht-PDF-Formate (Bilder, DOCX etc.)
