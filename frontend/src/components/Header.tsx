import { Link, useLocation } from "react-router-dom";

const NAV_LINKS = [
  { to: "/translate", label: "Translate" },
  { to: "/getting-started", label: "Get Started" },
  { to: "/api-reference", label: "API Reference" },
  { to: "/architecture", label: "Architecture" },
  { to: "/status", label: "Status" },
];

export function Header() {
  const location = useLocation();

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
        </nav>
        {/* Mobile menu */}
        <nav className="flex md:hidden items-center gap-2">
          <Link
            to="/translate"
            className="px-3 py-1.5 bg-dlv-accent rounded-md text-sm font-medium"
          >
            Translate
          </Link>
        </nav>
      </div>
    </header>
  );
}
