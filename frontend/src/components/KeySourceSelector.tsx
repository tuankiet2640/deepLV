import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

/**
 * How a translation will be paid for. The parent turns this into request
 * fields: `providerKeyId` -> provider_key_id (use that own key, free);
 * `forceAdmin` -> key_source="admin" (spend credits even if a key exists).
 */
export interface KeySelection {
  providerKeyId: string | null;
  forceAdmin: boolean;
}

interface StoredKey {
  id: string;
  provider: string;
  label: string;
}

interface KeySourceSelectorProps {
  provider: string;
  charCount: number;
  onChange: (sel: KeySelection) => void;
}

const ADMIN = "__admin__"; // sentinel for the "admin credits" option

export function KeySourceSelector({ provider, charCount, onChange }: KeySourceSelectorProps) {
  const { token } = useAuth();
  const [keys, setKeys] = useState<StoredKey[]>([]);
  // selected = a key id, or ADMIN. Owned by this component; reset per provider.
  const [selected, setSelected] = useState<string>(ADMIN);
  const [rate, setRate] = useState<number | null>(null);

  // Live per-provider rate from /providers -- the same source the backend
  // charges from, so the estimate never drifts from an admin rate change.
  useEffect(() => {
    if (provider === "marianmt") {
      setRate(0);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/v1/providers");
        if (!res.ok) return;
        const data = await res.json();
        const info = (data.providers ?? []).find((p: { name: string }) => p.name === provider);
        if (!cancelled && info) setRate(info.credit_cost_per_1k_chars ?? null);
      } catch {
        /* leave rate null -> cost shown as unknown rather than wrong */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [provider]);

  // Fetch the user's saved keys for this provider and default the selection:
  // prefer the user's own key (free, matches prior behavior) when one exists,
  // else admin credits.
  useEffect(() => {
    if (!token || provider === "marianmt") {
      setKeys([]);
      setSelected(ADMIN);
      onChange({ providerKeyId: null, forceAdmin: false });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/v1/providers/keys", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = res.ok ? await res.json() : { keys: [] };
        const all: StoredKey[] = data.keys ?? data ?? [];
        const forProvider = all.filter((k) => k.provider === provider);
        if (cancelled) return;
        setKeys(forProvider);
        const first = forProvider[0];
        if (first) {
          setSelected(first.id);
          onChange({ providerKeyId: first.id, forceAdmin: false });
        } else {
          setSelected(ADMIN);
          onChange({ providerKeyId: null, forceAdmin: false });
        }
      } catch {
        if (cancelled) return;
        setKeys([]);
        setSelected(ADMIN);
        onChange({ providerKeyId: null, forceAdmin: false });
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, provider]);

  const handleSelect = (value: string) => {
    setSelected(value);
    if (value === ADMIN) {
      // forceAdmin only matters when the user actually has a key to skip;
      // with no keys, auto already lands on admin.
      onChange({ providerKeyId: null, forceAdmin: keys.length > 0 });
    } else {
      onChange({ providerKeyId: value, forceAdmin: false });
    }
  };

  if (provider === "marianmt") {
    return (
      <div className="mt-2 flex items-center gap-1.5">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
          Free
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">MarianMT is always free</span>
      </div>
    );
  }

  const usingOwnKey = selected !== ADMIN;
  const estCost = rate !== null && charCount > 0 ? (charCount / 1000) * rate : 0;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <label className="text-gray-500 dark:text-gray-400">Pay with:</label>
      <select
        value={selected}
        onChange={(e) => handleSelect(e.target.value)}
        className="border border-dlv-border dark:border-dlv-dark-border rounded-md px-2 py-1 bg-white dark:bg-dlv-dark-card text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-dlv-accent/50"
      >
        {keys.map((k) => (
          <option key={k.id} value={k.id}>
            My key: {k.label} (free)
          </option>
        ))}
        <option value={ADMIN}>Admin credits</option>
      </select>

      {usingOwnKey ? (
        <span className="inline-flex items-center px-2 py-0.5 rounded font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
          Your key · free
        </span>
      ) : (
        <span className="inline-flex items-center px-2 py-0.5 rounded font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          Admin credits
          {rate !== null && (
            <span className="ml-1 font-normal">
              · {charCount > 0 ? `~${estCost.toFixed(2)} credits` : `${rate}/1k chars`}
            </span>
          )}
        </span>
      )}

      {!usingOwnKey && keys.length === 0 && (
        <span className="text-gray-400 dark:text-gray-500">
          (add your own key in Settings to translate for free)
        </span>
      )}
    </div>
  );
}
