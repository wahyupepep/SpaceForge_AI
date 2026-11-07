const labels: Record<string, string> = {
  DRAFT: "Draf", VALIDATED: "Tervalidasi", READY: "Siap", BLOCKED: "Terhambat",
  NEEDS_CLARIFICATION: "Perlu klarifikasi", BASELINED: "Baseline selesai",
  WAITING_USER_APPROVAL: "Menunggu persetujuan pengguna", REVISION_REQUESTED: "Revisi diminta",
  APPROVED: "Disetujui", REJECTED: "Ditolak", READY_FOR_REVIEW: "Siap ditinjau",
  REVISION_REQUIRED: "Perlu revisi", PASSED: "Lolos", MAX_REVISIONS_REACHED: "Batas revisi tercapai",
  LOW: "Rendah", MEDIUM: "Sedang", HIGH: "Tinggi", CRITICAL: "Kritis",
  UI_SCREENSHOT: "Screenshot UI", SOURCE_CODE: "Source code", API_DOCUMENTATION: "Dokumentasi API",
  DATABASE_SCHEMA: "Skema database", PROCESS_DOCUMENT: "Dokumen proses", OTHER: "Lainnya",
  REQUIREMENT_BASELINE: "Baseline requirement", RESEARCH: "Riset",
  EXISTING_SYSTEM_ANALYSIS: "Analisis sistem lama", SOLUTION: "Solusi", PROCESS_FLOW: "Alur proses",
  UI_PROTOTYPE: "Prototipe UI", DATABASE_DESIGN: "Desain database",
  API_SPECIFICATION: "Spesifikasi API", TEST_SCENARIO: "Skenario pengujian",
  ACCEPTANCE_CRITERIA: "Kriteria penerimaan", DEVELOPMENT_TASK: "Task pengembangan",
  APPROVE: "Disetujui", REQUEST_REVISION: "Meminta revisi", REJECT: "Ditolak",
  PENDING: "Menunggu", RUNNING: "Berjalan", COMPLETED: "Selesai", FAILED: "Gagal",
};

export const uiLabel = (value: string) => labels[value] ?? value.replaceAll("_", " ");
