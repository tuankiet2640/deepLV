function Endpoint({
  method,
  path,
  auth,
  desc,
  children,
}: {
  method: "GET" | "POST" | "DELETE";
  path: string;
  auth: string;
  desc: string;
  children: React.ReactNode;
}) {
  const methodColors = {
    GET: "bg-green-100 text-green-800",
    POST: "bg-blue-100 text-blue-800",
    DELETE: "bg-red-100 text-red-800",
  };

  return (
    <div className="border border-dlv-border rounded-lg overflow-hidden mb-6" id={`${method.toLowerCase()}-${path.replace(/\//g, "-").replace(/[{}:]/g, "")}`}>
      <div className="bg-gray-50 px-5 py-4 border-b border-dlv-border">
        <div className="flex items-center gap-3 mb-1">
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${methodColors[method]}`}>
            {method}
          </span>
          <code className="text-sm font-mono font-medium text-gray-900">{path}</code>
          <span className="text-xs text-gray-400 ml-auto">{auth}</span>
        </div>
        <p className="text-sm text-gray-500 mt-1">{desc}</p>
      </div>
      <div className="px-5 py-4 text-sm space-y-4">{children}</div>
    </div>
  );
}

function ParamTable({ params }: { params: { name: string; type: string; required: boolean; desc: string }[] }) {
  return (
    <table className="w-full text-sm border border-gray-100 rounded">
      <thead className="bg-gray-50">
        <tr>
          <th className="text-left px-3 py-2 font-medium text-gray-600">Field</th>
          <th className="text-left px-3 py-2 font-medium text-gray-600">Type</th>
          <th className="text-left px-3 py-2 font-medium text-gray-600">Required</th>
          <th className="text-left px-3 py-2 font-medium text-gray-600">Description</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {params.map((p) => (
          <tr key={p.name}>
            <td className="px-3 py-2 font-mono text-xs">{p.name}</td>
            <td className="px-3 py-2 text-gray-500">{p.type}</td>
            <td className="px-3 py-2">{p.required ? <span className="text-red-500">yes</span> : "no"}</td>
            <td className="px-3 py-2 text-gray-600">{p.desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ResponseExample({ status, body }: { status: number; body: string }) {
  const statusColor = status < 300 ? "text-green-600" : status < 400 ? "text-yellow-600" : "text-red-600";
  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs text-gray-400">Response</span>
        <span className={`text-xs font-medium ${statusColor}`}>{status}</span>
      </div>
      <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
        <code>{body}</code>
      </pre>
    </div>
  );
}

export function ApiReferencePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">API Reference</h1>
      <p className="text-gray-500 mb-4">
        Base URL: <code className="bg-gray-100 px-2 py-0.5 rounded text-sm">http://localhost:8000/api/v1</code>
      </p>
      <p className="text-gray-500 mb-10 text-sm">
        For interactive exploration, use the <a href="/docs" className="text-dlv-accent underline">Swagger UI</a>.
      </p>

      {/* Table of Contents */}
      <nav className="bg-white border border-dlv-border rounded-lg p-5 mb-10">
        <h2 className="font-semibold text-gray-900 mb-3 text-sm">Endpoints</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-1">Translation</h3>
            <a href="#post--api-v1-translate" className="block text-dlv-accent hover:underline">POST /api/v1/translate</a>
            <a href="#get--api-v1-languages" className="block text-dlv-accent hover:underline">GET /api/v1/languages</a>
          </div>
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-1">Authentication</h3>
            <a href="#post--api-v1-auth-register" className="block text-dlv-accent hover:underline">POST /api/v1/auth/register</a>
            <a href="#post--api-v1-auth-login" className="block text-dlv-accent hover:underline">POST /api/v1/auth/login</a>
          </div>
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-1">API Keys</h3>
            <a href="#post--api-v1-keys" className="block text-dlv-accent hover:underline">POST /api/v1/keys</a>
            <a href="#get--api-v1-keys" className="block text-dlv-accent hover:underline">GET /api/v1/keys</a>
            <a href="#delete--api-v1-keysid" className="block text-dlv-accent hover:underline">DELETE /api/v1/keys/:id</a>
          </div>
          <div>
            <h3 className="text-xs font-medium text-gray-400 mb-1">System</h3>
            <a href="#get--api-v1-usage" className="block text-dlv-accent hover:underline">GET /api/v1/usage</a>
            <a href="#get--health" className="block text-dlv-accent hover:underline">GET /health</a>
          </div>
        </div>
      </nav>

      {/* Translation */}
      <h2 className="text-xl font-bold text-gray-900 mb-4 mt-8">Translation</h2>

      <Endpoint method="POST" path="/api/v1/translate" auth="X-API-Key / Bearer JWT / none" desc="Translate text between supported language pairs.">
        <p className="text-xs text-gray-500">
          <code className="bg-gray-100 px-1 py-0.5 rounded">provider: "marianmt"</code> works with no
          credential at all -- anonymous requests are limited to 20/hour per IP. Every other{" "}
          <code className="bg-gray-100 px-1 py-0.5 rounded">provider</code> value requires
          <code className="bg-gray-100 px-1 py-0.5 rounded ml-1">X-API-Key</code> or a Bearer JWT.
        </p>
        <ParamTable
          params={[
            { name: "text", type: "string", required: true, desc: "Input text (1-5000 chars)" },
            { name: "source_lang", type: "string", required: true, desc: 'ISO 639-1 code or "auto"' },
            { name: "target_lang", type: "string", required: true, desc: "ISO 639-1 code" },
            { name: "provider", type: "string", required: false, desc: '"marianmt" (default), "openai", "huggingface", or "google"' },
          ]}
        />
        <ResponseExample
          status={200}
          body={`{
  "translated_text": "Hallo, wie geht es Ihnen?",
  "source_lang": "en",
  "target_lang": "de",
  "detected_lang": true,
  "cached": false,
  "latency_ms": 342.1
}`}
        />
        <div>
          <p className="text-xs text-gray-400">
            Errors: 400 (bad input), 401 (invalid key, or a non-MarianMT provider with no
            credential), 402 (insufficient credits), 413 (text too long), 429 (rate limited --
            20/hour/IP anonymous, 100/min per account), 503 (worker down)
          </p>
        </div>
      </Endpoint>

      <Endpoint method="GET" path="/api/v1/languages" auth="none" desc="List all supported languages.">
        <ResponseExample
          status={200}
          body={`{
  "languages": [
    { "code": "en", "name": "English" },
    { "code": "de", "name": "German" },
    { "code": "fr", "name": "French" },
    ...
  ]
}`}
        />
      </Endpoint>

      {/* Auth */}
      <h2 className="text-xl font-bold text-gray-900 mb-4 mt-12">Authentication</h2>

      <Endpoint method="POST" path="/api/v1/auth/register" auth="none" desc="Create a new user account.">
        <ParamTable
          params={[
            { name: "email", type: "string", required: true, desc: "Valid email address" },
            { name: "password", type: "string", required: true, desc: "Min 8 characters" },
          ]}
        />
        <ResponseExample
          status={201}
          body={`{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-04-22T10:00:00+00:00"
}`}
        />
      </Endpoint>

      <Endpoint method="POST" path="/api/v1/auth/login" auth="none" desc="Get a JWT access token.">
        <ParamTable
          params={[
            { name: "email", type: "string", required: true, desc: "Registered email" },
            { name: "password", type: "string", required: true, desc: "Account password" },
          ]}
        />
        <ResponseExample
          status={200}
          body={`{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}`}
        />
      </Endpoint>

      {/* API Keys */}
      <h2 className="text-xl font-bold text-gray-900 mb-4 mt-12">API Keys</h2>

      <Endpoint method="POST" path="/api/v1/keys" auth="Bearer JWT" desc="Create a new API key. Max 5 per account. Full key is returned only once.">
        <ParamTable
          params={[
            { name: "name", type: "string", required: true, desc: "Descriptive name for the key" },
          ]}
        />
        <ResponseExample
          status={201}
          body={`{
  "id": "key-uuid",
  "name": "my-app",
  "key": "dlv_live_a1b2c3d4e5f6...",
  "key_prefix": "dlv_live_a1b2...",
  "created_at": "2026-04-22T10:01:00+00:00"
}`}
        />
      </Endpoint>

      <Endpoint method="GET" path="/api/v1/keys" auth="Bearer JWT" desc="List all API keys for the current user. Key values are masked.">
        <ResponseExample
          status={200}
          body={`{
  "keys": [
    {
      "id": "key-uuid",
      "name": "my-app",
      "key_prefix": "dlv_live_a1b2...",
      "created_at": "2026-04-22T10:01:00+00:00",
      "last_used_at": "2026-04-22T12:30:00+00:00"
    }
  ]
}`}
        />
      </Endpoint>

      <Endpoint method="DELETE" path="/api/v1/keys/:id" auth="Bearer JWT" desc="Revoke an API key. This is irreversible.">
        <ResponseExample status={204} body="(no content)" />
      </Endpoint>

      {/* Usage & System */}
      <h2 className="text-xl font-bold text-gray-900 mb-4 mt-12">Usage & System</h2>

      <Endpoint method="GET" path="/api/v1/usage" auth="Bearer JWT" desc="Get translation usage statistics for the current user.">
        <ParamTable
          params={[
            { name: "key_id", type: "string", required: false, desc: "Filter to specific API key" },
            { name: "days", type: "integer", required: false, desc: "Lookback period, 1-90 (default: 30)" },
          ]}
        />
        <ResponseExample
          status={200}
          body={`{
  "total_requests": 1523,
  "total_characters": 284100,
  "cache_hit_rate": 0.34,
  "by_language_pair": {
    "en->de": { "requests": 800, "characters": 150000 }
  },
  "daily": [
    { "date": "2026-04-22", "requests": 45, "characters": 8200 }
  ]
}`}
        />
      </Endpoint>

      <Endpoint method="GET" path="/health" auth="none" desc="System health check. Probes Redis, PostgreSQL, and the model worker.">
        <ResponseExample
          status={200}
          body={`{
  "status": "healthy",
  "services": {
    "redis": "connected",
    "postgres": "connected",
    "model_worker": "connected"
  },
  "version": "1.0.0",
  "uptime_seconds": 3600.0
}`}
        />
      </Endpoint>

      {/* Auth info */}
      <div className="mt-12 bg-gray-50 border border-dlv-border rounded-lg p-5">
        <h2 className="font-semibold text-gray-900 mb-3">Authentication Methods</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="pb-2">Method</th>
              <th className="pb-2">Header</th>
              <th className="pb-2">Used for</th>
            </tr>
          </thead>
          <tbody className="text-gray-700">
            <tr>
              <td className="py-1.5 font-medium">JWT Bearer</td>
              <td className="py-1.5"><code className="bg-white px-1.5 py-0.5 rounded text-xs">Authorization: Bearer &lt;token&gt;</code></td>
              <td className="py-1.5">Account management (keys, usage)</td>
            </tr>
            <tr>
              <td className="py-1.5 font-medium">API Key</td>
              <td className="py-1.5"><code className="bg-white px-1.5 py-0.5 rounded text-xs">X-API-Key: dlv_live_...</code></td>
              <td className="py-1.5">Translation requests</td>
            </tr>
            <tr>
              <td className="py-1.5 font-medium">None</td>
              <td className="py-1.5 text-gray-400">&mdash;</td>
              <td className="py-1.5">
                POST /translate with <code className="bg-white px-1.5 py-0.5 rounded text-xs">provider: "marianmt"</code> only, 20 req/hour per IP
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
