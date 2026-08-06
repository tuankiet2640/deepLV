import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="text-xl font-bold text-gray-900 mb-4">{title}</h2>
      {children}
    </section>
  );
}

function Decision({
  title,
  chosen,
  over,
  why,
  tradeoff,
}: {
  title: string;
  chosen: string;
  over: string;
  why: string;
  tradeoff: string;
}) {
  return (
    <div className="bg-white border border-dlv-border rounded-lg p-5 mb-4">
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm mb-3">
        <div>
          <span className="text-xs font-medium text-green-600 uppercase">Chosen</span>
          <p className="text-gray-700">{chosen}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-400 uppercase">Over</span>
          <p className="text-gray-500">{over}</p>
        </div>
      </div>
      <p className="text-sm text-gray-600 mb-2"><strong>Why:</strong> {why}</p>
      <p className="text-sm text-gray-400"><strong>Trade-off:</strong> {tradeoff}</p>
    </div>
  );
}

export function ArchitecturePage() {
  useDocumentTitle("Architecture");
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Architecture</h1>
      <p className="text-gray-500 mb-10">
        System design, request flow, scaling strategy, and documented trade-offs.
      </p>

      {/* System Diagram */}
      <Section title="System Diagram">
        <div className="bg-dlv-blue rounded-xl p-6 overflow-x-auto">
          <pre className="text-green-400 text-sm font-mono leading-relaxed whitespace-pre">
{`                      +------------------+
                      |    React + TS    |
                      |    (Vite, TW)    |
                      +--------+---------+
                               |
                          HTTP / REST
                               |
                  +------------v------------+
                  |    FastAPI Gateway       |
                  |    :8000                 |
                  |                          |
                  |  - JWT / API key auth    |
                  |  - Rate limit (Redis)    |
                  |  - Language detection    |
                  |  - Cache check (Redis)   |
                  |  - Usage logging (PG)    |
                  +---+--------+--------+---+
                      |        |        |
               +------+   +---+---+  +-+--------+
               |           |       |  |          |
          +----v---+  +----v--+  +-v----------+  |
          | Redis  |  | Pg 16 |  | Model      |  |
          | 7      |  |       |  | Worker     |  |
          |        |  | users |  | :8001      |  |
          | cache  |  | keys  |  |            |  |
          | rates  |  | logs  |  | CTranslate2|  |
          +--------+  +-------+  | INT8 quant |  |
                                 |            |  |
                                 | LRU cache  |  |
                                 | max 6 pairs|  |
                                 +-----+------+  |
                                       |         |
                                +------v------+  |
                                | MarianMT    |  |
                                | (Opus-MT)   |  |
                                | HuggingFace |  |
                                +-------------+  |
                                                  |
                             Prometheus <---------+
                             /metrics`}
          </pre>
        </div>
      </Section>

      {/* Request Flow */}
      <Section title="Request Flow">
        <div className="bg-white border border-dlv-border rounded-lg overflow-hidden">
          <ol className="divide-y divide-gray-100">
            {[
              { step: "1", label: "Client", desc: "POST /api/v1/translate with X-API-Key header" },
              { step: "2", label: "Auth", desc: "Validate API key (SHA-256 hash lookup in PostgreSQL)" },
              { step: "3", label: "Rate Limit", desc: "Redis sorted set sliding window check (ZRANGEBYSCORE + ZCARD)" },
              { step: "4", label: "Language Detect", desc: "If source_lang='auto': fasttext detection in <10ms" },
              { step: "5", label: "Cache Check", desc: "Redis GET on SHA-256(source + target + normalized_text)" },
              { step: "HIT", label: "Cache Hit", desc: "Return cached result. Latency: <5ms total." },
              { step: "6", label: "Model Worker", desc: "Internal HTTP POST to worker:8001/translate" },
              { step: "7", label: "Inference", desc: "SentencePiece tokenize -> CTranslate2 beam search (beam=4) -> decode" },
              { step: "8", label: "Cache Write", desc: "Redis SET with 24h TTL" },
              { step: "9", label: "Usage Log", desc: "Async INSERT into PostgreSQL (non-blocking)" },
              { step: "10", label: "Response", desc: "Return translated_text + metadata to client" },
            ].map((item) => (
              <li key={item.step} className="flex items-start px-5 py-3 gap-4">
                <span className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                  item.step === "HIT" ? "bg-green-100 text-green-700" : "bg-blue-50 text-dlv-accent"
                }`}>
                  {item.step}
                </span>
                <div>
                  <span className="font-medium text-gray-900 text-sm">{item.label}</span>
                  <p className="text-sm text-gray-500">{item.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      {/* Latency Budget */}
      <Section title="Latency Budget">
        <div className="bg-white border border-dlv-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Operation</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Target</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Acceptable</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <tr><td className="px-4 py-2.5">Cached translation</td><td className="px-4 py-2.5 text-green-600 font-medium">&lt;5ms</td><td className="px-4 py-2.5">&lt;20ms</td></tr>
              <tr><td className="px-4 py-2.5">Single sentence inference</td><td className="px-4 py-2.5 text-green-600 font-medium">&lt;500ms</td><td className="px-4 py-2.5">&lt;1s</td></tr>
              <tr><td className="px-4 py-2.5">Language detection</td><td className="px-4 py-2.5 text-green-600 font-medium">&lt;10ms</td><td className="px-4 py-2.5">&lt;50ms</td></tr>
              <tr><td className="px-4 py-2.5">Cold model load (first request)</td><td className="px-4 py-2.5 text-yellow-600 font-medium">&lt;8s</td><td className="px-4 py-2.5">&lt;15s</td></tr>
              <tr><td className="px-4 py-2.5">Auth + rate limit</td><td className="px-4 py-2.5 text-green-600 font-medium">&lt;2ms</td><td className="px-4 py-2.5">&lt;5ms</td></tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* Scaling */}
      <Section title="Scaling Strategy">
        <div className="bg-white border border-dlv-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Component</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Approach</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <tr><td className="px-4 py-2.5 font-medium">API Gateway</td><td className="px-4 py-2.5">Horizontal &mdash; stateless, add replicas behind LB</td></tr>
              <tr><td className="px-4 py-2.5 font-medium">Model Worker</td><td className="px-4 py-2.5">Horizontal &mdash; each worker has its own model LRU cache</td></tr>
              <tr><td className="px-4 py-2.5 font-medium">Redis</td><td className="px-4 py-2.5">Vertical first, then Redis Cluster for &gt;64GB</td></tr>
              <tr><td className="px-4 py-2.5 font-medium">PostgreSQL</td><td className="px-4 py-2.5">Vertical first, read replicas for analytics</td></tr>
              <tr><td className="px-4 py-2.5 font-medium">Frontend</td><td className="px-4 py-2.5">CDN-served static assets, infinite scale</td></tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* Design Decisions */}
      <Section title="Key Design Decisions">
        <Decision
          title="Separate Model Worker"
          chosen="Dedicated FastAPI service on port 8001"
          over="In-process model loading in the API server"
          why="Model OOM or crash doesn't take down the API. Can scale model workers independently. Can update models without API downtime."
          tradeoff="Adds ~1ms network latency per request."
        />
        <Decision
          title="CTranslate2 over PyTorch"
          chosen="CTranslate2 INT8 quantized inference"
          over="Raw PyTorch, ONNX Runtime, TorchServe"
          why="2-5x faster on CPU, lower memory footprint. Simple API (translate_batch). Production-proven by OpenNMT."
          tradeoff="Requires a model conversion step at build time."
        />
        <Decision
          title="Synchronous Model Call"
          chosen="Direct HTTP to model worker"
          over="Message queue (Kafka, RabbitMQ)"
          why="Translation is latency-sensitive. A queue adds 10-50ms and complexity for no benefit at this scale."
          tradeoff="No built-in retry/backpressure. At 10K+ QPS, would add a queue with WebSocket push."
        />
        <Decision
          title="Redis over In-Process Cache"
          chosen="Redis with 24h TTL"
          over="Python lru_cache, Memcached"
          why="Shared across API replicas, survives restarts, built-in TTL eviction, atomic rate limit operations."
          tradeoff="Adds a dependency and ~0.5ms network hop."
        />
        <Decision
          title="PostgreSQL over SQLite"
          chosen="PostgreSQL 16 with asyncpg"
          over="SQLite (simpler), MongoDB (flexible)"
          why="Production-standard. Alembic migrations demonstrate schema evolution. Using SQLite in a 'production-grade' system undermines the premise."
          tradeoff="Heavier dependency for a portfolio project."
        />
        <Decision
          title="Pretrained Models"
          chosen="Helsinki-NLP/Opus-MT via HuggingFace"
          over="Training from scratch, external API (Google/DeepL)"
          why="Open-source, no billing, runs offline. The architecture is the showcase, not BLEU scores."
          tradeoff="Quality below commercial systems. Same architecture works with fine-tuned models."
        />
      </Section>

      {/* Honest Simplifications */}
      <Section title="Honest Simplifications">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-5">
          <p className="text-sm text-gray-700 mb-3">
            These are deliberate scope cuts for a portfolio project, not oversights:
          </p>
          <ul className="space-y-2 text-sm text-gray-600">
            <li><strong>CPU-only inference</strong> &mdash; No GPU requirement means docker compose up works on any machine.</li>
            <li><strong>English pivot for non-direct pairs</strong> &mdash; de-&gt;fr goes through en. Doubles latency but covers all N&times;N pairs with 2N models.</li>
            <li><strong>No model training</strong> &mdash; Uses pretrained MarianMT. Translation quality is "good" not "DeepL-quality."</li>
            <li><strong>No WebSocket streaming</strong> &mdash; Translations return as complete responses. Acceptable at &lt;1s latency.</li>
            <li><strong>Kubernetes is conceptual</strong> &mdash; System runs via Docker Compose. K8s manifests would be straightforward to add.</li>
          </ul>
        </div>
      </Section>

      <div className="text-center">
        <Link to="/status" className="text-dlv-accent text-sm font-medium hover:underline">
          View live system status &rarr;
        </Link>
      </div>
    </div>
  );
}
