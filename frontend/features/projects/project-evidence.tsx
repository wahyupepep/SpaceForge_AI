"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { projectsService } from "@/services/projects";
import { env } from "@/lib/env";
import { uiLabel } from "@/lib/ui-labels";
import type { ProjectEvidence } from "@/types/api";

const fieldClass =
  "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15";

const categories = [
  ["UI_SCREENSHOT", "Screenshot UI"],
  ["SOURCE_CODE", "Source code / arsip repository"],
  ["API_DOCUMENTATION", "Dokumentasi API"],
  ["DATABASE_SCHEMA", "Skema database"],
  ["PROCESS_DOCUMENT", "Dokumen proses atau bisnis"],
  ["OTHER", "Referensi lainnya"],
];

export function ProjectEvidenceWorkspace({
  projectId,
  evidence,
}: {
  projectId: string;
  evidence: ProjectEvidence[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const form = event.currentTarget;
    try {
      await projectsService.uploadEvidence(projectId, new FormData(form));
      form.reset();
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Referensi tidak dapat diunggah.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(evidenceId: string) {
    if (!window.confirm("Hapus referensi ini dari workspace proyek?")) return;
    setBusy(true);
    setError(null);
    try {
      await projectsService.deleteEvidence(projectId, evidenceId);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Referensi tidak dapat dihapus.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-violet-200 bg-violet-50/50 p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-700">Referensi sistem yang sudah ada</p>
      <h2 className="mt-2 text-xl font-bold">Berikan bahan nyata untuk dipelajari analis</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/60">
        Analisis peningkatan produk membutuhkan minimal satu referensi. Unggah screenshot, source code, dokumen API, skema, atau dokumen proses. Maksimal 4 MB per file.
      </p>

      {error ? <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

      <form onSubmit={upload} className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="text-sm font-semibold">Jenis referensi
          <select required name="category" className={fieldClass}>
            {categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold">Judul
          <input required name="title" maxLength={200} className={fieldClass} placeholder="Layar persetujuan saat ini" />
        </label>
        <label className="text-sm font-semibold md:col-span-2">Apa yang perlu diperhatikan analis?
          <textarea name="description" maxLength={2000} rows={2} className={fieldClass} placeholder="Jelaskan alur, keterbatasan, atau komponen yang relevan." />
        </label>
        <label className="text-sm font-semibold md:col-span-2">Berkas
          <input required name="file" type="file" className={fieldClass} />
        </label>
        <div className="md:col-span-2 flex justify-end">
          <button disabled={busy} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Mengunggah…" : "Tambahkan referensi"}</button>
        </div>
      </form>

      <div className="mt-6 space-y-3">
        {evidence.map((item) => (
          <article key={item.id} className="flex flex-col gap-3 rounded-xl border border-violet-100 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-violet-700">{uiLabel(item.category)}</p>
              <p className="mt-1 font-semibold">{item.title}</p>
              <p className="mt-1 text-xs text-ink/50">{item.original_filename} · {(item.size_bytes / 1024).toFixed(1)} KB</p>
              {item.description ? <p className="mt-2 text-sm leading-6 text-ink/60">{item.description}</p> : null}
            </div>
            <div className="flex gap-2">
              <a href={`${env.apiBaseUrl}/projects/${projectId}/evidence/${item.id}/download`} target="_blank" rel="noreferrer" className="rounded-lg border border-violet-200 px-3 py-2 text-xs font-semibold text-violet-700">Buka</a>
              <button type="button" disabled={busy} onClick={() => remove(item.id)} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 disabled:opacity-50">Hapus</button>
            </div>
          </article>
        ))}
        {!evidence.length ? <p className="rounded-xl border border-dashed border-violet-200 bg-white/60 p-5 text-sm text-violet-900">Belum ada referensi. Peningkatan produk belum dapat masuk ke penggalian requirement.</p> : null}
      </div>
    </section>
  );
}
