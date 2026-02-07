# Architecture

## Components (Top-Level)

- frontend/ — React + Vite UI (thin client)
- backend/ — Service layer for incidents and LLM explanations
- src/ — Core backend logic (ingestion, anomaly detection, data pipeline)
- llm/ — LLM inference, training, and adapters
- docs/ — Audits, phase artifacts, and limitations
- scripts/ — Local setup helpers

## Data Flow

1. Logs are ingested and parsed (src/data)
2. Features are computed (src/data)
3. Anomalies are detected (src/anomaly)
4. Incidents are built from anomalies (backend/incident)
5. LLM generates incident explanations (backend/llm_service → llm/)

## LLM Flow

- Prompting and schema validation are enforced in backend/llm_service.
- Local Mistral inference runs via llm/mistral.
- Optional LoRA adapters are loaded at inference time (llm/config).

## Integration Boundaries

- frontend/ communicates only through backend APIs.
- No business logic exists in frontend/.
- Training code is isolated under llm/training/.
