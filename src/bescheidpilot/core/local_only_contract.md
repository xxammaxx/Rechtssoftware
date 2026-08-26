# Local-only Core Contract

## Invariant

**Der Bescheid verlässt das Gerät nicht.**

BescheidPilot verarbeitet Bescheide vollständig lokal auf dem Gerät. Es werden keine Bescheide, Bilder, OCR-Texte, Fristen, Zusammenfassungen oder Antwortentwürfe an Server, Cloud-KI-Dienste, Telemetrie-Systeme oder externe APIs hochgeladen.

Der aktuelle Nachweisstatus wird auf der Evidence-Seite dokumentiert.

## Required Interface Properties

Future core interfaces must:

1. use local values or file handles only
2. avoid endpoint, credential, tenant, or provider configuration
3. return structured evidence spans and uncertainty
4. emit no document content to logs
5. remain functional with outbound networking denied
6. make export a separate, explicit caller action
7. fail closed when a local model or OCR component is unavailable

## Acceptance Gate

No core implementation is accepted until static dependency checks, Network-Deny tests, sensitive-log tests, and a synthetic offline Golden Path are present.
