"""
Minimal backend HTTP server for Deriv Anomaly Copilot.

Exposes endpoints required by the frontend without introducing new dependencies.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from backend.incident import IncidentBuilder
from typing import TYPE_CHECKING
from src.anomaly import AnomalyEngine, AnomalySeverity, overall_severity
from src.core.config import config
from src.data import aggregate_logs, extract_features_from_windows, ingest_logs, normalize_logs, parse_logs
from src.data.schema import FeatureVector, LogEntry

load_dotenv()

logger = logging.getLogger("backend")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

UPLOADS: Dict[str, Dict[str, object]] = {}
ACTIVE_FILE_ID: Optional[str] = None
EXPLANATION_SERVICE = None


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


USE_LORA = _parse_bool(os.getenv("USE_LORA"), False)
LORA_PATH = os.getenv("LORA_PATH", "llm/models/lora")


if TYPE_CHECKING:
    from llm.schema import Explanation


def _model_path() -> Optional[str]:
    return os.getenv("MODEL_PATH")


def _group_logs_by_service(logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
    grouped: Dict[str, List[LogEntry]] = {}
    for log in logs:
        grouped.setdefault(log.service, []).append(log)
    return grouped


def _features_from_file(path: Path) -> Tuple[List[FeatureVector], List[LogEntry], List[Dict[str, object]]]:
    raw_logs = list(ingest_logs(str(path), format="auto"))
    parsed_logs, _ = parse_logs(raw_logs)
    normalized_logs, _ = normalize_logs(parsed_logs)
    windows = aggregate_logs(normalized_logs, window_size_seconds=300)
    features, _ = extract_features_from_windows(list(windows.values()))
    return features, normalized_logs, parsed_logs


def _parse_content_disposition(value: str) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for part in value.split(";"):
        if "=" not in part:
            continue
        key, raw = part.strip().split("=", 1)
        params[key.strip()] = raw.strip().strip('"')
    return params


def _parse_multipart(body: bytes, boundary: bytes) -> Dict[str, Tuple[Dict[str, str], bytes]]:
    fields: Dict[str, Tuple[Dict[str, str], bytes]] = {}
    delimiter = b"--" + boundary
    for part in body.split(delimiter):
        part = part.strip()
        if not part or part == b"--":
            continue
        if part.startswith(b"--"):
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        if not content:
            continue
        header_lines = header_blob.decode("utf-8", errors="ignore").split("\r\n")
        headers: Dict[str, str] = {}
        for line in header_lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        content = content.rsplit(b"\r\n", 1)[0]
        disposition = headers.get("content-disposition", "")
        params = _parse_content_disposition(disposition)
        name = params.get("name")
        if name:
            fields[name] = (params, content)
    return fields


def _explanation_service() -> Optional[object]:
    global EXPLANATION_SERVICE
    if EXPLANATION_SERVICE is not None:
        return EXPLANATION_SERVICE

    model_path = _model_path()
    if not model_path:
        logger.error("MODEL_PATH is not set; LLM explanation unavailable.")
        return None

    try:
        from backend.llm_service import create_explanation_service
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Failed to import LLM service: %s", exc)
        return None

    logger.info("Loading LLM model from %s (USE_LORA=%s, LORA_PATH=%s)", model_path, USE_LORA, LORA_PATH)
    try:
        EXPLANATION_SERVICE = create_explanation_service(model_path=model_path)
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Model load failed: %s", exc)
        return None
    return EXPLANATION_SERVICE


def _map_severity(severity: AnomalySeverity) -> Optional[str]:
    if severity == AnomalySeverity.NONE:
        return None
    return severity.value


def _incident_description(service: str, anomaly_count: int) -> str:
    return f"{service} incident with {anomaly_count} anomaly windows detected."


def _explanation_to_frontend(explanation: "Explanation", service: str) -> Dict[str, object]:
    return {
        "incident_id": explanation.incident_id,
        "what_happened": explanation.summary,
        "probable_cause": explanation.probable_causes[0] if explanation.probable_causes else "unknown",
        "confidence": explanation.confidence_score,
        "recommended_actions": explanation.recommended_next_steps,
        "related_services": [service],
    }


class BackendHandler(BaseHTTPRequestHandler):
    server_version = "DerivBackend/1.0"

    def _send_json(self, status: int, payload: Dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Optional[Dict[str, object]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        data = self.rfile.read(length)
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if self.path == "/incidents":
            global ACTIVE_FILE_ID
            if not ACTIVE_FILE_ID or ACTIVE_FILE_ID not in UPLOADS:
                self._send_json(200, {"incidents": [], "total_count": 0})
                return

            incidents = UPLOADS[ACTIVE_FILE_ID].get("incidents", [])
            self._send_json(
                200,
                {
                    "incidents": incidents,
                    "total_count": len(incidents),
                },
            )
            return

        self._send_json(404, {"detail": "Not found"})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/logs/upload":
            self._handle_upload()
            return

        if self.path == "/anomalies/detect":
            self._handle_detect()
            return

        if self.path.startswith("/incidents/") and self.path.endswith("/explain"):
            self._handle_explain()
            return

        self._send_json(404, {"detail": "Not found"})

    def _handle_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"detail": "Expected multipart/form-data"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self._send_json(400, {"detail": "Empty request"})
            return

        boundary_token = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary_token = part.split("=", 1)[1]
                break

        if not boundary_token:
            self._send_json(400, {"detail": "Missing multipart boundary"})
            return

        body = self.rfile.read(length)
        fields = _parse_multipart(body, boundary_token.encode("utf-8"))
        if "file" not in fields:
            self._send_json(400, {"detail": "Missing file field"})
            return

        file_meta, data = fields["file"]
        filename = file_meta.get("filename", "upload.log")

        file_id = str(uuid.uuid4())
        suffix = Path(filename).suffix or ".log"
        save_path = config.logs_dir / f"{file_id}{suffix}"
        save_path.write_bytes(data)

        features, normalized_logs, parsed_logs = _features_from_file(save_path)

        columns = sorted({key for item in parsed_logs for key in item.keys()}) if parsed_logs else []

        UPLOADS[file_id] = {
            "path": str(save_path),
            "features": features,
            "normalized_logs": normalized_logs,
            "parsed_logs": parsed_logs,
            "incidents": [],
            "anomalies": [],
        }

        self._send_json(
            200,
            {
                "success": True,
                "file_id": file_id,
                "row_count": len(parsed_logs),
                "columns": columns,
            },
        )

    def _handle_detect(self) -> None:
        payload = self._read_json() or {}
        file_id = payload.get("file_id")
        if not file_id or file_id not in UPLOADS:
            self._send_json(404, {"detail": "Unknown file_id"})
            return

        start = datetime.now(timezone.utc)
        engine = AnomalyEngine()
        features = UPLOADS[file_id]["features"]
        events = engine.detect(features)

        anomalies = []
        for event in events:
            for anomaly in event.anomalies:
                severity = _map_severity(anomaly.severity)
                if not severity:
                    continue
                anomalies.append(
                    {
                        "id": f"{event.event_id}:{anomaly.feature}",
                        "timestamp": event.window_start.isoformat(),
                        "service": event.service,
                        "feature": anomaly.feature,
                        "observed_value": anomaly.observed,
                        "baseline_value": anomaly.baseline_mean,
                        "severity": severity,
                        "deviation": anomaly.z_score or anomaly.rate_change or 0.0,
                    }
                )

        logs_by_service = _group_logs_by_service(UPLOADS[file_id]["normalized_logs"])
        builder = IncidentBuilder()
        incidents_raw = builder.build_incidents(events, logs_by_service)

        incidents = []
        for incident in incidents_raw:
            event_severities = [e.severity for e in incident.anomalies]
            severity = overall_severity(*event_severities).value
            incidents.append(
                {
                    "id": incident.incident_id,
                    "service": incident.service,
                    "start_time": incident.start_time.isoformat(),
                    "end_time": incident.end_time.isoformat(),
                    "severity": severity,
                    "anomaly_count": incident.metrics_summary.anomaly_count,
                    "description": _incident_description(incident.service, incident.metrics_summary.anomaly_count),
                    "status": "open",
                }
            )

        UPLOADS[file_id]["anomalies"] = anomalies
        UPLOADS[file_id]["incidents_raw"] = incidents_raw
        UPLOADS[file_id]["incidents"] = incidents

        global ACTIVE_FILE_ID
        ACTIVE_FILE_ID = file_id

        detection_time_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        self._send_json(
            200,
            {
                "anomalies": anomalies,
                "total_count": len(anomalies),
                "detection_time_ms": detection_time_ms,
            },
        )

    def _handle_explain(self) -> None:
        if not self.path.startswith("/incidents/"):
            self._send_json(404, {"detail": "Not found"})
            return

        parts = self.path.strip("/").split("/")
        if len(parts) != 3:
            self._send_json(400, {"detail": "Invalid incident path"})
            return

        incident_id = parts[1]
        if not ACTIVE_FILE_ID or ACTIVE_FILE_ID not in UPLOADS:
            self._send_json(404, {"detail": "No incidents available"})
            return

        incidents_raw = UPLOADS[ACTIVE_FILE_ID].get("incidents_raw", [])
        incident = next((i for i in incidents_raw if i.incident_id == incident_id), None)
        if incident is None:
            self._send_json(404, {"detail": "Incident not found"})
            return

        service = _explanation_service()
        if service is None:
            self._send_json(500, {"detail": "MODEL_PATH not configured"})
            return

        explanation = service.explain(incident)
        self._send_json(200, _explanation_to_frontend(explanation, incident.service))


def run(host: str, port: int) -> None:
    logger.info("Starting backend server on %s:%s", host, port)
    logger.info("USE_LORA=%s LORA_PATH=%s", USE_LORA, LORA_PATH)
    logger.info("MODEL_PATH=%s", _model_path() or "<not set>")
    if _model_path():
        _explanation_service()
    server = ThreadingHTTPServer((host, port), BackendHandler)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deriv Anomaly Copilot backend server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    run(args.host, args.port)


if __name__ == "__main__":
    main()
