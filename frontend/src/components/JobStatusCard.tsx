import type { DocumentJob } from "../hooks/useDocumentTranslation";

interface JobStatusCardProps {
  job: DocumentJob;
  onDownload: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  pending: { bg: "bg-yellow-100", text: "text-yellow-800", label: "Pending" },
  processing: { bg: "bg-blue-100", text: "text-blue-800", label: "Processing" },
  completed: { bg: "bg-green-100", text: "text-green-800", label: "Completed" },
  failed: { bg: "bg-red-100", text: "text-red-800", label: "Failed" },
};

export function JobStatusCard({ job, onDownload, onDelete }: JobStatusCardProps) {
  const status = STATUS_STYLES[job.status] ?? { bg: "bg-gray-100", text: "text-gray-800", label: "Unknown" };

  return (
    <div className="border border-dlv-border rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-medium text-gray-900 truncate">{job.original_filename}</span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
            <span>{job.source_lang} &rarr; {job.target_lang}</span>
            <span className="capitalize">{job.provider}</span>
            <span>{new Date(job.created_at).toLocaleString()}</span>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-4">
          <span className={`text-xs font-medium px-2 py-1 rounded ${status.bg} ${status.text}`}>
            {status.label}
          </span>

          {job.status === "processing" && (
            <div className="flex gap-0.5">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" />
            </div>
          )}

          {job.status === "completed" && (
            <button
              onClick={() => onDownload(job.id)}
              className="flex items-center gap-1 px-3 py-1.5 bg-dlv-accent text-white text-xs font-medium rounded-md hover:bg-dlv-accent/90 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </button>
          )}

          <button
            onClick={() => onDelete(job.id)}
            title="Delete this job"
            aria-label={`Delete translation job for ${job.original_filename}`}
            className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {job.error_message && (
        <p className="mt-2 text-sm text-red-600">{job.error_message}</p>
      )}
    </div>
  );
}
