# UX-Audit — PrivateLegalNavigator v1.0.0rc2

**Audit-Datum:** 2026-07-31
**Methodik:** product-designer, frontend-design, design-systems, a11y-testing, dogfood
**Candidate:** 6a62460aaa798ede5784f07ac39a51953db5a0dd
**Evidence:** RC-017 screenshots (47 PNGs), Live-Browser-Exploration (alle 10 UI-Seiten), CSS-Analyse (1559 Zeilen), Template-Analyse (15 Dateien)

---

## Nutzer-Problem-Validierung (11 Suspected Issues)

Der Nutzer nannte 11 mögliche Prüfpunkte. Hier die Validierung:

### 1. "Sehr große Überschriften mit ungünstigen Zeilenumbrüchen"
**VALIDIERT — Medium**
- H1 `.page-title` = 32px (`--text-2xl`). Für "SYNTHETISCH – Sichtbarer Linux E2E Test RC-017" bricht die Zeile bei ~800px Content-Breite unschön um.
- Der Testfall-Titel ist absichtlich lang; reale Fallnamen wären kürzer (z.B. "Widerspruch Bescheid vom 15.07.").
- **Trotzdem:** 32px ist für diese Content-Breite zu groß. Empfehlung: H1 auf 24–28px reduzieren.

### 2. "Viel ungenutzter Leerraum"
**VALIDIERT — Medium**
- Case-Detail-Seite: Upload-Formular (`card__body`) nimmt ~300px, aber Dokumentenliste nur ~80px. Upload dominiert visuell, obwohl Dokumente die relevantere Information sind.
- Legal-Situation-Seite: 3 H2-Überschriften mit leeren Absätzen darunter → viel vertikaler Leerraum ohne Inhalt.
- Content-Max-Width 1200px auf 900px-effektivem Viewport → rechter Rand ungenutzt.

### 3. "Technisch wirkende Statuswerte wie 'open'"
**VALIDIERT — Low**
- Status "open" (englisch, lowercase) wirkt technisch im deutschen UI.
- Bestätigung: `view.status` direkt aus DB-Feld gerendert ohne Übersetzung/Formatierung.
- Empfehlung: Deutsch ("Offen"), mit visuellem Badge statt Plain-Text.

### 4. "Technische Warncodes wie LEGAL_CALCULATION_NOT_PERFORMED im Vordergrund"
**VALIDIERT — High**
- Document-Detail-Seite: Drei technische Codes (`LEGAL_CALCULATION_NOT_PERFORMED`, `MULTIPLE_DEADLINE_CANDIDATES`, `RELATIVE_REFERENCE_REQUIRED`) in `.warning-code` als primäre Information.
- Die menschenlesbare Erklärung folgt erst danach. Nicht-technische Nutzer sehen zuerst kryptische Codes.
- Empfehlung: Menschensatz zuerst, Code als Tooltip oder in Klammern.

### 5. "Schwache visuelle Priorisierung zwischen Hauptaktion und Sekundärinformationen"
**VALIDIERT — High**
- Candidate-Detail-Seite: "Vorschlag ablehnen" und "Datum bestätigen" sind gleich gestylt (`.btn--danger` vs `.btn--primary`), aber die Confirm-Action sollte visuell dominieren.
- Case-Detail: Upload-Formular hat mehr visuelles Gewicht (Card + Fieldset) als die Dokumentenliste.
- Footer-Disclaimer ist gleich prominent wie der Hauptinhalt.

### 6. "Sehr große Uploadfläche im Verhältnis zum übrigen Inhalt"
**VALIDIERT — Medium**
- Upload nimmt ~40% der Case-Detail-Seite ein, aber ist eine Sekundäraktion (nachdem der Fall bereits Dokumente hat).
- Empfehlung: Upload in kollabierbaren Bereich oder Sidebar verschieben.

### 7. "Uneinheitliche Informationsdichte"
**VALIDIERT — Medium**
- Case-Liste: kompakt (1 Card pro Case, ~75px)
- Case-Detail: gemischt (kompakte Doku-Liste + große Upload-Card)
- Document-Detail: hoch (Warnings + Candidates + viele Details)
- Legal-Sources: sehr dünn (Tabelle mit 1 Zeile, 0 Daten)
- Evidence-Pack: komplett leer bei leeren Daten

