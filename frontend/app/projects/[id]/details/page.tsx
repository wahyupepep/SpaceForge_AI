import Link from "next/link";
import { notFound } from "next/navigation";

import { contextFieldLabels, projectStatusClasses, projectStatusLabels, projectTypeLabels } from "@/features/projects/project-meta";
import { ApiClientError } from "@/services/api-client";
import { serverProjectsService } from "@/services/server-projects";
import { serverRequirementsService } from "@/services/server-requirements";

export const dynamic = "force-dynamic";

export default async function ProjectInputDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let project;
  try { project = await serverProjectsService.get(id); } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
  const [evidence, requirements] = await Promise.all([
    serverProjectsService.listEvidence(id),
    serverRequirementsService.list(id),
  ]);
  const context: Array<[string, string | null]> = [
    ["current_flow", project.context.current_flow], ["current_actors", project.context.current_actors],
    ["current_rules", project.context.current_rules], ["current_problem", project.context.current_problem],
    ["requested_change", project.context.requested_change], ["constraints", project.context.constraints],
    ["notes", project.context.notes],
  ];

  return (
    <div className="mx-auto max-w-5xl">
      <Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke daftar proyek</Link>
      <div className="mt-7 flex flex-col gap-5 border-b border-ink/10 pb-7 sm:flex-row sm:items-start sm:justify-between">
        <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">Detail input proyek</p><h1 className="mt-2 text-4xl font-bold">{project.name}</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-ink/60">{project.description}</p></div>
        <span className={`w-fit rounded-full px-3 py-1.5 text-xs font-semibold ${projectStatusClasses[project.status]}`}>{projectStatusLabels[project.status]}</span>
      </div>

      <div className="mt-7 flex flex-wrap gap-2">
        <Link href={`/projects/${id}`} className="rounded-xl bg-accent px-5 py-3 text-sm font-bold text-white">Lanjutkan analisis</Link>
        <Link href={`/projects/${id}/outputs`} className="rounded-xl bg-emerald-700 px-5 py-3 text-sm font-bold text-white">Lihat output</Link>
        <Link href={`/projects/${id}/edit`} className="rounded-xl border border-ink/15 bg-white px-5 py-3 text-sm font-bold text-ink/70">Edit input</Link>
      </div>

      <section className="mt-8 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-bold">Informasi utama</h2>
        <dl className="mt-6 grid gap-6 sm:grid-cols-2">
          <div><dt className="text-xs font-bold uppercase tracking-wide text-ink/40">Jenis pekerjaan</dt><dd className="mt-2 text-sm font-semibold">{projectTypeLabels[project.project_type]}</dd></div>
          <div><dt className="text-xs font-bold uppercase tracking-wide text-ink/40">Tujuan bisnis</dt><dd className="mt-2 text-sm leading-6 text-ink/70">{project.business_objective}</dd></div>
        </dl>
      </section>

      <section className="mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-bold">Konteks yang telah diinput</h2>
        <dl className="mt-6 grid gap-5 sm:grid-cols-2">
          {context.map(([key, value]) => value ? <div key={key} className="rounded-xl bg-canvas p-4"><dt className="text-xs font-bold uppercase tracking-wide text-ink/40">{contextFieldLabels[key] ?? (key === "constraints" ? "Batasan" : "Catatan")}</dt><dd className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink/70">{value}</dd></div> : null)}
        </dl>
      </section>

      <section className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm"><h2 className="font-bold">Requirement ({requirements.length})</h2><div className="mt-4 space-y-3">{requirements.map((item) => <div key={item.id} className="rounded-xl bg-canvas p-4"><p className="font-semibold">{item.title}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-ink/55">{item.raw_requirement}</p></div>)}{!requirements.length ? <p className="text-sm text-ink/50">Belum ada requirement.</p> : null}</div></div>
        <div className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm"><h2 className="font-bold">Referensi ({evidence.length})</h2><div className="mt-4 space-y-3">{evidence.map((item) => <div key={item.id} className="rounded-xl bg-canvas p-4"><p className="font-semibold">{item.title}</p><p className="mt-1 text-xs text-ink/50">{item.original_filename}</p></div>)}{!evidence.length ? <p className="text-sm text-ink/50">Belum ada referensi.</p> : null}</div></div>
      </section>
    </div>
  );
}
