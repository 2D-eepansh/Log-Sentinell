import { useState } from "react";
import Header from "@/components/Header";
import StepIndicator from "@/components/StepIndicator";
import LogUpload from "@/components/LogUpload";
import AnomalyTable from "@/components/AnomalyTable";
import IncidentList from "@/components/IncidentList";
import IncidentExplanationPanel from "@/components/IncidentExplanationPanel";
import { Button } from "@/components/ui/button";
import { uploadLogs, detectAnomalies, getIncidents, explainIncident } from "@/lib/api";
import type {
  AppStep,
  UploadResponse,
  Anomaly,
  Incident,
  IncidentExplanation,
} from "@/types";
import {
  Search,
  List,
  AlertCircle,
  Loader2,
  RotateCcw,
} from "lucide-react";

const Index = () => {
  // Flow state
  const [currentStep, setCurrentStep] = useState<AppStep>("upload");
  const [completedSteps, setCompletedSteps] = useState<AppStep[]>([]);

  // Data state
  const [fileId, setFileId] = useState<string | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [detectionTimeMs, setDetectionTimeMs] = useState(0);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<IncidentExplanation | null>(null);

  // Loading / error
  const [detecting, setDetecting] = useState(false);
  const [loadingIncidents, setLoadingIncidents] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completeStep = (step: AppStep) => {
    setCompletedSteps((prev) => (prev.includes(step) ? prev : [...prev, step]));
  };

  // Handlers
  const handleUploadComplete = (response: UploadResponse, _file: File) => {
    setFileId(response.file_id);
    completeStep("upload");
    setCurrentStep("detect");
  };

  const handleDetect = async () => {
    if (!fileId) return;
    setDetecting(true);
    setError(null);
    try {
      const result = await detectAnomalies(fileId);
      setAnomalies(result.anomalies);
      setDetectionTimeMs(result.detection_time_ms);
      completeStep("detect");
      setCurrentStep("incidents");
      // Auto-fetch incidents
      await handleFetchIncidents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Detection failed");
    } finally {
      setDetecting(false);
    }
  };

  const handleFetchIncidents = async () => {
    setLoadingIncidents(true);
    setError(null);
    try {
      const result = await getIncidents();
      setIncidents(result.incidents);
      completeStep("incidents");
      setCurrentStep("explain");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch incidents");
    } finally {
      setLoadingIncidents(false);
    }
  };

  const handleSelectIncident = (incident: Incident) => {
    setSelectedIncidentId(incident.id);
    setExplanation(null);
  };

  const handleExplainIncident = async (incident: Incident) => {
    setExplaining(true);
    setError(null);
    try {
      const result = await explainIncident(incident.id);
      setExplanation(result);
      completeStep("explain");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explanation failed");
    } finally {
      setExplaining(false);
    }
  };

  const handleReset = () => {
    setCurrentStep("upload");
    setCompletedSteps([]);
    setFileId(null);
    setAnomalies([]);
    setDetectionTimeMs(0);
    setIncidents([]);
    setSelectedIncidentId(null);
    setExplanation(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      {/* Step indicator + reset */}
      <div className="border-b bg-surface-elevated">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <div className="flex-1">
            <StepIndicator currentStep={currentStep} completedSteps={completedSteps} />
          </div>
          {completedSteps.length > 0 && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-md bg-severity-high-bg text-severity-high mb-6">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p className="text-xs flex-1">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-xs font-medium hover:underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left column */}
          <div className="lg:col-span-7 space-y-6">
            {/* Upload */}
            <div className="bg-card border rounded-md p-5">
              <LogUpload
                onUploadComplete={handleUploadComplete}
                uploadFn={uploadLogs}
              />
            </div>

            {/* Detect button */}
            {completedSteps.includes("upload") && (
              <div className="bg-card border rounded-md p-5 space-y-3">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">
                    Anomaly Detection
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Run ML-based anomaly detection on uploaded logs
                  </p>
                </div>
                {anomalies.length === 0 ? (
                  <Button
                    onClick={handleDetect}
                    disabled={detecting}
                    className="w-full"
                    size="sm"
                  >
                    {detecting ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Running detection model…
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Search className="w-3.5 h-3.5" />
                        Detect Anomalies
                      </span>
                    )}
                  </Button>
                ) : (
                  <AnomalyTable
                    anomalies={anomalies}
                    detectionTimeMs={detectionTimeMs}
                  />
                )}
              </div>
            )}

            {/* Incidents */}
            {incidents.length > 0 && (
              <div className="bg-card border rounded-md p-5">
                {loadingIncidents ? (
                  <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-xs">Loading incidents…</span>
                  </div>
                ) : (
                  <IncidentList
                    incidents={incidents}
                    selectedIncidentId={selectedIncidentId}
                    onSelectIncident={handleSelectIncident}
                    onExplainIncident={handleExplainIncident}
                    explaining={explaining}
                  />
                )}
              </div>
            )}
          </div>

          {/* Right column — Explanation panel */}
          <div className="lg:col-span-5">
            <div className="lg:sticky lg:top-6">
              {explanation ? (
                <div className="bg-card border rounded-md p-5">
                  <IncidentExplanationPanel explanation={explanation} />
                </div>
              ) : selectedIncidentId ? (
                <div className="bg-card border rounded-md p-5">
                  <div className="text-center py-8">
                    <List className="w-8 h-8 mx-auto text-muted-foreground mb-3" />
                    <p className="text-sm font-medium text-foreground">
                      Incident Selected
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Click "Explain Incident" to generate an AI analysis
                    </p>
                  </div>
                </div>
              ) : incidents.length > 0 ? (
                <div className="bg-card border rounded-md p-5">
                  <div className="text-center py-8">
                    <List className="w-8 h-8 mx-auto text-muted-foreground mb-3" />
                    <p className="text-sm font-medium text-foreground">
                      Select an Incident
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Choose an incident from the list to view its AI-generated explanation
                    </p>
                  </div>
                </div>
              ) : (
                <div className="bg-card border rounded-md p-5">
                  <div className="text-center py-8">
                    <Search className="w-8 h-8 mx-auto text-muted-foreground mb-3" />
                    <p className="text-sm font-medium text-foreground">
                      Incident Analysis
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Upload logs and run detection to view incident analysis
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
