"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { orchestratorService } from "@/services/orchestrator";
import type { OrchestratorWorkflow } from "@/types/api";

const label = (value: string) => value.replaceAll("_", " ");

export function OrchestratorDashboard({
  projectId,
  requirementId,
  workflow,
}: {
  projectId: string;
  requirementId: string;
  workflow?: OrchestratorWorkflow;
}) {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function advance() {
    setRunning(true);
    setError(null);
    try {
      if (workflow) await orchestratorService.resume(projectId, requirementId);
      else await orchestratorService.start(projectId, requirementId);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Orchestrator failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">SA Orchestrator</p>
          <h4 className="mt-1 font-bold">{workflow ? label(workflow.current_stage) : "Not started"}</h4>
          <p className="mt-1 text-xs text-ink/55">
            {workflow?.current_agent ? `Current agent: ${label(workflow.current_agent)}` : "No specialist is currently active."}
          </p>
        </div>
        <button
          type="button"
          disabled={running || workflow?.status === "COMPLETED"}
          onClick={advance}
          className="rounded-lg bg-cyan-800 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {running ? "Running…" : workflow ? "Resume workflow" : "Start workflow"}
        </button>
      </div>

      {error ? <p role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
      {workflow ? (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Pending user action</p>
            <p className="mt-2 text-sm font-semibold text-ink/75">{workflow.pending_user_action ? label(workflow.pending_user_action) : "None"}</p>
            {workflow.last_error ? <p className="mt-2 text-xs leading-5 text-red-700">{workflow.last_error}</p> : null}
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Completed stages</p>
            <p className="mt-2 text-sm leading-6 text-ink/65">{workflow.completed_stages.length ? workflow.completed_stages.map(label).join(" · ") : "None"}</p>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Artifact status</p>
            <ul className="mt-2 space-y-1 text-xs text-ink/65">
              {Object.entries(workflow.artifact_status).map(([type, status]) => (
                <li key={type} className="flex justify-between gap-3"><span>{label(type)}</span><span className="font-semibold">v{status.version} · {status.status}</span></li>
              ))}
              {!Object.keys(workflow.artifact_status).length ? <li>None</li> : null}
            </ul>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Revision history</p>
            <ul className="mt-2 space-y-1 text-xs text-ink/65">
              {workflow.revision_history.map((item, index) => <li key={index}>#{String(item.revision ?? index + 1)} · {label(String(item.artifact ?? "artifact"))}</li>)}
              {!workflow.revision_history.length ? <li>No reviewer revision yet.</li> : null}
            </ul>
          </div>
          <div className="rounded-xl border border-cyan-100 bg-white p-4 md:col-span-2">
            <p className="text-xs font-bold uppercase tracking-wide text-ink/45">Execution history</p>
            <ol className="mt-2 grid gap-2 sm:grid-cols-2">
              {workflow.executions.slice().reverse().map((execution) => (
                <li key={execution.id} className="rounded-lg bg-ink/[0.03] px-3 py-2 text-xs">
                  <span className="font-semibold">{label(execution.stage)}</span> · {execution.status}
                </li>
              ))}
            </ol>
          </div>
        </div>
      ) : null}
    </section>
  );
}
