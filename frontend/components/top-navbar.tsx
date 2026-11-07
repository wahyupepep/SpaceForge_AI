"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { LogoutButton } from "@/components/logout-button";
import { authService, type AuthUser } from "@/services/auth";

const pageTitle = (pathname: string) => {
  if (pathname === "/") return "Ringkasan";
  if (pathname === "/projects") return "Proyek";
  if (pathname.endsWith("/details")) return "Detail input";
  if (pathname.endsWith("/edit")) return "Edit proyek";
  if (pathname.includes("/outputs")) return "Output analisis";
  if (pathname.includes("/handoff")) return "Serah terima";
  if (pathname === "/projects/new") return "Proyek baru";
  return "Workspace analisis";
};

export function TopNavbar() {
  const pathname = usePathname();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  useEffect(() => { authService.me().then((response) => setUser(response.user)).catch(() => undefined); }, []);
  if (pathname === "/login") return null;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-ink/10 bg-[#f3f1eb]/95 px-6 backdrop-blur sm:px-8 lg:px-10">
      <div><p className="text-[11px] font-bold uppercase tracking-[0.13em] text-ink/35">SpaceForge</p><p className="text-sm font-semibold text-ink/75">{pageTitle(pathname)}</p></div>
      <div className="flex items-center">
      <div className="relative">
        <button
          type="button"
          aria-label="Buka notifikasi"
          aria-expanded={notificationsOpen}
          onClick={() => setNotificationsOpen((value) => !value)}
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-ink/10 bg-white shadow-sm hover:border-ink/20"
        >
          <svg aria-hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 text-ink/65"><path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9a6 6 0 1 0-12 0v.75a8.967 8.967 0 0 1-2.312 6.022 23.848 23.848 0 0 0 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" /></svg>
        </button>
        {notificationsOpen ? (
          <div className="absolute right-0 mt-3 w-80 rounded-2xl border border-ink/10 bg-white p-4 shadow-xl shadow-ink/10">
            <div className="flex items-center justify-between"><p className="font-bold">Notifikasi</p><span className="rounded-full bg-ink/5 px-2 py-1 text-[10px] font-bold text-ink/50">0 BARU</span></div>
            <div className="mt-4 rounded-xl bg-canvas p-4 text-sm leading-6 text-ink/55">Tidak ada notifikasi baru. Permintaan klarifikasi dan hasil review akan muncul di sini.</div>
          </div>
        ) : null}
      </div>
      <div className="mx-3 h-7 w-px bg-ink/10" />
      <div className="mr-3 hidden items-center gap-2.5 sm:flex"><span className="grid h-8 w-8 place-items-center rounded-full bg-[#d9ded8] text-xs font-bold text-ink/70">{user?.display_name?.slice(0, 1).toUpperCase() ?? "U"}</span><div className="max-w-36"><p className="truncate text-xs font-semibold">{user?.display_name ?? "Pengguna"}</p><p className="truncate text-[10px] text-ink/40">System analyst</p></div></div>
      <LogoutButton />
      </div>
    </header>
  );
}
