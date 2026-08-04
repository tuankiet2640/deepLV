import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthError, useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const successMessage =
    searchParams.get("registered") === "true"
      ? "Account created successfully. Please log in."
      : searchParams.get("verified") === "true"
        ? "Email verified. Please log in."
        : null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setUnverifiedEmail(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      showToast("Signed in successfully", "success");
      navigate("/translate", { replace: true });
    } catch (err) {
      if (err instanceof AuthError && err.code === "email_not_verified") {
        setUnverifiedEmail(email);
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Login failed");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Sign in to DeepLV</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Enter your credentials to access translation services.
          </p>
        </div>

        {successMessage && (
          <div className="mb-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 px-4 py-3 text-sm text-green-700 dark:text-green-300">
            {successMessage}
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
            {unverifiedEmail && (
              <>
                {" "}
                <Link
                  to={`/verify-email?email=${encodeURIComponent(unverifiedEmail)}`}
                  className="font-medium underline"
                >
                  Resend verification email
                </Link>
              </>
            )}
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

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              className="w-full border border-dlv-border dark:border-dlv-dark-border rounded-md px-3 py-2 text-sm bg-white dark:bg-dlv-dark-bg dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-dlv-accent focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-dlv-accent text-white text-sm font-medium rounded-md hover:bg-dlv-accent/90 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-dlv-accent font-medium hover:underline">
            Create one
          </Link>
        </p>
        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">
          <Link to="/forgot-password" className="text-dlv-accent font-medium hover:underline">
            Forgot password?
          </Link>
        </p>
      </div>
    </div>
  );
}
