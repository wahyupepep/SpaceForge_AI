"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { env } from "@/lib/env";
import { ApiClientError } from "@/services/api-client";
import { developmentHandoffService } from "@/services/development-handoff";
import type {
  DevelopmentTask,
  HandoffWorkflow,
  Project,
  QualityWorkflow,
  Requirement,
} from "@/types/api";

const errorMessage = (error: unknown) =>
  error instanceof ApiClientError ? error.message : "Permintaan tidak dapat diselesaikan.";

function developmentTasks(workflow: HandoffWorkflow | null): DevelopmentTask[] {
  const tasks = workflow?.task_artifact.content_json.tasks;
  return Array.isArray(tasks) ? (tasks as DevelopmentTask[]) : [];
}

export function DevelopmentHandoffWorkspace({
  project,
  requirement,
  qualityWorkflow,
  initialWorkflow,
}: {
  project: Project;
  requirement: Requirement;
  qualityWorkflow: QualityWorkflow | null;
  initialWorkflow: HandoffWorkflow | null;
}) {
  const router = useRouter();
  const [running, setRunning] = useState<"plan" | "package" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const workflow = initialWorkflow;
  const tasks = developmentTasks(workflow);
  const packageContent = workflow?.current_package?.content_json;
  const gateOpen = qualityWorkflow?.development_handoff_allowed === true;

  async function plan() {
    setRunning("plan");
    setError(null);
    try {
      await developmentHandoffService.plan(project.id, requirement.id);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setRunning(null);
    }
  }

  async function generatePackage() {
    if (!workflow) return;
    setRunning("package");
    setError(null);
    try {
      await developmentHandoffService.generate(
        project.id,
        requirement.id,
        workflow.current_task_version,
      );
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="mt-8 grid gap-8 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="h-fit rounded-2xl border border-ink/10 bg-white p-4 shadow-sm lg:sticky lg:top-6">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink/45">Navigasi paket</p>
        <nav className="mt-3 space-y-1">
          {(packageContent?.sections ?? []).map((section) => (
            <a key={section.slug} href={`#${section.slug}`} className="block rounded-lg px-3 py-2 text-xs font-semibold text-ink/65 hover:bg-ink/5 hover:text-accent">
              {section.number} {section.title}
            </a>
          ))}
          {!packageContent ? <p className="px-3 py-2 text-xs leading-5 text-ink/45">Buat paket setelah meninjau rancangan task.</p> : null}
        </nav>
      </aside>

      <main className="min-w-0 space-y-6">
        {error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <section className={`rounded-2xl border p-6 ${gateOpen ? "border-emerald-200 bg-emerald-50/50" : "border-amber-200 bg-amber-50"}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink/45">Pemeriksaan kualitas</p>
              <h2 className="mt-1 text-lg font-bold">{gateOpen ? "LOLOS — serah terima terbuka" : "Serah terima terkunci"}</h2>
              <p className="mt-1 text-sm text-ink/60">Hanya versi artefak yang telah diterima reviewer sistem analis yang dapat masuk ke paket ini.</p>
            </div>
            <button disabled={!gateOpen || running !== null} onClick={plan} className="rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">
              {running === "plan" ? "Menyusun…" : workflow ? "Susun ulang rencana task" : "Susun task pengembangan"}
            </button>
          </div>
        </section>

        {workflow ? (
          <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Pratinjau task · v{workflow.current_task_version}</p>
                <h2 className="mt-1 text-xl font-bold">Tinjau sebelum membuat paket</h2>
                <p className="mt-1 text-sm text-ink/55">{tasks.length} task beserta dependensinya. Paket akan memakai versi ini.</p>
              </div>
              <button disabled={!gateOpen || running !== null || !tasks.length} onClick={generatePackage} className="rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">
                {running === "package" ? "Membuat paket…" : "Buat paket serah terima"}
              </button>
            </div>
            <ol className="mt-6 space-y-4">
              {tasks.map((task, index) => (
                <li key={task.id} className="rounded-xl border border-ink/10 p-5">
                  <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-ink px-2.5 py-1 text-[11px] font-bold text-white">{index + 1}</span><span className="text-xs font-bold text-accent">{task.id}</span><span className="rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-bold text-accent">{task.workstream}</span></div>
                  <h3 className="mt-3 font-bold">{task.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-ink/65">{task.objective}</p>
                  <div className="mt-3 grid gap-3 text-xs text-ink/60 sm:grid-cols-2">
                    <p><span className="font-bold text-ink">Requirement:</span> {task.requirement}</p>
                    <p><span className="font-bold text-ink">Dependensi:</span> {task.dependency.join(", ") || "Tidak ada"}</p>
                    <p><span className="font-bold text-ink">Kriteria penerimaan:</span> {task.acceptance_criteria.join(", ")}</p>
                    <p><span className="font-bold text-ink">Artefak:</span> {task.reference_artifact.join(", ")}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        {workflow?.current_package && packageContent ? (
          <>
            <section className="rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Paket v{workflow.current_package.version}</p><h2 className="mt-1 text-xl font-bold">{packageContent.package_name}</h2></div>
                <div className="flex flex-wrap gap-2">
                  {(["json", "markdown", "trello"] as const).map((format) => (
                    <a key={format} href={`${env.apiBaseUrl}/projects/${project.id}/requirements/${requirement.id}/handoff/packages/${workflow.current_package?.version}/download/${format}`} className="rounded-lg border border-emerald-300 px-3 py-2 text-xs font-bold uppercase text-emerald-800 hover:bg-emerald-50">Unduh {format}</a>
                  ))}
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-sm">
              <div className="border-b border-ink/10 px-6 py-4"><h2 className="font-bold">Ketertelusuran task</h2></div>
              <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="bg-ink/[0.03] text-ink/50"><tr><th className="px-4 py-3">Task</th><th className="px-4 py-3">Requirement</th><th className="px-4 py-3">Kriteria penerimaan</th><th className="px-4 py-3">Artefak</th></tr></thead><tbody>{packageContent.traceability.map((entry) => <tr key={entry.task_id} className="border-t border-ink/10"><td className="px-4 py-3 font-bold">{entry.task_id}</td><td className="px-4 py-3">{entry.requirement}</td><td className="px-4 py-3">{entry.acceptance_criteria.join(", ")}</td><td className="px-4 py-3">{entry.reference_artifacts.join(", ")}</td></tr>)}</tbody></table></div>
            </section>

            {packageContent.sections.map((section) => (
              <section id={section.slug} key={section.slug} className="scroll-mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">{section.number}</p>
                <h2 className="mt-1 text-xl font-bold">{section.title}</h2>
                <div className="mt-2 flex flex-wrap gap-2">{section.source_artifacts.map((source) => <span key={`${source.artifact_id}-${source.version}`} className="rounded-full bg-ink/5 px-2.5 py-1 text-[11px] font-semibold text-ink/55">{source.artifact_type} v{source.version}</span>)}</div>
                <details className="mt-4" open={section.number === "13"}><summary className="cursor-pointer text-sm font-semibold text-accent">Lihat konten terstruktur</summary><pre className="mt-3 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">{JSON.stringify(section.content, null, 2)}</pre></details>
              </section>
            ))}
          </>
        ) : null}
      </main>
    </div>
  );
}
