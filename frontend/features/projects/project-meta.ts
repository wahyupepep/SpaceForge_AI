import type { ProjectStatus, ProjectType } from "@/types/api";

export const projectTypeLabels: Record<ProjectType, string> = {
  NEW_SYSTEM: "Sistem baru",
  NEW_FEATURE: "Fitur baru",
  ENHANCEMENT: "Peningkatan produk",
};

export const projectTypeDescriptions: Record<ProjectType, string> = {
  NEW_SYSTEM: "Membangun sistem baru secara utuh.",
  NEW_FEATURE: "Menambahkan kemampuan baru beserta batasan dan dependensinya.",
  ENHANCEMENT: "Meningkatkan produk yang sudah ada. Konteks AS-IS dan referensi nyata wajib disertakan.",
};

export const projectStatusLabels: Record<ProjectStatus, string> = {
  DRAFT: "Draf",
  CONTEXT_INCOMPLETE: "Konteks belum lengkap",
  READY_FOR_ANALYSIS: "Siap dianalisis",
};

export const projectStatusClasses: Record<ProjectStatus, string> = {
  DRAFT: "bg-ink/5 text-ink/65",
  CONTEXT_INCOMPLETE: "bg-amber-100 text-amber-800",
  READY_FOR_ANALYSIS: "bg-emerald-100 text-emerald-800",
};

export const contextFieldLabels: Record<string, string> = {
  current_flow: "Alur saat ini",
  current_actors: "Aktor saat ini",
  current_rules: "Aturan bisnis saat ini",
  current_problem: "Masalah saat ini",
  requested_change: "Perubahan yang diminta",
  reference_evidence: "Screenshot UI, source code, atau referensi sistem yang sudah ada",
};

