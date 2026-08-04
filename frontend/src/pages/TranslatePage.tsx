import { useState } from "react";
import { TranslationPanel } from "../components/TranslationPanel";
import { ProviderSelector } from "../components/ProviderSelector";
import { useTranslation } from "../hooks/useTranslation";
import { useModelWorkerStatus } from "../hooks/useModelWorkerStatus";
import { CostEstimate } from "../components/CostEstimate";
import { useAuth } from "../contexts/AuthContext";
import { LANGUAGES, TARGET_LANGUAGES } from "../constants/languages";

export function TranslatePage() {
  const { user } = useAuth();
  const [sourceLang, setSourceLang] = useState(user?.default_source_lang ?? "auto");
  const [targetLang, setTargetLang] = useState(user?.default_target_lang ?? "de");
  const [sourceText, setSourceText] = useState("");
  const [provider, setProvider] = useState("marianmt");
  const marianmtAvailable = useModelWorkerStatus();

  const { translatedText, isLoading, error, latencyMs, cached, detectedLang } = useTranslation(
    sourceText,
    sourceLang,
    targetLang,
    provider,
  );

  // MarianMT has no direct model for most non-English pairs and pivots
  // through English (source -> en -> target) instead. That extra hop
  // compounds errors badly on formal/technical text -- worth a heads-up
  // rather than silently producing weak output.
  const isPivotPair =
    provider === "marianmt" && sourceLang !== "auto" && sourceLang !== "en" && targetLang !== "en";

  const handleSwap = () => {
    if (sourceLang === "auto") return;
    const prevSource = sourceLang;
    const prevTarget = targetLang;
    setSourceLang(prevTarget);
    setTargetLang(prevSource);
    setSourceText(translatedText);
  };

  return (
    <div className="max-w-6xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Translate</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Type or paste text to translate. Results appear as you type with 300ms debounce.
        </p>
      </div>

      <div className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border overflow-hidden">
        {/* Language selector bar */}
        <div className="flex items-center border-b border-dlv-border dark:border-dlv-dark-border px-4 py-3 bg-gray-50 dark:bg-dlv-dark-bg">
          <div className="flex-1">
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              className="bg-transparent text-sm font-medium text-gray-700 dark:text-gray-200 focus:outline-none cursor-pointer"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="dark:bg-dlv-dark-card dark:text-gray-200">
                  {l.name}
                </option>
              ))}
            </select>
            {detectedLang && sourceLang === "auto" && (
              <span className="ml-2 text-xs text-dlv-accent">
                Detected: {LANGUAGES.find((l) => l.code === detectedLang)?.name ?? detectedLang}
              </span>
            )}
          </div>
          <button
            onClick={handleSwap}
            disabled={sourceLang === "auto"}
            className="mx-4 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Swap languages"
          >
            <svg className="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </button>
          <div className="flex-1 text-right">
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="bg-transparent text-sm font-medium text-gray-700 dark:text-gray-200 focus:outline-none cursor-pointer"
            >
              {TARGET_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="dark:bg-dlv-dark-card dark:text-gray-200">
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Provider selector */}
        <div className="flex items-center border-b border-dlv-border dark:border-dlv-dark-border px-4 py-2 bg-gray-50/50 dark:bg-dlv-dark-bg/50">
          <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Provider:</span>
          <ProviderSelector
            value={provider}
            onChange={setProvider}
            compact
            marianmtAvailable={marianmtAvailable}
          />
        </div>

        {isPivotPair && (
          <div className="px-4 py-2 text-xs text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/20 border-b border-dlv-border dark:border-dlv-dark-border">
            MarianMT has no direct model for this pair, so it translates via English
            (two hops) -- quality can suffer on formal or technical text. Consider
            OpenAI or Google for higher accuracy.
          </div>
        )}

        {/* Translation panels */}
        <div className="flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x divide-dlv-border dark:divide-dlv-dark-border min-h-[350px]">
          <TranslationPanel
            value={sourceText}
            onChange={setSourceText}
            placeholder="Type to translate..."
            editable
            charCount={sourceText.length}
            maxChars={5000}
          />
          <TranslationPanel
            value={translatedText}
            isLoading={isLoading}
            placeholder="Translation"
            editable={false}
            footer={
              latencyMs !== null && !isLoading ? (
                <span className="text-xs text-gray-400">
                  {cached ? "cached" : `${latencyMs}ms`}
                </span>
              ) : null
            }
          />
        </div>

        {/* Cost estimate */}
        <div className="px-4 pb-3">
          <CostEstimate provider={provider} charCount={sourceText.length} />
        </div>

        {/* Error bar */}
        {error && (
          <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Info bar */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-400">
        <span>Models: MarianMT (Opus-MT) via CTranslate2 INT8</span>
        <span>Cache: Redis 24h TTL</span>
        <span>Rate limit: 100 req/min per API key</span>
        <span>Max input: 5,000 characters</span>
      </div>
    </div>
  );
}
