"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { projectsService } from "@/services/projects";
import type { Project, ProjectContextInput, ProjectInput, ProjectType } from "@/types/api";

import { projectTypeDescriptions, projectTypeLabels } from "./project-meta";

const fieldClass =
  "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm outline-none transition placeholder:text-ink/30 focus:border-accent focus:ring-2 focus:ring-accent/15";

const emptyContext: ProjectContextInput = {
  current_flow: null,
  current_actors: null,
  current_rules: null,
  current_problem: null,
  requested_change: null,
  constraints: null,
  notes: null,
};

export function ProjectForm({ project }: { project?: Project }) {
  const router = useRouter();
  const [projectType, setProjectType] = useState<ProjectType>(project?.project_type ?? "NEW_SYSTEM");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const form = new FormData(event.currentTarget);
    const text = (name: string) => {
      const value = String(form.get(name) ?? "").trim();
      return value || null;
    };
    const payload: ProjectInput = {
      name: String(form.get("name") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      project_type: projectType,
      business_objective: String(form.get("business_objective") ?? "").trim(),
      context: {
        ...emptyContext,
        current_flow: text("current_flow"),
        current_actors: text("current_actors"),
        current_rules: text("current_rules"),
        current_problem: text("current_problem"),
        requested_change: text("requested_change"),
        constraints: text("constraints"),
        notes: text("notes"),
      },
    };

    try {
      const saved = project
        ? await projectsService.update(project.id, payload)
        : await projectsService.create(payload);
      router.push(`/projects/${saved.id}`);
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof ApiClientError ? caught.message : "Project could not be saved. Try again.",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {error ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Core context</p>
        <h2 className="mt-2 text-xl font-bold">What are we working on?</h2>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <label className="text-sm font-semibold text-ink">
            Project name
            <input name="name" required maxLength={200} defaultValue={project?.name} className={fieldClass} placeholder="e.g. Tiered approval" />
          </label>
          <label className="text-sm font-semibold text-ink">
            Work type
            <select name="project_type" value={projectType} onChange={(event) => setProjectType(event.target.value as ProjectType)} className={fieldClass}>
              {(Object.keys(projectTypeLabels) as ProjectType[]).map((type) => (
                <option key={type} value={type}>{projectTypeLabels[type]}</option>
              ))}
            </select>
            <span className="mt-2 block text-xs font-normal leading-5 text-ink/50">{projectTypeDescriptions[projectType]}</span>
          </label>
          <label className="text-sm font-semibold text-ink md:col-span-2">
            Description
            <textarea name="description" required rows={4} defaultValue={project?.description} className={fieldClass} placeholder="Describe the initiative and its boundaries." />
          </label>
          <label className="text-sm font-semibold text-ink md:col-span-2">
            Business objective
            <textarea name="business_objective" required rows={3} defaultValue={project?.business_objective} className={fieldClass} placeholder="What measurable business outcome should this work achieve?" />
          </label>
        </div>
      </section>

      {projectType === "ENHANCEMENT" ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50/50 p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Required AS-IS</p>
          <h2 className="mt-2 text-xl font-bold">Document the current state before TO-BE</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/60">All five fields are required before this enhancement can move to requirement analysis.</p>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            {[
              ["current_flow", "Current flow", "Describe the process from start to finish."],
              ["current_actors", "Current actors", "Who participates, owns decisions, or receives outcomes?"],
              ["current_rules", "Current business rules", "List validations, decisions, limits, and exceptions."],
              ["current_problem", "Current problem", "What fails, slows down, or creates risk today?"],
              ["requested_change", "Requested change", "What should change without designing the full solution?"],
            ].map(([name, label, placeholder]) => (
              <label key={name} className={`text-sm font-semibold text-ink ${name === "requested_change" ? "md:col-span-2" : ""}`}>
                {label} <span className="text-amber-700">*</span>
                <textarea name={name} required rows={4} defaultValue={project?.context[name as keyof ProjectContextInput] ?? ""} className={fieldClass} placeholder={placeholder} />
              </label>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded-2xl border border-ink/10 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-bold">Constraints and notes</h2>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <label className="text-sm font-semibold text-ink">
            Constraints
            <textarea name="constraints" rows={4} defaultValue={project?.context.constraints ?? ""} className={fieldClass} placeholder="Timeline, compliance, platform, budget, or policy constraints." />
          </label>
          <label className="text-sm font-semibold text-ink">
            Notes
            <textarea name="notes" rows={4} defaultValue={project?.context.notes ?? ""} className={fieldClass} placeholder="Supporting context that does not fit elsewhere." />
          </label>
        </div>
      </section>

      <div className="flex justify-end">
        <button type="submit" disabled={submitting} className="rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-orange-600 disabled:cursor-wait disabled:opacity-60">
          {submitting ? "Saving…" : project ? "Save changes" : "Create draft"}
        </button>
      </div>
    </form>
  );
}

