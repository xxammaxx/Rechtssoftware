<!--
Sync Impact Report
==================
Version change: (keine) → 1.0.0
Bump rationale: Erste formale Versionierung. MINOR-Änderungen:
  - Governance-Abschnitt hinzugefügt
  - Präambel hinzugefügt
  - Prinzip 13 "Keine Telemetrie" hinzugefügt
  - Prinzip 14 "Kein Push oder Merge ohne Remote-Freigabe" hinzugefügt
  - Prinzip 15 "Spec-Kit-gesteuerte Entwicklung" hinzugefügt

Modified principles: (keine)
Added sections:
  - Präambel
  - Governance (Änderungsverfahren, Versionierung, Compliance)
Added principles:
  - #13 Keine Telemetrie (vorher in #2 Privacy by Design enthalten)
  - #14 Kein Push oder Merge ohne Remote-Freigabe
  - #15 Spec-Kit-gesteuerte Entwicklung
Removed sections: (keine)
Templates requiring updates: (keine — keine Vorlagendateien vorhanden)
TODOs: (keine)
-->

# PrivateLegalNavigator — Verfassung (Constitution)

**Version:** 1.0.0
**Ratifikationsdatum:** 2026-07-12
**Letzte Änderung:** 2026-07-18
**Status:** Aktiv

## Präambel

Diese Verfassung definiert die nicht-verhandelbaren Prinzipien für Entwicklung,
Betrieb und Governance von PrivateLegalNavigator. Jede Entscheidung – ob
technisch, fachlich oder prozessual – muss diesen Prinzipien entsprechen.
Verstöße sind zu dokumentieren und zu begründen.

Die Verfassung gilt als lebendes Dokument. Änderungen folgen dem Governance-
Verfahren in Abschnitt 16.

---

## 1. Local-only als Standard

Jegliche Verarbeitung von Falldaten, Dokumenten und Nutzereingaben erfolgt
ausschließlich lokal. Cloud-Dienste, externe APIs und Remote-Processing sind
verboten, sofern nicht durch eine explizite, dokumentierte Architekturentscheidung
autorisiert.

*Rationale: Datenschutz durch Architektur. Lokale Verarbeitung ist die
grundlegende Sicherheitszusage dieser Software.*

## 2. Privacy by Design

Datenschutz ist kein nachträgliches Feature. Jede Komponente muss von Beginn an
so entworfen sein, dass personenbezogene Daten den lokalen Rechner nicht
verlassen. Personenbezogene Daten dürfen nicht in Logs, Fehlermeldungen oder
Diagnoseausgaben erscheinen.

*Rationale: Privacy by Design ist gesetzlich verankert (Art. 25 DSGVO) und
entspricht dem Grundsatz des datenschutzrechtlichen "Built-in".*

## 3. Keine automatische Rechtsentscheidung

Die Software bewertet keine Rechtslage automatisch. Sie unterstützt den Nutzer
bei der Strukturierung und Verwaltung eigener Angelegenheiten, trifft aber
keine eigenständigen rechtlichen Bewertungen oder Empfehlungen.

*Rationale: Rechtsberatung ist Rechtsdienstleistung (RDG) und darf nicht
automatisiert erfolgen. Die Software bleibt Werkzeug, nicht Berater.*

## 4. Human Review

Jede rechtlich oder behördlich relevante Ausgabe muss durch einen Menschen
geprüft werden. Automatisierte Kommunikation an Behörden, Gerichte oder Dritte
ist verboten. Die Software erzeugt keine rechtsverbindlichen Schreiben ohne
menschliche Autorisierung.

*Rationale: Die Letztverantwortung liegt beim Menschen. Automatisierte
Kommunikation birgt Haftungsrisiken und verstößt gegen den Grundsatz der
menschlichen Aufsicht.*

## 5. Modulare, nachvollziehbare Architektur

Die Architektur folgt einem modularen Monolithen mit klar getrennten Schichten:

    API → Application → Domain → Infrastructure

Kein Microservice, kein verteiltes System ohne dokumentierte
Architekturentscheidung (ADR). Jede Schicht hat genau eine Verantwortung und
kennt nur die direkt untergeordnete Schicht.

*Rationale: Schichtentrennung ermöglicht Testbarkeit, Austauschbarkeit und
nachvollziehbare Abhängigkeiten. Verteilte Systeme erhöhen die Komplexität
ohne Nutzen für einen lokalen Einzelnutzer.*

## 6. Kleine vertikale Slices

Jeder Entwicklungslauf implementiert genau einen vertikalen Slice: einen
vollständigen Pfad von außen (API/UI) bis zur Persistenz. Keine horizontalen
Schichten ohne Durchstich.

*Rationale: Vertikale Slices liefern sofortigen Nutzwert und vermeiden
"Big Design Up Front" ohne funktionierenden Code.*

## 7. Red Tests vor Featureimplementierung

Vor jeder Featureimplementierung stehen fehlschlagende Tests, die das
gewünschte Verhalten spezifizieren (Red-Green-Refactor). Erst nach Red Tests
wird implementiert. Ein Feature gilt erst dann als vollständig, wenn alle
Tests grün durchlaufen.

*Rationale: Tests spezifizieren Verhalten und verhindern
Regressionsfehler. Red-Green-Refactor ist die disziplinierte Form von
Specification by Example.*

## 8. Lokale Gates als Primärwahrheit

Der Zustand von Repository, Code, Tests und lokaler Runtime hat Vorrang vor
Dokumentation, Erinnerung oder externen Quellen. Nur was lokal verifiziert
wurde, darf als "funktionsfähig" gelten. Remote-CI-Ergebnisse bestätigen die
lokale Wahrheit, ersetzen sie nicht.

