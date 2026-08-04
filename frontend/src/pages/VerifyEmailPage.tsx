import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

const API_BASE = "/api/v1";
const RESEND_COOLDOWN_SECONDS = 30;

export function VerifyEmailPage() {
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const email = searchParams.get("email") ?? "";

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [isResending, setIsResending] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Verification failed" }));
        throw new Error(typeof body.detail === "string" ? body.detail : "Verification failed");
      }

      const data = await res.json();
      await loginWithToken(data.access_token);
      showToast("Email verified!", "success");
      navigate("/translate", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || !email) return;
    setIsResending(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/auth/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Could not resend code" }));
        throw new Error(typeof body.detail === "string" ? body.detail : "Could not resend code");
      }

      showToast("Verification code sent", "success");
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
      const timer = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend code");
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Verify your email</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            {email ? (
              <>
                We sent a 6-digit code to <span className="font-medium">{email}</span>.
              </>
            ) : (
              "Enter the 6-digit code we emailed you."
            )}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 space-y-5"
        >
          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Verification code
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              autoFocus
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-center text-lg tracking-[0.5em] bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || code.length !== 6}
            className="w-full py-2.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Verifying..." : "Verify"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Didn&apos;t get a code?{" "}
          <button
            type="button"
            onClick={handleResend}
            disabled={isResending || resendCooldown > 0}
            className="text-dlv-accent font-medium hover:underline disabled:opacity-50 disabled:no-underline"
          >
            {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend code"}
          </button>
        </p>
      </div>
    </div>
  );
}
