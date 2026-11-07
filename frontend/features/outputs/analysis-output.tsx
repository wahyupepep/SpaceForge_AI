"use client";

import { useState } from "react";

import { env } from "@/lib/env";
import type { Artifact, Project, ProjectEvidence, Requirement } from "@/types/api";

type Task = {
  id: string;
  title: string;
  objective: string;
  scope: string[];
  acceptance: string[];
};

const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

const objects = (value: unknown): Record<string, unknown>[] =>
  Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    : [];

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1800);
      }}
      className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-xs font-bold text-ink/70 hover:border-accent hover:text-accent"
    >
      {copied ? "Sudah disalin" : "Salin prompt"}
    </button>
  );
}

export function AnalysisOutput({
  project,
  requirement,
  artifacts,
  evidence,
}: {
  project: Project;
  requirement: Requirement;
  artifacts: Artifact[];
  evidence: ProjectEvidence[];
}) {
  const artifact = (type: Artifact["artifact_type"]) => artifacts.find((item) => item.artifact_type === type);
  const baseline = artifact("REQUIREMENT_BASELINE")?.content_json ?? {};
  const existing = artifact("EXISTING_SYSTEM_ANALYSIS")?.content_json ?? {};
  const research = artifact("RESEARCH")?.content_json ?? {};
  const solution = artifact("SOLUTION")?.content_json ?? {};
  const storedTasks = objects(artifact("DEVELOPMENT_TASK")?.content_json.tasks);
  const storedCriteria = objects(artifact("ACCEPTANCE_CRITERIA")?.content_json.criteria);
  const storedTests = objects(artifact("TEST_SCENARIO")?.content_json.test_cases);
  const knownRequirements = list(baseline.known_requirements).length
    ? list(baseline.known_requirements)
    : [requirement.raw_requirement];
  const rules = list(baseline.business_rules).length ? list(baseline.business_rules) : requirement.known_rules;
  const uiImage = evidence.find((item) => item.category === "UI_SCREENSHOT" && item.content_type.startsWith("image/"));

  const generatedTasks: Task[] = knownRequirements.slice(0, 6).map((item, index) => ({
    id: `DEV-${String(index + 1).padStart(3, "0")}`,
    title: index === 0 ? "Bangun fondasi alur persetujuan" : `Implementasi kebutuhan ${index + 1}`,
    objective: item,
    scope: index === 0
      ? ["Model data dan aturan bisnis", "Layanan backend", "Tampilan status untuk pengguna"]
      : ["Implementasi aturan", "Validasi dan penanganan kesalahan", "Unit test dan audit log"],
    acceptance: [`AC-${String(index + 1).padStart(3, "0")}`],
  }));
  const tasks: Task[] = storedTasks.length
    ? storedTasks.map((item, index) => ({
        id: String(item.id ?? `DEV-${index + 1}`),
        title: String(item.title ?? "Task pengembangan"),
        objective: String(item.objective ?? item.requirement ?? ""),
        scope: list(item.scope),
        acceptance: list(item.acceptance_criteria),
      }))
    : generatedTasks;

  const criteria = storedCriteria.length
    ? storedCriteria.map((item, index) => ({
        id: String(item.id ?? `AC-${index + 1}`),
        given: String(item.given ?? ""),
        when: String(item.when ?? ""),
        then: String(item.then ?? ""),
      }))
    : knownRequirements.slice(0, 6).map((item, index) => ({
        id: `AC-${String(index + 1).padStart(3, "0")}`,
        given: `Pengguna memiliki hak akses dan data yang diperlukan untuk: ${item}`,
        when: "Pengguna menjalankan proses sesuai alur yang disepakati",
        then: `Sistem menyelesaikan kebutuhan tersebut, mencatat hasil, dan tidak melanggar aturan bisnis terkait`,
      }));

  const tests = storedTests.length
    ? storedTests.map((item, index) => ({
        id: String(item.id ?? `TC-${index + 1}`),
        scenario: String(item.scenario ?? ""),
        precondition: String(item.precondition ?? ""),
        steps: list(item.steps),
        expected: String(item.expected_result ?? ""),
      }))
    : criteria.map((item, index) => ({
        id: `TC-${String(index + 1).padStart(3, "0")}`,
        scenario: `Verifikasi ${item.id}: ${knownRequirements[index] ?? requirement.title}`,
        precondition: item.given,
        steps: ["Masuk sebagai aktor yang sesuai", "Siapkan data uji pada batas aturan", "Jalankan aksi utama", "Periksa status dan riwayat"],
        expected: item.then,
      }));

  const prompt = `Anda adalah senior software engineer. Implementasikan enhancement \"${requirement.title}\" pada produk ${project.name}.

Tujuan bisnis:
${String(baseline.business_objective ?? requirement.business_objective ?? project.business_objective)}

Kebutuhan wajib:
${knownRequirements.map((item, index) => `${index + 1}. ${item}`).join("\n")}

Aturan bisnis:
${rules.map((item) => `- ${item}`).join("\n")}

Batasan:
${list(baseline.constraints).map((item) => `- ${item}`).join("\n")}

Kondisi sistem saat ini:
${String(existing.as_is_summary ?? "Ikuti source code dan dokumentasi yang terlampir di workspace.")}

Instruksi implementasi:
- Pertahankan kompatibilitas fitur lama dan kontrak integrasi yang sudah berjalan.
- Kerjakan task sesuai urutan DEV dan penuhi acceptance criteria terkait.
- Tambahkan validasi, audit trail, penanganan konkurensi, dan idempotensi bila relevan.
- Tambahkan unit test dan integration test untuk jalur utama, batas nilai, error, dan regresi.
- Jangan mengubah kebutuhan. Jika ada informasi yang belum jelas, berhenti dan tuliskan pertanyaan klarifikasi.
- Setelah selesai, tampilkan daftar file yang berubah, keputusan teknis, cara migrasi, dan hasil pengujian.`;

  const nav = [
    ["ui", "1. Gambar UI"],
    ["requirements", "2. Requirement & task"],
    ["prompt", "3. Prompt vibe coding"],
    ["tests", "4. Test case"],
    ["technical", "5. Dokumen teknis"],
  ];

  return (
    <div className="mt-8 grid gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="h-fit rounded-2xl border border-ink/10 bg-white p-4 shadow-sm lg:sticky lg:top-6">
        <p className="px-3 text-xs font-bold uppercase tracking-[0.16em] text-ink/45">Daftar hasil</p>
        <nav className="mt-3 space-y-1">
          {nav.map(([id, label]) => <a key={id} href={`#${id}`} className="block rounded-lg px-3 py-2 text-sm font-semibold text-ink/65 hover:bg-orange-50 hover:text-accent">{label}</a>)}
        </nav>
        <div className="mt-4 rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">
          Hasil ini dibuat dari data proyek yang tersimpan dan dapat dibuka kembali kapan saja.
        </div>
      </aside>

      <main className="min-w-0 space-y-8">
        <section id="ui" className="scroll-mt-6 overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-sm">
          <div className="border-b border-ink/10 p-6"><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Output 1</p><h2 className="mt-1 text-2xl font-bold">Gambar rancangan UI</h2><p className="mt-2 text-sm text-ink/55">Acuan visual untuk menyamakan pemahaman analyst, developer, dan stakeholder.</p></div>
          {uiImage ? <div className="bg-slate-100 p-4 sm:p-6"><a href={`${env.apiBaseUrl}/projects/${project.id}/evidence/${uiImage.id}/download`} target="_blank" rel="noreferrer">
            {/* Gambar berasal dari evidence privat yang memerlukan cookie sesi, sehingga tidak dapat memakai optimizer publik Next Image. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${env.apiBaseUrl}/projects/${project.id}/evidence/${uiImage.id}/download`} alt={uiImage.title} className="w-full rounded-xl border border-ink/10 bg-white shadow-lg" />
          </a><p className="mt-3 text-center text-xs text-ink/50">Klik gambar untuk melihat ukuran penuh · {uiImage.original_filename}</p></div> : <div className="m-6 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-8 text-center text-sm text-amber-900">Belum ada gambar UI. Unggah screenshot berkategori <strong>Screenshot UI</strong> pada bagian referensi proyek.</div>}
        </section>

        <section id="requirements" className="scroll-mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Output 2</p><h2 className="mt-1 text-2xl font-bold">Requirement, task, dan acceptance criteria</h2>
          <div className="mt-6 rounded-xl bg-ink/[0.03] p-5"><h3 className="font-bold">Tujuan bisnis</h3><p className="mt-2 text-sm leading-6 text-ink/65">{String(baseline.business_objective ?? requirement.business_objective ?? project.business_objective)}</p></div>
          <h3 className="mt-7 font-bold">Kebutuhan fungsional</h3><ol className="mt-3 space-y-2">{knownRequirements.map((item, index) => <li key={item} className="flex gap-3 rounded-lg border border-ink/10 p-3 text-sm leading-6"><span className="font-bold text-accent">REQ-{String(index + 1).padStart(3, "0")}</span><span>{item}</span></li>)}</ol>
          <h3 className="mt-8 font-bold">Rincian task developer</h3><div className="mt-3 space-y-4">{tasks.map((task) => <article key={task.id} className="rounded-xl border border-ink/10 p-5"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-ink px-2.5 py-1 text-[11px] font-bold text-white">{task.id}</span><h4 className="font-bold">{task.title}</h4></div><p className="mt-3 text-sm leading-6 text-ink/65">{task.objective}</p><ul className="mt-3 grid gap-2 text-xs text-ink/60 sm:grid-cols-2">{task.scope.map((item) => <li key={item}>• {item}</li>)}</ul><p className="mt-3 text-xs font-semibold text-accent">Acuan: {task.acceptance.join(", ")}</p></article>)}</div>
          <h3 className="mt-8 font-bold">Acceptance criteria</h3><div className="mt-3 space-y-3">{criteria.map((item) => <article key={item.id} className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 text-sm"><p className="font-bold text-emerald-800">{item.id}</p><p className="mt-2"><strong>Given:</strong> {item.given}</p><p className="mt-1"><strong>When:</strong> {item.when}</p><p className="mt-1"><strong>Then:</strong> {item.then}</p></article>)}</div>
        </section>

        <section id="prompt" className="scroll-mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Output 3</p><h2 className="mt-1 text-2xl font-bold">Prompt untuk vibe coding</h2><p className="mt-2 text-sm text-ink/55">Salin prompt ini ke coding agent. Konteks bisnis dan batas implementasi sudah disertakan.</p></div><CopyButton value={prompt} /></div><pre className="mt-5 max-h-[560px] overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-5 text-xs leading-6 text-slate-100">{prompt}</pre></section>

        <section id="tests" className="scroll-mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Output 4</p><h2 className="mt-1 text-2xl font-bold">Test case untuk tester</h2><div className="mt-6 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-ink text-white"><tr><th className="p-3">ID</th><th className="p-3">Skenario</th><th className="p-3">Prakondisi</th><th className="p-3">Langkah uji</th><th className="p-3">Hasil yang diharapkan</th></tr></thead><tbody>{tests.map((item) => <tr key={item.id} className="border-b border-ink/10 align-top"><td className="p-3 font-bold text-accent">{item.id}</td><td className="p-3 font-semibold">{item.scenario}</td><td className="p-3">{item.precondition}</td><td className="p-3"><ol className="list-decimal space-y-1 pl-4">{item.steps.map((step) => <li key={step}>{step}</li>)}</ol></td><td className="p-3">{item.expected}</td></tr>)}</tbody></table></div></section>

        <section id="technical" className="scroll-mt-6 rounded-2xl border border-ink/10 bg-white p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">Output 5</p><h2 className="mt-1 text-2xl font-bold">Dokumen teknis pengembangan</h2><div className="mt-6 space-y-6 text-sm leading-6 text-ink/70"><div><h3 className="font-bold text-ink">Ringkasan sistem saat ini</h3><p className="mt-2">{String(existing.as_is_summary ?? "Belum ada analisis sistem lama yang tersimpan.")}</p></div><div><h3 className="font-bold text-ink">Komponen terdampak</h3><ul className="mt-2 grid gap-2 sm:grid-cols-2">{list(existing.affected_components).map((item) => <li key={item} className="rounded-lg bg-ink/[0.03] px-3 py-2">• {item}</li>)}</ul></div><div><h3 className="font-bold text-ink">Pertimbangan teknis</h3><ul className="mt-2 space-y-2">{list(research.technical_considerations).map((item) => <li key={item}>• {item}</li>)}</ul></div><div><h3 className="font-bold text-ink">Dependensi</h3><p className="mt-2">{list(baseline.dependencies).join(", ") || "Tidak ada dependensi yang dicatat."}</p></div><div><h3 className="font-bold text-ink">Risiko regresi</h3><ul className="mt-2 space-y-2">{list(existing.regression_risks).map((item) => <li key={item}>• {item}</li>)}</ul></div>{String(solution.summary ?? "") ? <div><h3 className="font-bold text-ink">Rancangan solusi</h3><p className="mt-2">{String(solution.summary)}</p></div> : null}</div></section>
      </main>
    </div>
  );
}
