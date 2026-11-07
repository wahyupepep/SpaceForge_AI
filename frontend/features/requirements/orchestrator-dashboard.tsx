"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { orchestratorService } from "@/services/orchestrator";
import { uiLabel } from "@/lib/ui-labels";
import type { OrchestratorWorkflow } from "@/types/api";

const label = uiLabel;

export function OrchestratorDashboard({
  projectId,
  requirementId,
  workflow: initialWorkflow,
}: {
  projectId: string;
  requirementId: string;
  workflow?: OrchestratorWorkflow;
}) {
  const router = useRouter();
  const [progress, setWorkflow] = useState(initialWorkflow);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const workflow = running ? progress : initialWorkflow;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  async function advance() {
    setWorkflow(initialWorkflow);
    setRunning(true);
    setError(null);
    try {
      let current = workflow
        ? await orchestratorService.resume(projectId, requirementId)
        : await orchestratorService.start(projectId, requirementId);
      if (mounted.current) setWorkflow(current);
      // Each request persists one stage on Vercel. Continue until the workflow
      // reaches a human decision; closing the page leaves it resumable.
      while (mounted.current && current.status === "ACTIVE" && !current.pending_user_action) {
        current = await orchestratorService.resume(projectId, requirementId);
        if (mounted.current) setWorkflow(current);
      }
      if (mounted.current) router.refresh();
    } catch (caught) {
      if (mounted.current) {
        setError(caught instanceof ApiClientError ? caught.message : "Otomasi alur analisis gagal dijalankan.");
        router.refresh();
      }
    } finally {
      if (mounted.current) setRunning(false);
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Alur analisis otomatis</p>
          <h4 className="mt-1 font-bold">{workflow ? label(workflow.current_stage) : "Belum dimulai"}</h4>
          <p className="mt-1 text-xs text-ink/55">
            {workflow?.current_agent ? `Analis aktif: ${label(workflow.current_agent)}` : "Belum ada analis spesialis yang aktif."}
          </p>
        </div>
        <button
          type="button"
          disabled={running || workflow?.status === "COMPLETED"}
          onClick={advance}
          className="rounded-lg bg-cyan-800 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {running ? "Menjalankan…" : workflow ? "Lanjutkan alur" : "Mulai alur"}
        </button>
      </div>

      {error ? <p role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
      {workflow ? (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Tindakan pengguna</p>
            <p className="mt-2 text-sm font-semibold text-ink/75">{workflow.pending_user_action ? label(workflow.pending_user_action) : "Tidak ada"}</p>
            {workflow.last_error ? <p className="mt-2 text-xs leading-5 text-red-700">{workflow.last_error}</p> : null}
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Tahap yang selesai</p>
            <p className="mt-2 text-sm leading-6 text-ink/65">{workflow.completed_stages.length ? workflow.completed_stages.map(label).join(" · ") : "Belum ada"}</p>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Status artefak</p>
            <ul className="mt-2 space-y-1 text-xs text-ink/65">
              {Object.entries(workflow.artifact_status).map(([type, status]) => (
                <li key={type} className="flex justify-between gap-3"><span>{label(type)}</span><span className="font-semibold">v{status.version} · {label(status.status)}</span></li>
              ))}
              {!Object.keys(workflow.artifact_status).length ? <li>Belum ada</li> : null}
            </ul>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Riwayat revisi</p>
            <ul className="mt-2 space-y-1 text-xs text-ink/65">
              {workflow.revision_history.map((item, index) => <li key={index}>#{String(item.revision ?? index + 1)} · {label(String(item.artifact ?? "artifact"))}</li>)}
              {!workflow.revision_history.length ? <li>Belum ada revisi dari reviewer.</li> : null}
            </ul>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4 md:col-span-2">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Riwayat proses</p>
            <ol className="mt-2 grid gap-2 sm:grid-cols-2">
              {workflow.executions.slice().reverse().map((execution) => (
                <li key={execution.id} className="rounded-lg bg-ink/[0.03] px-3 py-2 text-xs">
                  <span className="font-semibold">{label(execution.stage)}</span> · {label(execution.status)}
                </li>
              ))}
            </ol>
          </div>
        </div>
      ) : null}
    </section>
  );
}
