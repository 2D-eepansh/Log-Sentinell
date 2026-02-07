import type { AppStep } from "@/types";
import { cn } from "@/lib/utils";
import { Upload, Search, List, MessageSquare } from "lucide-react";

interface StepIndicatorProps {
  currentStep: AppStep;
  completedSteps: AppStep[];
}

const steps: { key: AppStep; label: string; icon: React.ElementType }[] = [
  { key: "upload", label: "Upload Logs", icon: Upload },
  { key: "detect", label: "Detect Anomalies", icon: Search },
  { key: "incidents", label: "View Incidents", icon: List },
  { key: "explain", label: "Explain (AI)", icon: MessageSquare },
];

const StepIndicator = ({ currentStep, completedSteps }: StepIndicatorProps) => {
  const currentIndex = steps.findIndex((s) => s.key === currentStep);

  return (
    <div className="flex items-center gap-1 w-full max-w-2xl mx-auto">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.includes(step.key);
        const isCurrent = step.key === currentStep;
        const isUpcoming = index > currentIndex && !isCompleted;
        const Icon = step.icon;

        return (
          <div key={step.key} className="flex items-center flex-1">
            <div className="flex items-center gap-2 flex-1">
              <div
                className={cn(
                  "flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium shrink-0 transition-colors",
                  isCompleted && "bg-status-success text-primary-foreground",
                  isCurrent && "bg-primary text-primary-foreground",
                  isUpcoming && "bg-muted text-muted-foreground"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>
              <span
                className={cn(
                  "text-xs font-medium hidden sm:block whitespace-nowrap",
                  isCurrent && "text-foreground",
                  isCompleted && "text-status-success",
                  isUpcoming && "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "h-px flex-1 mx-2 min-w-[20px]",
                  isCompleted ? "bg-status-success" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StepIndicator;
