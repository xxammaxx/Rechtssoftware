# Erster Start

**PrivateLegalNavigator v1.0.0-rc.2**

Nach der Installation können Sie die Anwendung in wenigen Minuten zum ersten Mal starten und Ihren ersten Fall anlegen.

---

## 1. Anwendung starten

Öffnen Sie eine PowerShell und wechseln Sie in das Verzeichnis mit den entpackten Installationsdateien:

```powershell
cd C:\Downloads\PrivateLegalNavigator
```

Starten Sie die Anwendung:

```powershell
.\start.ps1
```

Was passiert:
1. Python wird im installierten virtuellen Umfeld gestartet
2. Die Anwendung bindet an `http://127.0.0.1:8000` (nur Ihr Rechner)
3. Die Datenbank wird automatisch angelegt (falls nicht vorhanden)
4. Ein Health-Check prüft, ob der Server bereit ist
5. Ihr Standard-Browser öffnet sich mit der Fallübersicht

> **Erwartete Dauer:** 5–15 Sekunden beim ersten Start.

---

## 2. Browser-Oberfläche

Nach dem Start sehen Sie die Fallübersichtsseite unter:

```
http://127.0.0.1:8000/ui/cases
```

Die Oberfläche ist deutsch und führt Sie durch alle Funktionen.

---

## 3. Ersten Fall anlegen

Klicken Sie auf **"Neuen Fall anlegen"** (oder den entsprechenden Button).

Geben Sie ein:
- **Fallname** (z. B. "Widerspruch Jobcenter März 2025")
- **Aktenzeichen** (optional, z. B. das Aktenzeichen der Behörde)
- **Beschreibung** (optional, z. B. eine kurze Notiz zum Fall)

Klicken Sie auf **"Speichern"**.

Der Fall wird angelegt und erscheint in der Fallübersicht.

---

## 4. PDF-Dokument hochladen

Klicken Sie auf den soeben angelegten Fall, um die Falldetailseite zu öffnen.

Klicken Sie auf **"Dokument hochladen"** und wählen Sie eine PDF-Datei von Ihrem Computer aus.

> **Hinweise:**
> - Nur PDF-Dateien werden akzeptiert (Endung `.pdf`)
> - Die maximale Dateigröße beträgt **20 MB**
> - Gescannte PDFs (Bilder ohne Text) können nicht verarbeitet werden

Nach dem Upload sehen Sie das Dokument in der Dokumentenliste.

---

## 5. Extrahierten Text anzeigen

Klicken Sie in der Dokumentenliste auf das hochgeladene Dokument.

Die Anwendung zeigt Ihnen:
- **Dokumentinformationen:** Name, Größe, Upload-Datum
- **Extrahierter Text:** Der automatisch ausgelesene Text aus dem PDF

> **Hinweis:** Der Text wird automatisch extrahiert, sobald das PDF hochgeladen wird. Bei sehr großen Dokumenten kann dies einige Sekunden dauern. Nur digital erstellte PDFs (nicht gescannt) werden unterstützt.

---

## 6. Nächste Schritte

Nachdem Sie Ihren ersten Fall angelegt und ein Dokument hochgeladen haben, können Sie:

- **Dokument klassifizieren lassen** — Die Anwendung erkennt automatisch, ob es sich um einen Bescheid, eine Rechnung, eine Mahnung oder einen anderen Dokumenttyp handelt.
- **Fristen erkennen lassen** — Die Anwendung sucht nach Datumsangaben und möglichen Fristen im Text.
- **Rechtsquellen durchsuchen** — Öffnen Sie die Rechtsquellenseite unter `http://127.0.0.1:8000/ui/legal-sources`, um Gesetze zu durchsuchen.
- **Eine Sicherung erstellen** — Siehe [BACKUP-RESTORE.md](BACKUP-RESTORE.md).

Eine vollständige Anleitung durch alle Funktionen finden Sie im [USER-GUIDE.md](USER-GUIDE.md).

---

## Anwendung beenden

Um die Anwendung zu beenden, führen Sie im Installationsverzeichnis aus:

```powershell
.\stop.ps1
```

Oder schließen Sie das PowerShell-Fenster. Die Daten bleiben dabei erhalten.
