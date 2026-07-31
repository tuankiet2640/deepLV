import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

const API_BASE = "/api/v1";

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
}

export function ApiKeysPage() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const headers = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }, [token]);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/keys`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setKeys(Array.isArray(data) ? data : data.keys ?? []);
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError(null);
    setCreatedKey(null);

    try {
      const res = await fetch(`${API_BASE}/keys`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ name: newKeyName.trim() }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Failed to create key" }));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      setCreatedKey(data.key);
      setNewKeyName("");
      showToast("API key created successfully", "success");
      await fetchKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await fetch(`${API_BASE}/keys/${id}`, {
        method: "DELETE",
        headers: headers(),
      });
      showToast("API key revoked", "success");
      await fetchKeys();
    } catch {
      showToast("Failed to revoke key", "error");
    }
  };

  const handleCopyKey = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey).catch(() => {});
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">API Keys</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Create and manage API keys for the translation endpoint. The translate API uses X-API-Key
          header authentication.
        </p>
      </div>

      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 space-y-6">
        {/* Create Key Section */}
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">Your Keys</h2>
          <button
            onClick={() => {
              setShowCreate(!showCreate);
              setCreatedKey(null);
              setError(null);
            }}
            className="px-3 py-1.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 transition-colors"
          >
            {showCreate ? "Cancel" : "Create New Key"}
          </button>
        </div>

        {showCreate && (
          <div className="border border-dlv-border dark:border-dlv-dark-border rounded-lg p-4 bg-gray-50 dark:bg-dlv-dark-bg space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Key Name</label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g., Production App"
                className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
              />
            </div>
            <button
              onClick={handleCreate}
              disabled={!newKeyName.trim() || creating}
              className="px-4 py-2 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
            >
              {creating ? "Creating..." : "Create Key"}
            </button>
          </div>
        )}

        {/* Newly Created Key Alert */}
        {createdKey && (
          <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4">
            <p className="text-sm font-medium text-green-800 dark:text-green-300 mb-2">
              Key created successfully! Copy it now - you will not be able to see it again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-white dark:bg-dlv-dark-bg border border-green-200 dark:border-green-800 rounded px-3 py-2 text-sm font-mono text-gray-800 dark:text-gray-200 break-all">
                {createdKey}
              </code>
              <button
                onClick={handleCopyKey}
                className="px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors whitespace-nowrap"
              >
                Copy
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Keys List */}
        {loading ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">Loading...</div>
        ) : keys.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">
            No API keys yet. Create one to start using the translation API.
          </p>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between border border-dlv-border dark:border-dlv-dark-border rounded-lg px-4 py-3 bg-white dark:bg-dlv-dark-bg"
              >
                <div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{key.name}</span>
                  <span className="ml-2 text-xs bg-gray-100 dark:bg-dlv-dark-border text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded font-mono">
                    {key.prefix}...
                  </span>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Created {new Date(key.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleRevoke(key.id)}
                  className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 text-sm font-medium"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
