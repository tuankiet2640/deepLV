import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { UserTable } from "../components/admin/UserTable";
import { UsageChart } from "../components/admin/UsageChart";
import { ProviderKeyManager } from "../components/admin/ProviderKeyManager";
import { SettingsPanel } from "../components/admin/SettingsPanel";
import { AuditLogTable } from "../components/admin/AuditLogTable";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

type Tab = "users" | "usage" | "provider-keys" | "settings" | "audit-log";

const TABS: { id: Tab; label: string; adminOnly?: boolean }[] = [
  { id: "users", label: "Users" },
  { id: "usage", label: "Usage Analytics" },
  { id: "provider-keys", label: "Provider Keys", adminOnly: true },
  { id: "settings", label: "Settings", adminOnly: true },
  { id: "audit-log", label: "Audit Log", adminOnly: true },
];

export function AdminPage() {
  useDocumentTitle("Admin Dashboard");
  const { user } = useAuth();
  const isFullAdmin = user?.role === "admin";
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || isFullAdmin);
  const [activeTab, setActiveTab] = useState<Tab>("users");

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage users, view platform analytics, configure provider keys and settings.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-dlv-border mb-6">
        <nav className="flex gap-1 -mb-px">
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-dlv-accent text-dlv-accent"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="bg-dlv-surface rounded-xl shadow-sm border border-dlv-border p-6">
        {activeTab === "users" && <UserTable />}
        {activeTab === "usage" && <UsageChart />}
        {activeTab === "provider-keys" && <ProviderKeyManager />}
        {activeTab === "settings" && <SettingsPanel />}
        {activeTab === "audit-log" && <AuditLogTable />}
      </div>
    </div>
  );
}
