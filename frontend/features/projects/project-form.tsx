"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { projectsService } from "@/services/projects";
import type { Project, ProjectInput, ProjectType } from "@/types/api";

import { projectTypeDescriptions, projectTypeLabels } from "./project-meta";

type Draft = {
  name: string;
  description: string;
  businessObjective: string;
  currentFlow: string;
  currentActors: string;
  currentRules: string;
  currentProblem: string;
  requestedChange: string;
  constraints: string;
  notes: string;
};

const fieldClass = "mt-2 w-full rounded-lg border border-ink/15 bg-white px-3.5 py-3 text-sm leading-6 outline-none placeholder:text-ink/25 focus:border-accent focus:ring-2 focus:ring-accent/10";

const initialDraft = (project?: Project): Draft => ({
  name: project?.name ?? "",
  description: project?.description ?? "",
  businessObjective: project?.business_objective ?? "",
  currentFlow: project?.context.current_flow ?? "",
  currentActors: project?.context.current_actors ?? "",
  currentRules: project?.context.current_rules ?? "",
  currentProblem: project?.context.current_problem ?? "",
  requestedChange: project?.context.requested_change ?? "",
  constraints: project?.context.constraints ?? "",
  notes: project?.context.notes ?? "",
});

function IntakePrompt({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="flex gap-3 border-b border-ink/10 pb-5"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-ink text-xs font-bold text-white">S</span><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent">{eyebrow}</p><h2 className="mt-1 text-xl font-semibold tracking-tight">{title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-ink/50">{description}</p></div></div>;
}

function ReviewItem({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) {
  return <div className="border-b border-ink/10 py-4 last:border-b-0"><div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink/35">{label}</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-ink/75">{value || "—"}</p></div><button type="button" onClick={onEdit} className="shrink-0 text-xs font-semibold text-accent hover:underline">Ubah</button></div></div>;
}

export function ProjectForm({ project }: { project?: Project }) {
  const router = useRouter();
  const [projectType, setProjectType] = useState<ProjectType>(project?.project_type ?? "NEW_SYSTEM");
  const [draft, setDraft] = useState<Draft>(() => initialDraft(project));
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const enhancement = projectType === "ENHANCEMENT";
  const steps = enhancement
    ? ["Jenis pekerjaan", "Tujuan", "Kondisi saat ini", "Pendukung", "Konfirmasi"]
    : ["Jenis pekerjaan", "Tujuan", "Pendukung", "Konfirmasi"];
  const finalStep = steps.length - 1;
  const set = (key: keyof Draft, value: string) => setDraft((current) => ({ ...current, [key]: value }));

  function validateAndContinue() {
    setError(null);
    if (step === 1 && (!draft.name.trim() || !draft.description.trim() || !draft.businessObjective.trim())) {
      setError("Lengkapi nama proyek, cerita kebutuhan, dan hasil bisnis yang ingin dicapai.");
      return;
    }
    if (enhancement && step === 2 && [draft.currentFlow, draft.currentActors, draft.currentRules, draft.currentProblem, draft.requestedChange].some((value) => !value.trim())) {
      setError("Lengkapi seluruh kondisi sistem saat ini agar analis tidak membuat asumsi.");
      return;
    }
    setStep((current) => Math.min(current + 1, finalStep));
  }

  async function save() {
    setSubmitting(true);
    setError(null);
    const nullable = (value: string) => value.trim() || null;
    const payload: ProjectInput = {
      name: draft.name.trim(),
      description: draft.description.trim(),
      project_type: projectType,
      business_objective: draft.businessObjective.trim(),
      context: {
        current_flow: enhancement ? nullable(draft.currentFlow) : null,
        current_actors: enhancement ? nullable(draft.currentActors) : null,
        current_rules: enhancement ? nullable(draft.currentRules) : null,
        current_problem: enhancement ? nullable(draft.currentProblem) : null,
        requested_change: enhancement ? nullable(draft.requestedChange) : null,
        constraints: nullable(draft.constraints),
        notes: nullable(draft.notes),
      },
    };
    try {
      const saved = project ? await projectsService.update(project.id, payload) : await projectsService.create(payload);
      router.push(`/projects/${saved.id}/details`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Proyek tidak dapat disimpan. Silakan coba lagi.");
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[190px_minmax(0,1fr)]">
      <aside className="h-fit lg:sticky lg:top-24">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink/35">Progres intake</p>
        <ol className="mt-4 space-y-1">
          {steps.map((label, index) => <li key={label}><button type="button" disabled={index > step} onClick={() => index <= step && setStep(index)} className={`flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-xs ${index === step ? "bg-white font-semibold text-ink" : index < step ? "text-ink/60" : "cursor-not-allowed text-ink/25"}`}><span className={`grid h-6 w-6 place-items-center rounded-full text-[10px] font-bold ${index < step ? "bg-[#246b5a] text-white" : index === step ? "bg-ink text-white" : "border border-ink/15"}`}>{index < step ? "✓" : index + 1}</span>{label}</button></li>)}
        </ol>
        <p className="mt-5 border-l border-ink/15 pl-3 text-[11px] leading-5 text-ink/40">Jawaban tersimpan setelah Anda memeriksa dan mengonfirmasi rangkuman.</p>
      </aside>

      <section className="min-w-0 border border-ink/10 bg-white/60 p-5 sm:p-7">
        {error ? <div role="alert" className="mb-5 border-l-2 border-red-500 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        {step === 0 ? <div><IntakePrompt eyebrow="Pertanyaan 1" title="Pekerjaan apa yang ingin Anda mulai?" description="Pilihan ini menentukan pertanyaan lanjutan dan referensi yang perlu disiapkan." /><div className="mt-6 grid gap-3 sm:grid-cols-3">{(Object.keys(projectTypeLabels) as ProjectType[]).map((type) => <button key={type} type="button" onClick={() => setProjectType(type)} className={`min-h-36 rounded-lg border p-4 text-left ${projectType === type ? "border-accent bg-[#fff8f4] ring-1 ring-accent/15" : "border-ink/10 bg-white hover:border-ink/25"}`}><span className="text-sm font-semibold">{projectTypeLabels[type]}</span><span className="mt-2 block text-xs font-normal leading-5 text-ink/45">{projectTypeDescriptions[type]}</span></button>)}</div></div> : null}

        {step === 1 ? <div><IntakePrompt eyebrow="Pertanyaan 2" title="Ceritakan kebutuhan Anda dengan bahasa sehari-hari." description="Belum perlu memakai istilah teknis. Jelaskan masalah, perubahan yang diharapkan, dan hasil bisnisnya." /><div className="mt-6 space-y-5"><label className="block text-sm font-semibold">Apa nama singkat pekerjaan ini?<input value={draft.name} onChange={(event) => set("name", event.target.value)} maxLength={200} className={fieldClass} placeholder="Contoh: Persetujuan pembelian berjenjang" /></label><label className="block text-sm font-semibold">Apa yang terjadi dan apa yang ingin diubah?<textarea value={draft.description} onChange={(event) => set("description", event.target.value)} rows={5} className={fieldClass} placeholder="Ceritakan situasi dan kebutuhan stakeholder seperti saat menjelaskan kepada seorang analis." /></label><label className="block text-sm font-semibold">Hasil bisnis apa yang ingin dicapai?<textarea value={draft.businessObjective} onChange={(event) => set("businessObjective", event.target.value)} rows={3} className={fieldClass} placeholder="Contoh: menurunkan waktu persetujuan 30% dan memastikan transaksi berisiko ditinjau Finance." /></label></div></div> : null}

        {enhancement && step === 2 ? <div><IntakePrompt eyebrow="Pertanyaan 3" title="Bantu saya memahami sistem yang berjalan sekarang." description="Jawaban konkret mencegah analis mengganti perilaku lama secara tidak sengaja." /><div className="mt-6 grid gap-5 sm:grid-cols-2"><label className="block text-sm font-semibold">Bagaimana alurnya saat ini?<textarea value={draft.currentFlow} onChange={(event) => set("currentFlow", event.target.value)} rows={4} className={fieldClass} placeholder="Jelaskan dari awal sampai selesai." /></label><label className="block text-sm font-semibold">Siapa saja yang terlibat?<textarea value={draft.currentActors} onChange={(event) => set("currentActors", event.target.value)} rows={4} className={fieldClass} placeholder="Pengguna, approver, admin, atau sistem lain." /></label><label className="block text-sm font-semibold">Aturan apa yang berlaku?<textarea value={draft.currentRules} onChange={(event) => set("currentRules", event.target.value)} rows={4} className={fieldClass} placeholder="Validasi, batas, keputusan, dan pengecualian." /></label><label className="block text-sm font-semibold">Apa masalah utamanya?<textarea value={draft.currentProblem} onChange={(event) => set("currentProblem", event.target.value)} rows={4} className={fieldClass} placeholder="Apa yang lambat, gagal, atau menimbulkan risiko?" /></label><label className="block text-sm font-semibold sm:col-span-2">Perubahan apa yang diminta?<textarea value={draft.requestedChange} onChange={(event) => set("requestedChange", event.target.value)} rows={4} className={fieldClass} placeholder="Fokus pada kebutuhan, belum perlu menentukan teknologi atau desain." /></label></div></div> : null}

        {step === (enhancement ? 3 : 2) ? <div><IntakePrompt eyebrow={enhancement ? "Pertanyaan 4" : "Pertanyaan 3"} title="Adakah batasan atau konteks lain yang harus dihormati?" description={enhancement ? "Setelah proyek disimpan, Anda juga akan diminta mengunggah screenshot UI, source code, atau dokumentasi sistem lama." : "Bagian ini opsional, tetapi membantu analis membuat pertanyaan yang lebih tepat."} /><div className="mt-6 grid gap-5 sm:grid-cols-2"><label className="block text-sm font-semibold">Batasan<textarea value={draft.constraints} onChange={(event) => set("constraints", event.target.value)} rows={5} className={fieldClass} placeholder="Waktu, anggaran, regulasi, platform, atau kebijakan." /></label><label className="block text-sm font-semibold">Catatan tambahan<textarea value={draft.notes} onChange={(event) => set("notes", event.target.value)} rows={5} className={fieldClass} placeholder="Konteks lain yang perlu diketahui analis." /></label></div>{enhancement ? <div className="mt-5 border-l-2 border-amber-500 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900"><strong>Referensi wajib setelah penyimpanan:</strong> minimal satu screenshot UI, source code, dokumen API, skema database, atau dokumen proses.</div> : null}</div> : null}

        {step === finalStep ? <div><IntakePrompt eyebrow="Verifikasi pemahaman" title="Apakah rangkuman ini sudah benar?" description="Periksa kembali sebelum disimpan. Anda tetap menjadi pihak yang mengonfirmasi konteks, bukan sistem." /><div className="mt-6 border-y border-ink/10"><ReviewItem label="Jenis pekerjaan" value={projectTypeLabels[projectType]} onEdit={() => setStep(0)} /><ReviewItem label="Nama proyek" value={draft.name} onEdit={() => setStep(1)} /><ReviewItem label="Kebutuhan" value={draft.description} onEdit={() => setStep(1)} /><ReviewItem label="Tujuan bisnis" value={draft.businessObjective} onEdit={() => setStep(1)} />{enhancement ? <><ReviewItem label="Alur saat ini" value={draft.currentFlow} onEdit={() => setStep(2)} /><ReviewItem label="Aktor dan aturan" value={`${draft.currentActors}\n\n${draft.currentRules}`} onEdit={() => setStep(2)} /><ReviewItem label="Masalah dan perubahan" value={`${draft.currentProblem}\n\n${draft.requestedChange}`} onEdit={() => setStep(2)} /></> : null}<ReviewItem label="Batasan dan catatan" value={[draft.constraints, draft.notes].filter(Boolean).join("\n\n")} onEdit={() => setStep(enhancement ? 3 : 2)} /></div><div className="mt-5 bg-[#edf5f2] px-4 py-3 text-xs leading-5 text-[#245647]"><strong>Konfirmasi pengguna:</strong> Informasi di atas akan menjadi dasar pertanyaan requirement dan analisis berikutnya. Belum ada solusi teknis yang diputuskan pada tahap ini.</div></div> : null}

        <div className="mt-7 flex items-center justify-between border-t border-ink/10 pt-5"><button type="button" disabled={step === 0 || submitting} onClick={() => { setError(null); setStep((current) => Math.max(0, current - 1)); }} className="rounded-lg px-3 py-2 text-sm font-semibold text-ink/50 hover:bg-canvas disabled:opacity-0">← Kembali</button>{step < finalStep ? <button type="button" onClick={validateAndContinue} className="rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white hover:bg-ink/90">Lanjutkan →</button> : <button type="button" disabled={submitting} onClick={save} className="rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#bd4524] disabled:opacity-50">{submitting ? "Menyimpan…" : project ? "Konfirmasi perubahan" : "Konfirmasi dan buat proyek"}</button>}</div>
      </section>
    </div>
  );
}
