export type Severity = "low" | "medium" | "high" | "critical";

export interface LogFile {
  name: string;
  size: number;
  type: string;
  uploadedAt: string;
}

export interface Anomaly {
  id: string;
  timestamp: string;
  service: string;
  feature: string;
  observed_value: number;
  baseline_value: number;
  severity: Severity;
  deviation: number;
}

export interface Incident {
  id: string;
  service: string;
  start_time: string;
  end_time: string;
  severity: Severity;
  anomaly_count: number;
  description: string;
  status: "open" | "investigating" | "resolved";
}

export interface IncidentExplanation {
  incident_id: string;
  what_happened: string;
  probable_cause: string;
  confidence: number;
  recommended_actions: string[];
  related_services: string[];
}

export type AppStep = "upload" | "detect" | "incidents" | "explain";

export interface UploadResponse {
  success: boolean;
  file_id: string;
  row_count: number;
  columns: string[];
}

export interface DetectionResponse {
  anomalies: Anomaly[];
  total_count: number;
  detection_time_ms: number;
}

export interface IncidentsResponse {
  incidents: Incident[];
  total_count: number;
}
