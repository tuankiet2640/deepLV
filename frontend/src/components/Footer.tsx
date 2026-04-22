import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="border-t border-dlv-border bg-white">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 bg-dlv-blue rounded flex items-center justify-center font-bold text-xs text-white">
                LV
              </div>
              <span className="font-semibold text-gray-900">DeepLV</span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">
              Production-grade machine translation system. Built as a portfolio project demonstrating
              systems engineering at scale.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 mb-3 text-sm">Product</h3>
            <ul className="space-y-2">
              <li><Link to="/translate" className="text-sm text-gray-500 hover:text-dlv-accent">Translator</Link></li>
              <li><Link to="/getting-started" className="text-sm text-gray-500 hover:text-dlv-accent">Getting Started</Link></li>
              <li><Link to="/api-reference" className="text-sm text-gray-500 hover:text-dlv-accent">API Reference</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 mb-3 text-sm">Engineering</h3>
            <ul className="space-y-2">
              <li><Link to="/architecture" className="text-sm text-gray-500 hover:text-dlv-accent">Architecture</Link></li>
              <li><Link to="/status" className="text-sm text-gray-500 hover:text-dlv-accent">System Status</Link></li>
              <li><a href="/docs" className="text-sm text-gray-500 hover:text-dlv-accent">Swagger UI</a></li>
              <li><a href="/metrics" className="text-sm text-gray-500 hover:text-dlv-accent">Prometheus Metrics</a></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-gray-100 text-center text-xs text-gray-400">
          DeepLV &mdash; FastAPI + CTranslate2 + React + Redis + PostgreSQL
        </div>
      </div>
    </footer>
  );
}
