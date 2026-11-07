"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { projectStatusClasses, projectStatusLabels, projectTypeLabels } from "@/features/projects/project-meta";
import { projectsService } from "@/services/projects";
import type { Project } from "@/types/api";

function ActionIcon({ name }: { name: "input" | "output" | "edit" | "delete" }) {
  const paths = {
    input: <><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5A3.375 3.375 0 0 0 10.125 2.25H8.25m0 12.75h7.5m-7.5 3h4.5M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></>,
    output: <><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25m-4.5-13.5h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0L6.75 21m9-12-3 3-2.25-2.25L7.5 12.75" /></>,
    edit: <><path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21h-10.5A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" /></>,
    delete: <><path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673A2.25 2.25 0 0 1 15.916 21.75H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></>,
  };
  return <svg aria-hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" className="h-[17px] w-[17px]">{paths[name]}</svg>;
}

const iconButton = "group relative grid h-9 w-9 place-items-center rounded-md border border-ink/15 bg-white text-ink/55 hover:border-ink/30 hover:bg-canvas hover:text-ink";
const Tooltip = ({ children }: { children: string }) => <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-ink px-2 py-1 text-[10px] font-semibold text-white opacity-0 shadow-sm transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">{children}</span>;

export function ProjectList({ projects }: { projects: Project[] }) {
  const router = useRouter();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove(project: Project) {
    if (!window.confirm(`Hapus proyek “${project.name}”? Semua konteks dan requirement proyek ini akan dihapus.`)) return;
    setDeletingId(project.id);
    setError(null);
    try {
      await projectsService.delete(project.id);
      router.refresh();
    } catch {
      setError("Proyek tidak dapat dihapus. Silakan coba kembali.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mt-8">
      {error ? <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      <div className="overflow-hidden border-y border-ink/10 bg-white/50">
        <div className="hidden grid-cols-[minmax(280px,1fr)_160px_160px_190px] gap-4 border-b border-ink/10 bg-ink/[0.025] px-5 py-3 text-[10px] font-bold uppercase tracking-[0.12em] text-ink/40 xl:grid">
          <span>Proyek</span><span>Jenis</span><span>Status</span><span>Aksi</span>
        </div>
        {projects.map((project) => (
          <article key={project.id} className="grid gap-4 border-b border-ink/10 p-5 last:border-b-0 hover:bg-white/70 xl:grid-cols-[minmax(280px,1fr)_160px_160px_190px] xl:items-center">
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold">{project.name}</h2>
              <p className="mt-1 line-clamp-1 text-sm text-ink/50">{project.description}</p>
              <p className="mt-1.5 text-[11px] text-ink/35">{project.evidence_count} referensi · {new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(new Date(project.updated_at))}</p>
            </div>
            <div><span className="text-xs font-bold uppercase tracking-wide text-accent xl:hidden">Jenis · </span><span className="text-sm font-semibold">{projectTypeLabels[project.project_type]}</span></div>
            <div><span className="text-xs font-bold uppercase tracking-wide text-ink/40 xl:hidden">Status · </span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${projectStatusClasses[project.status]}`}>{projectStatusLabels[project.status]}</span></div>
            <div className="flex flex-wrap gap-2">
              <Link href={`/projects/${project.id}/details`} aria-label={`Lihat input ${project.name}`} className={iconButton}><ActionIcon name="input" /><Tooltip>Lihat input</Tooltip></Link>
              <Link href={`/projects/${project.id}/outputs`} aria-label={`Lihat output ${project.name}`} className={`${iconButton} !border-[#246b5a] !bg-[#246b5a] !text-white hover:!border-[#1d584a] hover:!bg-[#1d584a]`}><ActionIcon name="output" /><Tooltip>Lihat output</Tooltip></Link>
              <Link href={`/projects/${project.id}/edit`} aria-label={`Edit ${project.name}`} className={iconButton}><ActionIcon name="edit" /><Tooltip>Edit proyek</Tooltip></Link>
              <button type="button" aria-label={`Hapus ${project.name}`} disabled={deletingId !== null} onClick={() => remove(project)} className={`${iconButton} !border-transparent !bg-transparent !text-red-600 hover:!border-red-200 hover:!bg-red-50 hover:!text-red-700 disabled:opacity-40`}><ActionIcon name="delete" /><Tooltip>{deletingId === project.id ? "Menghapus…" : "Hapus proyek"}</Tooltip></button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
