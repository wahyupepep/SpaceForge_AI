import Link from "next/link";

import { projectStatusClasses, projectStatusLabels, projectTypeLabels } from "@/features/projects/project-meta";
import { serverProjectsService } from "@/services/server-projects";
import type { Project } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  let projects: Project[] = [];
  let unavailable = false;
  try {
    projects = await serverProjectsService.list();
  } catch {
    unavailable = true;
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-col gap-5 border-b border-ink/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">Projects</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight">Project context intake</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/55">Capture the business objective and protect enhancement work with an AS-IS readiness gate.</p>
        </div>
        <Link href="/projects/new" className="rounded-xl bg-accent px-5 py-3 text-center text-sm font-semibold text-white shadow-sm hover:bg-orange-600">New project</Link>
      </div>

      {unavailable ? (
        <div role="alert" className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">The project API is unavailable. Confirm that the backend and PostgreSQL are running.</div>
      ) : projects.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-dashed border-ink/20 bg-white p-12 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-ink text-lg font-bold text-white">+</div>
          <h2 className="mt-5 text-lg font-semibold">Start with project context</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/55">Create a draft and choose whether the work is a new system, new feature, or enhancement.</p>
          <Link href="/projects/new" className="mt-6 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white">Create first project</Link>
        </div>
      ) : (
        <div className="mt-8 grid gap-4">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`} className="group rounded-2xl border border-ink/10 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-md">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-accent">{projectTypeLabels[project.project_type]}</span>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${projectStatusClasses[project.status]}`}>{projectStatusLabels[project.status]}</span>
                  </div>
                  <h2 className="mt-3 text-xl font-bold group-hover:text-accent">{project.name}</h2>
                  <p className="mt-2 line-clamp-2 max-w-3xl text-sm leading-6 text-ink/55">{project.description}</p>
                </div>
                <span className="text-sm font-semibold text-ink/35 group-hover:text-accent">Open →</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
