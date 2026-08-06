import { useEffect, useState } from "react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

interface HealthData {
  status: string;
  services: {
    redis: string;
    postgres: string;
    model_worker: string;
  };
  version: string;
  uptime_seconds: number;
}

function StatusDot({ status }: { status: string }) {
  const color = status === "connected" ? "bg-green-500" : "bg-red-500";
  return (
    <span className="relative flex h-3 w-3">
      {status === "connected" && (
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${color} opacity-75`} />
      )}
      <span className={`relative inline-flex rounded-full h-3 w-3 ${color}`} />
    </span>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function StatusPage() {
  useDocumentTitle("System Status");
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHealth(data);
      setError(null);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach API");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Status</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Live health checks, refreshed every 10 seconds.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          className="px-4 py-2 bg-white border border-dlv-border rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Overall status */}
      <div className={`rounded-xl p-6 mb-8 border ${
        loading
          ? "bg-gray-50 border-gray-200"
          : error
            ? "bg-red-50 border-red-200"
            : health?.status === "healthy"
              ? "bg-green-50 border-green-200"
              : "bg-yellow-50 border-yellow-200"
      }`}>
        <div className="flex items-center gap-4">
          {loading ? (
            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          ) : error ? (
            <span className="w-4 h-4 bg-red-500 rounded-full" />
          ) : (
            <StatusDot status={health?.status === "healthy" ? "connected" : "disconnected"} />
          )}
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {loading ? "Checking..." : error ? "Unreachable" : health?.status === "healthy" ? "All Systems Operational" : "Degraded"}
            </h2>
            {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
            {lastChecked && (
              <p className="text-xs text-gray-400 mt-1">
                Last checked: {lastChecked.toLocaleTimeString()}
              </p>
            )}
          </div>
          {health && (
            <div className="ml-auto text-right">
              <p className="text-sm text-gray-500">v{health.version}</p>
              <p className="text-xs text-gray-400">uptime: {formatUptime(health.uptime_seconds)}</p>
            </div>
          )}
        </div>
      </div>

      {/* Services */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Services</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        {[
          {
            name: "Redis",
            desc: "Translation cache + rate limit counters",
            port: "6379",
            status: health?.services.redis,
          },
          {
            name: "PostgreSQL",
            desc: "Users, API keys, usage logs",
            port: "5432",
            status: health?.services.postgres,
          },
          {
            name: "Model Worker",
            desc: "CTranslate2 inference engine",
            port: "8001",
            status: health?.services.model_worker,
          },
        ].map((svc) => (
          <div key={svc.name} className="bg-white border border-dlv-border rounded-lg p-5">
            <div className="flex items-center gap-3 mb-2">
              <StatusDot status={loading ? "unknown" : svc.status ?? "disconnected"} />
              <h3 className="font-semibold text-gray-900">{svc.name}</h3>
            </div>
            <p className="text-sm text-gray-500 mb-2">{svc.desc}</p>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">port {svc.port}</span>
              <span className={`text-xs font-medium ${
                svc.status === "connected" ? "text-green-600" : "text-red-500"
              }`}>
                {loading ? "checking" : svc.status ?? "unknown"}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Endpoints */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Monitoring Endpoints</h2>
      <div className="bg-white border border-dlv-border rounded-lg overflow-hidden mb-10">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Endpoint</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Purpose</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="px-4 py-3 font-mono text-xs">GET /health</td>
              <td className="px-4 py-3">Liveness + dependency probes</td>
              <td className="px-4 py-3"><a href="/health" className="text-dlv-accent hover:underline text-xs">Open</a></td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-mono text-xs">GET /metrics</td>
              <td className="px-4 py-3">Prometheus scrape target</td>
              <td className="px-4 py-3"><a href="/metrics" className="text-dlv-accent hover:underline text-xs">Open</a></td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-mono text-xs">GET /docs</td>
              <td className="px-4 py-3">Swagger interactive API docs</td>
              <td className="px-4 py-3"><a href="/docs" className="text-dlv-accent hover:underline text-xs">Open</a></td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-mono text-xs">GET /redoc</td>
              <td className="px-4 py-3">ReDoc API documentation</td>
              <td className="px-4 py-3"><a href="/redoc" className="text-dlv-accent hover:underline text-xs">Open</a></td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Key Metrics */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Key Metrics (Prometheus)</h2>
      <div className="bg-white border border-dlv-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Metric</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="px-4 py-2.5 font-mono text-xs">deeplv_http_requests_total</td>
              <td className="px-4 py-2.5">Counter</td>
              <td className="px-4 py-2.5 text-gray-600">Request count by method, endpoint, status</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 font-mono text-xs">deeplv_http_request_duration_seconds</td>
              <td className="px-4 py-2.5">Histogram</td>
              <td className="px-4 py-2.5 text-gray-600">Latency distribution by method, endpoint</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 font-mono text-xs">deeplv_translations_total</td>
              <td className="px-4 py-2.5">Counter</td>
              <td className="px-4 py-2.5 text-gray-600">Translations by language pair and cache status</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 font-mono text-xs">deeplv_cache_hits_total</td>
              <td className="px-4 py-2.5">Counter</td>
              <td className="px-4 py-2.5 text-gray-600">Translation cache hit count</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