### 8. "Teilweise lange Zeilen und schwer scannbare Hinweistexte"
**VALIDIERT — Low**
- `.notice--review` und Warning-Texte sind Fließtext ohne Aufzählungen in der deutschen Version.
- Zeilenlänge ~65ch innerhalb der Content-Bereichs — akzeptabel, aber kombiniert mit geringem Zeilenabstand (`--leading-relaxed: 1.65`) suboptimal.

### 9. "Begrenzte erkennbare Hauptnavigation"
**VALIDIERT — High (BEHOBEN in Slice 1)**
- Vorher: Nur Breadcrumbs + Back-Links. Keine Tab-Navigation.
- **Jetzt:** Case-Tab-Navigation implementiert (Übersicht|Rechtslage|Verlauf|Evidence) auf allen 4 Case-Views.
- **Verbleibend:** Keine globale Navigation zwischen Case-Liste und Legal-Sources.

### 10. "Noch funktionaler statt ausgereifter Produkteindruck"
**VALIDIERT — Medium**
- System-Fonts (Inter fällt zurück auf System-UI wenn nicht installiert).
- Einheitliches Grau-Weiß-Farbschema ohne Persönlichkeit.
- Status-Badges funktional korrekt, aber ohne visuelle Hierarchie.
- Keine Mikrointeraktionen, keine Übergänge außer Button-Hover.

### 11. (User didn't provide #11 explicitly, but the instruction said "diese Hinweise")

---

## Vollständiger Seiten-Audit

### 1. Fallliste (/ui/cases)
**Status:** Gut mit Verbesserungspotential
- ✓ Skip-Link, Breadcrumb, H1, Aktionen-Navigation
- ✓ Case-Card mit Titel, Status, Doku-Count, Datum
- ✗ Keine Sortierung/Filterung (nur relevant bei >5 Fällen)
- ✗ "1 Fall" als Text — könnte Badge sein
- ✗ Keine Empty-State-Guidance wenn 0 Fälle

### 2. Fallanlage (/ui/cases/create)
**Status:** Funktionell, minimalistisch
- ✓ Pflichtfeld (Fallname) mit required-Attribut
- ✓ Optionales Beschreibungsfeld mit Hint
- ✓ Back-Link
- ✗ Keine Cancel-Funktion (nur Back-Link)
- ✗ Kein visuelles Feedback bei erfolgreicher Anlage (Redirect zur Liste ohne Flash-Message getestet)
- ✗ Validierungsfehler nur per HTML5 — keine Server-seitige Fehlerdarstellung bei leerem Namen getestet

### 3. Falldetail (/ui/cases/{id})
**Status:** Verbessert (Tab-Navigation hinzugefügt)
- ✓ Tab-Navigation: Übersicht|Rechtslage|Verlauf|Evidence
- ✓ Dokumentenliste mit Metadaten
- ✓ Upload-Formular mit File-Picker, Size-Hint, Privacy-Hinweis
- ✗ Upload dominiert visuell (sollte sekundär sein)
- ✗ "Status: open" — technisch, englisch, kein Badge
- ✗ Kein visueller Unterschied zwischen leerem Zustand (0 Dokumente) und gefülltem Zustand außer Text

### 4. Dokumentdetail (/ui/cases/{id}/documents/{id})
**Status:** Funktional stark, visuell verbesserungswürdig
- ✓ Warning-Box mit strukturierten Hinweisen
- ✓ Candidate-Karten mit Typ, Wert, CTA
- ✓ "Menschliche Prüfung erforderlich" prominent
- ✗ Technische Codes (LEGAL_CALCULATION_NOT_PERFORMED) zu prominent
- ✗ 14-Tage-Kandidat: "14 Tagn" (Tippfehler — "Tag" ohne 'e' im Plural)
- ✗ "Bezugsereignis erforderlich" ohne Erklärung was ein Bezugsereignis ist

