import type { Incident } from "@/types";
import SeverityBadge from "@/components/SeverityBadge";
import { Button } from "@/components/ui/button";
import { Clock, AlertTriangle, MessageSquare, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface IncidentListProps {
  incidents: Incident[];
  selectedIncidentId: string | null;
  onSelectIncident: (incident: Incident) => void;
  onExplainIncident: (incident: Incident) => void;
  explaining: boolean;
}

const statusConfig = {
  open: { label: "Open", className: "bg-severity-high-bg text-severity-high" },
  investigating: { label: "Investigating", className: "bg-severity-medium-bg text-severity-medium" },
  resolved: { label: "Resolved", className: "bg-severity-low-bg text-severity-low" },
};

const IncidentList = ({
  incidents,
  selectedIncidentId,
  onSelectIncident,
  onExplainIncident,
  explaining,
}: IncidentListProps) => {
  const formatTimeRange = (start: string, end: string) => {
    const fmt = (ts: string) =>
      new Date(ts).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
    return `${fmt(start)} → ${fmt(end)}`;
  };

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-foreground">Incidents</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          {incidents.length} incidents identified from anomaly clusters
        </p>
      </div>

      <div className="space-y-2">
        {incidents.map((incident) => {
          const isSelected = incident.id === selectedIncidentId;
          const status = statusConfig[incident.status];

          return (
            <div
              key={incident.id}
              className={cn(
                "border rounded-md p-4 transition-colors cursor-pointer",
                isSelected
                  ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                  : "hover:border-muted-foreground/30 bg-card"
              )}
              onClick={() => onSelectIncident(incident)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0 space-y-2">
                  {/* Header row */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-semibold text-foreground">
                      {incident.id}
                    </span>
                    <SeverityBadge severity={incident.severity} />
                    <span
                      className={cn(
                        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider",
                        status.className
                      )}
                    >
                      {status.label}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-foreground leading-relaxed">
                    {incident.description}
                  </p>

                  {/* Meta */}
                  <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1 font-mono">
                      <span className="font-medium text-foreground">{incident.service}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTimeRange(incident.start_time, incident.end_time)}
                    </span>
                    <span className="flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {incident.anomaly_count} anomalies
                    </span>
                  </div>
                </div>

                {/* Explain button */}
                <div className="shrink-0">
                  {isSelected ? (
                    <Button
                      size="sm"
                      variant="default"
                      className="text-xs h-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        onExplainIncident(incident);
                      }}
                      disabled={explaining}
                    >
                      {explaining ? (
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                          Analyzing…
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5">
                          <MessageSquare className="w-3 h-3" />
                          Explain Incident
                        </span>
                      )}
                    </Button>
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default IncidentList;
