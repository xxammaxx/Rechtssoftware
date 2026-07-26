# Benutzerhandbuch

**PrivateLegalNavigator v1.0.0-rc.1**

Dieses Handbuch führt Sie Schritt für Schritt durch den gesamten Arbeitsablauf — vom Anlegen eines Falls bis zum Export Ihrer gesammelten Informationen.

---

## Übersicht

Die Anwendung hilft Ihnen bei der Organisation Ihrer rechtlichen Angelegenheiten:

1. **Fall anlegen** — Einen neuen Vorgang erstellen
2. **PDF hochladen** — Behördliche Schreiben digital erfassen
3. **Text extrahieren** — Den Inhalt des PDFs auslesen
4. **Dokument klassifizieren** — Die Art des Dokuments erkennen
5. **Fristen erkennen** — Mögliche Termine und Fristen identifizieren
6. **Bezugsdatum bestätigen** — Das relevante Datum festlegen
7. **Berechnungsvorschau** — Eine unverbindliche Fristberechnung anzeigen
8. **Rechtsquellen durchsuchen** — Gesetzestexte finden
9. **Norm mit Fall verknüpfen** — Passende Gesetze Ihrem Fall zuordnen
10. **Zeitleiste erstellen** — Wichtige Ereignisse festhalten
11. **Evidence Pack exportieren** — Eine Zusammenstellung aller Informationen

---

## 1. Fall anlegen

**Browser öffnen:** http://127.0.0.1:8000/ui/cases

Klicken Sie auf **"Neuen Fall anlegen"**.

| Feld | Erforderlich | Beschreibung |
|------|-------------|-------------|
| Fallname | Ja | Z. B. "Widerspruch gegen Bußgeldbescheid" |
| Aktenzeichen | Nein | Ihr Aktenzeichen oder das der Behörde |
| Beschreibung | Nein | Freitext-Notiz zum Fall |

Klicken Sie auf **"Speichern"**. Der Fall erscheint in der Übersicht.

---

## 2. PDF-Dokument hochladen

Öffnen Sie einen Fall durch Klicken auf den Fallnamen.

Klicken Sie auf **"Dokument hochladen"**.

Wählen Sie eine PDF-Datei von Ihrem Computer aus.

**Wichtig:**
- Nur PDF-Dateien (Endung `.pdf`)
- Maximale Größe: **20 Megabyte**
- Das PDF sollte digital erstellt sein (kein eingescanntes Papierdokument)

Nach dem Upload erscheint das Dokument in der Liste der Falldokumente.

---

## 3. Extrahierten Text anzeigen

Klicken Sie in der Dokumentenliste auf ein Dokument.

Die Anwendung zeigt Ihnen:
- **Dateiname** und **Größe**
- **Hochladedatum**
- **Extrahierter Text** — der automatisch ausgelesene Inhalt des PDFs

Sie können den Text markieren und kopieren.

---

## 4. Dokument klassifizieren

Öffnen Sie ein Dokument. Die Anwendung klassifiziert das Dokument automatisch.

Mögliche Klassifikationen:

| Typ | Beschreibung |
|-----|-------------|
| Bescheid | Amtliche Mitteilung oder Entscheidung |
| Rechnung | Zahlungsaufforderung |
| Mahnung | Erinnerung an eine ausstehende Zahlung |
| Antrag | Von Ihnen gestellter Antrag |
| Gerichtsschreiben | Mitteilung eines Gerichts |
| Sonstiges | Andere Dokumenttypen |

Die Klassifikation erscheint direkt im Dokumentendetail. Sie dient als Orientierung und ersetzt keine eigene Prüfung.

---

## 5. Fristkandidaten erkennen

Öffnen Sie ein Dokument und klicken Sie auf **"Fristen erkennen"**.

Die Anwendung durchsucht den extrahierten Text nach möglichen Fristen und Terminen. Sie erhalten eine Liste mit:

- **Gefundene Datumsangaben** — Alle Daten, die im Text gefunden wurden
- **Fristkandidaten** — Datumsangaben, die wie eine Frist aussehen
- **Kontext** — Der umgebende Text, der den Fund erklärt

Prüfen Sie die Vorschläge. Nicht alle gefundenen Daten sind tatsächlich Fristen.

---

## 6. Bezugsdatum bestätigen

Wählen Sie aus der Liste der Fristkandidaten einen Eintrag aus.

Klicken Sie auf **"Bezugsereignis-Kandidaten prüfen"**.

Die Anwendung zeigt Vorschläge für das relevante Bezugsdatum. Sie haben folgende Optionen:

| Aktion | Bedeutung |
|--------|-----------|
| **Bestätigen (Confirm)** | Dieses Datum ist korrekt und wird für Berechnungen verwendet |
| **Ablehnen (Reject)** | Dieses Datum ist nicht relevant |
| **Manuell eingeben** | Ein abweichendes Datum selbst eintragen |
| **Korrigieren (Correct)** | Nachträgliche Korrektur eines bestätigten Datums |
| **Widerrufen (Revoke)** | Eine Bestätigung rückgängig machen |

