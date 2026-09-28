"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { artifactsService } from "@/services/artifacts";
import { discoveryAnalysisService } from "@/services/discovery-analysis";
import { designGenerationService } from "@/services/design-generation";
import { env } from "@/lib/env";
import { requirementAnalysisService } from "@/services/requirement-analysis";
import { qualityGateService } from "@/services/quality-gate";
import { requirementsService } from "@/services/requirements";
import { solutionAnalysisService } from "@/services/solution-analysis";
import { OrchestratorDashboard } from "@/features/requirements/orchestrator-dashboard";
import type { Artifact, ArtifactType, Clarification, ExistingEvidenceInput, ExistingEvidenceType, OrchestratorWorkflow, Project, QualityWorkflow, Requirement, RequirementInput, SolutionApprovalAction, SolutionWorkflow } from "@/types/api";

const fieldClass =
  "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm outline-none transition placeholder:text-ink/30 focus:border-accent focus:ring-2 focus:ring-accent/15";

const lines = (value: FormDataEntryValue | null) =>
  String(value ?? "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

const errorMessage = (error: unknown) =>
  error instanceof ApiClientError ? error.message : "The request could not be completed.";

function getResearchSources(artifact: Artifact) {
  if (artifact.artifact_type !== "RESEARCH" || !Array.isArray(artifact.content_json.sources)) {
    return [];
  }
  return artifact.content_json.sources.filter(
    (source): source is { title: string; url: string; supports: string } =>
      typeof source === "object" &&
      source !== null &&
      typeof source.title === "string" &&
      typeof source.url === "string" &&
      /^https?:\/\//.test(source.url) &&
      typeof source.supports === "string",
  );
}

const stringList = (content: Record<string, unknown>, key: string) =>
  Array.isArray(content[key]) ? content[key].filter((item): item is string => typeof item === "string") : [];

function ArtifactSection({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <div><h5 className="text-xs font-bold uppercase tracking-[0.14em] text-ink/45">{title}</h5><ul className="mt-2 space-y-1.5 text-sm leading-6 text-ink/70">{items.map((item, index) => <li key={`${title}-${index}`} className="flex gap-2"><span className="text-accent">•</span><span>{item}</span></li>)}</ul></div>;
}

export function RequirementWorkspace({
  project,
  requirements,
  artifacts,
  clarifications,
  solutionWorkflows,
  qualityWorkflows,
  orchestratorWorkflows,
}: {
  project: Project;
  requirements: Requirement[];
  artifacts: Artifact[];
  clarifications: Clarification[];
  solutionWorkflows: SolutionWorkflow[];
  qualityWorkflows: QualityWorkflow[];
  orchestratorWorkflows: OrchestratorWorkflow[];
}) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [baselineFor, setBaselineFor] = useState<string | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [existingFor, setExistingFor] = useState<string | null>(null);
  const [specialistRun, setSpecialistRun] = useState<string | null>(null);
  const [solutionRun, setSolutionRun] = useState<string | null>(null);
  const [revisionFor, setRevisionFor] = useState<string | null>(null);
  const [designRuns, setDesignRuns] = useState<string[]>([]);
  const [qualityRun, setQualityRun] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isReady = project.status === "READY_FOR_ANALYSIS";

  async function createRequirement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const payload: RequirementInput = {
      title: String(form.get("title") ?? "").trim(),
      raw_requirement: String(form.get("raw_requirement") ?? "").trim(),
      business_objective: String(form.get("business_objective") ?? "").trim() || null,
      actors: lines(form.get("actors")),
      known_rules: lines(form.get("known_rules")),
      constraints: lines(form.get("constraints")),
      dependencies: lines(form.get("dependencies")),
    };
    try {
      await requirementsService.create(project.id, payload);
      event.currentTarget.reset();
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteRequirement(requirementId: string) {
    if (!window.confirm("Delete this requirement? Linked artifacts will keep their audit history.")) return;
    setError(null);
    try {
      await requirementsService.delete(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  async function createBaseline(event: FormEvent<HTMLFormElement>, requirement: Requirement) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await artifactsService.create(project.id, {
        artifact_type: "REQUIREMENT_BASELINE",
        requirement_id: requirement.id,
        created_by: "USER",
        status: "DRAFT",
        content_json: {
          feature: String(form.get("feature") ?? "").trim(),
          business_objective: String(form.get("baseline_business_objective") ?? "").trim(),
          problem_statement: String(form.get("problem_statement") ?? "").trim(),
          actors: lines(form.get("baseline_actors")),
          known_requirements: lines(form.get("known_requirements")),
          business_rules: lines(form.get("business_rules")),
          constraints: lines(form.get("baseline_constraints")),
          dependencies: lines(form.get("baseline_dependencies")),
          assumptions: lines(form.get("assumptions")),
          unknown_information: lines(form.get("unknown_information")),
        },
      });
      setBaselineFor(null);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function analyzeRequirement(requirementId: string) {
    setAnalyzingId(requirementId);
    setError(null);
    try {
      await requirementAnalysisService.analyze(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setAnalyzingId(null);
    }
  }

  async function answerClarifications(
    event: FormEvent<HTMLFormElement>,
    requirementId: string,
    pending: Clarification[],
  ) {
    event.preventDefault();
    setAnalyzingId(requirementId);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await requirementAnalysisService.answer(
        project.id,
        requirementId,
        pending.map((item) => ({
          clarification_id: item.id,
          answer: String(form.get(`answer-${item.id}`) ?? "").trim(),
        })),
      );
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setAnalyzingId(null);
    }
  }

  async function runResearch(requirementId: string) {
    setSpecialistRun(`${requirementId}:research`);
    setError(null);
    try {
      await discoveryAnalysisService.research(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSpecialistRun(null);
    }
  }

  async function analyzeExistingSystem(
    event: FormEvent<HTMLFormElement>,
    requirementId: string,
  ) {
    event.preventDefault();
    setSpecialistRun(`${requirementId}:existing`);
    setError(null);
    const form = new FormData(event.currentTarget);
    const evidenceFields: Array<[ExistingEvidenceType, string, string]> = [
      ["USER_DESCRIPTION", "User description", "user_description"],
      ["SOURCE_CODE_METADATA", "Source code metadata", "source_code_metadata"],
      ["DATABASE_SCHEMA", "Database schema", "database_schema"],
      ["API_DOCUMENTATION", "API documentation", "api_documentation"],
      ["EXISTING_DOCUMENTATION", "Existing documentation", "existing_documentation"],
      ["SCREENSHOT_DESCRIPTION", "Screenshot description", "screenshot_description"],
    ];
    const evidence: ExistingEvidenceInput[] = evidenceFields.flatMap(
      ([source_type, title, field]) => {
        const content = String(form.get(field) ?? "").trim();
        return content ? [{ source_type, title, content }] : [];
      },
    );
    try {
      await discoveryAnalysisService.analyzeExistingSystem(project.id, requirementId, evidence);
      setExistingFor(null);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSpecialistRun(null);
    }
  }

  async function generateSolution(requirementId: string) {
    setSolutionRun(`${requirementId}:generate`);
    setError(null);
    try {
      await solutionAnalysisService.generate(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSolutionRun(null);
    }
  }

  async function actOnSolution(
    requirementId: string,
    workflow: SolutionWorkflow,
    action: SolutionApprovalAction,
    note?: string,
  ) {
    setSolutionRun(`${requirementId}:${action}`);
    setError(null);
    try {
      await solutionAnalysisService.act(
        project.id,
        requirementId,
        action,
        workflow.current_version,
        note,
      );
      setRevisionFor(null);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSolutionRun(null);
    }
  }

  async function requestRevision(
    event: FormEvent<HTMLFormElement>,
    requirementId: string,
    workflow: SolutionWorkflow,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await actOnSolution(
      requirementId,
      workflow,
      "REQUEST_REVISION",
      String(form.get("revision_note") ?? "").trim(),
    );
  }

  async function retryRevision(requirementId: string) {
    setSolutionRun(`${requirementId}:retry`);
    setError(null);
    try {
      await solutionAnalysisService.retryRevision(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSolutionRun(null);
    }
  }

  async function runDesign(
    requirementId: string,
    stage: "flow" | "prototype" | "technical",
  ) {
    const runKey = `${requirementId}:${stage}`;
    setDesignRuns((current) => [...current, runKey]);
    setError(null);
    try {
      if (stage === "flow") await designGenerationService.flow(project.id, requirementId);
      if (stage === "prototype") await designGenerationService.uiPrototype(project.id, requirementId);
      if (stage === "technical") await designGenerationService.technicalArchitecture(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setDesignRuns((current) => current.filter((item) => item !== runKey));
    }
  }

  async function runQuality(requirementId: string, stage: "qa" | "review") {
    setQualityRun(`${requirementId}:${stage}`);
    setError(null);
    try {
      if (stage === "qa") await qualityGateService.qa(project.id, requirementId);
      if (stage === "review") await qualityGateService.review(project.id, requirementId);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setQualityRun(null);
    }
  }

  async function reviseQualityArtifact(requirementId: string, artifactType: ArtifactType) {
    setQualityRun(`${requirementId}:revise:${artifactType}`);
    setError(null);
    try {
      await qualityGateService.revise(project.id, requirementId, artifactType);
      router.refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setQualityRun(null);
    }
  }

  return (
    <section className="mt-10 border-t border-ink/10 pt-10">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Requirement workspace</p>
          <h2 className="mt-2 text-2xl font-bold">Capture intent before designing a solution</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/60">
            Store the original request and known facts. Baselines are structured manually; no AI or solution generation runs in this phase.
          </p>
        </div>
        <span className="text-sm font-semibold text-ink/50">{requirements.length} requirement{requirements.length === 1 ? "" : "s"}</span>
      </div>

      {error ? <div role="alert" className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

      {!isReady ? (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          <p className="font-semibold">Requirement intake is locked.</p>
          <p className="mt-1 leading-6">Complete the project context and submit it for analysis first.</p>
        </div>
      ) : (
        <form onSubmit={createRequirement} className="mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
          <h3 className="text-lg font-bold">Add a requirement</h3>
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <label className="text-sm font-semibold">Title<input required name="title" maxLength={200} className={fieldClass} placeholder="Tiered approval" /></label>
            <label className="text-sm font-semibold">Business objective<input name="business_objective" className={fieldClass} placeholder="Reduce approval risk" /></label>
            <label className="text-sm font-semibold md:col-span-2">Raw requirement<textarea required name="raw_requirement" rows={4} className={fieldClass} placeholder="Saya ingin menambahkan proses approval bertingkat berdasarkan nominal." /></label>
            <label className="text-sm font-semibold">Actors <span className="font-normal text-ink/45">(one per line)</span><textarea name="actors" rows={3} className={fieldClass} /></label>
            <label className="text-sm font-semibold">Known rules <span className="font-normal text-ink/45">(one per line)</span><textarea name="known_rules" rows={3} className={fieldClass} /></label>
            <label className="text-sm font-semibold">Constraints <span className="font-normal text-ink/45">(one per line)</span><textarea name="constraints" rows={3} className={fieldClass} /></label>
            <label className="text-sm font-semibold">Dependencies <span className="font-normal text-ink/45">(one per line)</span><textarea name="dependencies" rows={3} className={fieldClass} /></label>
          </div>
          <div className="mt-5 flex justify-end"><button disabled={submitting} className="rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">{submitting ? "Saving…" : "Save requirement"}</button></div>
        </form>
      )}

      <div className="mt-8 space-y-4">
        {requirements.map((requirement) => {
          const baseline = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "REQUIREMENT_BASELINE");
          const requirementClarifications = clarifications.filter((item) => item.requirement_id === requirement.id);
          const pendingClarifications = requirementClarifications.filter((item) => item.status === "PENDING");
          const researchArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "RESEARCH");
          const existingArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "EXISTING_SYSTEM_ANALYSIS");
          const solutionWorkflow = solutionWorkflows.find((item) => item.requirement_id === requirement.id);
          const solutionContent = solutionWorkflow?.artifact.content_json;
          const flowArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "PROCESS_FLOW");
          const prototypeArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "UI_PROTOTYPE");
          const databaseArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "DATABASE_DESIGN");
          const apiArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "API_SPECIFICATION");
          const testArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "TEST_SCENARIO");
          const acceptanceArtifact = artifacts.find((item) => item.requirement_id === requirement.id && item.artifact_type === "ACCEPTANCE_CRITERIA");
          const qualityWorkflow = qualityWorkflows.find((item) => item.requirement_id === requirement.id);
          return (
            <article key={requirement.id} className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">{requirement.title}</h3><span className="rounded-full bg-ink/5 px-2.5 py-1 text-[11px] font-semibold">{requirement.status}</span>{requirement.analysis_readiness ? <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${requirement.analysis_readiness === "READY" ? "bg-emerald-50 text-emerald-700" : requirement.analysis_readiness === "BLOCKED" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{requirement.analysis_readiness.replaceAll("_", " ")}</span> : null}</div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink/70">{requirement.raw_requirement}</p>
                  {requirement.business_objective ? <p className="mt-2 text-sm"><span className="font-semibold">Objective:</span> {requirement.business_objective}</p> : null}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button disabled={analyzingId === requirement.id || pendingClarifications.length > 0} onClick={() => analyzeRequirement(requirement.id)} className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">{analyzingId === requirement.id ? "Analyzing…" : "Analyze with AI"}</button>
                  {!baseline ? <button onClick={() => setBaselineFor(baselineFor === requirement.id ? null : requirement.id)} className="rounded-lg border border-accent px-3 py-2 text-xs font-semibold text-accent">Structure baseline</button> : <span className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">Baseline v{baseline.version}</span>}
                  <button onClick={() => deleteRequirement(requirement.id)} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-600">Delete</button>
                </div>
              </div>

              <OrchestratorDashboard
                projectId={project.id}
                requirementId={requirement.id}
                workflow={orchestratorWorkflows.find((item) => item.requirement_id === requirement.id)}
              />

              {pendingClarifications.length ? (
                <form onSubmit={(event) => answerClarifications(event, requirement.id, pendingClarifications)} className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
                  <h4 className="font-bold text-amber-900">Clarification required</h4>
                  <p className="mt-1 text-sm text-amber-800">The workflow is paused. Answer every question to automatically run the analysis again.</p>
                  <div className="mt-4 space-y-4">
                    {pendingClarifications.map((item) => (
                      <label key={item.id} className="block text-sm font-semibold text-ink">
                        {item.question}
                        <textarea required name={`answer-${item.id}`} rows={3} className={fieldClass} placeholder="Provide a specific answer." />
                      </label>
                    ))}
                  </div>
                  <div className="mt-4 flex justify-end"><button disabled={analyzingId === requirement.id} className="rounded-xl bg-amber-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">{analyzingId === requirement.id ? "Re-analyzing…" : "Submit answers and re-analyze"}</button></div>
                </form>
              ) : null}

              {requirement.analysis_readiness === "READY" ? (
                <div className="mt-6 border-t border-ink/10 pt-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <button disabled={specialistRun !== null} onClick={() => runResearch(requirement.id)} className="rounded-lg bg-sky-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{specialistRun === `${requirement.id}:research` ? "Researching…" : researchArtifact ? `Refresh research · v${researchArtifact.version}` : "Run research"}</button>
                    <button disabled={specialistRun !== null} onClick={() => setExistingFor(existingFor === requirement.id ? null : requirement.id)} className="rounded-lg border border-violet-300 px-3 py-2 text-xs font-semibold text-violet-700 disabled:opacity-50">{existingArtifact ? `Existing analysis · v${existingArtifact.version}` : "Analyze existing system"}</button>
                    {!solutionWorkflow ? <button disabled={!researchArtifact || solutionRun !== null} onClick={() => generateSolution(requirement.id)} className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">{solutionRun === `${requirement.id}:generate` ? "Generating…" : "Generate solution"}</button> : null}
                  </div>
                  {existingFor === requirement.id ? (
                    <form onSubmit={(event) => analyzeExistingSystem(event, requirement.id)} className="mt-4 rounded-xl border border-violet-200 bg-violet-50/60 p-5">
                      <h4 className="font-bold">Existing-system evidence</h4>
                      <p className="mt-1 text-sm text-ink/55">Add only evidence you have. Project AS-IS context and the latest Research Artifact are included automatically.</p>
                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        {[
                          ["user_description", "User description"],
                          ["source_code_metadata", "Source code metadata"],
                          ["database_schema", "Database schema"],
                          ["api_documentation", "API documentation"],
                          ["existing_documentation", "Existing documentation"],
                          ["screenshot_description", "Screenshot description"],
                        ].map(([name, label]) => <label key={name} className="text-sm font-semibold">{label}<textarea name={name} rows={3} className={fieldClass} placeholder={`Paste ${label.toLowerCase()} if available.`} /></label>)}
                      </div>
                      <div className="mt-4 flex justify-end"><button disabled={specialistRun !== null} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">{specialistRun === `${requirement.id}:existing` ? "Analyzing…" : "Run existing-system analysis"}</button></div>
                    </form>
                  ) : null}

                  {solutionWorkflow && solutionContent ? (
                    <section className="mt-5 rounded-2xl border border-accent/20 bg-accent/[0.03] p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Solution v{solutionWorkflow.current_version}</p><h4 className="mt-1 font-bold">{String(solutionContent.summary ?? "Proposed solution")}</h4></div>
                        <span className={`rounded-full px-3 py-1 text-xs font-bold ${solutionWorkflow.status === "APPROVED" ? "bg-emerald-100 text-emerald-800" : solutionWorkflow.status === "REJECTED" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-900"}`}>{solutionWorkflow.status.replaceAll("_", " ")}</span>
                      </div>
                      <div className="mt-5 grid gap-5 md:grid-cols-2">
                        <ArtifactSection title="Requirement" items={stringList(baseline?.content_json ?? {}, "known_requirements")} />
                        <ArtifactSection title="Research" items={stringList(researchArtifact?.content_json ?? {}, "common_practices")} />
                        <ArtifactSection title="AS-IS" items={stringList(solutionContent, "as_is")} />
                        <ArtifactSection title="Scope" items={stringList(solutionContent, "scope")} />
                        <ArtifactSection title="Proposed solution" items={stringList(solutionContent, "proposed_process")} />
                        <ArtifactSection title="TO-BE" items={stringList(solutionContent, "to_be")} />
                        <ArtifactSection title="Functional requirements" items={stringList(solutionContent, "functional_requirements")} />
                        <ArtifactSection title="Risks" items={stringList(solutionContent, "risks")} />
                      </div>
                      {solutionWorkflow.status === "WAITING_USER_APPROVAL" ? (
                        <div className="mt-6 border-t border-accent/15 pt-5">
                          <p className="text-sm font-semibold">Human approval required</p>
                          <p className="mt-1 text-xs leading-5 text-ink/50">Technical design remains locked until this exact Solution version is approved.</p>
                          <div className="mt-4 flex flex-wrap gap-2">
                            <button disabled={solutionRun !== null} onClick={() => actOnSolution(requirement.id, solutionWorkflow, "APPROVE")} className="rounded-lg bg-emerald-700 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">Approve</button>
                            <button disabled={solutionRun !== null} onClick={() => setRevisionFor(revisionFor === requirement.id ? null : requirement.id)} className="rounded-lg border border-amber-300 px-4 py-2 text-xs font-semibold text-amber-800 disabled:opacity-50">Request revision</button>
                            <button disabled={solutionRun !== null} onClick={() => actOnSolution(requirement.id, solutionWorkflow, "REJECT")} className="rounded-lg border border-red-200 px-4 py-2 text-xs font-semibold text-red-700 disabled:opacity-50">Reject</button>
                          </div>
                          {revisionFor === requirement.id ? <form onSubmit={(event) => requestRevision(event, requirement.id, solutionWorkflow)} className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4"><label className="text-sm font-semibold">Revision note<textarea required name="revision_note" rows={3} className={fieldClass} placeholder="Explain the precise change required." /></label><div className="mt-3 flex justify-end"><button disabled={solutionRun !== null} className="rounded-lg bg-amber-700 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">Submit revision and regenerate</button></div></form> : null}
                        </div>
                      ) : null}
                      {solutionWorkflow.status === "REVISION_REQUESTED" ? <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-sm font-semibold text-amber-900">Revision is pending after an interrupted agent run.</p><p className="mt-1 text-xs leading-5 text-amber-800">The original revision note is preserved and will be reused.</p><button disabled={solutionRun !== null} onClick={() => retryRevision(requirement.id)} className="mt-3 rounded-lg bg-amber-700 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">{solutionRun === `${requirement.id}:retry` ? "Retrying…" : "Retry revision"}</button></div> : null}
                      {solutionWorkflow.approvals.length ? <div className="mt-5 border-t border-ink/10 pt-4"><p className="text-xs font-semibold uppercase tracking-wide text-ink/45">Approval history</p><ul className="mt-2 space-y-1 text-xs text-ink/55">{solutionWorkflow.approvals.map((approval) => <li key={approval.id}>{approval.action.replaceAll("_", " ")} by {approval.acted_by}{approval.note ? ` — ${approval.note}` : ""}</li>)}</ul></div> : null}

                      {solutionWorkflow.status === "APPROVED" ? <div className="mt-6 border-t border-emerald-200 pt-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-bold text-emerald-800">Approved design stage</p><p className="mt-1 text-xs text-ink/50">Flow and technical architecture can run independently. Prototype requires a generated flow.</p></div><div className="flex flex-wrap gap-2"><button disabled={designRuns.includes(`${requirement.id}:flow`)} onClick={() => runDesign(requirement.id, "flow")} className="rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{designRuns.includes(`${requirement.id}:flow`) ? "Generating flow…" : flowArtifact ? `Refresh flow · v${flowArtifact.version}` : "Generate flow"}</button><button disabled={designRuns.includes(`${requirement.id}:prototype`) || !flowArtifact} onClick={() => runDesign(requirement.id, "prototype")} className="rounded-lg bg-fuchsia-700 px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">{designRuns.includes(`${requirement.id}:prototype`) ? "Generating prototype…" : prototypeArtifact ? `Refresh prototype · v${prototypeArtifact.version}` : "Generate prototype"}</button><button disabled={designRuns.includes(`${requirement.id}:technical`)} onClick={() => runDesign(requirement.id, "technical")} className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{designRuns.includes(`${requirement.id}:technical`) ? "Designing…" : databaseArtifact && apiArtifact ? "Refresh technical design" : "Generate technical design"}</button></div></div>
                        {flowArtifact && typeof flowArtifact.content_json.mermaid === "string" ? <div className="mt-5"><p className="text-xs font-bold uppercase tracking-[0.14em] text-ink/45">Mermaid process flow · v{flowArtifact.version}</p><pre className="mt-2 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">{flowArtifact.content_json.mermaid}</pre></div> : null}
                        {prototypeArtifact && Array.isArray(prototypeArtifact.content_json.screens) ? <div className="mt-5"><p className="text-xs font-bold uppercase tracking-[0.14em] text-ink/45">Browser prototypes · v{prototypeArtifact.version}</p><div className="mt-2 flex flex-wrap gap-2">{prototypeArtifact.content_json.screens.map((screen, index) => { if (typeof screen !== "object" || screen === null || !("filename" in screen) || typeof screen.filename !== "string") return null; const url = `${env.apiBaseUrl}/projects/${project.id}/requirements/${requirement.id}/ui-prototypes/${prototypeArtifact.id}/versions/${prototypeArtifact.version}/files/${screen.filename}`; return <a key={`${screen.filename}-${index}`} href={url} target="_blank" rel="noreferrer" className="rounded-lg border border-fuchsia-200 bg-white px-3 py-2 text-xs font-semibold text-fuchsia-700 hover:bg-fuchsia-50">Open {screen.filename}</a>; })}</div></div> : null}
                        {databaseArtifact && apiArtifact ? <div className="mt-5 grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-ink/10 bg-white p-4"><p className="text-xs font-bold uppercase tracking-wide text-ink/45">Database design</p><p className="mt-2 text-sm font-semibold">{Array.isArray(databaseArtifact.content_json.entities) ? databaseArtifact.content_json.entities.length : 0} entities · v{databaseArtifact.version}</p></div><div className="rounded-xl border border-ink/10 bg-white p-4"><p className="text-xs font-bold uppercase tracking-wide text-ink/45">API specification</p><p className="mt-2 text-sm font-semibold">{Array.isArray(apiArtifact.content_json.endpoints) ? apiArtifact.content_json.endpoints.length : 0} endpoints · v{apiArtifact.version}</p></div></div> : null}
                        {flowArtifact && prototypeArtifact && databaseArtifact && apiArtifact ? (
                          <div className="mt-6 rounded-xl border border-cyan-200 bg-cyan-50/50 p-5">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div>
                                <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-800">Quality gate</p>
                                <p className="mt-1 text-sm text-ink/60">QA generates traceable tests and Given/When/Then criteria. SA Review must pass before Development Handoff.</p>
                              </div>
                              {qualityWorkflow ? <span className={`rounded-full px-3 py-1 text-xs font-bold ${qualityWorkflow.status === "PASSED" && qualityWorkflow.development_handoff_allowed ? "bg-emerald-100 text-emerald-800" : qualityWorkflow.status === "REVISION_REQUIRED" || qualityWorkflow.status === "MAX_REVISIONS_REACHED" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-900"}`}>{qualityWorkflow.status.replaceAll("_", " ")}</span> : null}
                            </div>
                            <div className="mt-4 flex flex-wrap gap-2">
                              <button disabled={qualityRun !== null || qualityWorkflow?.status === "REVISION_REQUIRED"} onClick={() => runQuality(requirement.id, "qa")} className="rounded-lg bg-cyan-800 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">{qualityRun === `${requirement.id}:qa` ? "Generating QA…" : testArtifact && acceptanceArtifact ? "Refresh QA artifacts" : "Generate QA artifacts"}</button>
                              <button disabled={qualityRun !== null || !testArtifact || !acceptanceArtifact || qualityWorkflow?.status === "REVISION_REQUIRED"} onClick={() => runQuality(requirement.id, "review")} className="rounded-lg bg-ink px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">{qualityRun === `${requirement.id}:review` ? "Reviewing…" : "Run SA Review"}</button>
                            </div>
                            {testArtifact && acceptanceArtifact ? <p className="mt-3 text-xs text-ink/55">Test Scenario v{testArtifact.version} · Acceptance Criteria v{acceptanceArtifact.version}</p> : null}
                            {qualityWorkflow ? <p className="mt-2 text-xs text-ink/55">Revision {qualityWorkflow.revision_count} of {qualityWorkflow.max_revisions} · Development Handoff {qualityWorkflow.development_handoff_allowed ? "unlocked" : "locked"}</p> : null}
                            {qualityWorkflow?.development_handoff_allowed ? <Link href={`/projects/${project.id}/requirements/${requirement.id}/handoff`} className="mt-4 inline-flex rounded-lg bg-emerald-700 px-4 py-2 text-xs font-semibold text-white">Open Development Handoff</Link> : null}
                            {qualityWorkflow?.issues.length ? (
                              <div className="mt-4 space-y-3">
                                {qualityWorkflow.issues.map((issue, index) => (
                                  <div key={`${issue.artifact}-${index}`} className="rounded-lg border border-red-200 bg-white p-4">
                                    <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold text-red-700">{issue.severity}</span><span className="text-xs font-semibold">{issue.artifact.replaceAll("_", " ")}</span></div>
                                    <p className="mt-2 text-sm font-semibold">{issue.issue}</p>
                                    <p className="mt-1 text-xs leading-5 text-ink/60">{issue.reason}</p>
                                    <p className="mt-1 text-xs leading-5 text-ink/60"><span className="font-semibold">Revision:</span> {issue.recommended_revision}</p>
                                    <button disabled={qualityRun !== null || qualityWorkflow.status === "MAX_REVISIONS_REACHED"} onClick={() => reviseQualityArtifact(requirement.id, issue.artifact)} className="mt-3 rounded-lg border border-red-300 px-3 py-2 text-xs font-semibold text-red-700 disabled:opacity-40">{qualityRun === `${requirement.id}:revise:${issue.artifact}` ? "Revising…" : `Revise ${issue.artifact.replaceAll("_", " ")}`}</button>
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div> : null}
                    </section>
                  ) : null}
                </div>
              ) : null}

              {baselineFor === requirement.id && !baseline ? (
                <form onSubmit={(event) => createBaseline(event, requirement)} className="mt-6 border-t border-ink/10 pt-6">
                  <h4 className="font-bold">Requirement baseline</h4>
                  <p className="mt-1 text-sm text-ink/55">Review every field. This form structures supplied facts only.</p>
                  <div className="mt-5 grid gap-5 md:grid-cols-2">
                    <label className="text-sm font-semibold">Feature<input required name="feature" defaultValue={requirement.title} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Business objective<input required name="baseline_business_objective" defaultValue={requirement.business_objective ?? project.business_objective} className={fieldClass} /></label>
                    <label className="text-sm font-semibold md:col-span-2">Problem statement<textarea required name="problem_statement" rows={3} defaultValue={requirement.raw_requirement} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Actors<textarea name="baseline_actors" rows={3} defaultValue={requirement.actors.join("\n")} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Known requirements<textarea name="known_requirements" rows={3} defaultValue={requirement.raw_requirement} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Business rules<textarea name="business_rules" rows={3} defaultValue={requirement.known_rules.join("\n")} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Constraints<textarea name="baseline_constraints" rows={3} defaultValue={requirement.constraints.join("\n")} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Dependencies<textarea name="baseline_dependencies" rows={3} defaultValue={requirement.dependencies.join("\n")} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Assumptions<textarea name="assumptions" rows={3} className={fieldClass} /></label>
                    <label className="text-sm font-semibold">Unknown information<textarea name="unknown_information" rows={3} className={fieldClass} /></label>
                  </div>
                  <div className="mt-5 flex justify-end"><button disabled={submitting} className="rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">Create baseline v1</button></div>
                </form>
              ) : null}
            </article>
          );
        })}
        {!requirements.length ? <div className="rounded-2xl border border-dashed border-ink/20 p-8 text-center text-sm text-ink/50">No requirements captured yet.</div> : null}
      </div>

      {artifacts.length ? (
        <div className="mt-10">
          <h3 className="text-lg font-bold">Artifact registry</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {artifacts.map((artifact) => {
              const sources = getResearchSources(artifact);
              return <div key={artifact.id} className="rounded-xl border border-ink/10 bg-white px-4 py-3 text-sm"><div className="flex justify-between gap-3"><span className="font-semibold">{artifact.artifact_type.replaceAll("_", " ")}</span><span className="text-ink/45">v{artifact.version}</span></div><p className="mt-1 text-xs text-ink/45">{artifact.status} · {artifact.created_by}</p>{sources.length ? <div className="mt-3 border-t border-ink/10 pt-3"><p className="text-xs font-semibold uppercase tracking-wide text-ink/45">Sources</p><ul className="mt-2 space-y-2">{sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer" className="font-semibold text-sky-700 underline decoration-sky-300 underline-offset-2">{source.title}</a><p className="mt-0.5 text-xs leading-5 text-ink/55">{source.supports}</p></li>)}</ul></div> : null}</div>;
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
