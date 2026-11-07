import Link from "next/link";

import { ProjectForm } from "@/features/projects/project-form";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Kembali ke daftar proyek</Link>
      <p className="mt-7 text-xs font-bold uppercase tracking-[0.14em] text-accent">Proyek baru</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em]">Mulai dari konteks pekerjaan.</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/50">Pilih jenis pekerjaan agar pertanyaan dan referensi yang diminta sesuai dengan kebutuhan analisis.</p>
      <div className="mt-8"><ProjectForm /></div>
    </div>
  );
}

