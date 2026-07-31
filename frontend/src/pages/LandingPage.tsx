import { Link } from "react-router-dom";

const STATS = [
  { value: "10+", label: "Languages" },
  { value: "<1s", label: "Translation Speed" },
  { value: "99.9%", label: "Uptime" },
  { value: "Enterprise", label: "Ready" },
];

const STEPS = [
  {
    step: "01",
    title: "Type or Upload",
    description:
      "Enter text directly or upload PDF, DOCX, and TXT files for translation.",
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
        />
      </svg>
    ),
  },
  {
    step: "02",
    title: "Choose Provider",
    description:
      "Use our free built-in engine, or bring your own OpenAI, HuggingFace, or Google key.",
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M8 9l4-4 4 4m0 6l-4 4-4-4"
        />
      </svg>
    ),
  },
  {
    step: "03",
    title: "Get Translation",
    description:
      "Receive high-quality translations in milliseconds. Download translated documents instantly.",
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
];

const FEATURES = [
  {
    title: "Free Built-in Translation",
    description:
      "MarianMT-powered translations at zero cost. No API keys, no credit cards, no limits on getting started.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  {
    title: "Bring Your Own Key",
    description:
      "Connect your OpenAI, HuggingFace, or Google Translate API keys for premium translation quality.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
        />
      </svg>
    ),
  },
  {
    title: "Document Translation",
    description:
      "Upload PDF, DOCX, or TXT files and get them translated end-to-end. Smart chunking handles large documents.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    title: "Real-time Translation",
    description:
      "Translations appear as you type with sub-second latency powered by optimized inference and intelligent caching.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    ),
  },
  {
    title: "Encrypted Key Storage",
    description:
      "Your API keys are encrypted at rest and never exposed. Enterprise-grade security for your credentials.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
        />
      </svg>
    ),
  },
  {
    title: "Multi-Provider Flexibility",
    description:
      "Switch between translation providers per request. Compare quality across engines for your specific use case.",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
        />
      </svg>
    ),
  },
];

const PROVIDERS = [
  { name: "MarianMT", tag: "Free", description: "Open-source neural machine translation" },
  { name: "OpenAI", tag: "BYOK", description: "GPT-powered contextual translation" },
  { name: "HuggingFace", tag: "BYOK", description: "State-of-the-art transformer models" },
  { name: "Google", tag: "BYOK", description: "Google Cloud Translation API" },
];

const PRICING_TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Get started with MarianMT-powered translations at no cost.",
    features: [
      "MarianMT translation engine",
      "10 language pairs",
      "5,000 characters per request",
      "Rate limited (fair use)",
      "Text translation",
      "Community support",
    ],
    cta: "Start Free",
    highlight: false,
  },
  {
    name: "Bring Your Own Key",
    price: "$0",
    period: "from us",
    description: "Use your own API keys for premium providers. We never charge you.",
    features: [
      "OpenAI, HuggingFace, Google",
      "Unlimited translations",
      "Document translation (PDF, DOCX, TXT)",
      "No character limits",
      "Encrypted key storage",
      "Priority processing",
    ],
    cta: "Connect Your Key",
    highlight: true,
  },
  {
    name: "Credits",
    price: "Pay per use",
    period: "",
    description: "Use our managed premium keys. Pay only for what you translate.",
    features: [
      "All premium providers",
      "No API key needed",
      "Document translation",
      "Usage-based billing",
      "Detailed analytics",
      "Priority support",
    ],
    cta: "Buy Credits",
    highlight: false,
  },
];

const API_CODE_SNIPPET = `curl -X POST https://api.deeplv.com/api/v1/translate \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Hello, world!",
    "source_lang": "en",
    "target_lang": "de",
    "provider": "openai"
  }'

# Response:
{
  "translated_text": "Hallo, Welt!",
  "source_lang": "en",
  "target_lang": "de",
  "provider": "openai",
  "cached": false,
  "latency_ms": 245
}`;

