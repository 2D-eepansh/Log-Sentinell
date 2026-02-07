import { useState, useCallback } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { UploadResponse } from "@/types";

interface LogUploadProps {
  onUploadComplete: (response: UploadResponse, file: File) => void;
  uploadFn: (file: File) => Promise<UploadResponse>;
}

const LogUpload = ({ onUploadComplete, uploadFn }: LogUploadProps) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const validateFile = (f: File): string | null => {
    const validTypes = [
      "text/csv",
      "application/json",
      "application/vnd.ms-excel",
    ];
    const validExtensions = [".csv", ".json"];
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();

    if (!validTypes.includes(f.type) && !validExtensions.includes(ext)) {
      return "Invalid file type. Please upload a CSV or JSON file.";
    }
    if (f.size > 100 * 1024 * 1024) {
      return "File too large. Maximum size is 100MB.";
    }
    return null;
  };

  const handleFile = useCallback((f: File) => {
    setError(null);
    setResult(null);
    const validation = validateFile(f);
    if (validation) {
      setError(validation);
      return;
    }
    setFile(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      if (e.dataTransfer.files?.[0]) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const response = await uploadFn(file);
      setResult(response);
      onUploadComplete(response, file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setError(null);
    setResult(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Log File Upload</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Upload system logs in CSV or JSON format for analysis
          </p>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragActive(false);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={cn(
          "relative border-2 border-dashed rounded-md p-8 text-center transition-colors",
          dragActive && "border-primary bg-primary/5",
          !dragActive && !file && "border-border hover:border-muted-foreground/40",
          file && !result && "border-primary/40 bg-primary/5",
          result && "border-status-success/40 bg-severity-low-bg"
        )}
      >
        {!file && (
          <div className="space-y-3">
            <Upload className="w-8 h-8 mx-auto text-muted-foreground" />
            <div>
              <p className="text-sm text-foreground font-medium">
                Drag and drop your log file here
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Supports CSV and JSON • Max 100MB
              </p>
              <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                Logs are processed locally. No data leaves the system.
              </p>
            </div>
            <label className="inline-block">
              <input
                type="file"
                accept=".csv,.json"
                className="sr-only"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFile(e.target.files[0]);
                }}
              />
              <span className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md bg-secondary text-secondary-foreground hover:bg-accent cursor-pointer transition-colors">
                Browse Files
              </span>
            </label>
          </div>
        )}

        {file && (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-3">
              <FileText className="w-5 h-5 text-primary shrink-0" />
              <div className="text-left">
                <p className="text-sm font-medium text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
              </div>
              {!result && !uploading && (
                <button
                  onClick={clearFile}
                  className="p-1 rounded hover:bg-muted text-muted-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {result && (
              <div className="flex items-center justify-center gap-2 text-status-success">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-xs font-medium">
                  Uploaded — {result.row_count.toLocaleString()} rows •{" "}
                  {result.columns.length} columns
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-severity-high-bg text-severity-high">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <p className="text-xs">{error}</p>
        </div>
      )}

      {/* Upload Button */}
      {file && !result && (
        <Button
          onClick={handleUpload}
          disabled={uploading}
          className="w-full"
          size="sm"
        >
          {uploading ? (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              Uploading…
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Upload className="w-3.5 h-3.5" />
              Upload Log File
            </span>
          )}
        </Button>
      )}
    </div>
  );
};

export default LogUpload;
