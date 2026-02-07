import type { Severity } from "@/types";
import { cn } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

const severityConfig: Record<Severity, { label: string; classes: string }> = {
  low: {
    label: "Low",
    classes: "bg-severity-low-bg text-severity-low",
  },
  medium: {
    label: "Medium",
    classes: "bg-severity-medium-bg text-severity-medium",
  },
  high: {
    label: "High",
    classes: "bg-severity-high-bg text-severity-high",
  },
  critical: {
    label: "Critical",
    classes: "bg-severity-critical-bg text-severity-critical",
  },
};

const SeverityBadge = ({ severity, className }: SeverityBadgeProps) => {
  const config = severityConfig[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider",
        config.classes,
        className
      )}
    >
      {config.label}
    </span>
  );
};

export default SeverityBadge;
