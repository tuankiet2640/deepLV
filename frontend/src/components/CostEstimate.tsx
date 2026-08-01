import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const PROVIDER_COSTS: Record<string, number> = {
  marianmt: 0,
  openai: 5,
  huggingface: 2,
  google: 3,
};

interface CostEstimateProps {
  provider: string;
  charCount: number;
}

export function CostEstimate({ provider, charCount }: CostEstimateProps) {
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

  if (provider === "marianmt") {
    return (
      <div className="mt-2 flex items-center gap-1.5">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
          Free
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          MarianMT is always free
        </span>
      </div>
    );
  }

  if (hasStoredKey) {
    return (
      <div className="mt-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Using your own key (free)
        </span>
      </div>
    );
  }

  const costPer1k = PROVIDER_COSTS[provider] ?? 5;
  const estimatedCost = (charCount / 1000) * costPer1k;

  return (
    <div className="mt-2">
      <span className="text-xs text-gray-600 dark:text-gray-400">
        Estimated cost:{" "}
        <span className="font-medium text-gray-900 dark:text-gray-200">
          {charCount === 0 ? "0" : estimatedCost.toFixed(2)} credits
        </span>
      </span>
    </div>
  );
}
