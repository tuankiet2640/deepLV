import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const PROVIDER_COSTS: Record<string, number> = {
  marianmt: 0,
  openai: 5,
  huggingface: 2,
  google: 3,
};

// Character estimation multiplier by file type
const CHAR_MULTIPLIERS: Record<string, number> = {
  pdf: 0.5,
  docx: 0.9,
  txt: 1.0,
};

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return (parts[parts.length - 1] ?? "").toLowerCase();
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentCostEstimateProps {
  file: File;
  provider: string;
}

export function DocumentCostEstimate({ file, provider }: DocumentCostEstimateProps) {
  const { token } = useAuth();
  const [hasStoredKey, setHasStoredKey] = useState(false);

  useEffect(() => {
    if (!token || provider === "marianmt") {
      setHasStoredKey(false);
      return;
    }

    const fetchKeys = async () => {
      try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const apiKey = localStorage.getItem("dlv_api_key");
        if (apiKey) headers["X-API-Key"] = apiKey;

        const res = await fetch("/api/v1/providers/keys", { headers });
        if (res.ok) {
          const data = await res.json();
          const keys: { provider: string }[] = data.keys ?? data;
          setHasStoredKey(keys.some((k) => k.provider === provider));
        }
      } catch {
        setHasStoredKey(false);
      }
    };

    fetchKeys();
  }, [token, provider]);

  const ext = getFileExtension(file.name);
  const multiplier = CHAR_MULTIPLIERS[ext] ?? 1.0;
  const estimatedChars = Math.round(file.size * multiplier);

  if (provider === "marianmt") {
    return (
      <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400">
            Free
          </span>
          <span className="text-sm text-green-700 dark:text-green-300">
            MarianMT translation is always free
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          File size: {formatFileSize(file.size)} | Estimated ~{estimatedChars.toLocaleString()} chars
        </p>
      </div>
    );
  }

  if (hasStoredKey) {
    return (
      <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 px-4 py-3">
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Using your own key (free)
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          File size: {formatFileSize(file.size)} | Estimated ~{estimatedChars.toLocaleString()} chars
        </p>
      </div>
    );
  }

  const costPer1k = PROVIDER_COSTS[provider] ?? 5;
  const estimatedCost = (estimatedChars / 1000) * costPer1k;

  return (
    <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-4 py-3">
      <p className="text-sm text-amber-700 dark:text-amber-300">
        ~{estimatedCost.toFixed(2)} credits{" "}
        <span className="text-xs text-gray-500 dark:text-gray-400">
          (estimated {estimatedChars.toLocaleString()} chars)
        </span>
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
        File size: {formatFileSize(file.size)} | {costPer1k} credits per 1,000 characters
      </p>
    </div>
  );
}
