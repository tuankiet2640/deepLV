import { Link } from "react-router-dom";

const FEATURES = [
  {
    title: "10 Languages",
    desc: "English, German, French, Spanish, Chinese, Japanese, Vietnamese, Korean, Portuguese, Russian. Non-English pairs pivot through English automatically.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
      </svg>
    ),
  },
  {
    title: "Sub-Second Latency",
    desc: "CTranslate2 INT8 quantized inference. Redis translation cache with 24h TTL. Cached responses in <5ms.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    title: "Production API",
    desc: "JWT authentication, API key management, per-key rate limiting (sliding window), usage tracking and analytics.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
  },
  {
    title: "Auto Language Detection",
    desc: "Fasttext-based language identification. Send source_lang='auto' and the system detects it in <10ms.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    title: "Observable",
    desc: "Prometheus metrics, structured JSON logging, health checks on all dependencies, request correlation IDs.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    title: "One Command Deploy",
    desc: "docker compose up -- 5 containers, health checks, volume persistence, auto-restart. Full system in under 2 minutes.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
  },
];

const TECH_STACK = [
  { name: "FastAPI", role: "API Gateway" },
  { name: "CTranslate2", role: "ML Inference" },
  { name: "MarianMT", role: "Translation Models" },
  { name: "Redis", role: "Cache + Rate Limits" },
  { name: "PostgreSQL", role: "Persistence" },
  { name: "React + TypeScript", role: "Frontend" },
  { name: "Docker Compose", role: "Orchestration" },
  { name: "Prometheus", role: "Metrics" },
];

export function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-dlv-blue text-white">
        <div className="max-w-6xl mx-auto px-4 py-20 text-center">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Machine Translation,<br />Production-Grade
          </h1>
          <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8 leading-relaxed">
            A complete translation system with real ML inference, caching, auth, rate limiting,
            observability, and a clean API. Not a wrapper around Google Translate.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/translate"
              className="px-6 py-3 bg-dlv-accent text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
            >
              Try the Translator
            </Link>
            <Link
              to="/getting-started"
              className="px-6 py-3 bg-white/10 text-white rounded-lg font-medium hover:bg-white/20 transition-colors"
            >
              Get Started with the API
            </Link>
          </div>
        </div>
      </section>

      {/* Live demo hint */}
      <section className="border-b border-dlv-border bg-white">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-4 bg-blue-50 border border-blue-200 rounded-lg px-5 py-4">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse flex-shrink-0" />
            <p className="text-sm text-gray-700">
              <strong>Live system.</strong> The API, model worker, Redis cache, and PostgreSQL are all running right now.
              Hit <Link to="/status" className="text-dlv-accent underline">System Status</Link> to see real-time health
              or <a href="/metrics" className="text-dlv-accent underline">Prometheus metrics</a> for request telemetry.
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">
            What makes this portfolio-grade
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-white border border-dlv-border rounded-xl p-6 hover:shadow-md transition-shadow"
              >
                <div className="w-10 h-10 bg-blue-50 text-dlv-accent rounded-lg flex items-center justify-center mb-4">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 bg-white border-y border-dlv-border">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Tech Stack</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {TECH_STACK.map((t) => (
              <div key={t.name} className="text-center py-4">
                <div className="font-semibold text-gray-900 text-sm">{t.name}</div>
                <div className="text-xs text-gray-400 mt-1">{t.role}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture preview */}
      <section className="py-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">System Architecture</h2>
          <p className="text-gray-500 mb-8 max-w-xl mx-auto">
            5 services, each with a clear responsibility. Every design decision is documented with trade-offs.
          </p>
          <div className="bg-dlv-blue rounded-xl p-8 text-left overflow-x-auto">
            <pre className="text-green-400 text-sm font-mono leading-relaxed">
{`Client (React)
   |
   v
FastAPI Gateway :8000 ── auth, rate limit, language detect, cache check
   |           |
   v           v
 Redis       Model Worker :8001 ── CTranslate2 INT8 inference
 (cache)       |                    LRU model cache (max 6 pairs)
               v
             MarianMT models (Opus-MT, HuggingFace)
   |
   v
PostgreSQL ── users, API keys, usage logs`}
            </pre>
          </div>
          <Link
            to="/architecture"
            className="inline-block mt-6 text-dlv-accent text-sm font-medium hover:underline"
          >
            View full architecture docs &rarr;
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-dlv-blue text-white">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold mb-4">Ready to explore?</h2>
          <p className="text-gray-300 mb-6">
            Start with the translator, read the API docs, or check out the architecture.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/translate" className="px-6 py-3 bg-dlv-accent rounded-lg font-medium hover:bg-blue-600 transition-colors">
              Open Translator
            </Link>
            <Link to="/api-reference" className="px-6 py-3 bg-white/10 rounded-lg font-medium hover:bg-white/20 transition-colors">
              API Reference
            </Link>
            <a href="/docs" className="px-6 py-3 bg-white/10 rounded-lg font-medium hover:bg-white/20 transition-colors">
              Swagger UI
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
