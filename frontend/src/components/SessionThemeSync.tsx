import { useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

/**
 * Applies the signed-in user's server-stored theme preference on login,
 * so the choice follows them across devices instead of staying purely
 * localStorage-bound.
 */
export function SessionThemeSync() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    if (!user?.theme_preference) return;
    if (user.theme_preference === theme) return;
    if (user.theme_preference !== "light" && user.theme_preference !== "dark" && user.theme_preference !== "system") {
      return;
    }
    setTheme(user.theme_preference);
    // Deliberately depend only on user identity/preference, not `theme` --
    // otherwise a manual theme toggle would get immediately overwritten.
  }, [user?.id, user?.theme_preference]);

  return null;
}
