import Link from "next/link";
import { notFound } from "next/navigation";

import { AnalysisOutput } from "@/features/outputs/analysis-output";
import { serverProjectsService } from "@/services/server-projects";
import { serverArtifactsService, serverRequirementsService } from "@/services/server-requirements";

export const dynamic = "force-dynamic";

export default async function AnalysisOutputPage({ params }: { params: Promise<{ id: string; requirementId: string }> }) {
  const { id, requirementId } = await params;
  const [project, requirements, allArtifacts, evidence] = await Promise.all([
    serverProjectsService.get(id),
    serverRequirementsService.list(id),
    serverArtifactsService.list(id),
    serverProjectsService.listEvidence(id),
  ]);
  const requirement = requirements.find((item) => item.id === requirementId);
  if (!requirement) notFound();
  const artifacts = allArtifacts.filter((item) => item.requirement_id === requirementId);

  return <div className="mx-auto max-w-7xl"><Link href={`/projects/${id}`} className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke proyek</Link><div className="mt-7 rounded-3xl bg-ink p-7 text-white sm:p-9"><p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">Hasil analisis sistem</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{requirement.title}</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-white/65">Semua acuan kerja untuk developer dan tester tersedia di satu halaman: gambar UI, requirement, task, acceptance criteria, prompt coding, test case, dan dokumen teknis.</p><div className="mt-5 flex flex-wrap gap-2 text-xs"><span className="rounded-full bg-white/10 px-3 py-1.5">Proyek: {project.name}</span><span className="rounded-full bg-emerald-500/20 px-3 py-1.5 text-emerald-200">Data tersimpan</span></div></div><AnalysisOutput project={project} requirement={requirement} artifacts={artifacts} evidence={evidence} /></div>;
}
