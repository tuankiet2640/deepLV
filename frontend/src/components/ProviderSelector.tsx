interface Provider {
  id: string;
  name: string;
  description: string;
  pricing: string;
  isFree: boolean;
  hasStoredKey?: boolean;
}

const PROVIDERS: Provider[] = [
  {
    id: "marianmt",
    name: "MarianMT (Free)",
    description: "Open-source neural MT - fast and private, runs locally",
    pricing: "Free",
    isFree: true,
  },
  {
    id: "openai",
    name: "OpenAI GPT-4",
    description: "High-quality translation via GPT-4, best for nuanced text",
    pricing: "2 credits/page or use your own key",
    isFree: false,
  },
  {
    id: "huggingface",
    name: "HuggingFace Models",
    description: "Community translation models via HuggingFace Inference API",
    pricing: "1 credit/page or use your own key",
    isFree: false,
  },
  {
    id: "google",
    name: "Google Translate",
    description: "Google Cloud Translation API - broad language support",
    pricing: "1 credit/page or use your own key",
    isFree: false,
  },
];

interface ProviderSelectorProps {
  value: string;
  onChange: (provider: string) => void;
  storedKeyProviders?: string[];
  compact?: boolean;
  // Whether the MarianMT worker is reachable, per /health's
  // services.model_worker. null/undefined = unknown (not yet checked, or the
  // check failed) -- treated as available so a flaky health probe doesn't
  // itself block the free tier; only an explicit `false` disables it.
  marianmtAvailable?: boolean | null;
}

export function ProviderSelector({
  value,
  onChange,
  storedKeyProviders = [],
  compact = false,
  marianmtAvailable,
}: ProviderSelectorProps) {
  const isDisabled = (providerId: string) =>
    providerId === "marianmt" && marianmtAvailable === false;

  if (compact) {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-transparent text-sm font-medium text-gray-700 focus:outline-none cursor-pointer border border-dlv-border rounded-md px-2 py-1"
      >
        {PROVIDERS.map((p) => (
          <option key={p.id} value={p.id} disabled={isDisabled(p.id)}>
            {p.name}
            {storedKeyProviders.includes(p.id) ? " (key saved)" : ""}
            {isDisabled(p.id) ? " (unavailable)" : ""}
          </option>
        ))}
      </select>
    );
  }

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700">Translation Provider</label>
      <div className="grid gap-2">
        {PROVIDERS.map((provider) => {
          const hasKey = storedKeyProviders.includes(provider.id);
          const isSelected = value === provider.id;
          const disabled = isDisabled(provider.id);

          return (
            <button
              key={provider.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(provider.id)}
              className={`
                w-full text-left px-4 py-3 rounded-lg border-2 transition-all
                ${disabled ? "opacity-50 cursor-not-allowed bg-gray-50 border-dlv-border" : ""}
                ${!disabled && isSelected ? "border-dlv-accent bg-blue-50" : ""}
                ${!disabled && !isSelected ? "border-dlv-border hover:border-gray-300 bg-white" : ""}
              `}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{provider.name}</span>
                    {hasKey && (
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                        Key Saved
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {disabled
                      ? "Not running on this deployment right now -- pick another provider."
                      : provider.description}
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      disabled
                        ? "bg-gray-200 text-gray-500"
                        : provider.isFree
                          ? "bg-green-100 text-green-700"
                          : "bg-blue-100 text-blue-700"
                    }`}
                  >
                    {disabled ? "Unavailable" : provider.pricing}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
