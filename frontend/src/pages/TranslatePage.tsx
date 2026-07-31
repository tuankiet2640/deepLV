import { useState } from "react";
import { TranslationPanel } from "../components/TranslationPanel";
import { ProviderSelector } from "../components/ProviderSelector";
import { useTranslation } from "../hooks/useTranslation";

const LANGUAGES = [
  { code: "auto", name: "Detect language" },
  { code: "en", name: "English" },
  { code: "de", name: "German" },
  { code: "fr", name: "French" },
  { code: "es", name: "Spanish" },
  { code: "zh", name: "Chinese" },
  { code: "ja", name: "Japanese" },
  { code: "vi", name: "Vietnamese" },
  { code: "ko", name: "Korean" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
];

const TARGET_LANGUAGES = LANGUAGES.filter((l) => l.code !== "auto");

export function TranslatePage() {
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("de");
  const [sourceText, setSourceText] = useState("");
  const [provider, setProvider] = useState("marianmt");

  const { translatedText, isLoading, error, latencyMs, cached, detectedLang } = useTranslation(
    sourceText,
    sourceLang,
    targetLang,
  );

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
        <h1 className="text-2xl font-bold text-gray-900">Translate</h1>
        <p className="text-sm text-gray-500 mt-1">
          Type or paste text to translate. Results appear as you type with 300ms debounce.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-dlv-border overflow-hidden">
        {/* Language selector bar */}
        <div className="flex items-center border-b border-dlv-border px-4 py-3 bg-gray-50">
          <div className="flex-1">
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              className="bg-transparent text-sm font-medium text-gray-700 focus:outline-none cursor-pointer"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
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
            className="mx-4 p-2 rounded-full hover:bg-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Swap languages"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </button>
          <div className="flex-1 text-right">
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="bg-transparent text-sm font-medium text-gray-700 focus:outline-none cursor-pointer"
            >
              {TARGET_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Provider selector */}
        <div className="flex items-center border-b border-dlv-border px-4 py-2 bg-gray-50/50">
          <span className="text-xs text-gray-500 mr-2">Provider:</span>
          <ProviderSelector value={provider} onChange={setProvider} compact />
        </div>

        {/* Translation panels */}
        <div className="flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x divide-dlv-border min-h-[350px]">
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

        {/* Error bar */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-sm text-red-700">
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
