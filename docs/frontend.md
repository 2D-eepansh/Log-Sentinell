# Frontend Integration

## Location

frontend/log-sentinel

## Environment Variables

Set the backend base URL in frontend/log-sentinel/.env:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Expected Backend Endpoints

- POST /logs/upload
- POST /anomalies/detect
- GET /incidents
- POST /incidents/{incidentId}/explain

## Run Locally

```
cd frontend/log-sentinel
npm install
npm run dev
```

## Notes

- All backend responses are used as-is.
- Loading and error states are handled in the UI.
- No mock data remains in the frontend.
