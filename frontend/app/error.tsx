"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("SpecForge page error", { digest: error.digest });
  }, [error]);

  return (
    <main className="mx-auto max-w-2xl px-6 py-24">
      <section className="rounded-2xl border border-red-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-red-700">Request failed</p>
        <h1 className="mt-2 text-2xl font-bold">The workspace could not be loaded.</h1>
        <p className="mt-3 text-sm leading-6 text-ink/60">
          Your saved project state was not changed. Retry the request, or check the API health and
          request ID in the server logs if the problem continues.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white"
        >
          Retry
        </button>
      </section>
    </main>
  );
}
