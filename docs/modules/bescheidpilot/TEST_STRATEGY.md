# Test Strategy

## Priorität

1. Datenabfluss verhindern.
2. Frist- und Handlungsaussagen mit Fundstellen absichern.
3. Human Review und expliziten Export erzwingen.
4. Golden Path offline reproduzieren.
5. Website-Claims gegen Evidence prüfen.

## Testebenen

| Ebene | Ziel | Mindest-Evidence |
|---|---|---|
| Static scan | Provider, Endpunkte, Tracker und riskante Dependencies finden | reproduzierbarer Scanbericht |
| Unit | Extraktion, Unsicherheit, Redaction und Exportregeln | automatisierte Tests |
| Contract | Local-only-Core ohne Netzwerkberechtigung | Network-Deny-Test |
| Integration | Golden Path mit synthetischem Fixture | erwartete strukturierte Ausgabe |
| Validation | zwanzig Fälle gegen Goldstandard | Fehler- und Limitationsbericht |
| UI | Human Review, Barrierefreiheit, Fehlerzustände | Testprotokoll |
| Website | Claims, Tracker, JSON und lokale Assets | `validate_public_claims.py` |

## Pflichtfälle

- Netzwerk blockiert
- DNS/Endpoint nicht erreichbar
- Remote-Provider-Dependency eingebracht
- sensible Marker in Logausgabe
- fehlende oder widersprüchliche Frist
- fehlende Fundstelle
- Export ohne Review
- ungültige Website-Evidence-Datei
- verbotener öffentlicher Claim

## Aktueller Status

Implementiert und lokal reproduzierbar:

- Website-Claim-Validierung mit vier negativen und positiven Unit-Tests
- initialer Network-Deny-Harness für Socket, DNS, `urllib`, HTTP und HTTPS
- synthetischer lokaler Textanalysepfad unter Network-Deny
- Offline-Mode-Reality-Test ohne API-Keys oder Remote-Konfiguration
- negative Offline-Fixtures für Netzwerkpflicht, Remote-Credentials und
  erforderliche Endpoints
- statischer Produktcode-Scan für Netzwerk-, Upload-, Provider- und
  Telemetriepfade
- No-Remote-LLM-Guardrail-Test mit API-Key-, Remote-Fallback- und
  Provider-Denylist-Prüfung
- No-Cloud-OCR-Guardrail-Test mit Cloud-OCR-API-Key-, Dokument-Upload- und
  OCR-Fallback-Prüfung
- No-Sensitive-Logs-Guardrail-Test mit Redaction-, Logging- und
  Exception-Prüfung
- dedizierter GitHub-Actions-Workflow `.github/workflows/local-only-guardrails.yml`

Externe anonymisierte Dokumenttests:
- 5 lokal durchgeführte externe anonymisierte Dokumenttests
- 3 PASS, 2 LIMIT, 0 FAIL, 0 Critical Errors
- Ergebnisse nur aggregiert dokumentiert (siehe EXTERNAL_DOCUMENT_TEST_REPORT.md)
- Keine Originaldokumente oder personenbezogenen Daten committed
- Issue #52 abgeschlossen als GREEN_PARTIAL

Reproduktionsbefehle:

```bash
python scripts/validate_public_claims.py
python scripts/guardrail_check.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Network-Deny und Offline Mode sind für den initialen Python-Harness jeweils
`GREEN_PARTIAL`; No Remote LLM, No Cloud OCR und No Sensitive Logs sind initial
`GREEN_PARTIAL` belegt; der Produktstatus bleibt `YELLOW`. Externe Dokumenttests
sind initial `GREEN_PARTIAL` belegt (5 Tests, aggregiert). Die Tests decken
noch keinen echten Golden Path, keine OCR, keine Speicherung, keinen Export
und keine native App-Laufzeit ab. Der vollständige Offline-Golden-Path und
Vertical-Slice-Gates bleiben offen.
