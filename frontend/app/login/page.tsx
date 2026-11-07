"use client";

import Link from "next/link";
import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { SpaceForgeLogo } from "@/components/spaceforge-logo";
import { ApiClientError } from "@/services/api-client";
import { authService } from "@/services/auth";

import styles from "./login.module.css";

function PasswordVisibilityIcon({ visible }: { visible: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      {visible ? (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M6.3 6.3C4.3 7.6 2.9 9.5 2 12c1.8 4.8 5.2 7.2 10 7.2 2.2 0 4.1-.5 5.7-1.5M9.5 5a13 13 0 0 1 2.5-.2c4.8 0 8.2 2.4 10 7.2a14 14 0 0 1-2.7 4.5" />
        </>
      ) : (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2 12c1.8-4.8 5.2-7.2 10-7.2s8.2 2.4 10 7.2c-1.8 4.8-5.2 7.2-10 7.2S3.8 16.8 2 12Z" />
          <circle cx="12" cy="12" r="3" />
        </>
      )}
    </svg>
  );
}

function AnalysisIllustration() {
  return (
    <figure className={styles.illustration}>
      <div className={styles.documentHeader}>
        <span className={styles.documentIcon} aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z M14 3v6h6M8 13h8M8 17h5" />
          </svg>
        </span>
        <div>
          <p>Rencana pengembangan</p>
          <span>Alur analisis</span>
        </div>
      </div>
      <svg className={styles.workflow} viewBox="0 0 480 320" role="img" aria-labelledby="workflow-title workflow-description">
        <title id="workflow-title">Alur kerja SpaceForge</title>
        <desc id="workflow-description">Konteks proyek menjadi requirement. Setelah solusi disetujui, analisis menghasilkan alur dan antarmuka, spesifikasi teknis, serta rencana kerja.</desc>
        <g fill="none" stroke="#d47b53" strokeWidth="1.5">
          <path d="M240 75v28M240 159v28M240 215v27M85 262v-20h310v20M240 242v20" />
          <path d="m237 98 3 5 3-5M237 182l3 5 3-5" />
        </g>
        <rect x="156" y="19" width="168" height="56" rx="8" fill="#2a3731" stroke="#708076" />
        <g fill="none" stroke="#c7cec8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="177" y="36" width="18" height="21" rx="2" />
          <path d="M182 42h8M182 47h8M182 52h5" />
        </g>
        <text x="207" y="52" fill="#f4f1eb" fontSize="14" fontWeight="500">Konteks proyek</text>
        <rect x="156" y="103" width="168" height="56" rx="8" fill="#bf4623" stroke="#eb865f" />
        <g fill="none" stroke="#fff7ee" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="m177 125 3 3 5-6M189 125h8m-20 13 3 3 5-6M189 138h8" />
        </g>
        <text x="207" y="136" fill="#fff" fontSize="14" fontWeight="500">Requirement</text>
        <circle cx="240" cy="201" r="14" fill="#3c2b20" stroke="#e6a17d" />
        <path d="m234.5 201 3.5 3.5 7-7" fill="none" stroke="#ffc4a1" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <text x="263" y="206" fill="#c2c9c3" fontSize="12">Solusi disetujui</text>
        <g fill="#202b29" stroke="#5e6c63">
          <rect x="15" y="262" width="140" height="42" rx="7" />
          <rect x="170" y="262" width="140" height="42" rx="7" />
          <rect x="325" y="262" width="140" height="42" rx="7" />
        </g>
        <g fill="#e5ece5" fontSize="11.5" fontWeight="500" textAnchor="middle">
          <text x="85" y="288">Alur &amp; antarmuka</text>
          <text x="240" y="288">Spesifikasi teknis</text>
          <text x="395" y="288">Rencana kerja</text>
        </g>
      </svg>
    </figure>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const isRegister = mode === "register";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
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
      const message = caught instanceof ApiClientError
        ? caught.status === 401
          ? "Email atau kata sandi belum sesuai. Periksa kembali dan coba lagi."
          : caught.status === 409 && isRegister
            ? "Email ini sudah terdaftar. Gunakan email tersebut untuk masuk."
            : caught.message
        : "Tidak dapat terhubung. Periksa koneksi Anda, lalu coba lagi.";
      setError(message);
      requestAnimationFrame(() => errorRef.current?.focus());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.page}>
      <section className={styles.main} aria-labelledby="auth-heading">
        <header className={styles.header}>
          <Link href="/login" className={styles.brand} aria-label="SpaceForge, halaman masuk">
            <SpaceForgeLogo className={styles.logo} />
            <span>SpaceForge<span className={styles.brandDescription}>Workspace sistem analis</span></span>
          </Link>
        </header>

        <div className={styles.formRegion}>
          <div className={styles.formContent}>
            <div className={styles.formHeading}>
              <h1 id="auth-heading">{isRegister ? "Buat akun SpaceForge" : "Masuk ke SpaceForge"}</h1>
              <p>{isRegister ? "Mulai proyek analisis pertama Anda." : "Lanjutkan pekerjaan analisis Anda."}</p>
            </div>

            {error ? (
              <div ref={errorRef} role="alert" tabIndex={-1} className={styles.error} id="auth-error">
                {error}
              </div>
            ) : null}

            <form onSubmit={submit} className={styles.form} aria-busy={busy}>
              <fieldset disabled={busy} className={styles.fields}>
                {isRegister ? (
                  <div className={styles.field}>
                    <label htmlFor="auth-name">Nama lengkap</label>
                    <input id="auth-name" required name="display_name" minLength={2} maxLength={120} autoComplete="name" placeholder="Nama Anda" />
                  </div>
                ) : null}
                <div className={styles.field}>
                  <label htmlFor="auth-email">Email</label>
                  <input id="auth-email" required name="email" type="email" maxLength={320} inputMode="email" autoComplete="email" autoCapitalize="none" spellCheck={false} placeholder="nama@perusahaan.com" aria-describedby={error ? "auth-error" : undefined} />
                </div>
                <div className={styles.field}>
                  <label htmlFor="auth-password">Kata sandi</label>
                  <div className={styles.passwordField}>
                    <input id="auth-password" required name="password" type={showPassword ? "text" : "password"} minLength={isRegister ? 10 : 1} maxLength={200} autoComplete={isRegister ? "new-password" : "current-password"} placeholder={isRegister ? "Buat kata sandi" : "Masukkan kata sandi"} aria-describedby={isRegister ? "password-hint" : error ? "auth-error" : undefined} />
                    <button type="button" className={styles.visibilityButton} aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>
                      <PasswordVisibilityIcon visible={showPassword} />
                    </button>
                  </div>
                  {isRegister ? <p id="password-hint" className={styles.hint}>Gunakan minimal 10 karakter.</p> : null}
                </div>
              </fieldset>
              <button type="submit" disabled={busy} className={styles.submit}>
                {busy ? <span className={styles.spinner} aria-hidden="true" /> : null}
                {busy ? isRegister ? "Membuat akun…" : "Sedang masuk…" : isRegister ? "Buat akun" : "Masuk"}
              </button>
            </form>

            <p className={styles.switchMode}>
              {isRegister ? "Sudah punya akun?" : "Belum punya akun?"}{" "}
              <button type="button" disabled={busy} onClick={() => {
                setMode(isRegister ? "login" : "register");
                setError(null);
                setShowPassword(false);
              }}>
                {isRegister ? "Masuk" : "Buat akun"}
              </button>
            </p>
          </div>
        </div>
      </section>

      <aside className={styles.story} aria-labelledby="story-heading">
        <div className={styles.storyIntro}>
          <h2 id="story-heading">Dari kebutuhan<br />ke rencana kerja.</h2>
          <p>Catat kebutuhan, tinjau solusi, dan siapkan spesifikasi yang bisa dikerjakan tim.</p>
        </div>
        <AnalysisIllustration />
      </aside>
    </div>
  );
}
