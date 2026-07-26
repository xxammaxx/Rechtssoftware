# Bekannte Einschränkungen

**PrivateLegalNavigator v1.0.0-rc.1**

---

Diese Seite beschreibt, was die Software **nicht** kann und wo Sie mit eigenen Einschränkungen rechnen müssen.

---

## 1. Keine Rechtsberatung

**Diese Software bietet keine Rechtsberatung.** Sie ist ein Werkzeug zur Organisation Ihrer rechtlichen Angelegenheiten, aber:

- Sie trifft **keine automatischen Rechtsentscheidungen**
- Sie bewertet **keine Rechtslage** automatisch
- Sie gibt **keine Handlungsempfehlungen**
- Sie erstellt **keine Schreiben oder Anträge**

Jede rechtlich relevante Entscheidung müssen Sie selbst treffen oder mit einer Rechtsanwältin oder einem Rechtsanwalt besprechen.

---

## 2. Keine verbindliche Fristberechnung

Alle Fristberechnungen sind **unverbindliche Vorschauen**.

| Nicht berücksichtigt | Grund |
|---------------------|-------|
| Gesetzliche Feiertage | Werden je nach Bundesland unterschiedlich geregelt |
| Wochenenden | Samstage und Sonntage werden nicht erkannt |
| Zustellungsregeln | Die Berechnung von Zustellungsfristen ist komplex |
| Sonderregelungen | Viele Gesetze haben individuelle Fristregeln |

Die Berechnung dient als **erste Orientierung**. Eine rechtsverbindliche Fristberechnung müssen Sie selbst vornehmen oder von einer Fachperson durchführen lassen.

---

## 3. Keine Texterkennung für gescannte Dokumente (OCR)

Die Anwendung kann nur den Text aus **digital erstellten PDFs** auslesen.

- **Funktioniert:** PDFs, die am Computer erstellt wurden (z. B. mit Word, einem Online-Formular, etc.)
- **Funktioniert nicht:** Eingescannte Papierdokumente, Faxe, Fotos von Dokumenten

Für gescannte Dokumente benötigen Sie eine separate OCR-Software (Optical Character Recognition), um den Text zu extrahieren. Der extrahierte Text kann dann manuell in die Anwendung übernommen werden.

---

## 4. Nur lokale Nutzung

- Die Anwendung läuft **nur auf Ihrem Computer**
- Sie ist **nicht über das Netzwerk erreichbar** (Bindung an 127.0.0.1)
- Es gibt **keine Cloud-Synchronisation**
- Sie können **nicht von mehreren Geräten gleichzeitig** darauf zugreifen
- Es gibt **keine Mehrbenutzer-Funktion**

---

## 5. Keine Verschlüsselung der Daten im Ruhezustand

- Die Datenbank und die Dokumente liegen **unverschlüsselt** auf Ihrer Festplatte
- Ein Zugriff auf Ihre Dateien durch andere Programme oder Personen ist nicht ausgeschlossen
- Für zusätzliche Sicherheit können Sie Ihre Festplatte verschlüsseln (z. B. mit BitLocker unter Windows)

---

## 6. Gesetze im Internet (GII) als konsolidierte Quelle

Die integrierten Rechtsquellen beziehen ihre Daten von **gesetze-im-internet.de (GII)**.

- GII ist eine **konsolidierte** (zusammengefasste) Quelle, **kein amtliches Verkündungsblatt**
- Es kann zu **zeitlichen Verzögerungen** bei Aktualisierungen kommen
- Neue Gesetzesänderungen sind möglicherweise nicht sofort verfügbar
- Für die verbindliche Rechtslage ist das **Bundesgesetzblatt** maßgeblich

---

## 7. Menschliche Prüfung immer erforderlich

Jede Ausgabe der Software, die rechtlich relevant sein könnte, erfordert Ihre Prüfung. Automatisch erkannte:

- **Dokumentklassifikationen** — Können falsch sein
- **Fristkandidaten** — Können fehlerhaft oder unvollständig sein
- **Bezugsereignisse** — Können falsch erkannt worden sein
- **Berechnungen** — Können fehlerhaft sein
- **Normverknüpfungen** — Können unpassend sein

Verlassen Sie sich nie blind auf die automatischen Ergebnisse.

---

## 8. Nicht implementierte Funktionen

Folgende Funktionen sind **nicht** Teil dieser Version und auch nicht geplant:

- Authentifizierung und Mehrbenutzerbetrieb
- Verschlüsselung der Datenbank
- Cloud-Synchronisation
- Automatische Entwurfserstellung für Schreiben
- OCR für gescannte Dokumente
- Vollständig automatisierte Fristberechnung
- Mobile App
- Integration mit behördlichen Systemen (z. B. ELSTER, beA)

---

## Zusammenfassung

| Bereich | Einschränkung |
|---------|--------------|
| Rechtsberatung | ❌ Wird nicht angeboten |
| Fristberechnung | ⚠️ Unverbindliche Vorschau |
| OCR | ❌ Nur digital erstellte PDFs |
| Netzwerk | ⚠️ Lokal nur auf einem Rechner |
| Verschlüsselung | ❌ Keine Ruhezustand-Verschlüsselung |
| Rechtsquellen | ⚠️ Konsolidierte Quelle, kein amtliches Blatt |
| Menschliche Prüfung | ✅ Immer erforderlich |
| Multi-User | ❌ Nicht unterstützt |
