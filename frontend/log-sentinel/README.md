# Log Sentinel Frontend

Frontend UI for the Deriv Anomaly Copilot. This app is a thin client that connects to the backend APIs for log ingestion, anomaly detection, incident listing, and LLM-backed incident explanations.

## Requirements

- Node.js 18+
- npm

## Environment Variables

Create a `.env` file (or copy `.env.example`) and set the backend base URL:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Install & Run

```sh
npm install
npm run dev
```

## Build

```sh
npm run build
npm run preview
```

## Tech Stack

- Vite
- React
- TypeScript
- shadcn/ui
- Tailwind CSS

## Notes

- All data comes from the backend. No mock data is used.
- UI actions map directly to backend endpoints via a centralized API client.
