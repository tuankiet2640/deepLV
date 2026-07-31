import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  const icon =
    theme === "dark" ? (
      // Moon icon
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        />
      </svg>
    ) : theme === "light" ? (
      // Sun icon
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>
    ) : (
      // System/monitor icon
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
    );

  const label = theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System";

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
      title={`Theme: ${label}. Click to cycle.`}
      aria-label={`Current theme: ${label}. Click to change.`}
    >
      {icon}
      <span className="hidden lg:inline text-xs">{label}</span>
    </button>
  );
}

const NAV_LINKS = [
  { to: "/translate", label: "Translate" },
  { to: "/documents", label: "Documents" },
  { to: "/history", label: "History" },
  { to: "/getting-started", label: "Get Started" },
  { to: "/api-reference", label: "API Reference" },
  { to: "/architecture", label: "Architecture" },
  { to: "/status", label: "Status" },
];

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isAdmin = !!user?.is_admin;

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close dropdown on navigation
  useEffect(() => {
    setDropdownOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    setDropdownOpen(false);
    navigate("/login", { replace: true });
  };

  return (
    <header className="bg-dlv-blue text-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
          <div className="w-8 h-8 bg-dlv-accent rounded-lg flex items-center justify-center font-bold text-sm">
            LV
          </div>
          <h1 className="text-xl font-semibold tracking-tight">DeepLV</h1>
        </Link>
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                location.pathname === link.to
                  ? "bg-white/15 text-white font-medium"
                  : "text-gray-300 hover:text-white hover:bg-white/10"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {isAdmin && (
            <Link
              to="/admin"
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                location.pathname === "/admin"
                  ? "bg-white/15 text-white font-medium"
                  : "text-yellow-300 hover:text-white hover:bg-white/10"
              }`}
            >
              Admin
            </Link>
          )}
          {/* Theme toggle */}
          <ThemeToggle />
          {/* Auth section */}
          {isAuthenticated ? (
            <div className="relative ml-2" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              >
                <span className="w-6 h-6 bg-dlv-accent/80 rounded-full flex items-center justify-center text-xs font-medium text-white">
                  {user?.email?.charAt(0).toUpperCase() ?? "U"}
                </span>
                <span className="max-w-[120px] truncate">{user?.email}</span>
                <svg
                  className={`w-3 h-3 transition-transform ${dropdownOpen ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-dlv-dark-card rounded-lg shadow-lg border border-dlv-border dark:border-dlv-dark-border py-1 z-50">
                  <div className="px-4 py-2 border-b border-dlv-border dark:border-dlv-dark-border">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Signed in as</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{user?.email}</p>
                  </div>
                  <Link
                    to="/profile"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5"
                  >
                    Profile
                  </Link>
                  <Link
                    to="/api-keys"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5"
                  >
                    API Keys
                  </Link>
                  <Link
                    to="/settings"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5"
                  >
                    Settings
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 ml-2">
              <Link
                to="/login"
                className="px-3 py-1.5 rounded-md text-sm text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="px-3 py-1.5 bg-dlv-accent rounded-md text-sm font-medium text-white hover:bg-dlv-accent/90 transition-colors"
              >
                Register
              </Link>
            </div>
          )}
        </nav>
        {/* Mobile menu */}
        <nav className="flex md:hidden items-center gap-2">
          <Link
            to="/translate"
            className="px-3 py-1.5 bg-dlv-accent rounded-md text-sm font-medium"
          >
            Translate
          </Link>
          {isAuthenticated ? (
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 bg-white/10 rounded-md text-sm font-medium"
            >
              Sign out
            </button>
          ) : (
            <Link
              to="/login"
              className="px-3 py-1.5 bg-white/10 rounded-md text-sm font-medium"
            >
              Sign in
            </Link>
          )}
          {isAdmin && (
            <Link
              to="/admin"
              className="px-3 py-1.5 bg-yellow-500/80 rounded-md text-sm font-medium"
            >
              Admin
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