export function LandingPage() {
  return (
    <div className="overflow-hidden">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-dlv-blue to-[#163d5e] text-white">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-dlv-accent/10 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-dlv-accent/5 blur-3xl" />
        </div>
        <div className="relative max-w-6xl mx-auto px-4 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 border border-white/20 text-sm text-gray-200 mb-8">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            Now with multi-provider support
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight mb-6 leading-tight">
            AI Translation
            <br />
            <span className="text-dlv-accent">Without Limits</span>
          </h1>
          <p className="text-lg md:text-xl text-gray-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            Translate text and documents across 10+ languages using free built-in models
            or bring your own API keys from OpenAI, HuggingFace, and Google.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="px-8 py-3.5 bg-dlv-accent text-white rounded-lg font-semibold hover:bg-[#0065b8] transition-all shadow-lg shadow-dlv-accent/25 hover:shadow-dlv-accent/40"
            >
              Start Translating Free
            </Link>
            <a
              href="#pricing"
              className="px-8 py-3.5 bg-white/10 text-white rounded-lg font-semibold hover:bg-white/20 transition-all border border-white/20"
            >
              View Pricing
            </a>
          </div>

          {/* Mini demo preview */}
          <div className="mt-16 max-w-3xl mx-auto">
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 shadow-2xl">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="text-left">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                      English
                    </span>
                    <span className="text-xs text-gray-500">Auto-detected</span>
                  </div>
                  <p className="text-gray-200 text-base leading-relaxed">
                    The future of translation is here. Fast, accurate, and available in
                    multiple languages with the providers you trust.
                  </p>
                </div>
                <div className="text-left border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-dlv-accent uppercase tracking-wider">
                      German
                    </span>
                    <span className="text-xs text-gray-500">via MarianMT</span>
                  </div>
                  <p className="text-gray-200 text-base leading-relaxed">
                    Die Zukunft der Ubersetzung ist da. Schnell, genau und in mehreren
                    Sprachen mit den Anbietern, denen Sie vertrauen.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="bg-white border-b border-dlv-border">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl md:text-3xl font-bold text-dlv-blue">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-dlv-surface">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-gray-500 max-w-xl mx-auto text-lg">
              Three simple steps to translate any content
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {STEPS.map((step, i) => (
              <div key={step.step} className="relative">
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-12 left-full w-full h-px border-t-2 border-dashed border-dlv-border -translate-x-1/2 z-0" />
                )}
                <div className="relative bg-white rounded-2xl p-8 shadow-sm border border-dlv-border text-center hover:shadow-md transition-shadow">
                  <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-dlv-accent/10 text-dlv-accent mb-5">
                    {step.icon}
                  </div>
                  <div className="text-xs font-bold text-dlv-accent uppercase tracking-widest mb-2">
                    Step {step.step}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {step.title}
                  </h3>
                  <p className="text-gray-500 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Everything You Need
            </h2>
            <p className="text-gray-500 max-w-xl mx-auto text-lg">
              A complete translation platform built for developers and teams
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="group bg-white border border-dlv-border rounded-2xl p-7 hover:shadow-lg hover:border-dlv-accent/30 transition-all duration-200"
              >
                <div className="w-12 h-12 bg-dlv-accent/10 text-dlv-accent rounded-xl flex items-center justify-center mb-5 group-hover:bg-dlv-accent group-hover:text-white transition-colors">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-500 leading-relaxed text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-dlv-surface">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-gray-500 max-w-xl mx-auto text-lg">
              Start free, scale with your own keys, or let us handle it
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {PRICING_TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`relative bg-white rounded-2xl p-8 border-2 transition-shadow ${
                  tier.highlight
                    ? "border-dlv-accent shadow-lg shadow-dlv-accent/10 scale-[1.02]"
                    : "border-dlv-border hover:shadow-md"
                }`}
              >
                {tier.highlight && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-dlv-accent text-white text-xs font-semibold rounded-full">
                    Most Popular
                  </div>
                )}
                <h3 className="text-xl font-bold text-gray-900 mb-1">{tier.name}</h3>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-3xl font-bold text-dlv-blue">{tier.price}</span>
                  {tier.period && (
                    <span className="text-sm text-gray-400">{tier.period}</span>
                  )}
                </div>
                <p className="text-gray-500 text-sm mb-6">{tier.description}</p>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm">
                      <svg
                        className="w-4 h-4 text-dlv-accent mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span className="text-gray-600">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className={`block w-full text-center py-3 rounded-lg font-semibold transition-colors ${
                    tier.highlight
                      ? "bg-dlv-accent text-white hover:bg-[#0065b8]"
                      : "bg-dlv-surface text-gray-700 hover:bg-gray-200 border border-dlv-border"
                  }`}
                >
                  {tier.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Providers Showcase */}
      <section className="py-20 bg-white border-y border-dlv-border">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Translation Providers
            </h2>
            <p className="text-gray-500 max-w-xl mx-auto text-lg">
              Choose the best engine for your needs, or use them all
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 max-w-4xl mx-auto">
            {PROVIDERS.map((provider) => (
              <div
                key={provider.name}
                className="bg-dlv-surface border border-dlv-border rounded-xl p-6 text-center hover:shadow-md transition-shadow"
              >
                <div className="w-12 h-12 bg-white border border-dlv-border rounded-xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-lg font-bold text-dlv-blue">
                    {provider.name.charAt(0)}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">{provider.name}</h3>
                <span className="inline-block px-2 py-0.5 bg-dlv-accent/10 text-dlv-accent text-xs font-medium rounded-full mb-2">
                  {provider.tag}
                </span>
                <p className="text-xs text-gray-500">{provider.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Developer Section */}
      <section className="py-20 bg-dlv-surface">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                Built API-First
              </h2>
              <p className="text-gray-500 text-lg mb-6 leading-relaxed">
                Integrate translation into your application with a single API call. Full
                REST API with JWT authentication, per-key rate limiting, and detailed
                usage analytics.
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  "RESTful JSON API",
                  "JWT + API key authentication",
                  "Comprehensive Swagger/OpenAPI docs",
                  "Webhook notifications for async jobs",
                  "SDKs coming soon",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3">
                    <svg
                      className="w-5 h-5 text-dlv-accent flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span className="text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-6 py-3 bg-dlv-blue text-white rounded-lg font-semibold hover:bg-[#1a3f5c] transition-colors"
              >
                Get Your API Key
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                  />
                </svg>
              </Link>
            </div>
            <div className="bg-dlv-blue rounded-2xl p-6 shadow-xl overflow-hidden">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="text-xs text-gray-400 ml-2 font-mono">
                  translate.sh
                </span>
              </div>
              <pre className="text-sm text-gray-300 font-mono leading-relaxed overflow-x-auto">
                <code>{API_CODE_SNIPPET}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative py-24 bg-gradient-to-b from-dlv-blue to-[#0a1f33] text-white overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-dlv-accent/5 blur-3xl" />
        </div>
        <div className="relative max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Start Translating in Seconds
          </h2>
          <p className="text-lg text-gray-300 mb-8 max-w-xl mx-auto">
            Create a free account and start translating immediately. No credit card
            required, no complicated setup.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="px-8 py-4 bg-dlv-accent text-white rounded-lg font-semibold text-lg hover:bg-[#0065b8] transition-all shadow-lg shadow-dlv-accent/25 hover:shadow-dlv-accent/40"
            >
              Create Free Account
            </Link>
            <Link
              to="/translate"
              className="px-8 py-4 bg-white/10 text-white rounded-lg font-semibold text-lg hover:bg-white/20 transition-all border border-white/20"
            >
              Try Without Signing Up
            </Link>
          </div>
          <p className="mt-6 text-sm text-gray-400">
            Free tier includes unlimited MarianMT translations. No strings attached.
          </p>
        </div>
      </section>
    </div>
  );
}
