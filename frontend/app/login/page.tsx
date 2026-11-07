"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "@/services/api-client";
import { authService } from "@/services/auth";

const fieldClass = "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/15";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      if (mode === "register") {
        await authService.register(
          String(form.get("display_name") ?? ""),
          String(form.get("email") ?? ""),
          String(form.get("password") ?? ""),
        );
      } else {
        await authService.login(
          String(form.get("email") ?? ""),
          String(form.get("password") ?? ""),
        );
      }
      router.replace("/projects");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Proses masuk tidak berhasil.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid min-h-[76vh] max-w-5xl items-center gap-12 lg:grid-cols-[1fr_420px]">
      <div className="hidden lg:block"><p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">System analyst workbench</p><h1 className="mt-4 max-w-lg text-[42px] font-semibold leading-[1.08] tracking-[-0.035em]">Requirement yang baik dimulai dari konteks yang dipahami.</h1><p className="mt-5 max-w-md text-sm leading-7 text-ink/50">Simpan jejak keputusan dari penggalian awal hingga acuan kerja developer dan tester.</p><div className="mt-10 border-l-2 border-accent pl-4 text-xs leading-6 text-ink/45">Konteks terstruktur<br />Persetujuan manusia<br />Output yang tertelusur</div></div>
      <section className="w-full border border-ink/10 bg-white/65 p-7 sm:p-9">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-accent">Akses workspace</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight">{mode === "login" ? "Masuk untuk melanjutkan" : "Buat akun baru"}</h2>
        <p className="mt-2 text-sm leading-6 text-ink/45">Data analisis tersimpan di workspace pribadi Anda.</p>
        {error ? <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === "register" ? <label className="block text-sm font-semibold">Nama<input required name="display_name" minLength={2} maxLength={120} className={fieldClass} autoComplete="name" /></label> : null}
          <label className="block text-sm font-semibold">Email<input required name="email" type="email" className={fieldClass} autoComplete="email" /></label>
          <label className="block text-sm font-semibold">Kata sandi<input required name="password" type="password" minLength={mode === "register" ? 10 : 1} className={fieldClass} autoComplete={mode === "register" ? "new-password" : "current-password"} /></label>
          <button disabled={busy} className="w-full rounded-lg bg-accent px-5 py-3 text-sm font-bold text-white hover:bg-[#bd4524] disabled:opacity-50">{busy ? "Mohon tunggu…" : mode === "login" ? "Masuk" : "Buat akun"}</button>
        </form>
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }} className="mt-5 w-full text-sm font-semibold text-ink/55 hover:text-accent">
          {mode === "login" ? "Belum punya akun? Daftar" : "Sudah punya akun? Masuk"}
        </button>
      </section>
    </div>
  );
}
