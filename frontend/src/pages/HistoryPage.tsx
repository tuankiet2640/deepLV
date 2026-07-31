import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = "/api/v1";

const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "de", name: "German" },
  { code: "fr", name: "French" },
  { code: "es", name: "Spanish" },
  { code: "zh", name: "Chinese" },
  { code: "ja", name: "Japanese" },
  { code: "vi", name: "Vietnamese" },
  { code: "ko", name: "Korean" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
];

const PROVIDERS = [
  { value: "marianmt", label: "MarianMT" },
  { value: "openai", label: "OpenAI" },
  { value: "huggingface", label: "HuggingFace" },
  { value: "google", label: "Google" },
];

interface HistoryItem {
  id: string;
  source_lang: string;
  target_lang: string;
  character_count: number;
  cached: boolean;
  latency_ms: number;
  provider: string | null;
  created_at: string;
}

export function HistoryPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sourceLang, setSourceLang] = useState("");
  const [targetLang, setTargetLang] = useState("");
  const [provider, setProvider] = useState("");
  const [days, setDays] = useState(30);

  const fetchHistory = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    params.set("days", String(days));
    params.set("limit", "50");
    if (sourceLang) params.set("source_lang", sourceLang);
    if (targetLang) params.set("target_lang", targetLang);
    if (provider) params.set("provider", provider);

    try {
      const res = await fetch(`${API_BASE}/usage/history?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [token, sourceLang, targetLang, provider, days]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const getLangName = (code: string) =>
    LANGUAGES.find((l) => l.code === code)?.name ?? code;

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Translation History
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          View your past translations and usage patterns.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-dlv-dark-card border border-dlv-border dark:border-dlv-dark-border rounded-xl p-4 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Source Language
            </label>
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-lg px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg text-gray-900 dark:text-white"
            >
              <option value="">All</option>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Target Language
            </label>
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-lg px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg text-gray-900 dark:text-white"
            >
              <option value="">All</option>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-lg px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg text-gray-900 dark:text-white"
            >
              <option value="">All</option>
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Time Range
            </label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-lg px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg text-gray-900 dark:text-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white dark:bg-dlv-dark-card border border-dlv-border dark:border-dlv-dark-border rounded-xl overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-dlv-border dark:border-dlv-dark-border flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {total} translation{total !== 1 ? "s" : ""}
          </span>
          <button
            onClick={fetchHistory}
            className="text-xs text-dlv-accent hover:underline"
          >
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="px-4 py-12 text-center text-gray-400">
            <div className="inline-block w-6 h-6 border-2 border-dlv-accent border-t-transparent rounded-full animate-spin" />
            <p className="mt-2 text-sm">Loading history...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && items.length === 0 && (
          <div className="px-4 py-12 text-center">
            <svg
              className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-gray-500 dark:text-gray-400 font-medium">
              No translations yet
            </p>
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
              Your translation history will appear here after you start translating.
            </p>
          </div>
        )}

        {/* Table */}
        {!loading && items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dlv-border dark:border-dlv-dark-border bg-gray-50 dark:bg-dlv-dark-bg">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Languages
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Characters
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Latency
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cached
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dlv-border dark:divide-dlv-dark-border">
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-gray-50 dark:hover:bg-dlv-dark-bg/50 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                      {new Date(item.created_at).toLocaleDateString()}{" "}
                      <span className="text-gray-400 dark:text-gray-500">
                        {new Date(item.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-gray-900 dark:text-white font-medium">
                        {getLangName(item.source_lang)}
                      </span>
                      <span className="text-gray-400 dark:text-gray-500 mx-2">→</span>
                      <span className="text-gray-900 dark:text-white font-medium">
                        {getLangName(item.target_lang)}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 capitalize">
                        {item.provider ?? "marianmt"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 whitespace-nowrap">
                      {item.character_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 whitespace-nowrap">
                      {item.latency_ms}ms
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      {item.cached ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                          Hit
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                          Miss
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
