import { useEffect, useState } from "react";

interface UsageAnalytics {
  total_translations: number;
  total_characters: number;
  total_users: number;
  active_users_30d: number;
  translations_by_provider: Record<string, number>;
  translations_by_lang_pair: Array<{
    source_lang: string;
    target_lang: string;
    count: number;
  }>;
  daily_usage: Array<{
    date: string;
    translations: number;
    characters: number;
  }>;
}

const API_BASE = "/api/v1";

export function UsageChart() {
  const [analytics, setAnalytics] = useState<UsageAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const token = localStorage.getItem("dlv_token");
        const res = await fetch(`${API_BASE}/admin/usage`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to fetch analytics: ${res.status}`);
        setAnalytics(await res.json());
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dlv-accent" />
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
        {error || "Failed to load analytics"}
      </div>
    );
  }

  const maxDaily = Math.max(...analytics.daily_usage.map((d) => d.translations), 1);

  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Translations" value={analytics.total_translations.toLocaleString()} />
        <StatCard label="Total Characters" value={analytics.total_characters.toLocaleString()} />
        <StatCard label="Total Users" value={analytics.total_users.toLocaleString()} />
        <StatCard label="Active (30d)" value={analytics.active_users_30d.toLocaleString()} />
      </div>

      {/* Provider breakdown */}
      <div className="bg-white rounded-lg border border-dlv-border p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Translations by Provider</h4>
        <div className="space-y-2">
          {Object.entries(analytics.translations_by_provider).map(([provider, count]) => {
            const pct = analytics.total_translations > 0
              ? (count / analytics.total_translations) * 100
              : 0;
            return (
              <div key={provider} className="flex items-center gap-3">
                <span className="text-xs font-medium text-gray-600 w-24 capitalize">
                  {provider}
                </span>
                <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-dlv-accent rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">
                  {count.toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Daily usage chart (bar chart) */}
      {analytics.daily_usage.length > 0 && (
        <div className="bg-white rounded-lg border border-dlv-border p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Daily Usage (Last 30 Days)</h4>
          <div className="flex items-end gap-1 h-32">
            {analytics.daily_usage.map((day) => (
              <div
                key={day.date}
                className="flex-1 bg-dlv-accent/80 hover:bg-dlv-accent rounded-t transition-colors"
                style={{ height: `${(day.translations / maxDaily) * 100}%`, minHeight: "2px" }}
                title={`${day.date}: ${day.translations} translations, ${day.characters.toLocaleString()} chars`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-xs text-gray-400">
              {analytics.daily_usage[0]?.date}
            </span>
            <span className="text-xs text-gray-400">
              {analytics.daily_usage[analytics.daily_usage.length - 1]?.date}
            </span>
          </div>
        </div>
      )}

      {/* Top language pairs */}
      {analytics.translations_by_lang_pair.length > 0 && (
        <div className="bg-white rounded-lg border border-dlv-border p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Top Language Pairs</h4>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {analytics.translations_by_lang_pair.map((pair) => (
              <div
                key={`${pair.source_lang}-${pair.target_lang}`}
                className="bg-gray-50 rounded px-3 py-2 text-center"
              >
                <span className="text-xs font-medium text-gray-700 uppercase">
                  {pair.source_lang} &rarr; {pair.target_lang}
                </span>
                <div className="text-sm font-semibold text-dlv-accent">
                  {pair.count.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border border-dlv-border p-4">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}
