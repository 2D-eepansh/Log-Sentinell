# Deriv Anomaly Copilot

Deriv Anomaly Copilot is a local-first log anomaly detection system that ingests logs, detects statistical anomalies, builds incidents, and produces structured LLM explanations (optionally with LoRA adapters).

## Repository Structure

```
frontend/   # React + Vite UI
backend/    # Minimal HTTP server + service layer
src/        # Core pipeline (ingestion, features, anomaly engine)
llm/        # Local inference + LoRA integration
docs/       # Architecture, phases, limitations
scripts/    # Setup helpers
```

## Required Environment Variables

Backend (.env):

- MODEL_PATH: local filesystem path OR Hugging Face model ID (e.g., mistralai/Mistral-7B-Instruct-v0.2)
- USE_LORA: true/false
- LORA_PATH: path to LoRA adapter directory

Frontend (frontend/log-sentinel/.env):

- VITE_API_BASE_URL: backend base URL (e.g., http://localhost:8000)

Note: If VITE_API_BASE_URL is misconfigured or unreachable, the client will
surface API errors from the backend. UI-level graceful handling can be extended
if required.

## Run Backend

```
python -m backend.main --host 0.0.0.0 --port 8000
```

## Run Frontend

```
cd frontend/log-sentinel
cp .env.example .env
npm install
npm run dev
```

## Deploy Backend on EC2 (Ubuntu)

### 1) SSH to instance

```
ssh -i log-sentinel-key.pem ubuntu@<EC2_PUBLIC_IP>
```

If permissions fail:

```
chmod 400 log-sentinel-key.pem
```

### 2) System setup

```
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl
```

### 3) Clone repo

```
git clone https://github.com/2D-eepansh/Log-Sentinell.git
cd Log-Sentinell
```

### 4) Backend env + deps

```
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If torch install fails:

```
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 5) Model config

Create backend/.env:

```
USE_LORA=false
MODEL_PATH=./models/tiny-gpt2
```

### 6) Start backend

```
python -m backend.main --host 0.0.0.0 --port 8000
```

Verify from local machine:

```
curl http://<EC2_PUBLIC_IP>:8000/health
```

### 7) Connect Vercel frontend

Set Vercel env var:

```
VITE_API_BASE_URL=http://<EC2_PUBLIC_IP>:8000
```

Redeploy the Vercel project.

### Optional: run backend in tmux

```
sudo apt install -y tmux
tmux new -s backend
python -m backend.main --host 0.0.0.0 --port 8000
```

## API Endpoints

- GET /health
- POST /logs/upload
- POST /anomalies/detect
- GET /incidents
- POST /incidents/{incidentId}/explain

## Docs

- Architecture: docs/architecture.md
- Frontend integration: docs/frontend.md
- Backend overview: docs/backend.md
- Phase artifacts index: docs/phases/README.md
- Phase 5 limitations: docs/phase5/KNOWN_LIMITATIONS.md
