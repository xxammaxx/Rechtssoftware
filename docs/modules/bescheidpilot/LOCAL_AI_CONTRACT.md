# Local AI Contract

BescheidPilot darf sensible Bescheidinhalte nur lokal verarbeiten.

## Erlaubt

- regelbasierte lokale Extraktion
- lokale Heuristiken
- lokale Modelle
- lokale SLMs/LLMs, wenn sie ohne Upload laufen
- lokale Antwortentwurfslogik

## Verboten

- Remote-LLM-APIs fuer Bescheidinhalte
- Remote-Fallbacks
- Cloud-Prompting
- API-Key-Pflicht fuer Kernanalyse
- externe Trainingsnutzung
- automatische Uebertragung von Prompts

## Nachweisbare Provider-Denylist

Folgende Provider duerfen im Produktcode nicht aktiv referenziert werden:

- OpenAI (SDK: `openai`, Modul: `openai`)
- Anthropic (SDK: `anthropic`, Modul: `anthropic`)
- Google Gemini (SDK: `google-generativeai`, Modul: `google.generativeai`)
- Mistral (SDK: `mistralai`, Modul: `mistralai` / `mistral`)
- Groq (SDK: `groq`, Modul: `groq`)
- Cohere (SDK: `cohere`, Modul: `cohere`)
- Perplexity (Modul: `perplexity`)
- Together AI (Modul: `together`)
- Hugging Face Inference API (Modul: `huggingface_hub`)
- Ollama (remote endpoints) (Modul: `ollama`)
- Azure OpenAI (Modul: `azure.ai` / `azure`)
- AWS Bedrock (Modul: `boto3`)

## Nachweisbare API-Key-Denylist

Folgende Umgebungsvariablen duerfen im Produktcode nicht abgefragt werden:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `COHERE_API_KEY`
- `PERPLEXITY_API_KEY`
- `TOGETHER_API_KEY`
- `HF_TOKEN` / `HUGGINGFACE_API_TOKEN`
- `AZURE_OPENAI_API_KEY`
- `BEDROCK_API_KEY`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `REMOTE_LLM_URL`

## Nachweisbare Code-Muster-Denylist

Folgende Muster im Produktcode sind blockierend:

- `import openai`, `from openai import ...`
- `import anthropic`, `from anthropic import ...`
- `import google.generativeai`
- `import mistralai`, `import groq`, `import cohere`
- `import huggingface_hub`
- `AzureOpenAI`, `ChatOpenAI` (LangChain)
- `RemoteRunnable` (LangServe)

## Enforcement

- `scripts/guardrail_check.py` — statischer Produktcode-Scan
- `tests/test_no_remote_llm.py` — dynamische Guardrail-Tests
- `tests/test_offline_mode.py` — API-Key-Unabhaengigkeit
- GitHub Actions: `.github/workflows/local-only-guardrails.yml`

## Status

Aktuell ist nur der Guardrail-Harness nachgewiesen. Ein vollstaendiger
lokaler Antwortentwurf ist noch nicht implementiert.

Der No-Remote-LLM-Guardrail ist `GREEN_PARTIAL` fuer den aktuellen
Python-Harness. Der Local-only-Gesamtstatus bleibt `YELLOW`.

*Zuletzt aktualisiert: 2026-06-06*
