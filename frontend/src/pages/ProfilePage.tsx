import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { useToast } from "../contexts/ToastContext";
import { AvatarUpload } from "../components/AvatarUpload";
import { LANGUAGES, TARGET_LANGUAGES } from "../constants/languages";

const API_BASE = "/api/v1";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function ProfilePage() {
  const { user, token, refreshUser } = useAuth();
  const { setTheme } = useTheme();
  const { showToast } = useToast();

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [savingName, setSavingName] = useState(false);

  const [sourceLang, setSourceLang] = useState(user?.default_source_lang ?? "auto");
  const [targetLang, setTargetLang] = useState(user?.default_target_lang ?? "de");
  const [themePref, setThemePref] = useState(user?.theme_preference ?? "system");
  const [savingPrefs, setSavingPrefs] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(user?.display_name ?? "");
    setSourceLang(user?.default_source_lang ?? "auto");
    setTargetLang(user?.default_target_lang ?? "de");
    setThemePref(user?.theme_preference ?? "system");
  }, [user]);

  const patchProfile = async (payload: Record<string, string>) => {
    const res = await fetch(`${API_BASE}/users/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "Update failed" }));
      throw new Error(body.detail ?? "Update failed");
    }
    await refreshUser();
  };

  const handleSaveName = async (e: FormEvent) => {
    e.preventDefault();
    setSavingName(true);
    try {
      await patchProfile({ display_name: displayName });
      showToast("Display name updated", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to update name", "error");
    } finally {
      setSavingName(false);
    }
  };

  const handleSavePreferences = async (e: FormEvent) => {
    e.preventDefault();
    setSavingPrefs(true);
    try {
      await patchProfile({
        default_source_lang: sourceLang,
        default_target_lang: targetLang,
        theme_preference: themePref,
      });
      setTheme(themePref as "light" | "dark" | "system");
      showToast("Preferences saved", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to save preferences", "error");
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordError(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters");
      return;
    }

    setChangingPassword(true);

    try {
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Failed to change password" }));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }

      showToast("Password changed successfully", "success");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Failed to change password");
      showToast("Failed to change password", "error");
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Profile</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Manage your account, preferences, and password.
        </p>
      </div>

      {/* Avatar + Display Name */}
      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Avatar & Display Name</h2>
        <AvatarUpload />
        <form onSubmit={handleSaveName} className="mt-5 flex items-end gap-3">
          <div className="flex-1">
            <label htmlFor="display-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Display Name
            </label>
            <input
              id="display-name"
              type="text"
              maxLength={100}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How you'd like to be addressed"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={savingName}
            className="px-4 py-2 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {savingName ? "Saving..." : "Save"}
          </button>
        </form>
      </div>

      {/* Account Info */}
      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Account Information</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-dlv-border dark:border-dlv-dark-border">
            <span className="text-sm text-gray-500 dark:text-gray-400">Email</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.email ?? "N/A"}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dlv-border dark:border-dlv-dark-border">
            <span className="text-sm text-gray-500 dark:text-gray-400">Role</span>
            <span className="text-sm font-medium">
              {user?.is_admin ? (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300">
                  Admin
                </span>
              ) : (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
                  User
                </span>
              )}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dlv-border dark:border-dlv-dark-border">
            <span className="text-sm text-gray-500 dark:text-gray-400">Member since</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatDate(user?.created_at)}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dlv-border dark:border-dlv-dark-border">
            <span className="text-sm text-gray-500 dark:text-gray-400">Last login</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatDate(user?.last_login_at)}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dlv-border dark:border-dlv-dark-border">
            <span className="text-sm text-gray-500 dark:text-gray-400">Translations made</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {user?.translation_count ?? 0}
            </span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Account ID</span>
            <span className="text-sm font-mono text-gray-600 dark:text-gray-400">{user?.id ?? "N/A"}</span>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Preferences</h2>
        <form onSubmit={handleSavePreferences} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="default-source" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Default source language
              </label>
              <select
                id="default-source"
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="default-target" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Default target language
              </label>
              <select
                id="default-target"
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
              >
                {TARGET_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="theme-pref" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Theme
            </label>
            <select
              id="theme-pref"
              value={themePref}
              onChange={(e) => setThemePref(e.target.value)}
              className="w-full sm:w-48 border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={savingPrefs}
            className="px-4 py-2.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {savingPrefs ? "Saving..." : "Save Preferences"}
          </button>
        </form>
      </div>

      {/* Quick Links */}
      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Quick Links</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Link
            to="/api-keys"
            className="flex items-center gap-3 p-3 rounded-lg border border-dlv-border dark:border-dlv-dark-border hover:border-dlv-accent hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
          >
            <svg className="w-5 h-5 text-dlv-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">API Keys</span>
          </Link>
          <Link
            to="/settings"
            className="flex items-center gap-3 p-3 rounded-lg border border-dlv-border dark:border-dlv-dark-border hover:border-dlv-accent hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
          >
            <svg className="w-5 h-5 text-dlv-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Settings</span>
          </Link>
          <Link
            to="/history"
            className="flex items-center gap-3 p-3 rounded-lg border border-dlv-border dark:border-dlv-dark-border hover:border-dlv-accent hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
          >
            <svg className="w-5 h-5 text-dlv-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">History</span>
          </Link>
        </div>
      </div>

      {/* Change Password */}
      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Change Password</h2>

        {passwordError && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {passwordError}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter current password"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 8 characters"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="confirm-new-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confirm New Password
            </label>
            <input
              id="confirm-new-password"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat new password"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={changingPassword}
            className="px-4 py-2.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {changingPassword ? "Changing..." : "Change Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
