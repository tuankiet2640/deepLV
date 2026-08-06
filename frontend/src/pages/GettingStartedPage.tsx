import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div className="rounded-lg overflow-hidden border border-gray-200">
      <div className="bg-gray-100 px-4 py-2 text-xs font-medium text-gray-600 border-b border-gray-200">
        {title}
      </div>
      <pre className="bg-gray-900 text-gray-100 p-4 text-sm overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function GettingStartedPage() {
  useDocumentTitle("Getting Started");
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Getting Started</h1>
      <p className="text-gray-500 mb-4">
        Go from zero to translating text in under 5 minutes.
      </p>
      <p className="text-sm text-gray-500 bg-gray-50 border border-dlv-border rounded-lg px-4 py-3 mb-10">
        Just want to try it? <Link to="/translate" className="text-dlv-accent font-medium hover:underline">Translate</Link>{" "}
        works with MarianMT and no account at all &mdash; 20 requests/hour per IP. The steps below
        are for the API, other providers, and higher limits.
      </p>

      {/* Step 1 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-dlv-accent text-white rounded-full flex items-center justify-center text-sm font-bold">
            1
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Create an account</h2>
        </div>
        <p className="text-gray-600 mb-4 ml-11">
          Register with your email to get access to the API.
        </p>
        <div className="ml-11">
          <CodeBlock
            title="Register"
            code={`curl -X POST http://localhost:8000/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "you@example.com",
    "password": "your-secure-password"
  }'`}
          />
        </div>
        <div className="ml-11 mt-3">
          <CodeBlock
            title="Response"
            code={`{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "you@example.com",
  "created_at": "2026-04-22T10:00:00+00:00"
}`}
          />
        </div>
      </section>

      {/* Step 2 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-dlv-accent text-white rounded-full flex items-center justify-center text-sm font-bold">
            2
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Get your access token</h2>
        </div>
        <p className="text-gray-600 mb-4 ml-11">
          Log in to receive a JWT token (valid for 24 hours).
        </p>
        <div className="ml-11">
          <CodeBlock
            title="Login"
            code={`curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "you@example.com",
    "password": "your-secure-password"
  }'`}
          />
        </div>
        <div className="ml-11 mt-3">
          <CodeBlock
            title="Response"
            code={`{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}`}
          />
        </div>
      </section>

      {/* Step 3 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-dlv-accent text-white rounded-full flex items-center justify-center text-sm font-bold">
            3
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Create an API key</h2>
        </div>
        <p className="text-gray-600 mb-4 ml-11">
          API keys are used for translation requests. You can create up to 5 per account.
          The full key is only shown once at creation time.
        </p>
        <div className="ml-11">
          <CodeBlock
            title="Create API Key"
            code={`curl -X POST http://localhost:8000/api/v1/keys \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \\
  -H "Content-Type: application/json" \\
  -d '{ "name": "my-app" }'`}
          />
        </div>
        <div className="ml-11 mt-3">
          <CodeBlock
            title="Response (save the key!)"
            code={`{
  "id": "key-uuid",
  "name": "my-app",
  "key": "dlv_live_a1b2c3d4e5f6...",
  "key_prefix": "dlv_live_a1b2c3d4...",
  "created_at": "2026-04-22T10:01:00+00:00"
}`}
          />
        </div>
      </section>

      {/* Step 4 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-dlv-accent text-white rounded-full flex items-center justify-center text-sm font-bold">
            4
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Translate text</h2>
        </div>
        <p className="text-gray-600 mb-4 ml-11">
          Pass your API key in the <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm">X-API-Key</code> header.
          Set <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm">source_lang</code> to{" "}
          <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm">"auto"</code> for automatic language detection.
        </p>
        <div className="ml-11">
          <CodeBlock
            title="Translate"
            code={`curl -X POST http://localhost:8000/api/v1/translate \\
  -H "X-API-Key: dlv_live_a1b2c3d4e5f6..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Hello, how are you today?",
    "source_lang": "auto",
    "target_lang": "de"
  }'`}
          />
        </div>
        <div className="ml-11 mt-3">
          <CodeBlock
            title="Response"
            code={`{
  "translated_text": "Hallo, wie geht es Ihnen heute?",
  "source_lang": "en",
  "target_lang": "de",
  "detected_lang": true,
  "cached": false,
  "latency_ms": 342.1
}`}
          />
        </div>
      </section>

      {/* Rate limits */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Rate Limits</h2>
        <div className="bg-white border border-dlv-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Limit</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <tr><td className="px-4 py-3">Requests per minute</td><td className="px-4 py-3">100 per API key</td></tr>
              <tr><td className="px-4 py-3">Anonymous requests (MarianMT, no account)</td><td className="px-4 py-3">20 per hour, per IP</td></tr>
              <tr><td className="px-4 py-3">Max text length</td><td className="px-4 py-3">5,000 characters</td></tr>
              <tr><td className="px-4 py-3">API keys per account</td><td className="px-4 py-3">5</td></tr>
              <tr><td className="px-4 py-3">Token expiry</td><td className="px-4 py-3">24 hours</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Next steps */}
      <section className="bg-blue-50 border border-blue-200 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Next steps</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>
            <Link to="/api-reference" className="text-dlv-accent hover:underline font-medium">API Reference</Link>{" "}
            &mdash; full endpoint documentation with request/response schemas
          </li>
          <li>
            <Link to="/architecture" className="text-dlv-accent hover:underline font-medium">Architecture</Link>{" "}
            &mdash; system design, data flow, and trade-off decisions
          </li>
          <li>
            <a href="/docs" className="text-dlv-accent hover:underline font-medium">Swagger UI</a>{" "}
            &mdash; interactive API explorer (try requests from your browser)
          </li>
          <li>
            <Link to="/status" className="text-dlv-accent hover:underline font-medium">System Status</Link>{" "}
            &mdash; live health checks on all services
          </li>
        </ul>
      </section>
    </div>
  );
}
