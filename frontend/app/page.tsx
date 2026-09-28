import Link from "next/link";

import { serverProjectsService } from "@/services/server-projects";

const stages = ["Context", "Requirements", "Solution", "Technical design", "Quality gate", "Handoff"];

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let projectCount: number | string = 0;
  try {
    projectCount = (await serverProjectsService.list()).length;
  } catch {
    projectCount = "—";
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-col gap-5 border-b border-ink/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">Dashboard</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">Shape requirements into delivery.</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-ink/65">
            Create a clear, traceable specification package with deliberate human approval at every critical gate.
          </p>
        </div>
        <Link href="/projects" className="rounded-lg bg-accent px-5 py-3 text-center text-sm font-semibold text-white shadow-sm hover:bg-orange-600">
          View projects
        </Link>
      </div>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          ["Active projects", String(projectCount), "Project context intake is active"],
          ["Pending approvals", "0", "Approval gates arrive in Phase 5"],
          ["Handoffs ready", "0", "Packages arrive in Phase 8"],
        ].map(([label, value, note]) => (
          <article key={label} className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
            <p className="text-sm text-ink/55">{label}</p>
            <p className="mt-3 text-4xl font-bold">{value}</p>
            <p className="mt-3 text-xs leading-5 text-ink/45">{note}</p>
          </article>
        ))}
      </section>

      <section className="mt-8 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold">Analysis pipeline</p>
            <p className="mt-1 text-sm text-ink/55">Artifacts move forward only after required review gates.</p>
          </div>
          <span className="rounded-full bg-ink/5 px-3 py-1 text-xs font-semibold text-ink/60">Planned</span>
        </div>
        <ol className="mt-7 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {stages.map((stage, index) => (
            <li key={stage} className="rounded-xl bg-canvas p-4">
              <span className="text-xs font-bold text-accent">{String(index + 1).padStart(2, "0")}</span>
              <p className="mt-5 text-sm font-semibold">{stage}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
