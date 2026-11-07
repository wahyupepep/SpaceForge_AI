"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SpaceForgeLogo } from "@/components/spaceforge-logo";

const links = [
  { href: "/", label: "Ringkasan", icon: "home" },
  { href: "/projects", label: "Proyek", icon: "folder" },
];

function NavIcon({ name }: { name: string }) {
  return name === "home"
    ? <svg aria-hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-[18px] w-[18px]"><path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955a1.126 1.126 0 0 1 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75" /></svg>
    : <svg aria-hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-[18px] w-[18px]"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V6.108c0-1.135.92-2.055 2.055-2.055h3.91c.552 0 1.08.222 1.466.616l1.22 1.246c.386.394.914.616 1.466.616h7.328c1.135 0 2.055.92 2.055 2.055v8.806c0 1.135-.92 2.055-2.055 2.055H4.305a2.055 2.055 0 0 1-2.055-2.055V12.75Z" /></svg>;
}

export function Sidebar() {
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  return (
    <aside className="border-b border-white/5 bg-[#17201f] px-4 py-4 text-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col lg:border-b-0 lg:border-r lg:px-4 lg:py-5">
      <Link href="/" className="flex items-center gap-3 px-2">
        <SpaceForgeLogo className="h-9 w-9 shrink-0" />
        <span><span className="block text-[15px] font-bold tracking-tight">SpaceForge</span><span className="block text-[9px] font-bold uppercase tracking-[0.16em] text-white/40">System Analyst</span></span>
      </Link>
      {!isLogin ? <nav className="mt-5 flex gap-1 lg:flex-col">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${pathname === link.href || (link.href === "/projects" && pathname.startsWith("/projects")) ? "bg-white/10 text-white" : "text-white/55 hover:bg-white/[0.06] hover:text-white"}`}
          >
            <NavIcon name={link.icon} />
            {link.label}
          </Link>
        ))}
      </nav> : null}
      {!isLogin ? <div className="mt-auto hidden border-t border-white/10 px-2 pt-4 lg:block">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/35">Alur kerja</p>
        <p className="mt-1.5 text-xs leading-5 text-white/55">Konteks → Requirement<br />→ Acuan pengembangan</p>
      </div> : null}
    </aside>
  );
}
