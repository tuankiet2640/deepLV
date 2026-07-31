import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResetToken(null);
    setIsSubmitting(true);

    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Request failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      setResetToken(data.reset_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Forgot Password</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Enter your email address and we will generate a reset token.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {resetToken && (
          <div className="mb-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 px-4 py-3 text-sm text-green-700 dark:text-green-300 space-y-2">
            <p className="font-medium">Reset token generated!</p>
            <p className="font-mono text-xs break-all bg-green-100 dark:bg-green-900/40 p-2 rounded">
              {resetToken}
            </p>
            <p className="text-xs">
              Use this token on the{" "}
              <Link to="/reset-password" className="underline font-medium">
                reset password page
              </Link>
              .
            </p>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="bg-white dark:bg-dlv-dark-card rounded-xl shadow-sm border border-dlv-border dark:border-dlv-dark-border p-6 space-y-5"
        >
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Sending..." : "Send Reset Token"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Remember your password?{" "}
          <Link to="/login" className="text-dlv-accent font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