Der Verlauf aller Bestätigungen wird dokumentiert und kann jederzeit eingesehen werden.

---

## 7. Berechnungsvorschau anzeigen

Nachdem Sie ein Bezugsdatum bestätigt haben, klicken Sie auf **"Berechnungsvorschau"**.

Die Anwendung zeigt eine **unverbindliche** Berechnung:

- **Geschätzte Dauer in Tagen** — Berechnet aus dem bestätigten Bezugsdatum
- **Geschätzte Dauer in Wochen** — Für einen besseren zeitlichen Überblick
- **Berechnungs-Trace** — Welche Werte in die Berechnung eingeflossen sind

**Wichtig:** Diese Berechnung ist keine rechtsverbindliche Fristberechnung. Gesetzliche Feiertage, Wochenenden und Zustellungsregeln werden nicht berücksichtigt. Jede Berechnung erfordert Ihre eigene Prüfung.

---

## 8. Rechtsquellen durchsuchen

Öffnen Sie die Rechtsquellenseite:

```
http://127.0.0.1:8000/ui/legal-sources
```

Hier sehen Sie den Status der eingebundenen Rechtsquellen.

### Volltextsuche

Unter `http://127.0.0.1:8000/ui/legal-sources/search?q=...` können Sie Gesetze durchsuchen:

1. Geben Sie einen Suchbegriff ein (z. B. "Widerspruch", "Frist", "§ 70 VwGO")
2. Die Anwendung durchsucht den gesamten Rechtskorpus
3. Die Ergebnisse zeigen den passenden Gesetzesausschnitt mit Kontext

### Normdetail

Klicken Sie auf ein Suchergebnis, um die vollständige Vorschrift zu sehen:
- **Normtext** — Der Gesetzeswortlaut
- **Abkürzung** — Z. B. "VwGO" für Verwaltungsgerichtsordnung
- **Autoritätsstufe** — Die Vertrauenswürdigkeit der Quelle
- **Stand-Datum** — Letztes Aktualisierungsdatum

---

## 9. Norm mit Fall verknüpfen

Auf der Rechtslagenseite eines Falls (`/ui/cases/{id}/legal-situation`) können Sie Gesetze mit Ihrem Fall verknüpfen:

1. Klicken Sie auf **"Norm vorschlagen"**
2. Geben Sie die Gesetzesfundstelle ein (z. B. "§ 70 VwGO")
3. Die Anwendung sucht die passende Norm und schlägt eine Verknüpfung vor
4. Sie können die Verknüpfung **bestätigen**, **ablehnen** oder **korrigieren**

Verknüpfte Normen erscheinen in der Übersicht der Rechtslage Ihres Falls.

---

## 10. Zeitleiste mit Ereignissen

Auf der Rechtsverlaufsseite (`/ui/cases/{id}/legal-timeline`) können Sie Ereignisse zu Ihrem Fall erfassen:

1. Klicken Sie auf **"Ereignis anlegen"**
2. Wählen Sie den Ereignistyp:

| Ereignistyp | Beispiel |
|-------------|----------|
| DOCUMENT_ISSUED | Bescheid wurde ausgestellt |
| RECEIVED | Sie haben ein Schreiben erhalten |
| DEADLINE | Eine Frist läuft ab |
| ACTION_TAKEN | Sie haben Widerspruch eingelegt |
| DECISION | Entscheidung der Behörde |
| OTHER | Sonstiges Ereignis |

3. Geben Sie Datum und Beschreibung ein
4. Speichern Sie das Ereignis

Alle Ereignisse werden chronologisch angezeigt. Sie können Ereignisse nachträglich **bestätigen**, **korrigieren** oder **widerrufen**.

---

## 11. Evidence Pack exportieren

Öffnen Sie die Seite:

```
http://127.0.0.1:8000/ui/cases/{id}/evidence-pack
```

Das Evidence Pack ist eine gebündelte Zusammenstellung aller bestätigten Informationen Ihres Falls:

- **Bestätigte Fakten** — Von Ihnen geprüfte und bestätigte Angaben
- **Rechtsereignisse** — Alle Ereignisse in der Zeitleiste
- **Rechtsfragen** — Offene und geklärte rechtliche Fragen
- **Verknüpfte Normen** — Die Ihrem Fall zugeordneten Gesetze
- **Quellen-Snapshots** — Gespeicherte Gesetzesfassungen

Das Evidence Pack dient als **Grundlage für Ihre eigene rechtliche Prüfung**. Es ersetzt keine Rechtsberatung.

---

## Wichtige Hinweise

- **Keine Rechtsberatung:** Diese Software trifft keine automatischen Rechtsentscheidungen.
- **Menschliche Prüfung erforderlich:** Jede rechtlich relevante Ausgabe müssen Sie selbst prüfen.
- **Nicht rechtsverbindlich:** Alle Berechnungen sind unverbindliche Vorschauen.
- **Lokal:** Alle Daten verbleiben auf Ihrem Computer.
