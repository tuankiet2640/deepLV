import { useEffect, useState } from "react";

interface AuditLogEntry {
  id: string;
  actor_email: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: string | null;
  created_at: string;
}

const API_BASE = "/api/v1";

function formatDetails(details: string | null): string {
  if (!details) return "-";
  try {
    const parsed = JSON.parse(details);
    return Object.entries(parsed)
      .map(([key, change]) => {
        if (change && typeof change === "object" && "old" in change && "new" in change) {
          const c = change as { old: unknown; new: unknown };
          return `${key}: ${c.old} → ${c.new}`;
        }
        return `${key}: ${JSON.stringify(change)}`;
      })
      .join(", ");
  } catch {
    return details;
  }
}

export function AuditLogTable() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLog = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("dlv_token");
      const res = await fetch(`${API_BASE}/admin/audit-log`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to fetch audit log: ${res.status}`);
      const data = await res.json();
      setEntries(data.entries);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLog();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dlv-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Audit Log ({total})</h3>
        <button onClick={fetchAuditLog} className="text-sm text-dlv-accent hover:underline">
          Refresh
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 border-b border-dlv-border">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-600">Time</th>
              <th className="px-4 py-3 font-medium text-gray-600">Actor</th>
              <th className="px-4 py-3 font-medium text-gray-600">Action</th>
              <th className="px-4 py-3 font-medium text-gray-600">Target</th>
              <th className="px-4 py-3 font-medium text-gray-600">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dlv-border">
            {entries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-900 font-medium">{entry.actor_email}</td>
                <td className="px-4 py-3 text-gray-700 font-mono text-xs">{entry.action}</td>
                <td className="px-4 py-3 text-gray-700 text-xs">
                  {entry.target_type ? `${entry.target_type}:${entry.target_id ?? "-"}` : "-"}
                </td>
                <td className="px-4 py-3 text-gray-700 text-xs">
                  {formatDetails(entry.details)}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  No audit log entries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
