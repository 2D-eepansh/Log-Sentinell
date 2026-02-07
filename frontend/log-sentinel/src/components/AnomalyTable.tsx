import { useState } from "react";
import type { Anomaly } from "@/types";
import SeverityBadge from "@/components/SeverityBadge";
import { ArrowUpDown, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface AnomalyTableProps {
  anomalies: Anomaly[];
  detectionTimeMs: number;
}

type SortKey = "timestamp" | "service" | "severity" | "deviation";
type SortDir = "asc" | "desc";

const severityOrder = { low: 0, medium: 1, high: 2, critical: 3 };

const AnomalyTable = ({ anomalies, detectionTimeMs }: AnomalyTableProps) => {
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...anomalies].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case "timestamp":
        cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        break;
      case "service":
        cmp = a.service.localeCompare(b.service);
        break;
      case "severity":
        cmp = severityOrder[a.severity] - severityOrder[b.severity];
        break;
      case "deviation":
        cmp = a.deviation - b.deviation;
        break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <ArrowUpDown className="w-3 h-3 text-muted-foreground" />;
    return sortDir === "asc" ? (
      <ChevronUp className="w-3 h-3 text-foreground" />
    ) : (
      <ChevronDown className="w-3 h-3 text-foreground" />
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Anomaly Detection Results</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {anomalies.length} anomalies detected in {(detectionTimeMs / 1000).toFixed(1)}s
          </p>
        </div>
      </div>

      <div className="border rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-muted/50">
                {([
                  ["timestamp", "Time"],
                  ["service", "Service"],
                  [null, "Feature"],
                  [null, "Observed"],
                  [null, "Baseline"],
                  ["deviation", "Deviation"],
                  ["severity", "Severity"],
                ] as const).map(([key, label], i) => (
                  <th
                    key={i}
                    className={cn(
                      "px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap",
                      key && "cursor-pointer select-none hover:text-foreground"
                    )}
                    onClick={key ? () => handleSort(key) : undefined}
                  >
                    <span className="flex items-center gap-1">
                      {label}
                      {key && <SortIcon column={key} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((anomaly) => (
                <tr
                  key={anomaly.id}
                  className="border-t hover:bg-muted/30 transition-colors"
                >
                  <td className="px-3 py-2.5 font-mono whitespace-nowrap text-muted-foreground">
                    {formatTime(anomaly.timestamp)}
                  </td>
                  <td className="px-3 py-2.5 font-mono font-medium text-foreground">
                    {anomaly.service}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-muted-foreground">
                    {anomaly.feature}
                  </td>
                  <td className="px-3 py-2.5 font-mono font-medium text-foreground">
                    {anomaly.observed_value.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-muted-foreground">
                    {anomaly.baseline_value.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 font-mono">
                    <span
                      className={cn(
                        "font-medium",
                        anomaly.deviation > 5 ? "text-severity-critical" :
                        anomaly.deviation > 1 ? "text-severity-high" :
                        "text-severity-medium"
                      )}
                    >
                      {anomaly.deviation > 0 ? "+" : ""}{anomaly.deviation.toFixed(2)}σ
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <SeverityBadge severity={anomaly.severity} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AnomalyTable;
