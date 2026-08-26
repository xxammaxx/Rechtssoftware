# Evidence Standard

## Grundregel

Keine Erfolgsmeldung, kein GREEN-Status und keine öffentliche Funktionsbehauptung ohne überprüfbare Evidence.

## Zulässige Evidence

- automatisierter Test mit reproduzierbarem Befehl und Ergebnis
- Codefundstelle mit Review
- Audit mit Datum, Scope und Befund
- Demo mit unverändertem Fixture und dokumentierten Grenzen
- Pull Request mit Testausgabe
- Release mit nachvollziehbarer Artefaktversion
- geschlossenes Issue mit verlinkter Evidence

## Nicht ausreichend

- Absichtserklärung
- Mockup ohne Implementierung
- ungeprüfter Screenshot
- manuelle Behauptung ohne Reproduktionsweg
- geschlossenes Issue ohne Nachweis
- Marketingtext

## Statusdefinitionen

- `Missing`: keine verwertbare Evidence
- `Partial`: ein Teil ist belegt, wesentliche Gates fehlen
- `Complete`: Akzeptanzkriterien und Risiken sind überprüfbar dokumentiert
- `Not applicable`: nachvollziehbar nicht relevant

## Kritische Gates

Local-only, Offline, No Remote LLM (initial GREEN_PARTIAL), No Cloud OCR (initial GREEN_PARTIAL), No Sensitive Logs (initial GREEN_PARTIAL), Human Review, Source Evidence und Public Claim Evidence benötigen konkrete Test- oder Audit-Nachweise.
