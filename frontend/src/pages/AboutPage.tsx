import { Link } from "react-router-dom";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="text-xl font-bold text-gray-900 mb-4">{title}</h2>
      {children}
    </section>
  );
}

function Incident({
  title,
  symptom,
  cause,
  fix,
}: {
  title: string;
  symptom: string;
  cause: string;
  fix: string;
}) {
  return (
    <div className="bg-white border border-dlv-border rounded-lg p-5 mb-4">
      <h3 className="font-semibold text-gray-900 mb-3">{title}</h3>
      <div className="space-y-2 text-sm">
        <p className="text-gray-600">
          <span className="text-xs font-medium text-red-500 uppercase mr-2">Symptom</span>
          {symptom}
        </p>
        <p className="text-gray-600">
          <span className="text-xs font-medium text-gray-400 uppercase mr-2">Root cause</span>
          {cause}
        </p>
        <p className="text-gray-600">
          <span className="text-xs font-medium text-green-600 uppercase mr-2">Fix</span>
          {fix}
        </p>
      </div>
    </div>
  );
}

export function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">About</h1>
      <p className="text-gray-500 mb-10">
        Why DeepLV exists, how it was actually built, and a few of the real production
        incidents behind it &mdash; not the marketing version.
      </p>

      <Section title="What this is">
        <div className="bg-white border border-dlv-border rounded-lg p-5">
          <p className="text-sm text-gray-700 leading-relaxed mb-3">
            DeepLV is a solo-built, production-deployed machine translation platform: a
            FastAPI + PostgreSQL + Redis backend, a React/TypeScript frontend, a local
            CTranslate2 inference worker, and integrations with three external translation
            APIs (OpenAI, HuggingFace, Google), plus a BYOK key system, a credit-based
            billing model, document translation with format preservation for DOCX and PDF,
            and an admin dashboard.
          </p>
          <p className="text-sm text-gray-700 leading-relaxed">
            It's a portfolio project in the sense that nobody assigned it to me &mdash; but it
            runs in real production, on Railway, against real Supabase Postgres, and it's
            hit real production bugs with real users (myself, testing it against my own
            documents) filing real bug reports. The incidents below are unedited: symptom,
            root cause, fix, in that order, for issues that actually happened after deploy.
          </p>
        </div>
      </Section>

      <Section title="Production incidents">
        <p className="text-sm text-gray-500 mb-4">
          A running log of real bugs found after shipping, not hypotheticals. Each one was
          diagnosed from production logs or a user report, then verified &mdash; usually against
          a real database or a side-by-side comparison &mdash; before being called fixed.
        </p>

        <Incident
          title="Vietnamese filenames crashed every document download"
          symptom="Downloading any translated document with a non-ASCII filename (e.g. Vietnamese diacritics) returned a 500, every time, for every user."
          cause="The Content-Disposition header embedded the raw filename directly. HTTP headers must be latin-1 encodable; Starlette's header encoder threw UnicodeEncodeError the instant the filename contained a character outside that range."
          fix="RFC 5987 encoding: an ASCII-safe fallback filename plus a filename*=UTF-8'' percent-encoded variant, so non-ASCII names survive and browsers still show the real name."
        />

        <Incident
          title="A shipped migration never actually ran in production"
          symptom="Document upload, list, and download all started 500ing: UndefinedColumnError, a column that the code assumed existed didn't."
          cause="The app relied entirely on Base.metadata.create_all() at startup, which only creates missing tables &mdash; it can't add a column to a table that already exists. The Alembic migration for that column was in the repo, but nothing in the deploy pipeline ever ran it."
          fix="Migrations now auto-apply on every startup, right after create_all() (ordering matters: doing it the other way round breaks fresh databases). Verified by reproducing the exact production error against a real local Postgres in the broken state, then confirming the fix resolves it, before calling it done."
        />

        <Incident
          title="DOCX tables and text boxes silently kept the original language"
          symptom="A user reported a table in a translated DOCX still showing the source language. Later, a bordered callout box ('Lưu ý:' / 'Note:') did too."
          cause="python-docx's own object model (doc.paragraphs, doc.tables) doesn't reach every place text can live in a .docx file. Table cells needed their own walk; text boxes (w:txbxContent) sit entirely outside the model and needed the raw OOXML walked directly."
          fix="Extended extraction and rebuild to walk table cells, then text boxes, in the same order every time (parse and rebuild must stay in lockstep by index). Verified against the actual files that surfaced each bug, not synthetic fixtures alone."
        />

        <Incident
          title="Translated PDFs lost all layout, images, and formatting"
          symptom="A translated PDF came back as a flat wall of text &mdash; the original had bold labels, bullet lists, and two embedded company logos. All of it was gone."
          cause="The original implementation discarded the source PDF entirely and generated a brand-new document from scratch with reportlab, since PDF has no editable text layer the way DOCX does."
          fix="Switched to occlusion-and-redraw: extract each text block's position/font/size with pdfplumber, paint over just that region, redraw the translation into the same box with shrink-to-fit sizing, and composite it back onto the original page. Verified the embedded logos survive byte-for-byte identical, and rendered before/after screenshots rather than trusting the text-extraction diff alone."
        />

        <Incident
          title="Usage logging failed on effectively every translation"
          symptom="Every single usage-log write in production was throwing: 'A transaction is already begun on this Session.'"
          cause="The logging call ran as a detached background task but reused the same DB session the request handler was still using &mdash; which could already have an open transaction from earlier in that same request, and which FastAPI closes the moment the request returns regardless."
          fix="Give the background task its own fresh session, matching a pattern already used correctly elsewhere in the codebase. Reproduced the exact production error against a real Postgres with the old code first, to make sure the diagnosis (not just the symptom) was right before shipping the fix."
        />

        <Incident
          title="A logged-in user got 401'd translating free text"
          symptom="A fully authenticated user got 'Invalid API key or token' translating with the free tier &mdash; no BYOK key involved at all."
          cause="One fetch call built its auth headers as an either/or: if any value (even a stale, invalid leftover) existed for the API-key header, the valid session JWT was never attached to the request at all. Every other authenticated call in the app sent both headers and let the backend pick; this one call didn't."
          fix="Brought it in line with the rest of the codebase's own established pattern. The bug had been hiding in plain sight since every other call site already did this correctly."
        />

        <Incident
          title="MarianMT translated Vietnamese into French... on purpose"
          symptom="A document translation request came back in fluent-but-garbled French, full of hallucinated non-words, on a request the user believed should be in a different target language entirely."
          cause="Not a bug: the target language really was French. MarianMT has no direct Vietnamese-to-French model, so it silently pivots through English (vi→en→fr). That extra hop through small models compounds errors badly on formal, domain-specific text."
          fix="Diagnosed by comparing the same document translated through a different provider side-by-side, which ruled out a routing bug in about two minutes flat. Added an explicit warning in the UI when a pivot is about to happen, instead of a routing 'fix' for something that isn't actually broken."
        />
      </Section>

      <Section title="How it's actually built">
        <div className="bg-white border border-dlv-border rounded-lg p-5">
          <p className="text-sm text-gray-700 leading-relaxed mb-3">
            Built and maintained with Claude Code as an AI pair programmer &mdash; every incident
            above was diagnosed and fixed in that workflow, from reading raw production logs
            through to a verified, tested pull request. That includes actually spinning up a
            disposable local Postgres to reproduce a production error byte-for-byte before
            trusting a fix, and rendering before/after screenshots to check a PDF rebuild
            rather than taking a text diff's word for it.
          </p>
          <p className="text-sm text-gray-700 leading-relaxed">
            The discipline that mattered wasn't the AI part &mdash; it was insisting on
            reproduction before diagnosis, and verification before calling something shipped.
          </p>
        </div>
      </Section>

      <div className="flex items-center justify-center gap-6 text-sm">
        <Link to="/architecture" className="text-dlv-accent font-medium hover:underline">
          System architecture &amp; design decisions &rarr;
        </Link>
        <a
          href="https://github.com/tuankiet2640/deepLV"
          target="_blank"
          rel="noopener noreferrer"
          className="text-dlv-accent font-medium hover:underline"
        >
          Source on GitHub &rarr;
        </a>
      </div>
    </div>
  );
}
