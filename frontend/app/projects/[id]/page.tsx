import Link from "next/link";
import { notFound } from "next/navigation";

import { ProjectActions } from "@/features/projects/project-actions";
import { projectStatusClasses, projectStatusLabels, projectTypeLabels } from "@/features/projects/project-meta";
import { RequirementWorkspace } from "@/features/requirements/requirement-workspace";
import { ApiClientError } from "@/services/api-client";
import { serverProjectsService } from "@/services/server-projects";
import { serverArtifactsService, serverOrchestratorService, serverQualityGateService, serverRequirementAnalysisService, serverRequirementsService, serverSolutionAnalysisService } from "@/services/server-requirements";

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let project;
  try {
    project = await serverProjectsService.get(id);
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
  const [requirements, artifacts, solutionWorkflows, qualityWorkflows, orchestratorWorkflows] = await Promise.all([
    serverRequirementsService.list(id),
    serverArtifactsService.list(id),
    serverSolutionAnalysisService.list(id),
    serverQualityGateService.list(id),
    serverOrchestratorService.list(id),
  ]);
  const clarifications = (
    await Promise.all(
      requirements.map((requirement) =>
        serverRequirementAnalysisService.listClarifications(id, requirement.id),
      ),
    )
  ).flat();

  return (
    <div className="mx-auto max-w-5xl">
      <Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke daftar proyek</Link>
      <div className="mt-7 flex flex-col gap-5 border-b border-ink/10 pb-7 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-accent">Workspace analisis · {projectTypeLabels[project.project_type]}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em]">{project.name}</h1>
          <p className="mt-3 text-xs text-ink/45">Diperbarui {new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(project.updated_at))}</p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1.5 text-xs font-semibold ${projectStatusClasses[project.status]}`}>{projectStatusLabels[project.status]}</span>
      </div>

      {project.project_type === "ENHANCEMENT" && project.missing_context_fields.length ? (
        <div className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          <p className="font-semibold">Konteks peningkatan produk belum lengkap.</p>
          <p className="mt-1 leading-6">Lengkapi kondisi AS-IS dan unggah minimal satu referensi sistem sebelum mulai menggali requirement.</p>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-2"><Link href={`/projects/${id}/details`} className="rounded-lg border border-ink/15 bg-white px-3.5 py-2 text-xs font-semibold text-ink/60">Input</Link><Link href={`/projects/${id}/outputs`} className="rounded-lg border border-ink/15 bg-white px-3.5 py-2 text-xs font-semibold text-ink/60">Output</Link><Link href={`/projects/${id}/edit`} className="rounded-lg border border-ink/15 bg-white px-3.5 py-2 text-xs font-semibold text-ink/60">Edit proyek</Link></div>
      {project.status !== "READY_FOR_ANALYSIS" ? <div className="mt-8"><ProjectActions projectId={project.id} /></div> : null}
      <RequirementWorkspace project={project} requirements={requirements} artifacts={artifacts} clarifications={clarifications} solutionWorkflows={solutionWorkflows} qualityWorkflows={qualityWorkflows} orchestratorWorkflows={orchestratorWorkflows} />
    </div>
  );
}
