import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { TARGET_LANGUAGES } from "../constants/languages";

const SAMPLE = "The future of translation is here — fast, accurate, and open.";
const DEBOUNCE_MS = 450;

type DemoError = "rate" | "unavailable" | null;

/**
 * A real, working mini-translator embedded in the hero. It calls the same
 * anonymous /translate tier the product uses (MarianMT, no account needed),
 * so visitors see the actual engine respond -- not a hardcoded mock. If the
 * worker is unreachable or the free hourly limit is hit, it degrades to a
 * friendly CTA instead of ever showing a broken box.
 */
export function HeroDemo() {
  const [text, setText] = useState(SAMPLE);
  const [target, setTarget] = useState("de");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<DemoError>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setOutput("");
      setError(null);
      setLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);

      try {
        const token = localStorage.getItem("dlv_token");
        const res = await fetch("/api/v1/translate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            text: trimmed.slice(0, 500),
            source_lang: "auto",
            target_lang: target,
            provider: "marianmt",
          }),
          signal: controller.signal,
        });

        if (res.status === 429) {
          setError("rate");
          return;
        }
        if (!res.ok) {
          setError("unavailable");
          return;
        }
        const data = await res.json();
        setOutput(data.translated_text);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError("unavailable");
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [text, target]);

  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 shadow-2xl text-left">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Source (editable) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              Your text
            </span>
            <span className="text-xs text-gray-500">Auto-detected</span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            maxLength={500}
            spellCheck={false}
            aria-label="Text to translate"
            className="w-full resize-none bg-transparent text-gray-100 text-base leading-relaxed placeholder-gray-500 focus:outline-none"
            placeholder="Type anything to translate live…"
          />
        </div>

        {/* Target (live output) */}
        <div className="border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-4">
          <div className="flex items-center justify-between mb-2">
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              aria-label="Target language"
              className="bg-transparent text-xs font-medium text-dlv-accent uppercase tracking-wider focus:outline-none cursor-pointer"
            >
              {TARGET_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="bg-dlv-blue text-gray-100">
                  {l.name}
                </option>
              ))}
            </select>
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  loading ? "bg-amber-400 animate-pulse" : error ? "bg-gray-500" : "bg-green-400"
                }`}
              />
              {loading ? "translating" : error ? "demo" : "live via MarianMT"}
            </span>
          </div>

          {error === "rate" ? (
            <p className="text-gray-300 text-base leading-relaxed">
              You've hit the free hourly limit for anonymous translations.{" "}
              <Link to="/register" className="text-dlv-accent font-medium hover:underline">
                Sign up
              </Link>{" "}
              for a higher limit and more providers.
            </p>
          ) : error === "unavailable" ? (
            <p className="text-gray-300 text-base leading-relaxed">
              The live demo engine isn't reachable right now.{" "}
              <Link to="/translate" className="text-dlv-accent font-medium hover:underline">
                Open the full translator
              </Link>{" "}
              to try it.
            </p>
          ) : loading && !output ? (
            <div className="space-y-2" aria-hidden>
              <div className="h-4 bg-white/10 rounded animate-pulse w-11/12" />
              <div className="h-4 bg-white/10 rounded animate-pulse w-4/5" />
              <div className="h-4 bg-white/10 rounded animate-pulse w-2/3" />
            </div>
          ) : (
            <p className="text-gray-100 text-base leading-relaxed min-h-[1.5rem]">{output}</p>
          )}
        </div>
      </div>
    </div>
  );
}
