import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = "/api/v1";

export interface DocumentJob {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  source_lang: string;
  target_lang: string;
  provider: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  /** Only present on the job detail endpoint, not in the list response. */
  segment_count?: number | null;
  translated_segments?: number | null;
  failed_segments?: number | null;
  format_preserved?: boolean | null;
  output_filename?: string | null;
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
  deleteJob: (jobId: string) => Promise<void>;
  clearFinishedJobs: () => Promise<void>;
  deleteError: string | null;
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
  const [deleteError, setDeleteError] = useState<string | null>(null);
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
      // The server names the file, including its extension — a translated DOCX
      // comes back as DOCX, and a PDF comes back as DOCX.
      const disposition = res.headers.get("Content-Disposition");
      const filenameMatch = disposition?.match(/filename="?([^"]+)"?/);
      a.download = filenameMatch?.[1] ?? `translated-${jobId}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    }
  }, []);

  const deleteJob = useCallback(async (jobId: string) => {
    setDeleteError(null);
    // Drop it from the list immediately, restore on failure
    const previous = jobsRef.current;
    setJobs((current) => current.filter((j) => j.id !== jobId));

    try {
      const res = await fetch(`${API_BASE}/documents/jobs/${jobId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok && res.status !== 404) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `Delete failed: HTTP ${res.status}`);
      }
    } catch (err) {
      setJobs(previous);
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
    }
  }, []);

  const clearFinishedJobs = useCallback(async () => {
    setDeleteError(null);
    const previous = jobsRef.current;
    setJobs((current) => current.filter((j) => j.status === "pending" || j.status === "processing"));

    try {
      const res = await fetch(`${API_BASE}/documents/jobs`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `Clear failed: HTTP ${res.status}`);
      }
      await refreshJobs();
    } catch (err) {
      setJobs(previous);
      setDeleteError(err instanceof Error ? err.message : "Clear failed");
    }
  }, [refreshJobs]);

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

  return {
    jobs,
    isUploading,
    uploadError,
    uploadDocument,
    refreshJobs,
    downloadResult,
    deleteJob,
    clearFinishedJobs,
    deleteError,
  };
}
