import { useEffect, useRef, useState } from "react";

interface TranslationResult {
  translatedText: string;
  isLoading: boolean;
  error: string | null;
  latencyMs: number | null;
  cached: boolean;
  detectedLang: string | null;
}

const DEBOUNCE_MS = 300;
const API_BASE = "/api/v1";

export function useTranslation(
  text: string,
  sourceLang: string,
  targetLang: string,
  provider: string = "marianmt",
  providerKeyId: string | null = null,
  forceAdmin: boolean = false,
): TranslationResult {
  const [translatedText, setTranslatedText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [cached, setCached] = useState(false);
  const [detectedLang, setDetectedLang] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setTranslatedText("");
      setError(null);
      setLatencyMs(null);
      setCached(false);
      setDetectedLang(null);
      return;
    }

    if (trimmed.length > 5000) {
      setError("Text exceeds 5,000 character limit");
      return;
    }

    const timer = setTimeout(async () => {
      // Cancel previous in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      try {
        const token = localStorage.getItem("dlv_token");
        const apiKey = localStorage.getItem("dlv_api_key");
        const res = await fetch(`${API_BASE}/translate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // Send both when present -- the backend tries X-API-Key first
            // and falls back to the JWT (see get_user_from_api_key_or_jwt).
            // Picking only one here means a stale/invalid stored API key
            // silently shadows a perfectly valid session token.
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(apiKey ? { "X-API-Key": apiKey } : {}),
          },
          body: JSON.stringify({
            text: trimmed,
            source_lang: sourceLang,
            target_lang: targetLang,
            provider: provider,
            // A chosen own key wins; otherwise forceAdmin opts into credits.
            ...(providerKeyId ? { provider_key_id: providerKeyId } : {}),
            ...(forceAdmin ? { key_source: "admin" } : {}),
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(body.detail ?? `HTTP ${res.status}`);
        }

        const data = await res.json();
        setTranslatedText(data.translated_text);
        setLatencyMs(data.latency_ms);
        setCached(data.cached);
        setDetectedLang(data.detected_lang ? data.source_lang : null);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Translation failed");
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
    };
  }, [text, sourceLang, targetLang, provider, providerKeyId, forceAdmin]);

  return { translatedText, isLoading, error, latencyMs, cached, detectedLang };
}
