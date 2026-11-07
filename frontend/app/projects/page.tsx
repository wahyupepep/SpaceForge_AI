import Link from "next/link";

import { ProjectList } from "@/features/projects/project-list";
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
      <div className="flex flex-col gap-5 border-b border-ink/10 pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">Portofolio kerja</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em]">Proyek analisis</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/50">Pilih tindakan yang ingin dilakukan tanpa masuk ke workspace yang penuh.</p>
        </div>
        <Link href="/projects/new" className="rounded-lg bg-accent px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-[#bd4524]">+ Proyek baru</Link>
      </div>

      {unavailable ? (
        <div role="alert" className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">Data proyek tidak dapat diakses. Pastikan backend dan PostgreSQL sedang berjalan.</div>
      ) : projects.length === 0 ? (
        <div className="mt-8 border border-dashed border-ink/20 bg-white/50 p-12 text-center">
          <div className="mx-auto grid h-10 w-10 place-items-center rounded-lg bg-ink text-base font-bold text-white">+</div>
          <h2 className="mt-4 text-lg font-semibold">Mulai proyek pertama</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/55">Tentukan apakah Anda akan membuat sistem baru, fitur baru, atau meningkatkan produk yang sudah ada.</p>
          <Link href="/projects/new" className="mt-6 inline-flex rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white">Buat proyek pertama</Link>
        </div>
      ) : (
        <ProjectList projects={projects} />
      )}
    </div>
  );
}
