import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const API_BASE = "/api/v1";

export interface AuthUser {
  id: string;
  email: string;
  role?: string;
  is_admin?: boolean;
  is_verified?: boolean;
  display_name?: string | null;
  has_avatar?: boolean;
  default_source_lang?: string;
  default_target_lang?: string;
  theme_preference?: string;
  translation_count?: number;
  credits_balance?: number;
  created_at?: string;
  last_login_at?: string | null;
}

export function hasAdminAccess(user: AuthUser | null): boolean {
  return user?.role === "admin" || user?.role === "support";
}

export class AuthError extends Error {
  code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = "AuthError";
    this.code = code;
  }
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithToken: (accessToken: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function fetchUserProfile(accessToken: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/users/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to load profile (HTTP ${res.status})`);
  }
  const data = await res.json();
  return {
    id: data.id,
    email: data.email,
    role: data.role,
    is_admin: data.is_admin,
    is_verified: data.is_verified,
    display_name: data.display_name,
    has_avatar: data.has_avatar,
    default_source_lang: data.default_source_lang,
    default_target_lang: data.default_target_lang,
    theme_preference: data.theme_preference,
    translation_count: data.translation_count,
    credits_balance: data.credits_balance,
    created_at: data.created_at,
    last_login_at: data.last_login_at,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("dlv_token");
    const storedUser = localStorage.getItem("user");
    if (storedToken && storedUser) {
      try {
        const parsed = JSON.parse(storedUser) as AuthUser;
        setToken(storedToken);
        setUser(parsed);
      } catch {
        localStorage.removeItem("dlv_token");
        localStorage.removeItem("user");
      }
    }
    setIsLoading(false);
  }, []);

  const applySession = useCallback(async (accessToken: string) => {
    const userData = await fetchUserProfile(accessToken);
    localStorage.setItem("dlv_token", accessToken);
    localStorage.setItem("user", JSON.stringify(userData));
    setToken(accessToken);
    setUser(userData);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Login failed" }));
        if (body.detail && typeof body.detail === "object") {
          throw new AuthError(
            body.detail.message ?? "Login failed",
            body.detail.error,
          );
        }
        throw new AuthError(body.detail ?? `Login failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      await applySession(data.access_token);
    },
    [applySession],
  );

  const loginWithToken = useCallback(
    async (accessToken: string) => {
      await applySession(accessToken);
    },
    [applySession],
  );

  const register = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(body.detail ?? `Registration failed (HTTP ${res.status})`);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem("dlv_token");
    if (!storedToken) return;
    const userData = await fetchUserProfile(storedToken);
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("dlv_token");
    localStorage.removeItem("user");
    localStorage.removeItem("dlv_api_key");
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: !!token && !!user,
      isLoading,
      login,
      loginWithToken,
      register,
      refreshUser,
      logout,
    }),
    [user, token, isLoading, login, loginWithToken, register, refreshUser, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
