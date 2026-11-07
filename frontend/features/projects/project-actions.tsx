"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { contextFieldLabels } from "@/features/projects/project-meta";
import { ApiClientError } from "@/services/api-client";
import { projectsService } from "@/services/projects";

export function ProjectActions({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [busyAction, setBusyAction] = useState<"submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState<string[]>([]);

  async function submitForAnalysis() {
    setBusyAction("submit");
    setError(null);
    setMissing([]);
    try {
      await projectsService.submitForAnalysis(projectId);
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiClientError) {
        setError(caught.message);
        setMissing(caught.details.map((detail) => String(detail.field ?? "")));
      } else {
        setError("Proyek tidak dapat dikirim untuk dianalisis.");
      }
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="rounded-2xl bg-ink p-6 text-white shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/50">Pemeriksaan konteks</p>
      <h2 className="mt-2 text-xl font-bold">Konteks sudah siap dianalisis?</h2>
      <p className="mt-2 text-sm leading-6 text-white/65">Sistem akan memastikan informasi wajib sudah lengkap sebelum masuk ke tahap penggalian requirement.</p>
      {error ? (
        <div role="alert" className="mt-4 rounded-xl bg-red-400/15 p-4 text-sm text-red-100">
          <p>{error}</p>
          {missing.length ? <p className="mt-2">Belum lengkap: {missing.map((field) => contextFieldLabels[field] ?? field).join(", ")}.</p> : null}
        </div>
      ) : null}
      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" onClick={submitForAnalysis} disabled={busyAction !== null} className="rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50">
          {busyAction === "submit" ? "Memeriksa…" : "Kirim untuk dianalisis"}
        </button>
      </div>
    </div>
  );
}

