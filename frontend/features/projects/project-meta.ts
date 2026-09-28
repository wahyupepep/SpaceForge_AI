import type { ProjectStatus, ProjectType } from "@/types/api";

export const projectTypeLabels: Record<ProjectType, string> = {
  NEW_SYSTEM: "New system",
  NEW_FEATURE: "New feature",
  ENHANCEMENT: "Enhancement",
};

export const projectTypeDescriptions: Record<ProjectType, string> = {
  NEW_SYSTEM: "Build a new system as a whole.",
  NEW_FEATURE: "Add a new menu, module, or capability.",
  ENHANCEMENT: "Change an existing feature or process. AS-IS context is mandatory.",
};

export const projectStatusLabels: Record<ProjectStatus, string> = {
  DRAFT: "Draft",
  CONTEXT_INCOMPLETE: "Context incomplete",
  READY_FOR_ANALYSIS: "Ready for analysis",
};

export const projectStatusClasses: Record<ProjectStatus, string> = {
  DRAFT: "bg-ink/5 text-ink/65",
  CONTEXT_INCOMPLETE: "bg-amber-100 text-amber-800",
  READY_FOR_ANALYSIS: "bg-emerald-100 text-emerald-800",
};

export const contextFieldLabels: Record<string, string> = {
  current_flow: "Current flow",
  current_actors: "Current actors",
  current_rules: "Current business rules",
  current_problem: "Current problem",
  requested_change: "Requested change",
};

