# Backend Overview

## Entrypoint

- backend/main.py

## Start Command

```
python -m backend.main --host 0.0.0.0 --port 8000
```

## Port

- Default: 8000

## API Endpoints

- GET /health → {"status": "ok"}
- POST /logs/upload
- POST /anomalies/detect
- GET /incidents
- POST /incidents/{incidentId}/explain

## LoRA Toggle

- USE_LORA=true|false
- LORA_PATH=llm/models/lora
- MODEL_PATH=<local directory or Hugging Face model ID>

## Key Modules

- src/data — log ingestion and feature extraction
- src/anomaly — anomaly detection engine
- backend/incident — incident schema + builder
- backend/llm_service.py — prompt orchestration, schema validation, fallback handling
- llm/ — local inference and LoRA integration
