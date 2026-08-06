import { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";

type Role = "user" | "support" | "admin";
type StatusFilter = "all" | "active" | "inactive";

interface UserSummary {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  deactivated_at: string | null;
  deactivation_reason: string | null;
  credits_balance: number;
  created_at: string;
  usage_count: number;
  total_chars_translated: number;
}

const ROLE_STYLES: Record<Role, string> = {
  admin: "bg-green-100 text-green-700",
  support: "bg-blue-100 text-blue-700",
  user: "bg-gray-100 text-gray-500",
};

const API_BASE = "/api/v1";

export function UserTable() {
  const { user: viewer } = useAuth();
  const canManage = viewer?.role === "admin";
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  // The deactivation reason modal targets one user at a time.
  const [deactivateTarget, setDeactivateTarget] = useState<UserSummary | null>(null);
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem("dlv_token")}`,
    "Content-Type": "application/json",
  });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/users?status=${statusFilter}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`Failed to fetch users: ${res.status}`);
      const data = await res.json();
      setUsers(data.users);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const updateRole = async (userId: string, role: Role) => {
    const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ role }),
    });
    if (res.ok) {
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role } : u)));
    }
  };

  const confirmDeactivate = async () => {
    if (!deactivateTarget || reason.trim().length === 0) return;
    setBusy(true);
    setActionError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/users/${deactivateTarget.id}/deactivate`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ reason: reason.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail ?? `Failed (HTTP ${res.status})`);
      }
      // The active filter no longer matches this user; refetch to stay consistent.
      if (statusFilter === "active") {
        await fetchUsers();
      } else {
        setUsers((prev) =>
          prev.map((u) =>
            u.id === data.id
              ? {
                  ...u,
                  is_active: false,
                  deactivated_at: data.deactivated_at,
                  deactivation_reason: data.deactivation_reason,
                }
              : u,
          ),
        );
      }
      setDeactivateTarget(null);
      setReason("");
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const reactivate = async (user: UserSummary) => {
    const res = await fetch(`${API_BASE}/admin/users/${user.id}/reactivate`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data?.detail ?? `Failed to reactivate (HTTP ${res.status})`);
      return;
    }
    if (statusFilter === "inactive") {
      await fetchUsers();
    } else {
      setUsers((prev) =>
        prev.map((u) =>
          u.id === user.id
            ? { ...u, is_active: true, deactivated_at: null, deactivation_reason: null }
            : u,
        ),
      );
    }
  };

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
        <h3 className="text-lg font-semibold text-gray-900">Users ({total})</h3>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="text-sm border border-dlv-border rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
          >
            <option value="all">All statuses</option>
            <option value="active">Active only</option>
            <option value="inactive">Deactivated only</option>
          </select>
          <button onClick={fetchUsers} className="text-sm text-dlv-accent hover:underline">
            Refresh
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 border-b border-dlv-border">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="px-4 py-3 font-medium text-gray-600">Credits</th>
              <th className="px-4 py-3 font-medium text-gray-600">Translations</th>
              <th className="px-4 py-3 font-medium text-gray-600">Role</th>
              <th className="px-4 py-3 font-medium text-gray-600">Joined</th>
              {canManage && <th className="px-4 py-3 font-medium text-gray-600">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-dlv-border">
            {users.map((user) => (
              <tr
                key={user.id}
                className={`hover:bg-gray-50 ${user.is_active ? "" : "bg-red-50/40"}`}
              >
                <td className="px-4 py-3 text-gray-900 font-medium">{user.email}</td>
                <td className="px-4 py-3">
                  {user.is_active ? (
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                      Active
                    </span>
                  ) : (
                    <span
                      className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 cursor-help"
                      title={
                        user.deactivation_reason
                          ? `Reason: ${user.deactivation_reason}`
                          : "Deactivated"
                      }
                    >
                      Deactivated
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-700">{user.credits_balance.toFixed(1)}</td>
                <td className="px-4 py-3 text-gray-700">{user.usage_count.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <select
                    value={user.role}
                    disabled={!canManage}
                    onChange={(e) => updateRole(user.id, e.target.value as Role)}
                    className={`px-2 py-0.5 rounded text-xs font-medium border-0 ${ROLE_STYLES[user.role]} ${
                      canManage ? "cursor-pointer" : "cursor-default opacity-80"
                    }`}
                  >
                    <option value="user">User</option>
                    <option value="support">Support</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                {canManage && (
                  <td className="px-4 py-3">
                    {user.id === viewer?.id ? (
                      <span className="text-xs text-gray-400">You</span>
                    ) : user.is_active ? (
                      <button
                        onClick={() => {
                          setDeactivateTarget(user);
                          setReason("");
                          setActionError(null);
                        }}
                        className="text-xs font-medium text-red-600 hover:text-red-800 hover:underline"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => reactivate(user)}
                        className="text-xs font-medium text-dlv-accent hover:underline"
                      >
                        Reactivate
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={canManage ? 7 : 6} className="px-4 py-6 text-center text-gray-500">
                  No users match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Deactivation reason modal */}
      {deactivateTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-xl shadow-xl border border-dlv-border w-full max-w-md p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-1">Deactivate account</h4>
            <p className="text-sm text-gray-500 mb-4">
              {deactivateTarget.email} will be signed out and blocked from signing in. This is
              reversible. A reason is required and recorded in the audit log.
            </p>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Reason (e.g. abuse report, user request, non-payment)"
              className="w-full border border-dlv-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
            />
            {actionError && (
              <p className="text-sm text-red-600 mt-2">{actionError}</p>
            )}
            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={() => setDeactivateTarget(null)}
                disabled={busy}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeactivate}
                disabled={busy || reason.trim().length === 0}
                className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy ? "Deactivating…" : "Deactivate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
