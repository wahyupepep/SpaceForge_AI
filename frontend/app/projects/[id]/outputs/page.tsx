import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { serverProjectsService } from "@/services/server-projects";
import { serverArtifactsService, serverRequirementsService } from "@/services/server-requirements";

export const dynamic = "force-dynamic";

export default async function ProjectOutputsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let project;
  try { project = await serverProjectsService.get(id); } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
  const [requirements, artifacts] = await Promise.all([serverRequirementsService.list(id), serverArtifactsService.list(id)]);
  return <div className="mx-auto max-w-5xl"><Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke daftar proyek</Link><div className="mt-7 border-b border-ink/10 pb-7"><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-700">Output proyek</p><h1 className="mt-2 text-4xl font-bold">{project.name}</h1><p className="mt-3 text-sm leading-6 text-ink/55">Pilih requirement untuk melihat gambar UI, acuan developer, prompt vibe coding, test case, dan dokumentasi teknis.</p></div><div className="mt-8 space-y-4">{requirements.map((requirement) => { const count = artifacts.filter((item) => item.requirement_id === requirement.id).length; return <article key={requirement.id} className="flex flex-col gap-4 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-bold">{requirement.title}</h2><span className="rounded-full bg-ink/5 px-2.5 py-1 text-[11px] font-semibold text-ink/55">{count} artefak</span></div><p className="mt-2 line-clamp-2 max-w-2xl text-sm leading-6 text-ink/55">{requirement.raw_requirement}</p></div><Link href={`/projects/${id}/requirements/${requirement.id}/outputs`} className="shrink-0 rounded-xl bg-emerald-700 px-5 py-3 text-center text-sm font-bold text-white hover:bg-emerald-800">Buka output</Link></article>; })}{!requirements.length ? <div className="rounded-2xl border border-dashed border-ink/20 bg-white p-10 text-center"><h2 className="font-bold">Belum ada output</h2><p className="mt-2 text-sm text-ink/55">Buat dan analisis requirement terlebih dahulu.</p><Link href={`/projects/${id}`} className="mt-5 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-bold text-white">Mulai analisis</Link></div> : null}</div></div>;
}
