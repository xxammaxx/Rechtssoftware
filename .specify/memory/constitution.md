# PrivateLegalNavigator — Constitution

## 1. Local-only als Standard

Jegliche Verarbeitung von Falldaten, Dokumenten und Nutzereingaben erfolgt
ausschließlich lokal. Cloud-Dienste, externe APIs und Remote-Processing sind
verboten, sofern nicht durch eine explizite Architekturentscheidung autorisiert.

## 2. Privacy by Design

Datenschutz ist kein nachträgliches Feature. Jede Komponente muss von Beginn an
so entworfen sein, dass personenbezogene Daten den lokalen Rechner nicht
verlassen.

## 3. Keine automatische Rechtsentscheidung

Die Software bewertet keine Rechtslage automatisch. Sie unterstützt den Nutzer
bei der Strukturierung und Verwaltung eigener Angelegenheiten, trifft aber
keine eigenständigen rechtlichen Bewertungen.

## 4. Human Review

Jede rechtlich oder behördlich relevante Ausgabe muss durch einen Menschen
geprüft werden. Automatisierte Kommunikation an Behörden oder Dritte ist
verboten.

## 5. Modulare, nachvollziehbare Architektur

Die Architektur folgt einem modularen Monolithen mit klar getrennten Schichten:
API → Application → Domain → Infrastructure. Kein Microservice, kein
verteiltes System ohne dokumentierte Entscheidung.

## 6. Kleine vertikale Slices

Jeder Entwicklungslauf implementiert genau einen vertikalen Slice: ein
vollständiger Pfad von außen (API/UI) bis zur Persistenz. Keine horizontalen
Schichten ohne Durchstich.

## 7. Red Tests vor Featureimplementierung

Vor jeder Featureimplementierung stehen fehlschlagende Tests, die das
gewünschte Verhalten spezifizieren. Erst nach Red Tests wird implementiert.

## 8. Lokale Gates als Primärwahrheit

Der Zustand von Repository, Code, Tests und lokaler Runtime hat Vorrang vor
Dokumentation, Erinnerung oder externen Quellen. Remote-CI ist ohne
ausdrückliche Freigabe verboten.

## 9. Keine Remote-CI ohne Freigabe

GitHub Actions, Remote-CI, Auto-Merge und Deployment sind ohne explizite
menschliche Freigabe verboten.

## 10. Evidence vor Erfolgsmeldung

Jede Behauptung über Funktionsfähigkeit, Teststatus oder Codequalität muss
durch lokale, reproduzierbare Evidence belegt sein. Kein "sollte funktionieren".

## 11. Dokumentation als Living Truth Mirror

Dokumentation spiegelt den tatsächlichen, verifizierten Zustand. Sie wird nach
jedem relevanten Lauf aktualisiert. Widerspricht sie der Realität, ist sie
stale.

## 12. Keine produktiven oder personenbezogenen Testdaten

Tests verwenden ausschließlich synthetische Daten. Testdaten beginnen mit dem
Präfix "SYNTHETISCH –". Keine echten Namen, Aktenzeichen, Adressen oder
Falldaten in Tests.
