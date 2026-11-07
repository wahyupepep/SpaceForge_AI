import Link from "next/link";
import { notFound } from "next/navigation";

import { ProjectEvidenceWorkspace } from "@/features/projects/project-evidence";
import { ProjectForm } from "@/features/projects/project-form";
import { ApiClientError } from "@/services/api-client";
import { serverProjectsService } from "@/services/server-projects";

export const dynamic = "force-dynamic";

export default async function EditProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let project;
  try { project = await serverProjectsService.get(id); } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
  const evidence = project.project_type === "ENHANCEMENT" ? await serverProjectsService.listEvidence(id) : [];
  return <div className="mx-auto max-w-5xl"><Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke daftar proyek</Link><div className="mt-7 border-b border-ink/10 pb-7"><p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">Edit input proyek</p><h1 className="mt-2 text-4xl font-bold">{project.name}</h1><p className="mt-3 text-sm text-ink/55">Perbarui konteks yang akan menjadi dasar analisis. Perubahan tidak menghapus riwayat artefak.</p></div><div className="mt-8"><ProjectForm project={project} /></div>{project.project_type === "ENHANCEMENT" ? <div className="mt-8"><ProjectEvidenceWorkspace projectId={id} evidence={evidence} /></div> : null}</div>;
}
