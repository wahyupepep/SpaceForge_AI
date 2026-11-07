"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { authService } from "@/services/auth";

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return <button type="button" disabled={busy} onClick={async () => { setBusy(true); try { await authService.logout(); } finally { router.replace("/login"); router.refresh(); } }} className="rounded-lg border border-ink/10 bg-white px-3.5 py-2 text-xs font-semibold text-ink/60 hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:opacity-50">{busy ? "Keluar…" : "Keluar"}</button>;
}
