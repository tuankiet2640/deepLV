import { useState } from "react";
import { FileUpload } from "../components/FileUpload";
import { ProviderSelector } from "../components/ProviderSelector";
import { JobStatusCard } from "../components/JobStatusCard";
import { useDocumentTranslation } from "../hooks/useDocumentTranslation";

const LANGUAGES = [
  { code: "auto", name: "Detect Language" },
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

export function DocumentTranslatePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("en");
  const [provider, setProvider] = useState("marianmt");

  const { jobs, isUploading, uploadError, uploadDocument, downloadResult } =
    useDocumentTranslation();

  const handleSubmit = async () => {
    if (!selectedFile) return;
    await uploadDocument({
      file: selectedFile,
      sourceLang,
      targetLang,
      provider,
    });
    setSelectedFile(null);
  };

  return (
    <div className="max-w-4xl mx-auto w-full px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Document Translation</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a document and translate it using AI. Choose your provider or use platform credits.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-sm border border-dlv-border p-6 space-y-6">
        <FileUpload
          onFileSelect={setSelectedFile}
          selectedFile={selectedFile}
          disabled={isUploading}
        />

        {/* Language selectors */}
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              className="w-full border border-dlv-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="pt-6">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="w-full border border-dlv-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dlv-accent"
            >
              {TARGET_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Provider selection */}
        <ProviderSelector value={provider} onChange={setProvider} />

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={!selectedFile || isUploading}
          className="w-full py-3 bg-dlv-accent text-white font-medium rounded-lg hover:bg-dlv-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isUploading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Translate Document
            </>
          )}
        </button>

        {uploadError && (
          <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{uploadError}</p>
        )}
      </div>

      {/* Job History */}
      {jobs.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Translation Jobs</h2>
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobStatusCard key={job.id} job={job} onDownload={downloadResult} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
