import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = "/api/v1";

type Tab = "provider-keys" | "credits";

interface ProviderKey {
  id: string;
  provider: string;
  label: string;
  created_at: string;
}

interface CreditBalance {
  balance: number;
  currency: string;
}

interface Transaction {
  id: string;
  amount: number;
  type: string;
  description: string;
  created_at: string;
}

function useAuthHeaders(): () => Record<string, string> {
  const { token } = useAuth();
  return () => {
    const apiKey = localStorage.getItem("dlv_api_key");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (apiKey) headers["X-API-Key"] = apiKey;
    return headers;
  };
}

function ProviderKeysTab() {
  const getAuthHeaders = useAuthHeaders();
  const [keys, setKeys] = useState<ProviderKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newProvider, setNewProvider] = useState("openai");
  const [newLabel, setNewLabel] = useState("");
  const [newKey, setNewKey] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/providers/keys`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys ?? data);
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleAdd = async () => {
    if (!newKey.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/providers/keys`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          provider: newProvider,
          label: newLabel || `${newProvider} key`,
          api_key: newKey,
        }),
      });
      if (res.ok) {
        setNewKey("");
        setNewLabel("");
        setShowAddForm(false);
        await fetchKeys();
      }
    } catch {
      // Silently fail
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`${API_BASE}/providers/keys/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      await fetchKeys();
    } catch {
      // Silently fail
    }
  };

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium text-gray-900">Provider API Keys (BYOK)</h3>
          <p className="text-sm text-gray-500">
            Store your own API keys to use providers without spending credits.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3 py-1.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 transition-colors"
        >
          {showAddForm ? "Cancel" : "Add Key"}
        </button>
      </div>

      {showAddForm && (
        <div className="border border-dlv-border rounded-lg p-4 bg-gray-50 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={newProvider}
              onChange={(e) => setNewProvider(e.target.value)}
              className="w-full border border-dlv-border rounded-md px-3 py-2 text-sm"
            >
              <option value="openai">OpenAI</option>
              <option value="huggingface">HuggingFace</option>
              <option value="google">Google Cloud</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Label (optional)</label>
            <input
              type="text"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="My production key"
              className="w-full border border-dlv-border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="sk-..."
              className="w-full border border-dlv-border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleAdd}
            disabled={!newKey.trim() || saving}
            className="px-4 py-2 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Key"}
          </button>
        </div>
      )}

      {keys.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">No provider keys stored yet.</p>
      ) : (
        <div className="space-y-2">
          {keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between border border-dlv-border rounded-lg px-4 py-3 bg-white"
            >
              <div>
                <span className="font-medium text-gray-900">{key.label}</span>
                <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded capitalize">
                  {key.provider}
                </span>
                <p className="text-xs text-gray-400 mt-0.5">
                  Added {new Date(key.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(key.id)}
                className="text-red-500 hover:text-red-700 text-sm font-medium"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreditsTab() {
  const getAuthHeaders = useAuthHeaders();
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [balRes, txRes] = await Promise.all([
        fetch(`${API_BASE}/credits/balance`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/credits/transactions`, { headers: getAuthHeaders() }),
      ]);
      if (balRes.ok) {
        setBalance(await balRes.json());
      }
      if (txRes.ok) {
        const data = await txRes.json();
        setTransactions(data.transactions ?? data);
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePurchase = async (amount: number) => {
    setPurchasing(true);
    try {
      const res = await fetch(`${API_BASE}/credits/purchase`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ amount }),
      });
      if (res.ok) {
        await fetchData();
      }
    } catch {
      // Silently fail
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Balance */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
        <p className="text-sm text-gray-600">Current Balance</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">
          {balance?.balance ?? 0} <span className="text-lg font-normal text-gray-500">credits</span>
        </p>
      </div>

      {/* Purchase options */}
      <div>
        <h3 className="font-medium text-gray-900 mb-3">Purchase Credits</h3>
        <div className="grid grid-cols-3 gap-3">
          {[10, 50, 100].map((amount) => (
            <button
              key={amount}
              onClick={() => handlePurchase(amount)}
              disabled={purchasing}
              className="border border-dlv-border rounded-lg py-3 px-4 hover:border-dlv-accent hover:bg-blue-50 transition-all disabled:opacity-50 text-center"
            >
              <span className="block text-lg font-bold text-gray-900">{amount}</span>
              <span className="block text-xs text-gray-500">credits</span>
            </button>
          ))}
        </div>
      </div>

      {/* Transaction history */}
      <div>
        <h3 className="font-medium text-gray-900 mb-3">Transaction History</h3>
        {transactions.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No transactions yet.</p>
        ) : (
          <div className="space-y-2">
            {transactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between border border-dlv-border rounded-lg px-4 py-3 bg-white"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{tx.description}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(tx.created_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={`font-medium text-sm ${
                    tx.amount > 0 ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {tx.amount > 0 ? "+" : ""}
                  {tx.amount}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("provider-keys");

  const tabs: { id: Tab; label: string }[] = [
    { id: "provider-keys", label: "Provider Keys" },
    { id: "credits", label: "Credits" },
  ];

  return (
    <div className="max-w-4xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your provider API keys and translation credits.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-dlv-border">
        {/* Tab navigation */}
        <div className="border-b border-dlv-border px-4">
          <nav className="flex gap-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "border-dlv-accent text-dlv-accent"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab content */}
        <div className="p-6">
          {activeTab === "provider-keys" && <ProviderKeysTab />}
          {activeTab === "credits" && <CreditsTab />}
        </div>
      </div>
    </div>
  );
}
