import Link from "next/link";

import { projectStatusLabels, projectTypeLabels } from "@/features/projects/project-meta";
import { serverProjectsService } from "@/services/server-projects";
import type { Project } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let projects: Project[] = [];
  let unavailable = false;
  try { projects = await serverProjectsService.list(); } catch { unavailable = true; }
  const recent = projects.slice().sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at)).slice(0, 4);
  const ready = projects.filter((item) => item.status === "READY_FOR_ANALYSIS").length;
  const incomplete = projects.filter((item) => item.status === "CONTEXT_INCOMPLETE").length;
  const latest = recent[0];

  return (
    <div className="mx-auto max-w-6xl">
      <section className="grid gap-8 border-b border-ink/10 pb-9 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">Workspace sistem analis</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.08] tracking-[-0.035em] sm:text-[46px]">Dari konteks bisnis menjadi acuan kerja yang dapat dieksekusi.</h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-7 text-ink/55">Kelola penggalian requirement, keputusan solusi, dan output pengembangan dalam satu alur yang tertelusur.</p>
        </div>
        <div className="flex flex-wrap gap-2">{latest ? <Link href={`/projects/${latest.id}`} className="rounded-lg border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink/70 hover:border-ink/30">Lanjutkan terakhir</Link> : null}<Link href="/projects/new" className="rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#bd4524]">+ Proyek baru</Link></div>
      </section>

      {unavailable ? <div className="mt-6 border-l-2 border-red-500 bg-red-50 px-4 py-3 text-sm text-red-700">Data proyek tidak dapat dimuat.</div> : null}

      <section className="mt-7 grid border-y border-ink/10 sm:grid-cols-3">
        {[["Semua proyek", projects.length, "Workspace tersimpan"], ["Siap dianalisis", ready, "Konteks lengkap"], ["Perlu dilengkapi", incomplete, "Menunggu input"]].map(([label, value, note], index) => <div key={label} className={`py-5 sm:px-6 ${index ? "border-t border-ink/10 sm:border-l sm:border-t-0" : ""}`}><p className="text-xs font-semibold text-ink/45">{label}</p><div className="mt-2 flex items-baseline gap-2"><p className="text-3xl font-semibold tracking-tight">{value}</p><span className="text-xs text-ink/35">{note}</span></div></div>)}
      </section>

      <section className="mt-9">
        <div className="flex items-end justify-between"><div><h2 className="text-lg font-semibold tracking-tight">Pekerjaan terbaru</h2><p className="mt-1 text-sm text-ink/45">Proyek yang terakhir diperbarui.</p></div><Link href="/projects" className="text-xs font-bold text-accent hover:underline">Lihat semua →</Link></div>
        {recent.length ? <div className="mt-4 overflow-hidden border-y border-ink/10 bg-white/45">{recent.map((project) => <article key={project.id} className="grid gap-4 border-b border-ink/10 px-4 py-4 last:border-b-0 sm:grid-cols-[1fr_150px_170px_auto] sm:items-center"><div className="min-w-0"><p className="truncate text-sm font-semibold">{project.name}</p><p className="mt-1 truncate text-xs text-ink/40">{project.description}</p></div><p className="text-xs font-semibold text-ink/55">{projectTypeLabels[project.project_type]}</p><p className="text-xs text-ink/50">{projectStatusLabels[project.status]}</p><Link href={`/projects/${project.id}/details`} className="text-xs font-bold text-accent hover:underline">Buka proyek →</Link></article>)}</div> : <div className="mt-4 border border-dashed border-ink/20 p-10 text-center"><p className="font-semibold">Belum ada proyek</p><p className="mt-2 text-sm text-ink/45">Mulai dari konteks bisnis yang ingin Anda analisis.</p></div>}
      </section>

      <section className="mt-9 grid gap-4 lg:grid-cols-[1.25fr_.75fr]">
        <div className="border border-ink/10 bg-[#192321] p-6 text-white"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/35">Alur kerja</p><div className="mt-5 grid gap-4 sm:grid-cols-3">{[["01", "Konteks", "Tetapkan jenis proyek dan kondisi saat ini."], ["02", "Analisis", "Validasi requirement sebelum membuat solusi."], ["03", "Output", "Serahkan acuan siap pakai untuk tim delivery."]].map(([number, title, text]) => <div key={number}><p className="text-xs font-bold text-[#e87852]">{number}</p><h3 className="mt-3 text-sm font-semibold">{title}</h3><p className="mt-1 text-xs leading-5 text-white/45">{text}</p></div>)}</div></div>
        <div className="border border-ink/10 bg-white/55 p-6"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-ink/35">Prinsip analisis</p><p className="mt-4 text-base font-semibold leading-6">AI membantu menyusun. Pengguna tetap memutuskan.</p><p className="mt-2 text-xs leading-5 text-ink/45">Setiap asumsi, revisi, dan persetujuan disimpan sebagai jejak keputusan.</p></div>
      </section>
    </div>
  );
}