### 5. Candidate-Detail (/ui/cases/{id}/documents/{id}/candidates/{idx})
**Status:** Exzellente Daten, visuell überladen
- ✓ Vollständige History-Tabelle mit Zeitstempel, Aktion, Quelle, Status
- ✓ "Erkannte Zeitangabe" mit Art, Datum, Text, Quelle
- ✓ Zwei Action-Forms (Ablehnen + manuell bestätigen)
- ✗ Seite ist sehr lang (scrollt >1300px) — History könnte collapsible sein
- ✗ Confirm-Button nicht prominent genug vs. Ablehnen-Button
- ✓ Datums-Picker mit Tag/Monat/Jahr Spin-Buttons + Kalender-Button

### 6. Rechtsquellen (/ui/legal-sources)
**Status:** Daten-arm, strukturell solide
- ✓ Quellen-Tabelle mit Spalten für Name, Aktiv, Autorität, Import, Snapshots, Instrumente, Normen, Integrität, Fehler
- ✓ "Gesetze im Internet" Quelle registriert
- ✗ 0 Snapshots, 0 Instrumente, 0 Normen — aber kein "Sync starten" CTA
- ✗ "NOT_VERIFIED" als Integritätsstatus ohne Handlungsaufforderung
- ✓ "Rechtsquellen durchsuchen" Link vorhanden

### 7. Rechtssuche (/ui/legal-sources/search)
**Status:** Funktional
- ✓ Suchfeld mit Query-Parameter
- ✗ Keine Ergebnisse (keine Normen importiert) — aber kein "Keine Daten, zuerst synchronisieren" Hinweis

### 8. Rechtslage (/ui/cases/{id}/legal-situation)
**Status:** Rohbau
- ✓ Tab-Navigation vorhanden
- ✓ Norm-Verknüpfungsformular mit Norm-ID + Relevanznotiz
- ✗ Drei H2-Überschriften mit leeren Inhalten — visuell unschön
- ✗ "Keine aktiven Normverknüpfungen" Empty-State mit CTA (verbessert in Slice 2) ✓

### 9. Rechtsverlauf (/ui/cases/{id}/legal-timeline)
**Status:** Rohbau
- ✓ Tab-Navigation vorhanden
- ✓ Ereignis-Formular mit 8 Event-Types, Datum, Beschreibung
- ✓ Verbesserte Empty-State-Texte (Slice 2)
- ✗ Select-Feld zeigt "– Bitte wählen –" (nicht übersetzt: Bindestrich-Typographie)
- ✗ Date-Picker an zwei Stellen (Ereignet am, Bekannt seit) — redundant?

### 10. Evidence Pack (/ui/cases/{id}/evidence-pack)
**Status:** Struktur gut, Inhalt leer
- ✓ Tab-Navigation vorhanden
- ✓ 7 strukturierte Sektionen (Bestätigte Tatsachen, Offene Tatsachen, Rechtsereignisse, Normverknüpfungen, Rechtsfragen, Quellenmetadaten, Snapshot-Integrität)
- ✓ Verbesserte Empty-State-Texte (Slice 2)
- ✗ Alle Sektionen leer — keine Mock-Daten für Preview
- ✗ Kein Export-Button (nur HTML-Ansicht)
- ✗ Schema-Version und Export-Zeitpunkt angezeigt, aber kein Download

### 11. Fehlerseiten (/ui/errors/400, 403, 404, 409)
**Status:** Vorhanden aber ungetestet im Live-Betrieb
- Templates existieren für 400, 403, 404, 409
- Error-Page-Design mit Code, Title, Message, Action-Button

---

## Accessibility (a11y-testing Methodik)

