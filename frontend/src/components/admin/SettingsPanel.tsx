import { useEffect, useState } from "react";

interface Setting {
  key: string;
  value: string;
}

const API_BASE = "/api/v1";

const SETTING_LABELS: Record<string, { label: string; description: string }> = {
  credit_cost_per_1k_chars: {
    label: "Credit Cost per 1K Characters",
    description: "Number of credits deducted per 1,000 characters when users pay with platform credits.",
  },
  max_document_size_mb: {
    label: "Max Document Size (MB)",
    description: "Maximum allowed document upload size in megabytes.",
  },
  max_translation_chars: {
    label: "Max Translation Characters",
    description: "Maximum characters per single translation request.",
  },
  free_tier_daily_chars: {
    label: "Free Tier Daily Characters",
    description: "Number of characters free-tier users can translate per day without spending credits.",
  },
};

export function SettingsPanel() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const token = localStorage.getItem("dlv_token");
        const res = await fetch(`${API_BASE}/admin/settings`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`);
        const data = await res.json();
        setSettings(data.settings);
        const values: Record<string, string> = {};
        data.settings.forEach((s: Setting) => {
          values[s.key] = s.value;
        });
        setEditValues(values);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const token = localStorage.getItem("dlv_token");
      const res = await fetch(`${API_BASE}/admin/settings`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ settings: editValues }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Failed to save: ${res.status}`);
      }
      const data = await res.json();
      setSettings(data.settings);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
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
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-700 text-sm">
          Settings saved successfully.
        </div>
      )}

      <div className="bg-white rounded-lg border border-dlv-border p-4 space-y-5">
        <h4 className="text-sm font-semibold text-gray-700">Platform Settings</h4>
        {settings.map((setting) => {
          const meta = SETTING_LABELS[setting.key];
          return (
            <div key={setting.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {meta?.label || setting.key}
              </label>
              {meta?.description && (
                <p className="text-xs text-gray-500 mb-2">{meta.description}</p>
              )}
              <input
                type="text"
                value={editValues[setting.key] || ""}
                onChange={(e) =>
                  setEditValues((prev) => ({
                    ...prev,
                    [setting.key]: e.target.value,
                  }))
                }
                className="w-full max-w-xs px-3 py-2 border border-dlv-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
              />
            </div>
          );
        })}
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="px-5 py-2 bg-dlv-accent text-white rounded-md text-sm font-medium hover:bg-dlv-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {saving ? "Saving..." : "Save Settings"}
      </button>
    </div>
  );
}
