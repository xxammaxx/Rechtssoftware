# Browser Observation Scope — PrivateLegalNavigator

**Datum:** 31.07.2026
**Run:** RC-020
**Gültig für:** Alle Browser- und HTTP-Beobachtungen im Projekt

---

## Übersicht

Im Projekt existieren vier getrennte Beobachtungskanäle. Diese dürfen **niemals gleichgesetzt** werden.
Jede Evidence muss einen `observation_scope` tragen.

---

## Scope 1: `HTTP_ONLY`

**Werkzeuge:** `curl`, `terminal (httpx)`, `python requests`

**Belegt:**
- HTTP-Statuscode
- Response-Header (Location, Content-Type, CSP, etc.)
- Response-Body (HTML, JSON)
- Redirect-Ketten
- Response-Zeit

**Belegt NICHT:**
- Sichtbare Darstellung im Browser
- DOM-Zustand
- JavaScript-Ausführung
- Nutzerinteraktion
- Browser-Cookies/LocalStorage

**Beispiel korrekt:**
> `curl -L http://127.0.0.1:8000/` → HTTP 200, letzte URL `/ui/cases`

**Beispiel falsch:**
> „Der Browser zeigt die Fallliste." (nur HTTP geprüft)

---

## Scope 2: `AUTOMATION_BROWSER`

**Werkzeuge:** `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_console`

**Session:** Separater Browserbase/Playwright-Browser — **nicht** der Nutzer-Brave.

**Belegt:**
- DOM (Accessibility Tree via Snapshot)
- URL nach Navigation/Redirect
- Seitentitel
- Interaktive Elemente und deren Zustand
- JavaScript-Konsole (Fehler, Warnungen)
- Browser-Netzwerk (Requests, Responses)

**Belegt NICHT automatisch:**
- Zustand des sichtbaren Nutzer-Brave-Fensters
- Cookies/Profil des Nutzer-Browsers
- Visuelles Rendering (kein vision_analysis verfügbar)

**Beispiel korrekt:**
> `AUTOMATION_BROWSER`: `browser_navigate("http://127.0.0.1:8000/")` → final URL `/ui/cases`, Titel „Fälle — PrivateLegalNavigator", 2 Fälle im DOM

**Beispiel falsch:**
> „Der Nutzer sieht die Fallliste." (nur Automationsbrowser geprüft)

---

## Scope 3: `USER_BRAVE_AX`

**Werkzeuge:** `computer_use(action='capture', app='Brave-browser')`, `computer_use(action='list_windows')`

**Session:** Der tatsächliche Nutzer-Desktop, Brave-Browser (PID 15605).

**Belegt:**
- Fensterstruktur und -titel (via AX-Tree)
- Sichtbare Texte (via AX-Tree)
- Fensterposition und Z-Index
- Erkennbare UI-Elemente (Buttons, Links, Labels)

**Belegt NICHT:**
- Vollständiges DOM (kein DevTools-Zugriff)
- JavaScript-Konsole
- Netzwerk-Traffic
- Browser-History
- Nicht-sichtbare Tabs

**Beispiel korrekt:**
> `USER_BRAVE_AX`: Fenster „Rechtssoftware — Entwicklungsplanung" auf Desktop sichtbar, z-index 10

**Beispiel falsch:**
> „Der Nutzerbrowser zeigt keine JS-Fehler." (Konsole nicht zugänglich)

---

## Scope 4: `DESKTOP_SCREENSHOT`

**Werkzeuge:** `computer_use(action='capture', app='screen')`

**Session:** Gesamter sichtbarer Desktop.

**Belegt:**
- Tatsächlich sichtbarer Bildschirminhalt
- Fensterpositionen und Überlappungen
- Sichtbare URL (falls im Screenshot lesbar)
- Sichtbare Fehlermeldungen
- Visueller Gesamtzustand

**Belegt NICHT:**
- DOM-Semantik
- Unsichtbare/überlappte Elemente
- Backend-Zustand
- Exakte Textinhalte (nur pixelbasiert)

**Einschränkung:** Keine Vision-LLM-Analyse verfügbar (kein vision-Provider konfiguriert). Analyse erfolgt über AX-Tree.

**Beispiel korrekt:**
> `DESKTOP_SCREENSHOT`: Gnome-Terminal mit 3 Reitern sichtbar, Brave-Fenster „Positron" im Vordergrund

---

## Evidence-Schema

Jede Browser- oder HTTP-Evidence muss folgendes Schema einhalten:

```json
{
  "run_id": "RC020-...",
  "captured_at": "2026-07-31T16:00:00Z",
  "observation_scope": "HTTP_ONLY|AUTOMATION_BROWSER|USER_BRAVE_AX|DESKTOP_SCREENSHOT",
  "browser_executable": "Brave-browser|Browserbase/Playwright|null",
  "browser_pid": 15605,
  "profile": "user-default|automation-isolated|null",
  "url": "http://127.0.0.1:8000/ui/cases",
  "title": "Fälle — PrivateLegalNavigator",
  "source_tool": "browser_navigate",
  "result": "HTTP 200, 2 Fälle im DOM"
}
```

## Verbotene Formulierungen

| Verboten | Ersatz |
|----------|--------|
| „Browser funktioniert." | „AUTOMATION_BROWSER zeigt /ui/cases mit HTTP 200." |
| „Die Seite ist sichtbar." | „DESKTOP_SCREENSHOT zeigt Browserfenster mit Fallliste." |
| „Alles ist erreichbar." | „HTTP_ONLY: /health=200, /=302→200, /ui/cases=200" |
| „Keine Fehler." | „AUTOMATION_BROWSER console: 0 JS errors" |