| Check | Status |
|-------|--------|
| Skip-Link vorhanden | ✓ |
| Focus-Indikatoren (3px outline) | ✓ |
| Semantic HTML (main, nav, header, footer) | ✓ |
| Formular-Labels | ✓ |
| Required-Attribute | ✓ |
| Lang-Attribut (de) | ✓ |
| Viewport-Meta | ✓ |
| Prefers-reduced-motion | ✓ |
| Print-Stylesheet | ✓ |
| Touch-Targets ≥44px | ✓ |
| Heading-Hierarchie | PARTIAL — H1→H2→H3 Logik vorhanden, aber manche Seiten haben H2 ohne Inhalt |
| Tastatur-Navigation | ✓ (getestet über Tab-Reihenfolge in Snapshots) |
| ARIA-Labels | PARTIAL — Navigation hat aria-label, aber Status-Bereiche nicht |
| Color-Contrast | ✓ (Dunkelgrau #1a1a1a auf Weiß = 17:1) |
| Screen-Reader-Text (.u-visually-hidden) | ✓ |
| Error-Identifikation | ✓ (.form-error-summary mit List) |
| Focus-Trapping | N/A (keine Modals) |

---

## Top 10 priorisierte UX-Befunde

### 1. CRITICAL — Keine globale Navigation (BEHOBEN für Case-Views)
**Evidence:** Vor Slice 1 existierte keine Navigation zwischen Case-Sektionen. Jetzt: Tab-Leiste implementiert.
**Rest:** Keine Navigation zwischen Case-Liste ↔ Legal-Sources. Nutzer muss URL kennen.

### 2. HIGH — Technische Warncodes verdrängen menschenlesbare Erklärungen
**Evidence:** Document-Detail-Seite: `LEGAL_CALCULATION_NOT_PERFORMED`, `MULTIPLE_DEADLINE_CANDIDATES` als erste visuelle Elemente.
**Impact:** Nicht-technische Nutzer verstehen die Seite nicht.
**Fix:** Menschensatz zuerst: "Keine automatische Fristberechnung — 2 Textstellen erkannt. Bitte manuell prüfen."

### 3. HIGH — Status-Werte technisch und englisch
**Evidence:** "open" im deutschen UI. Direkter DB-Wert ohne UI-Transformation.
**Impact:** Wirkt unfertig, technisch. Vertrauensverlust bei nicht-technischen Nutzern.
**Fix:** Status-Mapping mit deutschen Labels + Badge-Komponente.

### 4. HIGH — Visuelle Hierarchie von Aktionen inkonsistent
**Evidence:** "Vorschlag ablehnen" und "Datum bestätigen" gleich gewichtet. Upload dominiert Case-Detail.
**Fix:** Primary-Button für Bestätigen, Secondary/Text-Button für Ablehnen. Upload in kollabierbaren Bereich.

### 5. MEDIUM — Upload-Formular zu prominent
**Evidence:** Upload nimmt ~40% der Case-Detail-Seite. Für Fälle mit bereits vorhandenen Dokumenten ist das Verschwendung.
**Fix:** Upload in Sidebar oder Collapsible unter der Dokumentenliste.

### 6. MEDIUM — H1-Überschrift zu groß (32px)
**Evidence:** "SYNTHETISCH – Sichtbarer Linux E2E Test RC-017" bricht bei 800px Breite.
**Fix:** H1 auf 24–28px reduzieren. Max-Zeilenlänge für Titel begrenzen.

### 7. MEDIUM — Ungenutzter Leerraum auf datenarmen Seiten
**Evidence:** Legal-Situation, Timeline, Evidence-Pack haben 3+ leere H2-Sektionen → viel vertikaler Raum ohne Inhalt.
**Fix:** Leere Sektionen nur zeigen wenn Daten vorhanden, oder mit klarem "Noch keine Daten" CTA (Slice 2 Verbesserung).

### 8. MEDIUM — Uneinheitliche Informationsdichte
**Evidence:** Case-Liste (kompakt) vs. Document-Detail (hoch) vs. Legal-Sources (kaum Inhalt).
**Fix:** Konsistentes Card-System für alle Listen. Min-Höhe für Cards. Gleiche Abstände.

### 9. LOW — "14 Tagn" Tippfehler
**Evidence:** Document-Detail: "14 Tagn" statt "14 Tage" (Pluralendung fehlt).
**Fix:** Plural-Form korrigieren.

### 10. LOW — Fehlende Mikrointeraktionen
**Evidence:** Keine Transitionen außer Button-Hover. Kein Loading-Feedback bei Upload. Kein Success-Flash nach Case-Erstellung.
**Fix:** CSS-Transitions für Status-Wechsel. Spinner für Upload. Flash-Message nach Mutationen.
