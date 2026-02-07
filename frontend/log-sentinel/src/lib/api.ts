import type {
  UploadResponse,
  DetectionResponse,
  IncidentsResponse,
  IncidentExplanation,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const contentType = res.headers.get("content-type");
    let message = res.statusText || "Request failed";
    try {
      if (contentType?.includes("application/json")) {
        const payload = await res.json();
        message = payload?.detail || payload?.message || message;
      } else {
        const text = await res.text();
        if (text) message = text;
      }
    } catch {
      // swallow parsing errors
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

/* ─── API Functions ─────────────────────────────────────── */

export async function uploadLogs(_file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", _file);
  return request<UploadResponse>("/logs/upload", {
    method: "POST",
    body: formData,
  });
}

export async function detectAnomalies(_fileId: string): Promise<DetectionResponse> {
  return request<DetectionResponse>("/anomalies/detect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: _fileId }),
  });
}

export async function getIncidents(): Promise<IncidentsResponse> {
  return request<IncidentsResponse>("/incidents");
}

export async function explainIncident(incidentId: string): Promise<IncidentExplanation> {
  return request<IncidentExplanation>(`/incidents/${incidentId}/explain`, {
    method: "POST",
  });
}
