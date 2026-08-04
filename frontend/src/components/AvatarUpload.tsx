import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

const API_BASE = "/api/v1";
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_SIZE_MB = 2;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export function AvatarUpload() {
  const { user, token, refreshUser } = useAuth();
  const { showToast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const loadAvatar = useCallback(async () => {
    if (!user?.has_avatar || !token) {
      setAvatarUrl(null);
      return;
    }
    const res = await fetch(`${API_BASE}/users/me/avatar`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setAvatarUrl(null);
      return;
    }
    const blob = await res.blob();
    setAvatarUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(blob);
    });
  }, [user?.has_avatar, token]);

  useEffect(() => {
    loadAvatar();
    return () => {
      setAvatarUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [user?.has_avatar, loadAvatar]);

  const handleFile = async (file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      showToast("Only PNG, JPEG, or WebP images are supported", "error");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      showToast(`Image too large. Maximum size is ${MAX_SIZE_MB}MB`, "error");
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/users/me/avatar`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(body.detail ?? "Upload failed");
      }
      await refreshUser();
      showToast("Avatar updated", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Upload failed", "error");
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = async () => {
    setIsUploading(true);
    try {
      const res = await fetch(`${API_BASE}/users/me/avatar`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to remove avatar");
      await refreshUser();
      showToast("Avatar removed", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to remove avatar", "error");
    } finally {
      setIsUploading(false);
    }
  };

  const initial = (user?.display_name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="flex items-center gap-4">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="relative w-16 h-16 rounded-full overflow-hidden bg-dlv-accent/10 border border-dlv-border dark:border-dlv-dark-border flex items-center justify-center text-lg font-semibold text-dlv-accent hover:opacity-80 transition-opacity disabled:opacity-50"
        title="Click to change avatar"
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
        ) : (
          initial
        )}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />
      <div className="flex flex-col gap-1">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className="text-sm font-medium text-dlv-accent hover:underline disabled:opacity-50 text-left"
        >
          {isUploading ? "Uploading..." : "Change avatar"}
        </button>
        {user?.has_avatar && (
          <button
            type="button"
            onClick={handleRemove}
            disabled={isUploading}
            className="text-sm text-gray-500 dark:text-gray-400 hover:underline disabled:opacity-50 text-left"
          >
            Remove
          </button>
        )}
        <p className="text-xs text-gray-400">PNG, JPEG, or WebP. Max {MAX_SIZE_MB}MB.</p>
      </div>
    </div>
  );
}
