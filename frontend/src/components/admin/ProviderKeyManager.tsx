import { useEffect, useState } from "react";

interface AdminProviderKey {
  id: string;
  provider: string;
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

const API_BASE = "/api/v1";
const PROVIDERS = ["openai", "huggingface", "google", "deepl"];

export function ProviderKeyManager() {
  const [keys, setKeys] = useState<AdminProviderKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newProvider, setNewProvider] = useState(PROVIDERS[0]);
  const [newApiKey, setNewApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/admin/provider-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to fetch keys: ${res.status}`);
      const data = await res.json();
      setKeys(data.keys);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newApiKey.trim()) return;
    setSubmitting(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/admin/provider-keys`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ provider: newProvider, api_key: newApiKey }),
      });
      if (!res.ok) throw new Error(`Failed to add key: ${res.status}`);
      setNewApiKey("");
      await fetchKeys();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm("Are you sure you want to delete this provider key?")) return;
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_BASE}/admin/provider-keys/${keyId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setKeys((prev) => prev.filter((k) => k.id !== keyId));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dlv-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Add new key form */}
      <div className="bg-white rounded-lg border border-dlv-border p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Add Provider Key</h4>
        <p className="text-xs text-gray-500 mb-3">
          Admin provider keys are used for credit-based translations when users pay with platform credits instead of using their own API keys.
        </p>
        <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-3">
          <select
            value={newProvider}
            onChange={(e) => setNewProvider(e.target.value)}
            className="px-3 py-2 border border-dlv-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
          >
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
          <input
            type="password"
            placeholder="API Key"
            value={newApiKey}
            onChange={(e) => setNewApiKey(e.target.value)}
            className="flex-1 px-3 py-2 border border-dlv-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
          />
          <button
            type="submit"
            disabled={submitting || !newApiKey.trim()}
            className="px-4 py-2 bg-dlv-accent text-white rounded-md text-sm font-medium hover:bg-dlv-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Adding..." : "Add Key"}
          </button>
        </form>
      </div>

      {/* Existing keys */}
      <div className="bg-white rounded-lg border border-dlv-border overflow-hidden">
        <div className="px-4 py-3 border-b border-dlv-border bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-700">Active Provider Keys</h4>
        </div>
        {keys.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">
            No admin provider keys configured yet. Add one above to enable credit-based translations.
          </div>
        ) : (
          <div className="divide-y divide-dlv-border">
            {keys.map((key) => (
              <div
                key={key.id}
                className="px-4 py-3 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                      key.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {key.provider}
                  </span>
                  <span className="text-xs text-gray-500">
                    {key.usage_count} uses
                  </span>
                  <span className="text-xs text-gray-400">
                    Added {new Date(key.created_at).toLocaleDateString()}
                  </span>
                </div>
                <button
                  onClick={() => handleDelete(key.id)}
                  className="text-xs text-red-500 hover:text-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
