import Link from "next/link";
import { notFound } from "next/navigation";

import { DevelopmentHandoffWorkspace } from "@/features/handoff/development-handoff-workspace";
import { ApiClientError } from "@/services/api-client";
import { serverProjectsService } from "@/services/server-projects";
import {
  serverDevelopmentHandoffService,
  serverQualityGateService,
  serverRequirementsService,
} from "@/services/server-requirements";
import type { HandoffWorkflow } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function DevelopmentHandoffPage({
  params,
}: {
  params: Promise<{ id: string; requirementId: string }>;
}) {
  const { id, requirementId } = await params;
  const [project, requirements, qualityWorkflows] = await Promise.all([
    serverProjectsService.get(id),
    serverRequirementsService.list(id),
    serverQualityGateService.list(id),
  ]);
  const requirement = requirements.find((item) => item.id === requirementId);
  if (!requirement) notFound();
  let workflow: HandoffWorkflow | null = null;
  try {
    workflow = await serverDevelopmentHandoffService.get(id, requirementId);
  } catch (error) {
    if (!(error instanceof ApiClientError && error.status === 404)) throw error;
  }
  const qualityWorkflow = qualityWorkflows.find(
    (item) => item.requirement_id === requirementId,
  ) ?? null;

  return (
    <div className="mx-auto max-w-7xl">
      <Link href={`/projects/${id}`} className="text-sm font-semibold text-ink/50 hover:text-accent">← Back to project</Link>
      <div className="mt-8 border-b border-ink/10 pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">Development Handoff</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">{requirement.title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-ink/60">Preview dependency-aware tasks, inspect traceability, and export the approved specification package without creating new requirements.</p>
      </div>
      <DevelopmentHandoffWorkspace project={project} requirement={requirement} qualityWorkflow={qualityWorkflow} initialWorkflow={workflow} />
    </div>
  );
}
