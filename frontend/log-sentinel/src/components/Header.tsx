import { Activity, Shield } from "lucide-react";

const Header = () => {
  return (
    <header className="bg-surface-header border-b border-border">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-md bg-primary">
              <Shield className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-surface-header-foreground tracking-tight">
                AI Incident & Anomaly Copilot
              </h1>
              <p className="text-xs text-muted-foreground">
                Detect and explain system incidents from logs
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
              <Activity className="w-3.5 h-3.5 text-status-success" />
              <span>System Operational</span>
            </div>
            <div className="mt-1 space-y-0 text-[10px] text-muted-foreground/70 font-mono leading-tight">
              <p>Backend: Connected</p>
              <p>LLM: Local (Mistral)</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
