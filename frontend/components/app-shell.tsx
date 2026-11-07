"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/sidebar";
import { TopNavbar } from "@/components/top-navbar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (pathname === "/login") {
    return <main>{children}</main>;
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[220px_1fr]">
      <Sidebar />
      <div className="min-w-0">
        <TopNavbar />
        <main className="min-w-0 p-6 sm:p-8 lg:p-12">{children}</main>
      </div>
    </div>
  );
}
