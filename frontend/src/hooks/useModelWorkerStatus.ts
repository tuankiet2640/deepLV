import { useEffect, useState } from "react";

/**
 * Whether the MarianMT model worker is reachable, per /health's
 * services.model_worker field. null while the check is in flight (or if it
 * fails) -- callers should treat that as "unknown, don't assume broken" so a
 * slow/failed health check doesn't itself block the free tier.
 */
export function useModelWorkerStatus(): boolean | null {
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch("/health")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        setAvailable(data.services?.model_worker === "connected");
      })
      .catch(() => {
        // Leave as null (unknown) -- don't punish users for a flaky check.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return available;
}
