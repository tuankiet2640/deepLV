import { useEffect, useState } from "react";

interface UserSummary {
  id: string;
  email: string;
  is_admin: boolean;
  credits_balance: number;
  created_at: string;
  usage_count: number;
  total_chars_translated: number;
}

const API_BASE = "/api/v1";

export function UserTable() {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("dlv_token");
      const res = await fetch(`${API_BASE}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
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
  }, []);

  const toggleAdmin = async (userId: string, currentStatus: boolean) => {
    const token = localStorage.getItem("dlv_token");
    const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ is_admin: !currentStatus }),
    });
    if (res.ok) {
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, is_admin: !currentStatus } : u
        )
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
        <h3 className="text-lg font-semibold text-gray-900">
          Users ({total})
        </h3>
        <button
          onClick={fetchUsers}
          className="text-sm text-dlv-accent hover:underline"
        >
          Refresh
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 border-b border-dlv-border">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="px-4 py-3 font-medium text-gray-600">Credits</th>
              <th className="px-4 py-3 font-medium text-gray-600">Translations</th>
              <th className="px-4 py-3 font-medium text-gray-600">Characters</th>
              <th className="px-4 py-3 font-medium text-gray-600">Admin</th>
              <th className="px-4 py-3 font-medium text-gray-600">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dlv-border">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-900 font-medium">
                  {user.email}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {user.credits_balance.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {user.usage_count.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {user.total_chars_translated.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleAdmin(user.id, user.is_admin)}
                    className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                      user.is_admin
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {user.is_admin ? "Admin" : "User"}
                  </button>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