*Rationale: Lokale Gates verhindern Abhängigkeit von externen Diensten und
ermöglichen Offline-Entwicklung.*

## 9. Keine Remote-CI ohne Freigabe

GitHub Actions, Remote-CI, Auto-Merge und automatisierte Deployments sind ohne
explizite menschliche Freigabe verboten. CI/CD-Pipelines dürfen erst nach
Prüfung ihrer Sicherheits-, Kosten- und Datenflussimplikationen aktiviert
werden.

*Rationale: Remote-CI bedeutet Codeausführung auf fremder Infrastruktur und
birgt Risiken für Vertraulichkeit und Verfügbarkeit.*

## 10. Evidence vor Erfolgsmeldung

Jede Behauptung über Funktionsfähigkeit, Teststatus oder Codequalität muss
durch lokale, reproduzierbare Evidenz belegt sein. "Sollte funktionieren" ist
kein akzeptabler Zustand. Keine Behauptung ohne Ausführung, kein grüner Haken
ohne Lauf.

*Rationale: Evidenz ist die Grundlage von Vertrauen. Ohne reproduzierbare
Nachweise sind Aussagen wertlos.*

## 11. Dokumentation als Living Truth Mirror

Dokumentation spiegelt den tatsächlichen, verifizierten Zustand der Software.
Sie wird nach jedem relevanten Lauf aktualisiert. Widerspricht sie der
Realität, gilt sie als veraltet (stale) und muss korrigiert werden, bevor
darauf aufgebaut wird.

*Rationale: Veraltete Dokumentation ist gefährlicher als keine
Dokumentation. Der "Living Truth Mirror"-Ansatz verhindert Wissensverlust.*

## 12. Keine produktiven oder personenbezogenen Testdaten

Tests verwenden ausschließlich synthetische Daten. Testdaten beginnen mit dem
Präfix "SYNTHETISCH –". Keine echten Namen, Aktenzeichen, Adressen,
Falldaten oder anderen personenbezogenen Informationen in Tests,
Testdatendateien oder Test-Datenbanken.

*Rationale: Produktive Daten in Tests sind ein Datenschutzverstoß und
erschweren die automatisierte Ausführung.*

## 13. Keine Telemetrie

Die Software überträgt keinerlei Nutzungs-, Analyse- oder Fehlerdaten an
Dritte oder externe Dienste. Analytics-Tracking, Error-Reporting-Dienste und
Usage-Metriken sind ohne explizite Sicherheitsentscheidung verboten.
Telemetrie ist eine Verletzung des Prinzips der Datenminimierung (Art. 5
DSGVO).

*Rationale: Telemetrie ist der häufigste unbeabsichtigte Datenabfluss in
lokalen Anwendungen. Fehlertoleranz muss lokal erreicht werden.*

## 14. Kein Push oder Merge ohne Remote-Freigabe

Lokale Commits sind jederzeit erlaubt, Push- und Merge-Operationen auf
Remote-Branches (insbesondere main/master) erfordern eine explizite
menschliche Freigabe. Automatisierte Remote-Operationen sind ohne
ausdrückliche Autorisierung verboten.

*Rationale: Remote-Push und -Merge sind die Grenze zwischen lokaler und
öffentlicher Sphäre. Unautorisierte Remote-Operationen können nicht
zurückgenommen werden.*

## 15. Spec-Kit-gesteuerte Entwicklung

Jeder Entwicklungsschritt folgt dem Spec-Kit-Ablauf:

    Verfassung → Spezifikation → Klärung → Plan → Aufgaben → Implementierung

Keine Implementierung ohne vorherige Spezifikation. Keine Spezifikation ohne
Prinzipienkonformität. Keine Aufgaben ohne Plan. Neue Prinzipien oder
Änderungen an bestehenden Prinzipien durchlaufen zuerst die Verfassung.

*Rationale: Der Spec-Kit-Ablauf stellt sicher, dass jede Änderung
wohlbegründet, spezifiziert und planvoll umgesetzt wird. Er verhindert
Ad-hoc-Entwicklung und nicht nachvollziehbare Entscheidungen.*

## 16. Governance

### 16.1 Änderungsverfahren

1. Änderungen an dieser Verfassung erfolgen durch Pull Request mit
   dokumentierter Begründung (Rationale, Auswirkung, alternative Erwägungen).
2. Jede Änderung muss durch den Projektinhaber genehmigt werden.
3. Wesentliche Änderungen (MAJOR und MINOR gemäß Versionierungsregeln)
   erfordern eine 48-stündige Überlegungsfrist zwischen Vorschlag und
   Inkraftsetzung.
4. Eilkorrekturen (PATCH) sind ohne Frist zulässig, müssen aber innerhalb
   von 7 Tagen nachträglich bestätigt werden.

### 16.2 Versionierung

Die Verfassung folgt semantischer Versionierung (MAJOR.MINOR.PATCH):

- **MAJOR:** Prinzipienentfernung oder -neudefinition mit
  Rückwärtsinkompatibilität.
- **MINOR:** Neues Prinzip oder wesentlich erweiterte Leitlinien.
- **PATCH:** Klarstellungen, Formulierungskorrekturen, nicht-semantische
  Verfeinerungen.

### 16.3 Compliance-Überprüfung

1. Jedes Milestone-Review (M1, M2, …) beinhaltet eine
   Verfassungskonformitätsprüfung.
2. Verstöße gegen Verfassungsprinzipien müssen dokumentiert, priorisiert und
   innerhalb des nächsten Meilensteins adressiert werden.
3. Nach jeder MAJOR- oder MINOR-Änderung erfolgt eine vollständige
   Konformitätsprüfung aller aktiven Spezifikationen und Aufgaben.
