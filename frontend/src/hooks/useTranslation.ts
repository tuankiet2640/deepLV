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
        const res = await fetch(`${API_BASE}/translate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(localStorage.getItem("dlv_api_key")
              ? { "X-API-Key": localStorage.getItem("dlv_api_key")! }
              : localStorage.getItem("dlv_token")
                ? { "Authorization": `Bearer ${localStorage.getItem("dlv_token")}` }
                : {}),
          },
          body: JSON.stringify({
            text: trimmed,
            source_lang: sourceLang,
            target_lang: targetLang,
            provider: provider,
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
  }, [text, sourceLang, targetLang, provider]);

  return { translatedText, isLoading, error, latencyMs, cached, detectedLang };
}
