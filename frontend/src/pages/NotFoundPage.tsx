import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-12">
      <div className="text-center max-w-md">
        {/* 404 illustration */}
        <div className="mb-8">
          <svg
            className="mx-auto w-32 h-32 text-gray-300 dark:text-gray-600"
            fill="none"
            viewBox="0 0 128 128"
            stroke="currentColor"
          >
            <circle cx="64" cy="64" r="56" strokeWidth="4" strokeDasharray="8 4" />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="4"
              d="M44 48l8-8m0 8l-8-8M76 48l8-8m0 8l-8-8M48 84c4-6 10-10 16-10s12 4 16 10"
            />
          </svg>
        </div>

        <h1 className="text-6xl font-bold text-gray-900 dark:text-gray-100 mb-2">404</h1>
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-4">
          Page not found
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-8">
          The page you are looking for does not exist or has been moved.
        </p>

        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-dlv-accent text-white font-medium rounded-lg hover:bg-dlv-accent/90 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
            />
          </svg>
          Go Home
        </Link>
      </div>
    </div>
  );
}
