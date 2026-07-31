import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = "/api/v1";

export interface DocumentJob {
  id: string;
  filename: string;
  source_lang: string;
  target_lang: string;
  provider: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at?: string;
  error?: string;
}

interface UploadParams {
  file: File;
  sourceLang: string;
  targetLang: string;
  provider: string;
  providerKeyId?: string;
}

interface UseDocumentTranslationResult {
  jobs: DocumentJob[];
  isUploading: boolean;
  uploadError: string | null;
  uploadDocument: (params: UploadParams) => Promise<void>;
  refreshJobs: () => Promise<void>;
  downloadResult: (jobId: string) => Promise<void>;
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("dlv_token");
  const apiKey = localStorage.getItem("dlv_api_key");
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

export function useDocumentTranslation(): UseDocumentTranslationResult {
  const [jobs, setJobs] = useState<DocumentJob[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobsRef = useRef<DocumentJob[]>(jobs);

  // Keep the ref in sync with state
  jobsRef.current = jobs;

  const refreshJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents/jobs`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs ?? data);
      }
    } catch {
      // Silently fail on refresh
    }
  }, []);

  const uploadDocument = useCallback(
    async ({ file, sourceLang, targetLang, provider, providerKeyId }: UploadParams) => {
      setIsUploading(true);
      setUploadError(null);

      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("source_lang", sourceLang);
        formData.append("target_lang", targetLang);
        formData.append("provider", provider);
        if (providerKeyId) {
          formData.append("provider_key_id", providerKeyId);
        }

        const res = await fetch(`${API_BASE}/documents/translate`, {
          method: "POST",
          headers: getAuthHeaders(),
          body: formData,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(body.detail ?? `Upload failed: HTTP ${res.status}`);
        }

        await refreshJobs();
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setIsUploading(false);
      }
    },
    [refreshJobs],
  );

  const downloadResult = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`${API_BASE}/documents/jobs/${jobId}/download`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        throw new Error("Download failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = res.headers.get("Content-Disposition");
      const filenameMatch = disposition?.match(/filename="?([^"]+)"?/);
      a.download = filenameMatch?.[1] ?? `translated-${jobId}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    }
  }, []);

  // Poll for active jobs using a stable interval
  useEffect(() => {
    refreshJobs();

    pollIntervalRef.current = setInterval(() => {
      const hasActive = jobsRef.current.some(
        (j) => j.status === "pending" || j.status === "processing",
      );
      if (hasActive) {
        refreshJobs();
      }
    }, 3000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [refreshJobs]);

  return { jobs, isUploading, uploadError, uploadDocument, refreshJobs, downloadResult };
}
