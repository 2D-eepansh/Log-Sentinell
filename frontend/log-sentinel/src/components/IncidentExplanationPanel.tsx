import type { IncidentExplanation } from "@/types";
import {
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  Gauge,
  Link2,
  Copy,
  Check,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface IncidentExplanationPanelProps {
  explanation: IncidentExplanation;
}

const IncidentExplanationPanel = ({ explanation }: IncidentExplanationPanelProps) => {
  const [copied, setCopied] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);

  const confidencePercent = Math.round(explanation.confidence * 100);
  const confidenceColor =
    confidencePercent >= 80
      ? "text-status-success"
      : confidencePercent >= 60
      ? "text-status-warning"
      : "text-status-error";

  const handleCopy = async () => {
    const text = `
Incident: ${explanation.incident_id}

What Happened:
${explanation.what_happened}

Probable Cause:
${explanation.probable_cause}

Confidence: ${confidencePercent}%

Recommended Actions:
${explanation.recommended_actions.map((a, i) => `${i + 1}. ${a}`).join("\n")}

Related Services: ${explanation.related_services.join(", ")}
    `.trim();

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Incident Analysis</h2>
          <p className="text-xs text-muted-foreground mt-0.5 font-mono">
            {explanation.incident_id}
          </p>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted-foreground rounded-md hover:bg-muted transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-status-success" />
              <span className="text-status-success">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Confidence meter */}
      <div className="flex items-center gap-3 p-3 rounded-md bg-muted/50 border">
        <Gauge className={cn("w-4 h-4", confidenceColor)} />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-foreground">Analysis Confidence</span>
            <span className={cn("text-xs font-mono font-semibold", confidenceColor)}>
              {confidencePercent}%
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-border overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                confidencePercent >= 80
                  ? "bg-status-success"
                  : confidencePercent >= 60
                  ? "bg-status-warning"
                  : "bg-status-error"
              )}
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* What happened */}
      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-status-warning" />
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            What Happened
          </h3>
        </div>
        <p className="text-xs text-foreground leading-relaxed pl-6">
          {explanation.what_happened}
        </p>
      </section>

      {/* Probable cause */}
      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-status-info" />
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            Why It Likely Happened
          </h3>
        </div>
        <p className="text-xs text-foreground leading-relaxed pl-6">
          {explanation.probable_cause}
        </p>
      </section>

      {/* Recommended actions */}
      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-status-success" />
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            Recommended Next Steps
          </h3>
        </div>
        <ol className="space-y-1.5 pl-6">
          {explanation.recommended_actions.map((action, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-relaxed">
              <span className="shrink-0 w-4 h-4 flex items-center justify-center rounded-full bg-muted text-muted-foreground text-[10px] font-medium mt-0.5">
                {i + 1}
              </span>
              <span>{action}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Related services */}
      {explanation.related_services.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center gap-2">
            <Link2 className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
              Related Services
            </h3>
          </div>
          <div className="flex flex-wrap gap-1.5 pl-6">
            {explanation.related_services.map((service) => (
              <span
                key={service}
                className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-muted text-muted-foreground"
              >
                {service}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* AI Input Context (transparency) */}
      <section className="border-t pt-3 mt-1">
        <button
          onClick={() => setContextExpanded((prev) => !prev)}
          className="flex items-center gap-2 w-full text-left text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 transition-transform",
              contextExpanded && "rotate-180"
            )}
          />
          <span className="font-medium">View incident context (AI input)</span>
        </button>
        {contextExpanded && (
          <div className="mt-2 max-h-60 overflow-auto rounded-md bg-muted/50 border p-3">
            <pre className="text-[11px] font-mono text-muted-foreground whitespace-pre-wrap break-words leading-relaxed">
              {JSON.stringify(
                {
                  incident_id: explanation.incident_id,
                  confidence: explanation.confidence,
                  related_services: explanation.related_services,
                  what_happened: explanation.what_happened,
                  probable_cause: explanation.probable_cause,
                  recommended_actions: explanation.recommended_actions,
                },
                null,
                2
              )}
            </pre>
          </div>
        )}
      </section>
    </div>
  );
};

export default IncidentExplanationPanel;
