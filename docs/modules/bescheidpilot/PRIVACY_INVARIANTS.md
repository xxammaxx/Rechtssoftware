# Privacy Invariants

## Leitsatz

**Der Bescheid verlässt das Gerät nicht.**

BescheidPilot verarbeitet Bescheide vollständig lokal auf dem Gerät. Es werden keine Bescheide, Bilder, OCR-Texte, Fristen, Zusammenfassungen oder Antwortentwürfe an Server, Cloud-KI-Dienste, Telemetrie-Systeme oder externe APIs hochgeladen.

Der aktuelle Nachweisstatus wird auf der Evidence-Seite dokumentiert.

## Verbindliche Invarianten

1. **Zero upload:** Dokumente und daraus abgeleitete Inhalte dürfen keinen Remote-Endpunkt erreichen.
2. **Offline-first:** Der Golden Path muss bei vollständig blockiertem Netzwerk funktionieren.
3. **Keine Remote-KI:** Keine Remote-LLM-/SLM-Anbieter, Provider-SDKs oder versteckten Fallbacks.
4. **Keine Cloud-OCR:** Bilder und OCR-Texte bleiben im lokalen Prozess.
5. **Keine sensiblen Logs:** Inhalte, Fundstellen, Fristen und Entwürfe erscheinen nicht in Logs oder Telemetrie.
6. **Expliziter Export:** Export erfolgt nur nach sichtbarer Nutzeraktion an ein lokal gewähltes Ziel.
7. **Human Review:** Konsequenzielle Ausgabe erfordert die Prüfung von Fundstellen und Entwurf.
8. **Source Evidence:** Extraktionen zeigen die zugrunde liegende Textstelle und Unsicherheit.
9. **Fail closed:** Eine unklare Komponente darf nicht auf einen Remote-Dienst ausweichen.
10. **Keine automatische Kommunikation:** BescheidPilot sendet nichts automatisch an Behörden oder Dritte.

## Nachweisregel

Eine Invariante erhält erst `Pass`, wenn Codefundstelle, automatisierter Test und dokumentierter Audit vorliegen. Architekturabsicht allein bleibt `Not checked` oder `YELLOW`.

## Aktueller Nachweisstand

- **Zero upload:** `YELLOW`; statischer Scan und Network-Deny-Harness bestehen,
  aber der echte Produktdatenfluss fehlt.
- **Offline-first:** `GREEN_PARTIAL` für den minimalen Python-Harness. Er läuft
  ohne Netzwerk, API-Keys oder Remote-Endpunkte. Der vollständige Golden Path
  mit Extraktion, Evidence, Entwurf, Review und Export existiert noch nicht.
- **Keine Remote-KI / Cloud-OCR / sensiblen Logs:** No-Remote-LLM-Guardrail
  ist initial `GREEN_PARTIAL` (Issue #13). No-Cloud-OCR-Guardrail ist initial
  `GREEN_PARTIAL` (Issue #14). No-Sensitive-Logs-Guardrail ist initial
  `GREEN_PARTIAL` (Issue #15).

Der Local-only-Gesamtstatus bleibt `YELLOW`.
