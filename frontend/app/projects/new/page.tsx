import Link from "next/link";

import { ProjectForm } from "@/features/projects/project-form";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <Link href="/projects" className="text-sm font-semibold text-ink/50 hover:text-accent">← Back to projects</Link>
      <p className="mt-8 text-sm font-semibold uppercase tracking-[0.18em] text-accent">New project</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight">Establish the project context</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/55">This context becomes the first workflow gate. You can save a draft before submitting it for analysis.</p>
      <div className="mt-8"><ProjectForm /></div>
    </div>
  );
}

